from functools import wraps
from flask import abort
from app import redis_client
from app.v1.models.constant import SUFFIX_PERMISSION
from app.exceptions.base import NotAccessException

import json
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def check_access(roles=[], function=None, access=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            security_credentials = args[0].checkCredentials()
            username = security_credentials['username']
            if username is None:
                raise NotAccessException()
            
            if not function or not access:
                raise NotAccessException()
            
            permissions = redis_client.get(f"{username}{SUFFIX_PERMISSION}")
            
            if not permissions:
                raise NotAccessException()
            
            if not _is_allowed(roles, function, access, permissions):
                raise NotAccessException()
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def _is_allowed(roles, function, access, permissions):
    json_permissions = json.loads(permissions)

    # Validar si tiene alguno de los Roles especificados
    if len(roles) > 0:
        for p in json_permissions:
            if p['rol_long_name'] in roles:
                logger.info(f"Rol: {p['rol_long_name']}")
                return True  

    # Validar si tiene la funcion y el acceso especificado            
    filtered_function = [item for item in json_permissions if function in item['function_name']]

    if not len(filtered_function) > 0:
        return False

    for a in filtered_function:
        filtered_access = [item for item in a['actions'] if access in item['id']]
        if filtered_access:
            logger.info(f"Role: {a['rol_long_name']}, Function: {a['function_name']}, Access: {filtered_access}")
            return True
        
    return False