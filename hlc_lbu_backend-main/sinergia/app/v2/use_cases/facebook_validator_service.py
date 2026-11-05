from dataclasses import dataclass, field, asdict
from enum import Enum
from io import BytesIO
from PIL import Image
from typing import List, Optional, Dict, Any, Set
import logging
import re

from pyparsing import Union
import requests
from app.tools.strapi import StrapiClient
from dataclasses import asdict

logger = logging.getLogger(__name__)

IMG_MAX_SIZE = 2560
IMG_MIN_SIZE = 335
MAX_SIZE_MB = 30

# MIN_ASPECT_RATIO = 0.8   # Equivalent to 4:5
MIN_ASPECT_RATIO = 0.5625   # Equivalent to 9:16
MAX_ASPECT_RATIO = 1.91  # Equivalent to 1.91:1
TOLERANCE = 0.01

GENDER_MAPPING = {
    'Male': [1],
    'Female': [2],
    'All': [1, 2]
}

TEXT_ASSET_MAX_LENGTH = {
    "titles": 255,
    "bodies": 1024,
    "descriptions": 255,
    "title": 255,
    "body": 1024,
    "description": 255
}

ASSET_MAX_AMOUNTS = {
    'images': 10,
    'titles': 5,
    'bodies': 5,
    'descriptions': 5,
    'call_to_action_types': 5
}

URL_PATTERN = '^https://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'

@dataclass
class Targeting:
    geo_locations: Optional[Dict[str, List[str]]] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    genders: Optional[List[int]] = None
    interests: Optional[List[Dict[str, str]]] = None

@dataclass
class AdImage:
    image_url: str

@dataclass
class LinkData:
    link: Optional[str] = None
    message: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    call_to_action: Optional[Dict[str, Any]] = None
    image_hash: Optional[str] = None
    image_url: Optional[str] = None

@dataclass
class ObjectStorySpec:
    page_id: str
    link_data: Optional[LinkData] = None
    ad_channel_id: Optional[int] = None

@dataclass
class AssetFeedSpec:
    images: List[Dict[str, str]] = field(default_factory=list)
    bodies: List[Dict[str, str]] = field(default_factory=list)
    titles: List[Dict[str, str]] = field(default_factory=list)
    descriptions: List[Dict[str, str]] = field(default_factory=list)
    call_to_action_types: List[Dict[str, str]] = field(default_factory=list)
    ad_formats: List[str] = field(default_factory=list)
    link_urls: List[Dict[str, str]] = field(default_factory=list)
    images_valid_amount: bool = False
    titles_valid_amount: bool = False
    bodies_valid_amount: bool = False
    descriptions_valid_amount: bool = False
    call_to_action_types_valid_amount: bool = False
    images_max_amount: int = ASSET_MAX_AMOUNTS.get('images')
    titles_max_amount: int = ASSET_MAX_AMOUNTS.get('titles')
    bodies_max_amount: int = ASSET_MAX_AMOUNTS.get('bodies')
    descriptions_max_amount: int = ASSET_MAX_AMOUNTS.get('descriptions')
    call_to_action_types_max_amount: int = ASSET_MAX_AMOUNTS.get('call_to_action_types')
    min_daily_budget: int = 0
    daily_budget_valid: bool = False
    link_url_valid: bool = False
    unique_titles: bool = False
    unique_bodies: bool = False
    unique_descriptions: bool = False
    ad_channel_id: int = None
    locations: List[Dict] = field(default_factory=list)
    locations_valid: bool = False

@dataclass
class CreativeAssetGroup:
    image_hash: str
    titles: List[Dict[str, str]]
    bodies: List[Dict[str, str]]
    descriptions: List[Dict[str, str]]
    call_to_action_type: str

@dataclass
class AdCreative:
    id: str
    name: str
    ad_account_id: str
    object_story_spec: ObjectStorySpec
    asset_feed_spec: Optional[AssetFeedSpec] = None
    creative_asset_groups: Optional[List[CreativeAssetGroup]] = None
    ad_image: Optional[AdImage] = None

@dataclass
class Ad:
    id: str
    name: str
    ad_account_id: str
    adset_id: str
    creative: Dict[str, str]
    status: str
    adCreative: Optional[AdCreative] = None

@dataclass
class AdSet:
    id: str
    name: str
    campaign_id: str
    ad_account_id: str
    daily_budget: str
    billing_event: str
    optimization_goal: str
    targeting: Targeting
    status: str
    ads: List[Ad] = field(default_factory=list)
    proposal_locations: List[str] = field(default_factory=list)
    locations: List[Dict] = field(default_factory=list)

@dataclass
class Campaign:
    id: str
    name: str
    ad_account_id: str
    objective: str
    status: str
    buying_type: str
    special_ad_categories: List[str]
    ad_sets: List[AdSet] = field(default_factory=list)

class CreativeType(Enum):
    STANDARD = "STANDARD"
    DYNAMIC = "DYNAMIC"

class CampaignObjective(Enum):
    AWARENESS = "OUTCOME_AWARENESS"
    TRAFFIC = "OUTCOME_TRAFFIC"
    SALES = "OUTCOME_SALES"
    LEADS = "OUTCOME_LEADS"


class SalesOptimizationGoal(Enum):
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"
    VALUE = "VALUE"
    CONVERSATIONS = "CONVERSATIONS"
    LINK_CLICKS = "LINK_CLICKS"
    LANDING_PAGE_VIEWS = "LANDING_PAGE_VIEWS"


class AwarenessOptimizationGoal(Enum):
    AD_RECALL_LIFT = "AD_RECALL_LIFT"
    REACH = "REACH"
    IMPRESSIONS = "IMPRESSIONS"
    THRUPLAY = "THRUPLAY"
    TWO_SECOND_CONTINUOUS_VIDEO_VIEWS = "TWO_SECOND_CONTINUOUS_VIDEO_VIEWS"


class LeadsOptimizationGoal(Enum):
    LEAD_GENERATION = "LEAD_GENERATION"
    QUALITY_LEAD = "QUALITY_LEAD"
    CONVERSATIONS = "CONVERSATIONS"
    OFFSITE_CONVERSIONS = "OFFSITE_CONVERSIONS"


OBJECTIVE_TO_GOALS = {
    CampaignObjective.SALES.value: {g.value for g in SalesOptimizationGoal},
    CampaignObjective.AWARENESS.value: {g.value for g in AwarenessOptimizationGoal},
    CampaignObjective.LEADS.value: {g.value for g in LeadsOptimizationGoal},
}

# CTA rules per sales optimization goal
SALES_GOAL_ALLOWED_CTAS = {
    SalesOptimizationGoal.OFFSITE_CONVERSIONS.value: {"SHOP_NOW", "GET_OFFER", "ORDER_NOW", "LEARN_MORE", "SIGN_UP", "SUBSCRIBE"},
    SalesOptimizationGoal.VALUE.value: {"SHOP_NOW", "ORDER_NOW", "LEARN_MORE"},
    SalesOptimizationGoal.CONVERSATIONS.value: {"WHATSAPP_MESSAGE", "SEND_MESSAGE"},
    SalesOptimizationGoal.LINK_CLICKS.value: {"SHOP_NOW", "LEARN_MORE", "GET_OFFER", "SIGN_UP", "DOWNLOAD"},
    SalesOptimizationGoal.LANDING_PAGE_VIEWS.value: {"SHOP_NOW", "LEARN_MORE", "GET_OFFER", "BOOK_TRAVEL", "SIGN_UP", "BUY_NOW", "APPLY_NOW"},
}

# CTA rules per awareness optimization goal
AWARENESS_GOAL_ALLOWED_CTAS = {
    AwarenessOptimizationGoal.AD_RECALL_LIFT.value: {"LEARN_MORE", "WATCH_MORE", "SIGN_UP", "BOOK_TRAVEL", "APPLY_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"},
    AwarenessOptimizationGoal.IMPRESSIONS.value: {"LEARN_MORE", "WATCH_MORE", "SIGN_UP", "BOOK_TRAVEL", "APPLY_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"},
    AwarenessOptimizationGoal.REACH.value: {"LEARN_MORE", "WATCH_MORE", "DOWNLOAD", "APPLY_NOW", "SIGN_UP"}, # "BOOK_TRAVEL", "CALL_NOW", "CONTACT_US", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"},
    AwarenessOptimizationGoal.THRUPLAY.value: {"LEARN_MORE", "WATCH_MORE", "SIGN_UP", "BOOK_TRAVEL", "APPLY_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"},
    AwarenessOptimizationGoal.TWO_SECOND_CONTINUOUS_VIDEO_VIEWS.value: {"LEARN_MORE", "WATCH_MORE", "SIGN_UP", "BOOK_TRAVEL", "APPLY_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"},
}

# CTA rules per leads optimization goal
LEADS_GOAL_ALLOWED_CTAS = {
    LeadsOptimizationGoal.LEAD_GENERATION.value: {"SIGN_UP", "APPLY_NOW", "DOWNLOAD", "GET_QUOTE", "LEARN_MORE", "SUBSCRIBE"},
    LeadsOptimizationGoal.QUALITY_LEAD.value: {"SIGN_UP", "APPLY_NOW", "BOOK_NOW", "DOWNLOAD", "GET_QUOTE", "LEARN_MORE"},
    LeadsOptimizationGoal.CONVERSATIONS.value: {"WHATSAPP_MESSAGE"}, # "MESSAGE_PAGE" - para hilos de Facebook Messenger
    # Leads captured on the advertiser's website (pixel + standard conversion event)
    LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value: {
        "LEARN_MORE", "SIGN_UP", "SUBSCRIBE", "ORDER_NOW", "SHOP_NOW", "APPLY_NOW",
        "BOOK_NOW", "CONTACT_US", "GET_OFFER", "GET_QUOTE", "DOWNLOAD", "SEE_MENU",
        "SEE_DETAILS", "GET_SHOWTIMES", "REQUEST_TIME", "BUY_TICKETS", "LISTEN_NOW",
        "PLAY_GAME", "WATCH_MORE", "NO_BUTTON",
    },
}

# Allowed conversion events for OUTCOME_LEADS + OFFSITE_CONVERSIONS
LEADS_ALLOWED_CONVERSION_EVENTS: Set[str] = {
    "COMPLETE_REGISTRATION", "LEAD", "CONTACT", "SUBMIT_APPLICATION",
    "SCHEDULE", "SUBSCRIBE", "START_TRIAL",
}

# Allowed custom events for OFFSITE_CONVERSIONS
SALES_ALLOWED_CUSTOM_EVENTS: Set[str] = {
    "PURCHASE", "INITIATE_CHECKOUT", "ADD_TO_CART", "ADD_TO_WISHLIST", "VIEW_CONTENT", "SUBSCRIBE", "START_TRIAL"
}

class MetaAdsValidator:
    VALID_CTA_VALUES = {
        "OPEN_LINK", "LIKE_PAGE", "SHOP_NOW", "PLAY_GAME", "INSTALL_APP", "USE_APP", "CALL",
        "CALL_ME", "VIDEO_CALL", "INSTALL_MOBILE_APP", "USE_MOBILE_APP", "MOBILE_DOWNLOAD",
        "BOOK_TRAVEL", "LISTEN_MUSIC", "WATCH_VIDEO", "LEARN_MORE", "SIGN_UP", "DOWNLOAD",
        "WATCH_MORE", "NO_BUTTON", "VISIT_PAGES_FEED", "CALL_NOW", "APPLY_NOW", "CONTACT",
        "BUY_NOW", "GET_OFFER", "GET_OFFER_VIEW", "BUY_TICKETS", "UPDATE_APP", "GET_DIRECTIONS",
        "BUY", "SEND_UPDATES", "MESSAGE_PAGE", "DONATE", "SUBSCRIBE", "SAY_THANKS", "SELL_NOW",
        "SHARE", "DONATE_NOW", "GET_QUOTE", "CONTACT_US", "ORDER_NOW", "START_ORDER", "ADD_TO_CART",
        "VIEW_CART", "VIEW_IN_CART", "VIDEO_ANNOTATION", "RECORD_NOW", "INQUIRE_NOW", "CONFIRM",
        "REFER_FRIENDS", "REQUEST_TIME", "GET_SHOWTIMES", "LISTEN_NOW", "TRY_DEMO", "WOODHENGE_SUPPORT",
        "SOTTO_SUBSCRIBE", "FOLLOW_USER", "RAISE_MONEY", "SEE_SHOP", "GET_DETAILS", "FIND_OUT_MORE",
        "VISIT_WEBSITE", "BROWSE_SHOP", "EVENT_RSVP", "WHATSAPP_MESSAGE", "FOLLOW_NEWS_STORYLINE",
        "SEE_MORE", "BOOK_NOW", "FIND_A_GROUP", "FIND_YOUR_GROUPS", "PAY_TO_ACCESS", "PURCHASE_GIFT_CARDS",
        "FOLLOW_PAGE", "SEND_A_GIFT", "SWIPE_UP_SHOP", "SWIPE_UP_PRODUCT", "SEND_GIFT_MONEY",
        "PLAY_GAME_ON_FACEBOOK", "GET_STARTED", "OPEN_INSTANT_APP", "AUDIO_CALL", "GET_PROMOTIONS",
        "JOIN_CHANNEL", "MAKE_AN_APPOINTMENT", "ASK_ABOUT_SERVICES", "BOOK_A_CONSULTATION", "GET_A_QUOTE",
        "BUY_VIA_MESSAGE", "ASK_FOR_MORE_INFO", "CHAT_WITH_US", "VIEW_PRODUCT", "VIEW_CHANNEL",
        "GET_IN_TOUCH", "ASK_A_QUESTION", "START_A_CHAT", "CHAT_NOW", "ASK_US", "WATCH_LIVE_VIDEO", 
        "SHOP_WITH_AI", "TRY_ON_WITH_AI", "SEE_MENU", "SEE_DETAILS"
    }

    META_ODAX_CTA_MAPPING = {
        "OUTCOME_AWARENESS": {
            "recommended_ctas": {"LEARN_MORE", "WATCH_MORE", "SIGN_UP", "BOOK_TRAVEL", "APPLY_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_SHOWTIMES", "LISTEN_NOW", "SUBSCRIBE", "WHATSAPP_MESSAGE"}
        },
        "OUTCOME_SALES": {
            "recommended_ctas": {"SHOP_NOW", "GET_OFFER", "SIGN_UP", "LEARN_MORE", "BUY_NOW", "BOOK_TRAVEL", "WHATSAPP_MESSAGE", "SEND_MESSAGE", "APPLY_NOW"}
        },
        "OUTCOME_TRAFFIC": {
            "recommended_ctas": {"APPLY_NOW", "BOOK_NOW", "CALL_NOW", "CONTACT_US", "DOWNLOAD", "GET_DIRECTIONS", "GET_QUOTE", "GET_SHOWTIMES", "LEARN_MORE", "LISTEN_NOW", "ORDER_NOW", "PLAY_GAME", "REQUEST_TIME", "SHOP_NOW", "SIGN_UP", "SUBSCRIBE", "WATCH_MORE"}
        },
        "OUTCOME_LEADS": {
            "recommended_ctas": {"SIGN_UP", "APPLY_NOW", "BOOK_NOW", "DOWNLOAD", "GET_OFFER", "GET_QUOTE", "LEARN_MORE", "SUBSCRIBE", "WHATSAPP_MESSAGE", "CONTACT_US", "SEND_MESSAGE"}
        }
    }

    def _normalize_cta(cta_text: str) -> str:
        if not cta_text: return ""
        return cta_text.strip().upper().replace(" ", "_")

    @classmethod
    def validate_optimization_goal_for_objective(cls, goal: str, objective: str, throw: bool = True) -> bool:
        if not objective or not goal:
            if throw:
                raise ValueError("Objective and optimization goal are required")
            return False

        allowed_goals = OBJECTIVE_TO_GOALS.get(objective, set())
        if goal not in allowed_goals:
            if throw:
                raise ValueError(f"Optimization goal '{goal}' is not valid for objective '{objective}'")
            return False

        return True

    @classmethod
    def get_allowed_ctas_for_goal(cls, objective: str, goal: str) -> Set[str]:
        if objective == CampaignObjective.SALES.value:
            return SALES_GOAL_ALLOWED_CTAS.get(goal, set())
        if objective == CampaignObjective.AWARENESS.value:
            return AWARENESS_GOAL_ALLOWED_CTAS.get(goal, set())
        if objective == CampaignObjective.LEADS.value:
            return LEADS_GOAL_ALLOWED_CTAS.get(goal, set())
        
        # default fallback: use META_ODAX_CTA_MAPPING by objective if available
        config = cls.META_ODAX_CTA_MAPPING.get(objective)
        if config:
            return set(config.get("recommended_ctas", []))
        return set()

    @classmethod
    def validate_cta_for_goal(cls, cta_text: str, objective: str, goal: str, throw: bool = True) -> bool:
        cta_normalized = cls._normalize_cta(cta_text)
        if not cta_normalized:
            if throw:
                raise ValueError("CTA is required but was empty")
            return False

        allowed = cls.get_allowed_ctas_for_goal(objective, goal)
        if cta_normalized not in allowed:
            if throw:
                raise ValueError(f"CTA '{cta_normalized}' not allowed for objective '{objective}' and goal '{goal}'")
            return False
        return True

    @classmethod
    def validate_promoted_object(cls, promoted_object: dict, objective: str, goal: str, pixel_id: Optional[str] = None, throw: bool = True) -> bool:
        # Only SALES has promoted_object rules for now
        if objective != CampaignObjective.SALES.value:
            return True

        # if goal == SalesOptimizationGoal.OFFSITE_CONVERSIONS.value:
        # allow callers to pass pixel_id separately; build promoted_object if missing
        if not promoted_object:
            if pixel_id:
                if isinstance(promoted_object, dict):
                    promoted_object.update({"pixel_id": pixel_id, "custom_event_type": "PURCHASE"})
                else:
                    # promoted_object is falsy and not a dict (e.g., None). Create a local dict.
                    promoted_object = {"pixel_id": pixel_id, "custom_event_type": "PURCHASE"}
            else:
                if throw:
                    raise ValueError("promoted_object is required for OFFSITE_CONVERSIONS")
                return False

        pid = promoted_object.get("pixel_id") or pixel_id
        cet = (promoted_object.get("custom_event_type") or "PURCHASE").upper()

        if not pid:
            if throw:
                raise ValueError("pixel_id is required inside promoted_object for OFFSITE_CONVERSIONS")
            return False

        if cet not in SALES_ALLOWED_CUSTOM_EVENTS:
            if throw:
                raise ValueError(f"custom_event_type '{cet}' is not allowed for OFFSITE_CONVERSIONS")
            return False

        # normalize back into object for callers
        promoted_object["pixel_id"] = pid
        promoted_object["custom_event_type"] = cet

        return True

    @classmethod
    def validate_cta(cls, cta_text: str, objective: str, throw: bool = True) -> bool:
        cta_normalized = cls._normalize_cta(cta_text)

        try:
            if cta_normalized not in cls.VALID_CTA_VALUES:
                raise ValueError(f"Invalid CTA value: {cta_normalized}")

            config = cls.META_ODAX_CTA_MAPPING.get(objective)

            if not config:
                raise ValueError(f"Unsupported campaign objective for CTA validation: {objective}")

            if not cta_normalized:
                raise ValueError("CTA is required but was empty")

            if cta_normalized not in config["recommended_ctas"]:
                raise ValueError(
                    f"CTA '{cta_normalized}' not allowed for objective '{objective}'"
                )
        except ValueError as e:
            if throw:
                raise e
            else:
                logger.warning(str(e))
                return False
        
        return True

    @staticmethod
    def validate_images_precheck(images: List[Dict[str, str]]):
        for image in images:
            valid = True
            error = None
            img_url = image.get('url')
            if not img_url: continue
            try:
                response = requests.get(img_url, timeout=10)
                response.raise_for_status()

                size = response.headers.get("Content-Length")
                if size and int(size) > MAX_SIZE_MB * 1024 * 1024:
                    valid = False
                    error = f"{size / 1024 / 1024} MB (INVALID)"
                    # raise ValueError(f"Image at {img_url} exceeds the maximum file size of {MAX_SIZE_MB} MB.")

                img = Image.open(BytesIO(response.content))
                width, height = img.size
                aspect_ratio = width / height

                if not (MIN_ASPECT_RATIO - TOLERANCE <= aspect_ratio <= MAX_ASPECT_RATIO + TOLERANCE):
                    valid = False
                    error = f"Aspect ratio {aspect_ratio:.2f}:1 (INVALID)"
                    #raise ValueError(
                    #    f"Image at {img_url} has invalid aspect ratio {aspect_ratio:.2f}:1. "
                    #    f"Allowed range is between 4:5 (0.8) and 1.91:1 (1.91)."
                    #)

                if width > IMG_MAX_SIZE or height > IMG_MAX_SIZE:
                    valid = False
                    error = f"{width}x{height} px (INVALID)"
                    # raise ValueError(f"Image at {img_url} exceeds maximum resolution of {IMG_MAX_SIZE}x{IMG_MAX_SIZE} pixels.")

                if width < IMG_MIN_SIZE or height < IMG_MIN_SIZE:
                    valid = False
                    error = f"{width}x{height} px (INVALID)"
                    # raise ValueError(f"Image at {img_url} is too small. Minimum required: {IMG_MIN_SIZE}x{IMG_MIN_SIZE} pixels.")

            except requests.exceptions.RequestException as e:
                valid = False
                error = f"Could not fetch image"
                # raise ValueError(f"Could not fetch image from {img_url}: {str(e)}")
            except Exception as e:
                valid = False
                error = f"Invalid image format"
                # raise ValueError(f"Invalid image format or data at {img_url}: {str(e)}")
            finally:
                image['valid'] = valid
                image['error'] = error

    @staticmethod
    def validate_images(images: Union[List[str], str]):
        if isinstance(images, str):
            image_list = [images]
        else:
            image_list = images

        for img_url in image_list:
            if not img_url: continue
            try:
                response = requests.get(img_url, timeout=10)
                response.raise_for_status()

                size = response.headers.get("Content-Length")
                if size and int(size) > MAX_SIZE_MB * 1024 * 1024:
                    raise ValueError(f"Image at {img_url} exceeds the maximum file size of {MAX_SIZE_MB} MB.")

                image = Image.open(BytesIO(response.content))
                width, height = image.size
                aspect_ratio = width / height

                if not (MIN_ASPECT_RATIO - TOLERANCE <= aspect_ratio <= MAX_ASPECT_RATIO + TOLERANCE):
                    raise ValueError(
                        f"Image at {img_url} has invalid aspect ratio {aspect_ratio:.2f}:1. "
                        f"Allowed range is between 4:5 (0.8) and 1.91:1 (1.91)."
                    )

                if width > IMG_MAX_SIZE or height > IMG_MAX_SIZE:
                    raise ValueError(f"Image at {img_url} exceeds maximum resolution of {IMG_MAX_SIZE}x{IMG_MAX_SIZE} pixels.")

                if width < IMG_MIN_SIZE or height < IMG_MIN_SIZE:
                    raise ValueError(f"Image at {img_url} is too small. Minimum required: {IMG_MIN_SIZE}x{IMG_MIN_SIZE} pixels.")

            except requests.exceptions.RequestException as e:
                raise ValueError(f"Could not fetch image from {img_url}: {str(e)}")
            except ValueError as ve:
                raise ve
            except Exception as e:
                raise ValueError(f"Invalid image format or data at {img_url}: {str(e)}")
            
    @staticmethod
    def is_unique_texts(texts: Union[List[str], str]):
        if isinstance(texts, str): texts = [texts]

        texts = [t for t in texts if t]

        if len(texts) != len(set(texts)):
            return False
        
        return True

    @staticmethod
    def is_valid_length(type: str, texts: List[Dict[str, str]]):
        max_length = TEXT_ASSET_MAX_LENGTH.get(type, 255)

        for text in texts:
            valid = True
            length = len(text.get('text', ''))
            if length == 0 or length > max_length:
                valid = False
                # raise ValueError(f"{type.capitalize()} '{text}' exceeds maximum length of {max_length} characters.")

            text['valid_length'] = valid

    @staticmethod
    def validate_text(type: str, texts: Union[List[str], str]):
        if isinstance(texts, str): texts = [texts]

        texts = [t for t in texts if t]

        if len(texts) != len(set(texts)):
            raise ValueError("Text entries must be unique.")

        max_length = TEXT_ASSET_MAX_LENGTH.get(type, 255)

        for text in texts:
            if len(text) > max_length:
                raise ValueError(f"{type.capitalize()} '{text}' exceeds maximum length of {max_length} characters.")

    @staticmethod
    def is_valid_amount(asset_feed: dict, creative_type: str, story_spec: dict = None):
        for key, max_amount in ASSET_MAX_AMOUNTS.items():
            items = asset_feed.get(key, [])
            valid = True
            if len(items) > max_amount:
                valid = False
            asset_feed[f"{key}_valid_amount"] = valid

    @staticmethod
    def is_valid_images_amount(images: List):
        size = len(images)
        if size == 0 or size > ASSET_MAX_AMOUNTS.get('images'):
            return False
        return True
    
    @staticmethod
    def is_valid_texts_amount(type: str, texts: List[Dict[str, str]]):
        size = len(texts)
        max_amount = ASSET_MAX_AMOUNTS.get(type)
        if size == 0 or size > max_amount:
            return False
        return True
    
    @staticmethod
    def is_valid_ctas_amount(ctas: List):
        size = len(ctas)
        if size == 0 or size > ASSET_MAX_AMOUNTS.get('call_to_action_types'):
            return False
        return True

    @staticmethod
    def validate_assets_amount(asset_feed: dict, creative_type: str, story_spec: dict = None):
        if creative_type == "DYNAMIC":
            if not asset_feed:
                raise ValueError("Asset feed is missing or empty for DYNAMIC creative.")

            images = asset_feed.get('images', [])
            titles = asset_feed.get('titles', [])
            bodies = asset_feed.get('bodies', [])
            descriptions = asset_feed.get('descriptions', [])

            if len(images) > ASSET_MAX_AMOUNTS.get('images'):
                raise ValueError(f"Maximum 10 images are required for DYNAMIC creative type. Found: {len(images)}")
            if len(titles) > ASSET_MAX_AMOUNTS.get('titles'):
                raise ValueError(f"Maximum 5 titles are required for DYNAMIC creative type. Found: {len(titles)}")
            if len(bodies) > ASSET_MAX_AMOUNTS.get('bodies'):
                raise ValueError(f"Maximum 5 bodies are required for DYNAMIC creative type. Found: {len(bodies)}")
            if len(descriptions) > ASSET_MAX_AMOUNTS.get('descriptions'):
                raise ValueError(f"Maximum 5 descriptions are required for DYNAMIC creative type. Found: {len(descriptions)}")

        elif creative_type == "STANDARD":
            if not story_spec:
                 raise ValueError("Object Story Spec is missing for STANDARD creative.")

            link_data = story_spec.get('link_data')
            if not link_data:
                raise ValueError("Link Data is missing inside Object Story Spec for STANDARD creative.")

            if not link_data.get('image_url') and not link_data.get('image_hash'):
                raise ValueError("An image URL or Image Hash is required for STANDARD creative type.")

            if not link_data.get('name'):
                raise ValueError("A title (name) is required for STANDARD creative type.")

            if not link_data.get('message'):
                raise ValueError("A body (message) is required for STANDARD creative type.")

    @staticmethod
    def is_valid_proposal_url(url: str):
        url_pattern = re.compile(rf"{URL_PATTERN}")
        if not url_pattern.match(url):
            return False
        
        return True

    @staticmethod
    def is_valid_link_url(url: str):
        urls = url.split(',')
        if len(urls) != 1:
            return False

        url_pattern = re.compile(rf"{URL_PATTERN}")
        if not url_pattern.match(url):
            return False
        
        return True
        


class MetaAdsPayloadBuilder:
    def __init__(self, campaign_id: str, campaign_objective: str = None, optimization_goal: str = None, creative_type: str = None):
        self.strapi_service = StrapiClient()
        self.campaign_id = campaign_id
        self.creative_type = creative_type
        self.campaign = Campaign(
            id="",
            name="",
            ad_account_id="",
            objective=campaign_objective,
            status="PAUSED",
            buying_type="AUCTION",
            special_ad_categories=[],
            ad_sets=[]
        )
        self.selected_page_id = ""
        self.campaign_object = None
        self.adset_objects = None
        self.funnel_flow_objects = None
        self.payload = None
        self.daily_budget = 0
        self.billing_event = 'IMPRESSIONS'
        self.optimization_goal = optimization_goal
        self.status = "PAUSED"
        self.buying_type = "AUCTION"
        self.ad_account_id = ""
        self.channel_id = 0

    def get_channel_id(self):
        return self.channel_id

    def select_ad_account(self, ad_account_id: str):
        self.ad_account_id = ad_account_id
        if self.campaign:
            self.campaign.ad_account_id = ad_account_id

    def select_page(self, page_id: str):
        self.selected_page_id = page_id

    def set_daily_budget(self, daily_budget: str):
        self.daily_budget = daily_budget

    def get_ad_account_id(self):
        return self.ad_account_id
    
    def get_billing_event(self):
        return self.billing_event

    def _get_campaign(self):
        campaign_data = self.strapi_service.get_campaign(self.campaign_id)
        if not campaign_data:
            raise Exception(f"Campaign not found: {self.campaign_id}")
        return campaign_data['data'][0]

    def _get_preferred_audience(self, adset_id: str):
        audience_data = self.strapi_service.get_audience_by_adset(adset_id)
        preferred_audience = audience_data.get('attributes', {}).get('preferred_audience', None)
        if not preferred_audience:
            raise Exception(f"Preferred audience not found: {self.campaign_id}")
        return preferred_audience

    def _get_funnel_flows(self):
        funnel_flows = self.strapi_service.find_by_filters("funnel-flows", filters={"campaign_ref": self.campaign_id})
        return funnel_flows

    def _get_objects(self):
        self.campaign_object = self._get_campaign()
        self.funnel_flow_objects = self._get_funnel_flows()

        funnel_flow_ids = [f['id'] for f in self.funnel_flow_objects.get('data', [])]

        if funnel_flow_ids:
            self.adset_objects = self._get_ad_sets(funnel_flow_ids)
        else:
            self.adset_objects = []

    def build_targeting(self, adset):
        audience = self._get_preferred_audience(adset['id'])
        targeting = Targeting()
        gender = audience.get('gender')
        ages_intervals = audience.get('age')
        ages = []
        for age_interval in ages_intervals:
            age_interval_list = age_interval.split('-')
            age_interval_list = [int(age) for age in age_interval_list]
            ages.extend(age_interval_list)
        targeting.genders = GENDER_MAPPING[gender]
        targeting.age_min = min(ages)
        targeting.age_max = max(ages)
        targeting.geo_locations = {
            #"country_groups": ["south_america"]
        }
        return targeting
    
    def build_proposal_locations(self, adset_id):
        audience = self._get_preferred_audience(adset_id)
        return audience.get('location', [])

    def build_asset_feed_spec(self, ad) -> Optional[AssetFeedSpec]:
        ad_channels_data = ad['attributes'].get('ad_channels', {}).get('data', [])
        if not ad_channels_data:
            return None

        channel = next((ch for ch in ad_channels_data if ch['attributes'].get("selected")), None)
        if not channel:
            return None
        
        channel_attrs = channel['attributes'].get('channel_attributes', [])

        self.channel_id = channel.get('attributes', {}).get('channel_ref', {}).get('data', {}).get('id', 0)

        asset_feed_spec = AssetFeedSpec()
        asset_feed_spec.ad_channel_id = channel.get('id')
        asset_feed_spec.ad_formats = ["SINGLE_IMAGE"]

        # if self.campaign.objective == CampaignObjective.LEADS.value and self.optimization_goal == LeadsOptimizationGoal.QUALITY_LEAD.value:
        #     asset_feed_spec.link_urls = [{"lead_generation_form_id": ""}]

        # else:
        #     channel_url = ad['attributes'].get('redirect_url')
        #     if channel_url:
        #         asset_feed_spec.link_urls = [{"website_url": channel_url}]

        channel_url = ad['attributes'].get('redirect_url')
        if channel_url:
            asset_feed_spec.link_urls = [{"website_url": channel_url}]

        for attribute in channel_attrs:
            attr_name = attribute.get('name')
            payloads = attribute.get('payloads', [])

            if attr_name == "primary_text":
                asset_feed_spec.bodies = [{"text": p['payload'], "valid_length": False} for p in payloads]

            elif attr_name == "headline":
                asset_feed_spec.titles = [{"text": p['payload'], "valid_length": False} for p in payloads]

            elif attr_name == "description":
                asset_feed_spec.descriptions = [{"text": p['payload'], "valid_length": False} for p in payloads]

            elif attr_name == "cta":
                asset_feed_spec.call_to_action_types = [{"value": self._normalize_cta(p["payload"]), "valid": False} for p in payloads]

        # Validate CTAs against objective and optimization_goal (if present) and set 'valid' flag
        try:
            objective = self.campaign.objective
        except Exception:
            objective = None

        for cta in asset_feed_spec.call_to_action_types:
            cval = cta.get('value')
            try:
                if self.optimization_goal:
                    valid = MetaAdsValidator.validate_cta_for_goal(cval, objective, self.optimization_goal, throw=False)
                else:
                    valid = MetaAdsValidator.validate_cta(cval, objective, throw=False)
            except Exception:
                valid = False
            cta['valid'] = bool(valid)

        media_formats = channel['attributes'].get('media_formats')
        if media_formats:
            formats_list = []
            if isinstance(media_formats, dict):
                 formats_list = media_formats.get('formats', [])
            elif isinstance(media_formats, list):
                 formats_list = media_formats

            if isinstance(formats_list, list):
                for fmt in formats_list:
                    if isinstance(fmt, dict):
                        visual_url = fmt.get('visual_url')
                        pinned = fmt.get('pinned', False)
                        if visual_url:
                            asset_feed_spec.images.append({"hash": None, "url": visual_url, "pinned": str(pinned)})

        if not asset_feed_spec.images:
            media = channel['attributes'].get('media', {}).get('data')
            if media:
                formats = media['attributes'].get('formats', {})
                image_url = None
                if 'large' in formats and formats['large'].get('url'):
                    image_url = formats['large']['url']
                elif 'medium' in formats and formats['medium'].get('url'):
                    image_url = formats['medium']['url']
                elif media['attributes'].get('url'):
                    image_url = media['attributes']['url']

                if image_url:
                    asset_feed_spec.images.append({"hash": None, "url": image_url})

        return asset_feed_spec

    def build_creative(self, ad):
        creative = AdCreative(
            id=None,
            name=ad['attributes']['name'],
            ad_account_id=self.get_ad_account_id(),
            object_story_spec=None,
            asset_feed_spec=None
        )

        asset_feed_spec = self.build_asset_feed_spec(ad)

        if self.creative_type == CreativeType.DYNAMIC.value:
            creative.asset_feed_spec = asset_feed_spec
            creative.object_story_spec = ObjectStorySpec(
                page_id=self.selected_page_id
            )

        elif self.creative_type == CreativeType.STANDARD.value:
            link_data = LinkData()

            if asset_feed_spec:
                if asset_feed_spec.bodies:
                    link_data.message = asset_feed_spec.bodies[0].get("text")
                if asset_feed_spec.titles:
                    link_data.name = asset_feed_spec.titles[0].get("text")
                if asset_feed_spec.descriptions:
                    link_data.description = asset_feed_spec.descriptions[0].get("text")
                if asset_feed_spec.images:
                    # buscar en la lista asset_feed_spec.images el item que tenga pinned == 'True'
                    image_pinned = next((img for img in asset_feed_spec.images if img.get("pinned").lower() == 'true'), None)
                    if image_pinned:
                        link_data.image_url = image_pinned.get("url")
                    # link_data.image_url = asset_feed_spec.images[0].get("url")
                if asset_feed_spec.call_to_action_types:
                    link_data.call_to_action = {
                        "type": asset_feed_spec.call_to_action_types[0]
                    }
                if asset_feed_spec.link_urls:
                    channel_url = asset_feed_spec.link_urls[0].get("website_url")
                    if channel_url:
                        link_data.link = channel_url
                        if link_data.call_to_action:
                            link_data.call_to_action["value"] = {"link": channel_url}

            logger.info(f"DEBUG: asset_feed_spec present? {bool(asset_feed_spec)}")
            logger.info(f"DEBUG: LinkData built: {link_data}")
            creative.object_story_spec = ObjectStorySpec(
                page_id=self.selected_page_id,
                link_data=link_data,
                ad_channel_id=asset_feed_spec.ad_channel_id if asset_feed_spec else None,
            )

        return creative


    def build_ads(self, adset):
        ads = []
        index = 0
        for ad in adset['attributes']['ads']['data']:
            ads.append(Ad(
                id=ad['id'],
                name=ad['attributes']['name'],
                ad_account_id="",
                adset_id="",
                creative={"creative_id": ""},
                status=self.status,
                adCreative=self.build_creative(ad),
            ))
            index += 1

        return ads

    def build_adset_payload(self):
        adsets = []

        if not self.adset_objects:
            print("No adsets found")
            return adsets

        if self.creative_type == CreativeType.STANDARD.value:
            for adset_data in self.adset_objects['data']:
                proposal_locations = self.build_proposal_locations(adset_data.get('id', 0))
                ads = self.build_ads(adset_data)
                adset = AdSet(
                    id=adset_data['id'],
                    name=adset_data['attributes']['name'],
                    daily_budget=self.daily_budget,
                    billing_event=self.billing_event,
                    optimization_goal=self.optimization_goal,
                    targeting=self.build_targeting(adset_data),
                    status=self.status,
                    ad_account_id=self.get_ad_account_id(),
                    campaign_id=None,
                    ads=ads,
                    proposal_locations=proposal_locations,
                    locations=[]
                )
                adsets.append(adset)

        elif self.creative_type == CreativeType.DYNAMIC.value:
            for adset_data in self.adset_objects['data']:

                base_targeting = self.build_targeting(adset_data)
                base_adset_name = adset_data['attributes']['name']
                ads_list = adset_data['attributes']['ads']['data']
                proposal_locations = self.build_proposal_locations(adset_data.get('id', 0))

                for ad_data in ads_list:
                    single_ad = Ad(
                        id=ad_data['id'],
                        name=ad_data['attributes']['name'],
                        ad_account_id="",
                        adset_id="",
                        creative={"creative_id": ""},
                        status=self.status,
                        adCreative=self.build_creative(ad_data),
                    )

                    new_adset = AdSet(
                        id=adset_data['id'],
                        name=f"{base_adset_name} - {single_ad.name}",
                        daily_budget=self.daily_budget,
                        billing_event=self.billing_event,
                        optimization_goal=self.optimization_goal,
                        targeting=base_targeting,
                        status=self.status,
                        ad_account_id=self.get_ad_account_id(),
                        campaign_id=None,
                        ads=[single_ad],
                        proposal_locations=proposal_locations,
                        locations=[]
                    )

                    adsets.append(new_adset)

        return adsets


    def _get_ad_sets(self, funnel_flow_ids: List[int]):
        params = {}
        for i, fid in enumerate(funnel_flow_ids):
            params[f"filters[funnel_flow_ref][id][$in][{i}]"] = fid

        populate = ["ads", "ads.ad_channels.channel_ref"]
        params["populate"] = ",".join(populate)

        return self.strapi_service.get("ad-sets", params=params)

    def _normalize_cta(self, cta_text: str) -> str:
        return cta_text.strip().upper().replace(" ", "_")

    def build_meta_payload(self):
        self._get_objects()

        self.payload = {
            "connection": "meta-ads",
            "campaign": {
                "name": self.campaign_object['attributes']['name'],
                "objective": self.campaign.objective,
                "status": self.status,
                "buying_type": self.buying_type,
                "special_ad_categories": [],
                "ad_sets": self.adset_objects,
                "ad_account_id": self.campaign_object['attributes'].get('ad_account_id'),
            },
            "selectedPageId": self.selected_page_id
        }

        self.payload["campaign"]["ad_sets"] = [asdict(adset) for adset in self.build_adset_payload()]
        self.campaign = self.payload['campaign']

        return self.payload

class MetaPayloadMapper:
    @property
    def meta_payload(self) -> Dict[str, Any]:
        return {
            "connection": "google-ads",
            "campaign": {
                "name": self.campaign_object.name,
                "objective": self.campaign.objective,
                "status": self.campaign.status,
                "buying_type": self.campaign.buying_type,
                "special_ad_categories": self.campaign.special_ad_categories,
                "ad_account_id": self.campaign.ad_account_id,
            },
            "adsets": [
                {
                    "name": ad_set.name,
                    "daily_budget": ad_set.daily_budget,
                    "billing_event": ad_set.billing_event,
                    "optimization_goal": ad_set.optimization_goal,
                    "targeting": self._targeting_to_dict(ad_set.targeting),
                    "status": ad_set.status,
                    "ad_account_id": ad_set.ad_account_id,
                    "campaign_id": ad_set.campaign_id,
                    "ads": [
                        {
                            "name": ad.name,
                            "ad_account_id": ad.ad_account_id,
                            "adCreative": self._ad_creative_to_dict(ad.adCreative),
                            "asset_feed_spec": None,
                            "status": ad.status,
                        }
                        for ad in ad_set.ads
                    ],
                }
                for ad_set in self.campaign.adSets
            ],
        }

    def _targeting_to_dict(self, targeting: Targeting) -> Dict[str, Any]:
        return {
            "geo_locations": targeting.geo_locations,
            "age_min": targeting.age_min,
            "age_max": targeting.age_max,
            "genders": targeting.genders,
            "interests": targeting.interests
        }

    def _ad_creative_to_dict(self, creative: Optional[AdCreative]) -> Optional[Dict[str, Any]]:
        if not creative:
            return None
        return {
            "id": creative.id,
            "name": creative.name,
            "ad_account_id": creative.ad_account_id,
            "object_story_spec": {"page_id": creative.object_story_spec.page_id} if creative.object_story_spec else None,
            "asset_feed_spec": self._asset_feed_spec_to_dict(creative.asset_feed_spec),
            "creative_asset_groups": [self._creative_asset_group_to_dict(g) for g in creative.creative_asset_groups] if creative.creative_asset_groups else None,
            "ad_image": {"image_url": creative.ad_image.image_url} if creative.ad_image else None
        }

    def _asset_feed_spec_to_dict(self, spec: Optional[AssetFeedSpec]) -> Optional[Dict[str, Any]]:
        if not spec:
            return None
        return {
            "images": spec.images,
            "bodies": spec.bodies,
            "titles": spec.titles,
            "descriptions": spec.descriptions,
            "call_to_action_types": spec.call_to_action_types,
            "ad_formats": spec.ad_formats
        }

    def _creative_asset_group_to_dict(self, group: CreativeAssetGroup) -> Dict[str, Any]:
         return {
            "image_hash": group.image_hash,
            "titles": group.titles,
            "bodies": group.bodies,
            "descriptions": group.descriptions,
            "call_to_action_type": group.call_to_action_type
         }

    def set_campaign(self, data: Dict[str, Any]):
        if 'id' in data: self.campaign.id = data['id']
        if 'name' in data: self.campaign.name = data['name']
        if 'ad_account_id' in data: self.campaign.ad_account_id = data['ad_account_id']
        if 'objective' in data: self.campaign.objective = data['objective']
        if 'status' in data: self.campaign.status = data['status']
        if 'buying_type' in data: self.campaign.buying_type = data['buying_type']
        if 'special_ad_categories' in data: self.campaign.special_ad_categories = data['special_ad_categories']
        if 'adSets' in data: self.campaign.adSets = data['adSets']

    def set_campaign_objective(self, objective: str):
        self.campaign.objective = objective

    def set_optimization_goal(self, ad_set_index: int, goal: str):
        if 0 <= ad_set_index < len(self.campaign.adSets):
             self.campaign.adSets[ad_set_index].optimization_goal = goal

    def set_ad_account_id(self, ad_account_id: str):
        self.campaign.ad_account_id = ad_account_id
        for ad_set in self.campaign.adSets:
            ad_set.ad_account_id = ad_account_id
            for ad in ad_set.ads:
                ad.ad_account_id = ad_account_id
                if ad.adCreative:
                    ad.adCreative.ad_account_id = ad_account_id

    def set_page_id(self, page_id: str):
        self.selected_page_id = page_id
        for ad_set in self.campaign.adSets:
            for ad in ad_set.ads:
                if ad.adCreative and ad.adCreative.object_story_spec:
                    ad.adCreative.object_story_spec.page_id = page_id

    def set_ad_sets(self, ad_sets: List[AdSet]):
        self.campaign.adSets = ad_sets

    def update_ad_set(self, ad_set_index: int, data: Dict[str, Any]):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            ad_set = self.campaign.adSets[ad_set_index]
            for key, value in data.items():
                if hasattr(ad_set, key):
                    setattr(ad_set, key, value)

    def add_ad(self, ad_set_index: int, data: Dict[str, Any]):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            ad_set = self.campaign.adSets[ad_set_index]
            new_ad = Ad(
                id="",
                name=data.get("name", ""),
                ad_account_id=self.campaign.ad_account_id,
                adset_id=ad_set.id,
                creative={"creative_id": ""},
                adCreative=data.get("adCreative") or AdCreative(
                    id="",
                    name="",
                    ad_account_id=self.campaign.ad_account_id,
                    object_story_spec=ObjectStorySpec(page_id=self.selected_page_id),
                    ad_image=None,
                    asset_feed_spec=None,
                    creative_asset_groups=[]
                ),
                status=data.get("status", "PAUSED")
            )
            ad_set.ads.append(new_ad)

    def set_ad_image(self, ad_set_index: int, ad_index: int, image: Dict[str, str]):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            ad_set = self.campaign.adSets[ad_set_index]
            if 0 <= ad_index < len(ad_set.ads):
                ad = ad_set.ads[ad_index]
                if ad.adCreative:
                     if not ad.adCreative.asset_feed_spec:
                         ad.adCreative.asset_feed_spec = AssetFeedSpec()

                     if "url" in image:
                         ad.adCreative.asset_feed_spec.images.append({"url": image["url"]})

    def set_targeting(self, ad_set_index: int, targeting: Targeting):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            self.campaign.adSets[ad_set_index].targeting = targeting

    def set_campaign_name(self, name: str):
        self.campaign.name = name

    def set_asset_feed_spec(self, ad_set_index: int, ad_index: int, asset_feed_spec: AssetFeedSpec):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            ad_set = self.campaign.adSets[ad_set_index]
            if 0 <= ad_index < len(ad_set.ads):
                ad = ad_set.ads[ad_index]
                if ad.adCreative:
                    ad.adCreative.asset_feed_spec = asset_feed_spec

    def set_creative_asset_groups_spec(self, ad_set_index: int, ad_index: int, creative_asset_groups_spec: List[CreativeAssetGroup]):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            ad_set = self.campaign.adSets[ad_set_index]
            if 0 <= ad_index < len(ad_set.ads):
                ad = ad_set.ads[ad_index]
                if ad.adCreative:
                    ad.adCreative.creative_asset_groups = creative_asset_groups_spec

    def set_daily_budget(self, ad_set_index: int, daily_budget: str):
        if 0 <= ad_set_index < len(self.campaign.adSets):
            self.campaign.adSets[ad_set_index].daily_budget = daily_budget
