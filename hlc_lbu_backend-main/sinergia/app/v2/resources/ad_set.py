from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from app.tools.permissions import check_access
from app.v1.models.constant import FUNCTION_FUNNEL_FLOW, ACTION_UPDATE, ROLE_HILUCA_ADMIN
from app.v2.use_cases.ad_set import SetMediaPlatformProjectUseCase, GenerateAdVariationsUseCase, GetJobResultGenerateAdVariationsUseCase, GetAdSetUseCase

ad_set_ns = v2_api.namespace('application', description='Aplication Services')

SetMediaPlatformProjectAdSetStruct = v2_api.model('SetMediaPlatformProjectAdSetStruct', {
    'brand_id': fields.Integer(required=True),
    'campaign_id': fields.Integer(required=True),
    'ad_set_id': fields.Integer(required=True),
    'media_platform_project_id': fields.Integer(required=False)
})

GenerateAdVariationsAdSetStruct = v2_api.model('GenerateAdVariationsAdSetStruct', {
    'brand_id': fields.Integer(required=True),
    'campaign_id': fields.Integer(required=True),
    'ad_set_id': fields.Integer(required=True),
    'n_variants': fields.Integer(required=True)
})

@ad_set_ns.route('/hiluca/brand/ad_set/media_platform/project')
@v2_api.expect(secureHeader)
class HilucaResourceAdSetMediaPlatformProjectSet(ProxySecureResource):
    
    @ad_set_ns.doc('Set Media Platform Project By Ad Set')
    @v2_api.expect(SetMediaPlatformProjectAdSetStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = SetMediaPlatformProjectUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_set_ns.route('/hiluca/brand/ad_set/variants')
@v2_api.expect(secureHeader)
class HilucaResourceAdSetVariants(ProxySecureResource):
    
    @ad_set_ns.doc('Generate Ad Variations By Ad Set')
    @v2_api.expect(GenerateAdVariationsAdSetStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = GenerateAdVariationsUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_set_ns.route('/hiluca/brand/ad_set/variants/job/<job_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdSetVariantsJobResult(ProxySecureResource):
    
    @ad_set_ns.doc('Get Job Resul - Generate Ad Variations By Ad Set')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def get(self, job_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetJobResultGenerateAdVariationsUseCase(user_id).execute(job_id)
        return {'ok': 1, 'data': data}, 200
