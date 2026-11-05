from flask import Blueprint
from flask_restplus import Api
from app import redis_client, jwt, babel
from flask.globals import request
from werkzeug.local import LocalProxy
from flask import current_app
import json
from app.exceptions.base import SinergiaException, NotAccessException

logger = LocalProxy(lambda: current_app.logger)

v2_blueprint = Blueprint('v2_blueprint', __name__,template_folder='/templates')
v2_api = Api(v2_blueprint,
             title='Sinergia Security API',
             version='2.0',
             description='OpenAPI to Sinergia Security Service')

from app.v2.resources.external import external_ns
from app.v2.resources.application import application_ns
from app.v2.resources.tasks import tasks_ns
from app.v2.resources.ad_set import ad_set_ns
from app.v2.resources.ad import ad_ns
from app.v2.resources.service import service_ns
from app.v2.resources.brand import brand_ns
from app.v2.resources.storage import storage_ns
from app.v2.resources.buyer_person import buyer_person_ns
from app.v2.resources.psd_resize import psd_resize_ns
from app.v2.resources.utils import utils_ns
from app.v2.resources.product import product_ns
from app.v2.resources.project import project_ns
from app.v2.resources.umbrella_campaign import umbrella_ns
from app.v2.resources.campaign import campaign_ns

LANGUAGES = {
    'en': 'English',
    'es': 'Espanol'
}

#@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(LANGUAGES.keys())

@v2_blueprint.errorhandler(NotAccessException)
def custom_handler_exception(e):
    return {'ok': 0, 'message': {'code': e.code, 'text': e.text} } , 401

@v2_blueprint.errorhandler(SinergiaException)
def custom_handler_exception(e):
    return {'ok': 0, 'message': {'code': e.code, 'text': e.text} } , 400
    
@jwt.expired_token_loader
def handle_expired_signature_error(e):
    return {'ok': 0, 'message': {'code': 'ESEC001', 'text': 'Token expired'} }, 401

@jwt.revoked_token_loader
def handle_revoked_signature_error():
    return {'ok': 0, 'message': {'code': 'ESEC001', 'text': 'Token expired'} }, 401

@jwt.invalid_token_loader
def handle_invalid_token_error(e):
    return {'ok': 0, 'message': {'code': 'ESEC002', 'text': 'Token incorrect, supplied or malformed'} }, 401

@jwt.unauthorized_loader
def handle_unauthorized_token_error(e):
    return {'ok': 0, 'message': {'code': 'ESEC002', 'text': 'Token incorrect, supplied or malformed'} }, 401

@jwt.token_in_blacklist_loader
def check_if_token_is_revoked(decrypted_token):
    logger.debug(request.headers)
    jti = decrypted_token['jti']
    entry = redis_client.get(jti)
    if entry is None:
        return True
    json_entry = json.loads(entry)
    return 'session_expired' in json_entry  and json_entry['session_expired'] == 'true'


@v2_blueprint.app_errorhandler(404)
def error_handler_404(error):
    return {'ok': 0, 'message': {'code': 'E404', 'text': 'Path not Found!' } }, 404

@v2_blueprint.app_errorhandler(500)
def error_handler_500(error):
    return {'ok': 0, 'message': {'code': 'E500', 'text': 'Internal Server Error -> %s' % str(error) } }, 500

@v2_blueprint.app_errorhandler(401)
def error_handler_401(error):
    return {'ok': 0, 'message': {'code': 'E401', 'text': 'Server Error -> %s' % str(error) } }, 400

@v2_blueprint.app_errorhandler(400)
def error_handler_400(error):
    return {'ok': 0, 'message': {'code': 'E400', 'text': 'Server Error -> %s' % str(error) } }, 400


v2_api.add_namespace(application_ns)
v2_api.add_namespace(ad_set_ns)
v2_api.add_namespace(ad_ns)
v2_api.add_namespace(external_ns)
v2_api.add_namespace(tasks_ns)
v2_api.add_namespace(service_ns)
v2_api.add_namespace(brand_ns)
v2_api.add_namespace(storage_ns)
v2_api.add_namespace(buyer_person_ns)
v2_api.add_namespace(psd_resize_ns)
v2_api.add_namespace(utils_ns)
v2_api.add_namespace(product_ns)
v2_api.add_namespace(project_ns)
v2_api.add_namespace(umbrella_ns)
v2_api.add_namespace(campaign_ns)