import os
import requests
import google.auth.transport.requests
import google.oauth2.id_token
from flask import request, Response, current_app
from flask_restplus import Resource
from werkzeug.datastructures import FileStorage
from flask_jwt_extended.view_decorators import jwt_required

from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.exceptions.base import SinergiaException
import logging
from app.v2.use_cases.storage import DownloadFileUseCase

logger = logging.getLogger(__name__)

psd_resize_ns = v2_api.namespace(
    "psd-resize",
    description="PSD Resize via Cloud Run"
)

upload_parser = v2_api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=False, help='PSD File')
upload_parser.add_argument('account_id', location='form', type=str, required=False, help='Account ID for GCS')
upload_parser.add_argument('filename', location='form', type=str, required=False, help='Filename in GCS')
upload_parser.add_argument('preserve_layers', location='form', type=str, default='true')
upload_parser.add_argument('engine', location='form', type=str, default='auto')
upload_parser.add_argument('auto_layout', location='form', type=str, default='false')

@psd_resize_ns.route("", "/")
@v2_api.expect(secureHeader)
class PSDResize(ProxySecureResource):
    @psd_resize_ns.doc("Resize PSD")
    @v2_api.expect(upload_parser)
    @jwt_required
    def post(self):
        try:
            args = upload_parser.parse_args()
            file_obj = args.get('file')
            account_id = args.get('account_id')
            filename = args.get('filename')
            preserve_layers = args.get('preserve_layers', 'true')
            engine = args.get('engine', 'auto')
            auto_layout = args.get('auto_layout', 'false')
            
            # Validar parámetros
            if not file_obj and not (account_id and filename):
                return {"ok": False, "message": {"code": "EVAL001", "text": "Debes proveer un archivo (file) o credenciales de storage (account_id + filename)."}}, 400
                
            cloud_run_url = current_app.config.get('PSD_RESIZE_URL')
            if not cloud_run_url:
                return {"ok": False, "message": {"code": "E500", "text": "PSD_RESIZE_URL no está configurada."}}, 500
                
            endpoint = f"{cloud_run_url.rstrip('/')}/process-psd"
            
            try:
                auth_req = google.auth.transport.requests.Request()
                audience = cloud_run_url.rstrip('/')
                id_token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
            except Exception as e:
                logger.exception("Error obteniendo token IAM de Google Cloud Run")
                return {"ok": False, "message": {"code": "E500", "text": f"Error obteniendo token IAM: {e}"}}, 500
                
            headers = {"Authorization": f"Bearer {id_token}"}
            
            creds = self.checkCredentials()

            # Preparamos el archivo para enviar
            files = {}
            if account_id and filename:
                # Opción 1: Delegar la descarga a Cloud Run (bypasses 32MB limit)
                try:
                    from app.v2.repository.storage import StorageRepository
                    repo = StorageRepository()
                    data = {
                        "preserve_layers": preserve_layers.lower() if isinstance(preserve_layers, str) else preserve_layers,
                        "engine": engine,
                        "auto_layout": auto_layout.lower() if isinstance(auto_layout, str) else auto_layout,
                        "gcs_bucket": repo._bucket,
                        "gcs_object": f"{account_id}/{filename.lstrip('/')}"
                    }
                    # Force multipart/form-data because FastAPI expects it when File() is present
                    files["dummy_file_to_force_multipart"] = ("", b"")
                except Exception as e:
                    logger.exception(f"Error preparando parámetros GCS de Storage (Account: {account_id})")
                    return {"ok": False, "message": {"code": "E500", "text": f"Error configurando GCS: {e}"}}, 500
            else:
                # Opción 2: Archivo subido directamente desde el cliente
                file_bytes = file_obj.read()
                if not file_bytes.startswith(b'8BPS'):
                    return {"ok": False, "message": {"code": "EVAL002", "text": "El archivo recibido no es un PSD válido (la firma de bytes es incorrecta). Asegúrate de que el frontend no esté enviando un error XML en lugar del archivo."}}, 400
                files["file"] = (file_obj.filename, file_bytes, "application/octet-stream")
                data = {
                    "preserve_layers": preserve_layers.lower() if isinstance(preserve_layers, str) else preserve_layers,
                    "engine": engine,
                    "auto_layout": auto_layout.lower() if isinstance(auto_layout, str) else auto_layout
                }
            
            try:
                # Enviamos el POST a Cloud Run
                resp = requests.post(endpoint, files=files, data=data, headers=headers, timeout=300)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                error_msg = str(e)
                if hasattr(e, 'response') and getattr(e, 'response') is not None:
                    error_msg += f" - {e.response.text}"
                logger.error(f"Error devuelto por Cloud Run: {error_msg}")
                return {"ok": False, "message": {"code": "E502", "text": f"Error del servicio Cloud Run: {error_msg}"}}, 502
                
            original_name = filename if account_id and filename else file_obj.filename
            safe_filename = original_name.rsplit('.', 1)[0]
            
            if account_id and filename:
                resp_json = resp.json()
                if not resp_json.get("ok"):
                    return {"ok": False, "message": {"code": "E500", "text": "Error from Cloud Run (no ok flag)"}}, 500
                    
                result_object = resp_json.get("result_object")
                dl_filename = result_object.split('/')[-1] if '/' in result_object else result_object
                
                try:
                    from app.v2.use_cases.storage import DownloadFileUseCase
                    stream, _, _ = DownloadFileUseCase().execute(account_id, dl_filename, creds.get("username"))
                    return Response(
                        stream.iter_content(chunk_size=8192),
                        mimetype="application/zip",
                        headers={
                            "Content-Disposition": f"attachment; filename={safe_filename}_exports.zip"
                        }
                    )
                except Exception as e:
                    logger.exception("Error streaming ZIP from GCS")
                    return {"ok": False, "message": {"code": "E500", "text": f"Error obteniendo resultado de GCS: {e}"}}, 500
            else:
                return Response(
                    resp.content,
                    mimetype="application/zip",
                    headers={
                        "Content-Disposition": f"attachment; filename={safe_filename}_exports.zip"
                    }
                )
        except Exception as e:
            logger.exception("Excepción no manejada en PSD Resize Endpoint")
            return {"ok": False, "message": {"code": "E500", "text": f"Error interno en Sinergia: {e}"}}, 500
