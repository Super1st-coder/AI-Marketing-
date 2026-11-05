"""Unit tests for ``FacebookGetCampaignObjectiveUseCase`` (Caso_Objetivos).

The catalog is static: it must not touch the Meta Graph API, Redis or Strapi,
and must return the same data for any ``user_id``. The only change introduced
by the ``meta-ads-leads-offsite-conversions`` spec is the new
``OFFSITE_CONVERSIONS`` goal appended at index 2 of ``OUTCOME_LEADS``.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 13.6, 14.13
"""
import copy
from unittest.mock import MagicMock, patch

import pytest

from app.v2.use_cases.meta_ads import FacebookGetCampaignObjectiveUseCase
from app.v2.use_cases.facebook_validator_service import LeadsOptimizationGoal


# Literal catalog returned before this spec (Requirement 2.4 / 13.6).
PREVIOUS_CATALOG = [
    {
        'id': 'OUTCOME_AWARENESS',
        'active': True,
        'goals': [
            {'id': 'AD_RECALL_LIFT', 'billing_event': 'IMPRESSIONS'},
            {'id': 'REACH', 'billing_event': 'IMPRESSIONS'},
            {'id': 'IMPRESSIONS', 'billing_event': 'IMPRESSIONS'},
            {'id': 'THRUPLAY', 'billing_event': 'IMPRESSIONS'},
            {'id': 'TWO_SECOND_CONTINUOUS_VIDEO_VIEWS', 'billing_event': 'IMPRESSIONS'},
        ],
    },
    {'id': 'OUTCOME_TRAFFIC', 'active': False, 'goals': []},
    {
        'id': 'OUTCOME_SALES',
        'active': True,
        'goals': [
            {'id': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS'},
            {'id': 'VALUE', 'billing_event': 'IMPRESSIONS'},
            {'id': 'LINK_CLICKS', 'billing_event': 'IMPRESSIONS'},
        ],
    },
    {
        'id': 'OUTCOME_LEADS',
        'active': True,
        'goals': [
            {'id': 'LEAD_GENERATION', 'billing_event': 'IMPRESSIONS'},
            {'id': 'CONVERSATIONS', 'billing_event': 'IMPRESSIONS'},
        ],
    },
]

NEW_LEADS_GOAL = {'id': 'OFFSITE_CONVERSIONS', 'billing_event': 'IMPRESSIONS'}


def _expected_catalog():
    expected = copy.deepcopy(PREVIOUS_CATALOG)
    expected[3]['goals'].insert(2, dict(NEW_LEADS_GOAL))
    return expected


def _fail(*args, **kwargs):
    raise AssertionError("External dependency must not be invoked by Caso_Objetivos")


@pytest.fixture
def isolated():
    """Patch ``requests`` and ``redis_client`` in ``meta_ads`` so any call fails."""
    requests_mock = MagicMock(name="requests")
    for method in ("get", "post", "put", "patch", "delete", "request"):
        getattr(requests_mock, method).side_effect = _fail
    redis_mock = MagicMock(name="redis_client")
    for method in ("get", "set", "exists", "delete", "setex"):
        getattr(redis_mock, method).side_effect = _fail
    with patch("app.v2.use_cases.meta_ads.requests", requests_mock), \
            patch("app.v2.use_cases.meta_ads.redis_client", redis_mock), \
            patch("requests.sessions.Session.request", side_effect=_fail):
        yield requests_mock, redis_mock


def _leads(catalog):
    return next(o for o in catalog if o['id'] == 'OUTCOME_LEADS')


class TestCampaignObjectiveCatalog:

    def test_catalog_equals_previous_plus_new_leads_goal(self, isolated):
        result = FacebookGetCampaignObjectiveUseCase().execute("user-1")
        assert result == _expected_catalog()

    def test_catalog_without_new_goal_equals_previous_catalog(self, isolated):
        result = copy.deepcopy(FacebookGetCampaignObjectiveUseCase().execute("user-1"))
        goals = _leads(result)['goals']
        assert goals.count(NEW_LEADS_GOAL) == 1
        goals.remove(NEW_LEADS_GOAL)
        assert result == PREVIOUS_CATALOG

    def test_leads_goals_order_and_new_element_at_index_2(self, isolated):
        goals = _leads(FacebookGetCampaignObjectiveUseCase().execute("user-1"))['goals']
        assert len(goals) == 3
        assert goals[0] == {'id': 'LEAD_GENERATION', 'billing_event': 'IMPRESSIONS'}
        assert goals[1] == {'id': 'CONVERSATIONS', 'billing_event': 'IMPRESSIONS'}
        assert goals[2] == NEW_LEADS_GOAL
        assert goals[2]['id'] == LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value

    def test_leads_active_without_quality_lead(self, isolated):
        leads = _leads(FacebookGetCampaignObjectiveUseCase().execute("user-1"))
        assert leads['active'] is True
        assert all(g['id'] != 'QUALITY_LEAD' for g in leads['goals'])

    def test_returns_four_objectives_in_order(self, isolated):
        result = FacebookGetCampaignObjectiveUseCase().execute("user-1")
        assert [o['id'] for o in result] == [
            'OUTCOME_AWARENESS', 'OUTCOME_TRAFFIC', 'OUTCOME_SALES', 'OUTCOME_LEADS'
        ]
        assert result[:3] == PREVIOUS_CATALOG[:3]

    @pytest.mark.parametrize("user_id", ["user-1", "another-user", "", None, "42"])
    def test_no_external_calls_and_same_result_for_any_user(self, isolated, user_id):
        requests_mock, redis_mock = isolated
        result = FacebookGetCampaignObjectiveUseCase().execute(user_id)
        assert result == _expected_catalog()
        assert requests_mock.method_calls == []
        assert redis_mock.method_calls == []
