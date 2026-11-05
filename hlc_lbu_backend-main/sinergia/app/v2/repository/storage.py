"""Storage repository — tenant-isolated file operations on GCS.

All objects are stored under the path:
    {account_id}/{filename}

This ensures tenant isolation at the blob-prefix level.

Upload flow (large file friendly):
  The server creates a GCS Resumable Upload Session URL and returns it
  to the caller.  The caller PUTs the file directly to GCS without
  routing it through Flask.

Download flow:
  The server fetches the object from GCS and streams it back in chunks.
"""
import logging
import os
from typing import Dict, List, Optional, Tuple

from config import config
from app.tools.gcs import GCSClient
from app.exceptions.base import S3ClientException, DataNotFoundException

logger = logging.getLogger(__name__)

config_type = os.environ.get("CONFIG_TYPE", "dev")


class StorageRepository:
    """High-level GCS operations scoped to a single tenant (account_id)."""

    def __init__(self):
        cfg = config.get(config_type)
        bucket_name = getattr(cfg, "GCS_BUCKET", None)
        if not bucket_name:
            raise S3ClientException("GCS_BUCKET is not configured")
        self._bucket = bucket_name
        self._gcs = GCSClient(bucket_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _blob_name(account_id: str, filename: str) -> str:
        """Build the full GCS blob path for a tenant file."""
        return f"{account_id}/{filename.lstrip('/')}"

    # ------------------------------------------------------------------
    # Upload — returns a GCS resumable session URL
    # ------------------------------------------------------------------

    def get_upload_session_url(
        self, account_id: str, filename: str, content_type: str, origin: Optional[str] = None
    ) -> Tuple[str, str]:
        """Create a GCS Resumable Upload Session.

        Returns:
            (upload_url, blob_name) — the caller PUT the file to upload_url.
        """
        blob_name = self._blob_name(account_id, filename)
        url = self._gcs.create_upload_session(blob_name, content_type, origin=origin)
        return url, blob_name

    # ------------------------------------------------------------------
    # Download — streaming response from GCS
    # ------------------------------------------------------------------

    def download_file_stream(self, account_id: str, filename: str):
        """Return a streaming requests.Response for the file.

        Raises:
            DataNotFoundException: if the blob does not exist.
        """
        blob_name = self._blob_name(account_id, filename)
        if not self._gcs.blob_exists(blob_name):
            raise DataNotFoundException(f"File not found: {filename}")
        return self._gcs.download_object_stream(blob_name), blob_name

    def get_file_metadata(self, account_id: str, filename: str) -> Optional[Dict]:
        """Return GCS object metadata for a file, or None."""
        blob_name = self._blob_name(account_id, filename)
        return self._gcs.get_object_metadata(blob_name)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def list_files(self, account_id: str) -> List[Dict]:
        """List all files belonging to *account_id*."""
        prefix = f"{account_id}/"
        blobs = self._gcs.list_blobs(prefix=prefix)
        for blob in blobs:
            blob["filename"] = blob["name"][len(prefix):]
        return blobs

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete_file(self, account_id: str, filename: str) -> bool:
        """Delete a file from the tenant's folder."""
        blob_name = self._blob_name(account_id, filename)
        return self._gcs.delete_blob(blob_name)
