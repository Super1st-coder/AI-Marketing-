'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.models.security import SecurityElement, User, PersonExtension, Rol
from app.v1.models.constant import *

from app import redis_client, db, alembic
from app.exceptions.base import UserCurrentPasswordException,UserRepeatedPasswordException,RepositoryUnknownException
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from app.exceptions.base import CryptoPOSException, ConnectionException,NotImplementedException,DatabaseException,IntegrityException
from .base import SinergiaRepository

import pandas as pd
import hashlib
import datetime
from sqlalchemy.sql import text

from sqlalchemy import exc

