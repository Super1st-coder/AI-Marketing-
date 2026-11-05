import json
import os
from flask.globals import request
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import fields
from io import BytesIO
from app.tools.permissions import check_access
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from app.v1.models.constant import FUNCTION_PRODUCT, ACTION_CREATE, ACTION_UPDATE, ACTION_READ, ROLE_HILUCA_ADMIN
from app.v2 import v2_api
from app.v2.use_cases.product import ProductBaseUseCase, DeleteProductImageUseCase
from app.v2.models.constant import PRODUCT_MAX_IMAGES
from config import config

product_ns = v2_api.namespace('application', description='Aplication Services')

config_type = os.environ.get('CONFIG_TYPE', 'dev')

DefineProductStruct = v2_api.model('DefineProductStruct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'product_url': fields.String(),
    'description': fields.String(),
    'language': fields.String()
})

SaveProductAttributesStruct = v2_api.model('SaveProductAttributesStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'not_advance': fields.Boolean(),
    'trigger_prompts': fields.Boolean(),
    'mandatory_attributes_generated': fields.Raw(),
    'mandatory_attributes_saved': fields.Raw(),
    'optional_attributes_generated': fields.Raw(),
    'optional_attributes_saved': fields.Raw()
})

DefineProductAttributesCategoryStruct = v2_api.model('DefineProductAttributesCategoryStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'category': fields.String(),
    'ask': fields.String(),
    'answer': fields.String()
})

UpdateProductStruct = v2_api.model('UpdateProductStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'name': fields.String(),
    'product_url': fields.String(),
    'description': fields.String(),
    'language': fields.String()
})

GenerateProductAttributesStruct = v2_api.model('GenerateProductAttributesStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

SaveProductCompleteStruct = v2_api.model('SaveProductCompleteStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'product_story': fields.String()
})

UploadProductImageIDStruct = v2_api.model('UploadProductImageIDStruct', { 
    'brand_id': fields.Integer(),
    'product_id': fields.Integer(),
    'image_id': fields.String()
})


@product_ns.route('/hiluca/brand/product')
@v2_api.expect(secureHeader)
class HilucaResourceDefineProduct(ProxySecureResource):     

    @product_ns.doc('Update a Product')
    @v2_api.expect(UpdateProductStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/product',payload,True)
        return  response, 200
    

    @product_ns.doc('Create a Product')
    @v2_api.expect(DefineProductStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/product',payload,True)
        return  response, 200


@product_ns.route('/hiluca/brand/<brand_id>/product/<product_id>/document')
@v2_api.expect(secureHeader)
class HilucaResourceProductDocumets(ProxySecureResource): 

    @product_ns.doc('Upload Product Documents')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self,brand_id,product_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        user_id = security_credentials['username']

        bucket_region = ProductBaseUseCase(user_id).get_docs_bucket_config()['region']

        files = request.files.to_dict(flat=False)

        files_dict = {}
        for i, value in enumerate(files['files']):
            content_type = value.content_type
            filename = value.filename

            buffer_image = BytesIO(value.read())
            buffer_image.seek(0)
            files_dict.update({f'file{i}' : (filename, buffer_image.read() , content_type)})

        params = { 'brand_id' : brand_id, 'product_id' : product_id, 'bucket_region': bucket_region }

        response = n8nClient.executePost('/webhook/v2/product/document',{},True,is_binary=False,params=params,files=files_dict)

        return  response, 200
    
    
@product_ns.route('/hiluca/brand/product/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceProductAttributesGenerate(ProxySecureResource): 
 
    @product_ns.doc('Generate Product Attributes')
    @v2_api.expect(GenerateProductAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/product/attributes/generate',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/product/category/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceProductAttributesCategory(ProxySecureResource): 
 
    @product_ns.doc('Generate Product Attributes By Category')
    @v2_api.expect(DefineProductAttributesCategoryStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/product/category/attributes',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/product/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceProductAttributes(ProxySecureResource): 
 
    @product_ns.doc('Save Product Attributes')
    @v2_api.expect(SaveProductAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/product/attributes',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/<brand_id>/product')
@v2_api.expect(secureHeader)
class HilucaResourceGetProducts(ProxySecureResource): 
 
    @product_ns.doc('Get a Product List From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'brand_id' : brand_id }

        limit = 10
        offset = 0
        filter_key = None
        filter_value = None
        order_key = None
        order_value = None

        filter = request.args.to_dict(flat=True)
        if 'onlyComplete' in filter and filter['onlyComplete'].upper() == 'TRUE':
            payload.update({'onlyComplete': True})

        if 'range' in  request.args and request.args['range']:
            range = eval(request.args['range'])
            if len(range) >= 2:
                low_limit = range[0]
                high_limit = range[1]
            else:
                low_limit = range[0]
                high_limit = range[0]

            limit = (high_limit - low_limit) + 1
            offset = low_limit

        if 'filter' in request.args and request.args['filter']:
            filter_param = request.args.get('filter', '').strip()
            filter_obj = json.loads(filter_param)
            if not isinstance(filter_obj, dict):
                return {"error": "Filter must be a JSON object with one field."}, 400
            filter_key, filter_value = list(filter_obj.items())[0]

        if 'order' in request.args and request.args['order']:
            order_param = request.args.get('order', '').strip()
            order_obj = json.loads(order_param)
            if not isinstance(order_obj, dict) or len(order_obj) != 1:
                return {"error": "Order must be a JSON object with one field."}, 400
            order_key, order_value = list(order_obj.items())[0]

            allowed_fields = ['name', 'createdAt', 'updatedAt']
            allowed_directions = ['asc', 'desc']

            if order_key not in allowed_fields:
                return {"error": f"Invalid order field '{order_key}'."}, 400
            if order_value.lower() not in allowed_directions:
                return {"error": f"Invalid order direction '{order_value}'."}, 400
            
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"

        payload.update({
            'limit': limit,
            'offset': offset,
            'filterKey': filter_key,
            'filterValue': filter_value,
            'orderKey': order_key,
            'orderValue': order_value,
            'API_URL': API_URL
        })

        response = n8nClient.executeGet('/webhook/v2/products',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/<brand_id>/product/<product_id>')
@v2_api.expect(secureHeader)
class HilucaResourceGetProduct(ProxySecureResource): 
 
    @product_ns.doc('Get a Product From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_READ)
    def get(self,product_id,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'product_id' : product_id, 'brand_id' : brand_id }
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"
        payload['API_URL'] = API_URL
        response = n8nClient.executeGet('/webhook/v2/product',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/<brand_id>/product/<product_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceSaveImageProduct(ProxySecureResource): 
 
    @product_ns.doc('Upload Product Image ')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self,brand_id,product_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        cfg = config.get(config_type)
        API_URL = getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')

        params = { 'brand_id' : brand_id, 'product_id' : product_id, 'MAX_IMAGES': PRODUCT_MAX_IMAGES, 'API_URL': API_URL }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/product/image',{},True,is_binary=False,params=params,files=files)

        return response, 200
    
    # @application_ns.doc('Get Image By Product')
    # @jwt_required    
    # def get(self,brand_id,product_id):
    #     security_credentials = self.checkCredentials()
    #     n8nClient = N8NClient(credentials=security_credentials)
    #     payload = { 'brand_id' : brand_id, 'product_id' : product_id }
    #     response = n8nClient.executeGet('/webhook/v2/product/image',payload,True,is_binary=True)

    #     buffer_image = BytesIO(response['content'])
    #     buffer_image.seek(0)

    #     return send_file(buffer_image, mimetype=response['content_type'])     
    

@product_ns.route('/hiluca/brand/product/complete')
@v2_api.expect(secureHeader)
class HilucaResourceProductComplete(ProxySecureResource): 
 
    @product_ns.doc('Save a Complete Product')
    @v2_api.expect(SaveProductCompleteStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/product/complete',payload,True)
        return  response, 200
    

@product_ns.route('/hiluca/brand/product/image')
@v2_api.expect(secureHeader)
class HilucaResourceSaveImageIDProduct(ProxySecureResource): 
 
    @product_ns.doc('Upload Product Image By Id')
    @v2_api.expect(UploadProductImageIDStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)  
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"
        payload['MAX_IMAGES'] = PRODUCT_MAX_IMAGES
        payload['API_URL'] = API_URL
        response = n8nClient.executePost('/webhook/v2/product/image_id',payload,True)
        return  response, 200


@product_ns.route('/hiluca/brand/<brand_id>/product/<product_id>/image/<thumbnail_id>')
@v2_api.expect(secureHeader)
class HilucaResourceImageProductDelete(ProxySecureResource): 

    @product_ns.doc('Delete Product Image')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PRODUCT, ACTION_UPDATE)
    def delete(self,brand_id,product_id,thumbnail_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = DeleteProductImageUseCase(user_id).execute(brand_id, product_id, thumbnail_id)
        return {'ok': 1, 'data': data}, 200