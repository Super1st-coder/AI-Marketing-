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
from app.v1.models.constant import FUNCTION_UMBRELLA_CAMPAIGN, ACTION_CREATE, ACTION_UPDATE, ACTION_READ, ROLE_HILUCA_ADMIN, FUNCTION_PROJECT
from app.v2 import v2_api

umbrella_ns = v2_api.namespace('application', description='Aplication Services')

config_type = os.environ.get('CONFIG_TYPE', 'dev')

DefineUmbrellaCampaignStruct = v2_api.model('DefineUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'name': fields.String(),
    'context': fields.String(),
    'target_regions': fields.String(),
    'language': fields.String()
})

UpdateUmbrellaCampaignStruct = v2_api.model('UpdateUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'name': fields.String(),
    'context': fields.String(),
    'target_regions': fields.String(),
    'language': fields.String()
})

SetCentralIdeaUmbrellaCampaignStruct = v2_api.model('SetCentralIdeaUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'central_idea': fields.String()
})

SetBPersonResourcesUmbrellaCampaignStruct = v2_api.model('SetBPersonResourcesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_resources': fields.List(fields.Raw())
})

SaveBenefitsUmbrellaCampaignStruct = v2_api.model('SaveBenefitsUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_resource_selected': fields.Raw(),
    'resource_exchange': fields.Raw(),
    'benefit_reasoning': fields.String(),
    'benefits': fields.List(fields.Raw())
})

PreferredBenefitUmbrellaCampaignStruct = v2_api.model('PreferredBenefitUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'preferred_benefit_id': fields.Integer()
})

SetBPersonMotivesBarriersUmbrellaCampaignStruct = v2_api.model('SetBPersonMotivesBarriersUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motives': fields.List(fields.Raw()),
    'bperson_barriers': fields.List(fields.Raw())
})

SaveDramasUmbrellaCampaignStruct = v2_api.model('SaveDramasUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw(),
    'drama_reasoning': fields.String(),
    'dramas': fields.List(fields.Raw())
})

PreferredDramaUmbrellaCampaignStruct = v2_api.model('PreferredDramaUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'preferred_drama_id': fields.Integer()
})

SetStoryStagesUmbrellaCampaignStruct = v2_api.model('SetStoryStagesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'story_stages': fields.List(fields.Raw())
})

SaveScenesUmbrellaCampaignStruct = v2_api.model('SaveScenesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String(),
    'scenes': fields.List(fields.Raw())
})

PreferredSceneUmbrellaCampaignStruct = v2_api.model('PreferredSceneUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'preferred_scene_id': fields.Integer()
})

GenerateUmbrellaCampaignsStruct = v2_api.model('GenerateUmbrellaCampaignsStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

AskLucaUmbrellaCampaignsStruct = v2_api.model('AskLucaUmbrellaCampaignsStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'umbrella_campaigns': fields.List(fields.Raw())
})

AskLucaUmbrellaCampaignStruct = v2_api.model('AskLucaUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'umbrella_campaign_selected': fields.Raw()
})

SaveUmbrellaCampaignsStruct = v2_api.model('SaveUmbrellaCampaignsStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'umbrella_campaigns': fields.List(fields.Raw())
})

PreferredUmbrellaCampaignStruct = v2_api.model('PreferredUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'preferred_umbrella_campaign_id': fields.Integer()
})

GenerateSummaryUmbrellaCampaignStruct = v2_api.model('GenerateSummaryUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

SetImageStyleUmbrellaCampaignStruct = v2_api.model('SetImageStyleUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'image_style_id': fields.Integer()
})

GenerateImageAttributesUmbrellaCampaignStruct = v2_api.model('GenerateImageAttributesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

SaveImageAttributesUmbrellaCampaignStruct = v2_api.model('SaveImageAttributesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

GenerateImagePromptsUmbrellaCampaignStruct = v2_api.model('GenerateImagePromptsUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

SetPreferredImagePromptUmbrellaCampaignStruct = v2_api.model('SetPreferredImagePromptUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'image_prompt_id': fields.Integer()
})

SavePreferredImagePromptUmbrellaCampaignStruct = v2_api.model('SavePreferredImagePromptUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'preferred_image_prompt': fields.Raw()
})

SaveSummaryUmbrellaCampaignStruct = v2_api.model('SaveSummaryUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'summary_generated': fields.Raw(),
    'summary_saved': fields.Raw()
})

AskLucaCentraIdeaUmbrellaCampaignStruct = v2_api.model('AskLucaCentraIdeaUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String()
})

AskLucaBuyerResourcesUmbrellaCampaignStruct = v2_api.model('AskLucaBuyerResourcesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

AskLucaBuyerResourceUmbrellaCampaignStruct = v2_api.model('AskLucaBuyerResourceUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_resource_selected': fields.Raw()
})

GenerateResourceExchangeUmbrellaCampaignStruct = v2_api.model('GenerateResourceExchangeUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_resource_base': fields.Raw(),
    'bperson_resource_exchangeable': fields.Raw()
})

GenerateBenefitsUmbrellaCampaignStruct = v2_api.model('GenerateBenefitsUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_resource_base': fields.Raw(),
    'bperson_resource_exchangeable': fields.Raw(),
    'resource_exchange': fields.Raw(),
    'benefit_reasoning': fields.String()
})

AskLucaBenefitsUmbrellaCampaignStruct = v2_api.model('AskLucaBenefitsUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'bperson_resource_base': fields.Raw(),
    'bperson_resource_exchangeable': fields.Raw(),
    'resource_exchange': fields.Raw(),
    'benefit_reasoning': fields.String()
})

AskLucaBenefitUmbrellaCampaignStruct = v2_api.model('AskLucaBenefitUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'bperson_resource_base': fields.Raw(),
    'bperson_resource_exchangeable': fields.Raw(),
    'resource_exchange': fields.Raw(),
    'benefit_reasoning': fields.String(),
    'benefit_selected': fields.Raw()
})

AskLucaMotivesBarriersUmbrellaCampaignStruct = v2_api.model('AskLucaMotivesBarriersUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer()
})

AskLucaMotiveBarrierUmbrellaCampaignStruct = v2_api.model('AskLucaMotiveBarrierUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'motive_barrier_selected': fields.Raw()
})

GenerateEmotionaTensionUmbrellaCampaignStruct = v2_api.model('GenerateEmotionaTensionUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw()
})

RegenerateEmotionaTensionUmbrellaCampaignStruct = v2_api.model('RegenerateEmotionaTensionUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw()
})

GenerateDramasUmbrellaCampaignStruct = v2_api.model('GenerateDramasUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw(),
    'drama_reasoning': fields.String()
})

RegenerateDramasUmbrellaCampaignStruct = v2_api.model('RegenerateDramasUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw(),
    'drama_reasoning': fields.String(),
    'dramas': fields.List(fields.Raw())
})

AskLucaDramasUmbrellaCampaignStruct = v2_api.model('AskLucaDramasUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw(),
    'drama_reasoning': fields.String(),
    'dramas': fields.List(fields.Raw())
})

AskLucaDramaUmbrellaCampaignStruct = v2_api.model('AskLucaDramaUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'bperson_motive_selected': fields.Raw(),
    'bperson_barrier_selected': fields.Raw(),
    'emotional_tension': fields.Raw(),
    'drama_reasoning': fields.String(),
    'drama_selected': fields.Raw()
})

GenerateCategoriesStagesUmbrellaCampaignStruct = v2_api.model('GenerateCategoriesStagesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw())
})

GenerateStoryPlotUmbrellaCampaignStruct = v2_api.model('GenerateStoryPlotUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw())
})

RegenerateStoryPlotUmbrellaCampaignStruct = v2_api.model('RegenerateStoryPlotUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String()
})

GenerateScenesUmbrellaCampaignStruct = v2_api.model('GenerateScenesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String()
})

RegenerateScenesUmbrellaCampaignStruct = v2_api.model('RegenerateScenesUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String(),
    'scenes': fields.List(fields.Raw())
})

AskLucaScenesPlotUmbrellaCampaignStruct = v2_api.model('AskLucaScenesPlotUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String(),
    'scenes': fields.List(fields.Raw())
})

AskLucaScenePlotUmbrellaCampaignStruct = v2_api.model('AskLucaScenePlotUmbrellaCampaignStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'text': fields.String(),
    'stages_selected': fields.List(fields.Raw()),
    'story_plot': fields.String(),
    'scene_reasoning': fields.String(),
    'scene_selected': fields.Raw()
})

UploadUmbrellaCampaignImageIDStruct = v2_api.model('UploadUmbrellaCampaignImageIDStruct', { 
    'brand_id': fields.Integer(),
    'project_id': fields.Integer(),
    'ucampaign_id': fields.Integer(),
    'image_id': fields.String()
})

AnalyzeMarketingHypothesisStruct = v2_api.model('AnalyzeMarketingHypothesisStruct', { 
    'project_id': fields.Integer(required=True, description='Project ID'),
    'marketing_hypothesis': fields.String(required=True, description='Marketing hypothesis text')
})


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignDefine(ProxySecureResource): 
 
    @umbrella_ns.doc('Define a Umbrella Campaign By Project')
    @v2_api.expect(DefineUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign',payload,True)
        return  response, 200

    @umbrella_ns.doc('Update a Umbrella Campaign By Project')
    @v2_api.expect(UpdateUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePut('/webhook/v2/project/umbrella_campaign',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/set_central_idea')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignCentralIdeaSet(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Central Idea By Umbrella Campaign')
    @v2_api.expect(SetCentralIdeaUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/set_central_idea',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/set_bperson_resources')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignBPersonResourcesSet(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Buyer Person Resources By Umbrella Campaign')
    @v2_api.expect(SetBPersonResourcesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/set_bperson_resources',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/benefit/generated')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignBenefitSave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Generated Benefits By Umbrella Campaign')
    @v2_api.expect(SaveBenefitsUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/benefit/generated',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/benefit/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignBenefitPreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Preferred Benefit By Umbrella Campaign')
    @v2_api.expect(PreferredBenefitUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/benefit/set_preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/set_bperson_motives_barriers')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignBPersonMotivesBarriersSet(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Buyer Person Motives and Barriers By Umbrella Campaign')
    @v2_api.expect(SetBPersonMotivesBarriersUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/set_bperson_motives_barriers',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/drama/generated')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignDramasSave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Generated Dramas By Umbrella Campaign')
    @v2_api.expect(SaveDramasUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/drama/generated',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/drama/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignDramaPreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Preferred Drama By Umbrella Campaign')
    @v2_api.expect(PreferredDramaUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/drama/set_preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/scene/set_story_stages')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignStoryStagesSet(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Story Stages By Umbrella Campaign')
    @v2_api.expect(SetStoryStagesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/scene/set_story_stages',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/scene/generated')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignScenesSave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Generated Scenes By Umbrella Campaign')
    @v2_api.expect(SaveScenesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/scene/generated',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/scene/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignScenePreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Preferred Scene By Umbrella Campaign')
    @v2_api.expect(PreferredSceneUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/scene/set_preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignsGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Umbrella Campaigns')
    @v2_api.expect(GenerateUmbrellaCampaignsStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_umbrella_campaigns')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignsAskLuca(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For Umbrella Campaigns')
    @v2_api.expect(AskLucaUmbrellaCampaignsStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_umbrella_campaigns',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_a_umbrella_campaign')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLuca(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For a Umbrella Campaign')
    @v2_api.expect(AskLucaUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_a_umbrella_campaign',payload,True)
        return  response, 200

@umbrella_ns.route('/hiluca/brand/project/marketing-hypothesis')
@v2_api.expect(secureHeader)
class HilucaResourceAnalyzeMarketingHypothesis(ProxySecureResource): 
 
    @umbrella_ns.doc('Analyze Marketing Hypothesis')
    @v2_api.expect(AnalyzeMarketingHypothesisStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_PROJECT, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json 
        
        cfg = config.get(os.environ.get('CONFIG_TYPE', 'dev'))
        fury_routing = getattr(cfg, 'FURY_ROUTING_ENABLED', False)

        if fury_routing:
            from app.v2.use_cases.project_v2 import AnalyzeMarketingHypothesisUseCase
            data = AnalyzeMarketingHypothesisUseCase(user_id).execute(payload)
            return data, 200
        else:
            n8nClient = N8NClient(credentials=security_credentials)
            response = n8nClient.executePost('/project/marketing-hypothesis', payload, True)
            return response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generated')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignsSave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Generated Umbrella Campaigns')
    @v2_api.expect(SaveUmbrellaCampaignsStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generated',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignPreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Preferred Umbrella Campaign')
    @v2_api.expect(PreferredUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/set_preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/summary/generate')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignSummaryGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Summary By Umbrella Campaign')
    @v2_api.expect(GenerateSummaryUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/summary/generate',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/set_image_style')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageStyleSet(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Image Style By Umbrella Campaign')
    @v2_api.expect(SetImageStyleUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/set_image_style',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageAttributesGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Image Attributes By Umbrella Campaign')
    @v2_api.expect(GenerateImageAttributesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image/attributes/generate',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageAttributesSave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Image Attributes By Umbrella Campaign')
    @v2_api.expect(SaveImageAttributesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image/attributes',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/umbrella_campaign/<ucampaign_id>/image/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageAttributesGet(ProxySecureResource): 
 
    @umbrella_ns.doc('Get Image Attributes from Umbrella Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_READ)
    def get(self,brand_id,project_id,ucampaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'ucampaign_id' : ucampaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/umbrella_campaign/image/attributes',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image/prompts/generate')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImagePromptsGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Image Prompts From Umbrella Campaign Attributes')
    @v2_api.expect(GenerateImagePromptsUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image/prompts/generate',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image/prompts/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImagePromptSetPreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Setting Preferred Image Prompt From Umbrella Campaign')
    @v2_api.expect(SetPreferredImagePromptUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image/prompts/set_preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image/prompts/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImagePromptSavePreferred(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Preferred Image Prompt From Umbrella Campaign')
    @v2_api.expect(SavePreferredImagePromptUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image/prompts/preferred',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/umbrella_campaign/<ucampaign_id>/image/prompts')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageAttributesGet(ProxySecureResource): 
 
    @umbrella_ns.doc('Get Image Attributes from Umbrella Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_READ)
    def get(self,brand_id,project_id,ucampaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'ucampaign_id' : ucampaign_id }
        response = n8nClient.executeGet('/webhook/v2/project/umbrella_campaign/image/prompts',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/umbrella_campaign/<ucampaign_id>/image')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImage(ProxySecureResource): 

    @umbrella_ns.doc('Upload Umbrella Campaign Image (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self,brand_id,project_id,ucampaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'project_id' : project_id, 'ucampaign_id' : ucampaign_id }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image',{},True,is_binary=False,params=params,files=files)

        return  response, 200
    

@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/image')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignImageID(ProxySecureResource): 
 
    @umbrella_ns.doc('Upload Umbrella Campaign Image by Id')
    @v2_api.expect(UploadUmbrellaCampaignImageIDStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/image_id',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/summary')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignSummarySave(ProxySecureResource): 
 
    @umbrella_ns.doc('Save Umbrella Campaign Summary')
    @v2_api.expect(SaveSummaryUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/summary',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/umbrella_campaign/<ucampaign_id>')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignGet(ProxySecureResource): 
 
    @umbrella_ns.doc('Get a Umbrella Campaign By Project')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_READ)
    def get(self,brand_id,project_id,ucampaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        cfg = config.get(config_type)
        API_URL = f"{getattr(cfg, 'IMAGE_LIBRARY_URL', 'http://image-library:8000')}/images"
        payload = { 'brand_id' : brand_id, 'project_id' : project_id, 'ucampaign_id' : ucampaign_id, 'API_URL': API_URL }
        response = n8nClient.executeGet('/webhook/v2/project/umbrella_campaign',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/<brand_id>/project/<project_id>/umbrella_campaign')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignsGet(ProxySecureResource): 
 
    @umbrella_ns.doc('Get a Umbrella Campaign List By Project')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_READ)
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

        response = n8nClient.executeGet('/webhook/v2/project/umbrella_campaigns',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_central_idea')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaCentralIdea(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca By Central Idea For Umbrella Campaign')
    @v2_api.expect(AskLucaCentraIdeaUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_central_idea',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_buyer_resources')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaBuyerResources(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca By Buyer Resources For Umbrella Campaign')
    @v2_api.expect(AskLucaBuyerResourcesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_buyer_resources',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_a_buyer_resource')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaBuyerResource(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca By a Buyer Resource For Umbrella Campaign')
    @v2_api.expect(AskLucaBuyerResourceUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_a_buyer_resource',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_resource_exchange')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaResourceExchange(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Resource Exchange For Umbrella Campaign')
    @v2_api.expect(GenerateResourceExchangeUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_resource_exchange',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_benefits')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignBenefitsGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Benefits For Umbrella Campaign')
    @v2_api.expect(GenerateBenefitsUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_benefits',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_benefits')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaBenefits(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For Benefits By Umbrella Campaign')
    @v2_api.expect(AskLucaBenefitsUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_benefits',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_a_benefit')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaBenefit(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For a Benefit By Umbrella Campaign')
    @v2_api.expect(AskLucaBenefitUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_a_benefit',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_bperson_motives_barriers')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaMotivesBarriers(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For Buyer Person Motives and Barriers By Umbrella Campaign')
    @v2_api.expect(AskLucaMotivesBarriersUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_bperson_motives_barriers',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_bperson_a_motive_barrier')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaMotiveBarrier(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For a Buyer Person Motive and Barrier By Umbrella Campaign')
    @v2_api.expect(AskLucaMotiveBarrierUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_bperson_a_motive_barrier',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_emotional_tension')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignEmotionalTensionGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Emotional Tension By Umbrella Campaign')
    @v2_api.expect(GenerateEmotionaTensionUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_emotional_tension',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/regenerate_emotional_tension')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignEmotionalTensionRegenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Regenerate Emotional Tension By Umbrella Campaign')
    @v2_api.expect(RegenerateEmotionaTensionUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/regenerate_emotional_tension',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_dramas')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignDramasGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Dramas By Umbrella Campaign')
    @v2_api.expect(GenerateDramasUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_dramas',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/regenerate_dramas')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignDramasRegenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Regenerate Dramas By Umbrella Campaign')
    @v2_api.expect(RegenerateDramasUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/regenerate_dramas',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_dramas')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaDramas(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For Dramas By Umbrella Campaign')
    @v2_api.expect(AskLucaDramasUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_dramas',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_a_drama')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaDrama(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca a For Drama By Umbrella Campaign')
    @v2_api.expect(AskLucaDramaUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_a_drama',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_categories_stages')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignCategoriesStagesGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Categories and Stages By Umbrella Campaign')
    @v2_api.expect(GenerateCategoriesStagesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_categories_stages',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_story_plot')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignStoryPlotGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Story Plot By Umbrella Campaign')
    @v2_api.expect(GenerateStoryPlotUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_story_plot',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/regenerate_story_plot')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignStoryPlotRegenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Regenerate Story Plot By Umbrella Campaign')
    @v2_api.expect(RegenerateStoryPlotUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/regenerate_story_plot',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/generate_scenes')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignScenesGenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Generate Scenes By Umbrella Campaign')
    @v2_api.expect(GenerateScenesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/generate_scenes',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/regenerate_scenes')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignScenesRegenerate(ProxySecureResource): 
 
    @umbrella_ns.doc('Regenerate Scenes By Umbrella Campaign')
    @v2_api.expect(RegenerateScenesUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/regenerate_scenes',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_scenes')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaScenes(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For Scenes By Umbrella Campaign')
    @v2_api.expect(AskLucaScenesPlotUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_scenes',payload,True)
        return  response, 200


@umbrella_ns.route('/hiluca/brand/project/umbrella_campaign/ask_luca_a_scene')
@v2_api.expect(secureHeader)
class HilucaResourceUmbrellaCampaignAskLucaScene(ProxySecureResource): 
 
    @umbrella_ns.doc('Ask Luca For a Scene By Umbrella Campaign')
    @v2_api.expect(AskLucaScenePlotUmbrellaCampaignStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_UMBRELLA_CAMPAIGN, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/project/umbrella_campaign/ask_luca_a_scene',payload,True)
        return  response, 200
