'''
Created on 17 dic. 2019

@author: ramon
'''
from app.v1.models.security import SecurityElement, User, PersonExtension
from app import redis_client, db, alembic
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from app.exceptions.base import CryptoPOSException, ConnectionException,NotImplementedException,RepositoryUnknownException,DataNotFoundException,IntegrityException
from .base import SinergiaRepository

import json
 
import pandas as pd

from sqlalchemy.sql import text

from psycopg2 import OperationalError, errorcodes, errors        

from app.exceptions.base import DatabaseException,IntegrityException
from psycopg2 import OperationalError, errorcodes, errors
from sqlalchemy import exc

