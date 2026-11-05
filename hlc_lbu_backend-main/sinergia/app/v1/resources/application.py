from app.v1 import v1_api
from app.v1.use_cases.application import GetApplicationUseCase, GetCoinBySymbolUseCase, GetDefaultCoinUseCase
from flask_jwt_extended.view_decorators import jwt_required
from flask_restplus import Resource, Namespace, fields
from app.v1.resources.base import ProxySecureResource, secureHeader,queryParams

from app.v1.repository.base import N8NClient

from flask import send_file

from flask.globals import request    
import json

application_ns = v1_api.namespace('application', description='Aplication Services')


CoinStruct = v1_api.model('CoinStruct', { 
    'id':  fields.String(),
    'diminutive':   fields.String(),
    'name':  fields.String(),
    'description':  fields.String(),
    'dec_separator':  fields.String(),
    'th_separator':  fields.String(),
    'creation_date': fields.DateTime(),
    'blockchain_address':  fields.String(),
    'application_id':  fields.String(),
    'status':  fields.String()
})

GetOneCoinStruct = v1_api.model('GetOneCoinStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(CoinStruct,attribute='data')
}) 

ApplicationStruct = v1_api.model('ApplicationStruct', { 
    'id' : fields.String(),
    'app_key' : fields.String(), 
    'fiat_coin': fields.Nested(CoinStruct,attribute='default_fiat_coin'),    
    'app_iv': fields.String(), 
    'name' : fields.String(), 
    'crypto_coin': fields.Nested(CoinStruct,attribute='default_crypto_coin'),
    'status': fields.String()
})

GetOneApplicationStruct = v1_api.model('GetOneApplicationStruct', { 
    'ok' : fields.Integer(description='Ok Result'), 
    'data' : fields.Nested(ApplicationStruct,attribute='data')
}) 

#############################################################################
#############################################################################
#############################################################################

CreateProjectStruct = v1_api.model('CreateProjectStruct', { 
    'name':   fields.String(),
})

ProjectIDStruct = v1_api.model('ProjectIDStruct', { 
    'project_id':   fields.Integer(),
})

#############################################################################

SetPreferredBuyerPersonProjectStruct = v1_api.model('SetPreferredBuyerPersonProjectStruct', { 
    'project_id':   fields.Integer(),
    'buyer_person_id':   fields.Integer(),
})

SaveBuyerPersonProjectStruct = v1_api.model('SaveBuyerPersonProjectStruct', { 
    'project_id':   fields.Integer(),
    'preferred_buyer_person':  fields.Raw()
})

#############################################################################

SetPreferredAudienceProjectStruct = v1_api.model('SetPreferredAudienceProjectStruct', { 
    'project_id':   fields.Integer(),
    'audience_id':   fields.Integer(),
})

SaveAudienceProjectStruct = v1_api.model('SaveAudienceProjectStruct', { 
    'project_id':   fields.Integer(),
    'preferred_audience':  fields.Raw()
})

#############################################################################

SetPreferredCampaignProjectStruct = v1_api.model('SetPreferredCampaignProjectStruct', { 
    'project_id':   fields.Integer(),
    'campaign_id':   fields.Integer(),
})

SaveCampaignProjectStruct = v1_api.model('SaveCampaignProjectStruct', { 
    'project_id':   fields.Integer(),
    'preferred_campaign':  fields.Raw()
})

#############################################################################


SaveMetaAdProjectStruct = v1_api.model('SaveMetaAdProjectStruct', { 
    'project_id':   fields.Integer(),
    'meta_ad':  fields.Raw(),
    'type': fields.String()
})

MetaAdIdStruct = v1_api.model('MetaAdIdStruct', { 
    'project_id':   fields.Integer(),
    'meta_ad_id':   fields.Integer(),
    'type': fields.String()
})

DefineGenerateMetaAdProjectStruct = v1_api.model('DefineGenerateMetaAdProjectStruct', { 
    'project_id': fields.Integer(),
    'type': fields.String()
})

#############################################################################

SetPreferredProductProjectStruct = v1_api.model('SetPreferredProductProjectStruct', { 
    'project_id':   fields.Integer(),
    'product_id':   fields.Integer(),
})

SaveProductProjectStruct = v1_api.model('SaveProductProjectStruct', { 
    'project_id':   fields.Integer(),
    'preferred_product':  fields.Raw()
})

#############################################################################

SetPreferredOptionHypothesisBuilderStruct = v1_api.model('SetPreferredOptionHypothesisBuilderStruct', { 
    'project_id':   fields.Integer(),
    'option_id':   fields.Integer(),
})


SaveHypothesisBuilderOptionsStruct = v1_api.model('SaveHypothesisBuilderOptionsStruct', { 
    'project_id':   fields.Integer(),
    'hypothesis_builder_options':  fields.Raw()
})

#############################################################################

SetPreferredImagePromptBuyerPersonStruct = v1_api.model('SetPreferredImagePromptBuyerPersonStruct', { 
    'project_id':   fields.Integer(),
    'buyer_person_image_prompt_id':   fields.Integer(),
})

GeneratePreferredImagePromptBuyerPersonStruct = v1_api.model('GeneratePreferredImagePromptBuyerPersonStruct', { 
    'prompt':   fields.String() 
})

#############################################################################

SetPreferredImagePromptCampaignStruct = v1_api.model('SetPreferredImagePromptCampaignStruct', { 
    'project_id':   fields.Integer(),
    'campaign_image_prompt_id':   fields.Integer(),
})


#############################################################################

UpdateProjectStatusStruct = v1_api.model('UpdateProjectStatusStruct', { 
    "project_id": fields.Integer(),
    "status": fields.String() 
})

MarketingHypothesisProjectStruct = v1_api.model('MarketingHypothesisProjectStruct', { 
    "project_id": fields.Integer(),
    "marketing_hypothesis": fields.String() 
})

########################################################################################################################

ProductDescriptionStruct = v1_api.model('DefineProductDescriptionStruct', { 
    "project_id": fields.Integer(),
    "brand_name": fields.String(),
    "product_name": fields.String(),
    "product_url": fields.String(),
    "faq_product_url": fields.String()
})

DefineProductAttributesProjectStruct = v1_api.model('DefineProductAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "product_attributes_generated": fields.Raw(),
    "product_attributes_saved": fields.Raw()
})

########################################################################################################################

CreativeConceptDescriptionStruct =  v1_api.model('CreativeConceptDescriptionStruct', {
    "consumer_insight": fields.String(),
    "value_proposition": fields.String(),
    "communication objetive": fields.String(),
    "tone_brand_personality": fields.String(),
    "big_idea": fields.String(),
    "time_frame": fields.String(),
    "target_regions": fields.String()
})

CreativeConceptStruct = v1_api.model('CreativeConceptStruct', { 
    "project_id": fields.Integer(),
    "creative_concept_description" : fields.Nested(CreativeConceptDescriptionStruct),
})

DefineCreativeConceptAttributesProjectStruct = v1_api.model('DefineCreativeConceptAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "creative_concept_attributes_generated": fields.Raw(),
    "creative_concept_attributes_saved": fields.Raw()
})

########################################################################################################################

SetPreferredCreativeConceptProjectStruct = v1_api.model('SetPreferredCreativeConceptProjectStruct', { 
    "project_id": fields.Integer(),
    "c_concept_id": fields.Integer()
})

SavePreferredCreativeConceptProjectStruct = v1_api.model('SavePreferredCreativeConceptProjectStruct', { 
    "project_id": fields.Integer(),
    "preferred_creative_concept": fields.Raw()
})

########################################################################################################################

TargetCustomerDescriptionProjectStruct = v1_api.model('TargetCustomerDescriptionProjectStruct', { 
    "project_id": fields.Integer(),
    "target_customer_description": fields.String() 
})

DefineTargetCustomerAttributesProjectStruct = v1_api.model('DefineTargetCustomerAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "target_customer_attributes_generated": fields.Raw(),
    "target_customer_attributes_saved": fields.Raw()
})

########################################################################################################################

HypothesisElementDescriptionProjectStruct = v1_api.model('HypothesisElementDescriptionProjectStruct', { 
    "project_id": fields.Integer(),
    "hypothesis_element_description": fields.String() 
})

DefineHypothesisElementAttributesProjectStruct = v1_api.model('DefineHypothesisElementAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "hypothesis_element_attributes_generated": fields.Raw(),
    "hypothesis_element_attributes_saved": fields.Raw()
})

########################################################################################################################

GoalDescriptionProjectStruct = v1_api.model('GoalDescriptionProjectStruct', { 
    "project_id": fields.Integer(),
    "goal_description": fields.String() 
})

DefineGoalAttributesProjectStruct = v1_api.model('DefineGoalAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "goal_attributes_generated": fields.Raw(),
    "goal_attributes_saved": fields.Raw()
})

########################################################################################################################

AdvantagesDescriptionProjectStruct = v1_api.model('AdvantagesDescriptionProjectStruct', { 
    "project_id": fields.Integer(),
    "advantages_description": fields.String() 
})

DefineAdvantagesAttributesProjectStruct = v1_api.model('DefineAdvantagesAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "advantages_attributes_generated": fields.Raw(),
    "advantages_attributes_saved": fields.Raw()
})

########################################################################################################################

AdvantagesDescriptionProjectStruct = v1_api.model('AdvantagesDescriptionProjectStruct', { 
    "project_id": fields.Integer(),
    "advantages_description": fields.String() 
})

DefineAdvantagesAttributesProjectStruct = v1_api.model('DefineAdvantagesAttributesProjectStruct', { 
    "project_id": fields.Integer(),
    "advantages_attributes_generated": fields.Raw(),
    "advantages_attributes_saved": fields.Raw()
})

########################################################################################################################


DefineLPHeroElementsProjectStruct = v1_api.model('DefineLPHeroElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_hero_section_generated": fields.Raw(),
    "type": fields.String()
})

DefineLPHeroProjectStruct = v1_api.model('DefineLPHeroProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_hero_section_configured": fields.Raw(),
    "type": fields.String()
})

DefineGenerateLPHeroProjectStruct = v1_api.model('DefineGenerateLPHeroProjectStruct', { 
    "project_id": fields.Integer(),
    "type": fields.String()
})


########################################################################################################################


DefineLPCompetitiveAdvantagesElementsProjectStruct = v1_api.model('DefineLPCompetitiveAdvantagesElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_competitive_advantages_section_generated": fields.Raw(),
    "type": fields.String()
})

DefineLPCompetitiveAdvantagesProjectStruct = v1_api.model('DefineLPCompetitiveAdvantagesProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_competitive_advantages_section_configured": fields.Raw(),
    "type": fields.String()
})

DefineGenerateLPCompetitiveAdvantagesProjectStruct = v1_api.model('DefineGenerateLPCompetitiveAdvantagesProjectStruct', { 
    "project_id": fields.Integer(),
    "type": fields.String()
})

########################################################################################################################


DefineLPHowWeDoElementsProjectStruct = v1_api.model('DefineLPHowWeDoElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_howwedo_section_generated": fields.Raw(),
    "type": fields.String()
})

DefineLPHowWeDoProjectStruct = v1_api.model('DefineLPHowWeDoProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_howwedo_section_configured": fields.Raw(),
    "type": fields.String()
})

DefineGenerateLPHowWeDoProjectStruct = v1_api.model('DefineGenerateLPHowWeDoProjectStruct', { 
    "project_id": fields.Integer(),
    "type": fields.String()
})

########################################################################################################################


DefineLPTestimonialElementsProjectStruct = v1_api.model('DefineLPTestimonialElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_testimonial_section_generated": fields.Raw(),
    "type": fields.String()
})

DefineLPTestimonialProjectStruct = v1_api.model('DefineLPTestimonialProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_testimonial_section_configured": fields.Raw(),
    "type": fields.String()
})

DefineGenerateLPTestimonialProjectStruct = v1_api.model('DefineGenerateLPTestimonialProjectStruct', { 
    "project_id": fields.Integer(),
    "type": fields.String()
})

########################################################################################################################


DefineLPBenefitsElementsProjectStruct = v1_api.model('DefineLPBenefitsElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_benefits_section_generated": fields.Raw(),
    "type": fields.String()
})

DefineLPBenefitsProjectStruct = v1_api.model('DefineLPBenefitsProjectStruct', { 
    "project_id": fields.Integer(),
    "landing_page_benefits_section_configured": fields.Raw(),
    "type": fields.String()
})

DefineGenerateLPBenefitsProjectStruct = v1_api.model('DefineGenerateLPBenefitsProjectStruct', { 
    "project_id": fields.Integer(),
    "type": fields.String()
})

########################################################################################################################


DefineEmailReminderProjectStruct = v1_api.model('DefineEmailReminderProjectStruct', { 
    "project_id": fields.Integer(),
    "email_reminder_generated": fields.Raw()
})

DefineEmailPainPointsProjectStruct = v1_api.model('DefineEmailPainPointsProjectStruct', { 
    "project_id": fields.Integer(),
    "email_painpoints_generated": fields.Raw()
})

DefineEmailUrgencyProjectStruct = v1_api.model('DefineEmailUrgencyProjectStruct', { 
    "project_id": fields.Integer(),
    "email_urgency_generated": fields.Raw()
})

DefineEmailUseCaseProjectStruct = v1_api.model('DefineEmailUseCaseProjectStruct', { 
    "project_id": fields.Integer(),
    "email_usecase_generated": fields.Raw()
})

DefineEmailOfferProjectStruct = v1_api.model('DefineEmailOfferProjectStruct', { 
    "project_id": fields.Integer(),
    "email_offer_generated": fields.Raw()
})


########################################################################################################################


DefineGenerateWBSchedulingProjectStruct = v1_api.model('DefineGenerateWBSchedulingProjectStruct', { 
    "project_id": fields.Integer(),
    "custom_tone_message": fields.String()
})

DefineWBSchedulingElementsProjectStruct = v1_api.model('DefineWBSchedulingElementsProjectStruct', { 
    "project_id": fields.Integer(),
    "whatsapp_bot_scheduling_generated": fields.Raw()
})

DefineWBSchedulingProjectStruct = v1_api.model('DefineWBSchedulingProjectStruct', { 
    "project_id": fields.Integer(),
    "whatsapp_bot_scheduling_configured": fields.Raw()
})

########################################################################################################################

@application_ns.route('/hiluca/project/whatsapp_bot/scheduling/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateWBScheduling(ProxySecureResource): 
 
    @application_ns.doc('Generate WhatsApp Appointment Scheduling Bot for a Project')
    @v1_api.expect(DefineGenerateWBSchedulingProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/whatsapp_bot/scheduling/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/whatsapp_bot/scheduling/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsWBScheduling(ProxySecureResource): 

    @application_ns.doc('Get Elements for WhatsApp Appointment Scheduling Bot for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/whatsapp_bot/scheduling/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/whatsapp_bot/scheduling/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPHero(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for WhatsApp Appointment Scheduling Bot for a Project')
    @v1_api.expect(DefineWBSchedulingElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/whatsapp_bot/scheduling/elements',payload,True)
        return  response, 200   

    
@application_ns.route('/hiluca/project/whatsapp_bot/scheduling')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPHeroConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for WhatsApp Appointment Scheduling Bot for a Project')
    @v1_api.expect(DefineWBSchedulingProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/whatsapp_bot/scheduling',payload,True)
        return  response, 200   
    

@application_ns.route('/hiluca/project/<project_id>/whatsapp_bot/scheduling')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPHeroConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for WhatsApp Appointment Scheduling Bot for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/whatsapp_bot/scheduling',payload,True)
        return  response, 200

########################################################################################################################

@application_ns.route('/hiluca/project/email/offer/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateEmailOffer(ProxySecureResource): 
 
    @application_ns.doc('Generate Email Offer for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/offer/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/email/offer')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetEmailOffer(ProxySecureResource): 

    @application_ns.doc('Get Email Offer for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/email/offer',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/email/offer')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveEmailOffer(ProxySecureResource): 
 
    @application_ns.doc('Save Email Offer for a Project')
    @v1_api.expect(DefineEmailOfferProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/offer',payload,True)
        return  response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/email/urgency/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateEmailUrgency(ProxySecureResource): 
 
    @application_ns.doc('Generate Email Urgency for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/urgency/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/email/urgency')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetEmailUrgency(ProxySecureResource): 

    @application_ns.doc('Get Email Urgency for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/email/urgency',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/email/urgency')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveEmailUrgency(ProxySecureResource): 
 
    @application_ns.doc('Save Email Urgency for a Project')
    @v1_api.expect(DefineEmailUrgencyProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/urgency',payload,True)
        return  response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/email/usecase/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateEmailUseCase(ProxySecureResource): 
 
    @application_ns.doc('Generate Email UseCase for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/usecase/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/email/usecase')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetEmailUseCase(ProxySecureResource): 

    @application_ns.doc('Get Email UseCase for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/email/usecase',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/email/usecase')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveEmailUseCase(ProxySecureResource): 
 
    @application_ns.doc('Save Email UseCase for a Project')
    @v1_api.expect(DefineEmailUseCaseProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/usecase',payload,True)
        return  response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/email/painpoints/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateEmailPainPoints(ProxySecureResource): 
 
    @application_ns.doc('Generate Email PainPoints for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/painpoints/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/email/painpoints')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetEmailPainPoints(ProxySecureResource): 

    @application_ns.doc('Get Email PainPoints for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/email/painpoints',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/email/painpoints')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveEmailPainPoints(ProxySecureResource): 
 
    @application_ns.doc('Save Email PainPoints for a Project')
    @v1_api.expect(DefineEmailPainPointsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/painpoints',payload,True)
        return  response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/email/reminder/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateEmailReminder(ProxySecureResource): 
 
    @application_ns.doc('Generate Email Reminder for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/reminder/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/email/reminder')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetEmailReminder(ProxySecureResource): 

    @application_ns.doc('Get Email Reminder for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/email/reminder',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/email/reminder')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveEmailReminder(ProxySecureResource): 
 
    @application_ns.doc('Save Email Reminder for a Project')
    @v1_api.expect(DefineEmailReminderProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/email/reminder',payload,True)
        return  response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/landing_page/benefits/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateLPBenefits(ProxySecureResource): 
 
    @application_ns.doc('Generate Landing Page  Benefits for a Project')
    @v1_api.expect(DefineGenerateLPBenefitsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/benefits/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/benefits/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsLPBenefits(ProxySecureResource): 

    @application_ns.doc('Get Elements for Landing Page Benefits for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/benefits/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/landing_page/benefits/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPBenefits(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for Landing Page Benefits for a Project')
    @v1_api.expect(DefineLPBenefitsElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/benefits/elements',payload,True)
        return  response, 200    
    
@application_ns.route('/hiluca/project/landing_page/benefits')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPBenefitsConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for Landing Page Benefits for a Project')
    @v1_api.expect(DefineLPBenefitsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/benefits',payload,True)
        return  response, 200    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/benefits')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPBenefitsConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for Landing Page Benefits  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/benefits',payload,True)
        return  response, 200


########################################################################################################################

@application_ns.route('/hiluca/project/landing_page/testimonial/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateLPTestimonial(ProxySecureResource): 
 
    @application_ns.doc('Generate Landing Page  Testimonial for a Project')
    @v1_api.expect(DefineGenerateLPTestimonialProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/testimonial/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/testimonial/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsLPTestimonial(ProxySecureResource): 

    @application_ns.doc('Get Elements for Landing Page Testimonial for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/testimonial/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/landing_page/testimonial/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPTestimonial(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for Landing Page Testimonial for a Project')
    @v1_api.expect(DefineLPTestimonialElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/testimonial/elements',payload,True)
        return  response, 200    
    
@application_ns.route('/hiluca/project/landing_page/testimonial')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPTestimonialConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for Landing Page Testimonial for a Project')
    @v1_api.expect(DefineLPTestimonialProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/testimonial',payload,True)
        return  response, 200    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/testimonial')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPTestimonialConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for Landing Page Testimonial  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/testimonial',payload,True)
        return  response, 200


########################################################################################################################

@application_ns.route('/hiluca/project/landing_page/howwedo/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateLPHowWeDo(ProxySecureResource): 
 
    @application_ns.doc('Generate Landing Page  HowWeDo for a Project')
    @v1_api.expect(DefineGenerateLPHowWeDoProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/howwedo/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/howwedo/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsLPHowWeDo(ProxySecureResource): 

    @application_ns.doc('Get Elements for Landing Page HowWeDo for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/howwedo/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/landing_page/howwedo/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPHowWeDo(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for Landing Page HowWeDo for a Project')
    @v1_api.expect(DefineLPHowWeDoElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/howwedo/elements',payload,True)
        return  response, 200    
    
@application_ns.route('/hiluca/project/landing_page/howwedo')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPHowWeDoConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for Landing Page HowWeDo for a Project')
    @v1_api.expect(DefineLPHowWeDoProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/howwedo',payload,True)
        return  response, 200    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/howwedo')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPHowWeDoConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for Landing Page HowWeDo  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/howwedo',payload,True)
        return  response, 200


########################################################################################################################

@application_ns.route('/hiluca/project/landing_page/competitive_advantages/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateLPCompetitiveAdvantages(ProxySecureResource): 
 
    @application_ns.doc('Generate Landing Page Competitive Advantages for a Project')
    @v1_api.expect(DefineGenerateLPCompetitiveAdvantagesProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/competitive_advantages/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/competitive_advantages/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsLPCompetitiveAdvantages(ProxySecureResource): 

    @application_ns.doc('Get Elements for Landing Page Competitive Advantages for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/competitive_advantages/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/landing_page/competitive_advantages/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPCompetitiveAdvantages(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for Landing Page Competitive Advantages for a Project')
    @v1_api.expect(DefineLPCompetitiveAdvantagesElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/competitive_advantages/elements',payload,True)
        return  response, 200    
    
@application_ns.route('/hiluca/project/landing_page/competitive_advantages')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPCompetitiveAdvantagesConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for Landing Page Competitive Advantages for a Project')
    @v1_api.expect(DefineLPCompetitiveAdvantagesProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/competitive_advantages',payload,True)
        return  response, 200    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/competitive_advantages')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPCompetitiveAdvantagesConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for Landing Page Competitive Advantages  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/competitive_advantages',payload,True)
        return  response, 200


########################################################################################################################

@application_ns.route('/hiluca/project/landing_page/hero/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateLPHero(ProxySecureResource): 
 
    @application_ns.doc('Generate Landing Page Hero for a Project')
    @v1_api.expect(DefineGenerateLPHeroProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/hero/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/hero/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetElementsLPHero(ProxySecureResource): 

    @application_ns.doc('Get Elements for Landing Page Hero  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/hero/elements',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/landing_page/hero/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveElementsLPHero(ProxySecureResource): 
 
    @application_ns.doc('Save Elements for Landing Page Hero for a Project')
    @v1_api.expect(DefineLPHeroElementsProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/hero/elements',payload,True)
        return  response, 200    
    
@application_ns.route('/hiluca/project/landing_page/hero')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveLPHeroConfiguration(ProxySecureResource): 
 
    @application_ns.doc('Save Configuration for Landing Page Hero for a Project')
    @v1_api.expect(DefineLPHeroProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/landing_page/hero',payload,True)
        return  response, 200    

@application_ns.route('/hiluca/project/<project_id>/landing_page/type/<type>/hero')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetLPHeroConfiguration(ProxySecureResource): 

    @application_ns.doc('Get Configuration for Landing Page Hero  for a Project')
    @jwt_required     
    def get(self,project_id, type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/landing_page/hero',payload,True)
        return  response, 200


########################################################################################################################

@application_ns.route('/hiluca/project/meta_ads/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateMetaAds(ProxySecureResource): 
 
    @application_ns.doc('Generate Meta Ads for a Project')
    @v1_api.expect(DefineGenerateMetaAdProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/meta_ads/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/<project_id>/type/<type>/meta_ads')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetAllMetaAds(ProxySecureResource): 

    @application_ns.doc('Get All Meta Ads for a Project')
    @jwt_required     
    def get(self,project_id,type):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'type' : type }
        response = n8nClient.executeGet('/webhook/project/meta_ads',payload,True)
        return  response, 200

@application_ns.route('/hiluca/project/meta_ad')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveMetaAd(ProxySecureResource): 
 
    @application_ns.doc('Save Meta Ad for a Project')
    @v1_api.expect(SaveMetaAdProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/meta_ad',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/type/<type>/meta_ad/<meta_ad_id>')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetMetaAd(ProxySecureResource): 

    @application_ns.doc('Get Meta Ad for a Project')
    @jwt_required     
    def get(self,project_id,type,meta_ad_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id, 'meta_ad_id' : meta_ad_id, 'type' : type}
        response = n8nClient.executeGet('/webhook/project/meta_ad',payload,True)
        return  response, 200

@application_ns.route('/hiluca/project/meta_ad/image/prompts/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateImagePromptsMetaAd(ProxySecureResource): 
 
    @application_ns.doc('Generate Images from Meta Ad in a Project')
    @v1_api.expect(MetaAdIdStruct)        
    @jwt_required      
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/meta_ad/image/prompts/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/type/<type>/meta_ad/<meta_ad_id>/image')
@v1_api.expect(secureHeader)
class HilucaResourceSaveImageMetaAd(ProxySecureResource): 
 
    @application_ns.doc('Save Image from Meta Ad')
    @jwt_required    
    def post(self,project_id,type,meta_ad_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = {'project_id' : project_id, 'meta_ad_id' : meta_ad_id, 'type' : type}
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/project/meta_ad/image',{},True,is_binary=False,params=params,files=files)

        return response, 200    
    

@application_ns.route('/hiluca/project/<project_id>/type/<type>/meta_ad/<meta_ad_id>/image')
@v1_api.expect(secureHeader)
class HilucaResourceGetImageMetaAd(ProxySecureResource): 
 
    @application_ns.doc('Get Image from Meta Ad')
    @jwt_required    
    def get(self,project_id,type,meta_ad_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id, 'meta_ad_id' : meta_ad_id, 'type' : type} 

        response = n8nClient.executeGet('/webhook/project/meta_ad/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])        



########################################################################################################################

@application_ns.route('/hiluca/project/preferred_campaign/image/prompts/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateImagePromptsCampaign(ProxySecureResource): 
 
    @application_ns.doc('Generate Images from Preferred Campaign in a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required      
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_campaign/image/prompts/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/preferred_campaign/image/prompts/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredImagePromptsCampaign(ProxySecureResource): 
 
    @application_ns.doc('Setting Preferred Image Prompt for Preferred Campaign in a Project')
    @v1_api.expect(SetPreferredImagePromptCampaignStruct )        
    @jwt_required      
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_campaign/image/prompts/set_preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/preferred_campaign/image/prompts')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSelectedImagePromptCampaign(ProxySecureResource): 
 
    @application_ns.doc('Get Image Prompts from Preferred Campaign in a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/preferred_campaign/image/prompts',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/creative_concept/description')
@v1_api.expect(secureHeader)
class HilucaResourceCreativeConceptDescriptionProject(ProxySecureResource): 
 
    @application_ns.doc('Define Creative Concept Description in a Project')
    @v1_api.expect(CreativeConceptStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/creative_concept/description',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/creative_concept/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceCreativeConceptAttributesProject(ProxySecureResource): 
 
    @application_ns.doc('Define Creative Concept Attributes in a Project')
    @v1_api.expect(DefineCreativeConceptAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/creative_concept/attributes',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/creative_concept/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectCreativeConcept(ProxySecureResource): 
 
    @application_ns.doc('Generate Creative Concepts in a Project')
    @v1_api.expect(ProjectIDStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/creative_concept/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/creative_concept/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredCreativeConcept(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Creative Concept for a Project')
    @v1_api.expect(SetPreferredCreativeConceptProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/creative_concept/set_preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/creative_concept/preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSavePreferredCreativeConcept(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Creative Concept for a Project')
    @v1_api.expect(SavePreferredCreativeConceptProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/creative_concept/preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/creative_concept/preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetPreferredCreativeConcept(ProxySecureResource): 

    @application_ns.doc('Get Preferred Creative Concept for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}
        response = n8nClient.executeGet('/webhook/project/creative_concept/preferred',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/campaign/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateCampaign(ProxySecureResource): 
 
    @application_ns.doc('Generate Campaign for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/campaign/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/campaign/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredCampaign(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Campaign for a Project')
    @v1_api.expect(SetPreferredCampaignProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/campaign/set_preferred',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/preferred_campaign')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSavePreferredCampaign(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Campaign for a Project')
    @v1_api.expect(SaveCampaignProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_campaign',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/preferred_campaign')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetPreferredCampaign(ProxySecureResource): 

    @application_ns.doc('Get Preferred Campaign for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}
        response = n8nClient.executeGet('/webhook/project/preferred_campaign',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/audience/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateAudience(ProxySecureResource): 
 
    @application_ns.doc('Generate Audience for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/audience/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/audience/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredAudience(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Audience for a Project')
    @v1_api.expect(SetPreferredAudienceProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/audience/set_preferred',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/preferred_audience')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSavePreferredAudience(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Audience for a Project')
    @v1_api.expect(SaveAudienceProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_audience',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/preferred_audience')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetPreferredAudience(ProxySecureResource): 

    @application_ns.doc('Get Preferred Audience for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}
        response = n8nClient.executeGet('/webhook/project/preferred_audience',payload,True)
        return  response, 200


########################################################################################################################

from io import StringIO,BytesIO

@application_ns.route('/hiluca/image')
@v1_api.expect(secureHeader)
class HilucaResourceGenerateImageFromPrompt(ProxySecureResource): 
 
    @application_ns.doc('Generate Image using a Prompt')
    @v1_api.expect(GeneratePreferredImagePromptBuyerPersonStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        print(payload)
        response = n8nClient.executePost('/webhook/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])       

########################################################################################################################

@application_ns.route('/hiluca/project/<project_id>/campaign/image')
@v1_api.expect(secureHeader)
class HilucaResourceSaveImageCampaign(ProxySecureResource): 
 
    @application_ns.doc('Save Image from Campaign')
    @jwt_required    
    def post(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = {'project_id' : project_id}
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/project/campaign/image',{},True,is_binary=False,params=params,files=files)

        return response, 200    
    
@application_ns.route('/hiluca/project/<project_id>/campaign/image')
@v1_api.expect(secureHeader)
class HilucaResourceGetImageCampaign(ProxySecureResource): 
 
    @application_ns.doc('Get Image from Buyer Person')
    @jwt_required    
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id } 

        response = n8nClient.executeGet('/webhook/project/campaign/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])        


########################################################################################################################

@application_ns.route('/hiluca/project/<project_id>/buyer_person/image')
@v1_api.expect(secureHeader)
class HilucaResourceGetImageBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Get Image from Buyer Person')
    @jwt_required    
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id } 
        print(payload)
        response = n8nClient.executeGet('/webhook/project/buyer_person/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])        
    
import base64

@application_ns.route('/hiluca/project/<project_id>/buyer_person/image')
@v1_api.expect(secureHeader)
class HilucaResourceSaveImageBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Save Image from Buyer Person')
    @jwt_required    
    def post(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = {'project_id' : project_id}
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/project/buyer_person/image',{},True,is_binary=False,params=params,files=files)

        return response, 200    


########################################################################################################################

@application_ns.route('/hiluca/project/<project_id>/product/image')
@v1_api.expect(secureHeader)
class HilucaResourceSaveImageProduct(ProxySecureResource): 
 
    @application_ns.doc('Save Image from Product')
    @jwt_required    
    def post(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = {'project_id' : project_id}
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/project/product/image',{},True,is_binary=False,params=params,files=files)

        return response, 200    


@application_ns.route('/hiluca/project/<project_id>/product/image')
@v1_api.expect(secureHeader)
class HilucaResourceGetImageProduct(ProxySecureResource): 
 
    @application_ns.doc('Get Image from Product')
    @jwt_required    
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'project_id' : project_id } 
        print(payload)
        response = n8nClient.executeGet('/webhook/project/product/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])        


########################################################################################################################

@application_ns.route('/hiluca/project/refination')
@v1_api.expect(secureHeader)
class HilucaResourceProjectRefination(ProxySecureResource): 
 
    @application_ns.doc('Init Project Refination')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/refination',payload,True)
        return  response, 200

########################################################################################################################

@application_ns.route('/hiluca/project/buyer_person/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Generate Buyer Person for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/buyer_person/generate',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/buyer_person/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Buyer Person for a Project')
    @v1_api.expect(SetPreferredBuyerPersonProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/buyer_person/set_preferred',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/preferred_buyer_person')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSavePreferredBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Buyer Person for a Project')
    @v1_api.expect(SaveBuyerPersonProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_buyer_person',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/preferred_buyer_person')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetPreferredBuyerPerson(ProxySecureResource): 

    @application_ns.doc('Get Preferred Buyer Person for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}
        response = n8nClient.executeGet('/webhook/project/preferred_buyer_person',payload,True)
        return  response, 200

########################################################################################################################

@application_ns.route('/hiluca/project/product/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateProduct(ProxySecureResource): 
 
    @application_ns.doc('Generate Product for a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/product/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/product/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredProduct(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Product for a Project')
    @v1_api.expect(SetPreferredProductProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/product/set_preferred',payload,True)
        return  response, 200
    

@application_ns.route('/hiluca/project/preferred_product')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSavePreferredProduct(ProxySecureResource): 
 
    @application_ns.doc('Save Preferred Product for a Project')
    @v1_api.expect(SaveProductProjectStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_product',payload,True)
        return  response, 200
    
@application_ns.route('/hiluca/project/<project_id>/preferred_product')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetPreferredProduct(ProxySecureResource): 
 
    @application_ns.doc('Get Preferred Product for a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}
        response = n8nClient.executeGet('/webhook/project/preferred_product',payload,True)
        return  response, 200

########################################################################################################################

@application_ns.route('/hiluca/project/<project_id>/hypothesis_builder/elements')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetHypothesisBuilderElements(ProxySecureResource): 
 
    @application_ns.doc('Get Hypothesis Builder Elements')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id}   
        response = n8nClient.executeGet('/webhook/project/hypothesis_builder/elements',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/hypothesis_builder/options')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSaveHypothesisBuilderOptions(ProxySecureResource): 
 
    @application_ns.doc('Save Available Options in Hypothesis Builder of a Project')
    @v1_api.expect(SaveHypothesisBuilderOptionsStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/hypothesis_builder/options',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/hypothesis_builder/options/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredOptionHypothesisBuilder(ProxySecureResource): 
 
    @application_ns.doc('Set Preferred Option in Hypothesis Builder of a Project')
    @v1_api.expect(SetPreferredOptionHypothesisBuilderStruct)        
    @jwt_required     
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/hypothesis_builder/options/set_preferred',payload,True)
        return  response, 200

@application_ns.route('/hiluca/project/<project_id>/hypothesis_builder/options')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGetOptionsHypothesisBuilder(ProxySecureResource): 
 
    @application_ns.doc('Get Options in Hypothesis Builder of a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/hypothesis_builder/options',payload,True)
        return  response, 200
    
########################################################################################################################

@application_ns.route('/hiluca/project/preferred_buyer_person/image/prompts/generate')
@v1_api.expect(secureHeader)
class HilucaResourceProjectGenerateImagePromptsBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Generate Images from Preferred Buyer Person in a Project')
    @v1_api.expect(ProjectIDStruct)        
    @jwt_required      
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_buyer_person/image/prompts/generate',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/preferred_buyer_person/image/prompts/set_preferred')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSetPreferredImagePromptsBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Setting Preferred Image Prompt for Preferred Buyer Person in a Project')
    @v1_api.expect(SetPreferredImagePromptBuyerPersonStruct)        
    @jwt_required      
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/preferred_buyer_person/image/prompts/set_preferred',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>/preferred_buyer_person/image/prompts')
@v1_api.expect(secureHeader)
class HilucaResourceProjectSelectedImagePromptBuyerPerson(ProxySecureResource): 
 
    @application_ns.doc('Get Image Prompts from Preferred Buyer Person in a Project')
    @jwt_required     
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {'project_id' : project_id }
        response = n8nClient.executeGet('/webhook/project/preferred_buyer_person/image/prompts',payload,True)
        return  response, 200



########################################################################################################################

@application_ns.route('/hiluca/project')
@v1_api.expect(secureHeader)
class HilucaResourceCreateProject(ProxySecureResource): 
 
    @application_ns.doc('Create a Project')
    @v1_api.expect(CreateProjectStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project',payload,True)
        return  response, 200
    
    @application_ns.doc('Get a Project List from a Account')
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = {} 
        response = n8nClient.executeGet('/webhook/project',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/<project_id>')
@v1_api.expect(secureHeader)
class HilucaResourceGetProject(ProxySecureResource): 
 
    @application_ns.doc('Get a Project')
    @jwt_required    
    def get(self,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        current_project_id = 0 
        if not project_id is None:
            current_project_id = project_id
        response = n8nClient.executeGet(end_point=f'/webhook/193b2a9b-db90-41b3-91e2-789f36bdbc62/project/{current_project_id}',authenticate=True)
        return  response, 200


@application_ns.route('/hiluca/project/status')
@v1_api.expect(secureHeader)
class HilucaResourceUpdateStatusProject(ProxySecureResource): 
 
    @application_ns.doc('Update Project Status')
    @v1_api.expect(UpdateProjectStatusStruct)        
    @jwt_required    
    def put(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost(end_point=f'/webhook/project/status',payload=payload,authenticate=True)
        return  response, 200
    

@application_ns.route('/hiluca/project/marketing-hypothesis')
@v1_api.expect(secureHeader)
class HilucaResourceMarketingHypothesisProject(ProxySecureResource): 
 
    @application_ns.doc('Define Marketing Hypothesis in a Project')
    @v1_api.expect(MarketingHypothesisProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/marketing-hypothesis',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/product/description')
@v1_api.expect(secureHeader)
class HilucaResourceProductDescriptionProject(ProxySecureResource): 
 
    @application_ns.doc('Define Product Description in a Project')
    @v1_api.expect(ProductDescriptionStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/product/description',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/product/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceProductAttributesProject(ProxySecureResource): 
 
    @application_ns.doc('Define Product Attributes in a Project')
    @v1_api.expect(DefineProductAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/product/attributes',payload,True)
        return  response, 200


########################################################################################################################


@application_ns.route('/hiluca/project/target_customer/description')
@v1_api.expect(secureHeader)
class HilucaResourceTargetCustomerDescriptionProject(ProxySecureResource): 
 
    @application_ns.doc('Define Target Customer Description in a Project')
    @v1_api.expect(TargetCustomerDescriptionProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/target_customer/description',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/target_customer/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceTargetCustomerAttributesProject(ProxySecureResource): 
 
    @application_ns.doc('Define Target Customer Attributes in a Project')
    @v1_api.expect(DefineTargetCustomerAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/target_customer/attributes',payload,True)
        return  response, 200

########################################################################################################################
    
@application_ns.route('/hiluca/project/hypothesis/description')
@v1_api.expect(secureHeader)
class HilucaResourceHypothesisDescriptionProject(ProxySecureResource):  
    
    @application_ns.doc('Define Hypothesis Description to Extract Elements')
    @v1_api.expect(HypothesisElementDescriptionProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/hypothesis_element/description',payload,True)
        return  response, 200

    
@application_ns.route('/hiluca/project/hypothesis/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceHypothesisAttributesProject(ProxySecureResource): 

    @application_ns.doc('Define Hypothesis Attributes in a Project')
    @v1_api.expect(DefineHypothesisElementAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/hypothesis_element/attributes',payload,True)
        return  response, 200

########################################################################################################################

@application_ns.route('/hiluca/project/goal/description')
@v1_api.expect(secureHeader)
class HilucaResourceGoalDescriptionProject(ProxySecureResource):  

    @application_ns.doc('Define Goal Description in a Project')
    @v1_api.expect(GoalDescriptionProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/goal/description',payload,True)
        return  response, 200
    
@application_ns.route('/hiluca/project/goal/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceGoalAttributesProject(ProxySecureResource):  

    @application_ns.doc('Define Goal Attributes in a Project')
    @v1_api.expect(DefineGoalAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/goal/attributes',payload,True)
        return  response, 200
    

########################################################################################################################


@application_ns.route('/hiluca/project/advantages/description')
@v1_api.expect(secureHeader)
class HilucaResourceAdvantagesDescriptionProject(ProxySecureResource): 
 
    @application_ns.doc('Define Advantages Description in a Project')
    @v1_api.expect(AdvantagesDescriptionProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/advantages/description',payload,True)
        return  response, 200


@application_ns.route('/hiluca/project/advantages/attributes')
@v1_api.expect(secureHeader)
class HilucaResourceAdvantagesAttributesProject(ProxySecureResource): 
 
    @application_ns.doc('Define Advantages Attributes in a Project')
    @v1_api.expect(DefineAdvantagesAttributesProjectStruct)         
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/project/advantages/attributes',payload,True)
        return  response, 200

#############################################################################
#############################################################################
#############################################################################

@application_ns.route('/')
@v1_api.expect(secureHeader)
class AppSettingsResource(ProxySecureResource): 
    @application_ns.doc('Application Settings')
    @v1_api.marshal_with(GetOneApplicationStruct)        
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        data = GetApplicationUseCase().execute(security_credentials)
        return  {'ok' : 1, 'data': data}, 200

@application_ns.route('/coin')
@v1_api.expect(secureHeader)
class CoinSettingsResource(ProxySecureResource): 
 
    @application_ns.doc('Coin Settings')
    @v1_api.marshal_with(GetOneCoinStruct)            
    @jwt_required    
    def get(self):
        security_credentials = self.checkCredentials()
        data = GetDefaultCoinUseCase().execute(security_credentials)
        return  {'ok' : 1, 'data': data}, 200


@application_ns.route('/coin/<symbol>')
@application_ns.param('symbol', 'Coin Symbol')
@v1_api.expect(secureHeader)
class GetCoinResource(ProxySecureResource): 
 
    @application_ns.doc('Get Coin By Symbol')
    @v1_api.marshal_with(GetOneCoinStruct) 
    @jwt_required    
    def get(self,symbol):
        security_credentials = self.checkCredentials()
        query_params = { 'symbol':  symbol}
        data = GetCoinBySymbolUseCase().execute(security_credentials,query_params)
        return  {'ok' : 1, 'data': data}, 200

