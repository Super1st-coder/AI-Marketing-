import logging
from urllib.parse import unquote
from app.v2 import v2_api
from app.v1.resources.base import ProxySecureResource, secureHeader
from app.v1.repository.base import N8NClient
from flask_jwt_extended.view_decorators import jwt_required
from flask.globals import request
from flask_restplus import fields
from flask import send_file
from io import BytesIO
from cerberus import Validator
import yaml
from app.exceptions.base import IncorrectValidationException
from app.v2.use_cases.unsplash import SearchUnsplashUseCase, GetUnsplashPhotoUseCase, TrackUnsplashDownloadUseCase, GetUnsplashAttributionUseCase
from app.v2.use_cases.ads_export import ExcelManagerUseCase
from flask_restplus import fields, Resource
from app.v2.use_cases.meta_ads import CampaignDataDict, FacebookAuthCallbackUseCase, FacebookCreateAdCreativeUseCase, FacebookCreateAdSetUseCase, FacebookCreateAdUseCase,\
    FacebookCreateCampaignUseCase, FacebookGetAdAccountsUseCase, FacebookGetAdsetsUseCase, FacebookGetCampaignsUseCase, FacebookGetInsightsUseCase, FacebookGetAdsUseCase,\
        FacebookGetInsightsFromAdAccountUseCase, FacebookGetPagesUseCase, FacebookMinimumBudgetUseCase, FacebookUploadImageUseCase, S3ImageProxyUseCase,\
        FacebookValidateTokenUseCase, FacebookSearchUseCase, FacebookRemoveRedisTokenUseCase, FacebookGetAdAccountDetailsUseCase, FacebookPublishCampaignUseCase,\
        FacebookTestCreativeUploadUseCase, FacebookGetCampaignObjectiveUseCase, FacebookGeneratePreCheckCreativeUseCase, PreCheckDataDict,\
        FacebookSavePreCheckImagesUseCase, FacebookSavePreCheckTextsUseCase, FacebookSavePreCheckCTAsUseCase, FacebookSavePreCheckBudgetUseCase, FacebookSavePreCheckProposalURLUseCase,\
        FacebookSavePreCheckLocationsUseCase, FacebookExportAssetsPostLaunchCampaignUseCase, FacebookGetPixelUseCase, FacebookGetAPixelUseCase, ExportAssetsDataDict,\
        FacebookGetLaunchCampaignCreativesUseCase
from app.v2.use_cases.meta_ads import FacebookGetPageLeadgenFormsUseCase, FacebookGetPageWhatsAppNumbersUseCase, FacebookGetPageAdsPostsUseCase
from app.v2.async_tasks.celery_tasks import publish_facebook_campaign, publish_google_campaign, launch_facebook_campaign
from app.v2.use_cases.google_ads import GoogleAdsAuthUseCase, GoogleAdsCallbackUseCase, GoogleAdsCreateCampaignUseCase, GoogleAdsListCampaignsUseCase,\
    GoogleAdsListCustomersUseCase, GoogleAdsListInterestsUseCase, GoogleAdsListLocationsUseCase, GoogleAdsStatusUseCase, GoogleAdsUnauthUseCase, GoogleAdsUploadImageUseCase
from flask import Response

from app.v2.use_cases.funnel_flow_validator import FunnelFlowValidatorUseCase
from app.tools.permissions import check_access
from app.v1.models.constant import ROLE_HILUCA_ADMIN, FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE, ACTION_READ

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# from app.v2.use_cases.application import GetApplicationUseCase, GetCoinBySymbolUseCase, GetDefaultCoinUseCase
# from flask_jwt_extended.view_decorators import jwt_required
# from flask_restplus import Resource, Namespace, fields
# from app.v1.resources.base import ProxySecureResource, secureHeader,queryParams
# from app.v1.repository.base import N8NClient
# from flask import send_file
# from flask.globals import request
# import json

external_ns = v2_api.namespace('external', description='External Services')

#############################################################################

# Unsplash
UnsplashTrackDownloadStruct = v2_api.model('UnsplashTrackDownloadStruct', {
    'download_location': fields.String(description='Unsplash photo download_location URL', required=True)
})

ExcelExportFiltersStruct = v2_api.model('ExcelExportFiltersStruct', {
    'brand_id': fields.Integer(description='Brand ID to filter ads', required=False),
    'campaign_id': fields.Integer(description='Campaign ID to filter ads', required=False),
    'project_id': fields.Integer(description='Project ID to filter ads', required=False),
    'status': fields.String(description='Ad status filter', required=False),
    'date_from': fields.String(description='Start date filter (YYYY-MM-DD)', required=False),
    'date_to': fields.String(description='End date filter (YYYY-MM-DD)', required=False)
})

ExcelImportStruct = v2_api.model('ExcelImportStruct', {
    'object_type': fields.String(description='Type of object to import (ads, campaigns, brands, projects)', required=True, enum=['ads', 'campaigns', 'brands', 'projects']),
    'validation_rules': fields.Raw(description='Optional validation rules for the data', required=False)
})

#############################################################################

# Facebook

AdImageCampaignStruct = v2_api.model('AdImageCampaignStruct', {
  'image_url': fields.String(required=True),
})

CreativeAssetGroupCampaignStruct = v2_api.model('CreativeAssetGroupCampaignStruct', {
  'image_hash': fields.String(required=True),
  'titles': fields.List(fields.Raw()),
  'bodies': fields.List(fields.Raw()),
  'descriptions': fields.List(fields.Raw()),
  'call_to_action_type': fields.String(required=True),
})

AssetFeedCampaignStruct = v2_api.model('AssetFeedCampaignStruct', {
  'images': fields.List(fields.Raw()),
  'bodies': fields.List(fields.Raw()),
  'titles': fields.List(fields.Raw()),
  'descriptions': fields.List(fields.Raw()),
  'call_to_action_types': fields.List(fields.String()),
  'ad_formats': fields.List(fields.String()),
})

ObjectStoryCampaignStruct = v2_api.model('ObjectStoryCampaignStruct', {
  'page_id': fields.String(required=True),
})

AdCreativeCampaignStruct = v2_api.model('AdCreativeCampaignStruct', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'ad_account_id': fields.String(required=True),
    'object_story_spec': fields.Nested(ObjectStoryCampaignStruct, required=True),
    'asset_feed_spec': fields.Nested(AssetFeedCampaignStruct, required=False),
    'creative_asset_groups': fields.List(fields.Nested(CreativeAssetGroupCampaignStruct, required=False)),
    'ad_image': fields.Nested(AdImageCampaignStruct, required=False),
})

TargetingCampaignStruct = v2_api.model('TargetingCampaignStruct', {
    'geo_locations': fields.Raw(required=False),
    'age_min': fields.Integer(required=False),
    'age_max': fields.Integer(required=False),
    'genders': fields.List(fields.Integer()),
    'interests': fields.List(fields.Raw()),
})

AdCampaignStruct = v2_api.model('AdCampaignStruct', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'ad_account_id': fields.String(required=True),
    'adset_id': fields.String(required=True),
    'adCreative': fields.Nested(AdCreativeCampaignStruct),
    'creative': fields.Raw(),
    'status': fields.String(required=True),
})

AdSetCampaignStruct = v2_api.model('AdSetCampaignStruct', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'campaign_id': fields.String(required=True),
    'ad_account_id': fields.String(required=True),
    'daily_budget': fields.String(required=True),
    'billing_event': fields.String(required=True),
    'optimization_goal': fields.String(required=True),
    'targeting': fields.Nested(TargetingCampaignStruct),
    'status': fields.String(required=True),
    'ads': fields.List(fields.Nested(AdCampaignStruct))
})

PublishCampaignStruct = v2_api.model('PublishCampaignStruct', {
    'id': fields.String(required=True),
    'name': fields.String(required=True),
    'ad_account_id': fields.String(required=True),
    'objective': fields.String(required=True),
    'status': fields.String(required=True),
    'buying_type': fields.String(required=True),
    'special_ad_categories': fields.List(fields.String()),
    'adSets': fields.List(fields.Nested(AdSetCampaignStruct))
})

GeneratePreCheckCampaignLaunchStruct = v2_api.model('GeneratePreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'ad_account_id': fields.String(),
    'page_id': fields.String(),
    'objective': fields.String(),
    'optimization_goal': fields.String(),
    'pixel_id': fields.String(),
    'conversion_event': fields.String(),
    'creative_type': fields.String(),
    'daily_budget': fields.String(),
    'lead_gen_form_id': fields.String(),
    'whatsapp_number_id': fields.String()
})

SaveImagesPreCheckCampaignLaunchStruct = v2_api.model('SaveImagesPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'images': fields.List(fields.Raw())
})

SaveTextsPreCheckCampaignLaunchStruct = v2_api.model('SaveTextsPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'bodies': fields.List(fields.Raw()),
    'titles': fields.List(fields.Raw()),
    'descriptions': fields.List(fields.Raw())
})

SaveCTAsPreCheckCampaignLaunchStruct = v2_api.model('SaveCTAsPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'call_to_action_types': fields.List(fields.Raw())
})

SaveBudgetPreCheckCampaignLaunchStruct = v2_api.model('SaveBudgetPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'daily_budget': fields.Integer()
})

SaveProposalUrlsPreCheckCampaignLaunchStruct = v2_api.model('SaveProposalUrlsPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'proposal_url': fields.String()
})

SaveLocationsPreCheckCampaignLaunchStruct = v2_api.model('SaveLocationsPreCheckCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
    'locations': fields.List(fields.Raw())
})

PublishCampaignLaunchStruct = v2_api.model('PublishCampaignLaunchStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'creatives': fields.List(fields.Raw())
})

LaunchCampaignExportAssetsStruct = v2_api.model('LaunchCampaignExportAssetsStruct', { 
    'brand_id': fields.Integer(),
    'campaign_id': fields.Integer(),
    'adset_id': fields.Integer(),
    'ad_id': fields.Integer(),
    'adchannel_id': fields.Integer(),
})

#############################################################################


@external_ns.route('/unsplash/images/search')
@v2_api.expect(secureHeader)
class UnsplashSearchImagesResource(ProxySecureResource):

    @external_ns.doc('Search images in Unsplash')
    @external_ns.param('q', 'Search query term', required=True, type='string')
    @external_ns.param('page', 'Page number for pagination', required=False, type='integer', default=1)
    @external_ns.param('per_page', 'Number of images per page', required=False, type='integer', default=12)
    @external_ns.param('orientation', 'Image orientation (landscape, portrait, squarish)', required=False, type='string')
    @external_ns.param('content_filter', 'Content filter (low, high)', required=False, type='string')
    @external_ns.param('color', 'Image color filter', required=False, type='string')
    @jwt_required
    def get(self):
        q = request.args.get('q', type=str)
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=12, type=int)
        orientation = request.args.get('orientation', default=None, type=str)
        content_filter = request.args.get('content_filter', default=None, type=str)
        color = request.args.get('color', default=None, type=str)

        if q is None or len(q.strip()) == 0:
            return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'Missing query parameter q' } }, 400
        result, status = SearchUnsplashUseCase().execute(
            query=q,
            page=page,
            per_page=per_page,
            orientation=orientation,
            content_filter=content_filter,
            color=color
        )
        return result, status


@external_ns.route('/unsplash/images/photo/<photo_id>')
@v2_api.expect(secureHeader)
class UnsplashGetPhotoResource(ProxySecureResource):

    @external_ns.doc('Get photo details from Unsplash by id')
    @jwt_required
    def get(self, photo_id):
        result, status = GetUnsplashPhotoUseCase().execute(photo_id)
        return result, status


@external_ns.route('/unsplash/images/track-download')
@v2_api.expect(secureHeader)
class UnsplashTrackDownloadResource(ProxySecureResource):

    @external_ns.doc('Track a download in Unsplash using download_location URL')
    @v2_api.expect(UnsplashTrackDownloadStruct)
    @jwt_required
    def post(self):
        payload = request.json or {}
        download_location = payload.get('download_location')
        if download_location is None or len(download_location.strip()) == 0:
            return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'download_location is required' } }, 400
        result, status = TrackUnsplashDownloadUseCase().execute(download_location)
        return result, status


@external_ns.route('/unsplash/images/photo/<photo_id>/attribution')
@v2_api.expect(secureHeader)
class UnsplashGetAttributionResource(ProxySecureResource):

    @external_ns.doc('Get attribution block with UTM links for Unsplash photo id')
    @jwt_required
    def get(self, photo_id):
        result, status = GetUnsplashAttributionUseCase().execute(photo_id)
        return result, status


@external_ns.route('/excel/export')
@v2_api.expect(secureHeader)
class ExcelExportResource(ProxySecureResource):

    @external_ns.doc('Export data to Excel format')
    @external_ns.param('brand_id', 'Brand ID to filter ads', required=False, type='integer')
    @external_ns.param('campaign_id', 'Campaign ID to filter ads', required=False, type='integer')
    @external_ns.param('project_id', 'Project ID to filter ads', required=False, type='integer')
    @external_ns.param('status', 'Ad status filter', required=False, type='string')
    @external_ns.param('date_from', 'Start date filter (YYYY-MM-DD)', required=False, type='string')
    @external_ns.param('date_to', 'End date filter (YYYY-MM-DD)', required=False, type='string')
    @jwt_required
    def get(self):
        import logging
        logger = logging.getLogger(__name__)

        logger.info("Excel export endpoint called")

        brand_id = request.args.get('brand_id', type=int)
        campaign_id = request.args.get('campaign_id', type=int)
        project_id = request.args.get('project_id', type=int)
        status = request.args.get('status', type=str)
        date_from = request.args.get('date_from', type=str)
        date_to = request.args.get('date_to', type=str)

        logger.info(f"Request params: brand_id={brand_id}, campaign_id={campaign_id}, project_id={project_id}, status={status}, date_from={date_from}, date_to={date_to}")

        filters = {}
        if status:
            filters['status'] = status
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to

        logger.info(f"Calling ExcelManagerUseCase.export_to_excel with filters: {filters}")

        excel_data, filename, status_code = ExcelManagerUseCase().export_to_excel(
            brand_id=brand_id,
            campaign_id=campaign_id,
            project_id=project_id,
            filters=filters
        )

        logger.info(f"ExcelManagerUseCase returned: excel_data={'None' if excel_data is None else 'Present'}, filename={filename}, status_code={status_code}")

        if excel_data is None:
            logger.error(f"Export failed with status_code: {status_code}")
            return { 'ok': 0, 'message': { 'code': 'EEXP', 'text': 'Failed to export data' } }, status_code

        excel_buffer = BytesIO(excel_data)
        excel_buffer.seek(0)

        return send_file(
            excel_buffer,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            attachment_filename=filename
        )


@external_ns.route('/excel/export/bulk')
@v2_api.expect(secureHeader)
class ExcelBulkExportResource(ProxySecureResource):

    @external_ns.doc('Export multiple datasets to Excel with multiple sheets')
    @v2_api.expect(ExcelExportFiltersStruct)
    @jwt_required
    def post(self):
        payload = request.json or {}

        export_configs = payload.get('export_configs', [])

        if not export_configs or not isinstance(export_configs, list):
            return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'export_configs array is required' } }, 400

        try:
            excel_data, filename, status_code = ExcelManagerUseCase().bulk_export_to_excel(export_configs)

            if excel_data is None:
                return { 'ok': 0, 'message': { 'code': 'EEXP', 'text': 'Failed to export data' } }, status_code

            excel_buffer = BytesIO(excel_data)
            excel_buffer.seek(0)

            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                attachment_filename=filename
            )

        except Exception as e:
            return { 'ok': 0, 'message': { 'code': 'EEXP', 'text': f'Export error: {str(e)}' } }, 500


@external_ns.route('/excel/import')
@v2_api.expect(secureHeader)
class ExcelImportResource(ProxySecureResource):

    @external_ns.doc('Import data from Excel file')
    @external_ns.expect(ExcelImportStruct)
    @jwt_required
    def post(self):
        try:
            if 'file' not in request.files:
                return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'No file uploaded' } }, 400

            file = request.files['file']
            if file.filename == '':
                return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'No file selected' } }, 400

            if not file.filename.endswith('.xlsx') and not file.filename.endswith('.xls'):
                return { 'ok': 0, 'message': { 'code': 'EVAL', 'text': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)' } }, 400

            object_type = request.form.get('object_type', 'ads')
            validation_rules = request.form.get('validation_rules')

            if validation_rules:
                try:
                    import json
                    validation_rules = json.loads(validation_rules)
                except:
                    validation_rules = None

            file_content = BytesIO(file.read())

            import_result, status_code, message = ExcelManagerUseCase().import_from_excel(
                excel_file=file_content,
                object_type=object_type,
                validation_rules=validation_rules
            )

            if import_result is None:
                return { 'ok': 0, 'message': { 'code': 'EIMP', 'text': message } }, status_code

            return {
                'ok': 1,
                'message': message,
                'data': import_result
            }, status_code

        except Exception as e:
            return { 'ok': 0, 'message': { 'code': 'EIMP', 'text': f'Import error: {str(e)}' } }, 500

@external_ns.route("/google-ads/auth/<string:user_id>")
class GoogleAdsAuthResource(Resource):
    def get(self, user_id):
        return GoogleAdsAuthUseCase().execute(user_id)

@external_ns.route("/google-ads/callback")
class GoogleAdsCallbackResource(Resource):
    def get(self):
        user_id = request.args.get("state")
        return GoogleAdsCallbackUseCase().execute(user_id, request)

@external_ns.route("/google-ads/status/<string:user_id>")
@external_ns.expect(secureHeader)
class GoogleAdsStatusResource(Resource):
    def get(self, user_id):
        return GoogleAdsStatusUseCase().execute(user_id)

@external_ns.route("/google-ads/unauth/<string:user_id>")
@external_ns.expect(secureHeader)
class GoogleAdsUnauthResource(Resource):
    def get(self, user_id):
        return GoogleAdsUnauthUseCase().execute(user_id)

@external_ns.route("/google-ads/list-campaigns/<string:user_id>/<string:customer_id>")
@external_ns.expect(secureHeader)
class GoogleAdsListCampaignsResource(Resource):
    def get(self, user_id, customer_id):
        return GoogleAdsListCampaignsUseCase().execute(user_id, customer_id)

@external_ns.route("/google-ads/create-campaign/<string:user_id>/<string:customer_id>")
class GoogleAdsCreateCampaignResource(Resource):
    @external_ns.expect(secureHeader)
    def post(self, user_id, customer_id):
        payload = request.json

        job = publish_google_campaign.delay(user_id, customer_id, payload)
        return { 'ok': 1, 'data': {'job_id': job.id}}, 200

@external_ns.route("/google-ads/list-customers/<string:user_id>")
@external_ns.expect(secureHeader)
class GoogleAdsListCustomersResource(Resource):
    def get(self, user_id):
        return GoogleAdsListCustomersUseCase().execute(user_id)

@external_ns.route("/google-ads/upload-image/<string:user_id>/<string:customer_id>")
@external_ns.expect(secureHeader)
class GoogleAdsUploadImageResource(Resource):
    def post(self, user_id, customer_id):

        if "file" not in request.files:
            return {"error": "file es requerido como multipart/form-data"}, 400

        file = request.files["file"]
        image_bytes = file.read()

        return GoogleAdsUploadImageUseCase().execute(
            user_id=user_id,
            customer_id=customer_id,
            image_bytes=image_bytes
        )

@external_ns.route("/google-ads/search/location")
@external_ns.expect(secureHeader)
class GoogleAdsSearchUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()
        query = request.args.get("q")

        return GoogleAdsListLocationsUseCase().execute(user_id=security_credentials['username'], query=query)

@external_ns.route("/google-ads/search/interests")
@external_ns.expect(secureHeader)
class GoogleAdsSearchUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()
        query = request.args.get("q")

        return GoogleAdsListInterestsUseCase().execute(user_id=security_credentials['username'], query=query)

@external_ns.route('/hiluca/brand/<brand_id>/ads/all-data-campaigns')
@v2_api.expect(secureHeader)
class HilucaResourceAdsExport(ProxySecureResource):
    @external_ns.doc('Export Ads to Excel by Campaign')
    @external_ns.param('campaigns', 'Lista de IDs de campañas separadas por comas', type=str, required=False)
    @jwt_required
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

            response = n8nClient.executeGet('/webhook/v2/all-data-campaigns', payload, True)


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

@external_ns.route("/facebook/auth/<string:code>")
@external_ns.expect(secureHeader)
class FacebookAuthResource(ProxySecureResource):
    @jwt_required
    def get(self, code):
        security_credentials = self.checkCredentials()

        return FacebookAuthCallbackUseCase().execute(code, user_id=security_credentials['username'])


@external_ns.route("/facebook/publish_campaign/<string:campaign_id>")
@v2_api.expect(secureHeader)
class FacebookPublishCampaignResource(ProxySecureResource):

    @external_ns.doc('Publish Campaign')
    @v2_api.expect(PublishCampaignStruct)
    @jwt_required
    def post(self, campaign_id):
        security_credentials = self.checkCredentials()
        user_id=security_credentials['username']

        payload = request.json or {}
        complete_campaign_data: CampaignDataDict = payload.get('complete_campaign_data', {})
        creative_type = payload.get('creative_type', '')

        # data = FacebookPublishCampaignUseCase(payload, user_id=security_credentials['username']).execute()
        # return {'ok' : 1, 'data': data }, 200

        job = publish_facebook_campaign.delay(user_id, campaign_id, complete_campaign_data, creative_type)
        return { 'ok': 1, 'data': {'job_id': job.id}}, 200


@external_ns.route("/facebook/create_campaign")
@external_ns.expect(secureHeader)
class FacebookCreateCampaignResource(ProxySecureResource):
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json or {}
        name = payload.get('name')
        objective = payload.get('objective')
        status = payload.get('status', 'PAUSED')
        buying_type = payload.get('buying_type', 'AUCTION')
        special_ad_categories = payload.get('special_ad_categories', [])

        ad_account_id = payload.get('ad_account_id')

        if not name or not objective:
            return {"error": "name and objective are required fields."}, 400

        return FacebookCreateCampaignUseCase(ad_account_id).execute(name, objective, status, buying_type, special_ad_categories, user_id=security_credentials['username'])

@external_ns.route("/facebook/create_ad_set")
@external_ns.expect(secureHeader)
class FacebookCreateAdSetUseCaseResource(ProxySecureResource):
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()

        payload = request.json or {}

        name= payload.get("name")
        campaign_id= payload.get("campaign_id")
        daily_budget= payload.get("daily_budget")
        billing_event= payload.get("billing_event")
        optimization_goal= payload.get("optimization_goal")
        bid_strategy= payload.get("bid_strategy")
        targeting= payload.get("targeting")
        targeting_automation = payload.get("targeting_automation")
        start_time= payload.get("start_time")
        end_time= payload.get("end_time")
        status= payload.get("status", "PAUSED")

        ad_account_id = payload.get('ad_account_id')

        user_id=security_credentials['username']

        if not all([name, campaign_id, daily_budget, billing_event, optimization_goal, bid_strategy, targeting, start_time, end_time]):
            return {"error": "All fields except status are required."}, 400

        return FacebookCreateAdSetUseCase(ad_account_id).execute(name, campaign_id, daily_budget, billing_event, optimization_goal, bid_strategy, targeting, targeting_automation, start_time, end_time, status, user_id)

@external_ns.route("/facebook/create_ad_creative")
@external_ns.expect(secureHeader)
class FacebookCreateAdCreativeUseCaseResource(ProxySecureResource):
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()
        payload = request.json or {}

        name = payload.get("name")
        ad_account_id = payload.get("ad_account_id")
        asset_feed_spec = payload.get("asset_feed_spec")
        object_story_spec = payload.get("object_story_spec")
        creative_asset_groups = payload.get("creative_asset_groups")

        if not name or not ad_account_id:
            return {"error": "Name and ad_account_id are required."}, 400

        user_id = security_credentials["username"]

        return FacebookCreateAdCreativeUseCase(ad_account_id).execute(
            name=name,
            user_id=user_id,
            asset_feed_spec=asset_feed_spec,
            object_story_spec=object_story_spec,
            creative_asset_groups=creative_asset_groups
        )

@external_ns.route("/facebook/ad_accounts")
@external_ns.expect(secureHeader)
class FacebookGetAdAccountsUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()

        result = FacebookGetAdAccountsUseCase().execute(user_id=security_credentials['username'])
        logger.info(f"Facebook ad accounts: {result}")
        return result

@external_ns.route("/facebook/upload_image")
@external_ns.expect(secureHeader)
class FacebookUploadImageUseCaseResource(ProxySecureResource):
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()

        file_storage = request.files.get("file")
        if not file_storage:
            return {"error": "file is required."}, 400

        ad_account_id = request.form.get("ad_account_id")

        if not ad_account_id:
            return {"error": "ad_account_id is required."}, 400

        return FacebookUploadImageUseCase(ad_account_id).execute(
            file_storage=file_storage,
            user_id=security_credentials["username"]
        )

@external_ns.route("/facebook/create_ad")
@external_ns.expect(secureHeader)
class FacebookCreateAdUseCaseResource(ProxySecureResource):
    @jwt_required
    def post(self):
        security_credentials = self.checkCredentials()

        payload = request.json or {}

        name= payload.get("name")
        adset_id= payload.get("adset_id")
        creative = payload.get("creative")
        status= payload.get("status", "PAUSED")

        ad_account_id = payload.get('ad_account_id')

        if not all([name, adset_id, creative]):
            return {"error": "name, adset_id, and creative are required."}, 400

        return FacebookCreateAdUseCase(ad_account_id).execute(name, adset_id, creative, status, user_id=security_credentials['username'])

@external_ns.route("/facebook/pages")
@external_ns.expect(secureHeader)
class FacebookGetPagesUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()

        result = FacebookGetPagesUseCase().execute(user_id=security_credentials['username'])
        logger.info(f"Facebook pages: {result}")
        return result

@external_ns.route("/facebook/pages/<string:page_id>/leadgen_forms")
@external_ns.expect(secureHeader)
class FacebookGetPageLeadgenFormsResource(ProxySecureResource):
    @jwt_required
    def get(self, page_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        data = FacebookGetPageLeadgenFormsUseCase().execute(user_id, page_id)
        return {'ok' : 1, 'data': data }, 200

@external_ns.route("/facebook/pages/<string:page_id>/whatsapp_numbers")
@external_ns.expect(secureHeader)
class FacebookGetPageWhatsAppNumbersResource(ProxySecureResource):
    @jwt_required
    def get(self, page_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        result, status = FacebookGetPageWhatsAppNumbersUseCase().execute(user_id, page_id)
        return result, status

@external_ns.route("/facebook/pages/<string:page_id>/ads_posts")
@external_ns.expect(secureHeader)
class FacebookGetPageAdsPostsResource(ProxySecureResource):
    @jwt_required
    def get(self, page_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        result, status = FacebookGetPageAdsPostsUseCase().execute(user_id, page_id)
        return result, status

@external_ns.route("/facebook/validate_token")
@external_ns.expect(secureHeader)
class FacebookValidateTokenUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()

        return FacebookValidateTokenUseCase().execute(user_id=security_credentials['username'])

@external_ns.route("/facebook/s3_image_proxy/<path:url>")
@external_ns.expect(secureHeader)
class S3ImageProxyUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, url):
        decoded_url = unquote(url)
        return S3ImageProxyUseCase().execute(url=decoded_url)

@external_ns.route("/facebook/search")
@external_ns.expect(secureHeader)
class FacebookSearchUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()

        type = request.args.get("type")
        query = request.args.get("q")
        location_types = request.args.get("location_types")

        return FacebookSearchUseCase().execute(user_id=security_credentials['username'], type=type, query=query, location_types=location_types)

@external_ns.route("/facebook/reset_auth")
@external_ns.expect(secureHeader)
class FacebookRemoveRedisTokenUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self):
        security_credentials = self.checkCredentials()

        return FacebookRemoveRedisTokenUseCase().execute(user_id=security_credentials['username'])

@external_ns.route("/facebook/ad_account/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookGetAdAccountDetailsResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()

        return FacebookGetAdAccountDetailsUseCase().execute(
            user_id=security_credentials['username'],
            ad_account_id=ad_account_id
        )

@external_ns.route("/facebook/upload_creatives/<string:campaign_id>")
@external_ns.expect(secureHeader)
class FacebookTestCreativeUploadResource(ProxySecureResource):
    @jwt_required
    def post(self, campaign_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        payload = request.json or {}
        complete_campaign_data: CampaignDataDict = payload.get('complete_campaign_data', {})
        creative_type = payload.get('creative_type', '')

        return FacebookTestCreativeUploadUseCase(campaign_id, user_id, complete_campaign_data, creative_type).execute()

@external_ns.route("/facebook/minimum_budget/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookRemoveRedisTokenUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        return FacebookMinimumBudgetUseCase().execute(user_id, ad_account_id)

@external_ns.route("/funnel_flow/validator/<string:campaign_id>")
@external_ns.expect(secureHeader)
class FunnelFlowValidatorUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, campaign_id):
        return FunnelFlowValidatorUseCase(campaign_id).execute()

@external_ns.route("/facebook/ads/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookGetAdsUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        return FacebookGetAdsUseCase().execute(user_id, ad_account_id)

@external_ns.route("/facebook/adsets/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookGetAdsetsUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        return FacebookGetAdsetsUseCase().execute(user_id, ad_account_id)

@external_ns.route("/facebook/campaigns/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookGetCampaignsUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        return FacebookGetCampaignsUseCase().execute(user_id, ad_account_id)

@external_ns.route("/facebook/insights/entity/<string:entity_id>")
@external_ns.expect(secureHeader)
class FacebookGetInsightsUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, entity_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        query_params = request.args or {}
        fields = query_params.get('fields')
        level = query_params.get('level')
        date_preset = query_params.get('date_preset')
        time_increment = query_params.get('time_increment')

        return FacebookGetInsightsUseCase().execute(user_id, entity_id, fields, level, date_preset, time_increment)

@external_ns.route("/facebook/insights/ad_account/<string:ad_account_id>")
@external_ns.expect(secureHeader)
class FacebookGetInsightsFromAdAccountUseCaseResource(ProxySecureResource):
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        query_params = request.args or {}
        fields = query_params.get('fields')
        level = query_params.get('level')
        date_preset = query_params.get('date_preset')
        time_increment = query_params.get('time_increment')

        return FacebookGetInsightsFromAdAccountUseCase().execute(user_id, ad_account_id, fields, level, date_preset, time_increment)


@external_ns.route("/facebook/campaign_objective")
@external_ns.expect(secureHeader)
class FacebookResourceGetCampaignObjective(ProxySecureResource):
    @external_ns.doc('Campaign Objetives')
    @jwt_required
    # Falta definir privilegios @check_access
    def get(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        data = FacebookGetCampaignObjectiveUseCase().execute(user_id)

        return {'ok' : 1, 'data': data }, 200
    

@external_ns.route('/facebook/launch/pre_check')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckGenerate(ProxySecureResource): 
 
    @external_ns.doc('Generate Launch Pre-Check By Campaig')
    @v2_api.expect(GeneratePreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        payload = request.json or {}
        campaign_id = payload.get('campaign_id')
        complete_campaign_data: CampaignDataDict = {
            'page_id': payload.get('page_id'),
            'ad_account_id': payload.get('ad_account_id'),
            'objective': payload.get('objective'),
            'optimization_goal': payload.get('optimization_goal'),
            'pixel_id': payload.get('pixel_id'),
            'conversion_event': payload.get('conversion_event'),
            'lead_gen_form_id': payload.get('lead_gen_form_id'),
            'whatsapp_number_id': payload.get('whatsapp_number_id')
        }
        creative_type = payload.get('creative_type', '')

        return FacebookGeneratePreCheckCreativeUseCase(campaign_id, user_id, complete_campaign_data, creative_type).execute()


@external_ns.route('/facebook/launch/pre_check/images')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckImagesSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (Images) By Creative')
    @v2_api.expect(SaveImagesPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_images_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'images': payload.get('images', [])
        }

        data = FacebookSavePreCheckImagesUseCase(user_id, pre_check_images_data).execute()

        return {'ok' : 1, 'data': data }, 200
    

@external_ns.route('/facebook/launch/pre_check/texts')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckTextsSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (Texts) By Creative')
    @v2_api.expect(SaveTextsPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_texts_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'bodies': payload.get('bodies', []),
            'titles': payload.get('titles', []),
            'descriptions': payload.get('descriptions', [])
        }

        data = FacebookSavePreCheckTextsUseCase(user_id, pre_check_texts_data).execute()

        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/pre_check/ctas')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckCTAsSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (CTAs) By Creative')
    @v2_api.expect(SaveCTAsPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_ctas_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'call_to_action_types': payload.get('call_to_action_types', [])
        }

        data = FacebookSavePreCheckCTAsUseCase(user_id, pre_check_ctas_data).execute()

        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/pre_check/budget')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckBudgetSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (Budget) By Creative')
    @v2_api.expect(SaveBudgetPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_budget_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'daily_budget': payload.get('daily_budget', 0)
        }

        data = FacebookSavePreCheckBudgetUseCase(user_id, pre_check_budget_data).execute()

        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/pre_check/proposal_url')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckProposalURLSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (Proposal URL) By Creative')
    @v2_api.expect(SaveProposalUrlsPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_proposal_url_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'proposal_url': payload.get('proposal_url')
        }

        data = FacebookSavePreCheckProposalURLUseCase(user_id, pre_check_proposal_url_data).execute()

        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/pre_check/locations')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPreCheckLocationsSave(ProxySecureResource): 
 
    @external_ns.doc('Save and Validate Launch Pre-Check (Locations) By Creative')
    @v2_api.expect(SaveLocationsPreCheckCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        pre_check_locations_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id'),
            'locations': payload.get('locations')
        }

        data = FacebookSavePreCheckLocationsUseCase(user_id, pre_check_locations_data).execute()

        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/publish')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchPublish(ProxySecureResource): 
 
    @external_ns.doc('Publish Campaign To Meta')
    @v2_api.expect(PublishCampaignLaunchStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        launch_data: PreCheckDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'creatives': payload.get('creatives')
        }

        # data = FacebookLaunchCampaignUseCase(user_id, launch_data).execute()
        # return {'ok' : 1, 'data': data }, 200

        job = launch_facebook_campaign.delay(user_id, launch_data)
        return { 'ok': 1, 'data': {'job_id': job.id}}, 200


@external_ns.route("/facebook/ad_account/<string:ad_account_id>/pixels")
@external_ns.expect(secureHeader)
class FacebookGetAdAccountPixelsResource(ProxySecureResource):

    @external_ns.doc('Get Pixels By Account')
    @jwt_required
    def get(self, ad_account_id):
        security_credentials = self.checkCredentials()

        data = FacebookGetPixelUseCase().execute(user_id=security_credentials['username'], ad_account_id=ad_account_id)
        return {'ok' : 1, 'data': data }, 200


@external_ns.route('/facebook/launch/publish/export_assets')
@external_ns.expect(secureHeader)
class FacebookResourceCampaignLaunchExportAssets(ProxySecureResource): 
 
    @external_ns.doc('Export Assets Post-Publish Campaign To Meta - STANDARD')
    @v2_api.expect(LaunchCampaignExportAssetsStruct)        
    @jwt_required    
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_CREATE)
    def post(self):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']
        payload = request.json or {}
        payload: ExportAssetsDataDict = {
            'brand_id': payload.get('brand_id'),
            'campaign_id': payload.get('campaign_id'),
            'adset_id': payload.get('adset_id'),
            'ad_id': payload.get('ad_id'),
            'adchannel_id': payload.get('adchannel_id')
        }

        data = FacebookExportAssetsPostLaunchCampaignUseCase(user_id).execute(payload)

        buffer_zip = BytesIO(data['content'])
        buffer_zip.seek(0)
        return send_file(
            buffer_zip,
            mimetype=data['content_type'],
            as_attachment=True,
            attachment_filename=data['filename']
        )


@external_ns.route("/facebook/launch/publish/brand/<brand_id>/campaign/<campaign_id>")
@external_ns.expect(secureHeader)
class FacebookGetCampaignPublishedResource(ProxySecureResource):

    @external_ns.doc('Get Campaign Published To Meta')
    @jwt_required
    @check_access([ROLE_HILUCA_ADMIN], FUNCTION_CAMPAIGN_LAUNCHPAD, ACTION_READ)
    def get(self, brand_id, campaign_id):
        security_credentials = self.checkCredentials()
        user_id = security_credentials['username']

        data = FacebookGetLaunchCampaignCreativesUseCase(user_id).execute(brand_id=brand_id, campaign_id=campaign_id)
        return {'ok' : 1, 'data': data }, 200


# @external_ns.route("/facebook/ad_account/<string:ad_account_id>/pixel/<string:pixel_id>/stats")
# @external_ns.expect(secureHeader)
# class FacebookGetAdAccountPixelResource(ProxySecureResource):

#     @external_ns.doc('Get Pixel Stats')
#     @jwt_required
#     def get(self, ad_account_id, pixel_id):
#         security_credentials = self.checkCredentials()

#         data = FacebookGetAPixelUseCase().execute(user_id=security_credentials['username'], ad_account_id=ad_account_id, pixel_id=pixel_id)
#         return {'ok' : 1, 'data': data }, 200