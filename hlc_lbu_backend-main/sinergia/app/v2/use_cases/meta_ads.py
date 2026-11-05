import requests
import uuid
import os
import json
import yaml
import urllib.parse
import logging
import mimetypes
import time
import zipfile
import re
import unicodedata

from app import redis_client
from flask import Response
from typing import List, TypedDict, Any, Dict, Optional, Set, Tuple
from cerberus import Validator
from app.exceptions.base import IncorrectValidationException, RESTClientException, NotAccessException, DataNotFoundException, StrapiException,\
    ParametersNotFoundException, SinergiaException, PermissionDeniedException, RateLimitExceededException, MetaException
from datetime import datetime, timezone, timedelta
from PIL import Image
from io import BytesIO
from app.v2.use_cases.facebook_validator_service import CreativeType, MetaAdsPayloadBuilder, MetaAdsValidator, AssetFeedSpec,\
    ObjectStorySpec, CampaignObjective, SalesOptimizationGoal, LeadsOptimizationGoal, AwarenessOptimizationGoal,\
    LEADS_ALLOWED_CONVERSION_EVENTS
from app.v2.repository.ad_channel import AdChannelRepository
from app.v2.repository.campaign_channel_publish import CampaignChannelPublishRepository
from app.v2.repository.campaign import CampaignRepository
from app.v2.repository.account import AccountRepository
from app.v2.repository.ad_set import AdSetRepository
from collections import defaultdict

_ZERO_DECIMAL_CURRENCIES = {
    "COP",  # Peso Colombiano
    "CLP",  # Peso Chileno
    "JPY",  # Yen Japonés
    "KRW",  # Won Surcoreano
    "VND",  # Dong Vietnamita
    "PYG",  # Guaraní Paraguayo
    "UGX",  # Shilling Ugandé s
    "BIF",  # Franco Burundés
    "DJF",  # Franco Yibutiano
    "GNF",  # Franco Guineano
    "KMF",  # Franco Comorense
    "MGA",  # Ariary Malgache
    "RWF",  # Franco Ruandés
    "VUV",  # Vatu Vanuatuense
    "XAF",  # Franco CFA de África Central
    "XOF",  # Franco CFA de África Occidental
    "XPF"   # Franco CFP
}

class CampaignDataDict(TypedDict, total=False):
    page_id: str
    ad_account_id: str
    objective: str
    optimization_goal: str
    pixel_id: Optional[str]
    lead_gen_form_id: Optional[str]
    whatsapp_number_id: Optional[str]
    conversion_event: Optional[str]

class PreCheckDataDict(TypedDict):
    brand_id: int
    campaign_id: int
    adset_id: int
    ad_id: int
    adchannel_id: int
    images: List[Dict[str, Any]]
    bodies: List[Dict[str, Any]]
    titles: List[Dict[str, Any]]
    descriptions: List[Dict[str, Any]]
    call_to_action_types: List[Dict[str, Any]]
    daily_budget: int
    proposal_url: str

class ExportAssetsDataDict(TypedDict):
    brand_id: int
    campaign_id: int
    adset_id: int
    ad_id: int
    adchannel_id: int

logger = logging.getLogger(__name__)


def _get_page_access_token_helper(graph_api_base: str, user_access_token: str, page_id: str) -> str:
    url = f"{graph_api_base}/me/accounts"
    params = {"access_token": user_access_token}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if "data" in data:
            for page in data["data"]:
                if str(page.get("id")) == str(page_id):
                    return page.get("access_token")
    except Exception as e:
        logger.error(f"Error fetching page access token via /me/accounts: {e}")
    return None

def _get_meta_currency_offset(currency_code: str) -> int:
    """
    Retorna el offset correspondiente para Meta Ads API.
    Si la moneda no tiene decimales retorna 1, de lo contrario retorna 100.
    """
    
    # Comprobar la moneda (asegurando mayúsculas)
    if currency_code.upper() in _ZERO_DECIMAL_CURRENCIES:
        return 1
    
    # Comportamiento por defecto seguro para el 95% de las monedas del mundo (USD, EUR, MXN, etc.)
    return 100


def _is_leads_offsite(objective: Optional[str], optimization_goal: Optional[str]) -> bool:
    """True solo para la combinación OUTCOME_LEADS + OFFSITE_CONVERSIONS."""
    return (objective == CampaignObjective.LEADS.value
            and optimization_goal == LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value)


def _normalize_conversion_event(value: Any) -> Optional[str]:
    """strip()+upper() si es str con contenido; None en cualquier otro caso. Nunca lanza."""
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip().upper()


def _is_blank(value: Any) -> bool:
    """None, '' o solo espacios => True."""
    return value is None or (isinstance(value, str) and not value.strip())


class FacebookAuthCallbackUseCase:
    def __init__(self):
        self.client_id = os.getenv("FACEBOOK_CLIENT_ID")
        self.client_secret = os.getenv("FACEBOOK_CLIENT_SECRET")
        self.redirect_uri = os.getenv("FACEBOOK_REDIRECT_URI")
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, code: str, user_id: str):
        url = f"{self.graph_api_base}/oauth/access_token"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "client_secret": self.client_secret,
            "code": code,
        }

        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        access_token = data.get("access_token")
        redis_key = f"facebook_access_token:{user_id}"
        redis_client.set(redis_key, access_token)

        return {
            "message": f"Facebook access token stored successfully for user {user_id}.",
            "access_token": access_token,
            "expires_in": 0
        }, 200

class FacebookPublishCampaignUseCase(object):
    def __init__(self, user_id, campaign_id, complete_campaign_data, creative_type):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = complete_campaign_data.get('ad_account_id')
        self.page_id = complete_campaign_data.get('page_id')
        self.objective = complete_campaign_data.get('objective')
        self.optimization_goal = complete_campaign_data.get('optimization_goal')
        self.campaign_id = campaign_id
        self.creative_type = creative_type
        self.user_id = user_id

    def execute(self):
        builder = MetaAdsPayloadBuilder(
            self.campaign_id,
            self.objective,
            self.optimization_goal,
            self.creative_type,
        )

        builder.select_ad_account(self.ad_account_id)
        builder.select_page(self.page_id)

        self.payload = builder.build_meta_payload()['campaign']

        daily_budget = self._daily_budget()
        builder.set_daily_budget(daily_budget)

        redis_key = f"facebook_access_token:{self.user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            raise NotAccessException('Access token not found. Please re-authenticate.')

        decoded_access_token = access_token.decode("utf-8")

        created_campaign_id = None
        created_ad_creative_ids = []

        try:
            campaign = self.create_campaign(decoded_access_token)
            created_campaign_id = campaign['id']

            for ad_set in self.payload['ad_sets']:
                ad_set['campaign_id'] = created_campaign_id

                ad_set_resp = self.create_adset(ad_set, decoded_access_token)
                ad_set_id = ad_set_resp['id']
                ad_set['id'] = ad_set_id

                for ad in ad_set['ads']:
                    asset_feed = ad['adCreative']['asset_feed_spec'] if ad['adCreative'] else None
                    object_story_spec = ad['adCreative']['object_story_spec'] if ad['adCreative'] else None

                    ad['adset_id'] = ad_set_id

                    if self.creative_type == CreativeType.DYNAMIC.value and asset_feed and asset_feed['images'] and len(asset_feed['images']) > 0:
                        uploaded_images = []

                        for index, value in enumerate(asset_feed['images']):
                            hash = value.get('hash', None)
                            if not hash:
                                hash = self.upload_image(value['url'], decoded_access_token)

                            if hash:
                                uploaded_images.append({'hash': hash})

                        ad['adCreative']['asset_feed_spec']['images'] = uploaded_images

                    if self.creative_type == CreativeType.STANDARD.value and object_story_spec:
                        image_url = object_story_spec['link_data']['image_url']
                        hash = self.upload_image(image_url, decoded_access_token)
                        if hash:
                            object_story_spec['link_data']['image_hash'] = hash

                        object_story_spec['link_data'].pop('image_url', None)
                    ad_creative_resp = self.create_ad_creative(ad['adCreative'], decoded_access_token)
                    ad_creative_id = ad_creative_resp['id']
                    ad['creative']['creative_id'] = ad_creative_id
                    created_ad_creative_ids.append(ad_creative_id)

                    ad_resp = self.create_ad(ad, decoded_access_token)

                    logger.info(f"Ad created: {ad_resp['id']}")

            return {'success': True}

        except Exception as e:
            logger.error(f"Error publishing campaign: {e}")
            self.rollback(created_campaign_id, created_ad_creative_ids, decoded_access_token)
            raise e

    def _daily_budget(self):
        ad_account_info, status = FacebookGetAdAccountDetailsUseCase().execute(self.user_id, self.ad_account_id)
        minimum_budgets_allowed, status = FacebookMinimumBudgetUseCase().execute(self.user_id, self.ad_account_id)
        for budget in minimum_budgets_allowed['data']:
            if budget['currency'] == ad_account_info['currency']:
                return budget['min_daily_budget_imp']

    def _get_pixel(self):
        data, status = FacebookGetPixelUseCase().execute(self.user_id, self.ad_account_id)
        return data['data'][0]['id']

    def rollback(self, campaign_id, creative_ids, access_token):
        logger.info("Starting rollback process...")

        # 1. Delete Campaign (Cascades to AdSets and Ads)
        if campaign_id:
            logger.info(f"Rolling back: Deleting campaign {campaign_id}")
            self.delete_object(campaign_id, access_token)

        # 2. Delete Ad Creatives (Must be done after ads are deleted)
        if creative_ids:
            logger.info(f"Rolling back: Deleting {len(creative_ids)} ad creatives")
            for cid in creative_ids:
                self.delete_object(cid, access_token)

    def delete_object(self, object_id, access_token):
        try:
            url = f"{self.graph_api_base}/{object_id}"
            params = {"access_token": access_token}
            response = requests.delete(url, params=params)

            if response.status_code == 200:
                logger.info(f"Successfully deleted object {object_id}")
            else:
                logger.error(f"Failed to delete object {object_id}. Status: {response.status_code}, Body: {response.text}")
        except Exception as e:
             logger.error(f"Exception while deleting object {object_id}: {e}")

    def create_campaign(self, access_token):
        if self.payload['special_ad_categories'] is None:
            self.payload['special_ad_categories'] = []

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/campaigns"

        payload = {
            "name": self.payload['name'],
            "objective": self.payload['objective'],
            "status": self.payload['status'],
            "buying_type": self.payload['buying_type'],
            "special_ad_categories": self.payload['special_ad_categories'],
            "is_adset_budget_sharing_enabled": False,
            "access_token": access_token
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        campaign = response.json()

        if "error" in campaign:
            logger.error(f"Error creating campaign: {campaign['error']}")
            raise RESTClientException(campaign["error"])

        logger.info(f"Campaign created: {campaign}")

        return campaign

    def create_adset(self, data, access_token):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adsets"
        date_time = datetime.now(timezone.utc)

        payload = {
            "name": data['name'],
            "campaign_id": data['campaign_id'],
            "daily_budget": data['daily_budget'],
            "billing_event": data['billing_event'],
            "optimization_goal": data['optimization_goal'],
            "bid_strategy": 'LOWEST_COST_WITHOUT_CAP',
            "is_dynamic_creative": True if self.creative_type == CreativeType.DYNAMIC.value else False,
            "targeting": {
                **data['targeting'],
                "targeting_automation": {
                    "advantage_audience": 0
                }
            },
            "start_time": date_time.isoformat(timespec='milliseconds'),
            "end_time": (date_time + timedelta(days=7)).isoformat(timespec='milliseconds'),
            "status": data['status'],
            "access_token": access_token
        }

        pixel_id = self._get_pixel()
        if pixel_id:
            payload["promoted_object"] = {
                "pixel_id": pixel_id,
                "custom_event_type": "CONTENT_VIEW"
            }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        json_response = response.json()

        if "error" in json_response:
            logger.error(f"Error creating adset: {json_response['error']}")
            raise RESTClientException(json_response["error"])

        logger.info(f"Adset created: {json_response}")
        return json_response

    def upload_image(self, url, access_token):
        try:
            resp = requests.get(url, timeout=10)

            if resp.status_code != 200:
                logger.error(f"Error fetching image: {resp.status_code}")
                return None
                # raise RESTClientException(f"Error fetching image: {resp.status_code}")

            image_data = BytesIO(resp.content)
            img = Image.open(image_data)
            width, height = img.size

            if width > 1080 or height > 1080:
                logger.error(f"Image dimensions are too large: {width}x{height}")
                return None
                # raise RESTClientException({'message': 'Image dimensions are too large. Maximum size is 1080x1080 pixels.'})

            if width < 600 or height < 600:
                logger.error(f"Image dimensions are too small: {width}x{height}")
                return None

            image_format = img.format.lower()
            dummy_filename = f"ad_image.{image_format}"
            mime_type, _ = mimetypes.guess_type(dummy_filename)

            url = f"{self.graph_api_base}/act_{self.ad_account_id}/adimages"
            files = {"filename": (dummy_filename, resp.content, mime_type)}
            data = {"access_token": access_token}

            response = requests.post(url, files=files, data=data)
            json_response = response.json()

            if "error" in json_response:
                logger.error(f"Error uploading image: {json_response['error']}")
                return None
                # raise RESTClientException(json_response["error"])

            logger.info(f"Image uploaded: {json_response}")
            hash = json_response['images'][dummy_filename]['hash']
            logger.info(f"Image hash: {hash}")
            return hash

        except Exception as e:
            logger.error(f"Error fetching image: {e}")
            return None
            # raise RESTClientException(f"Error fetching image: {e}")

    def create_ad_creative(self, data, access_token):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adcreatives"

        payload = {
            "name": data['name'],
            "object_story_spec": data['object_story_spec'],
            "access_token": access_token
        }

        if data['asset_feed_spec']:
            payload["asset_feed_spec"] = data['asset_feed_spec']
            payload["object_story_spec"].pop('link_data', None)

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        json_response = response.json()

        if "error" in json_response:
            logger.error(f"Error creating ad creative: {json_response['error']}")
            raise RESTClientException(json_response["error"])

        logger.info(f"Ad creative created: {json_response}")

        return json_response

    def create_ad(self, data, access_token):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/ads"

        payload = {
            "name": data['name'],
            "adset_id": data['adset_id'],
            "creative": data['creative'],
            "status": data['status'],
            "access_token": access_token
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        json_response = response.json()

        if "error" in json_response:
            logger.error(f"Error creating ad: {json_response['error']}")
            raise RESTClientException(json_response["error"])

        logger.info(f"Ad created: {json_response}")

        return json_response

class FacebookCreateCampaignUseCase:
    def __init__(self, ad_account_id: str):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = ad_account_id

    def execute(self, name: str, objective: str,
                status: str = "PAUSED", buying_type: str = "AUCTION",
                special_ad_categories: list = None, user_id: str = None):
        """
        Crea una campaña en Meta Ads usando el access_token ya obtenido.

        :param access_token: Token de acceso devuelto por FacebookAuthCallbackUseCase
        :param name: Nombre de la campaña
        :param objective: Objetivo (ej: OUTCOME_TRAFFIC, OUTCOME_ENGAGEMENT, etc.)
        :param status: Estado inicial de la campaña (default: PAUSED)
        :param buying_type: Tipo de compra (default: AUCTION)
        :param special_ad_categories: Lista de categorías especiales (default: [])
        """

        if special_ad_categories is None:
            special_ad_categories = []

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/campaigns"

        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        payload = {
            "name": name,
            "objective": objective,
            "status": status,
            "buying_type": buying_type,
            "special_ad_categories": special_ad_categories,
            "is_adset_budget_sharing_enabled": False,
            "access_token": access_token.decode("utf-8")
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookCreateAdSetUseCase:
    def __init__(self, ad_account_id: str):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = ad_account_id

    def execute(self, name: str, campaign_id: str, daily_budget: str,
                billing_event: str, optimization_goal: str,
                bid_strategy: str, targeting: dict, targeting_automation: dict,
                start_time: str, end_time: str,
                status: str = "PAUSED", user_id: str = None):
        """
        Crea un Ad Set en Meta Ads usando el access_token almacenado en Redis.
        """
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adsets"

        payload = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": daily_budget,
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "bid_strategy": bid_strategy,
            "is_dynamic_creative": True,
            "targeting": {
                **targeting,
                "targeting_automation": {
                    "advantage_audience": 0
                }
            },
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "access_token": access_token
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookGetAdAccountsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        url = f"{self.graph_api_base}/me/adaccounts"
        params = {
            "access_token": access_token,
            "fields": "id,account_id,name,account_status,account_currency,timezone_name",
        }

        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookCreateAdCreativeUseCase:
    def __init__(self, ad_account_id: str):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = ad_account_id

    def execute(
        self,
        name: str,
        user_id: str = None,
        asset_feed_spec: dict = None,
        object_story_spec: dict = None,
        creative_asset_groups: dict = None
    ):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adcreatives"

        payload = {
            "name": name,
            "object_story_spec": object_story_spec,
            # "creative_asset_groups_spec": {
            #    "ad_creative_asset_groups": creative_asset_groups
            # },
            "access_token": access_token
        }

        if asset_feed_spec:
            payload["asset_feed_spec"] = asset_feed_spec

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookUploadImageUseCase:
    def __init__(self, ad_account_id: str):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = ad_account_id

    def execute(self, file_storage, user_id: str = None):
        """
        Uploads an image to the Facebook Ad Account and returns its hash.
        """
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adimages"

        files = {"filename": (file_storage.filename, file_storage.stream, file_storage.mimetype)}
        data = {
            "access_token": access_token
        }

        response = requests.post(url, files=files, data=data)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookCreateAdUseCase:
    def __init__(self, ad_account_id: str):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.ad_account_id = ad_account_id

    def execute(self, name: str, adset_id: str, creative: dict, status: str = "PAUSED", user_id: str = None):
        """
        Crea un Ad en Meta Ads conectando un AdSet con un Creative.
        """
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/ads"

        payload = {
            "name": name,
            "adset_id": adset_id,
            "creative": creative,
            "status": status,
            "access_token": access_token
        }

        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookGetPagesUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/me/accounts"
        params = {"access_token": access_token}

        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        if "data" in data:
            for page in data["data"]:
                page.pop("access_token", None)

        return data, 200

class FacebookGetPageLeadgenFormsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, page_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            logger.error("No access token found in Redis for user_id: %s", user_id)
            raise MetaException("META003", "No access token found in Redis. Please re-authenticate.")

        access_token = access_token.decode("utf-8")

        page_access_token = _get_page_access_token_helper(self.graph_api_base, access_token, page_id)
        if not page_access_token:
            logger.warning(f"Could not retrieve page access token for page {page_id} from /me/accounts. Falling back to user access token.")

        url = f"{self.graph_api_base}/{page_id}/leadgen_forms"
        params = {
            # "status": "ACTIVE",
            "fields": "id,name,status",
            "access_token": page_access_token or access_token
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()

            if response.status_code != 200:
                error_type = response.json().get('error', {}).get('type', 'OAuthException')
                error_message = response.json().get('error', {}).get('message', '')
                logger.error(f"Facebook API error - Type: {error_type} - Message: {error_message}")
                raise MetaException("META005", f"Facebook API error - Type: {error_type} - Message: {error_message}")

            data = response.json().get("data", [])
            # Filtramos en caliente para dejar SOLO los formularios aptos para publicar
            forms = [
                {
                    "id": form["id"],
                    "name": form["name"]
                }
                for form in data if form.get("status") == "ACTIVE"
            ]

            return forms
        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Facebook Graph API: %s", str(e))
            raise MetaException("META004", "Failed to connect to Facebook Graph API. Please try again later.")

class FacebookGetPageWhatsAppNumbersUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def _resolve_waba_id(self, page_id, access_token, page_access_token=None):
        token_to_use = page_access_token or access_token
        
        # 1. Try to get WABAs assigned to the user directly
        url = f"{self.graph_api_base}/me/assigned_whatsapp_business_accounts"
        try:
            res = requests.get(url, params={"access_token": access_token}, timeout=10)
            data = res.json()
            logger.info(f"User assigned WABAs lookup response: {data}")
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0].get("id")
        except Exception as e:
            logger.error(f"Error querying user assigned WABAs: {e}")

        # 2. Try to query the Page's owning business (using "business" field)
        url = f"{self.graph_api_base}/{page_id}"
        try:
            res = requests.get(url, params={"fields": "business", "access_token": token_to_use}, timeout=10)
            data = res.json()
            logger.info(f"Page business owner lookup response for page {page_id}: {data}")
            business_id = data.get("business", {}).get("id")
            if business_id:
                url_waba = f"{self.graph_api_base}/{business_id}/owned_whatsapp_business_accounts"
                res_waba = requests.get(url_waba, params={"access_token": access_token}, timeout=10)
                data_waba = res_waba.json()
                logger.info(f"Business owned WABAs lookup response for business {business_id}: {data_waba}")
                if "data" in data_waba and len(data_waba["data"]) > 0:
                    return data_waba["data"][0].get("id")
        except Exception as e:
            logger.error(f"Error resolving WABA via page business: {e}")

        # 3. Try listing all businesses the user has access to, and check their WABAs
        url = f"{self.graph_api_base}/me/businesses"
        try:
            res = requests.get(url, params={"access_token": access_token}, timeout=10)
            data = res.json()
            logger.info(f"User businesses lookup response: {data}")
            if "data" in data:
                for biz in data["data"]:
                    biz_id = biz.get("id")
                    url_waba = f"{self.graph_api_base}/{biz_id}/owned_whatsapp_business_accounts"
                    res_waba = requests.get(url_waba, params={"access_token": access_token}, timeout=10)
                    data_waba = res_waba.json()
                    logger.info(f"Business {biz_id} owned WABAs lookup: {data_waba}")
                    if "data" in data_waba and len(data_waba["data"]) > 0:
                        return data_waba["data"][0].get("id")
        except Exception as e:
            logger.error(f"Error listing user businesses for WABA: {e}")

        return None

    def execute(self, user_id: str, page_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        page_access_token = _get_page_access_token_helper(self.graph_api_base, access_token, page_id)

        waba_id = self._resolve_waba_id(page_id, access_token, page_access_token)
        if not waba_id:
            return {"error": "Could not find a linked WhatsApp Business Account (WABA) for this page."}, 404

        url = f"{self.graph_api_base}/{waba_id}/phone_numbers"
        params = {"access_token": access_token}

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if "error" in data:
                return {"error": data["error"]}, 400
            return data, 200
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to connect to Facebook Graph API", "details": str(e)}, 502

class FacebookValidateTokenUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.client_id = os.getenv("FACEBOOK_CLIENT_ID")
        self.client_secret = os.getenv("FACEBOOK_CLIENT_SECRET")

    def execute(self, user_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "is_valid": False,
                "message": "No access token found in Redis. Please re-authenticate.",
                "expires_at": None
            }, 200

        access_token = access_token.decode("utf-8")
        app_token = f"{self.client_id}|{self.client_secret}"

        url = f"{self.graph_api_base}/debug_token"
        params = {
            "input_token": access_token,
            "access_token": app_token
        }

        try:
            response = requests.get(url, params=params)
            data = response.json()

            is_valid = data.get("data", {}).get("is_valid", False)
            expires_at = data.get("data", {}).get("expires_at")

            return {
                "is_valid": is_valid,
                "expires_at": expires_at,
                "raw": data
            }, 200

        except Exception as e:
            return {
                "is_valid": False,
                "message": f"Error validating token: {str(e)}",
                "expires_at": None
            }, 200

class FacebookRemoveRedisTokenUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.client_id = os.getenv("FACEBOOK_CLIENT_ID")
        self.client_secret = os.getenv("FACEBOOK_CLIENT_SECRET")

    def execute(self, user_id: str):
        redis_key = f"facebook_access_token:{user_id}"

        if redis_client.exists(redis_key):
            redis_client.delete(redis_key)
            return {"message": f"Redis key '{redis_key}' removed."}, 200
        else:
            return {"message": f"Redis key '{redis_key}' not found."}, 404

class S3ImageProxyUseCase:
    def __init__(self):
        pass

    def execute(self, url: str):
        s3_url = url

        try:
            resp = requests.get(s3_url, timeout=10)
        except requests.RequestException as e:
            return Response(f"Error connecting to S3: {e}", status=500)

        if resp.status_code != 200:
            return Response(f"Error fetching image: {resp.status_code}", status=resp.status_code)

        return Response(resp.content, content_type=resp.headers.get('Content-Type'))

class FacebookSearchUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
    def execute(self, user_id: str, type: str = None, query: str = None, location_types: List[str] = None):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/search"
        params = {
            "access_token": access_token,
            "type": type,
            "q": query,
            "limit": 500
        }

        if location_types:
            params["location_types"] = location_types

        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        if "data" in data:
            for page in data["data"]:
                page.pop("access_token", None)

        return data, 200

class FacebookGetAdAccountDetailsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, ad_account_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}"
        params = {
            "access_token": access_token,
            "fields": ",".join([
                "id",
                "account_id",
                "name",
                "account_status",
                "currency",
                "timezone_name",
                "created_time",
                "owner",
                "business",
            ])
        }

        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return {"error": data["error"]}, 400

        return data, 200

class FacebookTestCreativeUploadUseCase:
    def __init__(self, campaign_id: str, user_id: str, complete_campaign_data: CampaignDataDict = None, creative_type: str = ''):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.campaign_id = campaign_id
        self.user_id = user_id
        self.ad_account_id = complete_campaign_data.get('ad_account_id')
        self.page_id = complete_campaign_data.get('page_id')
        self.objective = complete_campaign_data.get('objective')
        self.optimization_goal = complete_campaign_data.get('optimization_goal')
        self.lead_gen_form_id = complete_campaign_data.get('lead_gen_form_id') if complete_campaign_data else None
        self.whatsapp_number_id = complete_campaign_data.get('whatsapp_number_id') if complete_campaign_data else None
        self.pixel_id = complete_campaign_data.get('pixel_id') if complete_campaign_data else None
        self.conversion_event = _normalize_conversion_event(
            complete_campaign_data.get('conversion_event') if complete_campaign_data else None
        )
        self.creative_type = creative_type
        self.billing_event = None
        self.channel_id = None

    def _get_decoded_access_token(self):
        redis_key = f"facebook_access_token:{self.user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            raise NotAccessException("No access token found in Redis. Please re-authenticate.")

        return access_token.decode("utf-8")
    
    def _build_meta_payload(self):
        builder = MetaAdsPayloadBuilder(self.campaign_id, self.objective, self.optimization_goal, self.creative_type)

        if self.ad_account_id: builder.select_ad_account(self.ad_account_id)
        if self.page_id: builder.select_page(self.page_id)
        self.billing_event = builder.get_billing_event()

        try:
            payload = builder.build_meta_payload()
            self.channel_id = builder.get_channel_id()
            return payload
        except Exception as e:
            logger.error(f"Error fetching/building Strapi payload: {e}")
            raise StrapiException(f"Failed to build payload from Strapi: {str(e)}")
        
    def _get_ad_account_id(self, campaign_data):
        ad_account_id = self.ad_account_id if self.ad_account_id else campaign_data.get('ad_account_id')

        if not ad_account_id:
            raise ParametersNotFoundException("No ad_account_id found. Please provide it in the body or link it to the campaign.")
        
        return ad_account_id

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()
        meta_payload = self._build_meta_payload()
        campaign_data = meta_payload.get('campaign', {})
        ad_account_id = self._get_ad_account_id(campaign_data)

        results = []
        ad_sets = campaign_data.get('ad_sets', [])

        for ad_set in ad_sets:
            ads = ad_set.get('ads', [])
            for ad in ads:
                ad_name = ad.get('name', 'Unknown')
                current_ad_errors = []

                ad_creative = ad.get('adCreative')
                if not ad_creative:

                    current_ad_errors.append({
                        'slug': 'missing-creative-error',
                        'message': "No creative found"
                    })
                    results.append({"ad_name": ad_name, "status": "Failed", "errors": current_ad_errors})
                    continue

                asset_feed = ad_creative.get('asset_feed_spec')
                story_spec = ad_creative.get('object_story_spec')

                if self.creative_type == "DYNAMIC" and asset_feed:

                    try:
                        titles = asset_feed.get('titles', [])
                        MetaAdsValidator.validate_text('title', [t.get('text') for t in titles])
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'title-error',
                            'message': f"Titles Error: {str(e)}"
                        })

                    try:
                        bodies = asset_feed.get('bodies', [])
                        MetaAdsValidator.validate_text('body', [b.get('text') for b in bodies])
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'body-error',
                            'message': f"Bodies Error: {str(e)}"
                        })

                    try:
                        descriptions = asset_feed.get('descriptions', [])
                        MetaAdsValidator.validate_text('description', [d.get('text') for d in descriptions])
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'description-error',
                            'message': f"Descriptions Error: {str(e)}"
                        })

                    ctas = asset_feed.get('call_to_action_types', [])
                    for cta in ctas:
                        try:
                            MetaAdsValidator.validate_cta(cta, self.objective)
                        except ValueError as e:
                            current_ad_errors.append({
                                'slug': 'cta-error',
                                'message': f"CTA Error ({cta}): {str(e)}"
                            })

                    images = asset_feed.get('images', [])
                    images_urls = [img.get('url') for img in images if img.get('url')]
                    try:
                        MetaAdsValidator.validate_images(images_urls)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'image-error',
                            'message': f"Images Error: {str(e)}"
                        })

                    try:
                        MetaAdsValidator.validate_assets_amount(asset_feed, self.creative_type, None)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'assets-amount-error',
                            'message': f"Assets Amount Error: {str(e)}"
                        })

                elif self.creative_type == "STANDARD" and story_spec:
                    link_data = story_spec.get('link_data')
                    if link_data:
                        cta_obj = link_data.get('call_to_action')
                        if cta_obj and isinstance(cta_obj, dict):
                            try:
                                MetaAdsValidator.validate_cta(cta_obj.get('type'), self.objective)
                            except ValueError as e:
                                current_ad_errors.append({
                                    'slug': 'cta-error',
                                    'message': f"CTA Error: {str(e)}"
                                })

                        image_url = link_data.get('image_url')
                        if image_url:
                            try:
                                MetaAdsValidator.validate_images(image_url)
                            except ValueError as e:
                                current_ad_errors.append({
                                    'slug': 'image-error',
                                    'message': f"Image Error: {str(e)}"
                                })
                        else:
                            current_ad_errors.append({
                                'slug': 'image-error',
                                'message': "Standard Creative missing image_url"
                            })

                        try:
                            MetaAdsValidator.validate_assets_amount(None, self.creative_type, story_spec=story_spec)
                        except ValueError as e:
                            current_ad_errors.append({
                                'slug': 'assets-amount-error',
                                'message': f"Standard Asset Error: {str(e)}"
                            })

                if current_ad_errors:
                    results.append({
                        "ad_name": ad_name,
                        "status": "Failed",
                        "errors": current_ad_errors
                    })
                    continue
            
                try:
                    if self.creative_type == "DYNAMIC" and asset_feed:
                        valid_images = []
                        for image in asset_feed.get('images', []):
                            image_url = image.get('url')
                            if image_url and not image.get('hash'):
                                    image_hash = self._upload_image(image_url, ad_account_id, decoded_access_token)
                                    if image_hash:
                                        image['hash'] = image_hash
                                        valid_images.append(image)
                                    else:
                                        raise Exception(f"Failed to upload image to FB: {image_url}")
                            elif image.get('hash'):
                                valid_images.append(image)
                        asset_feed['images'] = valid_images

                    elif self.creative_type == "STANDARD" and story_spec:
                        link_data = story_spec.get('link_data')
                        if link_data and link_data.get('image_url'):
                            image_hash = self._upload_image(link_data['image_url'], ad_account_id, decoded_access_token)
                            if image_hash:
                                link_data['image_hash'] = image_hash
                            else:
                                raise Exception(f"Failed to upload image to FB: {link_data['image_url']}")
                    
                    if self.page_id and ad_creative.get('object_story_spec'):
                        ad_creative['object_story_spec']['page_id'] = self.page_id

                    payload_asset_feed = asset_feed
                    if ad_creative.get('object_story_spec') and ad_creative['object_story_spec'].get('link_data'):
                        payload_asset_feed = None

                    creative_payload = {
                        "name": f"TEST_API_{ad_creative.get('name')}",
                        "object_story_spec": ad_creative.get('object_story_spec'),
                        "asset_feed_spec": payload_asset_feed,
                        "access_token": decoded_access_token
                    }

                    creative_payload = {k: v for k, v in creative_payload.items() if v is not None}

                    created_creative = self._create_ad_creative(creative_payload, ad_account_id)

                    if created_creative.get('error'):
                        raise Exception(f"Meta API Error: {created_creative['error'].get('message')}")

                    results.append({
                        "ad_name": ad_name,
                        "creative_id": created_creative.get('id'),
                        "status": "Created",
                        "meta_response": created_creative
                    })

                except Exception as e:
                    logger.error(f"Error processing ad execution {ad_name}: {e}")

                    results.append({
                        "ad_name": ad_name,
                        "status": "Failed",
                        "errors": [{
                            'slug': 'execution-error',
                            'message': f"Execution Error: {str(e)}"
                        }]
                    })

        has_errors = any(item.get('status') == 'Failed' for item in results)

        return {
            "ok": 0 if has_errors else 1,
            "data": results
        }, 200

    def _upload_image(self, url, ad_account_id, access_token):
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                logger.error(f"Error fetching image from URL {url}: {resp.status_code}")
                return None

            image_data = BytesIO(resp.content)
            img = Image.open(image_data)

            if img.width < 10 or img.height < 10:
                 pass

            image_format = img.format.lower() if img.format else 'jpeg'
            dummy_filename = f"ad_image_test.{image_format}"
            mime_type = mimetypes.guess_type(dummy_filename)[0] or "image/jpeg"

            api_url = f"{self.graph_api_base}/act_{ad_account_id}/adimages"
            files = {"filename": (dummy_filename, resp.content, mime_type)}
            data = {"access_token": access_token}

            response = requests.post(api_url, files=files, data=data)
            json_response = response.json()

            if "error" in json_response:
                logger.error(f"Error uploading image to Meta: {json_response['error']}")
                return None

            images = json_response.get("images", {})
            if images:
                 first_key = next(iter(images))
                 return images[first_key].get("hash")

            return None

        except Exception as e:
            logger.error(f"Exception uploading image: {e}")
            return None

    def _create_ad_creative(self, payload, ad_account_id):
        url = f"{self.graph_api_base}/act_{ad_account_id}/adcreatives"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        if response.status_code != 200:
             logger.error(f"Meta API Error ({response.status_code}): {response.text}")
        return response.json()

class FacebookGeneratePreCheckCreativeUseCase(FacebookTestCreativeUploadUseCase):
    _STANDARD_SUPPORTED_COMBINATIONS = {
        (CampaignObjective.AWARENESS.value, AwarenessOptimizationGoal.REACH.value),
        (CampaignObjective.LEADS.value, LeadsOptimizationGoal.LEAD_GENERATION.value),
        (CampaignObjective.LEADS.value, LeadsOptimizationGoal.CONVERSATIONS.value),
        (CampaignObjective.SALES.value, SalesOptimizationGoal.OFFSITE_CONVERSIONS.value),
        (CampaignObjective.LEADS.value, LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value),
    }

    def __init__(self, campaign_id: str, user_id: str, complete_campaign_data: CampaignDataDict = None, creative_type: str = ''):
        super().__init__(campaign_id, user_id, complete_campaign_data, creative_type)
        self.ad_channel_repository = AdChannelRepository()
        self.campaign_publish_repository = CampaignChannelPublishRepository()

    def _is_standard_combination_supported(self) -> bool:
        return (self.objective, self.optimization_goal) in self._STANDARD_SUPPORTED_COMBINATIONS

    def _validate_leads_offsite_params(self) -> None:
        """Valida pixel_id y conversion_event para OUTCOME_LEADS/OFFSITE_CONVERSIONS (Requirement 4).

        Orden: META012 (pixel_id blanco) -> META013 (evento ausente) -> META014 (evento no permitido).
        self.conversion_event ya está normalizado (strip + upper) desde el constructor.
        """
        combo = "OUTCOME_LEADS/OFFSITE_CONVERSIONS"
        if _is_blank(self.pixel_id):
            logger.error(f"Missing pixel_id for {combo}")
            raise MetaException("META012", f"pixel_id is required for {combo}")
        if self.conversion_event is None:
            logger.error(f"Missing conversion_event for {combo}")
            raise MetaException("META013", f"conversion_event is required for {combo}")
        if self.conversion_event not in LEADS_ALLOWED_CONVERSION_EVENTS:
            allowed = ", ".join(sorted(LEADS_ALLOWED_CONVERSION_EVENTS))
            logger.error(f"Invalid conversion_event '{self.conversion_event}' for {combo}")
            raise MetaException(
                "META014",
                f"conversion_event '{self.conversion_event}' is not allowed for {combo}. Allowed values: {allowed}",
            )

    @staticmethod
    def _standard_candidate_values(value):
        if isinstance(value, list):
            return value
        return [value] if value else []

    def _validate_standard_text_field(self, link_data, raw_value, field_name, annotation_key, error_slug, current_ad_errors):
        candidates = self._standard_candidate_values(raw_value)

        if len(candidates) != 1:
            link_data[annotation_key] = False
            current_ad_errors.append({
                'slug': error_slug,
                'message': f"{field_name.capitalize()} debe tener exactamente 1 valor, encontrados: {len(candidates)}",
            })
            return

        text_items = [{'text': candidates[0]}]
        MetaAdsValidator.is_valid_length(field_name, text_items)
        valid = text_items[0].get('valid_length', False)
        link_data[annotation_key] = valid

        if not valid:
            current_ad_errors.append({
                'slug': error_slug,
                'message': f"{field_name.capitalize()} '{candidates[0]}' no cumple la longitud requerida.",
            })

    def _validate_standard_image(self, link_data, current_ad_errors):
        candidates = self._standard_candidate_values(link_data.get('image_url'))

        if len(candidates) != 1:
            link_data['image_valid'] = False
            current_ad_errors.append({
                'slug': 'image-error',
                'message': f"Imagen debe tener exactamente 1 valor, encontrados: {len(candidates)}",
            })
            return

        images = [{'url': candidates[0]}]
        MetaAdsValidator.validate_images_precheck(images)
        valid = images[0].get('valid', False)
        error = images[0].get('error')

        link_data['image_valid'] = valid
        link_data['image_error'] = error

        if not valid:
            current_ad_errors.append({
                'slug': 'image-error',
                'message': f"Imagen inválida: {error}",
            })

    def _validate_standard_url(self, link_data, current_ad_errors):
        url = link_data.get('link')

        if not url:
            current_ad_errors.append({
                'slug': 'url-error',
                'message': "URL de destino ausente para el creativo STANDARD.",
            })
            return

        valid = MetaAdsValidator.is_valid_link_url(url)
        link_data['link_url_valid'] = valid

        if not valid:
            current_ad_errors.append({
                'slug': 'url-error',
                'message': f"URL '{url}' no tiene un formato válido.",
            })

    def _validate_leads_offsite_dynamic_url(self, asset_feed, current_ad_errors):
        """Valida link_urls DYNAMIC para OUTCOME_LEADS/OFFSITE_CONVERSIONS (Requirement 7.1–7.4).

        Normaliza website_url=None a '' (evita TypeError en _build_dynamic_creative_entry),
        une solo URLs no vacías y registra 'url-error' si falta o es inválida.
        """
        entries = [u for u in (asset_feed.get('link_urls') or []) if isinstance(u, dict)]
        for entry in entries:
            if 'website_url' in entry and entry['website_url'] is None:
                entry['website_url'] = ''
        urls = [e['website_url'] for e in entries if e.get('website_url')]

        if not urls:
            asset_feed['link_url_valid'] = False
            current_ad_errors.append({
                'slug': 'url-error',
                'message': "URL de destino ausente para el creativo DYNAMIC.",
            })
            return

        joined = ','.join(urls)
        valid = MetaAdsValidator.is_valid_link_url(joined)
        asset_feed['link_url_valid'] = valid

        if not valid:
            current_ad_errors.append({
                'slug': 'url-error',
                'message': f"URL '{joined}' no tiene un formato válido.",
            })

    def _validate_standard_daily_budget(self, ad_set, object_story_spec, min_budget, current_ad_errors):
        object_story_spec['min_daily_budget'] = min_budget
        try:
            object_story_spec['daily_budget_valid'] = (ad_set.get('daily_budget', 0) >= min_budget)
        except TypeError:
            current_ad_errors.append({
                'slug': 'daily-budget-error',
                'message': "El presupuesto diario no es comparable con el presupuesto mínimo requerido.",
            })

    def _validate_standard_cta(self, link_data, current_ad_errors):
        cta = link_data.get('call_to_action')

        if not cta:
            return  # Requirement 9.3: se omite sin error y sin anotación.

        if not isinstance(cta, dict):
            current_ad_errors.append({
                'slug': 'cta-error',
                'message': "call_to_action debe ser un diccionario.",
            })
            return  # Requirement 9.4: no es posible anotar 'valid' sobre un valor no-dict.

        cta_type = cta.get('type')
        if not isinstance(cta_type, dict):
            # Requirement 15.3: 'type' ausente o no-dict (None, str, list...) se
            # normaliza sin invocar al validador; conserva el valor original.
            cta_text = cta_type
            cta['type'] = {'value': cta_text, 'valid': False}
            valid = False
        else:
            # Requirement 15.1: se sobrescribe cualquier 'valid' recibido en la
            # entrada con el resultado real; 'value' queda intacto.
            cta_text = cta_type.get('value')
            valid = MetaAdsValidator.validate_cta_for_goal(
                cta_text=cta_text, objective=self.objective, goal=self.optimization_goal, throw=False,
            )
            cta_type['valid'] = valid

        # Requirement 15.2: mismo booleano en la raíz, para consumidores existentes.
        cta['valid'] = valid

        if not valid:
            current_ad_errors.append({
                'slug': 'cta-error',
                'message': f"CTA '{cta_text}' no permitido para el objetivo/optimización actuales.",
            })

    def _validate_standard_creative(self, ad_set, object_story_spec, min_budget, current_ad_errors):
        # Requirement 13: la combinación objetivo/optimización ya fue verificada
        # antes del bucle; si no fuera soportada, execute() habría lanzado
        # MetaException("META011", ...) y este método nunca se invocaría.

        # Decisión de diseño: link_data ausente se sustituye por un diccionario
        # vacío recién creado, reasignado a object_story_spec, para que las
        # anotaciones de Requirement 10 tengan siempre un destino mutable.
        link_data = object_story_spec.get('link_data')
        if link_data is None:
            link_data = {}
            object_story_spec['link_data'] = link_data

        self._validate_standard_text_field(
            link_data, link_data.get('name'), 'title', 'title_valid', 'title-error', current_ad_errors,
        )
        self._validate_standard_text_field(
            link_data, link_data.get('message'), 'body', 'body_valid', 'body-error', current_ad_errors,
        )
        self._validate_standard_text_field(
            link_data, link_data.get('description'), 'description', 'description_valid', 'description-error', current_ad_errors,
        )
        self._validate_standard_image(link_data, current_ad_errors)
        self._validate_standard_url(link_data, current_ad_errors)
        self._validate_standard_daily_budget(ad_set, object_story_spec, min_budget, current_ad_errors)
        self._validate_standard_cta(link_data, current_ad_errors)

    def _build_dynamic_creative_entry(self, idx, ad_set_to_publish, ad_creative):
        ads_to_publish = ad_set_to_publish.get('ads')[0]
        return {
            'idx': idx,
            'name': ad_set_to_publish.get('name'),
            'adset_id': ad_set_to_publish.get('id'),
            'ad_id': ads_to_publish.get('id'),
            'adchannel_id': ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0),
            # 'ad_account_id': ad_set_to_publish.get('ad_account_id'),
            'daily_budget': ad_set_to_publish.get('daily_budget'),
            #'targeting': ad_set_to_publish.get('targeting'),
            'images': [{'url': i.get('url'), 'valid': i.get('valid'), 'error': i.get('error')} for i in ad_creative.get('asset_feed_spec', {}).get('images', [])],
            'bodies': ad_creative.get('asset_feed_spec', {}).get('bodies', []),
            'titles': ad_creative.get('asset_feed_spec', {}).get('titles', []),
            'descriptions': ad_creative.get('asset_feed_spec', {}).get('descriptions', []),
            'call_to_action_types': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types', []),
            'images_valid_amount': ad_creative.get('asset_feed_spec', {}).get('images_valid_amount', False),
            'titles_valid_amount': ad_creative.get('asset_feed_spec', {}).get('titles_valid_amount', False),
            'bodies_valid_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_valid_amount', False),
            'descriptions_valid_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_valid_amount', False),
            'call_to_action_types_valid_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_valid_amount', False),
            'images_max_amount': ad_creative.get('asset_feed_spec', {}).get('images_max_amount', 0),
            'titles_max_amount': ad_creative.get('asset_feed_spec', {}).get('titles_max_amount', 0),
            'bodies_max_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_max_amount', 0),
            'descriptions_max_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_max_amount', 0),
            'call_to_action_types_max_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_max_amount', 0),
            'unique_titles': ad_creative.get('asset_feed_spec', {}).get('unique_titles', False),
            'unique_bodies': ad_creative.get('asset_feed_spec', {}).get('unique_bodies', False),
            'unique_descriptions': ad_creative.get('asset_feed_spec', {}).get('unique_descriptions', False),
            'daily_budget_valid': ad_creative.get('asset_feed_spec', {}).get('daily_budget_valid', False),
            'min_daily_budget': ad_creative.get('asset_feed_spec', {}).get('min_daily_budget', 0),
            # Req 16.4-16.5: skip only None website_url values (strings, '' included, join as before).
            'proposal_url': ','.join([
                u.get('website_url', '')
                for u in ad_creative.get('asset_feed_spec', {}).get('link_urls', [])
                if u.get('website_url', '') is not None
            ]),
            'proposal_url_valid': ad_creative.get('asset_feed_spec', {}).get('link_url_valid', False),
            'proposal_locations': ad_set_to_publish.get('proposal_locations', []),
            'locations': ad_creative.get('asset_feed_spec', {}).get('locations', []),
            'locations_valid': ad_creative.get('asset_feed_spec', {}).get('locations_valid', False),
            'promoted_object_valid': ad_creative.get('asset_feed_spec', {}).get('promoted_object_valid', False),
            #'billing_event': ad_set_to_publish.get('billing_event'),
            #'optimization_goal': ad_set_to_publish.get('optimization_goal'),

            #'ad_creative': ads_to_publish.get('adCreative')
        }

    def _build_standard_creative_entry(self, idx, ad_set_to_publish, ad):
        ad_creative = ad.get('adCreative') or {}
        object_story_spec = ad_creative.get('object_story_spec') or {}
        link_data = object_story_spec.get('link_data') or {}
        call_to_action = link_data.get('call_to_action') or {}
        if not isinstance(call_to_action, dict):
            call_to_action = {}

        image_url = link_data.get('image_url')
        images = [{
            'url': image_url,
            'valid': link_data.get('image_valid', False),
            'error': link_data.get('image_error'),
        }] if image_url else []

        def _as_single_item_list(value, valid_length):
            return [{'text': value, 'valid_length': valid_length}] if value else []

        title_valid = link_data.get('title_valid', False)
        body_valid = link_data.get('body_valid', False)
        description_valid = link_data.get('description_valid', False)

        return {
            'idx': idx,
            'name': f"{ad_set_to_publish.get('name')} - {ad.get('name')}",
            'adset_id': ad_set_to_publish.get('id'),
            'ad_id': ad.get('id'),
            'adchannel_id': object_story_spec.get('ad_channel_id', 0),
            'daily_budget': ad_set_to_publish.get('daily_budget'),
            'images': images,
            'bodies': _as_single_item_list(link_data.get('message'), link_data.get('body_valid', False)),
            'titles': _as_single_item_list(link_data.get('name'), link_data.get('title_valid', False)),
            'descriptions': _as_single_item_list(link_data.get('description'), link_data.get('description_valid', False)),
            'call_to_action_types': [call_to_action.get('type', {})] if call_to_action else [],
            'images_valid_amount': link_data.get('image_valid', False),
            'titles_valid_amount': title_valid,
            'bodies_valid_amount': body_valid,
            'descriptions_valid_amount': description_valid,
            'call_to_action_types_valid_amount': call_to_action.get('type', {}).get('valid', False) if call_to_action else False,
            'images_max_amount': 1,
            'titles_max_amount': 1,
            'bodies_max_amount': 1,
            'descriptions_max_amount': 1,
            'call_to_action_types_max_amount': 1,
            'unique_titles': title_valid,
            'unique_bodies': body_valid,
            'unique_descriptions': description_valid,
            'daily_budget_valid': object_story_spec.get('daily_budget_valid', False),
            'min_daily_budget': object_story_spec.get('min_daily_budget', 0),
            'proposal_url': link_data.get('link') or '',
            'proposal_url_valid': link_data.get('link_url_valid', False),
            'proposal_locations': ad_set_to_publish.get('proposal_locations', []),
            'locations': object_story_spec.get('locations', []),
            'locations_valid': object_story_spec.get('locations_valid', False),
            'promoted_object_valid': False,
        }

    def _get_account_details(self):
        ad_account_info, status_details = FacebookGetAdAccountDetailsUseCase().execute(self.user_id, self.ad_account_id)
        if status_details != 200:
            if ad_account_info.get('error', {}).get('code') == 190:  # Token error
                raise NotAccessException("Access token is invalid or expired. Please re-authenticate.")
            elif ad_account_info.get('error', {}).get('code') == 200:  # Permission error
                raise PermissionDeniedException("Insufficient permissions to access ad account details. Please check your Facebook app permissions.")
            elif ad_account_info.get('error', {}).get('code') == 100:  # Invalid parameter
                raise ParametersNotFoundException("Invalid parameters provided for fetching ad account details. Please check the ad account ID and try again.")
            elif ad_account_info.get('error', {}).get('code') == 613:  # Too many requests
                raise RateLimitExceededException("Facebook API rate limit exceeded. Please try again later.")
            else:
                raise RESTClientException(f"Failed to fetch ad account details: {ad_account_info.get('error', {}).get('message', 'Unknown error')}")
        return ad_account_info
    
    def _get_minimum_budget(self, ad_account_info):        
        minimum_budgets_allowed, status_budgets = FacebookMinimumBudgetUseCase().execute(self.user_id, self.ad_account_id)
        if status_budgets != 200:
            raise PermissionDeniedException("Insufficient permissions to access minimum budget details. Please check your Facebook app permissions.")
        
        minimum = next((item for item in minimum_budgets_allowed.get('data', []) if item.get('currency') == ad_account_info.get('currency', 'USD')), None)

        if minimum:
            offset = _get_meta_currency_offset(ad_account_info.get('currency', 'USD'))
            return int(minimum.get('min_daily_budget_imp', 0)) / offset
        else:
            raise DataNotFoundException("Minimum budget not found for account currency")

    def _save_creative_to_publish(self, creative):
        if self.creative_type == CreativeType.STANDARD.value:
            for item in creative.get('ads', []):
                ad_creative = item.get('adCreative', {})

                object_story_spec = ad_creative.get('object_story_spec') or {}
                ad_channel_id = object_story_spec.get('ad_channel_id', 0)

                data = {
                    'channel_creative': {**creative, 'ads': [item]} # creative
                }
                self.ad_channel_repository.update(ad_channel_id, data)
        else:
            ad_creative = creative.get('ads')[0].get('adCreative', {})
            ad_channel_id = ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0)

            data = {
                'channel_creative': creative
            }
            self.ad_channel_repository.update(ad_channel_id, data)

    def _save_campaign_channel_publish(self, campaign_channel_publish_data):
        filter_data = {
            'campaign_id': self.campaign_id,
            'channel_id': self.channel_id
        }

        self.campaign_publish_repository.save_or_update(filter_data, campaign_channel_publish_data)

    def _validate_pixel_eligibility(self, pixel_id, access_token):
        # 1. Definir la ventana de tiempo de los últimos 14 días exigida por Meta
        ahora = int(time.time())
        hace_14_dias = ahora - (14 * 24 * 60 * 60)

        url = f"{self.graph_api_base}/{pixel_id}/stats"
        params = {
            "access_token": access_token,
            "aggregation": "event_total_counts",
            "start_time": hace_14_dias,
            "end_time": ahora,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json().get('data', [])

            # 2. Buscar el evento 'Purchase' en el histórico
            compras_totales = 0
            for item in data:
                for stat in item.get('data', []):
                    if stat.get("value").lower() == "purchase":
                        compras_totales = stat.get("count", 0)
                        break
                else:
                    continue  # Se ejecuta solo si el ciclo interno NO se rompió
                break
                    
            # 3. Validar la regla de negocio: Meta requiere un volumen mínimo (aprox. 30 eventos atribuidos)
            # Nota: Como el endpoint entrega eventos totales (orgánicos + pagados), se recomienda un umbral 
            # ligeramente mayor en tu app (ej. 40 o 50 totales) para asegurar que se cumpla la cuota de atribución.
            if compras_totales >= 45:
                return True

            logger.info(f"Píxel inelegible: Solo registra {compras_totales} compras en los últimos 14 días.")
            return False

        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Facebook Graph API: %s", str(e))
            # raise MetaException("META004", "Failed to connect to Facebook Graph API. Please try again later.")
            return False

    def _validate_page_whatsapp_eligibility(self, page_id, access_token):
        url = f"{self.graph_api_base}/{page_id}"
        params = {
            "access_token": access_token,
            "fields": "id,name,whatsapp_number,has_whatsapp_number,has_transitioned_to_new_page_experience,has_whatsapp_business_number,phone",
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            # response.raise_for_status()
            logger.info(f"Fetching page info from Facebook: {response.text}")
            data = response.json()
            logger.info(f"Page WhatsApp validation data: {json.dumps(data)}")

            phone_numbers = data.get('connected_phone_numbers', {}).get('data', [])
            if not phone_numbers:
                return False

            # Verificar que al menos uno tenga el campo "platform" igual a "WHATSAPP"
            for phone in phone_numbers:
                if phone.get('platform') == 'WHATSAPP':
                    return True

            return False

        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Facebook Graph API: %s", str(e))
            return False


    def execute(self):
        decoded_access_token = self._get_decoded_access_token()
        meta_payload = self._build_meta_payload()
        ad_account_info = self._get_account_details()
        account_config = {'currency': ad_account_info.get('currency')}
        min_budget = self._get_minimum_budget(ad_account_info)        
        campaign_data = meta_payload.get('campaign', {})

        # Validaciones de objective OUTCOME_SALES
        if self.objective == CampaignObjective.SALES.value:
            # Validar que exista pixel_id
            if not self.pixel_id:
                logger.error("Missing pixel_id for SALES objective")
                raise MetaException("META001", "Missing pixel_id for SALES objective")

            # Si optimization es VALUE validar que el pixel cumpla con las reglas de negocio de Meta
            if self.optimization_goal == SalesOptimizationGoal.VALUE.value:
                is_pixel_valid = self._validate_pixel_eligibility(pixel_id=self.pixel_id, access_token=decoded_access_token)
                if not is_pixel_valid:
                    logger.error("Pixel is not eligible for VALUE optimization goal")
                    raise MetaException("META006", "Pixel is not eligible for VALUE optimization goal")

        # Validaciones de objective OUTCOME_LEADS
        if self.objective == CampaignObjective.LEADS.value:
            # Si optimization_goal es QUALITY_LEADS, validar que exista 'lead_gen_form_id'
            if self.optimization_goal == LeadsOptimizationGoal.LEAD_GENERATION.value and not self.lead_gen_form_id:
                logger.error("Missing lead_gen_form_id for QUALITY_LEADS optimization goal")
                raise MetaException("META007", "Missing lead_gen_form_id for QUALITY_LEADS optimization goal")

            # Si optimization_goal es CONVERSATIONS, validar que exista 'whatsapp_number_id'
            if self.optimization_goal == LeadsOptimizationGoal.CONVERSATIONS.value:
                # La combinacion con creative_type == 'DYNAMIC' no esta permitida por Meta
                if self.creative_type == CreativeType.DYNAMIC.value:
                    logger.error(f"The campaign objective {self.objective} is not currently supported by Dynamic Creative")
                    raise MetaException("META010", "The campaign objective is not currently supported by Dynamic Creative")

                if not self.whatsapp_number_id:
                    logger.error("Missing whatsapp_number_id for CONVERSATIONS optimization goal")
                    raise MetaException("META008", "Missing whatsapp_number_id for CONVERSATIONS optimization goal")

                is_page_whatsapp_valid = self._validate_page_whatsapp_eligibility(page_id=self.page_id, access_token=decoded_access_token)
                if not is_page_whatsapp_valid:
                    logger.error("Page is not eligible for CONVERSATIONS optimization goal")
                    raise MetaException("META009", "Page is not eligible for CONVERSATIONS optimization goal")

            # OUTCOME_LEADS + OFFSITE_CONVERSIONS: pixel_id y conversion_event obligatorios
            # (antes de META002/META011, del bucle de ads y de cualquier persistencia).
            if self.optimization_goal == LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value:
                self._validate_leads_offsite_params()

        # Validar optimization_goal pertenece a los goals del objective
        try:
            valid_goal = MetaAdsValidator.validate_optimization_goal_for_objective(self.optimization_goal, self.objective, throw=False)
            if not valid_goal:
                logger.error(f"Invalid optimization_goal for objective {self.objective}: {self.optimization_goal}")
                raise MetaException('META002', f"Invalid optimization_goal for objective {self.objective}: {self.optimization_goal}")
        except ValueError as e:
            raise MetaException('META002', str(e))

        # Validar que la combinación objective/optimization_goal esté soportada para STANDARD
        if self.creative_type == CreativeType.STANDARD.value and not self._is_standard_combination_supported():
            logger.error(
                f"Unsupported objective/optimization_goal combination for STANDARD: "
                f"{self.objective}/{self.optimization_goal}"
            )
            raise MetaException(
                "META011",
                f"Unsupported objective/optimization_goal combination for STANDARD creative: {self.objective}/{self.optimization_goal}",
            )

        results = []
        ad_sets = campaign_data.get('ad_sets', [])

        for ad_set in ad_sets:
            ads = ad_set.get('ads', [])
            for ad in ads:
                ad_name = ad.get('name', 'Unknown')
                current_ad_errors = []

                ad_creative = ad.get('adCreative')
                if not ad_creative:

                    current_ad_errors.append({
                        'slug': 'missing-creative-error',
                        'message': "No creative found"
                    })
                    results.append({"ad_name": ad_name, "status": "Failed", "errors": current_ad_errors})
                    continue

                asset_feed = ad_creative.get('asset_feed_spec')
                story_spec = ad_creative.get('object_story_spec')

                if self.creative_type == "DYNAMIC" and asset_feed:
                    asset_feed['promoted_object_valid'] = True
                    # Validaciones específicas para campañas de ventas (OUTCOME_SALES)
                    if self.objective == CampaignObjective.SALES.value:
                        promoted = ad_set.get('promoted_object') or {}
                        # usar pixel_id desde campaign data si no viene en payload
                        if not promoted.get('pixel_id') and self.pixel_id:
                            promoted['pixel_id'] = self.pixel_id
                        try:
                            valid_promoted = MetaAdsValidator.validate_promoted_object(promoted, self.objective, self.optimization_goal, self.pixel_id, throw=False)
                            if not valid_promoted:
                                asset_feed['promoted_object_valid'] = False
                                current_ad_errors.append({
                                    'slug': 'promoted-object-error',
                                    'message': 'Invalid or missing promoted_object for OFFSITE_CONVERSIONS. pixel_id and valid custom_event_type required.'
                                })
                            else:
                                ad_set['promoted_object'] = promoted
                        except ValueError as e:
                            asset_feed['promoted_object_valid'] = False
                            current_ad_errors.append({
                                'slug': 'promoted-object-error',
                                'message': str(e)
                            })

                    # Validaciones específicas para campañas de leads (OUTCOME_LEADS)
                    if self.objective == CampaignObjective.LEADS.value:
                        if self.optimization_goal == LeadsOptimizationGoal.LEAD_GENERATION.value:
                            promoted = ad_set.get('promoted_object') or {}
                            if not promoted.get('page_id') and self.page_id:
                                promoted['page_id'] = self.page_id

                            # asset_feed['link_urls'] = [{"lead_generation_form_id": self.lead_gen_form_id}]

                    try:
                        titles = asset_feed.get('titles', [])
                        # MetaAdsValidator.validate_text('title', [t.get('text') for t in titles])
                        titles_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in titles])
                        asset_feed['unique_titles'] = titles_inique_texts
                        MetaAdsValidator.is_valid_length('titles', titles)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'title-error',
                            'message': f"Titles Error: {str(e)}"
                        })

                    try:
                        bodies = asset_feed.get('bodies', [])
                        # MetaAdsValidator.validate_text('body', [b.get('text') for b in bodies])
                        bodies_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in bodies])
                        asset_feed['unique_bodies'] = bodies_inique_texts
                        MetaAdsValidator.is_valid_length('bodies', bodies)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'body-error',
                            'message': f"Bodies Error: {str(e)}"
                        })

                    try:
                        descriptions = asset_feed.get('descriptions', [])
                        # MetaAdsValidator.validate_text('description', [d.get('text') for d in descriptions])
                        descriptions_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in descriptions])
                        asset_feed['unique_descriptions'] = descriptions_inique_texts
                        MetaAdsValidator.is_valid_length('descriptions', descriptions)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'description-error',
                            'message': f"Descriptions Error: {str(e)}"
                        })

                    ctas = asset_feed.get('call_to_action_types', [])
                    for cta in ctas:
                        try:
                            valid_cta = MetaAdsValidator.validate_cta_for_goal(cta_text=cta.get('value'), objective=self.objective, goal=self.optimization_goal, throw=False)
                            cta['valid'] = valid_cta
                        except ValueError as e:
                            current_ad_errors.append({
                                'slug': 'cta-error',
                                'message': f"CTA Error ({cta}): {str(e)}"
                            })

                    images = asset_feed.get('images', [])
                    images_urls = [img.get('url') for img in images if img.get('url')]
                    try:
                        # MetaAdsValidator.validate_images(images_urls)
                        MetaAdsValidator.validate_images_precheck(images)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'image-error',
                            'message': f"Images Error: {str(e)}"
                        })

                    try:
                        # MetaAdsValidator.validate_assets_amount(asset_feed, self.creative_type, None)
                        MetaAdsValidator.is_valid_amount(asset_feed, self.creative_type, None)
                    except ValueError as e:
                        current_ad_errors.append({
                            'slug': 'assets-amount-error',
                            'message': f"Assets Amount Error: {str(e)}"
                        })

                    try:
                        # validar minimo budget
                        # MetaAdsValidator.validate_budget(ad.get('daily_budget', 0), self.optimization_goal, min_budget)
                        asset_feed['min_daily_budget'] = min_budget
                        asset_feed['daily_budget_valid'] = (ad_set.get('daily_budget', 0) >= min_budget)
                    except Exception as e:
                        current_ad_errors.append({
                            'slug': 'assets-budget-error',
                            'message': f"Assets Daily Budget Error: {str(e)}"
                        })

                    if _is_leads_offsite(self.objective, self.optimization_goal):
                        # Requirement 7.1–7.4: URL obligatoria y válida para Leads_Offsite
                        self._validate_leads_offsite_dynamic_url(asset_feed, current_ad_errors)
                    else:
                        try:
                            # validar url (Requirement 7.6: sin cambios para Otras_Combinaciones)
                            # url_valid = False
                            # if self.objective == CampaignObjective.LEADS.value and self.optimization_goal == LeadsOptimizationGoal.QUALITY_LEAD.value:
                            #     url_valid = True
                            # else:
                            #     url_valid = MetaAdsValidator.is_valid_link_url(','.join([u.get('website_url') for u in asset_feed.get('link_urls', [])]))
                            # asset_feed['link_url_valid'] = url_valid
                            url_valid = MetaAdsValidator.is_valid_link_url(','.join([u.get('website_url') for u in asset_feed.get('link_urls', [])]))
                            asset_feed['link_url_valid'] = url_valid
                        except Exception as e:
                            current_ad_errors.append({
                                'slug': 'assets-budget-error',
                                'message': f"Assets Daily Budget Error: {str(e)}"
                            })

                elif self.creative_type == "STANDARD" and story_spec:
                    self._validate_standard_creative(ad_set, story_spec, min_budget, current_ad_errors)

                if current_ad_errors:
                    results.append({
                        "ad_name": ad_name,
                        "status": "Failed",
                        "errors": current_ad_errors
                    })
                    continue
            
                try:
                    """ if self.creative_type == "DYNAMIC" and asset_feed:
                        valid_images = []
                        for image in asset_feed.get('images', []):
                            image_url = image.get('url')
                            if image_url and not image.get('hash'):
                                    image_hash = self._upload_image(image_url, ad_account_id, decoded_access_token)
                                    if image_hash:
                                        image['hash'] = image_hash
                                        valid_images.append(image)
                                    else:
                                        raise Exception(f"Failed to upload image to FB: {image_url}")
                            elif image.get('hash'):
                                valid_images.append(image)
                        asset_feed['images'] = valid_images

                    elif self.creative_type == "STANDARD" and story_spec:
                        link_data = story_spec.get('link_data')
                        if link_data and link_data.get('image_url'):
                            image_hash = self._upload_image(link_data['image_url'], ad_account_id, decoded_access_token)
                            if image_hash:
                                link_data['image_hash'] = image_hash
                            else:
                                raise Exception(f"Failed to upload image to FB: {link_data['image_url']}")
                    """
                    if self.page_id and ad_creative.get('object_story_spec'):
                        ad_creative['object_story_spec']['page_id'] = self.page_id

                    payload_asset_feed = asset_feed
                    if ad_creative.get('object_story_spec') and ad_creative['object_story_spec'].get('link_data'):
                        payload_asset_feed = None

                    creative_payload = {
                        "name": f"TEST_API_{ad_creative.get('name')}",
                        "object_story_spec": ad_creative.get('object_story_spec'),
                        "asset_feed_spec": payload_asset_feed,
                        "access_token": None # decoded_access_token
                    }

                    creative_payload = {k: v for k, v in creative_payload.items() if v is not None}

                    # created_creative = self._create_ad_creative(creative_payload, ad_account_id)

                    #if created_creative.get('error'):
                    #    raise Exception(f"Meta API Error: {created_creative['error'].get('message')}")

                    results.append({
                        "ad_name": ad_name,
                    #    "creative_id": created_creative.get('id'),
                        "status": "Created",
                    #    "meta_response": created_creative
                    })

                except Exception as e:
                    logger.error(f"Error processing ad execution {ad_name}: {e}")

                    results.append({
                        "ad_name": ad_name,
                        "status": "Failed",
                        "errors": [{
                            'slug': 'execution-error',
                            'message': f"Execution Error: {str(e)}"
                        }]
                    })

        has_errors = any(item.get('status') == 'Failed' for item in results)

        # Save Campaign Channel Setup
        campaign_channel_publish = {
            'meta_campaign_objective': self.objective,
            'meta_optimization_goal': self.optimization_goal,
            'meta_billing_event': self.billing_event,
            'meta_campaign_mode': self.creative_type,
            'meta_account_id': self.ad_account_id,
            'meta_page_id': self.page_id
        }
        if self.lead_gen_form_id:
            campaign_channel_publish['meta_lead_form_id'] = self.lead_gen_form_id
        if self.whatsapp_number_id:
            campaign_channel_publish['meta_whatsapp_id'] = self.whatsapp_number_id
        if self.pixel_id:
            campaign_channel_publish['meta_pixel_id'] = self.pixel_id
        # Requirement 9.1/9.3: meta_conversion_event solo para OUTCOME_LEADS + OFFSITE_CONVERSIONS
        if _is_leads_offsite(self.objective, self.optimization_goal):
            campaign_channel_publish['meta_conversion_event'] = self.conversion_event

        self._save_campaign_channel_publish(campaign_channel_publish)

        creatives = []
        for i, ad_set_to_publish in enumerate(campaign_data.get('ad_sets')):
            if self.lead_gen_form_id:
                ad_set_to_publish['lead_gen_form_id'] = self.lead_gen_form_id
            if self.whatsapp_number_id:
                ad_set_to_publish['whatsapp_number_id'] = self.whatsapp_number_id
            self._save_creative_to_publish(ad_set_to_publish)

            ads_to_publish = ad_set_to_publish.get('ads')[0]
            ad_creative = ads_to_publish.get('adCreative')
            if self.creative_type == CreativeType.STANDARD.value:
                for item in ad_set_to_publish.get('ads', []):
                    creative_to_publish = self._build_standard_creative_entry(i, ad_set_to_publish, item)
                    creatives.append(creative_to_publish)
            else:
                creative_to_publish = self._build_dynamic_creative_entry(i, ad_set_to_publish, ad_creative)

                creatives.append(creative_to_publish)

        is_leads_offsite = _is_leads_offsite(self.objective, self.optimization_goal)
        for idx, item in enumerate(creatives):
            item['idx'] = idx
            # Requirement 8.1-8.3: pixel_id y conversion_event ya validados; True en ambas ramas
            if is_leads_offsite:
                item['promoted_object_valid'] = True

        campaign = {
            'name': campaign_data.get('name'),
            'channel_name': 'Meta',
            'creatives_no': len(creatives),
            'objective': self.objective,
            'optimization_goal': self.optimization_goal,
            'mode': self.creative_type,
            #'daily_budget': campaign_data.get('daily_budget')
        }

        # valid_ctas = list(MetaAdsValidator.META_ODAX_CTA_MAPPING.get(self.objective)["recommended_ctas"])
        valid_ctas = list(MetaAdsValidator.get_allowed_ctas_for_goal(objective=self.objective, goal=self.optimization_goal))

        data = {
            "campaign": campaign,
            "creatives": creatives,
            "valid_ctas": valid_ctas,
            "account_config": account_config
        }

        return {
            "ok": 1, # if has_errors else 1,
            "data": data # creatives # results
        }, 200

class FacebookMinimumBudgetUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, ad_account_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/minimum_budgets"

        try:
            response = requests.get(
                url,
                params={"access_token": access_token},
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetAdsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, ad_account_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/ads"

        try:
            response = requests.get(
                url,
                params={"access_token": access_token, "fields": "id,name,status,creative{id,name,thumbnail_url,object_story_spec,asset_feed_spec}"},
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetAdsetsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, ad_account_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/adsets"

        try:
            response = requests.get(
                url,
                params={"access_token": access_token, "fields": "id,name"},
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetCampaignsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str, ad_account_id: str):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/campaigns"

        try:
            response = requests.get(
                url,
                params={"access_token": access_token, "fields": "id,name"},
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetInsightsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(
            self,
            user_id: str,
            entity_id: str,
            fields: str = None,
            level: str = None,
            date_preset: str = None,
            time_increment: str = None
        ):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/{entity_id}/insights"

        try:
            response = requests.get(
                url,
                params={
                    "access_token": access_token,
                    "fields": fields,
                    "level": level,
                    "date_preset": date_preset,
                    "time_increment": time_increment
                },
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetInsightsFromAdAccountUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(
        self,
        user_id: str,
        ad_account_id: str,
        fields: str = None,
        level: str = None,
        date_preset: str = None,
        time_increment: str = None
    ):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/insights"

        try:
            response = requests.get(
                url,
                params={
                    "access_token": access_token,
                    "fields": fields,
                    "level": level,
                    "date_preset": date_preset,
                    "time_increment": time_increment
                },
                timeout=10,
            )

            if response.status_code != 200:
                return {
                    "error": "Facebook API error",
                    "details": response.json(),
                }, response.status_code

            return response.json(), 200

        except requests.exceptions.RequestException as e:
            return {
                "error": "Failed to connect to Facebook Graph API",
                "details": str(e),
            }, 502

class FacebookGetPixelUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(
        self,
        user_id: str,
        ad_account_id: str
    ):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            logger.error("No access token found in Redis for user_id: %s", user_id)
            raise MetaException("META003", "No access token found in Redis. Please re-authenticate.")

        access_token = access_token.decode("utf-8")

        url = f"{self.graph_api_base}/act_{ad_account_id}/adspixels"
        params = {
            "access_token": access_token,
            "fields": ",".join([
                "id",
                # "code",
                "name",
                #"created_time",
                #"last_fired_time",
                #"config",
                #"event_stats",
                #"is_unavailable",
                #"usage",
                #"valid_entries",
                #"stats"
            ])
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                error_type = response.json().get('error', {}).get('type', 'OAuthException')
                error_message = response.json().get('error', {}).get('message', '')
                logger.error(f"Facebook API error - Type: {error_type} - Message: {error_message}")
                raise MetaException("META005", f"Facebook API error - Type: {error_type} - Message: {error_message}")

            return response.json().get('data', [])

        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Facebook Graph API: %s", str(e))
            raise MetaException("META004", "Failed to connect to Facebook Graph API. Please try again later.")

class FacebookGetAPixelUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(
        self,
        user_id: str,
        ad_account_id: str,
        pixel_id: str
    ):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            logger.error("No access token found in Redis for user_id: %s", user_id)
            raise MetaException("META003", "No access token found in Redis. Please re-authenticate.")

        access_token = access_token.decode("utf-8")

        # 1. Definir la ventana de tiempo de los últimos 14 días exigida por Meta
        ahora = int(time.time())
        hace_14_dias = ahora - (14 * 24 * 60 * 60)

        url = f"{self.graph_api_base}/{pixel_id}/stats"
        params = {
            "access_token": access_token,
            "aggregation": "event_total_counts",
            "start_time": hace_14_dias,
            "end_time": ahora,
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=10,
            )

            if response.status_code != 200:
                error_type = response.json().get('error', {}).get('type', 'OAuthException')
                error_message = response.json().get('error', {}).get('message', '')
                logger.error(f"Facebook API error - Type: {error_type} - Message: {error_message}")
                raise MetaException("META005", f"Facebook API error - Type: {error_type} - Message: {error_message}")

            data = response.json().get('data', [])

            # 2. Buscar el evento 'Purchase' en el histórico
            compras_totales = 0
            for item in data:
                for stat in item.get('data', []):
                    if stat.get("value").lower() == "purchase":
                        compras_totales = stat.get("count", 0)
                        break
                else:
                    continue  # Se ejecuta solo si el ciclo interno NO se rompió
                break
                    
            # 3. Validar la regla de negocio: Meta requiere un volumen mínimo (aprox. 30 eventos atribuidos)
            # Nota: Como el endpoint entrega eventos totales (orgánicos + pagados), se recomienda un umbral 
            # ligeramente mayor en tu app (ej. 40 o 50 totales) para asegurar que se cumpla la cuota de atribución.
            if compras_totales >= 45:
                logger.info(f"Píxel elegible: Registra {compras_totales} compras en los últimos 14 días.")
                # return True

            logger.info(f"Píxel inelegible: Solo registra {compras_totales} compras en los últimos 14 días.")
            # return False

            return response.json().get('data', {})

        except requests.exceptions.RequestException as e:
            logger.error("Failed to connect to Facebook Graph API: %s", str(e))
            raise MetaException("META004", "Failed to connect to Facebook Graph API. Please try again later.")

class FacebookGetCampaignObjectiveUseCase():
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id: str):
        """ redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {
                "error": "No access token found in Redis. Please re-authenticate."
            }, 401

        access_token = access_token.decode("utf-8") """

        awareness = {
            'id': CampaignObjective.AWARENESS.value,
            'active': True,
            'goals': [
                {
                    'id': AwarenessOptimizationGoal.AD_RECALL_LIFT.value, 
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': AwarenessOptimizationGoal.REACH.value, 
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': AwarenessOptimizationGoal.IMPRESSIONS.value, 
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': AwarenessOptimizationGoal.THRUPLAY.value, 
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': AwarenessOptimizationGoal.TWO_SECOND_CONTINUOUS_VIDEO_VIEWS.value, 
                    'billing_event': 'IMPRESSIONS'
                }
            ]
        }

        traffic = {'id': CampaignObjective.TRAFFIC.value, 'active': False, 'goals': []}
        sales = {
            'id': CampaignObjective.SALES.value, 
            'active': True, 
            'goals': [
                {
                    'id': SalesOptimizationGoal.OFFSITE_CONVERSIONS.value,
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': SalesOptimizationGoal.VALUE.value,
                    'billing_event': 'IMPRESSIONS'
                },
                # {
                #     'id': 'CONVERSATIONS',
                #     'billing_event': 'IMPRESSIONS'
                # },
                {
                    'id': SalesOptimizationGoal.LINK_CLICKS.value,
                    'billing_event': 'IMPRESSIONS'
                },
                # {
                #     'id': 'LANDING_PAGE_VIEWS',
                #     'billing_event': 'IMPRESSIONS'
                # }                                
            ]
        }

        leads = {
            'id': CampaignObjective.LEADS.value,
            'active': True,
            'goals': [
                {
                    'id': LeadsOptimizationGoal.LEAD_GENERATION.value,
                    'billing_event': 'IMPRESSIONS'
                },
                # {
                #     'id': LeadsOptimizationGoal.QUALITY_LEAD.value,
                #     'billing_event': 'IMPRESSIONS'
                # },
                {
                    'id': LeadsOptimizationGoal.CONVERSATIONS.value,
                    'billing_event': 'IMPRESSIONS'
                },
                {
                    'id': LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
                    'billing_event': 'IMPRESSIONS'
                }
            ]
        }
        data = [awareness, traffic, sales, leads]
        return data

class FacebookSavePreCheckBaseUseCase(FacebookGeneratePreCheckCreativeUseCase):
    def __init__(self, user_id: str, pre_check_data: PreCheckDataDict = {}):
        super().__init__(pre_check_data.get('campaign_id'), user_id, {})
        self.adset_id = pre_check_data.get('adset_id')
        self.ad_id = pre_check_data.get('ad_id')
        self.adchannel_id = pre_check_data.get('adchannel_id')
        self.images = pre_check_data.get('images', [])
        self.bodies = pre_check_data.get('bodies', [])
        self.titles = pre_check_data.get('titles', [])
        self.descriptions = pre_check_data.get('descriptions', [])
        self.call_to_action_types = pre_check_data.get('call_to_action_types', [])
        self.daily_budget = pre_check_data.get('daily_budget', 0)
        self.proposal_url = pre_check_data.get('proposal_url', '')
        self.locations = pre_check_data.get('locations', [])

    def _get_ad_channel(self):
        ad_channel = self.ad_channel_repository.get_by_campaign_and_ad_channel_id(self.campaign_id, self.adset_id, self.ad_id, self.adchannel_id)
        if not ad_channel:
            raise DataNotFoundException(f"Creative not found!")

        return ad_channel
    
    def _get_campaign_setup(self):
        campaign_setup = self.campaign_publish_repository.get_by_campaign_id_and_channel_id(self.campaign_id, self.channel_id)

        if not campaign_setup:
            raise DataNotFoundException(f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}")

        return campaign_setup
    
    def _set_channel_id(self, ad_channel):
        self.channel_id = ad_channel.get('attributes', {}).get('channel_ref', {}).get('data', {}).get('id', 0)

    def _set_creative_type(self, campaign_setup):
        self.creative_type = CreativeType(campaign_setup.get('attributes', {}).get('meta_campaign_mode')).value
    
    def _build_response(self, creative):
        ads_to_publish = creative.get('ads')[0]

        ad_creative = ads_to_publish.get('adCreative') or {}
        object_story_spec = ad_creative.get('object_story_spec')
        asset_feed_spec = ad_creative.get('asset_feed_spec')

        if self.creative_type == CreativeType.STANDARD.value:
            object_story_spec = object_story_spec or {}
            link_data = object_story_spec.get('link_data') or {}
            call_to_action = link_data.get('call_to_action') or {}
            if not isinstance(call_to_action, dict):
                call_to_action = {}

            def _as_single_item_list(value, valid_flag):
                return [{'text': value, 'valid_length': valid_flag}] if value else []

            image_url = link_data.get('image_url')
            images = [{
                'url': image_url,
                'valid': link_data.get('image_valid', False),
                'error': link_data.get('image_error'),
            }] if image_url else []

            creative_to_publish = {
                'name': creative.get('name'),
                'adset_id': creative.get('id'),
                'ad_id': ads_to_publish.get('id'),
                'adchannel_id': object_story_spec.get('ad_channel_id', 0),
                'daily_budget': creative.get('daily_budget'),
                'images': images,
                'bodies': _as_single_item_list(link_data.get('message'), link_data.get('body_valid', False)),
                'titles': _as_single_item_list(link_data.get('name'), link_data.get('title_valid', False)),
                'descriptions': _as_single_item_list(link_data.get('description'), link_data.get('description_valid', False)),
                'call_to_action_types': [call_to_action.get('type', {})] if call_to_action else [],
                'images_valid_amount': link_data.get('image_valid', False),
                'titles_valid_amount': link_data.get('title_valid', False),
                'bodies_valid_amount': link_data.get('body_valid', False),
                'descriptions_valid_amount': link_data.get('description_valid', False),
                'call_to_action_types_valid_amount': call_to_action.get('type', {}).get('valid', False) if call_to_action else False,
                'images_max_amount': 1,
                'titles_max_amount': 1,
                'bodies_max_amount': 1,
                'descriptions_max_amount': 1,
                'call_to_action_types_max_amount': 1,
                'unique_titles': link_data.get('title_valid', False),
                'unique_bodies': link_data.get('body_valid', False),
                'unique_descriptions': link_data.get('description_valid', False),
                'daily_budget_valid': object_story_spec.get('daily_budget_valid', False),
                'min_daily_budget': object_story_spec.get('min_daily_budget', 0),
                'proposal_url': link_data.get('link') or '',
                'proposal_url_valid': link_data.get('link_url_valid', False),
                'proposal_locations': creative.get('proposal_locations', []),
                'locations': object_story_spec.get('locations', []),
                'locations_valid': object_story_spec.get('locations_valid', False),
            }
        else:
            creative_to_publish = {
                #'idx': ad_creative.get('idx'),
                'name': creative.get('name'),
                'adset_id': creative.get('id'),
                'ad_id': ads_to_publish.get('id'),
                'adchannel_id': ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0),
                # 'ad_account_id': creative.get('ad_account_id'),
                'daily_budget': creative.get('daily_budget'),
                #'targeting': creative.get('targeting'),
                'images': [{'url': i.get('url'), 'valid': i.get('valid'), 'error': i.get('error')} for i in ad_creative.get('asset_feed_spec', {}).get('images', [])],
                'bodies': ad_creative.get('asset_feed_spec', {}).get('bodies', []),
                'titles': ad_creative.get('asset_feed_spec', {}).get('titles', []),
                'descriptions': ad_creative.get('asset_feed_spec', {}).get('descriptions', []),
                'call_to_action_types': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types', []),
                'images_valid_amount': ad_creative.get('asset_feed_spec', {}).get('images_valid_amount', False),
                'titles_valid_amount': ad_creative.get('asset_feed_spec', {}).get('titles_valid_amount', False),
                'bodies_valid_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_valid_amount', False),
                'descriptions_valid_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_valid_amount', False),
                'call_to_action_types_valid_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_valid_amount', False),
                'images_max_amount': ad_creative.get('asset_feed_spec', {}).get('images_max_amount', 0),
                'titles_max_amount': ad_creative.get('asset_feed_spec', {}).get('titles_max_amount', 0),
                'bodies_max_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_max_amount', 0),
                'descriptions_max_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_max_amount', 0),
                'call_to_action_types_max_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_max_amount', 0),
                'unique_titles': ad_creative.get('asset_feed_spec', {}).get('unique_titles', False),
                'unique_bodies': ad_creative.get('asset_feed_spec', {}).get('unique_bodies', False),
                'unique_descriptions': ad_creative.get('asset_feed_spec', {}).get('unique_descriptions', False),
                'daily_budget_valid': ad_creative.get('asset_feed_spec', {}).get('daily_budget_valid', False),
                'min_daily_budget': ad_creative.get('asset_feed_spec', {}).get('min_daily_budget', 0),
                'proposal_url': ','.join([u.get('website_url', '') for u in ad_creative.get('asset_feed_spec', {}).get('link_urls', [])]),
                'proposal_url_valid': ad_creative.get('asset_feed_spec', {}).get('link_url_valid', False),
                'proposal_locations': creative.get('proposal_locations', []),
                'locations': ad_creative.get('asset_feed_spec', {}).get('locations', []),
                'locations_valid': ad_creative.get('asset_feed_spec', {}).get('locations_valid', False),
                #'billing_event': ad_set_to_publish.get('billing_event'),
                #'optimization_goal': ad_set_to_publish.get('optimization_goal'),
                #'ad_creative': ads_to_publish.get('adCreative')
            }

        return creative_to_publish

class FacebookSavePreCheckImagesUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_images_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_images_data)
    
    def _validate_images_dynamic(self, asset_feed):
        MetaAdsValidator.validate_images_precheck(self.images)
        asset_feed['images'] = self.images
        asset_feed['images_valid_amount'] = MetaAdsValidator.is_valid_images_amount(self.images)

    def _validate_images_standard(self, story_spec):
        link_data = story_spec.get('link_data')
        if link_data is None:
            link_data = {}
            story_spec['link_data'] = link_data

        if len(self.images) != 1:
            link_data['image_valid'] = False
            return

        image_url = self.images[0].get('url')
        link_data['image_url'] = image_url

        images = [{'url': image_url}]
        MetaAdsValidator.validate_images_precheck(images)

        link_data['image_valid'] = images[0].get('valid', False)
        link_data['image_error'] = images[0].get('error')

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self._set_creative_type(campaign_setup)

        # Validar las imagenes del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                self._validate_images_dynamic(asset_feed)

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                self._validate_images_standard(story_spec)
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish
    

class FacebookSavePreCheckTextsUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_texts_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_texts_data)

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self._set_creative_type(campaign_setup)

        # Validar los textos del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                # titles = asset_feed.get('titles', [])
                titles_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in self.titles])
                asset_feed['unique_titles'] = titles_inique_texts
                MetaAdsValidator.is_valid_length('titles', self.titles)
                asset_feed['titles_valid_amount'] = MetaAdsValidator.is_valid_texts_amount('titles', self.titles)
                asset_feed['titles'] = self.titles

                # bodies = asset_feed.get('bodies', [])
                bodies_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in self.bodies])
                asset_feed['unique_bodies'] = bodies_inique_texts
                MetaAdsValidator.is_valid_length('bodies', self.bodies)
                asset_feed['bodies_valid_amount'] = MetaAdsValidator.is_valid_texts_amount('bodies', self.bodies)
                asset_feed['bodies'] = self.bodies

                # descriptions = asset_feed.get('descriptions', [])
                descriptions_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in self.descriptions])
                asset_feed['unique_descriptions'] = descriptions_inique_texts
                MetaAdsValidator.is_valid_length('descriptions', self.descriptions)
                asset_feed['descriptions_valid_amount'] = MetaAdsValidator.is_valid_texts_amount('descriptions', self.descriptions)
                asset_feed['descriptions'] = self.descriptions

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                link_data = story_spec.get('link_data')
                if link_data is None:
                    link_data = {}
                    story_spec['link_data'] = link_data

                for candidates, link_key, valid_key, singular_type in (
                    (self.titles, 'name', 'title_valid', 'title'),
                    (self.bodies, 'message', 'body_valid', 'body'),
                    (self.descriptions, 'description', 'description_valid', 'description'),
                ):
                    if len(candidates) != 1:
                        link_data[valid_key] = False
                        continue

                    text_item = {'text': candidates[0].get('text')}
                    MetaAdsValidator.is_valid_length(singular_type, [text_item])
                    valid = text_item.get('valid_length', False)
                    link_data[valid_key] = valid

                    if valid:
                        link_data[link_key] = candidates[0].get('text')
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish

class FacebookSavePreCheckCTAsUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_ctas_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_ctas_data)

    def _validate_ctas(self, asset_feed, objective, optimization_goal):
        # For CTA validation we need the optimization_goal as well (goals are per objective)
        # Expect caller to pass objective and optimization_goal via closure or set in instance

        for cta in self.call_to_action_types:
            try:
                valid_cta = MetaAdsValidator.validate_cta_for_goal(cta_text=cta.get('value'), objective=objective, goal=optimization_goal, throw=False)
            except Exception:
                valid_cta = False
            cta['valid'] = valid_cta

        asset_feed['call_to_action_types'] = self.call_to_action_types
        asset_feed['call_to_action_types_valid_amount'] = MetaAdsValidator.is_valid_ctas_amount(self.call_to_action_types)

    def _validate_ctas_standard(self, link_data, objective, optimization_goal):
        if len(self.call_to_action_types) == 0:
            link_data.pop('call_to_action', None)
            return
        if len(self.call_to_action_types) > 1:
            return

        cta_value = self.call_to_action_types[0].get('value')
        try:
            valid_cta = MetaAdsValidator.validate_cta_for_goal(cta_text=cta_value, objective=objective, goal=optimization_goal, throw=False)
        except Exception:
            valid_cta = False

        link_data['call_to_action'] = {'type': {'value': cta_value, 'valid': valid_cta}}

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self._set_creative_type(campaign_setup)

        # Validar los ctas del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                campaign_objective = campaign_setup.get('attributes', {}).get('meta_campaign_objective')
                optimization_goal = campaign_setup.get('attributes', {}).get('meta_optimization_goal')
                self._validate_ctas(asset_feed, campaign_objective, optimization_goal)

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                campaign_objective = campaign_setup.get('attributes', {}).get('meta_campaign_objective')
                optimization_goal = campaign_setup.get('attributes', {}).get('meta_optimization_goal')

                link_data = story_spec.get('link_data')
                if link_data is None:
                    link_data = {}
                    story_spec['link_data'] = link_data

                self._validate_ctas_standard(link_data, campaign_objective, optimization_goal)
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish
    
class FacebookSavePreCheckBudgetUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_budget_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_budget_data)

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self.ad_account_id = campaign_setup.get('attributes', {}).get('meta_account_id')
        self._set_creative_type(campaign_setup)

        # Validar el daily budget del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                ad_account_info = self._get_account_details()
                min_daily_budget = self._get_minimum_budget(ad_account_info)
                asset_feed['min_daily_budget'] = min_daily_budget
                asset_feed['daily_budget_valid'] = (self.daily_budget >= min_daily_budget)
                creative['daily_budget'] = self.daily_budget

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                ad_account_info = self._get_account_details()
                min_budget = self._get_minimum_budget(ad_account_info)

                story_spec['min_daily_budget'] = min_budget

                if isinstance(self.daily_budget, (int, float)) and not isinstance(self.daily_budget, bool):
                    story_spec['daily_budget_valid'] = (self.daily_budget >= min_budget)
                    creative['daily_budget'] = self.daily_budget
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish

class FacebookSavePreCheckProposalURLUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_proposal_url_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_proposal_url_data)

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self._set_creative_type(campaign_setup)

        # Validar el proposal url del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                #if campaign_setup.get('attributes', {}).get('meta_optimization_goal') != LeadsOptimizationGoal.QUALITY_LEAD.value:
                asset_feed['link_urls'] = [{'website_url': self.proposal_url}]
                asset_feed['link_url_valid'] = MetaAdsValidator.is_valid_proposal_url(self.proposal_url)

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                # Requirement 5.3: mismo patrón de creación/reasignación de link_data
                # ya usado por Textos/CTAs.
                link_data = story_spec.get('link_data')
                if link_data is None:
                    link_data = {}
                    story_spec['link_data'] = link_data

                # Requirement 5.1/5.2: is_valid_link_url (NO is_valid_proposal_url),
                # replicando la decisión ya fijada por el Requirement 7 de
                # meta-ads-standard-precheck-validation. is_valid_link_url(None)
                # lanzaría AttributeError (hace url.split(',')), por lo que la
                # invocación se evita por completo cuando self.proposal_url es falsy.
                if self.proposal_url:
                    link_data['link'] = self.proposal_url
                    link_data['link_url_valid'] = MetaAdsValidator.is_valid_link_url(self.proposal_url)
                else:
                    link_data['link_url_valid'] = False
                    # link_data['link'] deliberadamente NO se toca (Requirement 5.2).
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish
    
class FacebookSavePreCheckLocationsUseCase(FacebookSavePreCheckBaseUseCase):
    def __init__(self, user_id: str, pre_check_locations_data: PreCheckDataDict = {}):
        super().__init__(user_id, pre_check_locations_data)

    def _build_geo_locations(self):
        countries = []
        regions = []
        cities = []

        for location in self.locations:
            if location.get('type') == 'country':
                countries.append(location.get('key'))
            elif location.get('type') == 'region':
                regions.append({'key': location.get('key')})
            elif location.get('type') == 'city':
                cities.append({'key': location.get('key')})

        return dict(countries=countries, regions=regions, cities=cities)

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Validar account

        # Validar que la account sea dueño de la campaña

        # Buscar creative 
        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        # Buascar el Campaign Setup
        campaign_setup = self._get_campaign_setup()
        self._set_creative_type(campaign_setup)

        # Validar las locations del creative
        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            if self.creative_type == CreativeType.DYNAMIC.value and asset_feed:
                geo_locations = self._build_geo_locations()
                creative['targeting']['geo_locations'] = geo_locations
                asset_feed['locations'] = self.locations
                asset_feed['locations_valid'] = len(self.locations) > 0 

            elif self.creative_type == CreativeType.STANDARD.value and story_spec:
                geo_locations = self._build_geo_locations()
                creative['targeting']['geo_locations'] = geo_locations
                story_spec['locations'] = self.locations
                story_spec['locations_valid'] = len(self.locations) > 0
            
        except Exception as e:
            raise e

        # Actualizar creative
        self._save_creative_to_publish(creative)

        # construir response
        creative_to_publish = self._build_response(creative)
        return creative_to_publish
    
class FacebookLaunchCampaignUseCase():
    def __init__(self, user_id, data):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")
        self.user_id = user_id
        self.brand_id = data.get('brand_id')
        self.campaign_id = data.get('campaign_id')
        self.creatives = data.get('creatives', [])
        self.channel_id = 0
        self.ad_account_id = None
        self.campaign_mode = None
        self.campaign_objective = None
        self.campaign_optimization_goal = None
        self.pixel_id = None
        self.conversion_event = None
        self.ad_channel_repository = AdChannelRepository()
        self.campaign_publish_repository = CampaignChannelPublishRepository()
        self.campaign_repository = CampaignRepository()

    def _get_campaign(self):
        campaign = self.campaign_repository.get_by_id(self.campaign_id)

        if not campaign:
            raise DataNotFoundException(f"Campaign not found for id: {self.campaign_id}")

        return campaign
    
    def _get_decoded_access_token(self):
        redis_key = f"facebook_access_token:{self.user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            raise NotAccessException("No access token found in Redis. Please re-authenticate.")

        return access_token.decode("utf-8")
    
    def _build_leads_offsite_promoted_object(self) -> Dict[str, str]:
        """Req 11.3, 11.5, 11.9. Lanza ParametersNotFoundException antes de cualquier POST del ad set."""
        combo = "OUTCOME_LEADS/OFFSITE_CONVERSIONS"
        if _is_blank(self.pixel_id):
            raise ParametersNotFoundException(f"meta_pixel_id is required in Campaign Setup for {combo}")
        if _is_blank(self.conversion_event):
            raise ParametersNotFoundException(f"meta_conversion_event is required in Campaign Setup for {combo}")
        # Comparación exacta: el PreCheck persiste el valor ya normalizado.
        if self.conversion_event not in LEADS_ALLOWED_CONVERSION_EVENTS:
            raise ParametersNotFoundException(
                f"meta_conversion_event '{self.conversion_event}' is not a valid conversion event for {combo}"
            )
        return {"pixel_id": self.pixel_id, "custom_event_type": self.conversion_event}

    def _build_leads_offsite_tracking_specs(self) -> List[Dict[str, List[str]]]:
        """Req 12.1."""
        return [{"action.type": ["offsite_conversion"], "fb_pixel": [self.pixel_id]}]

    def _get_campaign_setup(self):
        campaign_setup = self.campaign_publish_repository.get_by_campaign_id_and_channel_id(self.campaign_id, self.channel_id)

        if not campaign_setup:
            raise DataNotFoundException(f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}")

        self.ad_account_id = campaign_setup.get('attributes', {}).get('meta_account_id')
        self.campaign_mode = campaign_setup.get('attributes', {}).get('meta_campaign_mode')
        self.campaign_objective = campaign_setup.get('attributes', {}).get('meta_campaign_objective')
        self.campaign_optimization_goal = campaign_setup.get('attributes', {}).get('meta_optimization_goal')
        self.lead_gen_form_id = campaign_setup.get('attributes', {}).get('meta_lead_form_id')
        self.whatsapp_number_id = campaign_setup.get('attributes', {}).get('meta_whatsapp_id')
        attrs = campaign_setup.get('attributes', {})
        self.pixel_id = attrs.get('meta_pixel_id')
        self.conversion_event = attrs.get('meta_conversion_event')
        self.campaign_setup = campaign_setup
        return campaign_setup

    def _get_ad_channel(self, adset_id, ad_id, adchannel_id):
        ad_channel = self.ad_channel_repository.get_by_campaign_and_ad_channel_id(self.campaign_id, adset_id, ad_id, adchannel_id)
        if not ad_channel:
            raise DataNotFoundException(f"Creative not found!")

        self.channel_id = ad_channel.get('attributes', {}).get('channel_ref', {}).get('data', {}).get('id', 0)
        return ad_channel
    
    def _build_meta_campaign(self, campaign, campaign_setup, access_token):
        meta_campaign = {
            'name': f"{campaign.get('attributes', {}).get('name')}",
            'objective': campaign_setup.get('attributes', {}).get('meta_campaign_objective'),
            'status': 'PAUSED',
            'buying_type': 'AUCTION',
            "special_ad_categories": [],
            "is_adset_budget_sharing_enabled": False,
            "access_token": access_token
        }

        return meta_campaign
    
    def _publish_campaign(self, meta_campaign):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/campaigns"
        headers = {"Content-Type": "application/json"}

        # if self.campaign_objective == CampaignObjective.LEADS.value and self.campaign_optimization_goal == LeadsOptimizationGoal.CONVERSATIONS.value:
        #     meta_campaign["objective"] = "OUTCOME_ENGAGEMENT"

        logger.info(f"Publishing campaign with payload: {json.dumps(meta_campaign)}")
        response = requests.post(url, json=meta_campaign, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Error creating campaign: {response.json()}")
            raise RESTClientException(response.json())

        campaign_data = response.json()

        if "error" in campaign_data:
            logger.error(f"Error creating campaign: {campaign_data['error']}")
            raise RESTClientException(campaign_data["error"])
        
        campaign_id = campaign_data.get('id')
        if not campaign_id:
            logger.error(f"Error getting campaign id: {campaign_data}")
            raise RESTClientException(campaign_data)

        return campaign_id

    def _get_pixel(self):
        data, status = FacebookGetPixelUseCase().execute(self.user_id, self.ad_account_id)
        return data['data'][0]['id']

    def _get_account_details(self):
        ad_account_info, status_details = FacebookGetAdAccountDetailsUseCase().execute(self.user_id, self.ad_account_id)
        if status_details != 200:
            if ad_account_info.get('error', {}).get('code') == 190:  # Token error
                raise NotAccessException("Access token is invalid or expired. Please re-authenticate.")
            elif ad_account_info.get('error', {}).get('code') == 200:  # Permission error
                raise PermissionDeniedException("Insufficient permissions to access ad account details. Please check your Facebook app permissions.")
            elif ad_account_info.get('error', {}).get('code') == 100:  # Invalid parameter
                raise ParametersNotFoundException("Invalid parameters provided for fetching ad account details. Please check the ad account ID and try again.")
            elif ad_account_info.get('error', {}).get('code') == 613:  # Too many requests
                raise RateLimitExceededException("Facebook API rate limit exceeded. Please try again later.")
            else:
                raise RESTClientException(f"Failed to fetch ad account details: {ad_account_info.get('error', {}).get('message', 'Unknown error')}")
        return ad_account_info
    
    def _publish_adset(self, adset, access_token):
        ad_account_info = self._get_account_details()
        offset = _get_meta_currency_offset(ad_account_info.get('currency', 'USD'))

        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adsets"
        date_time = datetime.now(timezone.utc)

        payload = {
            "name": adset['name'],
            "campaign_id": adset['campaign_id'],
            "daily_budget": adset.get('daily_budget', 0) * offset,
            "billing_event": adset['billing_event'],
            "optimization_goal": adset['optimization_goal'],
            "bid_strategy": 'LOWEST_COST_WITHOUT_CAP',
            "is_dynamic_creative": True if self.campaign_mode == CreativeType.DYNAMIC.value else False,
            "has_dynamic_creative": True if self.campaign_mode == CreativeType.DYNAMIC.value else False,
            "targeting": {
                **adset['targeting'],
                "targeting_automation": {
                    "advantage_audience": 0
                }
            },
            "start_time": date_time.isoformat(timespec='milliseconds'),
            "end_time": (date_time + timedelta(days=7)).isoformat(timespec='milliseconds'),
            "status": adset['status'],
            "access_token": access_token
        }

        if self.campaign_objective == CampaignObjective.LEADS.value:
            if _is_leads_offsite(self.campaign_objective, self.campaign_optimization_goal):
                # Req 11.2–11.5, 11.9: promoted_object solo desde Campaign_Setup (ignora el del ad set);
                # el helper lanza ParametersNotFoundException antes del POST (rollback en execute()).
                payload["promoted_object"] = self._build_leads_offsite_promoted_object()
                payload["destination_type"] = "WEBSITE"
                payload["optimization_goal"] = LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value
                payload["billing_event"] = "IMPRESSIONS"
            else:
                promoted = adset.get('promoted_object') or {}
                campaigm_page_id = self.campaign_setup.get('attributes', {}).get('meta_page_id') if getattr(self, 'campaign_setup', None) else None
                page_id = promoted.get('page_id') or campaigm_page_id
                payload["promoted_object"] = {"page_id": page_id}

                if self.campaign_optimization_goal == LeadsOptimizationGoal.CONVERSATIONS.value:
                    payload["destination_type"] = "WHATSAPP" # "MESSAGE_PAGE"
                    payload["targeting"]["targeting_automation"]["advantage_audience"] = 1
                    if payload["targeting"]["age_max"]:
                        del payload["targeting"]["age_max"]

                elif self.campaign_optimization_goal == LeadsOptimizationGoal.LEAD_GENERATION.value:
                    payload["destination_type"] = "ON_AD" # "FACEBOOK"


            # payload["promoted_object"] = {
            #     "page_id": self.campaign_setup.get('attributes', {}).get('meta_page_id')
            # }
            
        elif self.campaign_objective == CampaignObjective.SALES.value:
            # For sales campaigns, include promoted_object with pixel_id and custom_event_type.
            promoted = adset.get('promoted_object') or {}

            # Prefer pixel from campaign setup (saved during precheck), then adset payload, then account pixel
            campaign_pixel = self.campaign_setup.get('attributes', {}).get('meta_pixel_id') if getattr(self, 'campaign_setup', None) else None
            pixel_id = promoted.get('pixel_id') or campaign_pixel or None

            # default custom event
            custom_event = promoted.get('custom_event_type') or 'PURCHASE'

            # Validate promoted object (will raise if strict rules fail)
            promoted_obj = {
                'pixel_id': pixel_id,
                'custom_event_type': custom_event
            }
            try:
                MetaAdsValidator.validate_promoted_object(promoted_obj, self.campaign_objective, self.campaign_optimization_goal, pixel_id, throw=True)
            except Exception as e:
                logger.error(f"Invalid promoted_object for adset '{adset.get('name')}': {e}")
                raise ParametersNotFoundException(str(e))

            payload["promoted_object"] = promoted_obj

        # elif self.campaign_objective != CampaignObjective.AWARENESS.value:
        #     pixel_id = self._get_pixel()
        #     if pixel_id:
        #         payload["promoted_object"] = {
        #             "pixel_id": pixel_id,
        #             "custom_event_type": "CONTENT_VIEW"
        #         }

        logger.info(f"Publishing adset with payload: {json.dumps(payload)}")
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Error creating adset: {response.json()}")
            raise RESTClientException(response.json())

        adset_data = response.json()

        if "error" in adset_data:
            logger.error(f"Error creating adset: {adset_data['error']}")
            raise RESTClientException(adset_data["error"])
        
        adset_id = adset_data.get('id')
        if not adset_id:
            logger.error(f"Error getting adset id: {adset_data}")
            raise RESTClientException(adset_data)

        return adset_id
    
    def _upload_image(self, image_url, access_token):
        try:
            resp = requests.get(image_url, timeout=10)

            if resp.status_code != 200:
                logger.error(f"Error fetching image: {resp.status_code}")
                return None

            image_data = BytesIO(resp.content)
            img = Image.open(image_data)
            image_format = img.format.lower()
            dummy_filename = f"ad_image.{image_format}"
            mime_type, _ = mimetypes.guess_type(dummy_filename)

            url = f"{self.graph_api_base}/act_{self.ad_account_id}/adimages"
            files = {"filename": (dummy_filename, resp.content, mime_type)}
            data = {"access_token": access_token}

            response = requests.post(url, files=files, data=data)

            if response.status_code != 200:
                logger.error(f"Error uploading image: {response.json()}")
                return None
            
            image_data = response.json()
            if "error" in image_data:
                logger.error(f"Error uploading image: {image_data['error']}")
                return None
            
            hash = image_data.get('images', {}).get(dummy_filename, {}).get('hash')
            if not hash:
                logger.error(f"Error getting image hash: {image_data}")
                return None

            return hash
        
        except Exception as e:
            logger.error(f"Error fetching image: {e}")
            return None
    
    def _publish_media(self, ad, access_token):
        asset_feed = ad['adCreative']['asset_feed_spec'] if ad['adCreative'] else None
        object_story_spec = ad['adCreative']['object_story_spec'] if ad['adCreative'] else None

        if self.campaign_mode == CreativeType.DYNAMIC.value and asset_feed and asset_feed.get('images') and len(asset_feed.get('images', [])) > 0:
            uploaded_images = []

            for index, value in enumerate(asset_feed['images']):
                hash = value.get('hash')
                if not hash:
                    hash = self._upload_image(value['url'], access_token)

                if hash:
                    uploaded_images.append({'hash': hash})

            ad['adCreative']['asset_feed_spec']['images'] = uploaded_images

        if self.campaign_mode == CreativeType.STANDARD.value and object_story_spec:
            image_url = object_story_spec['link_data']['image_url']
            hash = self._upload_image(image_url, access_token)
            if hash:
                object_story_spec['link_data']['image_hash'] = hash

            object_story_spec['link_data'].pop('image_url', None)

    def _build_asset_feed_spec(self, data, lead_gen_form_id=None):
        asset_feed_spec = {
            'images': data.get('images', []),
            'bodies': [{'text': b.get('text', '' )} for b in data.get('bodies', [])],
            'titles': [{'text': t.get('text', '')} for t in data.get('titles', [])],
            'descriptions': [{'text': d.get('text', '')} for d in data.get('descriptions', [])],
            'call_to_action_types': [c.get('value', '') for c in data.get('call_to_action_types', [])],
            'ad_formats': data.get('ad_formats', []),
            'link_urls': data.get('link_urls', [])
        }

        if self.campaign_objective == CampaignObjective.LEADS.value: # and lead_gen_form_id:
            if self.campaign_optimization_goal == LeadsOptimizationGoal.LEAD_GENERATION.value and lead_gen_form_id:
                asset_feed_spec['call_to_actions'] = [
                    {
                        'type': cta_type,
                        'value': {
                            'lead_gen_form_id': lead_gen_form_id
                        }
                    }
                    for cta_type in asset_feed_spec.get('call_to_action_types', [])
                ]
            elif self.campaign_optimization_goal == LeadsOptimizationGoal.CONVERSATIONS.value:
                asset_feed_spec['ad_formats'] = ['AUTOMATIC_FORMAT']
                asset_feed_spec['call_to_actions'] = [
                    {
                        'type': 'WHATSAPP_MESSAGE',
                        'value': {
                            'app_destination': 'WHATSAPP'
                        }
                    }
                ]

        return asset_feed_spec
    
    def _build_object_story_spec(self, data, lead_gen_form_id=None):
        object_story_spec = {
            'page_id': data.get('page_id', '')
        }

        if data.get('link_data'):
            link_data = data.get('link_data')
            call_to_action = {'type': link_data.get('call_to_action', {}).get('type', {}).get('value', ''),
                              'value': link_data.get('call_to_action', {}).get('value', {})}
            valid_keys = ['link', 'message', 'name', 'description', 'image_hash']
            link_data = {k: v for k, v in link_data.items() if k in valid_keys}
            link_data['call_to_action'] = call_to_action

            # Req 12.5: Leads_Offsite nunca inyecta lead_gen_form_id en el CTA
            if (self.campaign_objective == CampaignObjective.LEADS.value and lead_gen_form_id
                    and not _is_leads_offsite(self.campaign_objective, self.campaign_optimization_goal)):
                if 'call_to_action' in link_data:
                    link_data['call_to_action']['value'] = {
                        'lead_gen_form_id': lead_gen_form_id
                    }
            elif self.campaign_optimization_goal == 'CONVERSATIONS':
                link_data['call_to_action'] = {
                    'type': 'WHATSAPP_MESSAGE',
                    'value': {
                        'app_destination': 'WHATSAPP'
                    }
                }
            object_story_spec['link_data'] = link_data

        return object_story_spec

    def _publish_ad_creative(self, ad, access_token):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/adcreatives"
        headers = {"Content-Type": "application/json"}

        payload = {
            'name': ad['adCreative']['name'],
            'object_story_spec': self._build_object_story_spec(ad.get('adCreative', {}).get('object_story_spec'), ad.get('lead_gen_form_id')),
            'access_token': access_token
        }

        if ad.get('adCreative', {}).get('asset_feed_spec'):
            payload['asset_feed_spec'] = self._build_asset_feed_spec(ad.get('adCreative', {}).get('asset_feed_spec'), ad.get('lead_gen_form_id'))

        logger.info(f"Publishing ad creative with payload: {json.dumps(payload)}")

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Error creating ad creative: {response.json()}")
            raise RESTClientException(response.json())

        ad_creative_data = response.json()

        if "error" in ad_creative_data:
            logger.error(f"Error creating ad creative: {ad_creative_data['error']}")
            raise RESTClientException(ad_creative_data["error"])
        
        ad_creative_id = ad_creative_data.get('id')
        if not ad_creative_id:
            logger.error(f"Error getting ad creative id: {ad_creative_data}")
            raise RESTClientException(ad_creative_data)

        ad['creative'] = {'creative_id': ad_creative_id}

        return ad_creative_id
    
    def _publish_ad(self, ad, access_token):
        url = f"{self.graph_api_base}/act_{self.ad_account_id}/ads"
        headers = {"Content-Type": "application/json"}
        payload = {
            "name": ad['name'],
            "adset_id": ad['adset_id'],
            "creative": ad['creative'],
            "status": ad['status'],
            "access_token": access_token
        }
        # Req 12.1–12.4: tracking_specs solo para OUTCOME_LEADS + OFFSITE_CONVERSIONS
        if _is_leads_offsite(self.campaign_objective, self.campaign_optimization_goal):
            payload["tracking_specs"] = self._build_leads_offsite_tracking_specs()

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code != 200:
            logger.error(f"Error creating ad - status != 200: {response.json()}")
            raise RESTClientException(response.json())

        ad_data = response.json()

        if "error" in ad_data:
            logger.error(f"Error creating ad: {ad_data['error']}")
            raise RESTClientException(ad_data["error"])
        
        ad_id = ad_data.get('id')
        if not ad_id:
            logger.error(f"Error getting ad id: {ad_data}")
            raise RESTClientException(ad_data)

        return ad_id
    
    def _delete_object(self, object_id, access_token):
        try:
            url = f"{self.graph_api_base}/{object_id}"
            headers = {"Content-Type": "application/json"}
            params = {"access_token": access_token}

            response = requests.delete(url, params=params, headers=headers)

            if response.status_code != 200:
                logger.error(f"Error deleting object {object_id}: {response.text}")
                
        except Exception as e:
            logger.error(f"Exception while deleting object {object_id}: {e}")
    
    def _rollback_publish(self, meta_campaign_id, created_ad_creative_ids, access_token):
        logger.info("Executing rollback...")

        # 1. Delete Campaign (Cascades to AdSets and Ads)
        if meta_campaign_id:
            logger.info(f"Rolling back: Deleting campaign {meta_campaign_id}")
            self._delete_object(meta_campaign_id, access_token)

        # 2. Delete Ad Creatives (Must be done after ads are deleted)
        for ad_creative_id in created_ad_creative_ids:
            self._delete_object(ad_creative_id, access_token)

    def _is_campaign_valid(self, creatives_to_publish):
        valid = True

        if not creatives_to_publish:
            logger.error("No hay creativos para publicar")
            return False

        for adset in creatives_to_publish:
            if not adset.get('ads'):
                logger.error("El adset no tiene anuncios")
                return False

            for ad in adset.get('ads'):
                if not ad.get('adCreative'):
                    logger.error("El anuncio no tiene adCreative")
                    return False
                
                if self.campaign_mode == CreativeType.DYNAMIC.value:
                    if not ad.get('adCreative', {}).get('asset_feed_spec'):
                        logger.error("El adCreative no tiene asset_feed_spec")
                        return False
                    
                    asset_feed_spec = ad.get('adCreative', {}).get('asset_feed_spec')

                    if not asset_feed_spec.get('unique_bodies') or \
                        not asset_feed_spec.get('unique_titles') or \
                        not asset_feed_spec.get('unique_descriptions') or \
                        not asset_feed_spec.get('link_url_valid') or \
                        not asset_feed_spec.get('locations_valid') or \
                        not asset_feed_spec.get('daily_budget_valid') or \
                        not asset_feed_spec.get('bodies_valid_amount') or \
                        not asset_feed_spec.get('images_valid_amount') or \
                        not asset_feed_spec.get('titles_valid_amount') or \
                        not asset_feed_spec.get('descriptions_valid_amount') or \
                        not asset_feed_spec.get('call_to_action_types_valid_amount'):
                        logger.error("El adCreative no tiene todos los campos validados")
                        return False

                elif self.campaign_mode == CreativeType.STANDARD.value:
                    # Requirement 2.5: cada eslabon de la cadena
                    # object_story_spec -> link_data -> call_to_action se
                    # sustituye por {} cuando esta ausente, es None, o no es
                    # un dict, de modo que las 8 lecturas siguientes nunca
                    # lancen. `or {}` cubre ausente y None; el isinstance
                    # cubre el caso "presente con un tipo distinto a dict".
                    object_story_spec = ad.get('adCreative', {}).get('object_story_spec') or {}
                    if not isinstance(object_story_spec, dict):
                        object_story_spec = {}

                    link_data = object_story_spec.get('link_data') or {}
                    if not isinstance(link_data, dict):
                        link_data = {}

                    call_to_action = link_data.get('call_to_action') or {}
                    if not isinstance(call_to_action, dict):
                        call_to_action = {}

                    cta_type = call_to_action.get('type') or {}
                    if not isinstance(cta_type, dict):
                        cta_type = {}

                    # Requirement 2.1: las 8 condiciones, todas con
                    # comparacion estricta `is not True`, de modo que un
                    # campo ausente, None, False, o truthy-no-booleano
                    # cuente como no valido.
                    # Requirement 2.6: se leen exclusivamente los campos ya
                    # anotados por el flujo de pre-check; ninguna llamada a
                    # MetaAdsValidator ni validacion de negocio nueva.
                    if link_data.get('title_valid') is not True or \
                        link_data.get('body_valid') is not True or \
                        link_data.get('description_valid') is not True or \
                        link_data.get('image_valid') is not True or \
                        link_data.get('link_url_valid') is not True or \
                        object_story_spec.get('daily_budget_valid') is not True or \
                        object_story_spec.get('locations_valid') is not True or \
                        cta_type.get('valid') is not True:
                        # Requirement 2.2: "todo o nada" -- un solo ad
                        # invalido invalida el conjunto completo, igual que
                        # ya hace hoy la Rama_DYNAMIC.
                        logger.error("El adCreative STANDARD no tiene todos los campos validados")
                        return False

                else:
                    valid = True

        return valid

    def _build_standard_creative_published(self, idx, ad_set_published, ads_published):
        # Requirement 3.3: ningun acceso puede lanzar. `or {}` normaliza
        # tanto la clave ausente como el valor None explicito, en los cuatro
        # niveles de la cadena.
        ad_creative = ads_published.get('adCreative') or {}
        object_story_spec = ad_creative.get('object_story_spec') or {}
        link_data = object_story_spec.get('link_data') or {}
        call_to_action = link_data.get('call_to_action') or {}
        if not isinstance(call_to_action, dict):
            call_to_action = {}

        image_url = link_data.get('image_url')
        images = [{
            'url': image_url,
            'valid': link_data.get('image_valid', False),
            'error': link_data.get('image_error'),
        }] if image_url else []

        def _as_single_item_list(value, valid_length):
            return [{'text': value, 'valid_length': valid_length}] if value else []

        title_valid = link_data.get('title_valid', False)
        body_valid = link_data.get('body_valid', False)
        description_valid = link_data.get('description_valid', False)

        # Requirement 3.2: exactamente el mismo conjunto fijo de 31 claves
        # que produce la entrada DYNAMIC, en el mismo orden.
        return {
            'idx': idx,
            'name': ad_set_published.get('name'),
            'adset_id': ad_set_published.get('id'),
            'ad_id': ads_published.get('id'),
            'adchannel_id': object_story_spec.get('ad_channel_id', 0),
            'daily_budget': ad_set_published.get('daily_budget'),
            'images': images,
            'bodies': _as_single_item_list(link_data.get('message'), body_valid),
            'titles': _as_single_item_list(link_data.get('name'), title_valid),
            'descriptions': _as_single_item_list(link_data.get('description'), description_valid),
            'call_to_action_types': [call_to_action.get('type', {})] if call_to_action else [],
            'images_valid_amount': link_data.get('image_valid', False),
            'titles_valid_amount': title_valid,
            'bodies_valid_amount': body_valid,
            'descriptions_valid_amount': description_valid,
            'call_to_action_types_valid_amount': call_to_action.get('type', {}).get('valid', False) if call_to_action else False,
            'images_max_amount': 1,
            'titles_max_amount': 1,
            'bodies_max_amount': 1,
            'descriptions_max_amount': 1,
            'call_to_action_types_max_amount': 1,
            'unique_titles': title_valid,
            'unique_bodies': body_valid,
            'unique_descriptions': description_valid,
            'daily_budget_valid': object_story_spec.get('daily_budget_valid', False),
            'min_daily_budget': object_story_spec.get('min_daily_budget', 0),
            'proposal_url': link_data.get('link') or '',
            'proposal_url_valid': link_data.get('link_url_valid', False),
            'proposal_locations': ad_set_published.get('proposal_locations', []),
            'locations': object_story_spec.get('locations', []),
            'locations_valid': object_story_spec.get('locations_valid', False),
        }

    def _build_response(self, campaign_id, campaign_data, data):
        campaign = {
            'name': campaign_data.get('name'),
            'channel_name': 'Meta',
            'creatives_no': len(data),
            'objective': self.campaign_objective,
            'optimization_goal': self.campaign_optimization_goal,
            'mode': self.campaign_mode,
        }

        creatives = []
        for i, ad_set_published in enumerate(data):
            ads_published = ad_set_published.get('ads')[0]

            # Requirement 3.1: se despacha por self.campaign_mode (ya asignado
            # por _get_campaign_setup), no por la presencia de asset_feed_spec.
            if self.campaign_mode == CreativeType.STANDARD.value:
                creative_published = self._build_standard_creative_published(i, ad_set_published, ads_published)
            else:
                # Rama DYNAMIC: cuerpo actual, verbatim (Requirement 3.4).
                # Incluye su `ad_creative = ads_published.get('adCreative')`
                # sin normalizar, preservando su comportamiento actual.
                ad_creative = ads_published.get('adCreative')
                creative_published = {
                    'idx': i,
                    'name': ad_set_published.get('name'),
                    'adset_id': ad_set_published.get('id'),
                    'ad_id': ads_published.get('id'),
                    'adchannel_id': ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0),
                    'daily_budget': ad_set_published.get('daily_budget'),
                    'images': [{'url': i.get('url'), 'valid': i.get('valid'), 'error': i.get('error')} for i in ad_creative.get('asset_feed_spec', {}).get('images', [])],
                    'bodies': ad_creative.get('asset_feed_spec', {}).get('bodies', []),
                    'titles': ad_creative.get('asset_feed_spec', {}).get('titles', []),
                    'descriptions': ad_creative.get('asset_feed_spec', {}).get('descriptions', []),
                    'call_to_action_types': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types', []),
                    'images_valid_amount': ad_creative.get('asset_feed_spec', {}).get('images_valid_amount', False),
                    'titles_valid_amount': ad_creative.get('asset_feed_spec', {}).get('titles_valid_amount', False),
                    'bodies_valid_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_valid_amount', False),
                    'descriptions_valid_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_valid_amount', False),
                    'call_to_action_types_valid_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_valid_amount', False),
                    'images_max_amount': ad_creative.get('asset_feed_spec', {}).get('images_max_amount', 0),
                    'titles_max_amount': ad_creative.get('asset_feed_spec', {}).get('titles_max_amount', 0),
                    'bodies_max_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_max_amount', 0),
                    'descriptions_max_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_max_amount', 0),
                    'call_to_action_types_max_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_max_amount', 0),
                    'unique_titles': ad_creative.get('asset_feed_spec', {}).get('unique_titles', False),
                    'unique_bodies': ad_creative.get('asset_feed_spec', {}).get('unique_bodies', False),
                    'unique_descriptions': ad_creative.get('asset_feed_spec', {}).get('unique_descriptions', False),
                    'daily_budget_valid': ad_creative.get('asset_feed_spec', {}).get('daily_budget_valid', False),
                    'min_daily_budget': ad_creative.get('asset_feed_spec', {}).get('min_daily_budget', 0),
                    'proposal_url': ','.join([u.get('website_url', '') for u in ad_creative.get('asset_feed_spec', {}).get('link_urls', [])]),
                    'proposal_url_valid': ad_creative.get('asset_feed_spec', {}).get('link_url_valid', False),
                    'proposal_locations': ad_set_published.get('proposal_locations', []),
                    'locations': ad_creative.get('asset_feed_spec', {}).get('locations', []),
                    'locations_valid': ad_creative.get('asset_feed_spec', {}).get('locations_valid', False),
                }

            creatives.append(creative_published)

        data = {
            "campaign": campaign,
            "creatives": creatives,
            "meta_url": f"https://adsmanager.facebook.com/adsmanager/manager/campaigns/edit?act={self.ad_account_id}&selected_campaign_ids={campaign_id}"
        }

        return data
    
    def _update_campaign_setup(self, campaign_setup_id, meta_campaign_id, meta_campaign_name, meta_adsets):
        payload = {
            'meta_published': True,
            'meta_campaign_id': f"{meta_campaign_id}",
            'meta_campaign_name': meta_campaign_name,
            'meta_resources': meta_adsets
        }

        self.campaign_publish_repository.update(campaign_setup_id, payload)

    @staticmethod
    def _is_meta_auth_error(exception):
        """Clasifica una excepcion capturada como error de autenticacion de
        Meta (codigo 31 / subcodigo 3858385), sin poder lanzar nunca.

        Requirement 5.3: acceso seguro al atributo `text` (getattr con
        default None), de modo que la clasificacion nunca produzca una
        excepcion secundaria.
        Requirement 5.4/5.5: cualquier excepcion sin `text`, o con un `text`
        que no sea un dict, se clasifica como NO de autenticacion.
        Requirement 5.6: los marcadores se buscan tanto en el propio dict
        `text` (forma plana) como en el dict anidado bajo la clave `error`
        (forma externa producida por `RESTClientException(response.json())`).
        """
        text = getattr(exception, 'text', None)
        if not isinstance(text, dict):
            return False

        candidates = [text]
        nested_error = text.get('error')
        if isinstance(nested_error, dict):
            candidates.append(nested_error)

        for candidate in candidates:
            if candidate.get('code') == 31 or candidate.get('error_subcode') == 3858385:
                return True

        return False

    def _group_creatives_by_adset(self, creatives: list) -> dict:
        """Agrupa los creativos (ads) por id (adset_id), devolviendo un dict
        """
        # Creamos el contenedor que agrupa de forma automática
        objetos_agrupados = defaultdict(list)

        # Llenamos el contenedor recorriendo la lista
        for objeto in creatives:
            objetos_agrupados[objeto["id"]].append(objeto)

        # Lo convertimos a un diccionario estándar de Python
        resultado = dict(objetos_agrupados)
        return resultado

    def execute(self):
        decoded_access_token = self._get_decoded_access_token()

        # Buscar campaign
        campaign = self._get_campaign()

        # Buscar los creativos a publicar
        creatives_to_publish = []
        for creative in self.creatives:
            # Buscar ad_channel
            ad_channel = self._get_ad_channel(creative.get('adset_id'), creative.get('ad_id'), creative.get('adchannel_id'))
            creatives_to_publish.append(ad_channel.get('attributes', {}).get('channel_creative'))

        self.lead_gen_form_id = None
        for c in creatives_to_publish:
            if c and c.get('lead_gen_form_id'):
                self.lead_gen_form_id = c.get('lead_gen_form_id')
                break

        self.whatsapp_number_id = None
        for c in creatives_to_publish:
            if c and c.get('whatsapp_number_id'):
                self.whatsapp_number_id = c.get('whatsapp_number_id')
                break

        # Buscar campaign setup
        campaign_setup = self._get_campaign_setup()

        # Validar que tenga todo lo necesario para publicar
        is_ready = self._is_campaign_valid(creatives_to_publish)

        if not is_ready:
            logger.error("The campaign is not ready to launch.")
            raise IncorrectValidationException("The campaign is not ready to launch.")

        # Construir meta_campaign
        meta_campaign = self._build_meta_campaign(campaign, campaign_setup, decoded_access_token)

        meta_campaign_id = None
        meta_adsets = []
        created_ad_creative_ids = []

        try:
            # Publicar campaign a meta
            meta_campaign_id = self._publish_campaign(meta_campaign)

            if self.campaign_mode == CreativeType.STANDARD.value:
                logger.info("Campaign mode is STANDARD.")
                creatives_std_to_publish = self._group_creatives_by_adset(creatives_to_publish)
                for adset_id in creatives_std_to_publish.keys():
                    logger.info(f"Processing adset: {adset_id}")
                    # Publicar el adset correspondiente a este grupo de creatives
                    adset = creatives_std_to_publish[adset_id][0]
                    adset['campaign_id'] = meta_campaign_id
                    meta_adset_id = self._publish_adset(adset, decoded_access_token)
                    adset['meta_adset_id'] = meta_adset_id
    
                    meta_adset = {'adset_id': f"{meta_adset_id}", 'ads': []}

                    for adset in creatives_std_to_publish[adset_id]:
                        for ad in adset.get('ads', []):
                            if adset.get('lead_gen_form_id'):
                                ad['lead_gen_form_id'] = adset.get('lead_gen_form_id')
                            elif self.lead_gen_form_id:
                                ad['lead_gen_form_id'] = self.lead_gen_form_id
        
                            if adset.get('whatsapp_number_id'):
                                ad['whatsapp_number_id'] = adset.get('whatsapp_number_id')
                            elif self.whatsapp_number_id:
                                ad['whatsapp_number_id'] = self.whatsapp_number_id
        
                            # Publicar las imagenes
                            ad['adset_id'] = meta_adset_id
                            self._publish_media(ad, decoded_access_token)
        
                            # Publicar adCreative
                            ad_creative_id = self._publish_ad_creative(ad, decoded_access_token)
                            created_ad_creative_ids.append(ad_creative_id)
        
                            # Publicar el ad
                            ad_id = self._publish_ad(ad, decoded_access_token)
        
                            meta_adset['ads'].append({'ad_id': f"{ad_id}"})
                        
                    meta_adsets.append(meta_adset)

            elif self.campaign_mode == CreativeType.DYNAMIC.value:
                logger.info("Campaign mode is DYNAMIC.")

                # Publicar cada adset
                for adset in creatives_to_publish:
                    adset['campaign_id'] = meta_campaign_id
                    meta_adset_id = self._publish_adset(adset, decoded_access_token)
                    adset['id'] = meta_adset_id

                    meta_adset = {'adset_id': f"{meta_adset_id}", 'ads': []}

                    # Publicar cada ad
                    for ad in adset.get('ads'):
                        if adset.get('lead_gen_form_id'):
                            ad['lead_gen_form_id'] = adset.get('lead_gen_form_id')
                        elif self.lead_gen_form_id:
                            ad['lead_gen_form_id'] = self.lead_gen_form_id

                        if adset.get('whatsapp_number_id'):
                            ad['whatsapp_number_id'] = adset.get('whatsapp_number_id')
                        elif self.whatsapp_number_id:
                            ad['whatsapp_number_id'] = self.whatsapp_number_id

                        # Publicar las imagenes
                        ad['adset_id'] = meta_adset_id
                        self._publish_media(ad, decoded_access_token)

                        # Publicar adCreative
                        ad_creative_id = self._publish_ad_creative(ad, decoded_access_token)
                        created_ad_creative_ids.append(ad_creative_id)

                        # Publicar el ad
                        ad_id = self._publish_ad(ad, decoded_access_token)

                        meta_adset['ads'].append({'ad_id': f"{ad_id}"})

                    meta_adsets.append(meta_adset)

        except Exception as e:
            logger.error(f"Error publishing campaign: {e}")

            # Requirements 5.7, 5.8, 5.9: el rollback se invoca de forma
            # incondicional, antes de clasificar la excepción, de modo que
            # tanto la ruta de autenticación como cualquier otra lo ejecuten.
            # Requirement 5.10: cuando `_publish_campaign` falló,
            # `meta_campaign_id` es None y `created_ad_creative_ids` está
            # vacía, con lo cual `_rollback_publish` es un no-op y no invoca
            # `_delete_object` ni una sola vez.
            # Requirement 5.13: el try/except acotado protege el *sitio de
            # invocación* (no modifica `_rollback_publish` ni
            # `_delete_object`) y garantiza que un fallo inesperado durante
            # el rollback no enmascare la excepción original.
            try:
                self._rollback_publish(meta_campaign_id, created_ad_creative_ids, decoded_access_token)
            except Exception as rollback_error:
                logger.error(f"Error during rollback, propagating original exception: {rollback_error}")

            # Requirement 5.7: el tipo de excepción y el mensaje visible para
            # el usuario se mantienen exactamente como hoy.
            if self._is_meta_auth_error(e): # Autenticación requerida
                raise SinergiaException('META31', 'Autentica tu cuenta en el administrador de anuncios')

            # Requirement 5.8/5.9: la excepción original se relanza sin
            # alterar su tipo, su mensaje ni sus atributos.
            raise e

        # Actualizar IDs de los objetos publicados
        self._update_campaign_setup(campaign_setup.get('id', 0), meta_campaign_id, meta_campaign.get('name', ''), meta_adsets)

        # Actualizar estado de la campaña publicada

        # construir response
        campaign_published = self._build_response(meta_campaign_id, meta_campaign, creatives_to_publish)

        return campaign_published


class FacebookGetPageAdsPostsUseCase:
    def __init__(self):
        self.graph_api_base = os.getenv("FACEBOOK_GRAPH_API_BASE")

    def execute(self, user_id, page_id):
        redis_key = f"facebook_access_token:{user_id}"
        access_token = redis_client.get(redis_key)

        if not access_token:
            return {"error": "No access token found in Redis. Please re-authenticate."}, 401

        access_token = access_token.decode("utf-8")

        # 1. Get Page Access Token
        page_url = f"{self.graph_api_base}/{page_id}"
        page_access_token = None
        try:
            page_res = requests.get(page_url, params={"fields": "access_token", "access_token": access_token}, timeout=10)
            page_data = page_res.json()
            page_access_token = page_data.get("access_token")
        except Exception as e:
            logger.error(f"Error fetching page access token: {e}")

        # 2. Get Page Ads Posts (specifically triggers pages_manage_ads permission)
        url = f"{self.graph_api_base}/{page_id}/ads_posts"
        params = {
            "access_token": page_access_token or access_token
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            if "error" in data:
                return {"error": data["error"]}, 400
            return data, 200
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to connect to Facebook Graph API", "details": str(e)}, 502

class FacebookExportAssetsPostLaunchCampaignUseCase():

    _REQUIRED_PAYLOAD_KEYS = ('campaign_id', 'brand_id', 'ad_id', 'adset_id', 'adchannel_id')

    _TEXT_CATEGORY_FILENAMES = {
        'primary_text': 'primary_texts.txt',
        'headline': 'headlines.txt',
        'description': 'descriptions.txt',
        'cta': 'ctas.txt',
    }

    _IMAGE_DOWNLOAD_TIMEOUT = 10
    _DEFAULT_IMAGE_EXTENSION = '.jpg'
    _ZIP_IMAGES_PREFIX = 'images/'
    _MANIFEST_FILENAME = 'manifest.txt'

    # --- ZIP package filename (Requirements 10.4, 10.12-10.15) ---
    _FILENAME_PREFIX = 'assets'
    _FILENAME_EXTENSION = '.zip'
    _FILENAME_SEPARATOR = '_'
    _FILENAME_EMPTY_FALLBACK = 'assets.zip'
    _FILENAME_COMPONENT_MAX_LENGTH = 60
    _FILENAME_FORBIDDEN_CHARACTERS = re.compile(r'[^A-Za-z0-9._-]')
    _FILENAME_UNDERSCORE_RUN = re.compile(r'_{2,}')
    _FILENAME_COMPONENT_LABELS = ('campaign_name', 'ad_set_name', 'ad_name', 'channel_name')

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.account_repository = AccountRepository()
        self.campaign_channel_publish_repository = CampaignChannelPublishRepository()
        self.ad_channel_repository = AdChannelRepository()
        self.campaign_repository = CampaignRepository()

    def _get_decoded_access_token(self):
        redis_key = f"facebook_access_token:{self.user_id}"
        access_token = redis_client.get(redis_key)
        if not access_token:
            raise NotAccessException("No access token found in Redis. Please re-authenticate.")

        return access_token.decode("utf-8")

    def _get_account(self):
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.user_id}")
            raise DataNotFoundException('Account not found')
        return account

    def _get_parent_account(self):
        account = self._get_account()
        parent_account = (
            account['attributes']['parent_account']['data']['id']
            if account.get('attributes', {}).get('parent_account', {}).get('data')
            else account['id']
        )
        return parent_account

    def _validate_payload(self, payload: ExportAssetsDataDict) -> None:
        """Validate the export payload before any network or Strapi access.

        Raises ParametersNotFoundException when the payload is not a dict, or
        when any of the five required keys is absent, None or an empty string.
        """
        if not isinstance(payload, dict):
            logger.error(
                f"Export assets payload must be a dict, got {type(payload).__name__}. "
                f"Required keys: {', '.join(self._REQUIRED_PAYLOAD_KEYS)}"
            )
            raise ParametersNotFoundException(
                'campaign_id, brand_id, ad_id, adset_id and adchannel_id are required'
            )

        invalid_keys: List[str] = []
        for key in self._REQUIRED_PAYLOAD_KEYS:
            if key not in payload:
                invalid_keys.append(key)
                continue
            value = payload[key]
            if value is None or (isinstance(value, str) and value == ''):
                invalid_keys.append(key)

        if invalid_keys:
            logger.error(
                f"Missing or invalid export assets payload keys: {', '.join(invalid_keys)}"
            )
            raise ParametersNotFoundException(
                'campaign_id, brand_id, ad_id, adset_id and adchannel_id are required'
            )

    def _get_campaign(self, campaign_id: Any, brand_id: Any, parent_account: Any) -> Dict[str, Any]:
        """Resolve the campaign by id, brand and parent account.

        Performs a single invocation of
        self.campaign_repository.get_by_id_brand_and_account and considers the
        campaign resolved only when the returned value is a dict instance with
        at least one key. The DataNotFoundException message is indistinguishable
        between the three possible failure reasons (unknown campaign, different
        brand, different account) so the response does not reveal which one was
        not met. Any exception raised by the repository is propagated untouched,
        preserving its original type, message and traceback.
        """
        try:
            campaign = self.campaign_repository.get_by_id_brand_and_account(
                campaign_id, brand_id, parent_account
            )
        except Exception as e:
            logger.error(
                f"Error retrieving campaign {campaign_id} for brand {brand_id} "
                f"and account {parent_account}: {e}"
            )
            raise

        if not isinstance(campaign, dict) or not campaign:
            logger.error(
                f"Campaign not found: {campaign_id} for brand {brand_id} "
                f"and account {parent_account}"
            )
            raise DataNotFoundException('Campaign not found or does not belong to account')

        return campaign

    def _get_ad_channel(self, campaign_id: Any, adset_id: Any, ad_id: Any, adchannel_id: Any) -> Dict[str, Any]:
        """Resolve the creative (ad channel) for the requested hierarchy.

        Performs a single invocation of
        self.ad_channel_repository.get_by_campaign_and_ad_channel_id passing the
        four identifiers positionally, in that order, exactly as they arrive
        from the export payload and without transforming or normalising them.
        Any falsy returned value (None, {}, ...) is logged and reported as
        DataNotFoundException, which is propagated to the caller.

        populate_names=True asks that same single query to bring the name
        relations populated (ad_ref2, the ad_set_ref2 nested inside it and
        channel_ref), so the four source names of the ZIP package filename are
        read from this record with zero additional Strapi queries.
        """
        ad_channel = self.ad_channel_repository.get_by_campaign_and_ad_channel_id(
            campaign_id, adset_id, ad_id, adchannel_id, populate_names=True
        )

        if not ad_channel:
            logger.error(
                f"Creative not found for campaign {campaign_id}, adset {adset_id}, "
                f"ad {ad_id} and ad channel {adchannel_id}"
            )
            raise DataNotFoundException('Creative not found')

        return ad_channel

    def _resolve_channel_id(self, ad_channel: Dict[str, Any]) -> int:
        """Read the Channel_ID from the nested attributes.channel_ref.data.id.

        Replicates the read pattern of
        FacebookSavePreCheckBaseUseCase._set_channel_id, defaulting to 0 when
        any level of the path is absent or is not a dict, and never raising:
        the failure is left to surface later, when the campaign setup is
        resolved.
        """
        node: Any = ad_channel
        for key in ('attributes', 'channel_ref', 'data'):
            if not isinstance(node, dict):
                return 0
            node = node.get(key, {})

        if not isinstance(node, dict):
            return 0

        return node.get('id', 0)

    def _get_validated_campaign_setup(self, campaign_id: Any, channel_id: int) -> Dict[str, Any]:
        """Resolve the campaign setup and validate publication and campaign mode.

        Performs a single invocation of
        self.campaign_channel_publish_repository.get_by_campaign_id_and_channel_id
        with campaign_id and channel_id positionally, in that order. The
        invocation is emitted as well when channel_id holds the default value 0,
        so the failure surfaces here as a DataNotFoundException instead of being
        silently skipped.

        Validation order is normative: publication is checked before campaign
        mode, so a campaign setup that is neither published nor STANDARD raises
        exactly one exception, the one about the missing publication, and the
        mode check is not evaluated. meta_published is compared by identity
        against True (1, 'True' and 'true' are rejected) and the mode is
        compared case-sensitively and without whitespace normalisation
        ('standard' and ' STANDARD ' are rejected).
        """
        campaign_setup = self.campaign_channel_publish_repository.get_by_campaign_id_and_channel_id(
            campaign_id, channel_id
        )

        if not campaign_setup or not isinstance(campaign_setup, dict):
            logger.error(
                f"Campaign publish record not found for campaign_id: {campaign_id} "
                f"and channel_id: {channel_id}"
            )
            raise DataNotFoundException('Campaign publish record not found')

        meta_published = campaign_setup.get('attributes', {}).get('meta_published')
        meta_campaign_mode = campaign_setup.get('attributes', {}).get('meta_campaign_mode')

        if meta_published is not True:
            logger.error(
                f"Campaign {campaign_id} is not published, cannot export surplus assets"
            )
            raise IncorrectValidationException('Campaign is not published')

        if meta_campaign_mode != CreativeType.STANDARD.value:
            logger.error(
                f"Campaign mode {meta_campaign_mode} does not allow surplus assets export"
            )
            raise IncorrectValidationException('Campaign mode does not allow surplus assets export')

        return campaign_setup

    def _download_image(self, visual_url: str) -> Optional[bytes]:
        """Download the binary of a surplus image with a single HTTP GET.

        Exactly one attempt per surplus image, with a 10 second timeout: no
        retry loop and no Session with a retry adapter, replicating the
        requests.get(url, timeout=10) pattern already used by
        FacebookPublishCampaignUseCase.upload_image,
        FacebookLaunchCampaignUseCase._upload_image and
        S3ImageProxyUseCase.execute in this same module.

        Returns the response body when the status code is 200, and None (after
        logger.error) when the status code is different from 200 or when the
        request raises. The capture is `except Exception` and not
        `except requests.exceptions.RequestException` because the image must be
        skipped and the walk continued on any download failure.
        """
        try:
            response = requests.get(visual_url, timeout=self._IMAGE_DOWNLOAD_TIMEOUT)
        except Exception as e:
            logger.error(f"Error downloading surplus image from {visual_url}: {e}")
            return None

        if response.status_code != 200:
            logger.error(
                f"Error downloading surplus image from {visual_url}: status {response.status_code}"
            )
            return None

        # The body is kept as received, without inspecting its size or format
        # and deliberately without opening it with PIL.Image (out of scope).
        return response.content

    @staticmethod
    def _derive_image_extension(visual_url: str) -> str:
        """Derive the file extension of a ZIP image entry from its source URL.

        The extension is taken from the last segment of the URL path component,
        so the query string and the fragment never take part in it:
        urllib.parse.urlsplit isolates .path from .query and .fragment in a
        single step, and rsplit('/', 1)[-1] keeps only the last path segment.

        os.path.splitext is preferred over a manual rsplit('.', 1) because it
        already treats segments without a dot and names starting with a dot
        (such as .gitignore) as having no extension, which is exactly the
        "does not contain an extension" case that falls back to
        _DEFAULT_IMAGE_EXTENSION.

        The capitalisation of the derived extension is preserved as it appears
        in the URL: '.PNG' stays '.PNG'.
        """
        path = urllib.parse.urlsplit(visual_url).path
        last_segment = path.rsplit('/', 1)[-1]
        _, extension = os.path.splitext(last_segment)
        return extension if extension else FacebookExportAssetsPostLaunchCampaignUseCase._DEFAULT_IMAGE_EXTENSION

    @staticmethod
    def _disambiguate_entry_name(entry_name: str, used_names: Set[str]) -> str:
        """Return an entry name that does not collide with the already used ones.

        The _{n} suffix is inserted immediately before the extension, never at
        the end of the whole name: 'images/img.jpg' becomes 'images/img_1.jpg',
        never 'images/img.jpg_1'. The counter starts at 1 and increases while
        the candidate is still present in used_names, so N entries sharing the
        same name produce 'img.jpg', 'img_1.jpg', ..., 'img_{N-1}.jpg'.

        used_names is a Set[str] because it is an unordered membership
        collection, which makes the `candidate in used_names` check O(1).

        With the production data the media format ids are unique within a
        single list, so this method is defensive and normally returns its
        argument unchanged.
        """
        if entry_name not in used_names:
            return entry_name

        base, extension = os.path.splitext(entry_name)
        suffix = 1
        candidate = f"{base}_{suffix}{extension}"
        while candidate in used_names:
            suffix += 1
            candidate = f"{base}_{suffix}{extension}"

        return candidate

    def _collect_surplus_images(self, ad_channel: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Walk media_formats once and return a two element tuple.

        [0] List[Dict[str, Any]] - descriptors of the surplus images that were
            downloaded successfully, in the order of appearance within
            media_formats. Each descriptor has the shape
            {'entry_name': str, 'content': bytes}.
        [1] List[str] - identifiers of the not-included assets, in that same
            order of appearance within media_formats.

        Only the keys id, visual_url and pinned are read from each element:
        uid, unit, width, height, errors, visual_id and preview_url are
        ignored, and in particular the binary of preview_url is never
        downloaded. Never raises because of an individual download failure nor
        because of a degraded structure.
        """
        media_formats = ad_channel.get('attributes', {}).get('media_formats')

        # Absent, None or non-list: both sets are treated as empty.
        if not isinstance(media_formats, list):
            logger.warning(
                f"media_formats is not a list for ad_channel; treating surplus images "
                f"and not-included assets as empty. type={type(media_formats).__name__}"
            )
            return [], []

        collected: List[Dict[str, Any]] = []
        not_included_ids: List[str] = []
        used_names: Set[str] = set()

        for index, media_format in enumerate(media_formats):
            # A non-dict element is skipped without logging an error. It is not
            # a not-included asset because it is not a surplus candidate.
            if not isinstance(media_format, dict):
                continue

            # pinned is compared by identity, so 'True', 1 and arbitrary truthy
            # values are still surplus candidates. A pinned element is not a
            # not-included asset either: it is the published asset, not a
            # surplus the user is expecting.
            if media_format.get('pinned') is True:
                continue

            # From here on the element IS a surplus candidate: either its
            # binary ends up as an images/... entry, or its identifier ends up
            # in the not-included set. Never both, never neither.

            # The identifier is derived ONCE and BEFORE branching by cause, so
            # the {id} of the images/... entry name and the identifier reported
            # in manifest.txt come literally from the same expression and
            # cannot diverge. The index is the zero-based index within the
            # complete media_formats, pinned and non-dict elements included.
            raw_id = media_format.get('id')
            entry_id = str(raw_id) if raw_id is not None else str(index)

            visual_url = media_format.get('visual_url')
            # Cause 1 of not-included asset: visual_url is not a str or is
            # empty after stripping.
            if not isinstance(visual_url, str) or len(visual_url.strip()) < 1:
                not_included_ids.append(entry_id)
                continue

            content = self._download_image(visual_url)
            # Causes 2 and 3 of not-included asset: a status code different
            # from 200, or a download that raised. Both are observed as
            # _download_image returning None, and both were already logged
            # there.
            if content is None:
                not_included_ids.append(entry_id)
                continue

            extension = self._derive_image_extension(visual_url)
            entry_name = f"{self._ZIP_IMAGES_PREFIX}{entry_id}{extension}"
            entry_name = self._disambiguate_entry_name(entry_name, used_names)
            used_names.add(entry_name)

            collected.append({'entry_name': entry_name, 'content': content})

        # The number of skipped images is the size of the not-included asset
        # set, not just the number of download failures.
        logger.info(
            f"Surplus images downloaded: {len(collected)}, skipped: {len(not_included_ids)}"
        )
        return collected, not_included_ids

    def _collect_surplus_texts(self, ad_channel: Dict[str, Any]) -> Dict[str, List[str]]:
        """Return a mapping of text category to its surplus texts.

        The four text categories of _TEXT_CATEGORY_FILENAMES are always
        present as keys, initialised as empty lists (deliberately not a
        defaultdict), so _build_zip_package can iterate the mapping
        deterministically regardless of which categories appeared.

        The order of appearance, the duplicates and the concatenation between
        repeated attributes of the same category are preserved. Never raises
        because of a degraded structure.
        """
        collected: Dict[str, List[str]] = {category: [] for category in self._TEXT_CATEGORY_FILENAMES}

        channel_attributes = ad_channel.get('attributes', {}).get('channel_attributes')

        # Absent, None or non-list: the four categories stay empty.
        if not isinstance(channel_attributes, list):
            logger.warning(
                f"channel_attributes is not a list for ad_channel; treating surplus texts as empty. "
                f"type={type(channel_attributes).__name__}"
            )
            return collected

        for attribute in channel_attributes:
            # A non-dict attribute, a missing name, a None name or a non-str
            # name are skipped without logging an error.
            if not isinstance(attribute, dict):
                continue

            name = attribute.get('name')
            if not isinstance(name, str):
                continue

            # Exact, case sensitive comparison against the four categories,
            # with no whitespace normalisation: 'Primary_Text', 'PRIMARY_TEXT'
            # and ' primary_text ' are all unrecognised names.
            if name not in self._TEXT_CATEGORY_FILENAMES:
                continue

            payloads = attribute.get('payloads')
            # payloads absent, None or non-list: the category is treated as
            # empty and the next attribute is processed.
            if not isinstance(payloads, list):
                continue

            for item in payloads:
                # A non-dict element of payloads is skipped.
                if not isinstance(item, dict):
                    continue

                # id must be present and different from 0 and '0'. Note that
                # id == 0 also excludes False, since False == 0 in Python.
                item_id = item.get('id')
                if item_id is None:
                    logger.warning(f"Skipping payload without id in channel_attribute '{name}'")
                    continue
                if item_id == 0 or item_id == '0':
                    continue

                # payload absent, None, non-str or blank after stripping.
                text = item.get('payload')
                if not isinstance(text, str) or len(text.strip()) < 1:
                    continue

                # The asymmetry is deliberate: strip() decides the exclusion,
                # but the original untrimmed value is the one accumulated, in
                # order of appearance, keeping duplicates and concatenating
                # repeated attributes of the same category.
                collected[name].append(text)

        return collected

    def _build_zip_package(
        self,
        images: List[Dict[str, Any]],
        texts: Dict[str, List[str]],
        not_included_ids: List[str],
    ) -> bytes:
        """Build the ZIP package fully in memory and return its bytes.

        Image entries live exclusively under the images/ prefix, in the order
        received (which is the order of appearance within media_formats). Text
        entries — the .txt file of every non empty text category, plus
        manifest.txt when there is at least one not-included asset — live
        exclusively at the root of the archive.

        manifest.txt is derived exclusively from not_included_ids, with zero
        reads of the channel attributes: it is not a text category and no value
        of the texts mapping can produce an entry with that name.
        """
        buffer = BytesIO()

        # Requirement 9.1: in memory, ZIP_DEFLATED, no temporary files. Each
        # entry inherits the compression of the ZipFile, so compress_type is
        # not passed per writestr call.
        with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
            # Requirements 9.15, 9.16: images under images/, in the order of
            # appearance of media_formats (already fixed by
            # _collect_surplus_images, which also produced final entry names).
            for image in images:
                zip_file.writestr(image['entry_name'], image['content'])

            # Requirements 9.6, 9.7, 9.8, 9.15: one .txt at the ROOT per NON
            # empty category.
            for category, filename in self._TEXT_CATEGORY_FILENAMES.items():
                category_texts = texts.get(category, [])
                if not category_texts:
                    # Requirement 9.8: an empty category has no file.
                    continue
                # Requirement 9.7: '\n' as separator BETWEEN elements, with no
                # trailing newline, encoded in UTF-8.
                zip_file.writestr(filename, '\n'.join(category_texts).encode('utf-8'))

            # Requirements 9.9, 9.10, 9.11, 9.12, 9.15: manifest.txt at the
            # root if and only if there are not-included assets, derived
            # EXCLUSIVELY from not_included_ids, with the same writing
            # convention as the category .txt files. An empty list is falsy, so
            # writing and omitting are the two branches of the same
            # expression: there is no path that writes an empty manifest.txt.
            # It is written last so namelist() stays stable and predictable.
            if not_included_ids:
                zip_file.writestr(
                    self._MANIFEST_FILENAME,
                    '\n'.join(not_included_ids).encode('utf-8')
                )

        if not images and not any(texts.values()):
            if not_included_ids:
                # Requirement 9.14: the package ends up with manifest.txt as
                # its only entry.
                logger.info(
                    f"No surplus assets could be packaged; returning a ZIP package with "
                    f"manifest.txt only. not_included={len(not_included_ids)}"
                )
            else:
                # Requirement 9.13: the THREE sets are empty, so the ZIP has no
                # entries at all.
                logger.info("No surplus assets found; returning an empty ZIP package")

        # Requirement 10.2: the whole buffer, read AFTER closing the ZipFile.
        # Leaving the with block is what writes the End Of Central Directory
        # record; reading the buffer inside it would yield an incomplete ZIP.
        return buffer.getvalue()

    @staticmethod
    def _read_nested_name(node: Any, *keys: str) -> Any:
        """Walk a nested key path and return None as soon as a level is missing.

        Same defensive criterion as _resolve_channel_id, with None — and not 0 —
        as the default, because here the default feeds the empty filename
        component of a missing source name and not a Strapi query. Never raises
        AttributeError nor TypeError: a level that is absent or whose value is
        not a dict simply ends the walk. The traversed record is only read, and
        never modified.
        """
        current: Any = node
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)

        return current

    @classmethod
    def _sanitize_filename_component(cls, raw_name: Any) -> str:
        """Return the sanitised filename component derived from raw_name.

        Returns the empty string for anything that is not a str instance, and
        also when the sanitisation leaves nothing behind. It never raises and
        never substitutes the value by an identifier of the export payload nor
        by any other internal identifier.
        """
        # Anything that is not a str yields the empty component, and in no case
        # is it replaced by an identifier of the payload.
        if not isinstance(raw_name, str):
            return ''

        # (a) + (b): NFKD, discarding of the combining characters and of every
        # character without an ASCII equivalence. 'Campaña Otoño' becomes
        # 'Campana Otono'.
        decomposed = unicodedata.normalize('NFKD', raw_name)
        ascii_only = ''.join(
            character for character in decomposed
            if not unicodedata.combining(character)
        ).encode('ascii', 'ignore').decode('ascii')

        # (c) + (d): whitelist of [A-Za-z0-9._-] and collapse of the repeated
        # '_' the replacement may have produced.
        whitelisted = cls._FILENAME_FORBIDDEN_CHARACTERS.sub('_', ascii_only)
        collapsed = cls._FILENAME_UNDERSCORE_RUN.sub('_', whitelisted)

        # (e) + (f): trimming of both ends, 60 character cap, and trimming
        # again of the trailing characters the truncation may have exposed.
        trimmed = collapsed.strip('_.')
        return trimmed[:cls._FILENAME_COMPONENT_MAX_LENGTH].rstrip('_.')

    def _resolve_filename_components(
        self,
        campaign: Dict[str, Any],
        ad_channel: Dict[str, Any],
    ) -> Tuple[str, str, str, str]:
        """Read and sanitise the four source names of the ZIP package filename.

        The campaign name comes from the record already resolved by
        _get_campaign, of which exclusively attributes.name is read, so no
        additional Strapi query is emitted. The other three come from the ad
        channel record, whose name relations were populated by the very same
        query that resolved it. All four reads are read only: neither campaign
        nor ad_channel is modified.

        Emits exactly one logger.warning per invocation when at least one
        component ends up empty, naming which of the four they are, and returns
        the four sanitised components in the order campaign, ad set, ad,
        channel.
        """
        raw_names = (
            # The only attribute of the campaign record that is ever read.
            campaign.get('attributes', {}).get('name')
            if isinstance(campaign, dict) else None,
            self._read_nested_name(
                ad_channel, 'attributes', 'ad_ref2', 'data', 'attributes',
                'ad_set_ref2', 'data', 'attributes', 'name',
            ),
            self._read_nested_name(
                ad_channel, 'attributes', 'ad_ref2', 'data', 'attributes', 'name',
            ),
            self._read_nested_name(
                ad_channel, 'attributes', 'channel_ref', 'data', 'attributes', 'name',
            ),
        )

        # Each source name is sanitised independently, so one missing name
        # never affects the component of another.
        components = tuple(
            self._sanitize_filename_component(raw_name) for raw_name in raw_names
        )

        empty_labels = [
            label
            for label, component in zip(self._FILENAME_COMPONENT_LABELS, components)
            if not component
        ]
        if empty_labels:
            # A single warning per invocation, never one per empty component,
            # and never an exception: the export goes on.
            logger.warning(
                f"Export filename components resolved empty: {', '.join(empty_labels)}"
            )

        return components

    def _build_export_filename(self, components: Tuple[str, str, str, str]) -> str:
        """Build the ZIP package filename out of the four sanitised components.

        Returns 'assets_{campaign_name}_{ad_set_name}_{ad_name}_{channel_name}.zip',
        or 'assets.zip' when the four components are the empty string, which
        avoids the degenerate 'assets____.zip'.

        An empty component keeps its position, which shows up as two
        consecutive '_'. That is deliberate: the client sees that a name is
        missing and no identifier leaves the server through this path. The
        collapse of repeated '_' happens INSIDE each component, before joining,
        so the join never erases those gaps.
        """
        if not any(components):
            return self._FILENAME_EMPTY_FALLBACK

        return '{prefix}{sep}{body}{extension}'.format(
            prefix=self._FILENAME_PREFIX,
            sep=self._FILENAME_SEPARATOR,
            body=self._FILENAME_SEPARATOR.join(components),
            extension=self._FILENAME_EXTENSION,
        )

    def execute(self, payload: ExportAssetsDataDict) -> Dict[str, Any]:
        """Export the surplus assets of a published STANDARD creative as a ZIP.

        Single argument, with no additional nor optional parameters. The
        textual order of this body IS the sequence guarantee: five sequential
        pre-validations (payload, token/account, campaign, ad channel,
        campaign setup) that abort on the first failure, followed by two read
        only filters over the creative and the in memory ZIP packaging. There
        is deliberately no enclosing try/except, so no pre-validation failure
        can be swallowed and turned into a successful export.
        """
        # First operation, before any network call: no Strapi query, no Graph
        # API invocation and no binary download happens if it fails.
        self._validate_payload(payload)

        # The five values are read as they arrive and passed to the
        # repositories verbatim: no int(), no str() and no strip(). None of
        # them takes part in the filename any more, so the number of
        # conversions to string of these values inside execute() is 0.
        campaign_id = payload['campaign_id']
        brand_id = payload['brand_id']
        adset_id = payload['adset_id']
        ad_id = payload['ad_id']
        adchannel_id = payload['adchannel_id']

        # Authentication gate: invoked for its NotAccessException side effect
        # before resolving account, campaign, creative or downloads. The
        # returned token is deliberately discarded, so it is never logged, and
        # never reaches the export result. user_id always comes from
        # self.user_id, never from the payload.
        self._get_decoded_access_token()

        parent_account = self._get_parent_account()

        # Existence and ownership check, and single source of the campaign
        # source name: the record is kept only to read attributes.name from it
        # for the filename. No other attribute is read, it is not passed on to
        # the ad channel or campaign setup resolution, and it does not appear
        # in the export result. The campaigns content type is still queried
        # exactly once.
        campaign = self._get_campaign(campaign_id, brand_id, parent_account)

        # The very same query brings the name relations of the ad set, the ad
        # and the channel populated.
        ad_channel = self._get_ad_channel(campaign_id, adset_id, ad_id, adchannel_id)
        channel_id = self._resolve_channel_id(ad_channel)

        # Publication and campaign mode gate: the returned campaign setup is
        # discarded as well, its only purpose is validation.
        self._get_validated_campaign_setup(campaign_id, channel_id)

        # Positional two element unpacking: the descriptors of the surplus
        # images first, the identifiers of the not-included assets second. The
        # latter travel straight to _build_zip_package as its THIRD argument,
        # never through _collect_surplus_texts, which is what makes
        # manifest.txt derive exclusively from the not-included asset set and
        # not be a text category.
        images, not_included_ids = self._collect_surplus_images(ad_channel)
        texts = self._collect_surplus_texts(ad_channel)
        content = self._build_zip_package(images, texts, not_included_ids)

        # Four sanitised names, none of them derived from an identifier of the
        # export payload.
        filename = self._build_export_filename(
            self._resolve_filename_components(campaign, ad_channel)
        )

        return {
            'content': content,
            'content_type': 'application/zip',
            'filename': filename,
        }

class FacebookGetLaunchCampaignCreativesUseCase():

    _CHANNEL_NAME = 'Meta'
    _META_CAMPAIGN_URL_TEMPLATE = (
        'https://adsmanager.facebook.com/adsmanager/manager/campaigns/edit'
        '?act={meta_account_id}&selected_campaign_ids={meta_campaign_id}'
    )
    _SUPPORTED_CAMPAIGN_MODES = (CreativeType.DYNAMIC.value, CreativeType.STANDARD.value)

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.account_repository = AccountRepository()
        self.campaign_repository = CampaignRepository()
        self.ad_set_repository = AdSetRepository()
        self.campaign_channel_publish_repository = CampaignChannelPublishRepository()
    
    def _get_account(self):
        account = self.account_repository.get_by_email(self.user_id)
        if not account:
            logger.error(f"Account not found: {self.user_id}")
            raise DataNotFoundException('Account not found')
        return account

    def _get_parent_account(self):
        account = self._get_account()
        parent_account = (
            account['attributes']['parent_account']['data']['id']
            if account.get('attributes', {}).get('parent_account', {}).get('data')
            else account['id']
        )
        return parent_account

    @staticmethod
    def _as_list(node: Any, *keys: str) -> List[Any]:
        """Walk a nested key path and return the list found at its end.

        Requirement 5.7: returns [] as soon as one level of the path is
        absent, is None or does not have the expected type, and also when the
        final value is not a list. Never raises AttributeError, TypeError nor
        KeyError: it is, for collections, the counterpart of what
        _resolve_channel_id is for the Channel_ID.
        """
        current: Any = node
        for key in keys:
            if not isinstance(current, dict):
                return []
            current = current.get(key)

        if not isinstance(current, list):
            return []

        return current

    @staticmethod
    def _resolve_channel_id(ad_channel: Dict[str, Any]) -> int:
        """Read the Channel_ID from the nested attributes.channel_ref.data.id.

        Requirements 6.1, 6.2: replicates the read pattern of the already
        existing FacebookSavePreCheckBaseUseCase._set_channel_id, defaulting to
        0 when any level of the path is absent, is None or is not a dict, and
        never raising: the failure is left to surface later, as the
        DataNotFoundException raised while resolving the campaign setup.
        """
        node: Any = ad_channel
        for key in ('attributes', 'channel_ref', 'data'):
            if not isinstance(node, dict):
                return 0
            node = node.get(key, {})

        if not isinstance(node, dict):
            return 0

        return node.get('id', 0)

    @staticmethod
    def _select_ad_channel(ad: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return the selected ad-channel of an ad, or None when there is none.

        Requirement 5.3: returns the first element of
        attributes.ad_channels.data whose attributes.selected evaluates as
        true, applying the same selection criterion as the line
        `next((ch for ch in ad_channels_data if ch['attributes'].get("selected")), None)`
        of MetaAdsPayloadBuilder.build_asset_feed_spec.

        Requirements 5.4, 5.7: returns None when no element is selected, and
        treats an element without 'attributes', or whose 'attributes' is not a
        dict, as not selected, without raising.
        """
        ad_channels = FacebookGetLaunchCampaignCreativesUseCase._as_list(
            ad, 'attributes', 'ad_channels', 'data'
        )

        for ad_channel in ad_channels:
            if not isinstance(ad_channel, dict):
                continue

            attributes = ad_channel.get('attributes')
            if not isinstance(attributes, dict):
                continue

            if attributes.get('selected'):
                return ad_channel

        return None

    def _get_campaign(self, campaign_id: Any, brand_id: Any, parent_account: Any) -> Dict[str, Any]:
        """Resolve the target campaign by id, brand and parent account.

        Requirement 4.1: performs a single invocation of
        self.campaign_repository.get_by_id_brand_and_account, passing the three
        values positionally and untransformed, and considers the campaign
        resolved only when the returned value is a dict instance with at least
        one key. Requirement 4.4: uses the repository instance created by the
        constructor, without instantiating a new one and without issuing any
        additional query to the 'campaigns' content type. Requirement 4.6: the
        brand_id is consumed exclusively as a filter argument, with 0 queries
        to the 'brands' content type.

        Requirements 4.2, 4.3: logs the three values used with logger.error and
        raises DataNotFoundException with a message indistinguishable between
        the three possible failure reasons (unknown campaign, campaign of
        another brand, campaign of another account), so the response does not
        reveal the existence of campaigns of other accounts.
        """
        campaign = self.campaign_repository.get_by_id_brand_and_account(
            campaign_id, brand_id, parent_account
        )

        if not isinstance(campaign, dict) or not campaign:
            logger.error(
                f"Campaign not found: {campaign_id} for brand {brand_id} "
                f"and account {parent_account}"
            )
            raise DataNotFoundException('Campaign not found or does not belong to account')

        return campaign

    def _collect_published_creatives(
        self, campaign_id: Any, brand_id: Any,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Collect the usable published creatives and the Channel_ID.

        Requirement 5.1: performs a single invocation of the ad-sets query,
        passing campaign_id and brand_id as they were received, and walks the
        response in memory with 0 queries to 'ads', 'ad-channels' and
        'channel-v2s' and 0 ChannelRepository instances (Requirements 5.10,
        6.3).

        Returns a two element tuple:

          [0] List[Dict[str, Any]] - descriptors of the usable published
              creatives, in the order of Requirement 7.5. Each descriptor has
              the form {'creative': dict, 'adchannel_id': Any}, where
              'creative' is a REFERENCE to the stored channel_creative dict,
              not a copy, and 'adchannel_id' is kept only for log messages
              (Requirement 8.6).
          [1] int - the Channel_ID of the FIRST selected ad-channel of the
              walk, or 0 (Requirements 6.1, 6.2, 6.4).

        Raises DataNotFoundException when the query returns no results
        (Requirement 5.2) or when the number of descriptors is 0
        (Requirement 5.9), so a query result with an empty creatives list is
        never returned. Skips, without raising, the ads without a selected
        ad-channel (Requirement 5.4, without log), and with logger.warning the
        degraded channel_creative (Requirement 5.5) and the published creatives
        whose 'ads' is unusable (Requirement 5.6). The walk is read-only: no
        statement assigns over ad_set, ad, ad_channel nor creative
        (Requirement 5.8), and there is no try/except block: the defense
        against degraded structures relies on isinstance and .get() with
        default (Requirement 10.7).
        """
        response = self.ad_set_repository.get_by_campaign_and_brand_with_selected_ad_channels(
            campaign_id, brand_id
        )

        # Requirement 5.2: None, non-dict, 'data' absent, non-list or empty list.
        ad_sets = response.get('data') if isinstance(response, dict) else None
        if not isinstance(ad_sets, list) or not ad_sets:
            logger.error(
                f"Ad sets not found for campaign_id: {campaign_id} and brand_id: {brand_id}"
            )
            raise DataNotFoundException('Published creatives not found')

        descriptors: List[Dict[str, Any]] = []
        channel_id = 0
        channel_id_resolved = False

        for ad_set in ad_sets:
            # Requirement 5.7: degraded attributes / ads / ads.data -> [].
            for ad in self._as_list(ad_set, 'attributes', 'ads', 'data'):
                ad_channel = self._select_ad_channel(ad)
                if ad_channel is None:
                    # Requirement 5.4: the ad is skipped, without exception and without log.
                    continue

                # Requirements 6.1, 6.4, 6.5: the Channel_ID is fixed with the
                # FIRST selected ad-channel of the walk; the later ones can
                # only produce a mismatch warning.
                current_channel_id = self._resolve_channel_id(ad_channel)
                if not channel_id_resolved:
                    channel_id = current_channel_id
                    channel_id_resolved = True
                elif current_channel_id != channel_id:
                    logger.warning(
                        f"Channel id mismatch: keeping {channel_id}, "
                        f"found {current_channel_id}"
                    )

                attributes = ad_channel.get('attributes') if isinstance(ad_channel, dict) else None
                creative = attributes.get('channel_creative') if isinstance(attributes, dict) else None

                # Requirement 5.5: channel_creative absent, None or non-dict
                # with at least one key.
                if not isinstance(creative, dict) or not creative:
                    logger.warning(
                        f"Unusable channel_creative for ad_channel "
                        f"{ad_channel.get('id') if isinstance(ad_channel, dict) else None}"
                    )
                    continue

                # Requirement 5.6: 'ads' absent, non-list or empty list.
                creative_ads = creative.get('ads')
                if not isinstance(creative_ads, list) or not creative_ads:
                    logger.warning(
                        f"Published creative without ads for ad_channel "
                        f"{ad_channel.get('id')}"
                    )
                    continue

                descriptors.append({'creative': creative, 'adchannel_id': ad_channel.get('id')})

        # Requirement 5.9: an empty creatives list is never returned.
        if not descriptors:
            logger.error(
                f"No usable published creatives for campaign_id: {campaign_id} "
                f"and brand_id: {brand_id}"
            )
            raise DataNotFoundException('Published creatives not found')

        return descriptors, channel_id

    def _get_campaign_setup(self, campaign_id: Any, channel_id: int) -> Dict[str, Any]:
        """Resolve the Campaign_Setup of the campaign for the resolved Channel_ID.

        Requirement 7.1: performs a single invocation of
        self.campaign_channel_publish_repository.get_by_campaign_id_and_channel_id
        with campaign_id and channel_id passed positionally, an invocation that
        is emitted ALSO when channel_id keeps its default value 0.

        Requirement 7.2: logs both values with logger.error and raises
        DataNotFoundException when the returned value is falsy or is not a dict
        instance. An absent 'attributes' node does not raise here: it surfaces
        as the IncorrectValidationException of _validate_published.
        """
        campaign_setup = self.campaign_channel_publish_repository.get_by_campaign_id_and_channel_id(
            campaign_id, channel_id
        )

        if not campaign_setup or not isinstance(campaign_setup, dict):
            logger.error(
                f"Campaign setup not found for campaign_id: {campaign_id} "
                f"and channel_id: {channel_id}"
            )
            raise DataNotFoundException('Campaign setup not found')

        return campaign_setup

    def _validate_published(self, campaign_setup: Dict[str, Any]) -> None:
        """Validate that the campaign was actually published on Meta.

        Requirement 7.4: compares meta_published against True BY IDENTITY, so
        that False, None, 1, 'True', 'true' and the absence of the attribute all
        log with logger.error and raise IncorrectValidationException, before any
        Entrada_de_Creativo is composed (Requirement 10.4).

        Requirement 7.7: the attribute is read through .get('attributes', {}),
        with 0 reads of meta_resources.
        """
        meta_published = campaign_setup.get('attributes', {}).get('meta_published')

        if meta_published is not True:
            logger.error('Campaign is not published on Meta')
            raise IncorrectValidationException('Campaign is not published')

    def _validate_campaign_mode(self, campaign_setup: Dict[str, Any]) -> str:
        """Validate the Modo_de_Campaña and return it as a string.

        Requirements 8.5, 10.5: reads meta_campaign_mode and returns its value
        when it belongs to _SUPPORTED_CAMPAIGN_MODES; in any other case logs the
        read value with logger.error and raises IncorrectValidationException.
        Invoked once, after _validate_published and before the composition loop,
        so an unsupported mode produces 0 composed entries.

        Decision D-6: returns the mode STRING and not a Callable, so that
        'Callable' is not needed in the typing import line.
        """
        campaign_mode = campaign_setup.get('attributes', {}).get('meta_campaign_mode')

        if campaign_mode not in self._SUPPORTED_CAMPAIGN_MODES:
            logger.error(f"Unsupported campaign mode: {campaign_mode}")
            raise IncorrectValidationException('Unsupported campaign mode')

        return campaign_mode

    def _build_dynamic_creative_published(self, idx: int, descriptor: Dict[str, Any]) -> Dict[str, Any]:
        """Compose an Entrada_de_Creativo in DYNAMIC mode.

        Requirement 8.3: counterpart of the DYNAMIC branch of
        FacebookLaunchCampaignUseCase._build_response(), with the same paths,
        the same default values and the same transformations, including the
        composition of 'images' as a list of dicts of keys 'url', 'valid' and
        'error', and of 'proposal_url' as the ',' join of the 'website_url'
        values of asset_feed_spec.link_urls.

        Requirement 8.1: returns the 31 keys in the order fixed there, the same
        set and the same order as the STANDARD branch. Requirement 8.6:
        'adchannel_id' is read from asset_feed_spec.ad_channel_id with default
        0, never from the 'adchannel_id' of the descriptor, which only exists
        for the log messages. Requirement 8.7: 0 keys for Meta identifiers.

        Requirement 8.8: an absent key or a key with value None falls back to
        the default the launch use case applies today for that key, without
        raising. Requirement 8.9: the *_valid, *_valid_amount, *_max_amount,
        unique_* and min_daily_budget values are delivered as the pre-check
        flow persisted them, with 0 invocations of MetaAdsValidator and
        MetaAdsPayloadBuilder.

        Decision D-4: 'adCreative' and 'asset_feed_spec' are normalized with
        `or {}`, a strict widening over the launch branch, which raises when
        either of them holds None.
        """
        creative = descriptor.get('creative') or {}
        creative_ads = creative.get('ads')
        ads_published = creative_ads[0] if isinstance(creative_ads, list) and creative_ads else {}
        if not isinstance(ads_published, dict):
            ads_published = {}

        ad_creative = ads_published.get('adCreative') or {}
        asset_feed_spec = ad_creative.get('asset_feed_spec') or {}

        def _spec(key, default):
            # Requirement 8.8: absent key or explicit None -> default.
            value = asset_feed_spec.get(key, default)
            return default if value is None else value

        images = [{
            'url': image.get('url'),
            'valid': image.get('valid'),
            'error': image.get('error'),
        } for image in _spec('images', [])]

        proposal_url = ','.join(
            [link_url.get('website_url') or '' for link_url in _spec('link_urls', [])]
        )

        # Requirement 8.1: the 31 keys, in this order.
        return {
            'idx': idx,
            'name': creative.get('name'),
            'adset_id': creative.get('id'),
            'ad_id': ads_published.get('id'),
            'adchannel_id': _spec('ad_channel_id', 0),
            'daily_budget': creative.get('daily_budget'),
            'images': images,
            'bodies': _spec('bodies', []),
            'titles': _spec('titles', []),
            'descriptions': _spec('descriptions', []),
            'call_to_action_types': _spec('call_to_action_types', []),
            'images_valid_amount': _spec('images_valid_amount', False),
            'titles_valid_amount': _spec('titles_valid_amount', False),
            'bodies_valid_amount': _spec('bodies_valid_amount', False),
            'descriptions_valid_amount': _spec('descriptions_valid_amount', False),
            'call_to_action_types_valid_amount': _spec('call_to_action_types_valid_amount', False),
            'images_max_amount': _spec('images_max_amount', 0),
            'titles_max_amount': _spec('titles_max_amount', 0),
            'bodies_max_amount': _spec('bodies_max_amount', 0),
            'descriptions_max_amount': _spec('descriptions_max_amount', 0),
            'call_to_action_types_max_amount': _spec('call_to_action_types_max_amount', 0),
            'unique_titles': _spec('unique_titles', False),
            'unique_bodies': _spec('unique_bodies', False),
            'unique_descriptions': _spec('unique_descriptions', False),
            'daily_budget_valid': _spec('daily_budget_valid', False),
            'min_daily_budget': _spec('min_daily_budget', 0),
            'proposal_url': proposal_url,
            # Name asymmetry already present in the launch flow: the value of
            # 'proposal_url_valid' is read from 'link_url_valid'.
            'proposal_url_valid': _spec('link_url_valid', False),
            'proposal_locations': creative.get('proposal_locations') or [],
            'locations': _spec('locations', []),
            'locations_valid': _spec('locations_valid', False),
        }

    def _build_standard_creative_published(self, idx: int, descriptor: Dict[str, Any]) -> Dict[str, Any]:
        """Compose an Entrada_de_Creativo in STANDARD mode.

        Requirement 8.4: counterpart of the already existing
        FacebookLaunchCampaignUseCase._build_standard_creative_published(), with
        the same paths, the same default values and the same transformations,
        including 'titles', 'bodies' and 'descriptions' as lists of at most one
        dict of keys 'text' and 'valid_length', the five *_max_amount keys fixed
        to the literal 1, and the reuse of 'title_valid', 'body_valid' and
        'description_valid' as 'unique_titles', 'unique_bodies' and
        'unique_descriptions'.

        Requirement 8.1: returns the same 31 keys, in the same order, as the
        DYNAMIC branch. Requirement 8.6: 'adchannel_id' is read from
        object_story_spec.ad_channel_id with default 0, never from the
        'adchannel_id' of the descriptor. Requirement 8.7: 0 keys for Meta
        identifiers. Requirements 8.8, 8.9: the same defaults as the launch use
        case for an absent or None key, and the persisted validation values
        delivered as they are, with 0 invocations of MetaAdsValidator and
        MetaAdsPayloadBuilder.
        """
        creative = descriptor.get('creative') or {}
        creative_ads = creative.get('ads')
        ads_published = creative_ads[0] if isinstance(creative_ads, list) and creative_ads else {}
        if not isinstance(ads_published, dict):
            ads_published = {}

        # Decision D-4: `or {}` normalizes both the absent key and the explicit
        # None value, on the four levels of the chain.
        ad_creative = ads_published.get('adCreative') or {}
        object_story_spec = ad_creative.get('object_story_spec') or {}
        link_data = object_story_spec.get('link_data') or {}
        call_to_action = link_data.get('call_to_action') or {}
        # Requirement 16.1: a truthy non-dict call_to_action is treated as {}.
        if not isinstance(call_to_action, dict):
            call_to_action = {}
        call_to_action_type = call_to_action.get('type') or {}
        # Requirement 16.2: a truthy non-dict call_to_action.type is treated as {}.
        if not isinstance(call_to_action_type, dict):
            call_to_action_type = {}

        def _spec(key, default):
            # Requirement 8.8: absent key or explicit None -> default.
            value = object_story_spec.get(key, default)
            return default if value is None else value

        def _link(key, default):
            # Requirement 8.8: absent key or explicit None -> default.
            value = link_data.get(key, default)
            return default if value is None else value

        def _as_single_item_list(value, valid_length):
            return [{'text': value, 'valid_length': valid_length}] if value else []

        image_url = link_data.get('image_url')
        image_valid = _link('image_valid', False)
        images = [{
            'url': image_url,
            'valid': image_valid,
            'error': link_data.get('image_error'),
        }] if image_url else []

        title_valid = _link('title_valid', False)
        body_valid = _link('body_valid', False)
        description_valid = _link('description_valid', False)

        call_to_action_type_valid = call_to_action_type.get('valid', False)
        if call_to_action_type_valid is None:
            call_to_action_type_valid = False

        # Requirement 8.1: the same 31 keys, in the same order, as the DYNAMIC branch.
        return {
            'idx': idx,
            'name': creative.get('name'),
            'adset_id': creative.get('id'),
            'ad_id': ads_published.get('id'),
            'adchannel_id': _spec('ad_channel_id', 0),
            'daily_budget': creative.get('daily_budget'),
            'images': images,
            'bodies': _as_single_item_list(link_data.get('message'), body_valid),
            'titles': _as_single_item_list(link_data.get('name'), title_valid),
            'descriptions': _as_single_item_list(link_data.get('description'), description_valid),
            'call_to_action_types': [call_to_action_type] if call_to_action else [],
            'images_valid_amount': image_valid,
            'titles_valid_amount': title_valid,
            'bodies_valid_amount': body_valid,
            'descriptions_valid_amount': description_valid,
            'call_to_action_types_valid_amount': call_to_action_type_valid if call_to_action else False,
            'images_max_amount': 1,
            'titles_max_amount': 1,
            'bodies_max_amount': 1,
            'descriptions_max_amount': 1,
            'call_to_action_types_max_amount': 1,
            'unique_titles': title_valid,
            'unique_bodies': body_valid,
            'unique_descriptions': description_valid,
            'daily_budget_valid': _spec('daily_budget_valid', False),
            'min_daily_budget': _spec('min_daily_budget', 0),
            'proposal_url': link_data.get('link') or '',
            'proposal_url_valid': _link('link_url_valid', False),
            'proposal_locations': creative.get('proposal_locations') or [],
            'locations': _spec('locations', []),
            'locations_valid': _spec('locations_valid', False),
        }

    def _build_creatives(
        self, descriptors: List[Dict[str, Any]], campaign_mode: str,
    ) -> List[Dict[str, Any]]:
        """Compose the creatives list of the Resultado_de_Consulta.

        Requirement 8.2: dispatches on the already validated Modo_de_Campaña —
        and NOT on the presence of asset_feed_spec or object_story_spec in the
        Published_Creative— with an if/else of two branches, safe because
        _validate_campaign_mode already rejected any other value (decision D-6).

        Requirement 7.5: assigns to 'idx' the zero based index of each entry
        within the final list, which preserves the order of appearance of the
        ad-sets and, inside each of them, of the ads.
        """
        creatives: List[Dict[str, Any]] = []

        for idx, descriptor in enumerate(descriptors):
            if campaign_mode == CreativeType.STANDARD.value:
                creatives.append(self._build_standard_creative_published(idx, descriptor))
            else:
                creatives.append(self._build_dynamic_creative_published(idx, descriptor))

        return creatives

    def _build_result(
        self,
        campaign: Dict[str, Any],
        campaign_setup: Dict[str, Any],
        creatives: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compose the Resultado_de_Consulta of exactly three keys.

        Requirement 7.3: the 'campaign' block has exactly the six keys 'name',
        'channel_name', 'creatives_no', 'objective', 'optimization_goal' and
        'mode', in that order, with 'channel_name' taken from the _CHANNEL_NAME
        class constant ('Meta'), 'creatives_no' equal to len(creatives) and the
        three remaining ones read from the Campaign_Setup.

        Requirement 4.5: of the Campaña_Objetivo only attributes.name is read.

        Requirement 7.6: 'meta_url' interpolates _META_CAMPAIGN_URL_TEMPLATE
        with meta_account_id and meta_campaign_id, both read from the already
        persisted Campaign_Setup record and not from freshly created values.

        Requirement 7.7: 0 reads of meta_resources and 0 keys holding a URL of
        the form '.../adsmanager/manager/adsets/edit?...', which stays out of
        scope.

        Requirements 7.8, 7.9: exactly the three keys 'campaign', 'creatives'
        and 'meta_url', without debug, pagination nor status keys, returned as
        the single return value, neither wrapped in a tuple nor accompanied by
        an HTTP status code.
        """
        setup_attributes = campaign_setup.get('attributes', {})

        return {
            'campaign': {
                'name': campaign.get('attributes', {}).get('name'),
                'channel_name': self._CHANNEL_NAME,
                'creatives_no': len(creatives),
                'objective': setup_attributes.get('meta_campaign_objective'),
                'optimization_goal': setup_attributes.get('meta_optimization_goal'),
                'mode': setup_attributes.get('meta_campaign_mode'),
                'conversion_event': setup_attributes.get('meta_conversion_event'),
            },
            'creatives': creatives,
            'meta_url': self._META_CAMPAIGN_URL_TEMPLATE.format(
                meta_account_id=setup_attributes.get('meta_account_id'),
                meta_campaign_id=setup_attributes.get('meta_campaign_id'),
            ),
        }

    def execute(self, brand_id: int, campaign_id: int) -> Dict[str, Any]:
        """Return the already published creatives of a Meta Ads campaign.

        Requirement 2.5: exactly two positional parameters, in this order.
        Requirement 10.1: the textual order of the eight statements IS the
        sequence guarantee of the normative chain Cuenta_Padre ->
        Campaña_Objetivo -> Ad_Sets_Seleccionados (which yields the Channel_ID)
        -> Campaign_Setup -> publication state -> Modo_de_Campaña ->
        composition, where each stage consumes only values already resolved by
        the previous ones.

        Requirement 10.7: no try/except wraps the chain, so the six exceptions
        of the validations propagate to the caller. Requirement 10.6: 4 read
        queries to Strapi per successful invocation and 0 writes.

        Requirement 7.9: returns the Resultado_de_Consulta as the single return
        value, neither wrapped in a tuple nor accompanied by an HTTP status
        code.
        """
        # Stage 1 - Requirement 3.1: first operation of the body.
        parent_account = self._get_parent_account()

        # Stage 2 - Requirement 4.1. brand_id and campaign_id are passed as
        # they were received, without type conversion nor normalization
        # (Requirement 2.6).
        campaign = self._get_campaign(campaign_id, brand_id, parent_account)

        # Stage 3 - Requirements 5.1, 5.9, 6.1: one query to ad-sets, the
        # read-only walk and the Channel_ID of the first selected ad-channel.
        descriptors, channel_id = self._collect_published_creatives(campaign_id, brand_id)

        # Stage 4 - Requirement 7.1: emitted also with channel_id == 0.
        campaign_setup = self._get_campaign_setup(campaign_id, channel_id)

        # Stage 5 - Requirement 7.4, before composing any entry.
        self._validate_published(campaign_setup)

        # Stage 6 - Requirements 8.5, 10.5: a single validation of the mode,
        # after stage 5 and before the composition loop.
        campaign_mode = self._validate_campaign_mode(campaign_setup)

        # Stage 7 - in memory composition, 0 additional queries.
        creatives = self._build_creatives(descriptors, campaign_mode)

        return self._build_result(campaign, campaign_setup, creatives)