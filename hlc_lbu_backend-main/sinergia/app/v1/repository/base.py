'''
Created on 17 dic. 2019

@author: ramon
'''
from app.tools.substrate import Substrate
from app.v1.models.security import SecurityElement, User, PersonExtension
from app import redis_client
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from app.exceptions.base import BiostartException, CryptoPOSException, ConnectionException,N8NException

class CacheRepository(object):

    DEFAULT_EXPIRED_TIME = 600

    def getByKey(self,key):
        value = redis_client.get(key)
        json_value = None
        if (not value is None):
            json_value = json.loads(value)        
        return json_value

    def save(self,key,payload,expired_time = int(DEFAULT_EXPIRED_TIME)):
        json_payload = json.dumps(payload)
        redis_client.set(key, json_payload,ex=expired_time)

    def deleteByKey(self,key):
        value = redis_client.delete(key)


class SinergiaRepository(object):
    username = None
    token = None

    def getUser(self):
        user = User.query.filter(User.name==self.username.lower()).first()        
        return user       

    def __init__(self,username=None,token=None):
        self.username = username        
        self.token = token

class SubstrateRepository(object):
    substrate = None
    username = None

    def __init__(self,username=None):
        self.username = username        
        self.substrate = Substrate()


import urllib.parse
from config import Config
import os

class N8NClient(object):

    url_base = "http://localhost:5678"
    credentials = {}
    
    def __init__(self,url_base=None,credentials=None):
        if (not url_base is None):
            self.url_base = url_base
        else:
            current_config = Config()
            self.url_base = current_config.N8N_SERVICE_URI

        if (not credentials is None):
            self.credentials = credentials
    


    def executePost(self, end_point, payload, authenticate = True,is_binary=False,params={},files={},timeout=300):
        service_response = None
        try:
            headers = {
                # 'content-type': "application/json",
                'cache-control': "no-cache"
            }

            if authenticate:
                headers['email'] = self.credentials['username']

            json_payload = json.dumps(payload)
            final_url = urllib.parse.urljoin(self.url_base,end_point)

            if len(files) == 0:
                headers['content-type'] =  "application/json"
                response = requests.post(final_url ,data=json_payload,headers=headers,params=params,timeout=timeout)
            else:
               response = requests.post(final_url,headers=headers,params=params,files=files,timeout=timeout)
 
            response.raise_for_status()
        except HTTPError as http_err:           
            if response.status_code == 400:
                response_json = response.json()
                raise N8NException(text=response_json['message']['text'])
            else:
                raise ConnectionException(text='HTTP error occurred: %s' % http_err)
        except Exception as err:
            raise N8NException(text='Other error occurred: %s' % err)
        else:
            if not is_binary:
                service_response = json.loads(response.text)
            else:
                service_response = {
                    'content' : response.content,
                    'content_type' : response.headers.get('content-type','').lower()
                }
        
        return service_response


    def executePut(self, end_point, payload, authenticate = True, timeout=300):
        json_response = None
        try:
            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache"
            }
            if authenticate:
                headers['email'] = self.credentials['username']
    
            json_payload = json.dumps(payload)
    
            final_url = urllib.parse.urljoin(self.url_base,end_point)
            response = requests.put(final_url ,data=json_payload,headers=headers,timeout=timeout)

            response.raise_for_status()
        except HTTPError as http_err:           
            if response.status_code == 400:
                response_json = response.json()
                raise N8NException(text=response_json['message']['text'])
            else:
                raise ConnectionException(text='HTTP error occurred: %s' % http_err)
        except Exception as err:
            raise N8NException(text='Other error occurred: %s' % err)
        else:
            json_response = json.loads(response.text)
        
        return json_response


    def executeGet(self, end_point, params={}, authenticate = True,is_binary=False, timeout=300):
        service_response = None
        try:

            headers = {
                'content-type': "application/json",
                'cache-control': "no-cache"
            }
            if authenticate:
                headers['email'] = self.credentials['username']
    
            final_url = urllib.parse.urljoin(self.url_base,end_point)
            response = requests.get(final_url ,params=params,headers=headers,timeout=timeout)
            response.raise_for_status()
            
        except HTTPError as http_err:
            if response.status_code == 400:
                response_json = response.json()
                raise N8NException(text=response_json['message']['text'])
            else:
                raise ConnectionException(text='HTTP error occurred: %s' % http_err)
        except Exception as err:
            raise N8NException(text='Other error occurred: %s' % err)
        else:
            if not is_binary:
                service_response = json.loads(response.text)
            else:
                service_response = {
                    'content' : response.content,
                    'content_type' : response.headers.get('content-type','').lower()
                }
        
        return service_response

# from .cryptopos import *
