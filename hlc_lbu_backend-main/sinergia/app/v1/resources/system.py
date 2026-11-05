from flask import current_app, request, jsonify
from flask_restplus import Resource, Namespace, fields
from app import db, redis_client
from app.v1 import v1_api
import re
import jwt
import datetime
import hashlib
from flask_jwt_extended.utils import create_access_token, create_refresh_token,\
    get_jti, get_raw_jwt, get_jwt_identity
from flask_jwt_extended.view_decorators import jwt_required,\
    jwt_refresh_token_required
from ..use_cases.security import AuthenticateUseCase
import json
import requests
from requests.auth import HTTPBasicAuth
from ..repository.base import CacheRepository
from app.exceptions.base import SinergiaException, ProxyCredentialsNotFound
from app.v1.resources.base import ProxySecureResource, secureHeader,queryParams, DateRangeStruct

from app.v1.models.constant import STATUS_ACTIVE, STATUS_GENERATED,\
    STATUS_PENDING

# from tools.json import AlchemyEncoder
from app.tools.sqlalchemy import entity_as_dict
from app.tools.response_tools import make_template_response

system_ns = v1_api.namespace('system', description='System Services')
