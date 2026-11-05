'''
Created on 17 dic. 2019

@author: ramon
'''
from getpass import getuser
from app.exceptions.base import DataNotFoundException, DatabaseException
from app.tools.substrate import Substrate
from app.v1.models.security import SecurityElement, User, PersonExtension
from app.v1.models.business import Empresa
from app import redis_client, db
import json
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from .base import SinergiaRepository, SubstrateRepository

import pandas as pd
import logging

from sqlalchemy import text    
from sqlalchemy import select, func
from sqlalchemy import and_

from psycopg2 import OperationalError, errorcodes, errors    
from sqlalchemy import exc
from datetime import datetime, timedelta
from app.v1.models.constant import *

class EmpresaRepository(SinergiaRepository):
    def getAll(self):
        try:
            table_df = pd.read_sql_query('select * from business.empresa',con=db.engine)
            table_df = table_df.fillna('')
            result = table_df.to_dict('records')
            return result
        except exc.DatabaseError as err:
            # pass exception to function
            error_description = '%s' % (err)
            raise DatabaseException(text=error_description)

# class ContentTypeRepository(SubstrateRepository):

#     def new(self, data):
#         json_data = json.dumps(data)
#         params = {
#             'conten_type_raw' : json_data,
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','create_content_type',params)
#         if result is None:
#             raise DatabaseException(text="Can't save ContentType!")
#         return {'ok' : 1}

#     def getById(self,id):
#         e = self.substrate.execute_query('TemplateModule','ContenTypes',[id])
#         if e is None:
#             raise DataNotFoundException(text='Content Type NOT Found!')            
#         filtered_element = {}
#         filtered_element = {
#                 'id' : e['id'],
#                 'name' : e['name'],
#                 'description' : e['description'],
#                 'owner' : e['owner'],
#             }
#         return filtered_element


#     def getByUsername(self,email):
#         keypair_origen = self.substrate.create_keypair(email)
#         data = self.substrate.execute_query('TemplateModule','UserContenTypes',[keypair_origen.ss58_address])
#         if e is None:
#             raise DataNotFoundException(text='Content Type NOT Found!')
#         filtered_data = []
#         for e in data:
#             filtered_data.append({
#                 'id' : e['id'],
#                 'name' : e['name'],
#                 'description' : e['description'],
#                 'owner' : e['owner'],
#             })
#         return filtered_data


#     def getAll(self):
#         data = self.substrate.execute_query('TemplateModule','AllContenTypes',[])
#         filtered_data = []
#         for e in data:
#             filtered_data.append({
#                 'id' : e['id'],
#                 'name' : e['name'],
#                 'description' : e['description'],
#                 'owner' : e['owner'],
#             })
#         return filtered_data


# class ContentRepository(SubstrateRepository):

#     def new(self, metadata, file_data):
#         json_data = json.dumps(metadata)
#         params = {
#             'content_type_id' : metadata['content_type_id'],
#             'site_id' : metadata['site_id'],
#             'metadata' : json_data,
#             'binary' : file_data
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','create_user_entry',params)
#         if result is None:
#             raise DatabaseException(text="Can't save Site!")
#         return {'ok' : 1}

#     def getById(self,id):
#         data = self.substrate.execute_query('TemplateModule','Metadata',[id])
#         if data is None:
#             raise DataNotFoundException(text='Content NOT Found!')            
#         return data.serialize()

#     def getBinaryById(self,id):
#         data = self.substrate.execute_query('TemplateModule','Binaries',[id])
#         if data is None:
#             raise DataNotFoundException(text='Content NOT Found!')        
#         return data.serialize()

#     def getByUsername(self,email):
#         keypair_origen = self.substrate.create_keypair(email)
#         data = self.substrate.execute_query('TemplateModule','UserEntries',[keypair_origen.ss58_address])
#         if data is None:
#             raise DataNotFoundException(text='Content NOT Found!')
#         return data.serialize()

#     def getBySite(self,site_id):
#         data = self.substrate.execute_query('TemplateModule','SiteEntries',[site_id])
#         if data is None:
#             raise DataNotFoundException(text='Content NOT Found!')            
#         return data.serialize()

#     def getAll(self):
#         data = self.substrate.execute_query('TemplateModule','AllEntries',[])
#         if data is None:
#             raise DataNotFoundException(text='Content NOT Found!')            
#         return data.serialize()


# class SiteRepository(SubstrateRepository):

#     def new(self, data):
#         params = {
#             'name' : data['name'],
#             'description' : data['description']
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','create_site',params)
#         if result is None:
#             raise DatabaseException(text="Can't save Site!")
#         return {'ok' : 1}

#     def make_affiliation(self, id):

#         params = {
#             'site_id' : id,
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','make_affiliation',params)
#         if result is None:
#             raise DatabaseException(text="Can't Make Affiliation in Site!")
#         return {'ok' : 1}

#     def follow(self, id):

#         params = {
#             'site_id' : id,
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','follow_site',params)
#         if result is None:
#             raise DatabaseException(text="Can't Follow Site!")
#         return {'ok' : 1}

#     def love(self, id):

#         params = {
#             'site_id' : id,
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','love_site',params)
#         if result is None:
#             raise DatabaseException(text="Can't Love Site!")
#         return {'ok' : 1}


#     def pay_impressions(self, id, amount):
#         params = {
#             'site_id' : id,
#             'amount' : amount
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','pay_impression',params)
#         if result is None:
#             raise DatabaseException(text="Can't Pay Impression in Site!")
#         return {'ok' : 1}

#     def view_impression(self, site_id, content_id):
#         params = {
#             'site_id' : site_id,
#             'content_id' : content_id
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','view_impression',params)
#         if result is None:
#             raise DatabaseException(text="Can't Make Impression in Site!")
#         return {'ok' : 1}

#     def promote_content(self, site_id, content_id):
#         params = {
#             'site_id' : site_id,
#             'content_id' : content_id
#         }
#         keypair = self.substrate.create_keypair(self.username)
#         result = self.substrate.execute_call(keypair,'TemplateModule','promote_content',params)
#         if result is None:
#             raise DatabaseException(text="Can't Promote Content in Site!")
#         return {'ok' : 1}

    
#     def getById(self,id):
#         e = self.substrate.execute_query('TemplateModule','Sites',[id])
#         filtered_element = {}
#         if not e is None:
#             filtered_element = {
#                     'id' : e['id'],
#                     'name' : e['name'],
#                     'description' : e['description'],
#                     'owner' : e['owner'],
#                 }
#         else:
#             raise DataNotFoundException(text='Site NOT Found!')
        
#         return filtered_element 

#     def getAll(self):
#         data = self.substrate.execute_query('TemplateModule','AllSites',[])
#         filtered_data = []
#         for e in data:
#             filtered_data.append({
#                 'id' : e['id'],
#                 'name' : e['name'],
#                 'description' : e['description'],
#                 'owner' : e['owner'],
#             })
#         return filtered_data

# class BalanceRepository(SubstrateRepository):

#     def get(self,origen) :
#         keypair_origen = self.substrate.create_keypair(origen)
#         filtered_element = { 'username' : origen, 'address' : keypair_origen.ss58_address }

#         balances = []


#         # Warocoin Balance
#         result = self.substrate.execute_query('System','Account',[keypair_origen.ss58_address])
#         if not result is None:
#             if 'data' in result:
#                 # Se hace esta operacion para manejar 2 Decimales en las cantidades
#                 free = result['data']['free']
#                 long_free = int(str(free))
#                 balance_free = float(long_free * (10 ** -2)) if long_free > 0 else 0
#                 balances.append({
#                     'coin' : 'WRX',
#                     'free' : balance_free
#                 })
#             else: 
#                 balances.append({
#                     'coin' : 'WRX',
#                     'free' : 0
#                 })
#         else:
#             balances.append({
#                 'coin' : 'WRX',
#                 'free' : 0
#             })

        
#         # Gamification Token Balance
#         result = self.substrate.execute_query('TemplateModule','BalanceToAccount',[keypair_origen.ss58_address])
#         if not result is None:
#             free = int(str(result))
#             balances.append({
#                 'coin' : 'WRX-USR',
#                 'free' : result
#             })
#         else: 
#             balances.append({
#                 'coin' : 'WRX-USR',
#                 'free' : 0
#             })            

#         filtered_element['balances'] = balances
#         print(filtered_element)

#         return filtered_element 

#     def transfer(self, origen, destino, cantidad):
#         keypair_origen = self.substrate.create_keypair(origen)
#         keypair_destino = self.substrate.create_keypair(destino)
#         params = {
#             'dest': keypair_destino.ss58_address,
#             'value': cantidad * 10**2          
#         }
#         result = self.substrate.execute_call(keypair_origen,'Balances','transfer',params)
#         if result is None:
#             raise DatabaseException(text="Can't save Site!")        