"""Storage endpoints — tenant-isolated file storage on Google Cloud Storage.

Two authentication modes, same operations:

  Frontend (JWT) — ownership verified against Strapi account:
    POST   /api/v2/storage/<account_id>/upload-url
    POST   /api/v2/storage/<account_id>/upload-confirm     (cancels session after upload)
    GET    /api/v2/storage/<account_id>/files
    GET    /api/v2/storage/<account_id>/files/<path:filename>/download
    DELETE /api/v2/storage/<account_id>/files/<path:filename>

  Service-to-service (X-Service-API-Key — trusted caller, no ownership check):
    POST   /api/v2/storage/service/<account_id>/upload-url
    POST   /api/v2/storage/service/<account_id>/upload-confirm
    GET    /api/v2/storage/service/<account_id>/files
    GET    /api/v2/storage/service/<account_id>/files/<path:filename>/download
    DELETE /api/v2/storage/service/<account_id>/files/<path:filename>

Upload flow (large file friendly — no bytes through Flask):
  1. POST .../upload-url        → Sinergia creates a GCS Resumable Session URL
  2. Client PUTs file directly  → GCS handles storage; Flask is never a proxy
  3. POST .../upload-confirm    → Client notifies server; server cancels the session
                                  preventing any further uploads to that URL
"""
import logging
import os

from flask import request, Response, stream_with_context
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import Resource

from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.tools.service_auth import service_api_key_required
from app.exceptions.base import SinergiaException, NotAccessException, DataNotFoundException
from app.v2.use_cases.storage import (
    GetUploadUrlUseCase,
    CancelUploadSessionUseCase,
    DownloadFileUseCase,
    ListFilesUseCase,
    DeleteFileUseCase,
)

logger = logging.getLogger(__name__)


def _err_msg(e: Exception) -> str:
    """Extract a readable message from any exception type."""
    if isinstance(e, SinergiaException):
        return e.text or repr(e)
    return str(e) or repr(e)


storage_ns = v2_api.namespace(
    "storage",
    description="Tenant-isolated file storage (Google Cloud Storage)",
)


# ---------------------------------------------------------------------------
# Shared logic — reused by both auth flavors
# ---------------------------------------------------------------------------

def _upload_url(account_id: str, account_email: str = None) -> tuple:
    body = request.json or {}
    filename = body.get("filename")
    content_type = body.get("content_type")
    origin = request.headers.get("Origin")
    if not filename or not content_type:
        return {"ok": False, "message": {"code": "EVAL001", "text": "filename and content_type are required"}}, 400
    data = GetUploadUrlUseCase().execute(account_id, filename, content_type, account_email, origin=origin)
    return {"ok": True, "data": data}, 200


def _cancel_upload(account_id: str) -> tuple:
    body = request.json or {}
    upload_url = body.get("upload_url")
    if not upload_url:
        return {"ok": False, "message": {"code": "EVAL001", "text": "upload_url is required"}}, 400
    CancelUploadSessionUseCase().execute(upload_url)
    return {"ok": True, "message": {"code": "I001", "text": "Upload session cancelled"}}, 200


def _list_files(account_id: str, account_email: str = None) -> tuple:
    data = ListFilesUseCase().execute(account_id, account_email)
    return {"ok": True, "data": data, "total": len(data)}, 200


def _download_file(account_id: str, filename: str, account_email: str = None) -> Response:
    """Stream the file from GCS to the client."""
    stream, dl_filename, content_type = DownloadFileUseCase().execute(
        account_id, filename, account_email
    )

    def generate():
        try:
            for chunk in stream.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    yield chunk
        finally:
            stream.close()

    safe_name = os.path.basename(dl_filename)
    return Response(
        stream_with_context(generate()),
        content_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "X-Blob-Name": f"{account_id}/{dl_filename}",
        },
    )


def _delete_file(account_id: str, filename: str, account_email: str = None) -> tuple:
    DeleteFileUseCase().execute(account_id, filename, account_email)
    return {"ok": True, "message": {"code": "I001", "text": f"{filename} deleted"}}, 200


# ===========================================================================
# FRONTEND — JWT protected + tenant ownership verified
# ===========================================================================

@storage_ns.route("/<string:account_id>/upload-url")
@v2_api.expect(secureHeader)
class StorageUploadUrl(ProxySecureResource):
    """Get a GCS Resumable Upload Session URL to upload a file directly."""

    @storage_ns.doc("Generate Upload Session URL")
    @jwt_required
    def post(self, account_id: str):
        creds = self.checkCredentials()
        try:
            return _upload_url(account_id, account_email=creds["username"])
        except NotAccessException as e:
            return {"ok": False, "error": _err_msg(e)}, 403
        except Exception as e:
            logger.error(f"[storage] upload-url error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/<string:account_id>/upload-confirm")
@v2_api.expect(secureHeader)
class StorageUploadConfirm(ProxySecureResource):
    """Cancel the upload session after the file has been successfully uploaded.

    Body: { "upload_url": "<the session URL returned by /upload-url>" }
    """

    @storage_ns.doc("Confirm Upload & Invalidate Session")
    @jwt_required
    def post(self, account_id: str):
        self.checkCredentials()
        try:
            return _cancel_upload(account_id)
        except Exception as e:
            logger.error(f"[storage] upload-confirm error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/<string:account_id>/files")
@v2_api.expect(secureHeader)
class StorageFileList(ProxySecureResource):
    """List all files for a tenant."""

    @storage_ns.doc("List Tenant Files")
    @jwt_required
    def get(self, account_id: str):
        creds = self.checkCredentials()
        try:
            return _list_files(account_id, account_email=creds["username"])
        except NotAccessException as e:
            return {"ok": False, "error": _err_msg(e)}, 403
        except Exception as e:
            logger.error(f"[storage] list error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/<string:account_id>/files/<path:filename>/download")
@v2_api.expect(secureHeader)
class StorageDownload(ProxySecureResource):
    """Stream a file from GCS to the client."""

    @storage_ns.doc("Download File (streaming)")
    @jwt_required
    def get(self, account_id: str, filename: str):
        creds = self.checkCredentials()
        try:
            return _download_file(account_id, filename, account_email=creds["username"])
        except NotAccessException as e:
            return {"ok": False, "error": _err_msg(e)}, 403
        except DataNotFoundException as e:
            return {"ok": False, "error": _err_msg(e)}, 404
        except Exception as e:
            logger.error(f"[storage] download error account={account_id} file={filename}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/<string:account_id>/files/<path:filename>")
@v2_api.expect(secureHeader)
class StorageFileDelete(ProxySecureResource):
    """Delete a specific file from tenant storage."""

    @storage_ns.doc("Delete File")
    @jwt_required
    def delete(self, account_id: str, filename: str):
        creds = self.checkCredentials()
        try:
            return _delete_file(account_id, filename, account_email=creds["username"])
        except NotAccessException as e:
            return {"ok": False, "error": _err_msg(e)}, 403
        except Exception as e:
            logger.error(f"[storage] delete error account={account_id} file={filename}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


# ===========================================================================
# SERVICE-TO-SERVICE — X-Service-API-Key (trusted, no ownership check)
# ===========================================================================

@storage_ns.route("/service/<string:account_id>/upload-url")
class ServiceStorageUploadUrl(Resource):
    @storage_ns.doc("[Service] Generate Upload Session URL")
    @service_api_key_required
    def post(self, account_id: str):
        try:
            return _upload_url(account_id)  # no email → no ownership check
        except Exception as e:
            logger.error(f"[storage][svc] upload-url error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/service/<string:account_id>/upload-confirm")
class ServiceStorageUploadConfirm(Resource):
    @storage_ns.doc("[Service] Confirm Upload & Invalidate Session")
    @service_api_key_required
    def post(self, account_id: str):
        try:
            return _cancel_upload(account_id)
        except Exception as e:
            logger.error(f"[storage][svc] upload-confirm error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/service/<string:account_id>/files")
class ServiceStorageFileList(Resource):
    @storage_ns.doc("[Service] List Tenant Files")
    @service_api_key_required
    def get(self, account_id: str):
        try:
            return _list_files(account_id)
        except Exception as e:
            logger.error(f"[storage][svc] list error account={account_id}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/service/<string:account_id>/files/<path:filename>/download")
class ServiceStorageDownload(Resource):
    @storage_ns.doc("[Service] Download File (streaming)")
    @service_api_key_required
    def get(self, account_id: str, filename: str):
        try:
            return _download_file(account_id, filename)
        except DataNotFoundException as e:
            return {"ok": False, "error": _err_msg(e)}, 404
        except Exception as e:
            logger.error(f"[storage][svc] download error account={account_id} file={filename}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500


@storage_ns.route("/service/<string:account_id>/files/<path:filename>")
class ServiceStorageFileDelete(Resource):
    @storage_ns.doc("[Service] Delete File")
    @service_api_key_required
    def delete(self, account_id: str, filename: str):
        try:
            return _delete_file(account_id, filename)
        except Exception as e:
            logger.error(f"[storage][svc] delete error account={account_id} file={filename}: {e}")
            return {"ok": False, "error": _err_msg(e)}, 500
