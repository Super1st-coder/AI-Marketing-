from flask import Blueprint, jsonify, Response
from flask_restplus import Api
# from .exceptions import ValidationException
from app import redis_client, jwt, babel
import json
from app.exceptions.base import SinergiaException, NotAccessException
from flask.globals import request
from flask_babel import gettext

from werkzeug.local import LocalProxy
from flask import current_app

logger = LocalProxy(lambda: current_app.logger)

v1_blueprint = Blueprint('v1_blueprint', __name__,template_folder='/templates')
v1_api = Api(v1_blueprint,
             title='Sinergia Security API',
             version='1.0',
             description='OpenAPI to Sinergia Security Service')

from app.v1.resources.base import member_ns
from app.v1.resources.entities import entities_ns
from app.v1.resources.configuration import configuration_ns
from app.v1.resources.admin import admin_ns
from app.v1.resources.system import system_ns
from app.v1.resources.process import process_ns
from app.v1.resources.application import application_ns

# pybabel extract -o locale/base.pot  .
# pybabel init -i base.pot -d translations -l en
# pybabel compile -d app/translations

LANGUAGES = {
    'en': 'English',
    'es': 'Espanol'
}

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(LANGUAGES.keys())

@v1_blueprint.errorhandler(NotAccessException)
def custom_handler_exception(e):
    return {'ok': 0, 'message': {'code': e.code, 'text': e.text} } , 401

@v1_blueprint.errorhandler(SinergiaException)
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


@v1_blueprint.app_errorhandler(404)
def error_handler_404(error):
    return {'ok': 0, 'message': {'code': 'E404', 'text': 'Path not Found!' } }, 404

@v1_blueprint.app_errorhandler(500)
def error_handler_500(error):
    return {'ok': 0, 'message': {'code': 'E500', 'text': 'Internal Server Error -> %s' % str(error) } }, 500

@v1_blueprint.app_errorhandler(401)
def error_handler_401(error):
    return {'ok': 0, 'message': {'code': 'E401', 'text': 'Server Error -> %s' % str(error) } }, 400

@v1_blueprint.app_errorhandler(400)
def error_handler_400(error):
    return {'ok': 0, 'message': {'code': 'E400', 'text': 'Server Error -> %s' % str(error) } }, 400


@v1_blueprint.before_app_request
def before_request():
    headers = {'Access-Control-Allow-Origin': '*',
               'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
               'Access-Control-Allow-Headers': 'Content-Type'}
    if request.method.lower() == 'options':
        #return jsonify(headers), 200
        return Response()

v1_api.add_namespace(member_ns)
v1_api.add_namespace(entities_ns)
v1_api.add_namespace(configuration_ns)
v1_api.add_namespace(admin_ns)
v1_api.add_namespace(system_ns)
v1_api.add_namespace(process_ns)
v1_api.add_namespace(application_ns)
