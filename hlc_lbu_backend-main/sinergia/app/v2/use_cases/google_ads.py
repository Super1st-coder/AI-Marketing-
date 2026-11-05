from typing import List
from werkzeug.exceptions import BadRequest
from google_auth_oauthlib.flow import Flow
from app import redis_client
from flask import redirect, Response
import os
import pathlib
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
from uuid import uuid4
import requests
from io import BytesIO
from PIL import Image

BASE_DIR = pathlib.Path(__file__).resolve().parents[3]
CLIENT_SECRET_FILE = str(BASE_DIR / "config" / "client_secret.json")

SCOPES: List[str] = ["https://www.googleapis.com/auth/adwords"]

REDIRECT_URI = os.getenv("GOOGLE_ADS_REDIRECT_URI", "http://backend.hiluca.com:60002/api/v2/external/google-ads/callback")

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_MANAGER_ID= os.getenv("GOOGLE_ADS_MANAGER_ID")

def build_ads_service(user_id: str):
    refresh_token = redis_client.get(user_id)

    refresh_token = redis_client.get(f"google_ads_refresh_token:{user_id}")
    if not refresh_token:
        raise RuntimeError("User has not authenticated Google Ads yet.")

    config = {
        "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token.decode(),
        "use_proto_plus": True,
    }

    client = GoogleAdsClient.load_from_dict(config)
    return client

class GoogleAdsAuthUseCase(object):
    def execute(self, user_id: str, req=None):
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        auth_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="false",
            state=user_id,
        )

        return redirect(auth_url)

class GoogleAdsCallbackUseCase(object):
    def execute(self, user_id: str, req):
        code = req.args.get("code")
        state = req.args.get("state") or user_id
        error = req.args.get("error")

        if error:
            status = "error"
        else:
            status = "success"
        if not code:
            raise BadRequest("Missing code")

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        flow.fetch_token(code=code)
        credentials = flow.credentials

        if not credentials.refresh_token:
            raise BadRequest("Google did not return a refresh_token")

        redis_client.set(f"google_ads_refresh_token:{user_id}", credentials.refresh_token)

        html = f"""
        <html>
          <body>
            <script>
              (function() {{
                const message = {{
                  provider: "google-drive",
                  type: "oauth-callback",
                  status: "{status}",
                  code: {f'"{code}"' if code else "null"},
                  state: "{state}",
                  error: {f'"{error}"' if error else "null"},
                }};
                window.opener.postMessage(message, "*");
                setTimeout(() => window.close(), 100);
              }})();
            </script>
          </body>
        </html>
        """
        return Response(html, mimetype="text/html")

class GoogleAdsStatusUseCase:
    def execute(self, user_id: str):
        refresh_token = redis_client.get(f"google_ads_refresh_token:{user_id}")

        if not refresh_token:
            return {
                "authenticated": False,
                "message": "El usuario no ha autenticado Google Ads aún."
            }, 200

        try:
            refresh_token = refresh_token.decode("utf-8")

            client = build_ads_service(user_id)

            ga_service = client.get_service("GoogleAdsService")
            query = "SELECT customer.id FROM customer LIMIT 1"

            ga_service.search(customer_id=GOOGLE_ADS_MANAGER_ID, query=query)

            return {
                "authenticated": True,
                "user": GOOGLE_ADS_MANAGER_ID
            }, 200

        except GoogleAdsException as ex:
            return {
                "authenticated": False,
                "message": "Error autenticando Google Ads",
                "errors": [e.message for e in ex.failure.errors],
            }, 200
        except Exception:
            return {
                "authenticated": False,
                "message": "El usuario no ha autenticado Google Ads aún."
            }, 200

class GoogleAdsUnauthUseCase:
    def execute(self, user_id: str):
        key = f"google_ads_refresh_token:{user_id}"
        refresh_token = redis_client.get(key)

        if not refresh_token:
            return {
                "authenticated": False,
                "message": "El usuario no tenía autenticación activa de Google Ads."
            }, 200

        redis_client.delete(key)

        return {
            "authenticated": False,
            "message": "Autenticación de Google Ads eliminada correctamente."
        }, 200

class GoogleAdsListCampaignsUseCase:
    def execute(self, user_id: str, customer_id: str):
        try:
            client = build_ads_service(user_id)
            ga_service = client.get_service("GoogleAdsService")

            query = """
                SELECT campaign.id, campaign.name, campaign.status
                FROM campaign
                ORDER BY campaign.id DESC
                LIMIT 50
            """

            response = ga_service.search_stream(
                customer_id=customer_id,
                query=query
            )

            campaigns = []
            for batch in response:
                for row in batch.results:
                    campaigns.append({
                        "id": row.campaign.id,
                        "name": row.campaign.name,
                        "status": row.campaign.status.name,
                    })

            return {
                "campaigns": campaigns,
                "count": len(campaigns)
            }, 200

        except GoogleAdsException as ex:
            return {
                "error": "Google Ads API error",
                "details": [e.message for e in ex.failure.errors],
            }, 400

        except Exception as e:
            return {
                "error": str(e),
            }, 500

class GoogleAdsCreateCampaignUseCase:
    def execute(self, user_id: str, customer_id: str, data: dict):
        try:
            client = build_ads_service(user_id)

            campaign_service = client.get_service("CampaignService")
            budget_service = client.get_service("CampaignBudgetService")
            ad_group_service = client.get_service("AdGroupService")
            ad_group_ad_service = client.get_service("AdGroupAdService")

            # -----------------------
            # Create budget
            # -----------------------
            budget_op = client.get_type("CampaignBudgetOperation")
            budget = budget_op.create
            budget_name = data["budget"].get("name", f"Budget #{uuid4()}")
            budget.name = f"{budget_name}-{uuid4()}"
            budget.amount_micros = data["budget"]["amount_micros"]
            budget.delivery_method = getattr(
                client.enums.BudgetDeliveryMethodEnum,
                data["budget"]["delivery_method"]
            )

            budget_response = budget_service.mutate_campaign_budgets(
                customer_id=customer_id,
                operations=[budget_op]
            )
            budget_id = budget_response.results[0].resource_name

            # -----------------------
            # Create campaign
            # -----------------------
            campaign_op = client.get_type("CampaignOperation")
            campaign = campaign_op.create
            campaign_data = data["campaign"]

            campaign_name = campaign_data.get("name", f"Campaign #{uuid4()}")
            campaign.name = f"{campaign_name}-{uuid4()}"
            campaign.advertising_channel_type = getattr(
                client.enums.AdvertisingChannelTypeEnum,
                campaign_data.get("channel_type", "DISPLAY")
            )
            campaign.status = getattr(
                client.enums.CampaignStatusEnum,
                campaign_data.get("status", "PAUSED")
            )
            campaign.manual_cpc.enhanced_cpc_enabled = False
            campaign.contains_eu_political_advertising = (
                client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
            )

            objective = campaign_data.get("objective", "SALES")
            self.apply_objective(campaign, objective, client)
            campaign.campaign_budget = budget_id

            campaign_response = campaign_service.mutate_campaigns(
                customer_id=customer_id,
                operations=[campaign_op]
            )
            campaign_id = campaign_response.results[0].resource_name

            # -----------------------
            # Create ad groups & ads
            # -----------------------
            created_ad_groups = []
            created_ads = []

            for ag in data["ad_groups"]:

                ag_op = client.get_type("AdGroupOperation")
                ad_group = ag_op.create
                ad_group.name = ag["name"]
                ad_group.status = getattr(
                    client.enums.AdGroupStatusEnum,
                    ag.get("status", "ENABLED")
                )
                ad_group.campaign = campaign_id

                ag_response = ad_group_service.mutate_ad_groups(
                    customer_id=customer_id,
                    operations=[ag_op]
                )
                ad_group_id = ag_response.results[0].resource_name
                created_ad_groups.append(ad_group_id)

                for ad_data in ag["ads"]:
                    ad_op = client.get_type("AdGroupAdOperation")
                    ad_group_ad = ad_op.create
                    ad_group_ad.ad_group = ad_group_id
                    ad = ad_group_ad.ad

                    # Responsive Display Ad
                    rda = ad.responsive_display_ad

                    # Required: Business name
                    rda.business_name = "CompanyName"

                    # Required: Long headline
                    rda.long_headline.text = ad_data["headlines"][0]

                    # Headlines
                    for text in ad_data.get("headlines", []):
                        headline = client.get_type("AdTextAsset")
                        headline.text = text
                        rda.headlines.append(headline)

                    # Descriptions
                    for text in ad_data.get("descriptions", []):
                        desc = client.get_type("AdTextAsset")
                        desc.text = text
                        rda.descriptions.append(desc)

                    # Final URLs
                    for url in ad_data.get("final_urls", []):
                        ad.final_urls.append(url)

                    # Images (wide + square)
                    if "image_assets" in ad_data:

                        image_urls = set(ad_data["image_urls"])

                        for url in image_urls:
                            resp = requests.get(url, timeout=10)
                            validation = self.validate_proportion(resp.content)

                            if validation:
                                upload_result, status = GoogleAdsUploadImageUseCase().execute(
                                    user_id,
                                    customer_id,
                                    resp.content
                                )

                                asset_resource_name = upload_result["asset_resource_name"]

                                img = Image.open(BytesIO(resp.content))
                                width, height = img.size
                                ratio = width / height

                                if abs(ratio - 1.91) <= 0.03:
                                    # Wide 1.91:1
                                    marketing_image = client.get_type("AdImageAsset")
                                    marketing_image.asset = asset_resource_name
                                    rda.marketing_images.append(marketing_image)

                                elif abs(ratio - 1) <= 0.03:
                                    # Square 1:1
                                    square_image = client.get_type("AdImageAsset")
                                    square_image.asset = asset_resource_name
                                    rda.square_marketing_images.append(square_image)

                    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED

                    ad_response = ad_group_ad_service.mutate_ad_group_ads(
                        customer_id=customer_id,
                        operations=[ad_op]
                    )
                    created_ads.append(ad_response.results[0].resource_name)

            return {
                "budget": budget_id,
                "campaign": campaign_id,
                "ad_groups": created_ad_groups,
                "ads": created_ads
            }, 201

        except GoogleAdsException as e:
            return {
                'ok': 0,
                'message': {
                    'text': {
                        'error_user_title': e.error.code().name if hasattr(e, "error") else "GOOGLE_ADS_ERROR",
                        'error_user_msg': "; ".join([err.message for err in e.failure.errors])
                    }
                }
            }

        except Exception as e:
            return {
                'ok': 0,
                'message': {
                    'text': {
                        'error_user_title': "Internal Server Error",
                        'error_user_msg': "; ".join([err.message for err in e.failure.errors])
                    }
                }
            }

    def apply_objective(self, campaign, objective, client):

        if objective in ("SALES", "LEADS"):
            campaign.maximize_conversions = client.get_type("MaximizeConversions")()

        elif objective in ("WEBSITE_TRAFFIC", "BRAND_AWARENESS_AND_REACH", "PRODUCT_AND_BRAND_CONSIDERATION"):
            campaign.manual_cpc = client.get_type("ManualCpc")
            campaign.manual_cpc.enhanced_cpc_enabled = False

        else:
            campaign.manual_cpc = client.get_type("ManualCpc")
            campaign.manual_cpc.enhanced_cpc_enabled = False

    def validate_proportion(self, image_bytes: bytes) -> dict:
        try:
            img = Image.open(BytesIO(image_bytes))
            width, height = img.size
            ratio = width / height

            TOL = 0.03

            is_square = abs(ratio - 1) <= TOL
            is_landscape_191 = abs(ratio - 1.91) <= TOL

            if is_square or is_landscape_191:
                return True

            return False

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "message": "Error leyendo la imagen"
            }


class GoogleAdsListCustomersUseCase:
    def execute(self, user_id: str):
        try:
            client = build_ads_service(user_id)

            customer_service = client.get_service("CustomerService")
            response = customer_service.list_accessible_customers()

            ga_service = client.get_service("GoogleAdsService")

            customers = []

            for resource_name in response.resource_names:
                customer_id = resource_name.split("/")[1]

                query = """
                    SELECT customer.id, customer.descriptive_name
                    FROM customer
                    LIMIT 1
                """

                results = ga_service.search(customer_id=customer_id, query=query)

                for row in results:
                    customers.append({
                        "id": row.customer.id,
                        "name": row.customer.descriptive_name,
                    })

            return {
                "customers": customers,
                "count": len(customers)
            }, 200

        except GoogleAdsException as ex:
            return {
                "error": "Google Ads API error",
                "details": [e.message for e in ex.failure.errors],
            }, 400

        except Exception as e:
            return {
                "error": str(e),
            }, 500

class GoogleAdsUploadImageUseCase:
    def execute(self, user_id: str, customer_id: str, image_bytes: bytes):
        try:
            if not isinstance(image_bytes, (bytes, bytearray)):
                raise ValueError("image_bytes debe ser bytes")

            client = build_ads_service(user_id)
            asset_service = client.get_service("AssetService")

            asset_operation = client.get_type("AssetOperation")
            asset = asset_operation.create

            asset.name = f"Image Asset {uuid4()}"
            asset.image_asset.data = image_bytes

            response = asset_service.mutate_assets(
                customer_id=customer_id,
                operations=[asset_operation]
            )

            asset_resource_name = response.results[0].resource_name

            return {
                "asset_resource_name": asset_resource_name,
                "message": "Imagen subida correctamente"
            }, 201

        except GoogleAdsException as ex:
            return {
                "error": "Google Ads API error",
                "details": [e.message for e in ex.failure.errors],
            }, 400

        except Exception as e:
            return {"error": str(e)}, 500

import pdb

class GoogleAdsListLocationsUseCase:
    def execute(self, user_id: str, query: str):
        try:
            client = build_ads_service(user_id)
            ga_service = client.get_service("GoogleAdsService")

            q = f"""
                SELECT
                  geo_target_constant.id,
                  geo_target_constant.name,
                  geo_target_constant.canonical_name,
                  geo_target_constant.target_type,
                  geo_target_constant.status
                FROM geo_target_constant
                WHERE geo_target_constant.name LIKE '%{query}%'
                ORDER BY geo_target_constant.name
                LIMIT 50
            """

            response = ga_service.search_stream(
                customer_id=GOOGLE_ADS_MANAGER_ID,
                query=q
            )

            locations = []
            for batch in response:
                for row in batch.results:
                    g = row.geo_target_constant
                    locations.append({
                        "id": g.id,
                        "name": g.name,
                        "canonical_name": g.canonical_name
                    })

            return {
                "locations": locations,
                "count": len(locations),
            }, 200

        except GoogleAdsException as ex:
            return {
                "error": "Google Ads API error",
                "details": [e.message for e in ex.failure.errors],
            }, 400
        except Exception as e:
            return {"error": str(e)}, 500

class GoogleAdsListInterestsUseCase:
    def execute(self, user_id: str, query: str):
        try:
            client = build_ads_service(user_id)
            ga_service = client.get_service("GoogleAdsService")

            q = f"""
                SELECT
                  user_interest.user_interest_id,
                  user_interest.name,
                  user_interest.availabilities
                FROM user_interest
                WHERE user_interest.name LIKE '%{query}%'
                LIMIT 50
            """

            response = ga_service.search_stream(
                customer_id=GOOGLE_ADS_MANAGER_ID,
                query=q
            )

            interests = []
            for batch in response:
                for row in batch.results:
                    ui = row.user_interest
                    interests.append({
                        "id": ui.user_interest_id,
                        "name": ui.name
                    })

            return {
                "interests": interests,
                "count": len(interests),
            }, 200

        except GoogleAdsException as ex:
            return {
                "error": "Google Ads API error",
                "details": [e.message for e in ex.failure.errors],
            }, 400

        except Exception as e:
            return {"error": str(e)}, 500

class GoogleAdsListIncomeRangesUseCase:
    def execute(self):
        try:
            ranges = [
                {"id": 510001, "name": "INCOME_RANGE_LOWER_50_PERCENT"},
                {"id": 510002, "name": "INCOME_RANGE_50_TO_60"},
                {"id": 510003, "name": "INCOME_RANGE_60_TO_70"},
                {"id": 510004, "name": "INCOME_RANGE_70_TO_80"},
                {"id": 510005, "name": "INCOME_RANGE_80_TO_90"},
                {"id": 510006, "name": "INCOME_RANGE_UPPER_10_PERCENT"},
                {"id": 510000, "name": "INCOME_RANGE_UNDETERMINED"},
            ]

            return {"income_ranges": ranges}, 200

        except Exception as e:
            return {"error": str(e)}, 500

class GoogleAdsListAgeRangesUseCase:
    def execute(self):
        try:
            ranges = [
                {"id": 503001, "name": "AGE_RANGE_18_24"},
                {"id": 503002, "name": "AGE_RANGE_25_34"},
                {"id": 503003, "name": "AGE_RANGE_35_44"},
                {"id": 503004, "name": "AGE_RANGE_45_54"},
                {"id": 503005, "name": "AGE_RANGE_55_64"},
                {"id": 503006, "name": "AGE_RANGE_65_UP"},
                {"id": 503000, "name": "AGE_RANGE_UNDETERMINED"},
            ]

            return {"age_ranges": ranges}, 200

        except Exception as e:
            return {"error": str(e)}, 500

class GoogleAdsListGenderTypesUseCase:
    def execute(self):
        try:
            genders = [
                {"id": 1, "name": "MALE"},
                {"id": 2, "name": "FEMALE"},
                {"id": 10, "name": "UNKNOWN"},
                {"id": 11, "name": "UNDISCLOSED"},
            ]

            return {"gender_types": genders}, 200

        except Exception as e:
            return {"error": str(e)}, 500

