import os
import json
from io import BytesIO
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import fields
from flask.globals import request
from config import config
from app.tools.permissions import check_access
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from app.v1.models.constant import FUNCTION_CAMPAIGN_SETUP, FUNCTION_CAMPAIGN_CREATIVE, ACTION_CREATE, ACTION_READ, ACTION_UPDATE, ROLE_HILUCA_ADMIN
from app.v2 import v2_api
from app.v2.use_cases.campaign import GetACampaignByMetaIDUseCase

campaign_ns = v2_api.namespace('application', description='Aplication Services')

config_type = os.environ.get('CONFIG_TYPE', 'dev')

DefineCampaignStruct = v2_api.model('DefineCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'target_regions': fields.String(),
    'language': fields.String()
})

UpdateCampaignStruct = v2_api.model('UpdateCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'name': fields.String(),
    'description': fields.String(),
    'target_regions': fields.String(),
    'language': fields.String()
})

SetUmbrellaCampaignByCampaignStruct = v2_api.model('SetUmbrellaCampaignByCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

SetFunnelCampaignStruct = v2_api.model('SetFunnelCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'funnel_id': fields.Integer()
})

SetChannelGroupCampaignStruct = v2_api.model('SetChannelGroupCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'channel_group': fields.List(fields.Integer())
})

SaveMetricsCampaignStruct = v2_api.model('SaveMetricsCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'advance': fields.Boolean(default=True),
    'channel_group_metrics': fields.List(fields.Raw())
})

SetBigIdeaCampaignStruct = v2_api.model('SetBigIdeaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'big_idea': fields.String()
})

SetTimingCampaignStruct = v2_api.model('SetTimingCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'timing': fields.String()
})

SetMessageLocationCampaignStruct = v2_api.model('SetMessageLocationCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'message_location': fields.String()
})

SetAudienceExperienceCampaignStruct = v2_api.model('SetAudienceExperienceCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'audience_experience': fields.String()
})

SetToolsCampaignStruct = v2_api.model('SetToolsCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'tools': fields.String()
})

SetProductDetailsCampaignStruct = v2_api.model('SetProductDetailsCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'product_details': fields.Raw()
})

SetBuyerPersonDetailsCampaignStruct = v2_api.model('SetBuyerPersonDetailsCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'bperson_details': fields.Raw()
})

SaveGeneratedCampaignStruct = v2_api.model('SaveGeneratedCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'campaigns': fields.List(fields.Raw())
})

SetPreferredCampaignStruct = v2_api.model('SetPreferredCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'preferred_campaign_id': fields.Integer()
})

GenerateSummaryCampaignStruct = v2_api.model('GenerateSummaryCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer()
})

SetImageStyleCampaignStruct = v2_api.model('SetImageStyleCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'image_style_id': fields.Integer()
})

GenerateImageAttributesCampaignStruct = v2_api.model('GenerateImageAttributesCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer()
})

SaveImageAttributesCampaignStruct = v2_api.model('SaveImageAttributesCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

GenerateImagePromptsCampaignStruct = v2_api.model('GenerateImagePromptsCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer()
})

SetPreferredImagePromptCampaignStruct = v2_api.model('SetPreferredImagePromptCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'image_prompt_id': fields.Integer()
})

SavePreferredImagePromptCampaignStruct = v2_api.model('SavePreferredImagePromptCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'preferred_image_prompt': fields.Raw()
})

UploadCampaignImageIdStruct = v2_api.model('UploadCampaignImageIdStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'image_id': fields.String()
})

SaveSummaryCampaignStruct = v2_api.model('SaveSummaryCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'summary_generated': fields.Raw(),
    'summary_saved': fields.Raw()
})

AskLucaStepCampaignStruct = v2_api.model('AskLucaStepCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'step': fields.Integer(),
    'text': fields.String()
})

AskLucaCampaignsStruct = v2_api.model('AskLucaCampaignsStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'text': fields.String(),
    'campaigns': fields.List(fields.Raw())
})

AskLucaCampaignStruct = v2_api.model('AskLucaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'campaign_selected': fields.Raw(),
    'text': fields.String()
})

SetAssetPaltformProjectCampaignStruct = v2_api.model('SetAssetPaltformProjectCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'asset_platform_project_id': fields.String()
})

SaveAssetDeliveryCampaignStruct = v2_api.model('SaveAssetDeliveryCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'campaign_name': fields.String(),
    'summary': fields.Raw(),
    'type': fields.String(),
    'masters': fields.List(fields.Raw())
})

@campaign_ns.route('/hiluca/brand/project/campaign')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignDefine(ProxySecureResource): 
 
    @campaign_ns.doc('Define a Campaign By Project')
    @v2_api.expect(DefineCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign',payload,True)
        return  response, 200

    @campaign_ns.doc('Update a Campaign By Project')
    @v2_api.expect(UpdateCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/project/campaign',payload,True)
        return  response, 200
    

@campaign_ns.route('/hiluca/brand/project/campaign/set_umbrella_campaign')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetUmbrellaCampaign(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Umbrella Campaign By Campaign')
    @v2_api.expect(SetUmbrellaCampaignByCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_umbrella_campaign',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_funnel')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetFunnel(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Funnel By Campaign')
    @v2_api.expect(SetFunnelCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_funnel',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_channel_group')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetChannelGroup(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Channel Group By Campaign')
    @v2_api.expect(SetChannelGroupCampaignStruct)        
    @jwt_required   
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_UPDATE) 
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_channel_group',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/metrics')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSaveMatrics(ProxySecureResource): 
 
    @campaign_ns.doc('Save Metrics By Campaign')
    @v2_api.expect(SaveMetricsCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_SETUP, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/metrics',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_big_idea')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetBigIdea(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Big Idea By Campaign')
    @v2_api.expect(SetBigIdeaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_big_idea',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_timing')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetTiming(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Timing By Campaign')
    @v2_api.expect(SetTimingCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_timing',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_message_location')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetMessageLocation(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Message Location By Campaign')
    @v2_api.expect(SetMessageLocationCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_message_location',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_audience_experience')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetAudienceExperience(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Audience Experience By Campaign')
    @v2_api.expect(SetAudienceExperienceCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_audience_experience',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_tools')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetTools(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Tools By Campaign')
    @v2_api.expect(SetToolsCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_tools',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_product_details')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetProductDetails(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Product Details By Campaign')
    @v2_api.expect(SetProductDetailsCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_product_details',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_buyer_person_details')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetBuyerPersonDetails(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Buyer Person Details By Campaign')
    @v2_api.expect(SetBuyerPersonDetailsCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_buyer_person_details',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/generated')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSaveGenerated(ProxySecureResource): 
 
    @campaign_ns.doc('Save Generated Campaigns')
    @v2_api.expect(SaveGeneratedCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/generated',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetPreferred(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Preferred Campaign')
    @v2_api.expect(SetPreferredCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_preferred',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/summary/generate')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGenerateSummary(ProxySecureResource): 
 
    @campaign_ns.doc('Generate Summary By Campaign')
    @v2_api.expect(GenerateSummaryCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/summary/generate',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_image_style')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetImageStyle(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Image Style By Campaign')
    @v2_api.expect(SetImageStyleCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_image_style',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGenerateImageAttributes(ProxySecureResource): 
 
    @campaign_ns.doc('Generate Image Attributes By Campaign')
    @v2_api.expect(GenerateImageAttributesCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image/attributes/generate',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSaveImageAttributes(ProxySecureResource): 
 
    @campaign_ns.doc('Save Image Attributes By Campaign')
    @v2_api.expect(SaveImageAttributesCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image/attributes',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGetImageAttributes(ProxySecureResource): 
 
    @campaign_ns.doc('Get Image Attributes from Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/image/attributes',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image/prompts/generate')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGenerateImagePrompts(ProxySecureResource): 
 
    @campaign_ns.doc('Generate Image Prompts By Campaign Attributes')
    @v2_api.expect(GenerateImagePromptsCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image/prompts/generate',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image/prompts/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetImagePrompt(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Preferred Image Prompt By Campaign')
    @v2_api.expect(SetPreferredImagePromptCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image/prompts/set_preferred',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image/prompts/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSavePreferredImagePrompt(ProxySecureResource): 
 
    @campaign_ns.doc('Save Preferred Image Prompt By Campaign')
    @v2_api.expect(SavePreferredImagePromptCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image/prompts/preferred',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/image/prompts')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGetImagePrompts(ProxySecureResource): 
 
    @campaign_ns.doc('Get Image Prompts from Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/image/prompts',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignImage(ProxySecureResource): 

    @campaign_ns.doc('Upload Campaign Image (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/project/campaign/image',{},True,is_binary=False,params=params,files=files)

        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/image')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignImageId(ProxySecureResource): 
 
    @campaign_ns.doc('Upload Campaign Image By ID')
    @v2_api.expect(UploadCampaignImageIdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/image_id',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/summary')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSaveSummary(ProxySecureResource): 
 
    @campaign_ns.doc('Save Summary By Campaign')
    @v2_api.expect(SaveSummaryCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/summary',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGetOne(ProxySecureResource): 
 
    @campaign_ns.doc('Get a Campaign By Project')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id, 'API_URL' : API_URL }
        response = n8nClient.executeGet('/webhook/v2/project/campaign',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGetList(ProxySecureResource): 
 
    @campaign_ns.doc('Get a Campaign List By Project')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id }

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

        response = n8nClient.executeGet('/webhook/v2/project/campaigns', payload, True)
        return response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/ask_luca_step')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignAskLucaByStep(ProxySecureResource): 
 
    @campaign_ns.doc('Ask Luca By Step for Campaign')
    @v2_api.expect(AskLucaStepCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/ask_luca_step',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/ask_luca_campaigns')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignAskLucaForCampaigns(ProxySecureResource): 
 
    @campaign_ns.doc('Ask Luca for Campaigns')
    @v2_api.expect(AskLucaCampaignsStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/ask_luca_campaigns',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/ask_luca_campaign')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignAskLucaForCampaign(ProxySecureResource): 
 
    @campaign_ns.doc('Ask Luca for a Campaign')
    @v2_api.expect(AskLucaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/ask_luca_campaign',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/set_asset_platform_project')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSetAssetPlatformProjectId(ProxySecureResource): 
 
    @campaign_ns.doc('Setting Asset Platform Project ID By Campaign')
    @v2_api.expect(SetAssetPaltformProjectCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/set_asset_platform_project',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/campaign/<campaign_id>/asset_delivery')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignGetAssetDelivery(ProxySecureResource): 
 
    @campaign_ns.doc('Get Asset Delivery By Campaign (Email)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,brand_id,project_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/campaign/asset_delivery',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/project/campaign/asset_delivery')
@v2_api.expect(secureHeader)
class HilucaResourceCampaignSaveAssetDelivery(ProxySecureResource): 
 
    @campaign_ns.doc('Save Asset Delivery By Campaign (Email)')
    @v2_api.expect(SaveAssetDeliveryCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/campaign/asset_delivery',payload,True)
        return  response, 200


@campaign_ns.route('/hiluca/brand/campaign/meta_campaign/<meta_campaign_id>')
@v2_api.expect(secureHeader)
class HilucaResourceMetaCampaignGet(ProxySecureResource): 
 
    @campaign_ns.doc('Get Campaign By Meta')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_CREATIVE, ACTION_READ)
    def get(self,meta_campaign_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = GetACampaignByMetaIDUseCase(user_id).execute(meta_campaign_id)
        return {'ok': 1, 'data': data}, 200


    