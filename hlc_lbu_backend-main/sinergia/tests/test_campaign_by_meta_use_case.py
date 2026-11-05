from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.base import DataNotFoundException, ParametersNotFoundException
from app.v2.use_cases.campaign import GetACampaignByMetaIDUseCase


@patch('app.v2.use_cases.campaign.AccountRepository')
@patch('app.v2.use_cases.campaign.BrandRepository')
@patch('app.v2.use_cases.campaign.CampaignChannelPublishRepository')
def test_execute_returns_campaign_data_for_valid_meta_mapping(
    mock_publish_repo_cls,
    mock_brand_repo_cls,
    mock_account_repo_cls,
):
    account_repo = mock_account_repo_cls.return_value
    brand_repo = mock_brand_repo_cls.return_value
    publish_repo = mock_publish_repo_cls.return_value

    account_repo.get_by_email.return_value = {
        'id': 10,
        'attributes': {
            'parent_account': {'data': {'id': 99}}
        }
    }
    brand_repo.get_by_id_and_account.return_value = {
        'id': 7,
        'attributes': {'name': 'Brand One'}
    }

    publish_repo.get_by_meta_campaign_id_and_brand_account.return_value = {
        'attributes': {
            'campaign_id': {
                'data': {
                    'id': 55,
                    'attributes': {
                        'name': 'Campaign One',
                        'brand_ref': {'data': {'id': 7, 'attributes': {'name': 'Brand One'}}},
                        'project_ref': {'data': {
                            'id': 12,
                            'attributes': {
                                'product_ref': {'data': {'id': 21, 'attributes': {'name': 'Product One'}}},
                                'bperson_ref': {'data': {'id': 33, 'attributes': {'name': 'Buyer Person One'}}},
                            }
                        }},
                        'ucampaign_ref': {'data': {'id': 88, 'attributes': {'name': 'Umbrella One'}}},
                    }
                }
            }
        }
    }

    use_case = GetACampaignByMetaIDUseCase(user_id='user@example.com')
    result = use_case.execute(7, 'meta-123')

    assert result == {
        'brand_id': 7,
        'brand_name': 'Brand One',
        'campaign_id': 55,
        'campaign_name': 'Campaign One',
        'project_id': 12,
        'umbrella_campaign_id': 88,
        'umbrella_campaign_name': 'Umbrella One',
        'buyer_person_id': 33,
        'buyer_person_name': 'Buyer Person One',
        'product_id': 21,
        'product_name': 'Product One',
    }

    account_repo.get_by_email.assert_called_once_with('user@example.com')
    brand_repo.get_by_id_and_account.assert_called_once_with(7, 99)
    publish_repo.get_by_meta_campaign_id_and_brand_account.assert_called_once_with('meta-123', 7, 99)


@patch('app.v2.use_cases.campaign.AccountRepository')
@patch('app.v2.use_cases.campaign.BrandRepository')
@patch('app.v2.use_cases.campaign.CampaignChannelPublishRepository')
def test_execute_raises_when_brand_is_missing_for_parent_account(
    mock_publish_repo_cls,
    mock_brand_repo_cls,
    mock_account_repo_cls,
):
    account_repo = mock_account_repo_cls.return_value
    brand_repo = mock_brand_repo_cls.return_value
    publish_repo = mock_publish_repo_cls.return_value

    account_repo.get_by_email.return_value = {
        'id': 10,
        'attributes': {'parent_account': {'data': {'id': 99}}}
    }
    brand_repo.get_by_id_and_account.return_value = None

    use_case = GetACampaignByMetaIDUseCase(user_id='user@example.com')

    with pytest.raises(DataNotFoundException, match='Brand not found'):
        use_case.execute(7, 'meta-123')

    publish_repo.get_by_meta_campaign_id_and_brand_account.assert_not_called()


@patch('app.v2.use_cases.campaign.AccountRepository')
@patch('app.v2.use_cases.campaign.BrandRepository')
@patch('app.v2.use_cases.campaign.CampaignChannelPublishRepository')
def test_execute_raises_when_mapping_not_found(
    mock_publish_repo_cls,
    mock_brand_repo_cls,
    mock_account_repo_cls,
):
    account_repo = mock_account_repo_cls.return_value
    brand_repo = mock_brand_repo_cls.return_value
    publish_repo = mock_publish_repo_cls.return_value

    account_repo.get_by_email.return_value = {
        'id': 10,
        'attributes': {'parent_account': {'data': {'id': 99}}}
    }
    brand_repo.get_by_id_and_account.return_value = {'id': 7, 'attributes': {'name': 'Brand One'}}
    publish_repo.get_by_meta_campaign_id_and_brand_account.return_value = None

    use_case = GetACampaignByMetaIDUseCase(user_id='user@example.com')

    with pytest.raises(DataNotFoundException, match='Campaign not found for the given Meta campaign and brand/account'):
        use_case.execute(7, 'meta-123')


@patch('app.v2.use_cases.campaign.AccountRepository')
@patch('app.v2.use_cases.campaign.BrandRepository')
@patch('app.v2.use_cases.campaign.CampaignChannelPublishRepository')
def test_execute_raises_when_required_params_are_missing(
    mock_publish_repo_cls,
    mock_brand_repo_cls,
    mock_account_repo_cls,
):
    use_case = GetACampaignByMetaIDUseCase(user_id='user@example.com')

    with pytest.raises(ParametersNotFoundException, match='Brand Id is required'):
        use_case.execute(None, 'meta-123')

    with pytest.raises(ParametersNotFoundException, match='Meta Campaign Id is required'):
        use_case.execute(7, None)

    mock_account_repo_cls.return_value.get_by_email.assert_not_called()
    mock_brand_repo_cls.return_value.get_by_id_and_account.assert_not_called()
    mock_publish_repo_cls.return_value.get_by_meta_campaign_id_and_brand_account.assert_not_called()


@patch('app.v2.use_cases.campaign.AccountRepository')
def test_parent_account_falls_back_to_account_id_when_no_parent_relation(mock_account_repo_cls):
    account_repo = mock_account_repo_cls.return_value
    account_repo.get_by_email.return_value = {
        'id': 42,
        'attributes': {'parent_account': {'data': None}}
    }

    use_case = GetACampaignByMetaIDUseCase(user_id='user@example.com')

    assert use_case._get_parent_account() == 42
