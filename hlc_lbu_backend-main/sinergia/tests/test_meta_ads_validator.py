import pytest

from app.v2.use_cases.facebook_validator_service import (
    MetaAdsValidator,
    CampaignObjective,
)


def test_validate_promoted_object_offsite_conversions_fills_defaults():
    promoted = {}
    # should accept pixel_id passed separately and fill default custom_event_type PURCHASE
    result = MetaAdsValidator.validate_promoted_object(promoted, CampaignObjective.SALES.value, 'OFFSITE_CONVERSIONS', pixel_id='PIXEL123', throw=True)
    assert result is True
    assert promoted.get('pixel_id') == 'PIXEL123'
    assert promoted.get('custom_event_type') == 'PURCHASE'


def test_validate_cta_for_goal_sales_allowed_and_disallowed():
    # allowed CTA for VALUE
    ok = MetaAdsValidator.validate_cta_for_goal('shop_now', CampaignObjective.SALES.value, 'VALUE', throw=False)
    assert ok is True

    # disallowed CTA for CONVERSATIONS
    nok = MetaAdsValidator.validate_cta_for_goal('SHOP_NOW', CampaignObjective.SALES.value, 'CONVERSATIONS', throw=False)
    assert nok is False
