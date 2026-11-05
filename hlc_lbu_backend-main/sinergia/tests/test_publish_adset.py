import json
from unittest.mock import patch, MagicMock

from app.v2.use_cases.meta_ads import FacebookLaunchCampaignUseCase


def make_response(status=200, data=None):
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = data or {"id": "123"}
    return mock


@patch('app.v2.use_cases.meta_ads.requests.post')
def test_publish_adset_includes_promoted_object_sales(mock_post):
    # Arrange
    mock_post.return_value = make_response(200, {"id": "adset-1"})

    usecase = FacebookLaunchCampaignUseCase(user_id='u1', data={
        'brand_id': 1,
        'campaign_id': 1,
        'creatives': []
    })

    # set attributes needed by _publish_adset
    usecase.ad_account_id = 'act_123'
    usecase.campaign_mode = 'DYNAMIC'
    usecase.campaign_objective = 'OUTCOME_SALES'
    usecase.campaign_optimization_goal = 'OFFSITE_CONVERSIONS'
    usecase.campaign_setup = {'attributes': {'meta_pixel_id': 'PIXEL_FROM_SETUP'}}

    # patch _get_pixel to return fallback pixel
    usecase._get_pixel = lambda: 'PIXEL_ACCOUNT'

    adset = {
        'name': 'adset test',
        'campaign_id': 'camp-1',
        'daily_budget': 10,
        'billing_event': 'IMPRESSIONS',
        'optimization_goal': 'OFFSITE_CONVERSIONS',
        'targeting': {},
        'status': 'PAUSED',
        # no promoted_object provided -> should be constructed
    }

    # Act
    adset_id = usecase._publish_adset(adset, access_token='token123')

    # Assert
    assert adset_id == 'adset-1'
    # Verify requests.post called and payload includes promoted_object with pixel and custom_event_type PURCHASE
    args, kwargs = mock_post.call_args
    payload = kwargs.get('json')
    assert payload is not None
    promoted = payload.get('promoted_object')
    assert promoted is not None
    assert promoted.get('pixel_id') in ('PIXEL_FROM_SETUP', 'PIXEL_ACCOUNT')
    assert promoted.get('custom_event_type') == 'PURCHASE'
