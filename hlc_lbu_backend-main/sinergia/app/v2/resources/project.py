import json
import os
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import fields
from flask.globals import request
from config import config
from app.tools.permissions import check_access
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from app.v1.models.constant import FUNCTION_PROJECT, ACTION_CREATE, ACTION_READ, ACTION_UPDATE, ROLE_HILUCA_ADMIN
from app.v2 import v2_api

project_ns = v2_api.namespace('application', description='Aplication Services')

config_type = os.environ.get('CONFIG_TYPE', 'dev')


DefineProjectStruct = v2_api.model('DefineProjectStruct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'language': fields.String(),
    'description': fields.String(),
    'target_regions': fields.String()
})

UpdateProjectStatusStruct = v2_api.model('UpdateProjectStatusStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'status': fields.String()
})

ProjectRefinationStruct = v2_api.model('ProjectRefinationStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer()
})

UpdateProjectStruct = v2_api.model('UpdateProjectStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'name': fields.String(),
    'language': fields.String(),
    'description': fields.String(),
    'target_regions': fields.String()
})

SetProductProjectStruct = v2_api.model('SetProductProjectStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'product_id': fields.Integer()
})

SetBuyerPersonProjectStruct = v2_api.model('SetBuyerPersonProjectStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'bperson_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

SaveSummaryProjectStruct = v2_api.model('SaveSummaryProjectStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'summary_generated': fields.Raw(),
    'summary_saved': fields.Raw()
})


@project_ns.route('/hiluca/brand/project')
@v2_api.expect(secureHeader)
class HilucaResourceDefineProject(ProxySecureResource): 
 
    @project_ns.doc('Define a Project')
    @v2_api.expect(DefineProjectStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project',payload,True)
        return  response, 200

    @project_ns.doc('Update a Project')
    @v2_api.expect(UpdateProjectStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/project',payload,True)
        return  response, 200


@project_ns.route('/hiluca/brand/project/set_product')
@v2_api.expect(secureHeader)
class HilucaResourceSetProductProject(ProxySecureResource): 
 
    @project_ns.doc('Setting Product By Project')
    @v2_api.expect(SetProductProjectStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/set_product',payload,True)
        return  response, 200


@project_ns.route('/hiluca/brand/project/set_buyer_person')
@v2_api.expect(secureHeader)
class HilucaResourceSetBuyerPersonProject(ProxySecureResource): 
 
    @project_ns.doc('Setting Buyer Person By Project')
    @v2_api.expect(SetBuyerPersonProjectStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/set_buyer_person',payload,True)
        return  response, 200
    

@project_ns.route('/hiluca/brand/project/summary')
@v2_api.expect(secureHeader)
class HilucaResourceSaveSummaryProject(ProxySecureResource): 
 
    @project_ns.doc('Save Project Summary')
    @v2_api.expect(SaveSummaryProjectStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/summary',payload,True)
        return  response, 200


@project_ns.route('/hiluca/brand/<brand_id>/project')
@v2_api.expect(secureHeader)
class HilucaResourceGetProjects(ProxySecureResource): 
 
    @project_ns.doc('Get a Project List From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        limit = 10
        offset = 0
        filter_key = None
        filter_value = None
        order_key = None
        order_value = None

        payload = {'brand_id' : brand_id }

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

        response = n8nClient.executeGet('/webhook/v2/projects',payload,True)
        return  response, 200
        

@project_ns.route('/hiluca/brand/<brand_id>/project/<project_id>')
@v2_api.expect(secureHeader)
class HilucaResourceGetBuyerPerson(ProxySecureResource): 
 
    @project_ns.doc('Get a Project From a Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_READ)
    def get(self,brand_id,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'API_URL': API_URL }
        response = n8nClient.executeGet('/webhook/v2/project',payload,True)
        return  response, 200