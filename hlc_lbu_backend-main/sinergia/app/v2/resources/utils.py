from io import BytesIO
from flask import send_file
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from app.exceptions.base import ParametersNotFoundException
from app.tools.permissions import check_access
from app.v2.use_cases.utils import GetBinaryObject
from app.v1.models.constant import FUNCTION_TARGET_CUSTOMER, ACTION_READ, ROLE_HILUCA_ADMIN
from app.v2.use_cases.utils import GetJobResultUseCase

utils_ns = v2_api.namespace('application', description='Aplication Services')

GenerateImagePromptStruct = v2_api.model('GenerateImagePromptStruct', { 
    'prompt': fields.String()
})

@utils_ns.route('/hiluca/convert/voice/to/text')
@v2_api.expect(secureHeader)
class HilucaResourceConvertVoiceToText(ProxySecureResource): 
 
    @utils_ns.doc('Convert Voice to Text ')
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_voice = BytesIO(file.read())
        buffer_voice.seek(0)
         
        files = { 
            'file' : (filename, buffer_voice.read() , content_type) 
        }

        language = request.form['language']
        params = { 'language' : language }

        response = n8nClient.executePost('/webhook/v2/convert/voice/to/text',{},True,is_binary=False,params=params,files=files)

        return response, 200     


########################################################################################################################


@utils_ns.route('/hiluca/image/generate')
@v2_api.expect(secureHeader)
class HilucaResourceGenerateImageFromPrompt(ProxySecureResource): 
 
    @utils_ns.doc('Generate Image using a Prompt')
    @v2_api.expect(GenerateImagePromptStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/image/generate',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])


########################################################################################################################

@utils_ns.route('/hiluca/funnel')
@v2_api.expect(secureHeader)
class HilucaResourceFunnelGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Funnel List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/funnel',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/channel_group')
@v2_api.expect(secureHeader)
class HilucaResourceChannelGroupGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Channel Group List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/channel_group',payload,True)
        return  response, 200
    

########################################################################################################################


@utils_ns.route('/hiluca/channel_group/<channel_group_id>/channels')
@v2_api.expect(secureHeader)
class HilucaResourceChannelGroupChannelsGet(ProxySecureResource): 
 
    @utils_ns.doc('Get Channels by Channel Group')
    @jwt_required    
    def get(self,channel_group_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'channel_group_id' : channel_group_id }
        response = n8nClient.executeGet('/webhook/v2/channel_group/channels',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/metric')
@v2_api.expect(secureHeader)
class HilucaResourceMetricGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Metric List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}

        filter = request.args.to_dict(flat=True)
        if 'group' in filter:
            payload.update({'group': filter['group']})

        response = n8nClient.executeGet('/webhook/v2/metric',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/image_style')
@v2_api.expect(secureHeader)
class HilucaResourceImageStyleGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Image Style List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}

        filter = request.args.to_dict(flat=True)
        if 'target' in filter:
            payload.update({'target': filter['target']})

        response = n8nClient.executeGet('/webhook/v2/image_style',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/umbrella_resource')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaResourceGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Umbrella Campaign Resource List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/umbrella_resource',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/umbrella_motive_barrier')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaMotiveBarrierGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Umbrella Campaign Motive and Barrier List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/umbrella_motive_barrier',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/umbrella_stage_category')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaStageCategoryGet(ProxySecureResource): 
 
    @utils_ns.doc('Get a Umbrella Campaign Stage Category List')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/umbrella_stage_category',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/income_level')
@v2_api.expect(secureHeader)
class HilucaResourceIncomeLevelGet(ProxySecureResource): 
 
    @utils_ns.doc('Get Income Levels')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        response = n8nClient.executeGet('/webhook/v2/income_level',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/image_library')
@v2_api.expect(secureHeader)
class HilucaResourceIncomeLevelGet(ProxySecureResource): 
 
    @utils_ns.doc('Get Image Library')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {}
        limit = 10
        start = 0

        if 'filter' in  request.args and request.args['filter']:
            filter = eval(request.args['filter'])
            request_payload = filter
            payload = request_payload

        if 'brand' in request.args and request.args['brand'] and str.isdigit(request.args['brand']):
            request_brand = eval(request.args['brand'])
            brand = request_brand
            payload.update({'brand': brand})
        else:
            raise ParametersNotFoundException('The brand ID is missing or invalid.')

        if 'lastKey' in  request.args and request.args['lastKey']:
            lastKey = str(request.args['lastKey'])
            request_payload = lastKey
            payload.update({'lastKey': request_payload})

        if 'limit' in  request.args and request.args['limit'] and str.isdigit(request.args['limit']):
            request_limit = eval(request.args['limit'])
            limit = request_limit if request_limit <= 50 else limit

        if 'start' in  request.args and request.args['start'] and str.isdigit(request.args['start']):
            request_start = eval(request.args['start'])
            start = max(request_start, start)

        payload.update({'limit': limit, 'start': start})

        response = n8nClient.executeGet('/webhook/v2/image_library',payload,True)
        return  response, 200


########################################################################################################################


@utils_ns.route('/hiluca/binary_object')
@v2_api.expect(secureHeader)
class HilucaResourceBinaryObjectGet(ProxySecureResource):

    @utils_ns.doc('Get Binary From Presigned URL')
    @jwt_required    
    # @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        presigned_url = None

        if 'presigned_url' in request.args and request.args['presigned_url']:
            presigned_url = request.args.get('presigned_url')

        response = GetBinaryObject(user_id).execute(presigned_url)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)
        return send_file(buffer_image, mimetype=response['content_type'])


########################################################################################################################


@utils_ns.route('/hiluca/job/<job_id>')
@v2_api.expect(secureHeader)
class HilucaResourceBuyerPersonJobResult(ProxySecureResource):
    
    @utils_ns.doc('Get Job Result - Agent Flow')
    @jwt_required
    #@check_access([ROLE_HILUCA_ADMIN], FUNCTION_TARGET_CUSTOMER, ACTION_READ)
    def get(self, job_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetJobResultUseCase(user_id).execute(job_id)
        return {'ok': 1, 'data': data}, 200