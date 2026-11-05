from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from flask import send_file
from io import BytesIO
from cerberus import Validator
import json
from app.exceptions.base import ParametersNotFoundException, IncorrectValidationException
from flask import Response
import os
from config import config
from app.tools.permissions import check_access
from app.v1.models.constant import FUNCTION_BRAND, FUNCTION_PRODUCT, FUNCTION_TARGET_CUSTOMER, \
    FUNCTION_PROJECT, FUNCTION_UMBRELLA_CAMPAIGN, FUNCTION_CAMPAIGN_SETUP, \
    FUNCTION_CAMPAIGN_CREATIVE, FUNCTION_FUNNEL_FLOW, FUNCTION_APPROVAL_PROCESS, FUNCTION_CAMPAIGN_LAUNCHPAD, \
    ACTION_READ, ACTION_CREATE, ACTION_UPDATE, ACTION_DELETE, ROLE_HILUCA_ADMIN
from app.v2.async_tasks.celery_tasks import generate_topics_from_desc
from app.tools.strapi import StrapiClient
from app.v2.use_cases.utils import GetBinaryObject
from app.v2.use_cases.media_platform_project import AddMediaPlatformProjectUseCase, GetMediaPlatformProjectsUseCase, \
    GetMediaPlatformTemplatesUseCase, GetMediaTemplatesUseCase

application_ns = v2_api.namespace('application', description='Aplication Services')


#############################################################################

AddMediaPlatformStruct = v2_api.model('AddMediaPlatformStruct', { 
    'brand_id': fields.Integer(),
    'project_name': fields.String(),
    'project_id': fields.String()
})

#############################################################################

DefineBrandStep0Struct = v2_api.model('DefineBrandStep0Struct', { 
    'name': fields.String(),
    'website': fields.String(),
    'language': fields.String()
})

DefineBrandStep1_4Struct = v2_api.model('DefineBrandStep1_4Struct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'website': fields.String(),
    'vision': fields.String(),
    'uniqueness': fields.String(),
    'industry': fields.String(),
    'markets': fields.String(),
    'geography': fields.String(),
    'step': fields.Integer(),
    'attributes_generated': fields.Raw(),
    'attributes_saved': fields.Raw(),
    'trigger_prompts': fields.Boolean()
})

UpdateBrandStruct = v2_api.model('UpdateBrandStruct', { 
    'brand_id': fields.Integer(),
    'attributes_saved': fields.Raw()
})


########################################################################################################################


DefineCreativeConceptStruct = v2_api.model('DefineCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'central_idea': fields.String(),
    'language': fields.String()
})

UpdateCreativeConceptStruct = v2_api.model('UpdateCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'central_idea': fields.String(),
    'language': fields.String()
})

SetMatterToAudienceCreativeConceptStruct = v2_api.model('SetMatterToAudienceCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'matter_to_audience': fields.String()
})

SetStyleCreativeConceptStruct = v2_api.model('SetStyleCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'style': fields.String()
})

SetPlatformChannelCreativeConceptStruct = v2_api.model('SetPlatformChannelCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'platforms_and_channels': fields.String(),
    'trigger_prompts': fields.Boolean()
})

SaveCreativeConceptStruct = v2_api.model('SaveCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'creative_concepts': fields.Raw()
})

SetPreferredCreativeConceptStruct = v2_api.model('SetPreferredCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'preferred_cconcept_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

SavePreferredCreativeConceptStruct = v2_api.model('SavePreferredCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'preferred_creative_concept': fields.Raw()
})

GenerateImageAttributesCreativeConceptStruct = v2_api.model('GenerateImageAttributesCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'trigger_prompts': fields.Boolean()
})

SaveImageAttributesCreativeConceptStruct = v2_api.model('SaveImageAttributesCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

SetPreferredImagePromptCreativeConceptStruct = v2_api.model('SetPreferredImagePromptCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'image_prompt_id': fields.Integer()
})

SavePreferredImagePromptCreativeConceptStruct = v2_api.model('SavePreferredImagePromptCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'preferred_image_prompt': fields.Raw()
})

AskLucaCreativeConceptStruct = v2_api.model('AskLucaCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'step': fields.Integer()
})

SaveSummaryCreativeConceptStruct = v2_api.model('SaveSummaryCreativeConceptStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'cconcept_id': fields.Integer(),
    'summary_generated': fields.Raw(),
    'summary_saved': fields.Raw()
})


########################################################################################################################

SetChannelFunnelFlowStruct = v2_api.model('SetChannelFunnelFlowStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'funnel_flow_id': fields.Integer(),
    'channels': fields.List(fields.Raw())
})

########################################################################################################################

DefineAdStructureStruct = v2_api.model('DefineAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_set_number': fields.Integer(),
    'ad_number': fields.Integer()
})

UpdateAdStructureStruct = v2_api.model('UpdateAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_structure_id': fields.Integer(),
    'ad_sets': fields.List(fields.Raw())
})

CreateAdSetAdStructureStruct = v2_api.model('CreateAdSetAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_structure_id': fields.Integer(),
    'ad_set_name': fields.String()
})

DeleteAdSetAdStructureStruct = v2_api.model('DeleteAdSetAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_structure_id': fields.Integer(),
    'ad_set_id': fields.Integer()
})

CreateAdAdStructureStruct = v2_api.model('CreateAdAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_structure_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'ad_name': fields.String()
})

DeleteAdAdStructureStruct = v2_api.model('DeleteAdAdStructureStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.Integer(),
    'ad_structure_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'ad_id': fields.Integer()
})

DefineAdStructureTemplateStruct = v2_api.model('DefineAdStructureTemplateStruct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'ad_set_number': fields.Integer(),
    'ad_number': fields.Integer()
})


########################################################################################################################

DescriptionGenerateAudienceStruct = v2_api.model('DescriptionGenerateAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'description': fields.String()
})

FormGenerateAudienceStruct = v2_api.model('FormGenerateAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'gender': fields.String(),
    'age_min': fields.Integer(),
    'age_max': fields.Integer(),
    'income_level': fields.String(),
    'interests': fields.List(fields.String()),
    'locations': fields.List(fields.Raw())
})

GenerateTopicAudienceStruct = v2_api.model('GenerateTopicAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'description': fields.String()
})

TopicsGenerateAudienceStruct = v2_api.model('TopicsGenerateAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'topics': fields.List(fields.Raw())
})

PreferredSetAudienceStruct = v2_api.model('PreferredSetAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'preferred_audience_id': fields.Integer()
})

ResetAdsAudienceStruct = v2_api.model('ResetAdsAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer()
})

PreferredSaveAudienceStruct = v2_api.model('PreferredSaveAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'preferred_audience': fields.Raw()
})

SavedAudienceStruct = v2_api.model('SavedAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'audience': fields.Raw()
})

CancelAudienceStruct = v2_api.model('CancelAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer()
})

PreferredDeleteAudienceStruct = v2_api.model('PreferredDeleteAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer()
})

UpdateAudienceStruct = v2_api.model('UpdateAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'comments': fields.String()
})

DefineAudienceTemplateStruct = v2_api.model('DefineAudienceTemplateStruct', { 
    'brand_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'gender': fields.String(),
    'age_min': fields.Integer(),
    'age_max': fields.Integer(),
    'income_level_id': fields.Integer(),
    'interests': fields.List(fields.Raw()),
    'location': fields.Raw(),
    'comments': fields.String()
})

SavedGenerateAudienceStruct = v2_api.model('SavedGenerateAudienceStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'audience': fields.Raw()
})

########################################################################################################################

DefineAdsExperimentStruct = v2_api.model('DefineAdsExperimentStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'subcategory_id': fields.Integer(),
    'type': fields.String()
})

UpdateAdsExperimentStruct = v2_api.model('UpdateAdsExperimentStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer(),
    'subcategory_id': fields.Integer(),
    'type': fields.String()
})

DeleteAdsExperimentStruct = v2_api.model('DeleteAdsExperimentStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_set_id': fields.Integer()
})

DefineAdsExperimentCategoryStruct = v2_api.model('DefineAdsExperimentCategoryStruct', { 
    'brand_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'type': fields.String()
})

DefineAdsExperimentSubcategoryStruct = v2_api.model('DefineAdsExperimentSubcategoryStruct', { 
    'brand_id': fields.Integer(),
    'category_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String()
})

########################################################################################################################

MarketingAssetElementStruct = v2_api.model('MarketingAssetElementStruct', { 
    'name': fields.String(),
    'type': fields.String(),
    'payload': fields.String(),
    'intention': fields.String()
})

SaveMarketingAssetStruct = v2_api.model('SaveMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'language': fields.String(),
    'tone': fields.String(),
    'extra_context': fields.String(),
    'generate_visual': fields.Boolean(),
    'elements': fields.List(fields.Nested(MarketingAssetElementStruct))
})

SetImageStyleMarketingAssetStruct = v2_api.model('SetImageStyleMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'image_style_id': fields.Integer()
})

GenerateImageAttributesMarketingAssetStruct = v2_api.model('GenerateImageAttributesMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'language': fields.String(),
    'tone': fields.String(),
    'extra_context': fields.String(),
    'elements': fields.List(fields.Nested(MarketingAssetElementStruct))
})

SaveImageAttributesMarketingAssetStruct = v2_api.model('SaveImageAttributesMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

GenerateImagePromptsMarketingAssetStruct = v2_api.model('GenerateImagePromptsMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'language': fields.String(),
    'tone': fields.String(),
    'extra_context': fields.String(),
    'elements': fields.List(fields.Nested(MarketingAssetElementStruct))
})

SetImagePromptMarketingAssetStruct = v2_api.model('SetImagePromptMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'image_prompt_id': fields.Integer()
})

SaveImagePromptMarketingAssetStruct = v2_api.model('SaveImagePromptMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'image_name': fields.String(),
    'preferred_image_prompt': fields.Raw()
})

GenerateTextsMarketingAssetStruct = v2_api.model('GenerateTextsMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'language': fields.String(),
    'tone': fields.String(),
    'extra_context': fields.String(),
    'elements': fields.List(fields.Nested(MarketingAssetElementStruct))
})

GenerateTextMarketingAssetStruct = v2_api.model('GenerateTextMarketingAssetStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'template_id': fields.String(),
    'language': fields.String(),
    'tone': fields.String(),
    'extra_context': fields.String(),
    'element': fields.Nested(MarketingAssetElementStruct)
})

AbyssaleHooktMarketingAssetStruct = v2_api.model('AbyssaleHooktMarketingAssetStruct', { 
    'generation_request_id': fields.String(),
    'banners': fields.List(fields.Raw()),
    'errors': fields.List(fields.Raw())
})


########################################################################################################################



@application_ns.route('/hiluca/brand/media_platform/project')
@v2_api.expect(secureHeader)
class HilucaResourceMediaPlatformAdd(ProxySecureResource): 
 
    @application_ns.doc('Add Media Platform Project')
    @v2_api.expect(AddMediaPlatformStruct)        
    @jwt_required
    # @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        payload = request.json 
        data = AddMediaPlatformProjectUseCase(user_id).execute(payload)
        return {'ok' : 1, 'data': data }, 200


@application_ns.route('/hiluca/brand/<brand_id>/media_platform/project')
@v2_api.expect(secureHeader)
class HilucaResourceMediaPlatformProjectsGet(ProxySecureResource): 
 
    @application_ns.doc('Get Media Platform Projects By Brand')
    @jwt_required    
    # @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        data = GetMediaPlatformProjectsUseCase(user_id).execute(brand_id)
        return {'ok' : 1, 'data': data }, 200


@application_ns.route('/hiluca/brand/<brand_id>/media_platform/project/<project_id>/template')
@v2_api.expect(secureHeader)
class HilucaResourceMediaPlatformTemplatesGet(ProxySecureResource): 
 
    @application_ns.doc('Get Media Platform Templates By Project')
    @jwt_required    
    # @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id, project_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        data = GetMediaPlatformTemplatesUseCase(user_id).execute(brand_id, project_id)
        return {'ok' : 1, 'data': data }, 200


@application_ns.route('/hiluca/brand/<brand_id>/media_platform/template/<project_id>')
@v2_api.expect(secureHeader)
class HilucaResourceMediaTemplatesGet(ProxySecureResource): 
 
    @application_ns.doc('Get Templates From Abyssale')
    @jwt_required    
    # @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id, project_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']
        data = GetMediaTemplatesUseCase(user_id).execute(brand_id, project_id)
        return {'ok' : 1, 'data': data }, 200


########################################################################################################################


@application_ns.route('/hiluca/brand')
@v2_api.expect(secureHeader)
class HilucaResourceDefineBrand(ProxySecureResource): 
 
    @application_ns.doc('Defien a Brand (Step 0)')
    @application_ns.deprecated
    @v2_api.expect(DefineBrandStep0Struct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/brand',payload,True)
        return  response, 200
    
    @application_ns.doc('Get a Brand List from a Account')
    @application_ns.deprecated
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
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

        response = n8nClient.executeGet('/webhook/v2/brands',payload,True)
        return  response, 200

    @application_ns.doc('Defien a Brand (Step 1 - 4)')
    @application_ns.deprecated
    @v2_api.expect(DefineBrandStep1_4Struct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/brand',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/brand/update')
@v2_api.expect(secureHeader)
class HilucaResourceUpdateBrand(ProxySecureResource): 
    @application_ns.doc('Update a Brand')
    @application_ns.deprecated
    @v2_api.expect(UpdateBrandStruct)        
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/brand/update',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>')
@v2_api.expect(secureHeader)
class HilucaResourceGetBrand(ProxySecureResource): 
 
    @application_ns.doc('Get a Brand By Id')
    @application_ns.deprecated
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'brand_id' : brand_id }
        response = n8nClient.executeGet('/webhook/v2/brand',payload,True)
        return  response, 200
    

    @application_ns.doc('Delete a Brand')
    @application_ns.deprecated
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_DELETE)
    def delete(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id }
        response = n8nClient.executePut('/webhook/v2/brand/delete',payload,True)
        return  response, 200    


@application_ns.route('/hiluca/brand/<brand_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceSaveImageBrand(ProxySecureResource): 
 
    @application_ns.doc('Upload Brand Image ')
    @application_ns.deprecated
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_UPDATE)
    def post(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/brand/image',{},True,is_binary=False,params=params,files=files)

        return response, 200    
    

    @application_ns.doc('Get Image By Brand')
    @application_ns.deprecated
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_BRAND, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id }
        response = n8nClient.executeGet('/webhook/v2/brand/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])


########################################################################################################################


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/funnel_flow')
@v2_api.expect(secureHeader)
class HilucaResourceFunnelFlowGet(ProxySecureResource): 
 
    @application_ns.doc('Get Funnel Flow by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/funnel_flow',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/funnel_flow/<funnel_flow_id>/channels')
@v2_api.expect(secureHeader)
class HilucaResourceFunnelFlowChannelsGet(ProxySecureResource): 
 
    @application_ns.doc('Get Channels by Funnel Flow')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,funnel_flow_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'funnel_flow_id' : funnel_flow_id }
        response = n8nClient.executeGet('/webhook/v2/funnel_flow/channels',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/funnel_flow/set_channels')
@v2_api.expect(secureHeader)
class HilucaResourceFunnelFlowChannelsSet(ProxySecureResource): 
 
    @application_ns.doc('Set Channels by Funnel Flow')
    @v2_api.expect(SetChannelFunnelFlowStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/funnel_flow/channels',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_structure/channel_group')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureGetChannelGroup(ProxySecureResource): 
 
    @application_ns.doc('Get Channel Group by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/ad_structure/campaign/channel_group',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ad_structure')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureDefine(ProxySecureResource): 
 
    @application_ns.doc('Define Ad Structure by Campaign')
    @v2_api.expect(DefineAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure',payload,True)
        return  response, 200
    
    @application_ns.doc('Update Ad Structure by Campaign')
    @v2_api.expect(UpdateAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/ad_structure',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ad_structure/ad_set')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureAdSetCreate(ProxySecureResource): 
 
    @application_ns.doc('Create Ad Set By Ad Structure')
    @v2_api.expect(CreateAdSetAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure/ad_set',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ad_structure/delete_ad_set')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureAdSetDelete(ProxySecureResource): 
 
    @application_ns.doc('Delete Ad Set By Ad Structure')
    @v2_api.expect(DeleteAdSetAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_DELETE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure/delete_ad_set',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ad_structure/ad_set/ad')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureAdSetAdCreate(ProxySecureResource): 
 
    @application_ns.doc('Create Ad By Ad Set')
    @v2_api.expect(CreateAdAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure/ad_set/ad',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ad_structure/ad_set/delete_ad')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureAdSetAdDelete(ProxySecureResource): 
 
    @application_ns.doc('Delete Ad By Ad Set')
    @v2_api.expect(DeleteAdAdStructureStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_DELETE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure/ad_set/delete_ad',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_structure')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureGetList(ProxySecureResource): 
 
    @application_ns.doc('Get Ad Structure List by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/ad_structures',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_structure/<ad_structure_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureGet(ProxySecureResource): 
 
    @application_ns.doc('Get Ad Structure by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,ad_structure_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_structure_id': ad_structure_id }
        response = n8nClient.executeGet('/webhook/v2/ad_structure',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/channel_group/<channel_group_id>/ad_structure')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureGetByChannelGroup(ProxySecureResource): 
 
    @application_ns.doc('Get Ad Structure by Campaign and Channel Group')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,channel_group_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'channel_group_id': channel_group_id }
        response = n8nClient.executeGet('/webhook/v2/ad_structure/channel_group',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/channel_group/<channel_group_id>/ad_structure/export')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureExportByChannelGroup(ProxySecureResource): 
 
    @application_ns.doc('Export Ad Structure to Excel by Campaign and Channel Group')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,channel_group_id):
        try:
            from app.v2.use_cases.ads_export import ExcelManagerUseCase
            
            export_use_case = ExcelManagerUseCase()
            
            excel_data, filename, status_code = export_use_case.export_to_excel_by_channel_group(
                brand_id=int(brand_id), 
                campaign_id=int(campaign_id),
                channel_group_id=int(channel_group_id)
            )
            
            if excel_data is None:
                return {"error": "No data found or export failed"}, status_code or 404
            
            from flask import send_file
            from io import BytesIO
            
            excel_buffer = BytesIO(excel_data)
            excel_buffer.seek(0)
            
            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=filename
            )
            
        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}, 500


@application_ns.route('/hiluca/brand/ad_structure_template')
@v2_api.expect(secureHeader)
class HilucaResourceAdStructureTemplateDefine(ProxySecureResource): 
 
    @application_ns.doc('Define Ad Structure Template')
    @v2_api.expect(DefineAdStructureTemplateStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad_structure_template',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/brand/audience/generate/description')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceDescriptionGenerate(ProxySecureResource): 
 
    @application_ns.doc('Generate Audiences from Description')
    @v2_api.expect(DescriptionGenerateAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/generate/description',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/brand/audience/generate/form')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceFormGenerate(ProxySecureResource): 
 
    @application_ns.doc('Generate Audiences from Form')
    @v2_api.expect(FormGenerateAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/generate/form',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_set/<ad_set_id>/audience/generate/file')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceFileGenerate(ProxySecureResource): 

    @application_ns.doc('Generate Audiences from File (Image, PDF)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self,brand_id,campaign_id,ad_set_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        files_dict = {}

        if 'files' in request.files:
            files = request.files.getlist('files')
            if files:
                i = 0
                for value in files:
                    if value:
                        content_type = value.content_type
                        filename = value.filename

                        buffer_image = BytesIO(value.read())
                        buffer_image.seek(0)
                        files_dict.update({f'file{i}' : (filename, buffer_image.read() , content_type)})
                        i +=1
                    
        if not files_dict:
            return {"ok": 0, "message": {"code": "SYSVAL001", "text": "File is missing!"}}, 400
        
        params = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_set_id': ad_set_id }

        response = n8nClient.executePost('/webhook/v2/audience/generate/file',{},True,is_binary=False,params=params,files=files_dict)

        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_set/<ad_set_id>/audience/generate/description')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceFileDescriptionGenerate(ProxySecureResource): 

    @application_ns.doc('Generate Audiences from Description - File (Image, PDF)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self,brand_id,campaign_id,ad_set_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        files_dict = {}
        description = request.form.get('description') if request.form else None

        if 'files' in request.files:
            files = request.files.getlist('files')
            if files:
                i = 0
                for value in files:
                    if value:
                        content_type = value.content_type
                        filename = value.filename

                        buffer_image = BytesIO(value.read())
                        buffer_image.seek(0)
                        files_dict.update({f'file{i}' : (filename, buffer_image.read() , content_type)})
                        i +=1
                    
        if not files_dict and not description:
            return {"ok": 0, "message": {"code": "SYSVAL001", "text": "File and Description are missing!"}}, 400
        
        params = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_set_id': ad_set_id, 'description': description }

        response = n8nClient.executePost('/webhook/v2/audience/generate/unified',{},True,is_binary=False,params=params,files=files_dict)

        return  response, 200


@application_ns.route('/hiluca/brand/audience/topic/generate')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceGenerateTopic(ProxySecureResource): 
 
    @application_ns.doc('Generate Topics from Description')
    @v2_api.expect(GenerateTopicAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json
        url = '/webhook/v2/audience/topic/generate'
        job = generate_topics_from_desc.delay({'username': security_credentials['username']}, url, payload)
        return { 'ok': 1, 'data': {'job_id': job.id}}, 200


@application_ns.route('/hiluca/brand/audience/generate/topic')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceTopicsGenerate(ProxySecureResource): 
 
    @application_ns.doc('Generate Audiences from Topics')
    @v2_api.expect(TopicsGenerateAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/generate/topic',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceAudiencePreferredSet(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Audience')
    @v2_api.expect(PreferredSetAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/set_preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceAudiencePreferredSave(ProxySecureResource): 
 
    @application_ns.doc('Update Preferred Audience')
    @v2_api.expect(PreferredSaveAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/preferred',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/brand/audience/reset_ads')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceResetAds(ProxySecureResource): 
 
    @application_ns.doc('Reset Ads By Ad-Set')
    @v2_api.expect(ResetAdsAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/reset_ads',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/saved')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceSaved(ProxySecureResource): 
 
    @application_ns.doc('Save Audience (Saved Audience)')
    @v2_api.expect(SavedAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/saved',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/unsave')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceUnsave(ProxySecureResource): 
 
    @application_ns.doc('Unsave Audience (Saved Audience)')
    @v2_api.expect(SavedAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/unsave',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/saved/<saved_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceSavedDelete(ProxySecureResource):     

    @application_ns.doc('Delete Saved Audience')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_DELETE)
    def delete(self,saved_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'saved_id' : saved_id }
        response = n8nClient.executePut('/webhook/v2/audience/saved/delete',payload,True)
        return  response, 200 


@application_ns.route('/hiluca/brand/audience/cancel')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceCancel(ProxySecureResource): 
 
    @application_ns.doc('Cancel Proposal Audiences By Ad-Set')
    @v2_api.expect(CancelAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_DELETE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/cancel',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/preferred/delete')
@v2_api.expect(secureHeader)
class HilucaResourceAudiencePreferredDelete(ProxySecureResource): 
 
    @application_ns.doc('Delete Preferred Audience By Ad-Set')
    @v2_api.expect(PreferredDeleteAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_DELETE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/preferred/delete',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_set/<ad_set_id>/audience')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceGet(ProxySecureResource): 
 
    @application_ns.doc('Get Audiences by Ad-set')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,ad_set_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_set_id': ad_set_id }
        response = n8nClient.executeGet('/webhook/v2/audiences',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/audience/saved')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceSavedGet(ProxySecureResource): 
 
    @application_ns.doc('Get Saved Audiences by Brand')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id }
        response = n8nClient.executeGet('/webhook/v2/audiences/saved',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/audience/generate/saved')
@v2_api.expect(secureHeader)
class HilucaResourceAudienceCreateSaved(ProxySecureResource): 
 
    @application_ns.doc('Create Audience from Saved')
    @v2_api.expect(SavedGenerateAudienceStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/audience/generate/saved',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/brand/ads_experiment')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentDefine(ProxySecureResource): 
 
    @application_ns.doc('Define Ads Experiment By Ad-Set')
    @v2_api.expect(DefineAdsExperimentStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ads_experiment',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/brand/ads_experiment/<ads_experiment_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentUpdate(ProxySecureResource): 
 
    @application_ns.doc('Update Ads Experiment By Ad-Set')
    @v2_api.expect(UpdateAdsExperimentStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def put(self,ads_experiment_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        payload['ads_experiment_id'] = ads_experiment_id
        response = n8nClient.executePut('/webhook/v2/ads_experiment',payload,True)
        return  response, 200


    @application_ns.doc('Delete Ads Experiment By Ad-Set')
    @v2_api.expect(DeleteAdsExperimentStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def delete(self,ads_experiment_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        payload['ads_experiment_id'] = ads_experiment_id
        response = n8nClient.executePut('/webhook/v2/ads_experiment/delete',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad_set/<ad_set_id>/ads_experiment')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentGet(ProxySecureResource): 
 
    @application_ns.doc('Get Ads Experiment by Ad-set')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,ad_set_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_set_id': ad_set_id }
        response = n8nClient.executeGet('/webhook/v2/ads_experiment',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/ads_experiment/categories')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentCategoriesGet(ProxySecureResource): 
 
    @application_ns.doc('Get Ads Experiment Categories')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id }

        filter = request.args.to_dict(flat=True)
        if 'type' in filter:
            payload.update({'type': filter['type']})

        response = n8nClient.executeGet('/webhook/v2/ads_experiment/categories',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/ads_experiment/category/<category_id>/subcategories')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentSubcategoriesGet(ProxySecureResource): 
 
    @application_ns.doc('Get Ads Experiment Subcategories')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,category_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'category_id': category_id }
        response = n8nClient.executeGet('/webhook/v2/ads_experiment/category/subcategories',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ads_experiment/category')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentCategoryDefine(ProxySecureResource): 
 
    @application_ns.doc('Create Category by Ads Experiment')
    @v2_api.expect(DefineAdsExperimentCategoryStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ads_experiment/category',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/ads_experiment/category/subcategory')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExperimentSubcategoryDefine(ProxySecureResource): 
 
    @application_ns.doc('Create Subcategory by Ads Experiment')
    @v2_api.expect(DefineAdsExperimentSubcategoryStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ads_experiment/category/subcategory',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/marketing_asset/templates')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGetTemplates(ProxySecureResource): 
 
    @application_ns.doc('Get Templates from Asset Platform By Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/marketing_asset/templates',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/marketing_asset/template/<template_id>')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGetTemplate(ProxySecureResource): 
 
    @application_ns.doc('Get a Template from Asset Platform By Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id,template_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id, 'template_id' : template_id }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/marketing_asset/template',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetVisualGenerate(ProxySecureResource): 
 
    @application_ns.doc('Save Marketing Asset')
    @v2_api.expect(SaveMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/set_image_style')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetImageStyleSet(ProxySecureResource): 
 
    @application_ns.doc('Setting Image Style By Marketing Asset')
    @v2_api.expect(SetImageStyleMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/set_image_style',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/image/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGenerateImageAttributes(ProxySecureResource): 
 
    @application_ns.doc('Generate Image Attributes By Marketing Asset')
    @v2_api.expect(GenerateImageAttributesMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image/attributes/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetSaveImageAttributes(ProxySecureResource): 
 
    @application_ns.doc('Save Image Attributes By Marketing Asset')
    @v2_api.expect(SaveImageAttributesMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image/attributes',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/image/prompts/generate')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGenerateImagePrompts(ProxySecureResource): 
 
    @application_ns.doc('Generate Image Prompts By Marketing Asset Attributes')
    @v2_api.expect(GenerateImagePromptsMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image/prompts/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/image/prompts/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetSetImagePrompt(ProxySecureResource): 
 
    @application_ns.doc('Setting Preferred Image Prompt from Marketing Asset')
    @v2_api.expect(SetImagePromptMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image/prompts/set_preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/image/prompts/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetSaveImagePrompt(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Image Prompt from Marketing Asset')
    @v2_api.expect(SaveImagePromptMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image/prompts/preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/marketing_asset/<template_id>/image/<image_name>')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetImage(ProxySecureResource): 

    @application_ns.doc('Upload Marketing Asset Image')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self,brand_id,project_id,campaign_id,template_id,image_name):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id, 'template_id' : template_id, 'image_name' : image_name }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/image',{},True,is_binary=False,params=params,files=files)

        return  response, 200
    
    @application_ns.doc('Get Marketing Asset Image')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id,template_id,image_name):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id, 'template_id' : template_id, 'image_name' : image_name }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/marketing_asset/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])  


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/generate_texts')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGenerateTexts(ProxySecureResource): 
 
    @application_ns.doc('Generate Texts By Marketing Asset')
    @v2_api.expect(GenerateTextsMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/generate_texts',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/generate_text')
@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetGenerateTexts(ProxySecureResource): 
 
    @application_ns.doc('Generate a Text By Marketing Asset')
    @v2_api.expect(GenerateTextMarketingAssetStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/generate_text',payload,True)
        return  response, 200


@application_ns.route('/hiluca/brand/project/campaign/marketing_asset/platform/asset_generation_hook')
#@v2_api.expect(secureHeader)
class HilucaResourceMarketingAssetAbyssaleHook(ProxySecureResource): 
 
    @application_ns.doc('Abyssale Web Hook')
    @v2_api.expect(AbyssaleHooktMarketingAssetStruct)        
    #@jwt_required    
    def post(self):
        #security_credentials = self.checkCredentials()
        n8nClient = N8NClient()
        payload = request.json
        if 'generation_request_id' in payload:
            response = n8nClient.executePost('/webhook/v2/project/campaign/marketing_asset/platform/asset_generation_hook',payload,False)
        
        return {}, 200

########################################################################################################################


@application_ns.route('/hiluca/test/strapi/campaign/<campaign_id>')
@v2_api.expect(secureHeader)
class HilucaResourceTestStrapiGetCampaign(ProxySecureResource):
    @application_ns.doc('Test Strapi Connection - Get Campaign')
    @application_ns.param('brand_id', 'Brand ID', required=False, type='integer')
    @application_ns.param('channel_group_id', 'Channel Group ID', required=False, type='integer')
    @application_ns.param('user_id', 'User ID for Page Fetching', required=False, type='string')
    #@jwt_required
    #@check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_READ)
    def get(self, campaign_id):
        import traceback
        try:
            brand_id = request.args.get('brand_id')
            channel_group_id = request.args.get('channel_group_id')
            user_id = request.args.get('user_id')

            from app.v2.use_cases.facebook_validator_service import MetaAdsConnectionService
            
            try:
                meta_ads_connection_service = MetaAdsConnectionService(campaign_id=120, campaign_platform_id=1)
                payload = meta_ads_connection_service.build_meta_payload()
                #payload = validator.execute(campaign_id=campaign_id, brand_id=brand_id, channel_group_id=channel_group_id, user_id=user_id)
                return { 
                    'ok': 1, 
                    'can_publish': True, 
                    'message': 'Campaign is ready to be published',
                    'payload': payload 
                }, 200
            except IncorrectValidationException as ive:
                 return { 
                     'ok': 1, 
                     'can_publish': False, 
                     'message': 'Campaign cannot be published',
                     'errors': ive.errors 
                }, 200

        except Exception as e:
            return {'error': str(e), 'repr': repr(e), 'traceback': traceback.format_exc()}, 500
