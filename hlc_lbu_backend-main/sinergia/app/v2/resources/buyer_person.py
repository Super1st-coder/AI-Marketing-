import json
import os
from io import BytesIO
from flask_restplus import fields
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from werkzeug.utils import secure_filename
from app.tools.permissions import check_access
from app.v1.models.constant import FUNCTION_TARGET_CUSTOMER, ACTION_CREATE, ACTION_UPDATE, ACTION_READ, ROLE_HILUCA_ADMIN, ACTION_DELETE
from app.v1.repository.base import N8NClient
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v2 import v2_api
from app.v2.use_cases.buyer_person import GenerateMainImagesAutomaticUseCase, GetMainImagesUseCase, EditMainImageUseCase, \
    DeleteMainImageUseCase, GenerateVariantImagesUseCase, GetVariantImagesUseCase, DeleteVariantImageUseCase, SelectVariantImageUseCase, \
    BuyerParsonBaseUseCase, UploadVariantImageByIdUseCase, UploadVariantImageBinarydUseCase, GetAVariantImageUseCase
from app.v2.use_cases.ad_set import GetJobResultGenerateAdVariationsUseCase
from app.v2.models.constant import ALLOWED_PHOTOGRAPHY_EFFECTS, BUYER_IMAGE_VARIANT_LABELS, ALLOWED_VISUAL_STYLES
from config import config

buyer_person_ns = v2_api.namespace('application', description='Aplication Services')

config_type = os.environ.get('CONFIG_TYPE', 'dev')

DefineBuyerPersonStruct = v2_api.model('DefineBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'description_01': fields.String(),
    'description_02': fields.String(),
    'description_03': fields.String(),
    'language': fields.String()
})

UpdateBuyerPersonStruct = v2_api.model('UpdateBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'name': fields.String(),
    'description_01': fields.String(),
    'description_02': fields.String(),
    'description_03': fields.String(),
    'language': fields.String()
})

SetProductBuyerPersonStruct = v2_api.model('SetProductBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'product_id': fields.Integer()
})

GenerateBuyerPersonAttributesStruct = v2_api.model('GenerateBuyerPersonAttributesStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

GenerateBuyerPersonAttributesCategoryStruct = v2_api.model('GenerateBuyerPersonAttributesCategoryStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'category': fields.String(),
    'ask': fields.String(),
    'answer': fields.String()
})

SaveBuyerPersonAttributesStruct = v2_api.model('SaveBuyerPersonAttributesStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'mandatory_attributes_generated': fields.Raw(),
    'mandatory_attributes_saved': fields.Raw(),
    'trigger_prompts': fields.Boolean()
})

GenerateBuyerPersonImageAttributesStruct = v2_api.model('GenerateBuyerPersonImageAttributesStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

SaveBuyerPersonImageAttributesStruct = v2_api.model('SaveBuyerPersonImageAttributesStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

GenerateImagePromptsBuyerPersonStruct = v2_api.model('GenerateImagePromptsBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer()
})

SetPreferredImagePromptsBuyerPersonStruct = v2_api.model('SetPreferredImagePromptsBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'image_prompt_id': fields.Integer()
})

SavePreferredImagePromptsBuyerPersonStruct = v2_api.model('SavePreferredImagePromptsBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'preferred_image_prompt': fields.Raw()
})

SaveBuyerPersonCompleteStruct = v2_api.model('SaveBuyerPersonCompleteStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'bperson_story': fields.String(),
    'name_and_nickname': fields.String()
})

UploadBuyerPersonImageIDStruct = v2_api.model('UploadBuyerPersonImageIDStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'image_id': fields.String()
})

GenerateMainImageAutomaticBuyerPersonStruct = v2_api.model('GenerateMainImageAutomaticBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'product_id': fields.Integer()
})

GenerateVariantsImageBuyerPersonStruct = v2_api.model('GenerateVariantsImageBuyerPersonStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'image_id': fields.String()
})

UploadBuyerPersonVariantImageIDStruct = v2_api.model('UploadBuyerPersonVariantImageIDStruct', { 
    'brand_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'image_id': fields.String(),
    'label': fields.String()
})


@buyer_person_ns.route('/hiluca/brand/buyer_person')
@v2_api.expect(secureHeader)
class HilucaResourceDefineBuyerPerson(ProxySecureResource): 
 
    @buyer_person_ns.doc('Define a Buyer Person')
    @v2_api.expect(DefineBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person',payload,True)
        return  response, 200


    @buyer_person_ns.doc('Update a Buyer Person')
    @v2_api.expect(UpdateBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/buyer_person',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/set_product')
@v2_api.expect(secureHeader)
class HilucaResourceDefineBuyerPerson(ProxySecureResource): 
 
    @buyer_person_ns.doc('Set a Product to Buyer Person')
    @v2_api.expect(SetProductBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/set_product',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/document')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonDocumets(ProxySecureResource): 

    @buyer_person_ns.doc('Upload Buyer Person Documents')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self,brand_id,bperson_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        bucket_region = BuyerParsonBaseUseCase().get_docs_bucket_config()['region']

        files = request.files.to_dict(flat=False)

        files_dict = {}
        for i, value in enumerate(files['files']):
            content_type = value.content_type
            filename = value.filename

            buffer_image = BytesIO(value.read())
            buffer_image.seek(0)
            files_dict.update({f'file{i}' : (filename, buffer_image.read() , content_type)})

        params = { 'brand_id' : brand_id, 'bperson_id' : bperson_id, 'bucket_region': bucket_region }

        response = n8nClient.executePost('/webhook/v2/buyer_person/document',{},True,is_binary=False,params=params,files=files_dict)

        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonAttributesGenerate(ProxySecureResource): 
 
    @buyer_person_ns.doc('Generate Buyer Person Attributes')
    @v2_api.expect(GenerateBuyerPersonAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/attributes/generate',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/category/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonAttributesCategory(ProxySecureResource): 
 
    @buyer_person_ns.doc('Generate Buyer Person Attributes By Category')
    @v2_api.expect(GenerateBuyerPersonAttributesCategoryStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/category/attributes',payload,True)
        return  response, 200
    

@buyer_person_ns.route('/hiluca/brand/buyer_person/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonAttributes(ProxySecureResource): 
 
    @buyer_person_ns.doc('Save Buyer Person Attributes')
    @v2_api.expect(SaveBuyerPersonAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/attributes',payload,True)
        return  response, 200
        

@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>')
@v2_api.expect(secureHeader)
class HilucaResourceGetBuyerPerson(ProxySecureResource): 
 
    @buyer_person_ns.doc('Get a Buyer Person From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self,bperson_id,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'bperson_id' : bperson_id, 'brand_id' : brand_id }
        response = n8nClient.executeGet('/webhook/v2/buyer_person',payload,True)
        return  response, 200
        

@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person')
@v2_api.expect(secureHeader)
class HilucaResourceGetBuyerPersons(ProxySecureResource): 
 
    @buyer_person_ns.doc('Get a Buyer Person List From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
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

        payload.update({
            'limit': limit,
            'offset': offset,
            'filterKey': filter_key,
            'filterValue': filter_value,
            'orderKey': order_key,
            'orderValue': order_value
        })

        response = n8nClient.executeGet('/webhook/v2/buyer_persons',payload,True)
        return  response, 200
        

@buyer_person_ns.route('/hiluca/brand/buyer_person/image/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageAttributesGenerate(ProxySecureResource): 
 
    @buyer_person_ns.doc('Generate Buyer Person Image Attributes')
    @v2_api.expect(GenerateBuyerPersonImageAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image/attributes/generate',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageAttributesSave(ProxySecureResource): 
 
    @buyer_person_ns.doc('Save Buyer Person Image Attributes')
    @v2_api.expect(SaveBuyerPersonImageAttributesStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image/attributes',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/prompts/generate')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImagePromptsAttributesGenerate(ProxySecureResource): 
 
    @buyer_person_ns.doc('Generate Image Prompts from Buyer Person Attributes')
    @v2_api.expect(GenerateImagePromptsBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image/prompts/generate',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/prompts/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImagePromptsAttributesGenerate(ProxySecureResource): 
 
    @buyer_person_ns.doc('Setting Preferred Image Prompt from Buyer Person')
    @v2_api.expect(SetPreferredImagePromptsBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image/prompts/set_preferred',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/prompts/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImagePromptsAttributesGenerate(ProxySecureResource): 
 
    @buyer_person_ns.doc('Save Preferred Image Prompt from Buyer Person')
    @v2_api.expect(SavePreferredImagePromptsBuyerPersonStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image/prompts/preferred',payload,True)
        return  response, 200

@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/prompts')
@v2_api.expect(secureHeader)
class HilucaResourceGetBuyerPerson(ProxySecureResource): 
 
    @buyer_person_ns.doc('Get Image Prompts from Buyer Person')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self,bperson_id,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'bperson_id' : bperson_id, 'brand_id' : brand_id }
        response = n8nClient.executeGet('/webhook/v2/buyer_person/image/prompts',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImage(ProxySecureResource): 

    @buyer_person_ns.doc('Upload Buyer Person Image (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self,brand_id,bperson_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'bperson_id' : bperson_id }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/buyer_person/image',{},True,is_binary=False,params=params,files=files)

        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageID(ProxySecureResource): 
 
    @buyer_person_ns.doc('Upload Buyer Person Image By Id')
    @v2_api.expect(UploadBuyerPersonImageIDStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/image_id',payload,True)
        return  response, 200

    
    # @buyer_person_ns.doc('Get Image By Buyer Person')
    # @jwt_required    
    # def get(self,brand_id,bperson_id):
    #     security_credentials = self.checkCredentials()
    #     n8nClient = N8NClient(credentials=security_credentials)
    #     payload = { 'brand_id' : brand_id, 'bperson_id' : bperson_id }
    #     response = n8nClient.executeGet('/webhook/v2/buyer_person/image',payload,True,is_binary=True)

    #     buffer_image = BytesIO(response['content'])
    #     buffer_image.seek(0)

    #     return send_file(buffer_image, mimetype=response['content_type'])  


@buyer_person_ns.route('/hiluca/brand/buyer_person/complete')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonComplete(ProxySecureResource): 
 
    @buyer_person_ns.doc('Save a Complete Buyer Person')
    @v2_api.expect(SaveBuyerPersonCompleteStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/buyer_person/complete',payload,True)
        return  response, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/automatic/main/generate')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageMainAutomatic(ProxySecureResource):
    
    @buyer_person_ns.doc('Generate Main Images Automatic With Luca by Buyer Person')
    @v2_api.expect(GenerateMainImageAutomaticBuyerPersonStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = GenerateMainImagesAutomaticUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main')
@v2_api.expect(secureHeader)
class HilucaResourceGetBuyerPerson(ProxySecureResource): 
 
    @buyer_person_ns.doc('Get Main Images By Buyer Person')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self,brand_id,bperson_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetMainImagesUseCase(user_id).execute(brand_id, bperson_id)
        return {'ok': 1, 'data': data}, 200
    

@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main/edit')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonMainImageEdit(ProxySecureResource): 
 
    @buyer_person_ns.doc('Edit Main Image by Buyer Person (More Like This)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self,brand_id,bperson_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']

        base_image_id = request.form.get('base_image_id') if request.form else None
        if not base_image_id:
            return {'ok': 0, 'message': {'code': 'EVAL001', 'text': 'The base_image_id field is required.'} }, 400

        # Validar custom_prompt
        custom_prompt = request.form.get('custom_prompt') if request.form else None
        if not custom_prompt:
            return {'ok': 0, 'message': {'code': 'EVAL002', 'text': 'The custom_prompt field is required.'} }, 400
        
        # Validar que si existe photography_effect, este sea uno de los valores permitidos
        photography_effect = request.form.get('photography_effect') if request.form else None
        allowed_effects = ALLOWED_PHOTOGRAPHY_EFFECTS.keys()
        if photography_effect and photography_effect not in allowed_effects:
            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': f'The photography_effect field must be one of the following values: {", ".join(allowed_effects)}.'} }, 400

        visual_style = request.form.get('visual_style') if request.form else None
        allowed_visual_styles = ALLOWED_VISUAL_STYLES.keys()
        if visual_style and visual_style not in allowed_visual_styles:
            return {'ok': 0, 'message': {'code': 'EVAL008', 'text': f'The visual_style field must be one of the following values: {", ".join(allowed_visual_styles)}.'} }, 400
        
        # Validar que si existe n_variants, este sea un número entero entre 1 y 4
        n_variants = request.form.get('n_variants') if request.form else None
        if n_variants:
            try:
                n_variants = int(n_variants)
                if n_variants < 1 or n_variants > 4:
                    return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The n_variants field must be an integer between 1 and 4.'} }, 400
            except ValueError:
                return {'ok': 0, 'message': {'code': 'EVAL005', 'text': 'The n_variants field must be an integer.'} }, 400
            
        # Validar que si existe product_id, este sea un número entero positivo
        product_id = request.form.get('product_id') if request.form else None
        if product_id:
            try:
                product_id = int(product_id)
                if product_id < 1:
                    return {'ok': 0, 'message': {'code': 'EVAL006', 'text': 'The product_id field must be a valid id.'} }, 400
            except ValueError:
                return {'ok': 0, 'message': {'code': 'EVAL007', 'text': 'The product_id field must be an integer.'} }, 400

        files_payload = []
        for file in request.files.getlist('reference_images') if 'reference_images' in request.files else []:
            # file = request.files[file_key]
            content_type = file.content_type
            filename = secure_filename(file.filename)
            print(f"Processing file: {filename}, content_type: {content_type}")

            buffer_image = BytesIO(file.read())
            buffer_image.seek(0)

            files_payload.append({
                'filename': filename,
                'content': buffer_image.read(),
                'content_type': content_type
            })

        payload = {
            'brand_id': int(brand_id),
            'bperson_id': int(bperson_id),
            'base_image_id': base_image_id,
            'custom_prompt': custom_prompt,
            'photography_effect': photography_effect,
            'n_variants': n_variants,
            'product_id': product_id,
            'reference_images': files_payload,
            'visual_style': visual_style
        }

        data = EditMainImageUseCase(user_id).execute(payload)
        return {'ok' : 1, 'data': data }, 200
    

@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main/<image_id>')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonMainImageDelete(ProxySecureResource): 

    @buyer_person_ns.doc('Delete Main Image by Buyer Person')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_DELETE)
    def delete(self,brand_id,bperson_id,image_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = DeleteMainImageUseCase(user_id).execute(brand_id, bperson_id, image_id)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/variant/generate')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageVariantsGenerate(ProxySecureResource):

    @buyer_person_ns.doc('Generate Variants of Main Image by Buyer Person')
    @v2_api.expect(GenerateVariantsImageBuyerPersonStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = GenerateVariantImagesUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main/<base_image_id>/variants')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageVariantsList(ProxySecureResource):

    @buyer_person_ns.doc('List Variants of a Base Image by Buyer Person')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self, brand_id, bperson_id, base_image_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetVariantImagesUseCase(user_id).execute(brand_id, bperson_id, base_image_id)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main/<base_image_id>/variant/<variant_id>')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonVariantImageDelete(ProxySecureResource):

    @buyer_person_ns.doc('Delete a Variant of a Base Image by Buyer Person')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_DELETE)
    def delete(self, brand_id, bperson_id, base_image_id, variant_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = DeleteVariantImageUseCase(user_id).execute(brand_id, bperson_id, base_image_id, variant_id)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/variant/edit')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonVariantImageEdit(ProxySecureResource):

    @buyer_person_ns.doc('Edit a Variant of a Base Image by Buyer Person (image-to-image)')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self, brand_id, bperson_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        # base_image_id here is the VARIANT's image id, used as the edit seed.
        base_image_id = request.form.get('base_image_id') if request.form else None
        if not base_image_id:
            return {'ok': 0, 'message': {'code': 'EVAL001', 'text': 'The base_image_id field is required.'} }, 400

        custom_prompt = request.form.get('custom_prompt') if request.form else None
        if not custom_prompt:
            return {'ok': 0, 'message': {'code': 'EVAL002', 'text': 'The custom_prompt field is required.'} }, 400

        photography_effect = request.form.get('photography_effect') if request.form else None
        allowed_effects = ALLOWED_PHOTOGRAPHY_EFFECTS.keys()
        if photography_effect and photography_effect not in allowed_effects:
            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': f'The photography_effect field must be one of the following values: {", ".join(allowed_effects)}.'} }, 400

        label = request.form.get('label') if request.form else None
        allowed_labels = BUYER_IMAGE_VARIANT_LABELS.keys()
        if label and label not in allowed_labels:
            return {'ok': 0, 'message': {'code': 'EVAL008', 'text': f'The label field must be one of the following values: {", ".join(allowed_labels)}.'} }, 400

        visual_style = request.form.get('visual_style') if request.form else None
        allowed_visual_styles = ALLOWED_VISUAL_STYLES.keys()
        if visual_style and visual_style not in allowed_visual_styles:
            return {'ok': 0, 'message': {'code': 'EVAL009', 'text': f'The visual_style field must be one of the following values: {", ".join(allowed_visual_styles)}.'} }, 400

        n_variants = request.form.get('n_variants') if request.form else None
        if n_variants:
            try:
                n_variants = int(n_variants)
                if n_variants < 1 or n_variants > 4:
                    return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The n_variants field must be an integer between 1 and 4.'} }, 400
            except ValueError:
                return {'ok': 0, 'message': {'code': 'EVAL005', 'text': 'The n_variants field must be an integer.'} }, 400

        product_id = request.form.get('product_id') if request.form else None
        if product_id:
            try:
                product_id = int(product_id)
                if product_id < 1:
                    return {'ok': 0, 'message': {'code': 'EVAL006', 'text': 'The product_id field must be a valid id.'} }, 400
            except ValueError:
                return {'ok': 0, 'message': {'code': 'EVAL007', 'text': 'The product_id field must be an integer.'} }, 400

        files_payload = []
        for file in request.files.getlist('reference_images') if 'reference_images' in request.files else []:
            content_type = file.content_type
            filename = secure_filename(file.filename)

            buffer_image = BytesIO(file.read())
            buffer_image.seek(0)

            files_payload.append({
                'filename': filename,
                'content': buffer_image.read(),
                'content_type': content_type
            })

        payload = {
            'brand_id': int(brand_id),
            'bperson_id': int(bperson_id),
            'base_image_id': base_image_id,
            'custom_prompt': custom_prompt,
            'photography_effect': photography_effect,
            'n_variants': n_variants,
            'product_id': product_id,
            'reference_images': files_payload,
            'label': label,
            'visual_style': visual_style
        }

        # Editing a variant is the same image-to-image edit as the main image,
        # seeded from the variant's image — reuse the proven use case.
        data = EditMainImageUseCase(user_id).execute(payload, save_as='variant')
        return {'ok' : 1, 'data': data }, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/main/<base_image_id>/variant/<variant_image_id>/select')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonVariantImageSelect(ProxySecureResource):

    @buyer_person_ns.doc('Select a Variant of a Base Image by Buyer Person')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self, brand_id, bperson_id, base_image_id, variant_image_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = SelectVariantImageUseCase(user_id).execute(brand_id, bperson_id, base_image_id, variant_image_id)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/buyer_person/image/main/<main_image_id>/variant')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonVariantImageID(ProxySecureResource): 
 
    @buyer_person_ns.doc('Upload Variant Image of Main Image By Id')
    @v2_api.expect(UploadBuyerPersonVariantImageIDStruct)        
    @jwt_required    
    def post(self,main_image_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json 
        payload['main_image_id'] = main_image_id
        data = UploadVariantImageByIdUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@buyer_person_ns.route('/hiluca/brand/<int:brand_id>/buyer_person/<int:bperson_id>/image/main/<string:main_image_id>/variant')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonVariantImage(ProxySecureResource): 

    @buyer_person_ns.doc('Upload Variant Image of Main Image (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_UPDATE)
    def post(self,brand_id,bperson_id,main_image_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']

        label = request.form.get('label')

        file = request.files['file']
        content_type = file.content_type
        filename = secure_filename(file.filename)

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        image_payload = {
            'filename': filename,
            'content': buffer_image.read(),
            'content_type': content_type
        }

        payload = {
            'brand_id' : brand_id, 
            'bperson_id' : bperson_id,
            'main_image_id' : main_image_id,
            'image': image_payload
        }

        if label:
            payload['label'] = label

        data = UploadVariantImageBinarydUseCase(user_id).execute(payload)
        return {'ok' : 1, 'data': data }, 200


@buyer_person_ns.route('/hiluca/brand/<brand_id>/buyer_person/<bperson_id>/image/variant/<image_id>')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonImageVariantsList(ProxySecureResource):

    @buyer_person_ns.doc('Get a Variant Image by Buyer Person')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self, brand_id, bperson_id, image_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetAVariantImageUseCase(user_id).execute(brand_id, bperson_id, image_id)
        return {'ok': 1, 'data': data}, 200