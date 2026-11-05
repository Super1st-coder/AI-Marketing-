'''
Created on 17 dic. 2019

@author: ramon
'''
from datetime import datetime
import json
from app.exceptions.base import DataNotFoundException
from config import config
# from app.v1.repository.entities import BalanceRepository, ContentTypeRepository, EmpresaRepository, SiteRepository, ContentRepository
from app.v1.repository.entities import EmpresaRepository

class GetEmpresaListUseCase(object):
    def execute(self,security_credentials):
        return EmpresaRepository(username=security_credentials['username']).getAll()

# class GetSiteListUseCase(object):
#     def execute(self,security_credentials):
#         return SiteRepository(username=security_credentials['username']).getAll()

# class GetOneSiteUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return SiteRepository(username=security_credentials['username']).getById(query_params['id'])

# class CreateSiteUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).new(payload)

# class GetUserBalanceUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return BalanceRepository(username=security_credentials['username']).get(query_params['username'])

# class RefillBalanceUseCase(object):
#     def execute(self,security_credentials,payload):
#         origen = config['dev'].SUBSTRATE_MASTER_ACCOUNT
#         BalanceRepository(username=security_credentials['username']).transfer(origen, payload['username'], payload['amount'])

# class SiteAffiliationUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).make_affiliation(payload['id'])

# class SiteImpressionsPaymentUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).pay_impressions(payload['id'],payload['amount'])

# class ViewImpressionUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).view_impression(payload['site_id'],payload['content_id'])

# class SiteFollowUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).follow(payload['id'])

# class SiteLoveUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).love(payload['id'])

# class PromoteContentUseCase(object):
#     def execute(self,security_credentials,payload):
#         SiteRepository(username=security_credentials['username']).view_impression(payload['site_id'],payload['content_id'])

# import base64

# class CreateContentUseCase(object):
#     def execute(self,security_credentials,payload,uploaded_file):

#         if uploaded_file.filename == '':
#             raise DataNotFoundException(text="Upload File Not Found!")

#         filename = uploaded_file.filename
#         created_time = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
#         update_time = created_time

#         payload['file_name'] = filename
#         payload['created_time'] = created_time
#         payload['update_time'] = update_time

#         # Encode File To Send 
#         file_encoded = ''
#         b64_encoded_data = base64.b64encode(uploaded_file.read())
#         file_encoded = b64_encoded_data.decode('ascii')

#         ContentRepository(username=security_credentials['username']).new(payload,file_encoded)

#     def execute(self,security_credentials,payload):

#         created_time = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
#         update_time = created_time

#         payload['created_time'] = created_time
#         payload['update_time'] = update_time

#         # Encode File To Send 
#         file_encoded = ''
#         # b64_encoded_data = base64.b64encode(uploaded_file.read())
#         # file_encoded = b64_encoded_data.decode('ascii')

#         # Creado para Probar el tema de la carga de datos
#         file_encoded = ''
#         if 'binary_data' in payload :
#             file_encoded = payload['binary_data']
#             payload.pop('binary_data', None)
#         else:
#             with open("/home/ramon/Desarrollos/digitalizacion/imagenes/Captura.png", "rb") as image_file:
#                 encoded_image = base64.b64encode(image_file.read())
#                 file_encoded = encoded_image.decode('ascii')

#             payload['file_name'] = 'Captura.png'

#         payload['author'] = security_credentials['username']
#         print(payload)

#         if 'binary_data' in payload :
#             file_encoded = payload['binary_data']
#             payload.pop('binary_data', None)

#         ContentRepository(username=security_credentials['username']).new(payload,file_encoded)


# class GetContentListUseCase(object):
#     def execute(self,security_credentials):
#         return ContentRepository(username=security_credentials['username']).getAll()

# class GetContentListBySiteUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return ContentRepository(username=security_credentials['username']).getBySite(query_params['site_id'])

# class GetContentListByUserUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return ContentRepository(username=security_credentials['username']).getByUsername(query_params['username'])

# class GetOneContentUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return ContentRepository(username=security_credentials['username']).getById(query_params['id'])

# import mimetypes

# class GetContentBinaryUseCase(object):
#     def execute(self,security_credentials,query_params):
#         metadata_id = query_params['id']
#         content_repository = ContentRepository(username=security_credentials['username'])
#         metadata_content = content_repository.getById(metadata_id)
#         file_name = metadata_content['file_name']
#         mimetype = mimetypes.MimeTypes().guess_type(file_name)[0]
#         binary_data = content_repository.getBinaryById(metadata_content['binary_data'])
#         string_data = str(binary_data['content'])
#         bytes_content = base64.b64decode(string_data)          
#         return bytes_content,file_name,mimetype

###############################################################################################

# class CreateContentTypeUseCase(object):
#     def execute(self,security_credentials,payload):
#         ContentTypeRepository(username=security_credentials['username']).new(payload)        

# class GetContenTypeListUseCase(object):
#     def execute(self,security_credentials):
#         return ContentTypeRepository(username=security_credentials['username']).getAll()

# class GetOneContentTypeUseCase(object):
#     def execute(self,security_credentials,query_params):
#         return ContentTypeRepository(username=security_credentials['username']).getById(query_params['id'])
