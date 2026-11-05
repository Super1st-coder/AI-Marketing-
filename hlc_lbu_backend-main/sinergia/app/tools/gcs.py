"""Google Cloud Storage client for Sinergia.

Signing constraint: the Compute Engine VM's OAuth access scopes are limited
(storage only, no IAM), and the org policy blocks SA key creation.
Therefore Signed URLs are NOT available.

Upload strategy — Resumable Upload Session:
  The server creates a GCS Resumable Upload Session using its storage token
  and returns the session URL to the client.  The client then PUTs the file
  directly to GCS without passing through Flask.  GCS resumable sessions
  support arbitrarily large files and can be resumed if the connection drops.

Download strategy — Streaming Proxy:
  The server fetches the object from GCS using its storage token and streams
  the bytes back to the client in chunks.  Flask's stream_with_context keeps
  memory usage flat regardless of file size.

All other operations (list, delete, exists) use the standard GCS JSON API
via google-cloud-storage, which only needs storage scope.
"""
import datetime
import logging
import urllib.parse
from typing import Dict, Iterator, List, Optional

import google.auth
import google.auth.transport.requests
import requests as http_requests
from google.cloud import storage

logger = logging.getLogger(__name__)

_UPLOAD_API = "https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o"
_DOWNLOAD_API = "https://storage.googleapis.com/storage/v1/b/{bucket}/o/{obj}?alt=media"


class GCSClient:
    """GCS wrapper that works with storage-only OAuth scopes (no signing)."""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self._credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self._client = storage.Client(
            credentials=self._credentials,
            project=project,
        )

    def _fresh_token(self) -> str:
        """Return a valid Bearer token, refreshing if necessary."""
        req = google.auth.transport.requests.Request()
        if not self._credentials.valid:
            self._credentials.refresh(req)
        return self._credentials.token

    # ------------------------------------------------------------------
    # Upload — Resumable Session URL
    # ------------------------------------------------------------------

    def create_upload_session(
        self,
        blob_name: str,
        content_type: str,
        metadata: Optional[Dict] = None,
        origin: Optional[str] = None,
    ) -> str:
        """Create a GCS Resumable Upload Session and return its upload URL.

        The URL is temporary (~7 days) and requires no authentication to PUT.
        The client uploads the file body directly to GCS using this URL.

        Args:
            blob_name:    Full GCS object path (e.g. "tenant/file.pdf").
            content_type: MIME type of the file to upload.
            metadata:     Optional GCS object metadata dict.

        Returns:
            Resumable upload session URL (the Location header from GCS).

        Raises:
            requests.HTTPError: if the GCS API returns an error.
        """
        token = self._fresh_token()
        url = _UPLOAD_API.format(bucket=self.bucket_name)
        body = {"contentType": content_type}
        if metadata:
            body["metadata"] = metadata

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Type": content_type,
        }
        if origin:
            headers["Origin"] = origin

        resp = http_requests.post(
            url,
            params={"uploadType": "resumable", "name": blob_name},
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        session_url = resp.headers.get("Location")
        if not session_url:
            raise RuntimeError("GCS did not return a Location header for the resumable session")
        return session_url

    # ------------------------------------------------------------------
    # Download — Streaming Iterator
    # ------------------------------------------------------------------

    def download_object_stream(
        self, blob_name: str, chunk_size: int = 1024 * 1024
    ):
        """Stream a GCS object as a requests.Response (streaming mode).

        The caller is responsible for iterating and closing the response.

        Returns:
            requests.Response with stream=True.

        Raises:
            requests.HTTPError: if the object does not exist or access is denied.
        """
        token = self._fresh_token()
        encoded = urllib.parse.quote(blob_name, safe="")
        url = _DOWNLOAD_API.format(bucket=self.bucket_name, obj=encoded)
        resp = http_requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            stream=True,
            timeout=60,
        )
        resp.raise_for_status()
        return resp

    def get_object_metadata(self, blob_name: str) -> Optional[Dict]:
        """Return GCS object metadata or None if not found."""
        token = self._fresh_token()
        encoded = urllib.parse.quote(blob_name, safe="")
        url = f"https://storage.googleapis.com/storage/v1/b/{self.bucket_name}/o/{encoded}"
        resp = http_requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------

    def list_blobs(self, prefix: str) -> List[Dict]:
        """List all blobs whose name starts with *prefix*."""
        try:
            blobs = self._client.list_blobs(self.bucket_name, prefix=prefix)
            result = []
            for blob in blobs:
                result.append(
                    {
                        "name": blob.name,
                        "size": blob.size,
                        "content_type": blob.content_type,
                        "updated": blob.updated.isoformat() if blob.updated else None,
                        "gs_uri": f"gs://{self.bucket_name}/{blob.name}",
                    }
                )
            return result
        except Exception as e:
            logger.error(f"[GCSClient] list_blobs error (prefix={prefix}): {e}")
            raise

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a single object. Returns True on success."""
        try:
            bucket = self._client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"[GCSClient] delete_blob error (blob={blob_name}): {e}")
            raise

    # ------------------------------------------------------------------
    # Existence check
    # ------------------------------------------------------------------

    def blob_exists(self, blob_name: str) -> bool:
        """Return True if the object exists in the bucket."""
        try:
            bucket = self._client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            return blob.exists()
        except Exception as e:
            logger.error(f"[GCSClient] blob_exists error (blob={blob_name}): {e}")
            raise
