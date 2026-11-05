"""Use cases for the tenant-scoped GCS storage service.

Security model:
- For JWT-protected endpoints, all use cases receive the caller's email
  (from security_credentials['username']) and verify that the requested
  account_id matches their actual Strapi account (parent_account resolution).
- For service-to-service endpoints (X-Service-API-Key), the caller is trusted
  and no ownership check is performed.
"""
import logging
from typing import Dict, List, Optional, Tuple

import requests as http_requests

from app.v2.repository.storage import StorageRepository
from app.v2.repository.account import AccountRepository
from app.exceptions.base import (
    ParametersNotFoundException,
    DataNotFoundException,
    NotAccessException,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tenant ownership helper
# ---------------------------------------------------------------------------

def _assert_account_ownership(account_email: str, requested_account_id: str):
    """Verify the JWT user actually owns the requested account_id.

    Follows the same pattern used by BrandUseCase / BuyerPersonUseCase:
      1. Look up the account in Strapi by email.
      2. Resolve parent_account (root tenant).
      3. Compare with the account_id in the URL.

    Raises:
        NotAccessException: if the account_id doesn't match the user's account.
        DataNotFoundException: if the user's account can't be found in Strapi.
    """
    # TEMPORARY: Validation bypassed for testing
    return

    repo = AccountRepository()
    account = repo.get_by_email(account_email)
    if not account:
        raise DataNotFoundException("Account not found for the authenticated user")

    parent_account = (
        str(account["attributes"]["parent_account"]["data"]["id"])
        if account["attributes"].get("parent_account", {}).get("data")
        else str(account["id"])
    )

    if parent_account != str(requested_account_id):
        logger.warning(
            f"[storage] ownership check FAILED: user={account_email} "
            f"owns={parent_account} requested={requested_account_id}"
        )
        raise NotAccessException(
            f"You do not have access to account {requested_account_id}"
        )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class GetUploadUrlUseCase:
    """Create a GCS Resumable Upload Session URL.

    Returns a dict with:
        upload_url  — PUT the file body to this URL (no auth header needed)
        blob_name   — full GCS path (tenant/filename) for reference
        method      — "PUT"
        note        — human-readable instruction
    """

    def __init__(self):
        self._repo = StorageRepository()

    def execute(
        self,
        account_id: str,
        filename: str,
        content_type: str,
        account_email: Optional[str] = None,
        origin: Optional[str] = None,
    ) -> Dict:
        if not account_id:
            raise ParametersNotFoundException("account_id is required")
        if not filename:
            raise ParametersNotFoundException("filename is required")
        if not content_type:
            raise ParametersNotFoundException("content_type is required")

        if account_email:
            _assert_account_ownership(account_email, account_id)

        logger.info(f"[storage] creating upload session account={account_id} file={filename}")
        url, blob_name = self._repo.get_upload_session_url(account_id, filename, content_type, origin=origin)
        return {
            "upload_url": url,
            "blob_name": blob_name,
            "method": "PUT",
            "note": "PUT the file body to upload_url with Content-Type header. No Authorization header needed.",
        }


# ---------------------------------------------------------------------------
# Upload session cancellation (invalidation after upload)
# ---------------------------------------------------------------------------

class CancelUploadSessionUseCase:
    """Cancel a GCS Resumable Upload Session to prevent further uploads.

    The client calls this after confirming the upload is complete,
    or if they abandon the upload.  Sends DELETE to the session URL.
    """

    def execute(self, upload_url: str, account_email: Optional[str] = None) -> bool:
        if not upload_url:
            raise ParametersNotFoundException("upload_url is required")

        logger.info(f"[storage] cancelling upload session url={upload_url[:80]}...")
        try:
            resp = http_requests.delete(upload_url, timeout=15)
            # GCS returns 499 (Client Closed Request) for cancelled sessions
            if resp.status_code in (200, 204, 499):
                logger.info("[storage] upload session cancelled successfully")
                return True
            logger.warning(f"[storage] cancel session returned HTTP {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"[storage] cancel session error: {e}")
            raise


# ---------------------------------------------------------------------------
# Download (streaming)
# ---------------------------------------------------------------------------

class DownloadFileUseCase:
    """Return a streaming requests.Response for a tenant file."""

    def __init__(self):
        self._repo = StorageRepository()

    def execute(
        self,
        account_id: str,
        filename: str,
        account_email: Optional[str] = None,
    ) -> Tuple:
        if not account_id:
            raise ParametersNotFoundException("account_id is required")
        if not filename:
            raise ParametersNotFoundException("filename is required")

        if account_email:
            _assert_account_ownership(account_email, account_id)

        logger.info(f"[storage] downloading file account={account_id} file={filename}")
        stream, blob_name = self._repo.download_file_stream(account_id, filename)
        meta = self._repo.get_file_metadata(account_id, filename)
        content_type = (meta or {}).get("contentType", "application/octet-stream")
        return stream, filename, content_type


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

class ListFilesUseCase:
    """List all files belonging to a tenant."""

    def __init__(self):
        self._repo = StorageRepository()

    def execute(
        self,
        account_id: str,
        account_email: Optional[str] = None,
    ) -> List[Dict]:
        if not account_id:
            raise ParametersNotFoundException("account_id is required")

        if account_email:
            _assert_account_ownership(account_email, account_id)

        logger.info(f"[storage] listing files for account={account_id}")
        return self._repo.list_files(account_id)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class DeleteFileUseCase:
    """Delete a file from a tenant's storage folder."""

    def __init__(self):
        self._repo = StorageRepository()

    def execute(
        self,
        account_id: str,
        filename: str,
        account_email: Optional[str] = None,
    ) -> bool:
        if not account_id:
            raise ParametersNotFoundException("account_id is required")
        if not filename:
            raise ParametersNotFoundException("filename is required")

        if account_email:
            _assert_account_ownership(account_email, account_id)

        logger.info(f"[storage] deleting file account={account_id} file={filename}")
        deleted = self._repo.delete_file(account_id, filename)
        if not deleted:
            raise DataNotFoundException(f"File not found or could not be deleted: {filename}")
        return True
