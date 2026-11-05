import pymupdf
import json
from io import BytesIO
from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from werkzeug.utils import secure_filename
from pathlib import Path
from app.tools.permissions import check_access
from app.v1.models.constant import FUNCTION_BRAND, ACTION_UPDATE, ACTION_CREATE, ACTION_READ, ACTION_DELETE, ROLE_HILUCA_ADMIN
from app.v1.repository.base import N8NClient
from app.v2.use_cases.brand import CreateBrandManualUseCase, GetABrandUseCase, SaveBrandUseCase, GetBrandsUseCase, \
    UploadBrandFontFileUseCase, CreateBrandAIUseCase, GetSourceFilesUseCase, RemoveDataSourceUseCase, EditBrandUseCase

brand_ns = v2_api.namespace('application', description='Aplication Services')

CreateNewBrandManualStruct = v2_api.model('CreateNewBrandManualStruct', { 
    'name': fields.String(),
    'website_url': fields.String(),
    'language': fields.String()
})

SaveNewBrandStruct = v2_api.model('SaveNewBrandStruct', { 
    'identity': fields.Raw(),
    'logos': fields.List(fields.Raw()),
    'colors': fields.List(fields.Raw()),
    'typography': fields.List(fields.Raw()),
    'dos_donts': fields.List(fields.Raw())
})

ResearchOnlineNewBrandStruct = v2_api.model('ResearchOnlineNewBrandStruct', { 
    'brand_id': fields.Integer(),
    'attribute': fields.String()
})

UploadNewBrandLogoImageIDStruct = v2_api.model('UploadNewBrandLogoImageIDStruct', { 
    'brand_id': fields.Integer(),
    'logo_id': fields.Integer(),
    'image_id': fields.String()
})

UploadNewBrandDoDontImageIDStruct = v2_api.model('UploadNewBrandDoDontImageIDStruct', { 
    'brand_id': fields.Integer(),
    'do_dont_id': fields.Integer(),
    'image_id': fields.String()
})

DataSourceRemoveNewBrandStruct = v2_api.model('DataSourceRemoveNewBrandStruct', { 
    'brand_id': fields.Integer(),
    'data_source_id': fields.Integer(),
    'data_source_name': fields.String()
})

@brand_ns.route('/hiluca/new_brand/ai')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandCreateAI(ProxySecureResource): 

    @brand_ns.doc('Create Brand By AI')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        user_id = security_credentials['username']

        brand_use_case = CreateBrandAIUseCase(user_id)
        bucket_conf = brand_use_case.get_docs_bucket_config()

        files_dict = {}

        if 'files' in request.files:
            files = request.files.getlist('files')
            if files:
                for i, file in enumerate(files):
                    filename = secure_filename(file.filename)
                    content_type = file.content_type
                    file_bytes = None
                    if content_type == 'application/pdf':
                        file_bytes = BytesIO(file.read())
                        file_bytes.seek(0)
                    else:
                        try:
                            filename = Path(filename).stem + '.pdf'
                            image_bytes = BytesIO(file.read())
                            img = pymupdf.open(filename, image_bytes)
                            pdf_bytes = img.convert_to_pdf()
                            img.close()
                            file_bytes = BytesIO(pdf_bytes)
                            content_type = 'application/pdf'
                            file_bytes.seek(0)
                        except Exception as e:
                            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': f'Error processing file {file.filename}: {str(e)}'} }, 400
                    
                    files_dict.update({f'file{i}' : (filename, file_bytes.read() , content_type)})

        name = request.form.get('name') if request.form else None
        if not name:
            return {'ok': 0, 'message': {'code': 'EVAL001', 'text': 'The name field is required.'} }, 400
        
        website_url = request.form.get('website_url') if request.form else None
        if not website_url:
            return {'ok': 0, 'message': {'code': 'EVAL002', 'text': 'The website_url field is required.'} }, 400

        language = request.form.get('language') if request.form else None
        if not language:
            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': 'The language field is required.'} }, 400

        # Validar que el valor de language sea uno de los permitidos ['English', 'Spanish']
        if language.lower() not in ['english', 'spanish']:
            return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The language field must be either English or Spanish.'} }, 400

        urls = request.form.get('urls') if request.form else None
        if urls and not isinstance(urls, list):
            try:
                urls = json.loads(urls)
                if not isinstance(urls, list):
                    return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a JSON array.'} }, 400
            except json.JSONDecodeError as e:
                print(f"Error parsing urls: {str(e)}")
                return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a valid JSON array.'} }, 400

        params = {'name': name, 'urls': urls, 'website_url': website_url, 'language': language.capitalize(),
                  'bucket_name': bucket_conf.get('bucket_name'), 'region': bucket_conf.get('region')}

        response = n8nClient.executePost('/webhook/v2/new_brand/ai',{},True,is_binary=False,params=params,files=files_dict)

        # if response.get('ok') == 1:
        #     data = response.get('data')
        #     if data:
        #         creation_doc = data.get('creation_doc_id')
        #         doc_url = None
        #         if creation_doc:
        #             doc_url = brand_use_case.get_doc_presigned_url('get_object', creation_doc)

        #         data.update({'creation_doc_url': doc_url})
        #         del data['creation_doc_id']

        return  response, 200


@brand_ns.route('/hiluca/new_brand/manual')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandCreateManual(ProxySecureResource): 
 
    @brand_ns.doc('Create Brand Manual')
    @v2_api.expect(CreateNewBrandManualStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        payload = request.json 
        data = CreateBrandManualUseCase(user_id).execute(payload)
        return {'ok' : 1, 'data': data }, 200


@brand_ns.route('/hiluca/new_brand/<brand_id>')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandGetOne(ProxySecureResource): 
 
    @brand_ns.doc('Get a Brand By Id')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        data = GetABrandUseCase(user_id).execute(brand_id)
        return {'ok' : 1, 'data': data }, 200


    @brand_ns.doc('Save Brand')
    @v2_api.expect(SaveNewBrandStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def put(self,brand_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        payload = request.json 
        data = SaveBrandUseCase(user_id).execute(brand_id, payload)
        return {'ok' : 1, 'data': data }, 200

    
    @brand_ns.doc('Delete a Brand')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_DELETE)
    def delete(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id }
        response = n8nClient.executePut('/webhook/v2/new_brand/delete',payload,True)
        return  response, 200


@brand_ns.route('/hiluca/new_brand')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandGet(ProxySecureResource):

    @brand_ns.doc('Get a Brand List from a Account')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        payload = {}

        limit = 10
        offset = 0
        filter_key = None
        filter_value = None
        order_key = None
        order_value = None

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

        data = GetBrandsUseCase(user_id).execute(payload)
        return {'ok' : 1, 'count': data['count'], 'total': data['total'], 'data': data['data'] }, 200


@brand_ns.route('/hiluca/new_brand/research_online')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandResearchOnline(ProxySecureResource): 
    @brand_ns.doc('Research Online')
    @v2_api.expect(ResearchOnlineNewBrandStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/new_brand/research_online',payload,True)
        return  response, 200
    

@brand_ns.route('/hiluca/new_brand/generate_ai')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandGenerateWithAI(ProxySecureResource): 
    @brand_ns.doc('Generate with AI')
    @v2_api.expect(ResearchOnlineNewBrandStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/new_brand/generate_ai',payload,True)
        return  response, 200


@brand_ns.route('/hiluca/new_brand/<brand_id>/logo/<logo_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandSaveLogoImage(ProxySecureResource): 
 
    @brand_ns.doc('Upload Brand Logo Image (Binary) ')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self,brand_id,logo_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'item_id' : logo_id }
         
        files = { 
            'file' : (filename, buffer_image, content_type)#,
        }

        response = n8nClient.executePost('/webhook/v2/new_brand/image',{},True,is_binary=False,params=params,files=files)
        return response, 200
        

@brand_ns.route('/hiluca/new_brand/logo/image')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandSaveLogoImageID(ProxySecureResource): 
 
    @brand_ns.doc('Upload Brand Logo Image By Id')
    @v2_api.expect(UploadNewBrandLogoImageIDStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/new_brand/image_id',payload,True)
        return  response, 200 


@brand_ns.route('/hiluca/new_brand/<brand_id>/do_dont/<do_dont_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandSaveDoDontImage(ProxySecureResource): 
 
    @brand_ns.doc('Upload Brand Dos and Donts Image (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self,brand_id,do_dont_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'item_id' : do_dont_id }
         
        files = { 
            'file' : (filename, buffer_image, content_type)#,
        }

        response = n8nClient.executePost('/webhook/v2/new_brand/image',{},True,is_binary=False,params=params,files=files)
        return response, 200
        

@brand_ns.route('/hiluca/new_brand/do_dont/image')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandSaveDoDontImageID(ProxySecureResource): 
 
    @brand_ns.doc('Upload Brand Dos and Donts Image By Id')
    @v2_api.expect(UploadNewBrandDoDontImageIDStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/new_brand/image_id',payload,True)
        return  response, 200 


@brand_ns.route('/hiluca/new_brand/<brand_id>/font/<font_id>/file')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandSaveFontFile(ProxySecureResource): 
 
    @brand_ns.doc('Upload Brand Font (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self,brand_id,font_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        file = request.files['file']
        data = UploadBrandFontFileUseCase(user_id).execute(brand_id, font_id, file)
        return {'ok' : 1, 'data': data }, 200
    

@brand_ns.route('/hiluca/new_brand/data_source/<brand_id>')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandDataSources(ProxySecureResource): 
 
    @brand_ns.doc('Get a List of Data Sources By Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        data = GetSourceFilesUseCase(user_id).execute(brand_id)
        return {'ok' : 1, 'data': data }, 200
    

    @brand_ns.doc('Add Data Sources By Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        user_id = security_credentials['username']

        brand_use_case = CreateBrandAIUseCase(user_id)
        bucket_conf = brand_use_case.get_docs_bucket_config()

        files_dict = {}

        if 'files' in request.files:
            files = request.files.getlist('files')
            if files:
                for i, file in enumerate(files):
                    filename = secure_filename(file.filename)
                    content_type = file.content_type
                    file_bytes = None
                    if content_type == 'application/pdf':
                        file_bytes = BytesIO(file.read())
                        file_bytes.seek(0)
                    else:
                        try:
                            filename = Path(filename).stem + '.pdf'
                            image_bytes = BytesIO(file.read())
                            img = pymupdf.open(filename, image_bytes)
                            pdf_bytes = img.convert_to_pdf()
                            img.close()
                            file_bytes = BytesIO(pdf_bytes)
                            content_type = 'application/pdf'
                            file_bytes.seek(0)
                        except Exception as e:
                            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': f'Error processing file {file.filename}: {str(e)}'} }, 400
                    
                    files_dict.update({f'file{i}' : (filename, file_bytes.read() , content_type)})

        urls = request.form.get('urls') if request.form else None
        if urls and not isinstance(urls, list):
            try:
                urls = json.loads(urls)
                if not isinstance(urls, list):
                    return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a JSON array.'} }, 400
            except json.JSONDecodeError as e:
                print(f"Error parsing urls: {str(e)}")
                return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a valid JSON array.'} }, 400
            
        if not files_dict and not urls:
            return {'ok': 0, 'message': {'code': 'EVAL005', 'text': 'At least one file or url is required.'} }, 400
        
        section = request.form.get('section') if request.form else None
        valid_sections = ['all', 'logos', 'colors', 'typography', 'dos_donts']
        if not section or section not in valid_sections:
            return {'ok': 0, 'message': {'code': 'EVAL007', 'text': f'The section field is required and must be one of the following values: {", ".join(valid_sections)}.'} }, 400

        params = {'brand_id': brand_id, 'urls': urls, 'bucket_name': bucket_conf.get('bucket_name'), 'region': bucket_conf.get('region'), 'section': section}

        response = n8nClient.executePost('/webhook/v2/new_brand/data_source/add',{},True,is_binary=False,params=params,files=files_dict)

        # if response.get('ok') == 1:
        #     data = response.get('data')
        #     if data:
        #         creation_doc = data.get('creation_doc_id')
        #         doc_url = None
        #         if creation_doc:
        #             doc_url = brand_use_case.get_doc_presigned_url('get_object', creation_doc)

        #         data.update({'creation_doc_url': doc_url})
        #         del data['creation_doc_id']

        return  response, 200


@brand_ns.route('/hiluca/new_brand/data_source/remove')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandDataSourceRemove(ProxySecureResource): 
    @brand_ns.doc('Remove Data Source By Brand')
    @v2_api.expect(DataSourceRemoveNewBrandStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self):    
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        payload = request.json 
        data = RemoveDataSourceUseCase(user_id).execute(payload)
        return {'ok' : 1, 'data': data }, 200
    

@brand_ns.route('/hiluca/new_brand/edit/<brand_id>')
@v2_api.expect(secureHeader)
class HilucaResourceNewBrandEdit(ProxySecureResource): 
    @brand_ns.doc('Edit Brand')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def put(self,brand_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']

        files_payload = []

        if 'files' in request.files:
            files = request.files.getlist('files')
            if files:
                for i, file in enumerate(files):
                    filename = secure_filename(file.filename)
                    content_type = file.content_type
                    file_bytes = None
                    if content_type == 'application/pdf':
                        file_bytes = BytesIO(file.read())
                        file_bytes.seek(0)
                    else:
                        try:
                            filename = Path(filename).stem + '.pdf'
                            image_bytes = BytesIO(file.read())
                            img = pymupdf.open(filename, image_bytes)
                            pdf_bytes = img.convert_to_pdf()
                            img.close()
                            file_bytes = BytesIO(pdf_bytes)
                            content_type = 'application/pdf'
                            file_bytes.seek(0)
                        except Exception as e:
                            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': f'Error processing file {file.filename}: {str(e)}'} }, 400

                    files_payload.append({'filename': filename, 'content_type': content_type, 'content': file_bytes.read()})

        name = request.form.get('name') if request.form else None
        if not name:
            return {'ok': 0, 'message': {'code': 'EVAL001', 'text': 'The name field is required.'} }, 400
        
        website_url = request.form.get('website_url') if request.form else None
        if not website_url:
            return {'ok': 0, 'message': {'code': 'EVAL002', 'text': 'The website_url field is required.'} }, 400

        language = request.form.get('language') if request.form else None
        if not language:
            return {'ok': 0, 'message': {'code': 'EVAL003', 'text': 'The language field is required.'} }, 400

        # Validar que el valor de language sea uno de los permitidos ['English', 'Spanish']
        if language.lower() not in ['english', 'spanish']:
            return {'ok': 0, 'message': {'code': 'EVAL007', 'text': 'The language field must be either English or Spanish.'} }, 400

        urls = request.form.get('urls') if request.form else None
        if urls and not isinstance(urls, list):
            try:
                urls = json.loads(urls)
                if not isinstance(urls, list):
                    return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a JSON array.'} }, 400
            except json.JSONDecodeError as e:
                print(f"Error parsing urls: {str(e)}")
                return {'ok': 0, 'message': {'code': 'EVAL004', 'text': 'The urls field must be a valid JSON array.'} }, 400
            
        # Extraer atributo analyze (Boolean) del request.form, si no viene, asignar False
        analyze = request.form.get('analyze', 'false').lower() == 'true'

        # Extraer atributo delete_data_sources (JSON ejemplo: {"data_source_id": 22,"data_source_name": "pagina_3.pdf"}) del request.form, si no viene, asignar None
        delete_data_sources = request.form.get('delete_data_sources')
        if delete_data_sources:
            try:
                delete_data_sources = json.loads(delete_data_sources)
            except json.JSONDecodeError as e:
                print(f"Error parsing delete_data_sources: {str(e)}")
                return {'ok': 0, 'message': {'code': 'EVAL006', 'text': 'The delete_data_sources field must be a valid JSON.'} }, 400
        else:
            delete_data_sources = None


        payload = {'name': name, 'urls': urls, 'website_url': website_url, 
                   'files': files_payload, 'analyze': analyze, 
                   'delete_data_sources': delete_data_sources, 'language': language.capitalize()}

        data = EditBrandUseCase(user_id).execute(brand_id, payload)
        return {'ok' : 1, 'data': data }, 200