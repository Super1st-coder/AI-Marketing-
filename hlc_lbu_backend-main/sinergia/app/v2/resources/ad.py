from io import BytesIO
from app.v2 import v2_api
from app.v2.use_cases.ad import SelectAdUseCase, DeleteAdUseCase, GenerateAnAdVariantUseCase, GenerateAllAdVariantUseCase, AbyssaleVisualEditUseCase, PinFormatAdVariantUseCase, UnpinFormatAdVariantUseCase, EditAdVariantImageUseCase
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.models.constant import FUNCTION_FUNNEL_FLOW, ACTION_UPDATE, ROLE_HILUCA_ADMIN, ACTION_READ, FUNCTION_APPROVAL_PROCESS, ACTION_CREATE
from app.v1.repository.base import N8NClient
from app.tools.permissions import check_access
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from flask import send_file, Response

ad_ns = v2_api.namespace('application', description='Aplication Services')

SetMediaTemplateAdStruct = v2_api.model('SetMediaTemplateAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'media_template_id': fields.String(),
    'media_platform_project_id': fields.String()
})

SaveMediaElementsAdStruct = v2_api.model('SaveMediaElementsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'elements': fields.List(fields.Raw())
})

SetImageStyleAdStruct = v2_api.model('SetImageStyleAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'image_style_id': fields.Integer()
})

GenerateMediaImageAttributesAdStruct = v2_api.model('GenerateMediaImageAttributesAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'elements': fields.List(fields.Raw())
})

SaveMediaImageAttributesAdStruct = v2_api.model('SaveMediaImageAttributesAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'image_attributes_generated': fields.Raw(),
    'image_attributes_saved': fields.Raw()
})

GenerateMediaImagePromptsAdStruct = v2_api.model('GenerateMediaImagePromptsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'elements': fields.List(fields.Raw())
})

SetPreferredMediaImagePromptsAdStruct = v2_api.model('SetPreferredMediaImagePromptsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'image_prompt_id': fields.Integer()
})

SavePreferredMediaImagePromptsAdStruct = v2_api.model('SavePreferredMediaImagePromptsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'preferred_image_prompt': fields.Raw()
})

UploadMediaImageIDAdStruct = v2_api.model('UploadMediaImageIDAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'image_id': fields.String()
})

GenerateTextsMediaElementsAdStruct = v2_api.model('GenerateTextsMediaElementsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'elements': fields.List(fields.Raw())
})

GenerateTextMediaElementsAdStruct = v2_api.model('GenerateTextMediaElementsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'elements': fields.List(fields.Raw())
})

SaveChannelAttributesAdStruct = v2_api.model('SaveChannelAttributesAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'attributes': fields.List(fields.Raw())
})

SaveChannelRedirectUrlAdStruct = v2_api.model('SaveChannelRedirectUrlAdStruct', {
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'redirect_url': fields.String()
})

GenerateTextsChannelAttributesAdStruct = v2_api.model('GenerateTextsChannelAttributesAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'attributes': fields.List(fields.Raw())
})

GenerateTextChannelAttributesAdStruct = v2_api.model('GenerateTextChannelAttributesAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'attribute': fields.Raw()
})

GenerateMediaVisualsAdStruct = v2_api.model('GenerateMediaVisualsAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'elements': fields.List(fields.Raw())
})

UpdateAdStruct = v2_api.model('UpdateAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'name': fields.String()
})

AbyssaleHooktMarketingAssetStruct = v2_api.model('AbyssaleHooktMarketingAssetStruct', { 
    'generation_request_id': fields.String(),
    'banners': fields.List(fields.Raw()),
    'errors': fields.List(fields.Raw())
})

SelectAdStruct = v2_api.model('SelectAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer()
})

DeleteAdStruct = v2_api.model('DeleteAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer()
})

GenerateAnAdStruct = v2_api.model('GenerateAnAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'add_variant': fields.Boolean(),
    'custom_prompt': fields.String()
})

GenerateAllAdStruct = v2_api.model('GenerateAllAdStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'add_variant': fields.Boolean(),
    'custom_prompt': fields.String(),
    'n_variants': fields.Integer()
})

PinFormatAdVariantStruct = v2_api.model('PinFormatAdVariantStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'format_id': fields.String()
})

UnpinFormatAdVariantStruct = v2_api.model('UnpinFormatAdVariantStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer()
})

EditAdVariantImageStruct = v2_api.model('EditAdVariantImageStruct', {
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'channel_id': fields.Integer(),
    'variant_id': fields.Integer(),
    'image_name': fields.String(),
    'image_id': fields.String(),
    'n_variations': fields.Integer(),
    'custom_prompt': fields.String(),
    'expand_zoom_option': fields.String(
        enum=['TOP', 'BOTTOM', 'LEFT', 'RIGHT', 'ZOOM_2X', 'ZOOM_1_5X', 'ZOOM_1_25X'])
})

@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ads')
@v2_api.expect(secureHeader)
class HilucaResourceAdsGetList(ProxySecureResource): 
 
    @ad_ns.doc('Get All Ads by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id }
        response = n8nClient.executeGet('/webhook/v2/ads',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ads/export')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExport(ProxySecureResource): 
 
    @ad_ns.doc('Export Ads to Excel by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_APPROVAL_PROCESS, ACTION_READ)
    def get(self,brand_id,campaign_id):
        try:
            from app.v2.use_cases.ads_export import ExcelManagerUseCase
            
            export_use_case = ExcelManagerUseCase()
            
            excel_data, filename, status_code = export_use_case.export_to_excel(
                brand_id=int(brand_id), 
                campaign_id=int(campaign_id)
            )
            
            if excel_data is None:
                return {"error": "No data found or export failed"}, status_code or 404
            
            from flask import send_file
            from io import BytesIO
            
            excel_buffer = BytesIO(excel_data)
            excel_buffer.seek(0)
            
            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformattedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=filename
            )
            
        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}, 500

@ad_ns.route('/hiluca/brand/<brand_id>/ads/export_excel')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExport(ProxySecureResource):
    @ad_ns.doc('Export Ads to Excel by Campaign')
    @ad_ns.param('campaigns', 'Lista de IDs de campañas separadas por comas', type=str, required=False)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_APPROVAL_PROCESS, ACTION_READ)
    def get(self, brand_id):
        try:
            from app.v2.use_cases.ads_export_v2 import ExcelManagerUseCaseV2

            export_use_case = ExcelManagerUseCaseV2()

            security_credentials = self.checkCredentials()
            n8nClient = N8NClient(credentials=security_credentials)

            campaigns_param = request.args.get("campaigns")
            campaigns = []

            if campaigns_param:
                campaigns = [c.strip() for c in campaigns_param.split(",") if c.strip()]

            payload = {
                "brand_id": brand_id,
                "campaigns": campaigns,
            }

            response = n8nClient.executeGet('/webhook/v2/campaigns', payload, True)


            excel_bytes, filename, status = export_use_case.export_to_excel(response)

            if status == 200:
                return Response(
                    excel_bytes,
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={
                        "Content-Disposition": f"attachment; filename={filename}"
                    }
                )
            else:
                return {"error": "Error generating Excel"}, 500

        except Exception as e:
            return {"error": f"Export failed: {str(e)}"}, 500

@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ads/import_excel')
@v2_api.expect(secureHeader)
class HilucaResourceAdsImport(ProxySecureResource):
    @ad_ns.doc('Import Ads from Excel by Brand')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_APPROVAL_PROCESS, ACTION_CREATE)
    def post(self, brand_id, campaign_id):
        try:
            from app.v2.use_cases.ads_import import ExcelReaderValidator

            if 'file' not in request.files:
                return {"message": "No se envió ningún archivo."}, 400

            security_credentials = self.checkCredentials()
            n8nClient = N8NClient(credentials=security_credentials)

            file = request.files['file']

            if not file.filename.endswith(('.xlsx', '.xls')):
                return {"message": "Formato inválido. Se requiere un archivo Excel."}, 400

            file_bytes = BytesIO(file.read())

            required_cols = [
                "brand_name",
                "campaign_name",
                "adset_id",
                "adset_name",
                "ad_id",
                "ad_name",
                "ad_channel_id",
                "channel_id",
                "channel_name",
                "media_format_id",
                "dimensions",
                "visual_url_editor",
                "primary_text_1",
                "primary_text_2",
                "primary_text_3",
                "primary_text_4",
                "primary_text_5",
                "headline_1",
                "headline_2",
                "headline_3",
                "headline_4",
                "headline_5",
                "description_1",
                "description_2",
                "description_3",
                "description_4",
                "description_5",
                "cta",
                "status",
                "comments",
            ]

            rules = [
                {"type": "required_field", "field": "brand_name"},
                {"type": "required_field", "field": "campaign_name"},
                {"type": "required_field", "field": "adset_id"},
                {"type": "required_field", "field": "adset_name"},
                {"type": "required_field", "field": "ad_id"},
                {"type": "required_field", "field": "ad_name"},
                {"type": "required_field", "field": "ad_channel_id"},
                {"type": "required_field", "field": "channel_id"},
                {"type": "required_field", "field": "channel_name"},
                {"type": "required_field", "field": "media_format_id"},
                {"type": "required_field", "field": "dimensions"},
                {"type": "required_field", "field": "visual_url_editor"},
                {"type": "required_field", "field": "primary_text_1"},
                {"type": "required_field", "field": "primary_text_2"},
                {"type": "required_field", "field": "primary_text_3"},
                {"type": "required_field", "field": "primary_text_4"},
                {"type": "required_field", "field": "primary_text_5"},
                {"type": "required_field", "field": "headline_1"},
                {"type": "required_field", "field": "headline_2"},
                {"type": "required_field", "field": "headline_3"},
                {"type": "required_field", "field": "headline_4"},
                {"type": "required_field", "field": "headline_5"},
                {"type": "required_field", "field": "description_1"},
                {"type": "required_field", "field": "description_2"},
                {"type": "required_field", "field": "description_3"},
                {"type": "required_field", "field": "description_4"},
                {"type": "required_field", "field": "description_5"},
                {"type": "required_field", "field": "cta"},
                {"type": "required_field", "field": "status"},
                {"type": "required_field", "field": "comments"},
                {"type": "allowed_values", "field": "status", "values": ["aprobado", "rechazado", "pendiente"]},
            ]

            validator = ExcelReaderValidator(required_columns=required_cols, validation_rules=rules)

            df = validator.read_excel(file_bytes)

            result = validator.validate_dataframe(df)

            if result["valid"]:
                banners_list = validator.get_values(df, brand_id, campaign_id)

                response = n8nClient.executePost('/webhook/v2/review-process', {
                    "banners_list": banners_list
                }, True, is_binary=False)

                return response, 200
            else:
                return {"message": "Errores encontrados", "errors": result["errors"]}, 400

        except Exception as e:
            return {"message": "Error procesando el archivo", "error": str(e)}, 500


@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad/<ad_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdGet(ProxySecureResource): 
 
    @ad_ns.doc('Get Ad by Campaign')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,ad_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_id': ad_id }
        response = n8nClient.executeGet('/webhook/v2/ad',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad/media/templates/<project_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaTemplatesGet(ProxySecureResource): 
 
    @ad_ns.doc('Get Media Templates from Asset Platform')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,project_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'project_id': project_id }
        response = n8nClient.executeGet('/webhook/v2/ad/media/templates',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/template')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaTemplateSet(ProxySecureResource): 
 
    @ad_ns.doc('Set Media Template By Ad Channel')
    @v2_api.expect(SetMediaTemplateAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/template',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/elements')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaElementsSave(ProxySecureResource): 
 
    @ad_ns.doc('Save Media Elements By Ad Channel')
    @v2_api.expect(SaveMediaElementsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/elements',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/style')
@v2_api.expect(secureHeader)
class HilucaResourceAdImageStyleSet(ProxySecureResource): 
 
    @ad_ns.doc('Set Image Style By Ad Channel')
    @v2_api.expect(SetImageStyleAdStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/style',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/attributes/generate')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImagesAttributesGenerate(ProxySecureResource): 
 
    @ad_ns.doc('Generate Image Attributes By Ad Channel')
    @v2_api.expect(GenerateMediaImageAttributesAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/attributes/generate',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImagesAttributesSave(ProxySecureResource): 
 
    @ad_ns.doc('Save Image Attributes By Ad Channel')
    @v2_api.expect(SaveMediaImageAttributesAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/attributes',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/prompts/generate')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImagesPromptsGenerate(ProxySecureResource): 
 
    @ad_ns.doc('Generate Image Prompts By Ad Channel')
    @v2_api.expect(GenerateMediaImagePromptsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/prompts/generate',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/prompts/set_preferred')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImagesPromptsSetPreferred(ProxySecureResource): 
 
    @ad_ns.doc('Set Preferred Image Prompt By Ad Channel')
    @v2_api.expect(SetPreferredMediaImagePromptsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/prompts/set_preferred',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/images/prompts/preferred')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImagesPromptsSavePreferred(ProxySecureResource): 
 
    @ad_ns.doc('Save Preferred Image Prompt By Ad Channel')
    @v2_api.expect(SavePreferredMediaImagePromptsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/prompts/preferred',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/<brand_id>/campaign/<campaign_id>/ad/<ad_id>/channel/<channel_id>/variant/<variant_id>/media/images/<image_name>')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImage(ProxySecureResource): 

    @ad_ns.doc('Upload Image By Ad Channel (Binary)')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self,brand_id,campaign_id,ad_id,channel_id,variant_id,image_name):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)

        file = request.files['file']
        content_type = file.content_type
        filename = file.filename

        buffer_image = BytesIO(file.read())
        buffer_image.seek(0)

        params = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 'ad_id' : ad_id, 
                  'channel_id': channel_id, 'variant_id': variant_id, 'image_name' : image_name }
         
        files = { 
            'file' : (filename, buffer_image.read() , content_type) 
        }

        response = n8nClient.executePost('/webhook/v2/ad/media/images/image',{},True,is_binary=False,params=params,files=files)

        return  response, 200
    
    @ad_ns.doc('Get Image By Ad Channel')
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_READ)
    def get(self,brand_id,campaign_id,ad_id,channel_id,variant_id,image_name):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = { 'brand_id' : brand_id, 'campaign_id' : campaign_id, 
                   'ad_id' : ad_id, 'channel_id': channel_id, 
                   'variant_id': variant_id, 'image_name' : image_name }
        response = n8nClient.executeGet('/webhook/v2/ad/media/images/image',payload,True,is_binary=True)

        buffer_image = BytesIO(response['content'])
        buffer_image.seek(0)

        return send_file(buffer_image, mimetype=response['content_type'])  


@ad_ns.route('/hiluca/brand/campaign/ad/channel/media/images')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaImageID(ProxySecureResource): 
 
    @ad_ns.doc('Upload Image ID By Ad Channel')
    @v2_api.expect(UploadMediaImageIDAdStruct)        
    @jwt_required    
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/images/image_id',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/elements/generate_texts')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaElementsGenerateTexts(ProxySecureResource): 
 
    @ad_ns.doc('Generate Texts By Media Elements For Ad Channel')
    @v2_api.expect(GenerateTextsMediaElementsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/elements/generate_texts',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/elements/generate_text')
@v2_api.expect(secureHeader)
class HilucaResourceAdMediaElementsGenerateText(ProxySecureResource): 
 
    @ad_ns.doc('Generate a Text By Media Elements For Ad Channel')
    @v2_api.expect(GenerateTextMediaElementsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/elements/generate_text',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/channel/attributes')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelAttributesSave(ProxySecureResource): 
 
    @ad_ns.doc('Save Channel Attributes By Ad Channel')
    @v2_api.expect(SaveChannelAttributesAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/channel/attributes',payload,True)
        return  response, 200

@ad_ns.route('/hiluca/brand/ad/channel/redirect_url')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelAttributesSave(ProxySecureResource):

    @ad_ns.doc('Save Redirect Url By Ad Channel')
    @v2_api.expect(SaveChannelRedirectUrlAdStruct)
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json
        response = n8nClient.executePost('/webhook/v2/ad/channel/redirect_url',payload,True)
        return  response, 200

@ad_ns.route('/hiluca/brand/ad/channel/attributes/generate_texts')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelAttributesGenerateTexts(ProxySecureResource): 
 
    @ad_ns.doc('Generate Texts By Channel Attributes For Ad Channel')
    @v2_api.expect(GenerateTextsChannelAttributesAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/channel/attributes/generate_texts',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/channel/attributes/generate_text')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelAttributesGenerateText(ProxySecureResource): 
 
    @ad_ns.doc('Generate a Text By Channel Attribute For Ad Channel')
    @v2_api.expect(GenerateTextChannelAttributesAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/channel/attributes/generate_text',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/visuals/generate')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelMadiaVisualsGenerate(ProxySecureResource): 
 
    @ad_ns.doc('Generate Media Visuals By Ad Channel (Abyssale)')
    @v2_api.expect(GenerateMediaVisualsAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        response = n8nClient.executePost('/webhook/v2/ad/media/visuals/generate',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/media/visuals/platform/visual_generation_hook')
class HilucaResourceMarketingAssetAbyssaleHook(ProxySecureResource): 
 
    @ad_ns.doc('Abyssale Web Hook')
    @v2_api.expect(AbyssaleHooktMarketingAssetStruct)        
    def post(self):
        n8nClient = N8NClient()
        payload = request.json
        if 'generation_request_id' in payload:
            response = n8nClient.executePost('/webhook/v2/ad/media/visuals/platform/visual_generation_hook',payload,False)
        
        return {}, 200


@ad_ns.route('/hiluca/brand/ad/<ad_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdUpdate(ProxySecureResource): 
 
    @ad_ns.doc('Update Ad By Campaign')
    @v2_api.expect(UpdateAdStruct)
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def put(self, ad_id):
        security_credentials = self.checkCredentials()
        n8nClient = N8NClient(credentials=security_credentials)
        payload = request.json 
        payload['ad_id'] = ad_id
        response = n8nClient.executePut('/webhook/v2/ad/update_name',payload,True)
        return  response, 200


@ad_ns.route('/hiluca/brand/ad/variant/select')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantSelect(ProxySecureResource): 
 
    @ad_ns.doc('Select Variant By Ad')
    @v2_api.expect(SelectAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = SelectAdUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200
    

@ad_ns.route('/hiluca/brand/ad/variant/<variant_id>')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantDelete(ProxySecureResource): 

    @ad_ns.doc('Delete Variant By Ad')
    @v2_api.expect(DeleteAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def delete(self,variant_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json 
        payload['variant_id'] = variant_id
        data = DeleteAdUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_ns.route('/hiluca/brand/ad/variant/generate')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantGenerate(ProxySecureResource): 
 
    @ad_ns.doc('Generate a Variant By Ad')
    @v2_api.expect(GenerateAnAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = GenerateAnAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_ns.route('/hiluca/brand/ad/variant/generate_all')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantGenerate(ProxySecureResource): 
 
    @ad_ns.doc('Generate all Variants By Ad')
    @v2_api.expect(GenerateAllAdStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = GenerateAllAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200
    

@ad_ns.route('/hiluca/brand/ad/media/visuals/platform/visual_edit_hook')
class HilucaResourceAbyssaleVisualEditHook(ProxySecureResource): 
 
    @ad_ns.doc('Abyssale Visual Edit Web Hook')
    @v2_api.expect(AbyssaleHooktMarketingAssetStruct)        
    def post(self):
        payload = request.json
        data = AbyssaleVisualEditUseCase().execute(payload)
        return {}, 200


@ad_ns.route('/hiluca/brand/ad/variant/pin_format')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantSelect(ProxySecureResource): 
 
    @ad_ns.doc('Pin a Format By Ad variant')
    @v2_api.expect(PinFormatAdVariantStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = PinFormatAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_ns.route('/hiluca/brand/ad/variant/unpin_formats')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelVariantUnpinFormat(ProxySecureResource): 
 
    @ad_ns.doc('Unpin Formats By Ad variant')
    @v2_api.expect(UnpinFormatAdVariantStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = UnpinFormatAdVariantUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200


@ad_ns.route('/hiluca/brand/campaign/ad/channel/media/image/edit')
@v2_api.expect(secureHeader)
class HilucaResourceAdChannelMediaImageEdit(ProxySecureResource):

    @ad_ns.doc('Edit an Ad Variant Image')
    @v2_api.expect(EditAdVariantImageStruct)
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_FUNNEL_FLOW, ACTION_UPDATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json
        data = EditAdVariantImageUseCase(user_id).execute(payload)
        return {'ok': 1, 'data': data}, 200
