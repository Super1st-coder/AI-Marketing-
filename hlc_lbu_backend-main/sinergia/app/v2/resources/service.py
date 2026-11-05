"""Service endpoints for trusted internal callers (e.g. Fury).

These endpoints are protected by X-Service-API-Key and query Strapi
directly, bypassing the JWT + n8n flow used by the frontend.

Base path: /api/v2/service/
"""
import logging
from flask_restplus import Resource
from app.v2 import v2_api
from app.tools.service_auth import service_api_key_required
from app.tools.strapi import StrapiClient
from app.v2.use_cases.ad_set import GetAdSetUseCase, SaveAdsVariantsFuryUseCase
from app.v2.use_cases.media_platform_project import GetMediaPlatformTemplatesFuryUseCase, GetAbyssaleTemplateFuryUseCase
from app.v2.use_cases.image_library import GetProductImagesUseCase, UploadImageFuryUseCase, GetAdVariantImageUseCase
from app.v2.use_cases.cta import GetCtasUseCase
from app.v2.use_cases.ad import UpdateAdChannelGenerationFuryUseCase, DeleteAdsVariantsFuryUseCase
from app.v2.use_cases.buyer_person import GetBuyerPersonUseCase, UploadMainImageBuyerPersonUseCase, GetAMainImageUseCase, UploadVariantImageBuyerPersonUseCase, GetAVariantImageFuryToolUseCase
from app.v2.use_cases.product import GetProductUseCase
from flask.globals import request

logger = logging.getLogger(__name__)

service_ns = v2_api.namespace('service', description='Internal service-to-service API')


# ---------------------------------------------------------------------------
# Buyer Person Context
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/buyer_persona/<int:id_buyer_person>')
class ServiceBPersonContext(Resource):

    @service_api_key_required
    def get(self, id_buyer_person):
        data = GetBuyerPersonUseCase().execute(id_buyer_person)
        return {'ok': True, 'data': data}, 200
    

# ---------------------------------------------------------------------------
# Buyer Person Main Image Upload
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/buyer_persona/<int:id_buyer_person>/image/upload')
class ServiceBPersonMainImageUpload(Resource):

    @service_api_key_required
    def post(self, id_buyer_person):
        payload = request.json
        data = UploadMainImageBuyerPersonUseCase().execute(id_buyer_person, payload)
        return {'ok': True, 'data': data}, 200
    

# ---------------------------------------------------------------------------
# Buyer Person Variant Image Upload
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/buyer_persona/<int:id_buyer_person>/image/<string:id_base_image>/variant/upload')
class ServiceBPersonVariantImageUpload(Resource):

    @service_api_key_required
    def post(self, id_buyer_person, id_base_image):
        payload = request.json
        data = UploadVariantImageBuyerPersonUseCase().execute(id_buyer_person, id_base_image, payload)
        return {'ok': True, 'data': data}, 200


# ---------------------------------------------------------------------------
# Product Context
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/product/<int:id_product>')
class ServiceProductContext(Resource):

    @service_api_key_required
    def get(self, id_product):
        data = GetProductUseCase().execute(id_product)
        return {'ok': True, 'data': data}, 200
    

# ---------------------------------------------------------------------------
# Ad Set
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/adset/<int:id_adset>')
class ServiceAdSet(Resource):

    @service_api_key_required
    def get(self, id_adset):
        data = GetAdSetUseCase().execute(id_adset)
        return {'ok': True, 'data': data}, 200


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/media_platform/<string:project_id>/templates')
class ServiceTemplates(Resource):

    @service_api_key_required
    def get(self,project_id):
        data = GetMediaPlatformTemplatesFuryUseCase().execute(project_id)
        return {'ok' : True, 'data': data }, 200



# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/template/<string:template_id>')
class ServiceTemplate(Resource):

    @service_api_key_required
    def get(self,template_id):
        data = GetAbyssaleTemplateFuryUseCase().execute(template_id)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Image Library
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/product/<product_id>/images')
class ServiceImageLibrary(Resource):

    @service_api_key_required
    def get(self,product_id):
        data = GetProductImagesUseCase().execute(product_id)
        return {'ok' : True, 'data': data }, 200



# ---------------------------------------------------------------------------
# Save Ads
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/adset/<int:id_adset>/ads')
class ServiceSaveAds(Resource):

    @service_api_key_required
    def post(self,id_adset):
        payload = request.json
        data = SaveAdsVariantsFuryUseCase().execute(id_adset, payload)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Delete Variants
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/variants/delete')
class ServiceDeleteVariants(Resource):

    @service_api_key_required
    def post(self):
        payload = request.json
        data = DeleteAdsVariantsFuryUseCase().execute(payload)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# CTAs 
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/cta')
class ServiceCTAs(Resource):

    @service_api_key_required
    def get(self):
        data = GetCtasUseCase().execute()
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Update Ads
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/ad/<id_ad>/update_channel')
class ServiceUpdateAdChannel(Resource):

    @service_api_key_required
    def post(self,id_ad):
        payload = request.json
        data = UpdateAdChannelGenerationFuryUseCase().execute(id_ad, payload)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Upload Image To Library
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/ad/<id_ad>/image/upload')
class ServiceUploadImage(Resource):

    @service_api_key_required
    def post(self,id_ad):
        payload = request.json
        data = UploadImageFuryUseCase().execute(id_ad,payload)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Brand
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/brand/<string:brand_id>')
class ServiceBrand(Resource):

    @service_api_key_required
    def get(self, brand_id):
        """Get brand guidelines: tone_of_voice, color_palette, do_donts."""
        try:
            strapi = StrapiClient()
            data = strapi.get(
                f"brands/{brand_id}",
                params={"populate": "*"}
            )
            return {"ok": True, "brand": data}, 200
        except Exception as e:
            logger.error(f"[service] get_brand brand_id={brand_id} error: {e}")
            return {"ok": False, "error": str(e)}, 500


# ---------------------------------------------------------------------------
# Audiences
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/adset/<string:id_adset>/audiences')
class ServiceAudiences(Resource):

    @service_api_key_required
    def get(self, id_adset):
        """Get audience segments and insights for an Ad Set."""
        try:
            strapi = StrapiClient()
            data = strapi.get(
                "audience-audiences",
                params={
                    "filters[ad_set_ref][$eq]": id_adset,
                    "populate": "ad_set_ref"
                }
            )
            return {"ok": True, "audiences": data}, 200
        except Exception as e:
            logger.error(f"[service] get_audiences adset_id={id_adset} error: {e}")
            return {"ok": False, "error": str(e)}, 500


# ---------------------------------------------------------------------------
# Image Library - Get a Main Image by Buyer Person
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/buyer_persona/<int:buyer_person_id>/image/main/<string:image_id>')
class ServiceBuyerMainImageLibrary(Resource):

    @service_api_key_required
    def get(self, buyer_person_id, image_id):
        data = GetAMainImageUseCase().execute(buyer_person_id, image_id)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Image Library - Get a Variant Image by Buyer Person
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/buyer_persona/<int:buyer_person_id>/image/variant/<string:image_id>')
class ServiceBuyerVariantImageLibrary(Resource):

    @service_api_key_required
    def get(self, buyer_person_id, image_id):
        data = GetAVariantImageFuryToolUseCase().execute(buyer_person_id, image_id)
        return {'ok' : True, 'data': data }, 200


# ---------------------------------------------------------------------------
# Image Library - Get an Ad Variant Image
# ---------------------------------------------------------------------------

@service_ns.route('/hiluca/brand/<int:brand_id>/campaign/<int:campaign_id>/ad/<int:ad_id>/channel/<int:channel_id>/variant/<int:variant_id>/image/<string:image_id>')
class ServiceAdVariantImage(Resource):

    @service_api_key_required
    def get(self, brand_id, campaign_id, ad_id, channel_id, variant_id, image_id):
        data = GetAdVariantImageUseCase().execute(brand_id, campaign_id, ad_id, channel_id, variant_id, image_id)
        return {'ok': True, 'data': data}, 200
