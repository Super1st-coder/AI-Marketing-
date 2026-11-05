from app.v1 import v1_api
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import Resource, Namespace, fields
from app.v1.resources.base import ProxySecureResource, secureHeader,queryParams
from flask.globals import request    
import json 

configuration_ns = v1_api.namespace('configuration', description='Configuration Services')
