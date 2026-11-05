"""Google Ads client factory -- shared across all tool modules."""

import os
from dotenv import load_dotenv

load_dotenv()

_client_cache = None


def get_google_ads_client():
    """Returns a cached GoogleAdsClient instance configured from .env variables."""
    global _client_cache
    if _client_cache is not None:
        return _client_cache

    from google.ads.googleads.client import GoogleAdsClient

    config = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").replace("-", ""),
        "use_proto_plus": True,
    }
    _client_cache = GoogleAdsClient.load_from_dict(config, version="v23")
    return _client_cache


def get_customer_id() -> str:
    """Returns the Google Ads customer ID (no dashes)."""
    return os.getenv("GOOGLE_ADS_CUSTOMER_ID", "").replace("-", "")


def micros_to_currency(micros: int) -> float:
    """Convert Google Ads micros (millionths) to dollars."""
    return micros / 1_000_000 if micros else 0.0


def currency_to_micros(dollars: float) -> int:
    """Convert dollars to Google Ads micros (millionths)."""
    return int(dollars * 1_000_000)
