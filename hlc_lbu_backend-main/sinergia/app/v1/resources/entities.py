from app.v1 import v1_api
from app.v1.models import security
# from app.v1.use_cases.entities import CreateContentTypeUseCase, CreateSiteUseCase, GetContenTypeListUseCase, GetContentBinaryUseCase, GetContentListBySiteUseCase, GetContentListByUserUseCase, GetContentListUseCase, GetEmpresaListUseCase, GetOneContentTypeUseCase, GetOneContentUseCase, GetOneSiteUseCase, GetSiteListUseCase, GetUserBalanceUseCase, PromoteContentUseCase, RefillBalanceUseCase, SiteAffiliationUseCase, SiteFollowUseCase, SiteImpressionsPaymentUseCase, SiteLoveUseCase, ViewImpressionUseCase, CreateContentUseCase
from app.v1.use_cases.entities import GetEmpresaListUseCase
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import Resource, Namespace, fields
from flask_restplus import reqparse
from app.v1.resources.base import ProxySecureResource, secureHeader, queryParams, publicHeader, uploadFilePublicHeader,uploadFileSecureHeader

from flask import send_file
from flask.globals import request    
import json 

entities_ns = v1_api.namespace('entities', description='Business Entities Services')

EmpresaStruct = v1_api.model('EmpresaStruct', { 
    'codigo' : fields.String(), 
    'nombre' : fields.String(), 
})

UpdateEmpresaStruct = v1_api.model('UpdateEmpresaStruct', { 
    'codigo' : fields.String(), 
})

@entities_ns.route('/empresa')
@v1_api.expect(secureHeader)
class EmpresaResource(ProxySecureResource): 

    @entities_ns.doc('Empresa')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()        
        data = GetEmpresaListUseCase().execute(security_credentials)
        return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200


# CreateSiteStruct = v1_api.model('CreateSiteStruct', { 
#     'name' : fields.String(), 
#     'description' : fields.String(), 
# })

# SiteStruct = v1_api.model('SiteStruct', { 
#     'id' : fields.String(),     
#     'name' : fields.String(), 
#     'description' : fields.String(), 
#     'owner' : fields.String(), 
# })

# GetSiteListStruct = v1_api.model('GetSiteListStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'count' : fields.Integer(description='Count Row'), 
#     'total' : fields.Integer(description='Total Row'), 
#     'data' : fields.Nested(SiteStruct,attribute='data')
# }) 

# GetOneSiteStruct = v1_api.model('GetOneSiteStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'data' : fields.Nested(SiteStruct,attribute='data')
# }) 

# RefillBalanceStruct = v1_api.model('RefillBalanceStruct', { 
#     'username' : fields.String(), 
#     'amount' : fields.Float(), 
# })

# BalanceCoinStruct = v1_api.model('BalanceCoinStruct', { 
#     'coin' : fields.String(), 
#     'free' : fields.String(), 
# })

# BalanceUserStruct = v1_api.model('BalanceUserStruct', { 
#     'username' : fields.String(), 
#     'address' : fields.String(), 
#     'balances' : fields.Nested(BalanceCoinStruct,attribute='balances')
# })

# GetOneBalanceUserStruct = v1_api.model('GetOneBalanceUserStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'data' : fields.Nested(BalanceUserStruct,attribute='data')
# }) 

# SiteIdStruct = v1_api.model('SiteIdStruct', { 
#     'id' : fields.String(),     
# })

# SiteImpressionsPaymentStruct = v1_api.model('SiteImpressionsPaymentStruct', { 
#     'id' : fields.String(),    
#     'amount' : fields.Integer(),      
# })

# SiteAndContentStruct = v1_api.model('SiteAndContentStruct', { 
#     'site_id' : fields.String(),    
#     'content_id' : fields.String(),   
# })


# @entities_ns.route('/site')
# @v1_api.expect(secureHeader)
# class SiteResource(ProxySecureResource): 

#     @entities_ns.doc('Site')
#     @v1_api.marshal_with(GetSiteListStruct)     
#     @jwt_required    
#     def get(self):
#         security_credentials = self.checkCredentials()        
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         data = GetSiteListUseCase().execute(security_credentials)
#         return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200

#     @entities_ns.doc('Create Site')
#     @v1_api.expect(CreateSiteStruct)    
#     @jwt_required    
#     def post(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         payload = request.json        
#         CreateSiteUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200


# @entities_ns.route('/site/<id>')
# @entities_ns.param('id', 'Id Site')
# @v1_api.expect(secureHeader)
# class OneSiteResource(ProxySecureResource):

#     @entities_ns.doc('Get Site')
#     @v1_api.marshal_with(GetOneSiteStruct) 
#     @jwt_required    
#     def get(self,id):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'id': id}
#         data = GetOneSiteUseCase().execute(security_credentials,query_params)
#         return  {'ok' : 1, 'data': data}, 200

# @entities_ns.route('/site/affiliate')
# @v1_api.expect(secureHeader)
# class SiteAffiliationResource(ProxySecureResource): 

#     @entities_ns.doc('Affiliate Site')
#     @v1_api.expect(SiteIdStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'avazquez@najoconsultores.com'}
#         payload = request.json        
#         SiteAffiliationUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200 


# @entities_ns.route('/site/follow')
# @v1_api.expect(secureHeader)
# class FollowSiteResource(ProxySecureResource): 

#     @entities_ns.doc('Follow Site')
#     @v1_api.expect(SiteIdStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramonvalera28@gmail.com'}
#         payload = request.json        
#         SiteFollowUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200


# @entities_ns.route('/site/love')
# @v1_api.expect(secureHeader)
# class LoveSiteResource(ProxySecureResource): 

#     @entities_ns.doc('Love Site')
#     @v1_api.expect(SiteIdStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramonvalera28@gmail.com'}
#         payload = request.json        
#         SiteLoveUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200               


# @entities_ns.route('/site/pay_impressions')
# @v1_api.expect(secureHeader)
# class SiteImpressionsPaymentResource(ProxySecureResource): 

#     @entities_ns.doc('Pay Impressions in Site')
#     @v1_api.expect(SiteImpressionsPaymentStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'avazquez@najoconsultores.com'}
#         payload = request.json        
#         SiteImpressionsPaymentUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200        


# @entities_ns.route('/site/view_impression')
# @v1_api.expect(secureHeader)
# class ViewImpressionResource(ProxySecureResource): 

#     @entities_ns.doc('Pay Impressions in Site')
#     @v1_api.expect(SiteAndContentStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramonvalera28@gmail.com'}
#         payload = request.json        
#         ViewImpressionUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200


# @entities_ns.route('/site/promote_content')
# @v1_api.expect(secureHeader)
# class PromoteContentResource(ProxySecureResource): 

#     @entities_ns.doc('Pay Impressions in Site')
#     @v1_api.expect(SiteAndContentStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'avazquez@najoconsultores'}
#         payload = request.json        
#         PromoteContentUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200

# @entities_ns.route('/balance/refill')
# @v1_api.expect(secureHeader)
# class RefillResource(ProxySecureResource): 

#     @entities_ns.doc('Refill Balance')
#     @v1_api.expect(RefillBalanceStruct)    
#     @jwt_required    
#     def put(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         payload = request.json        
#         RefillBalanceUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200

# @entities_ns.route('/balance/<username>')
# @entities_ns.param('username', 'User Name')
# @v1_api.expect(secureHeader)
# class UserBalanceResource(ProxySecureResource):

#     @entities_ns.doc('Get Balance')
#     @v1_api.marshal_with(GetOneBalanceUserStruct) 
#     @jwt_required    
#     def get(self,username):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'username': username}
#         data = GetUserBalanceUseCase().execute(security_credentials,query_params)
#         return  {'ok' : 1, 'data': data}, 200


# ContentStruct = v1_api.model('ContentStruct', { 
#     'id' : fields.String(), 
#     'title' : fields.String(), 
#     'description' : fields.String(), 
#     'author' : fields.String(),
#     'keywords' : fields.String(),
#     'content_type' : fields.String(),
#     'site_id' : fields.String(),
#     'file_name' : fields.String(),
# 	'created_time' : fields.String(),
# 	'update_time' : fields.String(),
#     'binary_data' : fields.String(),
#     'owner' : fields.String()
#     # Customized Fields
#     # 'fields' : fields.Nested(ContentFieldStruct,attribute='fields')
# })

# GetContentListStruct = v1_api.model('GetContentListStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'count' : fields.Integer(description='Count Row'), 
#     'total' : fields.Integer(description='Total Row'), 
#     'data' : fields.Nested(ContentStruct,attribute='data')
# }) 

# GetOneContentStruct = v1_api.model('GetOneContentStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'data' : fields.Nested(ContentStruct,attribute='data')
# }) 


# ContentTypeFieldStruct = v1_api.model('ContentTypeFieldStruct', { 
#     'name' : fields.String(), 
#     'description' : fields.String(), 
#     'primitive_type' : fields.String(),
# })

# CreateContentTypeStruct = v1_api.model('CreateContentTypeStruct', { 
#     'name' : fields.String(), 
#     'description' : fields.String(), 
#     # Customized Fields
#     # 'fields' : fields.Nested(ContentTypeFieldStruct,attribute='fields')
# })

# ContentTypeStruct = v1_api.model('ContentTypeStruct', { 
#     'id' : fields.String(), 
#     'name' : fields.String(), 
#     'description' : fields.String(), 
#     # Customized Fields
#     # 'fields' : fields.Nested(ContentTypeFieldStruct,attribute='fields')
# })

# GetContentTypeListStruct = v1_api.model('GetContentTypeListStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'count' : fields.Integer(description='Count Row'), 
#     'total' : fields.Integer(description='Total Row'), 
#     'data' : fields.Nested(ContentTypeStruct,attribute='data')
# }) 

# GetOneContentTypeStruct = v1_api.model('GetOneContentTypeStruct', { 
#     'ok' : fields.Integer(description='Ok Result'), 
#     'data' : fields.Nested(ContentTypeStruct,attribute='data')
# }) 

# ContentFieldStruct = v1_api.model('ContentFieldStruct', { 
#     'name' : fields.String(), 
#     'value' : fields.String()
# })

# CreateContentStruct = v1_api.model('CreateContentStruct', { 
#     'title' : fields.String(), 
#     'author' : fields.String(),
#     'description' : fields.String(), 
#     'keywords' : fields.String(),
#     'content_type_id' : fields.String(),
#     'site_id' : fields.String(),
#     'binary_data' : fields.String(),
#     'file_name' : fields.String(),
#     # Customized Fields
#     # 'fields' : fields.Nested(ContentFieldStruct,attribute='fields')
# })


# createContentHeader = v1_api.parser()
# createContentHeader.add_argument('title', required = True)
# createContentHeader.add_argument('author', required = True)
# createContentHeader.add_argument('description', required = True)
# createContentHeader.add_argument('keywords', required = True)
# createContentHeader.add_argument('content_type_id', required = True)
# createContentHeader.add_argument('site_id', required = True)

# @entities_ns.route('/content/create')
# @v1_api.expect(secureHeader)
# class CreateContentResource(ProxySecureResource): 

#     @entities_ns.doc('Create Content')
#     @v1_api.expect(CreateContentStruct)
#     @jwt_required    
#     def post(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         payload = request.json  
#         print(payload)

#         CreateContentUseCase().execute(security_credentials,payload)

#         return  {'ok':1 } , 200

# @entities_ns.route('/content/create')
# # @v1_api.expect(uploadFileSecureHeader)
# @v1_api.expect(secureHeader)
# class CreateContentResource(ProxySecureResource): 
#     @entities_ns.doc('Create Content')
#     @v1_api.expect(CreateContentTypeStruct)
#     # @v1_api.expect(createContentHeader)
#     @jwt_required    
#     def post(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         payload = {}
#         args_payload = createContentHeader.parse_args()
#         payload['title'] = args_payload['title']        
#         payload['description'] = args_payload['description']        
#         payload['author'] = args_payload['author']        
#         payload['keywords'] = args_payload['keywords']        
#         payload['content_type_id'] = args_payload['content_type_id']        
#         payload['site_id'] = args_payload['site_id']        
#         # Extract File 
#         args = uploadFilePublicHeader.parse_args() # upload a file
#         uploaded_file = args['file']
#         CreateContentUseCase().execute(security_credentials,payload,uploaded_file)
#         return  {'ok':1 } , 200

# @entities_ns.route('/content')
# @v1_api.expect(secureHeader)
# class ContentResource(ProxySecureResource):    
#     @entities_ns.doc('Content')
#     @v1_api.marshal_with(GetContentListStruct)     
#     @jwt_required    
#     def get(self):
#         security_credentials = self.checkCredentials()        
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         data = GetContentListUseCase().execute(security_credentials)
#         # for d in data:
#         #     d['url_binary_data'] = '/entities/content/binary/%s' % d['binary_data']
#         print(data)
#         return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200

# import io

# @entities_ns.route('/content/binary/<id>')
# @entities_ns.param('id', 'Id Content')
# # @v1_api.expect(publicHeader)
# # @v1_api.expect(secureHeader)
# class ContentBinaryResource(Resource):
#     @entities_ns.doc('Binary Content')
#     # @jwt_required    
#     def get(self,id):
#         # security_credentials = self.checkCredentials()        
#         security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = { 'id': id }
#         (bites,file_name,mimetype) = GetContentBinaryUseCase().execute(security_credentials,query_params)
#         return send_file(io.BytesIO(bites),attachment_filename=file_name,mimetype=mimetype)


# @entities_ns.route('/content/<id>')
# @entities_ns.param('id', 'Id Content')
# @v1_api.expect(secureHeader)
# class OneContentResource(ProxySecureResource):

#     @entities_ns.doc('Get Content')
#     @v1_api.marshal_with(GetOneContentStruct) 
#     @jwt_required    
#     def get(self,id):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'id': id}
#         data = GetOneContentUseCase().execute(security_credentials,query_params)
#         return  {'ok' : 1, 'data': data}, 200

# @entities_ns.route('/content/user/<username>')
# @entities_ns.param('username', 'Username')
# @v1_api.expect(secureHeader)
# class GetContentByUserResource(ProxySecureResource):

#     @entities_ns.doc('Get Content by Username')
#     @v1_api.marshal_with(GetContentListStruct) 
#     @jwt_required    
#     def get(self,username):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'username': username}
#         data = GetContentListByUserUseCase().execute(security_credentials,query_params)
#         return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200

# @entities_ns.route('/content/site/<site_id>')
# @entities_ns.param('site_id', 'Site Id')
# @v1_api.expect(secureHeader)
# class GetContentBySiteResource(ProxySecureResource):

#     @entities_ns.doc('Get Content by Site')
#     @v1_api.marshal_with(GetContentListStruct) 
#     @jwt_required    
#     def get(self,site_id):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'site_id': site_id}
#         data = GetContentListBySiteUseCase().execute(security_credentials,query_params)
#         return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200


# @entities_ns.route('/content_type')
# @v1_api.expect(secureHeader)
# class ContentTypeResource(ProxySecureResource): 

#     @entities_ns.doc('Create Content Type')
#     @v1_api.expect(CreateContentTypeStruct)
#     @jwt_required    
#     def post(self):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         payload = request.json  
#         CreateContentTypeUseCase().execute(security_credentials,payload)
#         return  {'ok':1 } , 200

#     @entities_ns.doc('Content Type')
#     @v1_api.marshal_with(GetContentTypeListStruct)     
#     @jwt_required    
#     def get(self):
#         security_credentials = self.checkCredentials()        
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         data = GetContenTypeListUseCase().execute(security_credentials)
#         return  {'ok':1,  "count": len(data), "total": len(data), 'data': data} , 200

# @entities_ns.route('/content_type/<id>')
# @entities_ns.param('id', 'Id Content Type')
# @v1_api.expect(secureHeader)
# # class OneContentTypeResource(Resource):
# # @v1_api.expect(publicHeader)
# class OneContentTypeResource(ProxySecureResource):

#     @entities_ns.doc('Get Content Type')
#     @v1_api.marshal_with(GetOneSiteStruct) 
#     @jwt_required    
#     def get(self,id):
#         security_credentials = self.checkCredentials()
#         # security_credentials = {'username' : 'ramon.valera@gmail.com'}
#         query_params = {'id': id}
#         data = GetOneContentTypeUseCase().execute(security_credentials,query_params)
#         return  {'ok' : 1, 'data': data}, 200