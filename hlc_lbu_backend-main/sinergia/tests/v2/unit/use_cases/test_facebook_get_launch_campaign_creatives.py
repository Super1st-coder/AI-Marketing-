"""Unit test suite for ``FacebookGetLaunchCampaignCreativesUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookGetLaunchCampaignCreativesUseCase``
(the read-only query that returns the already published creatives of a Meta Ads
campaign) plus the additive query method of
``app.v2.repository.ad_set.AdSetRepository`` that feeds it.

The use case is read-only: four Strapi read queries (``accounts``,
``campaigns``, ``ad-sets``, ``campaign-channel-publishes``), 0 Graph API
requests, 0 Redis accesses and 0 writes. It returns the three-key query result
(``campaign``, ``creatives``, ``meta_url``) with the very same 31 keys per
creative that ``FacebookLaunchCampaignUseCase._build_response()`` produces
today.

Criteria covered by this module (Requirement 11 of the spec
``sinergia/.kiro/specs/meta-ads-get-launch-campaign-creatives/``):

* 11.1  this file is the only test file created by the specification.
* 11.2  the four repositories are substituted by test doubles in the namespace
        from which the use case resolves them; 0 real network requests,
        0 Redis connections and 0 Strapi requests in the whole suite.
* 11.3  no HTTP client is mocked; ``requests`` is never invoked.
* 11.4  every test datum comes from a builder function that returns, on every
        invocation, a brand new dict with brand new lists (no mutable default
        arguments), so no test case shares mutable state with another one and
        the outcome of a case is independent of the suite execution order.
* 11.5 - 11.23  main flows (``DYNAMIC``/``STANDARD``), parity with the launch
        use case, ``campaign`` block, ``meta_url``, Channel_ID resolution,
        ad-channel selection, Strapi identifiers, failure scenarios,
        validation order, degraded structures, absence of external traffic and
        the new ``AdSetRepository`` query.

Requirements: 11.1, 11.2, 11.3, 11.4
"""
import ast
import contextlib
import copy
import inspect
import os
import re
from unittest.mock import MagicMock, call, patch  # noqa: F401  (MagicMock: spies)

import pytest
import requests  # noqa: F401  (``deny_network`` patches it by dotted path)

from app.exceptions.base import (  # noqa: F401  (used by the failure scenarios)
    DataNotFoundException,
    IncorrectValidationException,
)
from app.v2.repository.ad_set import AdSetRepository  # noqa: F401
from app.v2.use_cases import meta_ads as meta_ads_module
from app.v2.use_cases.facebook_validator_service import CreativeType
from app.v2.use_cases.meta_ads import (  # noqa: F401
    FacebookGetLaunchCampaignCreativesUseCase,
    FacebookLaunchCampaignUseCase,
)


class _AbsentSentinel:
    """Private sentinel type used by the builder functions below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it entirely from the resulting dict" from
    "this key was provided by the caller with the value ``None``". That
    distinction is unavoidable here, because Requirements 5.5, 5.6, 5.7, 6.2
    and 7.4 treat an absent key and a key present with value ``None`` as two
    different scenarios with (potentially) different outcomes.

    Requirements: 11.4
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


class _DefaultSentinel:
    """Private sentinel marking "the builder supplies its canonical value".

    ``ABSENT`` already means "omit this key", and an explicit ``None`` must
    stay available as a *value* (Requirements 5.5, 5.6, 5.7, 6.2, 7.4), so a
    third marker is needed for the parameter defaults of every degradable
    level. It is never exposed in a built structure: ``DEFAULT`` in, canonical
    value out.

    Requirements: 11.4
    """

    def __repr__(self):
        return "DEFAULT"


_DEFAULT = _DefaultSentinel()


#: The 31 keys of a Creative_Entry, in the exact order fixed by Requirement
#: 8.1 and identical in the ``DYNAMIC`` and ``STANDARD`` branches. Frozen as a
#: tuple so that assertions can compare both the key *set* and the key
#: *order* against it (Requirements 8.1, 11.5, 11.6).
CREATIVE_ENTRY_KEYS = (
    'idx',
    'name',
    'adset_id',
    'ad_id',
    'adchannel_id',
    'daily_budget',
    'images',
    'bodies',
    'titles',
    'descriptions',
    'call_to_action_types',
    'images_valid_amount',
    'titles_valid_amount',
    'bodies_valid_amount',
    'descriptions_valid_amount',
    'call_to_action_types_valid_amount',
    'images_max_amount',
    'titles_max_amount',
    'bodies_max_amount',
    'descriptions_max_amount',
    'call_to_action_types_max_amount',
    'unique_titles',
    'unique_bodies',
    'unique_descriptions',
    'daily_budget_valid',
    'min_daily_budget',
    'proposal_url',
    'proposal_url_valid',
    'proposal_locations',
    'locations',
    'locations_valid',
)


def _put(container, key, value):
    """Assign ``value`` to ``container[key]`` unless it is the ``ABSENT``
    sentinel, in which case the key is left out of ``container`` entirely.

    Requirements: 11.4
    """
    if value is not ABSENT:
        container[key] = value


def _merge(container, overrides):
    """Merge ``overrides`` into ``container``, honouring the ``ABSENT``
    sentinel: an override whose value is ``ABSENT`` *removes* the key instead
    of assigning it.

    Requirements: 11.4
    """
    for key, value in overrides.items():
        if value is ABSENT:
            container.pop(key, None)
        else:
            container[key] = value
    return container


# ---------------------------------------------------------------------------
# Builder functions (Requirement 11.4)
#
# Every builder returns, on every invocation, a brand new dict with brand new
# nested dicts and lists. No builder has a mutable default argument: the
# degradable parameters default to the private ``_DEFAULT`` marker and the
# canonical structure is rebuilt from scratch on each call.
# ---------------------------------------------------------------------------


def make_account(parent_account_id=ABSENT, account_id=1, **overrides):
    """Build a fresh ``accounts`` record as returned by
    ``AccountRepository.get_by_email``.

    ``parent_account_id`` defaults to ``ABSENT``: the ``parent_account`` key
    is then omitted from ``attributes`` and ``_get_parent_account()`` falls
    back to ``account['id']`` (Requirement 3.5). Pass an integer to exercise
    the ``attributes.parent_account.data.id`` path (Requirement 3.4).

    Requirements: 3.4, 3.5, 11.4
    """
    attributes = {'email': 'user@example.com'}
    if parent_account_id is not ABSENT:
        attributes['parent_account'] = {'data': {'id': parent_account_id}}
    account = {'id': account_id, 'attributes': attributes}
    return _merge(account, overrides)


def make_campaign(campaign_id=41, name='Campaña Primavera', attributes=_DEFAULT,
                  **overrides):
    """Build a fresh ``campaigns`` record as returned by
    ``CampaignRepository.get_by_id_brand_and_account``.

    Deliberately built with ``attributes.name`` and **no other attribute**, so
    that Requirement 4.5 ("no other attribute is read") is verifiable by
    construction. Pass ``name=ABSENT`` to omit the key, or ``attributes`` to
    degrade the whole node (``ABSENT``, ``None`` or an unexpected type).

    Requirements: 4.5, 11.4
    """
    campaign = {'id': campaign_id}
    if attributes is _DEFAULT:
        node = {}
        _put(node, 'name', name)
        campaign['attributes'] = node
    else:
        _put(campaign, 'attributes', attributes)
    return _merge(campaign, overrides)


def _make_dynamic_asset_feed_spec(ad_channel_id=9001):
    """Build a fresh canonical ``asset_feed_spec`` (``DYNAMIC`` branch).

    Requirements: 8.3, 11.4
    """
    return {
        'ad_channel_id': ad_channel_id,
        'images': [
            {'url': 'https://example.test/img-1.jpg', 'valid': True, 'error': None},
            {'url': 'https://example.test/img-2.jpg', 'valid': False, 'error': 'too small'},
        ],
        'bodies': [{'text': 'Cuerpo 1', 'valid_length': True}],
        'titles': [{'text': 'Titular 1', 'valid_length': True}],
        'descriptions': [{'text': 'Descripción 1', 'valid_length': True}],
        'call_to_action_types': [{'value': 'SHOP_NOW', 'valid': True}],
        'link_urls': [{'website_url': 'https://example.test/landing'}],
        'images_valid_amount': True,
        'titles_valid_amount': True,
        'bodies_valid_amount': True,
        'descriptions_valid_amount': True,
        'call_to_action_types_valid_amount': True,
        'images_max_amount': 10,
        'titles_max_amount': 5,
        'bodies_max_amount': 5,
        'descriptions_max_amount': 5,
        'call_to_action_types_max_amount': 5,
        'unique_titles': True,
        'unique_bodies': True,
        'unique_descriptions': True,
        'daily_budget_valid': True,
        'min_daily_budget': 10,
        'link_url_valid': True,
        'locations': [{'key': '1234', 'name': 'Madrid'}],
        'locations_valid': True,
    }


def make_dynamic_creative(creative_id=120, name='Ad Set A', daily_budget=15,
                          ad_id=501, ad_name='Ad 1', ad_channel_id=9001,
                          ads=_DEFAULT, ad_creative=_DEFAULT,
                          asset_feed_spec=_DEFAULT, targeting=_DEFAULT,
                          proposal_locations=_DEFAULT, **spec_overrides):
    """Build a fresh Published_Creative (``channel_creative``) in ``DYNAMIC``
    mode, with the ad-set shape persisted by the pre-check flow and an ``ads``
    list of exactly one element.

    Degradation points, each accepting ``ABSENT`` (key omitted), ``None`` or
    an unexpected type: ``ads``, ``ad_creative`` (the ``adCreative`` key of the
    single ad), ``asset_feed_spec``, ``targeting`` and ``proposal_locations``.
    Any ``**spec_overrides`` are merged into ``asset_feed_spec``, so every leaf
    key can be replaced or removed (``ABSENT``) individually.

    Requirements: 8.1, 8.3, 8.8, 11.4
    """
    creative = {'id': creative_id}
    _put(creative, 'name', name)
    _put(creative, 'daily_budget', daily_budget)
    if targeting is _DEFAULT:
        creative['targeting'] = {'geo_locations': {'cities': []}}
    else:
        _put(creative, 'targeting', targeting)
    if proposal_locations is _DEFAULT:
        creative['proposal_locations'] = [{'key': '1234', 'name': 'Madrid'}]
    else:
        _put(creative, 'proposal_locations', proposal_locations)

    if ads is _DEFAULT:
        ad = {'id': ad_id}
        _put(ad, 'name', ad_name)
        if ad_creative is _DEFAULT:
            spec = (
                _make_dynamic_asset_feed_spec(ad_channel_id)
                if asset_feed_spec is _DEFAULT
                else asset_feed_spec
            )
            if isinstance(spec, dict):
                _merge(spec, spec_overrides)
            creative_node = {'name': 'Creative 1'}
            _put(creative_node, 'asset_feed_spec', spec)
            ad['adCreative'] = creative_node
        else:
            _put(ad, 'adCreative', ad_creative)
        creative['ads'] = [ad]
    else:
        _put(creative, 'ads', ads)

    return creative


def _make_standard_object_story_spec(ad_channel_id=9001, link_data=_DEFAULT,
                                     call_to_action=_DEFAULT):
    """Build a fresh canonical ``object_story_spec`` (``STANDARD`` branch).

    Requirements: 8.4, 11.4
    """
    spec = {
        'ad_channel_id': ad_channel_id,
        'page_id': '111222333',
        'daily_budget_valid': True,
        'min_daily_budget': 10,
        'locations': [{'key': '1234', 'name': 'Madrid'}],
        'locations_valid': True,
    }
    if link_data is _DEFAULT:
        node = {
            'name': 'Titular',
            'title_valid': True,
            'message': 'Cuerpo',
            'body_valid': True,
            'description': 'Descripción',
            'description_valid': True,
            'image_url': 'https://example.test/img-1.jpg',
            'image_valid': True,
            'image_error': None,
            'link': 'https://example.test/landing',
            'link_url_valid': True,
        }
        if call_to_action is _DEFAULT:
            node['call_to_action'] = {'type': {'value': 'SHOP_NOW', 'valid': True}}
        else:
            _put(node, 'call_to_action', call_to_action)
        spec['link_data'] = node
    else:
        _put(spec, 'link_data', link_data)
    return spec


def make_standard_creative(creative_id=120, name='Ad Set A', daily_budget=15,
                           ad_id=501, ad_name='Ad 1', ad_channel_id=9001,
                           ads=_DEFAULT, ad_creative=_DEFAULT,
                           object_story_spec=_DEFAULT, link_data=_DEFAULT,
                           call_to_action=_DEFAULT, targeting=_DEFAULT,
                           proposal_locations=_DEFAULT, spec_overrides=None,
                           **link_data_overrides):
    """Build a fresh Published_Creative (``channel_creative``) in ``STANDARD``
    mode, with the same ad-set shape and a single-element ``ads`` list.

    Degradation points, each accepting ``ABSENT`` (key omitted), ``None`` or
    an unexpected type: ``ads``, ``ad_creative``, ``object_story_spec``,
    ``link_data``, ``call_to_action``, ``targeting`` and
    ``proposal_locations``. ``spec_overrides`` is merged into
    ``object_story_spec`` and ``**link_data_overrides`` into ``link_data``, so
    every leaf key can be replaced or removed (``ABSENT``) individually.

    Requirements: 8.1, 8.4, 8.8, 11.4
    """
    creative = {'id': creative_id}
    _put(creative, 'name', name)
    _put(creative, 'daily_budget', daily_budget)
    if targeting is _DEFAULT:
        creative['targeting'] = {'geo_locations': {'cities': []}}
    else:
        _put(creative, 'targeting', targeting)
    if proposal_locations is _DEFAULT:
        creative['proposal_locations'] = [{'key': '1234', 'name': 'Madrid'}]
    else:
        _put(creative, 'proposal_locations', proposal_locations)

    if ads is _DEFAULT:
        ad = {'id': ad_id}
        _put(ad, 'name', ad_name)
        if ad_creative is _DEFAULT:
            if object_story_spec is _DEFAULT:
                spec = _make_standard_object_story_spec(
                    ad_channel_id, link_data, call_to_action,
                )
            else:
                spec = object_story_spec
            if isinstance(spec, dict):
                _merge(spec, spec_overrides or {})
                if isinstance(spec.get('link_data'), dict):
                    _merge(spec['link_data'], link_data_overrides)
            creative_node = {'name': 'Creative 1'}
            _put(creative_node, 'object_story_spec', spec)
            ad['adCreative'] = creative_node
        else:
            _put(ad, 'adCreative', ad_creative)
        creative['ads'] = [ad]
    else:
        _put(creative, 'ads', ads)

    return creative


def make_ad_channel(ad_channel_id=9001, selected=True, channel_ref_id=2,
                    channel_creative=_DEFAULT, attributes=_DEFAULT,
                    channel_ref=_DEFAULT, channel_ref_data=_DEFAULT,
                    **attribute_overrides):
    """Build a fresh element of ``ad_channels.data``.

    ``channel_creative`` defaults to a fresh ``make_dynamic_creative()``; pass
    ``ABSENT`` to omit the key, ``None`` to include it with value ``None``, or
    any other value (a non-dict, an empty dict, ...) for the degraded
    scenarios of Requirement 5.5.

    ``selected`` accepts any value, including the falsy ones of Requirement
    5.3 (``False``, ``None``, ``0``, ``''``) and ``ABSENT`` to omit the key.

    The four levels of ``attributes.channel_ref.data.id`` are individually
    degradable through ``attributes``, ``channel_ref``, ``channel_ref_data``
    and ``channel_ref_id``, each accepting ``ABSENT``, ``None`` or an
    unexpected type (Requirements 6.1, 6.2).

    Requirements: 5.3, 5.4, 5.5, 5.7, 6.1, 6.2, 11.4
    """
    ad_channel = {'id': ad_channel_id}
    if attributes is not _DEFAULT:
        _put(ad_channel, 'attributes', attributes)
        return ad_channel

    node = {}
    _put(node, 'selected', selected)

    if channel_ref is _DEFAULT:
        ref = {}
        if channel_ref_data is _DEFAULT:
            data = {}
            _put(data, 'id', channel_ref_id)
            ref['data'] = data
        else:
            _put(ref, 'data', channel_ref_data)
        node['channel_ref'] = ref
    else:
        _put(node, 'channel_ref', channel_ref)

    if channel_creative is _DEFAULT:
        node['channel_creative'] = make_dynamic_creative()
    else:
        _put(node, 'channel_creative', channel_creative)

    _merge(node, attribute_overrides)
    ad_channel['attributes'] = node
    return ad_channel


def make_ad(ad_id=501, name='Ad 1', ad_channels=_DEFAULT,
            ad_channels_data=_DEFAULT, attributes=_DEFAULT,
            **attribute_overrides):
    """Build a fresh element of ``ads.data``.

    ``attributes``, ``ad_channels`` and ``ad_channels_data`` (the ``data`` key
    of ``ad_channels``) are individually degradable to ``ABSENT`` (key
    omitted), to ``None`` and to an unexpected type, as required by
    Requirement 5.7. By default ``ad_channels.data`` holds a single fresh
    ``make_ad_channel()``.

    Requirements: 5.3, 5.7, 11.4
    """
    ad = {'id': ad_id}
    if attributes is not _DEFAULT:
        _put(ad, 'attributes', attributes)
        return ad

    node = {}
    _put(node, 'name', name)
    if ad_channels is _DEFAULT:
        channels = {}
        if ad_channels_data is _DEFAULT:
            channels['data'] = [make_ad_channel()]
        else:
            _put(channels, 'data', ad_channels_data)
        node['ad_channels'] = channels
    else:
        _put(node, 'ad_channels', ad_channels)

    _merge(node, attribute_overrides)
    ad['attributes'] = node
    return ad


def make_ad_set(ad_set_id=120, name='Ad Set A', ads=_DEFAULT, ads_data=_DEFAULT,
                attributes=_DEFAULT, **attribute_overrides):
    """Build a fresh element of the ``data`` list of the ad-sets response.

    ``attributes``, ``ads`` and ``ads_data`` (the ``data`` key of ``ads``) are
    individually degradable to ``ABSENT`` (key omitted), to ``None`` and to an
    unexpected type, as required by Requirement 5.7. By default ``ads.data``
    holds a single fresh ``make_ad()``.

    Requirements: 5.3, 5.7, 11.4
    """
    ad_set = {'id': ad_set_id}
    if attributes is not _DEFAULT:
        _put(ad_set, 'attributes', attributes)
        return ad_set

    node = {}
    _put(node, 'name', name)
    if ads is _DEFAULT:
        ads_node = {}
        if ads_data is _DEFAULT:
            ads_node['data'] = [make_ad()]
        else:
            _put(ads_node, 'data', ads_data)
        node['ads'] = ads_node
    else:
        _put(node, 'ads', ads)

    _merge(node, attribute_overrides)
    ad_set['attributes'] = node
    return ad_set


def make_ad_sets_response(ad_sets=_DEFAULT, envelope=_DEFAULT,
                          include_meta=True):
    """Build a fresh response of the new ``AdSetRepository`` query.

    By default returns ``{'data': [make_ad_set()], 'meta': {...}}``. The
    ``data`` key is degradable to ``ABSENT`` (yielding ``{}``), to ``None``,
    to an empty list and to a non-list value. Pass ``envelope`` to return an
    arbitrary value verbatim — ``None`` or a non-dict — covering the remaining
    invalid-response scenarios of Requirement 5.2.

    Requirements: 5.2, 9.4, 9.5, 11.4
    """
    if envelope is not _DEFAULT:
        return envelope

    response = {}
    if ad_sets is _DEFAULT:
        response['data'] = [make_ad_set()]
    else:
        _put(response, 'data', ad_sets)
    if include_meta:
        response['meta'] = {'pagination': {'page': 1, 'pageSize': 25, 'total': 1}}
    return response


def make_campaign_setup(campaign_setup_id=55, meta_published=True,
                        meta_campaign_mode=CreativeType.DYNAMIC.value,
                        meta_campaign_objective='OUTCOME_TRAFFIC',
                        meta_optimization_goal='LINK_CLICKS',
                        meta_account_id='1234567890',
                        meta_campaign_id='987654321',
                        meta_resources=_DEFAULT, attributes=_DEFAULT,
                        **attribute_overrides):
    """Build a fresh ``campaign-channel-publishes`` record (the
    Campaign_Setup) as returned by
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``.

    The use case reads seven attributes (``meta_published``,
    ``meta_campaign_mode``, ``meta_campaign_objective``,
    ``meta_optimization_goal``, ``meta_account_id``, ``meta_campaign_id``,
    ``meta_conversion_event``). The canonical fixture includes the first six
    but **not** ``meta_conversion_event``, so the expected
    ``conversion_event`` is ``None``; a case injects it through
    ``**attribute_overrides``. The fixture **also** includes
    ``meta_resources``, whose presence in the fixture is what
    makes Requirement 7.7 ("``meta_resources`` is not read") verifiable.

    Every attribute accepts ``ABSENT`` to omit the key; ``meta_published``
    additionally accepts the five rejected values of Requirement 11.15
    (``False``, ``None``, ``1``, ``'True'``, ``'true'``), and ``attributes``
    is degradable as a whole.

    Requirements: 7.3, 7.4, 7.6, 7.7, 8.5, 11.4, 11.15
    """
    campaign_setup = {'id': campaign_setup_id}
    if attributes is not _DEFAULT:
        _put(campaign_setup, 'attributes', attributes)
        return campaign_setup

    node = {}
    _put(node, 'meta_published', meta_published)
    _put(node, 'meta_campaign_mode', meta_campaign_mode)
    _put(node, 'meta_campaign_objective', meta_campaign_objective)
    _put(node, 'meta_optimization_goal', meta_optimization_goal)
    _put(node, 'meta_account_id', meta_account_id)
    _put(node, 'meta_campaign_id', meta_campaign_id)
    if meta_resources is _DEFAULT:
        node['meta_resources'] = [{'adset_id': '120', 'ads': [{'ad_id': '501'}]}]
    else:
        _put(node, 'meta_resources', meta_resources)

    _merge(node, attribute_overrides)
    campaign_setup['attributes'] = node
    return campaign_setup


ALL_BUILDERS = (
    make_account,
    make_campaign,
    make_dynamic_creative,
    make_standard_creative,
    make_ad_channel,
    make_ad,
    make_ad_set,
    make_ad_sets_response,
    make_campaign_setup,
)


# ---------------------------------------------------------------------------
# Shared fixtures and helpers (Requirements 11.2, 11.3, 11.4)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Local guard (not a global ``conftest.py`` fixture), ``autouse=True`` at
    function scope, that replaces ``requests.sessions.Session.request`` with a
    function raising ``AssertionError`` immediately.

    The use case under test issues 0 external HTTP requests: it only performs
    four Strapi *read* queries, and those four repositories are always
    substituted by test doubles (see ``patched_use_case``). No HTTP client and
    no ``redis_client`` is patched anywhere in this suite (Requirement 11.3);
    this fixture is the safety net that turns any accidental leak towards a
    real endpoint into a loud, immediate failure instead of real traffic.

    It replicates the mechanism already present in
    ``sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py``
    and lives in this module, not in a ``conftest.py`` (Requirement 1.2 allows
    exactly one new file).

    Requirements: 11.2, 11.3
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request", _raise_on_network_access
    )


#: Patch targets of the four dependencies, taken verbatim from the table of
#: ``design.md``: the namespace of the *consuming* module
#: (``app.v2.use_cases.meta_ads``), never the namespace where each repository
#: is defined. All four are resolved in ``__init__``, hence they are patched
#: *before* the use case is constructed (Requirement 11.2).
ACCOUNT_REPOSITORY_TARGET = 'app.v2.use_cases.meta_ads.AccountRepository'
CAMPAIGN_REPOSITORY_TARGET = 'app.v2.use_cases.meta_ads.CampaignRepository'
AD_SET_REPOSITORY_TARGET = 'app.v2.use_cases.meta_ads.AdSetRepository'
CAMPAIGN_CHANNEL_PUBLISH_REPOSITORY_TARGET = (
    'app.v2.use_cases.meta_ads.CampaignChannelPublishRepository'
)


@contextlib.contextmanager
def patched_use_case(user_id='user@example.com', account=_DEFAULT,
                     campaign=_DEFAULT, ad_sets_response=_DEFAULT,
                     campaign_setup=_DEFAULT):
    """Patch the four repository classes in the namespace from which the use
    case resolves them, **before** constructing it, and yield the instance
    together with the four repository doubles::

        with patched_use_case() as (use_case, account_repo, campaign_repo,
                                    ad_set_repo, publish_repo):
            ...

    The four patch points are the ones of the table of ``design.md``
    (``ACCOUNT_REPOSITORY_TARGET`` and friends above). They are patched before
    the construction because the four repositories are instantiated in
    ``__init__``, so patching them afterwards would leave the instance holding
    real repositories.

    Each keyword argument pre-configures the return value of the single method
    the use case calls on the corresponding double, so a test case describes
    only its own scenario instead of repeating the scaffolding:

    ==================== ==================================================
    argument             double method it configures
    ==================== ==================================================
    ``account``          ``AccountRepository.get_by_email``
    ``campaign``         ``CampaignRepository.get_by_id_brand_and_account``
    ``ad_sets_response`` ``AdSetRepository.get_by_campaign_and_brand_with_selected_ad_channels``
    ``campaign_setup``   ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``
    ==================== ==================================================

    Each one defaults to the private ``_DEFAULT`` marker, meaning "use the
    canonical value of the corresponding builder", so passing ``None``
    explicitly stays available for the failure scenarios of Requirement 11.14.

    **No HTTP client and no ``redis_client`` is patched** (Requirement 11.3):
    the use case issues no external HTTP request and performs no Redis access.
    The ``deny_network`` fixture above is what accredits that in every test.

    The four targets are patched without ``create=True``: ``AdSetRepository``
    is now imported into ``app.v2.use_cases.meta_ads``, so all four names
    already exist in that namespace and patching them must fail loudly if one
    of the imports ever disappears.

    Requirements: 11.2, 11.3, 11.4
    """
    with patch(ACCOUNT_REPOSITORY_TARGET) as account_repository_cls, \
            patch(CAMPAIGN_REPOSITORY_TARGET) as campaign_repository_cls, \
            patch(AD_SET_REPOSITORY_TARGET) as ad_set_repository_cls, \
            patch(
                CAMPAIGN_CHANNEL_PUBLISH_REPOSITORY_TARGET
            ) as campaign_channel_publish_repository_cls:
        account_repository = account_repository_cls.return_value
        campaign_repository = campaign_repository_cls.return_value
        ad_set_repository = ad_set_repository_cls.return_value
        campaign_channel_publish_repository = (
            campaign_channel_publish_repository_cls.return_value
        )

        account_repository.get_by_email.return_value = (
            make_account() if account is _DEFAULT else account
        )
        campaign_repository.get_by_id_brand_and_account.return_value = (
            make_campaign() if campaign is _DEFAULT else campaign
        )
        ad_set_repository.get_by_campaign_and_brand_with_selected_ad_channels\
            .return_value = (
                make_ad_sets_response()
                if ad_sets_response is _DEFAULT
                else ad_sets_response
            )
        campaign_channel_publish_repository.get_by_campaign_id_and_channel_id\
            .return_value = (
                make_campaign_setup()
                if campaign_setup is _DEFAULT
                else campaign_setup
            )

        use_case = FacebookGetLaunchCampaignCreativesUseCase(user_id)

        yield (
            use_case,
            account_repository,
            campaign_repository,
            ad_set_repository,
            campaign_channel_publish_repository,
        )


def assert_exception_type(exc_info, expected_type):
    """Assert that the exception captured by ``pytest.raises`` (through its
    ``exc_info``) is of exactly ``expected_type`` and **not** of a subclass.

    Deliberately checks the type and **nothing else**: the message text is
    never inspected here, because Requirement 11.14 mandates asserting only
    the exception type for the six failure scenarios. The one place where a
    message *is* compared is the indistinguishability check of Requirement
    4.3, which compares two messages against each other rather than against a
    literal.

    Requirements: 11.4
    """
    assert type(exc_info.value) is expected_type, (
        f"expected exception type {expected_type!r}, "
        f"got {type(exc_info.value)!r}"
    )


def entry_keys_in_order(entry):
    """Return the keys of a Creative_Entry as a tuple, preserving insertion
    order, so an assertion can compare the key *set* **and** the key *order*
    against ``CREATIVE_ENTRY_KEYS`` in a single comparison.

    Requirements: 8.1, 11.4
    """
    return tuple(entry.keys())


def _iter_containers(node):
    """Yield every nested ``dict`` and ``list`` of ``node``, itself included.

    Requirements: 11.4
    """
    if isinstance(node, dict):
        yield node
        for value in node.values():
            for container in _iter_containers(value):
                yield container
    elif isinstance(node, list):
        yield node
        for value in node:
            for container in _iter_containers(value):
                yield container


def _mutate_every_container(node):
    """Mutate every nested container of ``node`` in place, so that any object
    shared with another built structure becomes observable.

    Requirements: 11.4
    """
    for container in list(_iter_containers(node)):
        if isinstance(container, dict):
            container['__mutated__'] = 'tampered'
        else:
            container.append('__mutated__')


class TestBuildersIndependence:
    """Every builder returns a brand new structure on every invocation.

    Requirements: 11.4
    """

    @pytest.mark.parametrize(
        'builder', ALL_BUILDERS, ids=[builder.__name__ for builder in ALL_BUILDERS],
    )
    def test_two_invocations_return_equal_but_distinct_objects(self, builder):
        """Two invocations are equal by value and share no container object.

        Requirements: 11.4
        """
        first = builder()
        second = builder()

        assert first == second
        assert first is not second

        first_ids = {id(container) for container in _iter_containers(first)}
        second_ids = {id(container) for container in _iter_containers(second)}
        assert first_ids and second_ids
        assert first_ids.isdisjoint(second_ids)

    @pytest.mark.parametrize(
        'builder', ALL_BUILDERS, ids=[builder.__name__ for builder in ALL_BUILDERS],
    )
    def test_mutating_one_result_does_not_affect_another(self, builder):
        """Mutating every container of one result leaves another untouched.

        Requirements: 11.4
        """
        first = builder()
        second = builder()
        pristine = copy.deepcopy(second)

        _mutate_every_container(first)

        assert second == pristine
        assert first != second

    def test_creative_entry_keys_is_a_frozen_ordered_tuple_of_31_keys(self):
        """``CREATIVE_ENTRY_KEYS`` freezes the 31 keys of Requirement 8.1.

        Requirements: 8.1, 11.4
        """
        assert isinstance(CREATIVE_ENTRY_KEYS, tuple)
        assert len(CREATIVE_ENTRY_KEYS) == 31
        assert len(set(CREATIVE_ENTRY_KEYS)) == 31
        assert CREATIVE_ENTRY_KEYS[0] == 'idx'
        assert CREATIVE_ENTRY_KEYS[-1] == 'locations_valid'

    def test_absent_sentinel_is_distinguishable_from_none(self):
        """``ABSENT`` omits a key; an explicit ``None`` keeps it present.

        Requirements: 11.4
        """
        assert repr(ABSENT) == 'ABSENT'
        assert ABSENT is not None

        omitted = make_ad_channel(channel_creative=ABSENT)
        explicit_none = make_ad_channel(channel_creative=None)

        assert 'channel_creative' not in omitted['attributes']
        assert 'channel_creative' in explicit_none['attributes']
        assert explicit_none['attributes']['channel_creative'] is None


# ---------------------------------------------------------------------------
# The constructor (Requirements 2.1, 2.2, 2.3, 2.4, 2.8, 11.2)
# ---------------------------------------------------------------------------


class TestConstructor:
    """``FacebookGetLaunchCampaignCreativesUseCase.__init__``.

    Every case builds the instance through ``patched_use_case``, which patches
    the four repository classes in the consuming namespace **before** the
    construction, so the four attributes hold the doubles and not real
    repositories (Requirement 11.2).

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.8, 11.2
    """

    #: The five instance attributes Requirement 2.2 fixes, and no sixth one.
    EXPECTED_ATTRIBUTES = (
        'user_id',
        'account_repository',
        'campaign_repository',
        'ad_set_repository',
        'campaign_channel_publish_repository',
    )

    # -- The five assignments (Requirements 2.2, 2.3, 11.2) -----------------

    def test_four_repository_attributes_hold_the_corresponding_doubles(self):
        """Each attribute is the instance produced by its patched class.

        The four patch targets are the ones of ``design.md``: the namespace of
        the consuming module. Patching happens before the construction because
        the four repositories are instantiated inside ``__init__``, so identity
        against the yielded double is what accredits that no real repository
        (and therefore no real Strapi client) reached the instance.

        Requirements: 2.2, 11.2
        """
        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            assert use_case.account_repository is account_repository
            assert use_case.campaign_repository is campaign_repository
            assert use_case.ad_set_repository is ad_set_repository
            assert use_case.campaign_channel_publish_repository is (
                publish_repository
            )

            doubles = (
                use_case.account_repository,
                use_case.campaign_repository,
                use_case.ad_set_repository,
                use_case.campaign_channel_publish_repository,
            )
            for double in doubles:
                assert isinstance(double, MagicMock)
            assert len({id(double) for double in doubles}) == 4

    def test_vars_holds_exactly_the_five_expected_keys(self):
        """``vars(use_case)`` has the five keys of Requirement 2.2 and no more.

        The absence of a sixth attribute is what accredits Requirement 2.3 on
        the state side: no access token, no Redis client, no HTTP session and
        no extra repository (``AdChannelRepository``, ``AdRepository`` or
        ``ChannelRepository``) is created or stored during the construction.

        Requirements: 2.2, 2.3
        """
        with patched_use_case() as (use_case, _, _, _, _):
            assert set(vars(use_case)) == set(self.EXPECTED_ATTRIBUTES)
            assert len(vars(use_case)) == 5

    def test_user_id_is_stored_untransformed(self):
        """``self.user_id`` is the very object received, not a copy nor a
        normalised value.

        Requirements: 2.2
        """
        user_id = 'User@Example.COM  '

        with patched_use_case(user_id=user_id) as (use_case, _, _, _, _):
            assert use_case.user_id is user_id
            assert use_case.user_id == 'User@Example.COM  '

    def test_constructor_takes_a_single_required_positional_parameter(self):
        """The signature stays ``__init__(self, user_id)``: one positional
        parameter, required, with no optional parameter after it.

        Requirements: 2.1
        """
        with patched_use_case() as (use_case, _, _, _, _):
            assert isinstance(use_case, FacebookGetLaunchCampaignCreativesUseCase)

            with pytest.raises(TypeError):
                FacebookGetLaunchCampaignCreativesUseCase()

            with pytest.raises(TypeError):
                FacebookGetLaunchCampaignCreativesUseCase(
                    'user@example.com', 41,
                )

    # -- Zero side effects (Requirements 2.3, 11.2) -------------------------

    def test_no_repository_method_is_invoked_during_construction(self):
        """The four doubles record **zero** invocations after the construction:
        0 Strapi queries.

        0 outgoing HTTP requests are accredited by the ``deny_network``
        fixture, active in this case as in every other one of the suite; 0
        Redis accesses are accredited by the empty call record together with
        the five-key assertion above (no token is read and no client is
        stored) and by the absence of ``_get_decoded_access_token``.

        Requirements: 2.3, 11.2
        """
        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []
                assert double.method_calls == []

            assert account_repository.get_by_email.call_count == 0
            assert campaign_repository.get_by_id_brand_and_account.call_count == 0
            assert ad_set_repository\
                .get_by_campaign_and_brand_with_selected_ad_channels\
                .call_count == 0
            assert publish_repository\
                .get_by_campaign_id_and_channel_id.call_count == 0

    # -- No validation of ``user_id`` (Requirement 2.4) ---------------------

    @pytest.mark.parametrize('user_id', [None, ''], ids=['none', 'empty'])
    def test_falsy_user_id_constructs_without_validating_and_without_raising(
        self, user_id,
    ):
        """``user_id=None`` and ``user_id=''`` complete the construction.

        The absence of an account must surface as the
        ``DataNotFoundException`` of Requirement 3.3, raised by
        ``_get_account()`` during the execution, never at instantiation time.

        Requirements: 2.4
        """
        with patched_use_case(user_id=user_id) as (use_case, account_repository,
                                                   campaign_repository,
                                                   ad_set_repository,
                                                   publish_repository):
            assert use_case.user_id is user_id
            assert set(vars(use_case)) == set(self.EXPECTED_ATTRIBUTES)
            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []

    # -- ``NotAccessException`` is unreachable (Requirement 2.8) ------------

    def test_use_case_does_not_define_get_decoded_access_token(self):
        """The use case does **not** define ``_get_decoded_access_token``, so
        ``NotAccessException`` is unreachable from any execution path.

        The launch use case, which does define it, is asserted alongside as the
        control: the check is meaningful precisely because the method exists
        elsewhere in the very same module.

        Requirements: 2.8
        """
        assert hasattr(
            FacebookGetLaunchCampaignCreativesUseCase,
            '_get_decoded_access_token',
        ) is False

        with patched_use_case() as (use_case, _, _, _, _):
            assert hasattr(use_case, '_get_decoded_access_token') is False

        assert hasattr(
            FacebookLaunchCampaignUseCase, '_get_decoded_access_token',
        ) is True


# ---------------------------------------------------------------------------
# The additive ``AdSetRepository`` query (Requirements 9.1 - 9.6, 11.21)
# ---------------------------------------------------------------------------

#: The three query filter keys fixed literally by Requirement 9.2.
CAMPAIGN_FILTER_KEY = 'filters[funnel_flow_ref][campaign_ref][id][$eq]'
BRAND_FILTER_KEY = 'filters[funnel_flow_ref][campaign_ref][brand_ref][id][$eq]'
SELECTED_FILTER_KEY = 'filters[ads][ad_channels][selected][$eq]'

#: The three populate paths fixed by Requirement 9.3, in order.
POPULATE_PATHS = ['ads', 'ads.ad_channels', 'ads.ad_channels.channel_ref']

#: Response values that must yield ``None`` (Requirement 9.5): falsy response,
#: response without ``data``, ``data`` present but ``None``, and empty ``data``.
EMPTY_RESPONSES = (
    None,
    {},
    {'data': None},
    {'data': []},
)
EMPTY_RESPONSE_IDS = ('none', 'no-data-key', 'data-none', 'data-empty-list')


def _repository_with_get_double(return_value):
    """Build a **real** ``AdSetRepository`` whose ``get`` method, inherited
    from ``StrapiClient``, is replaced by a test double on the instance.

    The method under test is therefore the real one (not a double of itself),
    while the only collaborator that would touch the network is substituted.
    The double is installed on the instance, which is local to each test case,
    so nothing leaks into the class or into other cases. Combined with the
    ``deny_network`` fixture this accredits 0 real requests (Requirement
    11.21).

    Requirements: 9.1, 11.21
    """
    repository = AdSetRepository()
    repository.get = MagicMock(return_value=return_value)
    return repository, repository.get


def _repository_with_put_double(return_value):
    """Same as ``_repository_with_get_double`` for the write method ``put``,
    used only by the non-regression case of ``update`` (Requirement 9.6).

    Requirements: 9.6, 11.21
    """
    repository = AdSetRepository()
    repository.put = MagicMock(return_value=return_value)
    return repository, repository.put


class TestAdSetRepositoryQuery:
    """The new ``get_by_campaign_and_brand_with_selected_ad_channels``.

    Exercises the **real** method on a **real** ``AdSetRepository`` instance
    with the inherited ``get`` replaced by a double and 0 network requests, and
    guards the four pre-existing methods against regression.

    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 11.21
    """

    # -- Query parameters (Requirements 9.2, 9.3) ---------------------------

    def test_query_carries_the_three_filters_with_the_received_values(self):
        """The three filter keys of Requirement 9.2 hold the received values.

        Requirements: 9.1, 9.2
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        params = get_double.call_args[0][1]
        assert params[CAMPAIGN_FILTER_KEY] == 41
        assert params[BRAND_FILTER_KEY] == 7
        assert params[SELECTED_FILTER_KEY] == 'true'

    def test_selected_filter_value_is_the_string_true_and_not_the_boolean(self):
        """``selected`` is filtered with the string ``'true'``.

        ``requests`` serialises the boolean ``True`` as ``'True'`` with a
        capital letter, which the Strapi query parser does not coerce to a
        boolean, so the literal string is the only correct value.

        Requirements: 9.2
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        value = get_double.call_args[0][1][SELECTED_FILTER_KEY]
        assert isinstance(value, str)
        assert not isinstance(value, bool)
        assert value == 'true'

    def test_query_populates_the_three_paths_as_a_list(self):
        """``populate`` is the list of the three paths of Requirement 9.3.

        Requirements: 9.3
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        populate = get_double.call_args[0][1]['populate']
        assert isinstance(populate, list)
        assert populate == POPULATE_PATHS

    def test_first_positional_argument_is_the_ad_sets_content_type(self):
        """The endpoint is ``self.content_type``, whose value is ``ad-sets``.

        Requirements: 9.1, 9.6
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        assert repository.content_type == 'ad-sets'
        assert get_double.call_args[0][0] == repository.content_type
        assert get_double.call_args[0][0] == 'ad-sets'

    def test_single_query_is_emitted(self):
        """Exactly one read query reaches the Strapi client.

        Requirements: 9.1
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        assert get_double.call_count == 1

    def test_arguments_are_not_transformed(self):
        """``campaign_id`` and ``brand_id`` reach the filters untransformed.

        Requirements: 9.1, 9.2
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_campaign_and_brand_with_selected_ad_channels('41', '7')

        params = get_double.call_args[0][1]
        assert params[CAMPAIGN_FILTER_KEY] == '41'
        assert isinstance(params[CAMPAIGN_FILTER_KEY], str)
        assert params[BRAND_FILTER_KEY] == '7'
        assert isinstance(params[BRAND_FILTER_KEY], str)

    # -- Return value (Requirements 9.4, 9.5) -------------------------------

    def test_non_empty_response_is_returned_complete_including_meta(self):
        """A response with non-empty ``data`` is returned whole.

        This is the single shape difference against the four pre-existing
        methods and it is deliberate: the use case walks every ad-set of the
        campaign, so the ``meta`` key and the full ``data`` list must survive.

        Requirements: 9.4
        """
        response = make_ad_sets_response()
        expected = copy.deepcopy(response)
        repository, _ = _repository_with_get_double(response)

        result = repository.get_by_campaign_and_brand_with_selected_ad_channels(
            41, 7,
        )

        assert result == expected
        assert result is response
        assert 'meta' in result
        assert result['meta'] == expected['meta']
        assert isinstance(result['data'], list)
        assert len(result['data']) == 1

    def test_response_with_several_ad_sets_keeps_the_whole_data_list(self):
        """``data`` is returned as the complete list, not as its first item.

        Requirements: 9.4
        """
        response = make_ad_sets_response(
            ad_sets=[make_ad_set(ad_set_id=120), make_ad_set(ad_set_id=121)],
        )
        repository, _ = _repository_with_get_double(response)

        result = repository.get_by_campaign_and_brand_with_selected_ad_channels(
            41, 7,
        )

        assert [ad_set['id'] for ad_set in result['data']] == [120, 121]

    @pytest.mark.parametrize(
        'response', EMPTY_RESPONSES, ids=EMPTY_RESPONSE_IDS,
    )
    def test_empty_responses_return_none(self, response):
        """``None``, ``{}``, ``{'data': None}`` and ``{'data': []}`` → ``None``.

        Requirements: 9.5
        """
        repository, _ = _repository_with_get_double(response)

        result = repository.get_by_campaign_and_brand_with_selected_ad_channels(
            41, 7,
        )

        assert result is None

    def test_empty_response_still_emits_the_query(self):
        """The guard runs *after* the query, never instead of it.

        Requirements: 9.1, 9.5
        """
        repository, get_double = _repository_with_get_double({'data': []})

        repository.get_by_campaign_and_brand_with_selected_ad_channels(41, 7)

        assert get_double.call_count == 1

    # -- Non-regression of the four pre-existing methods (Requirement 9.6) --

    @pytest.mark.parametrize(
        'method_name, args',
        [
            ('get_by_id', (120,)),
            ('get_by_id_with_ads', (120,)),
            ('get_by_id_and_campaign_and_brand', (120, 41, 7)),
        ],
        ids=['get_by_id', 'get_by_id_with_ads',
             'get_by_id_and_campaign_and_brand'],
    )
    def test_existing_read_methods_still_return_the_first_record(
        self, method_name, args,
    ):
        """The three read methods keep returning ``response['data'][0]``.

        Requirements: 9.6
        """
        first = make_ad_set(ad_set_id=120)
        response = make_ad_sets_response(
            ad_sets=[first, make_ad_set(ad_set_id=121)],
        )
        repository, get_double = _repository_with_get_double(response)

        result = getattr(repository, method_name)(*args)

        assert result is response['data'][0]
        assert result['id'] == 120
        assert get_double.call_args[0][0] == 'ad-sets'

    @pytest.mark.parametrize(
        'response', EMPTY_RESPONSES, ids=EMPTY_RESPONSE_IDS,
    )
    @pytest.mark.parametrize(
        'method_name, args',
        [
            ('get_by_id', (120,)),
            ('get_by_id_with_ads', (120,)),
            ('get_by_id_and_campaign_and_brand', (120, 41, 7)),
        ],
        ids=['get_by_id', 'get_by_id_with_ads',
             'get_by_id_and_campaign_and_brand'],
    )
    def test_existing_read_methods_still_return_none_on_empty_responses(
        self, method_name, args, response,
    ):
        """The three read methods keep returning ``None`` in the same
        scenarios as the new one.

        Requirements: 9.5, 9.6
        """
        repository, _ = _repository_with_get_double(response)

        assert getattr(repository, method_name)(*args) is None

    def test_get_by_id_is_fury_still_populates_its_relations(self):
        """``get_by_id(is_fury=True)`` keeps its own ``populate`` list and the
        plain call keeps emitting none.

        Requirements: 9.6
        """
        repository, get_double = _repository_with_get_double(
            make_ad_sets_response()
        )

        repository.get_by_id(120)
        assert 'populate' not in get_double.call_args[0][1]

        repository.get_by_id(120, is_fury=True)
        populate = get_double.call_args[0][1]['populate']
        assert isinstance(populate, list)
        assert 'funnel_flow_ref.campaign_ref.brand_ref' in populate
        assert 'ads' in populate

    def test_update_still_returns_the_data_node_and_none(self):
        """``update`` is the write method of the class: its contract is
        ``response['data']`` (the whole node, not its first item) and ``None``
        for a falsy response or a response without ``data``. Asserted as it
        really behaves, since Requirement 9.6 demands 0 modified lines in it.

        Requirements: 9.6
        """
        data = {'id': 120, 'attributes': {'name': 'Ad Set A'}}
        repository, put_double = _repository_with_put_double({'data': data})

        result = repository.update(120, {'name': 'Ad Set A'})

        assert result is data
        assert put_double.call_args[0][0] == 'ad-sets/120'
        assert put_double.call_args[0][1] == {'data': {'name': 'Ad Set A'}}

        for empty in (None, {}, {'data': None}):
            repository, _ = _repository_with_put_double(empty)
            assert repository.update(120, {'name': 'Ad Set A'}) is None

    def test_content_type_and_constructor_are_untouched(self):
        """The constructor still sets ``content_type`` to ``ad-sets`` and the
        class still exposes the four pre-existing methods plus the new one.

        Requirements: 9.6
        """
        repository = AdSetRepository()

        assert repository.content_type == 'ad-sets'
        for method_name in (
            'get_by_id',
            'get_by_id_with_ads',
            'update',
            'get_by_id_and_campaign_and_brand',
            'get_by_campaign_and_brand_with_selected_ad_channels',
        ):
            assert callable(getattr(repository, method_name))


# ---------------------------------------------------------------------------
# The three defensive read helpers (Requirements 5.3, 5.4, 5.7, 6.1, 6.2)
#
# The three of them are declared ``@staticmethod`` precisely because they use
# no ``self``: they are pure utilities and the cases below invoke them
# **directly on the class**, with no instance and therefore no patched
# repository involved. ``deny_network`` stays active, so the absence of
# traffic is accredited here as well.
# ---------------------------------------------------------------------------

#: The three staticmethods under test, resolved once through the class so that
#: every case below invokes the very same object the production code uses.
_as_list = FacebookGetLaunchCampaignCreativesUseCase._as_list
_resolve_channel_id = FacebookGetLaunchCampaignCreativesUseCase._resolve_channel_id
_select_ad_channel = FacebookGetLaunchCampaignCreativesUseCase._select_ad_channel

#: Values that are **not** a ``dict`` and are used to degrade an intermediate
#: level of a nested path (Requirements 5.7, 6.2). ``None`` is listed apart in
#: each matrix, because an absent key and a key present with value ``None`` are
#: two different scenarios.
NON_DICT_VALUES = (0, 7, '', 'oops', [], ['x'], (), True)
NON_DICT_IDS = ('zero', 'int', 'empty-str', 'str', 'empty-list', 'list',
                'tuple', 'bool')

#: Values that are **not** a ``list`` and are used to degrade the final value
#: of a path walked by ``_as_list`` (Requirement 5.7).
NON_LIST_VALUES = (0, 7, '', 'oops', {}, {'0': 'x'}, (), ('x',), True)
NON_LIST_IDS = ('zero', 'int', 'empty-str', 'str', 'empty-dict', 'dict',
                'empty-tuple', 'tuple', 'bool')


def _ids(matrix):
    """Return the ``pytest`` ids of a ``(id, kwargs)`` matrix.

    The matrices below pair an id with the **keyword arguments** of a builder
    instead of with an already built structure, so the structure is rebuilt
    inside each case and no two cases ever share a container (Requirement
    11.4).

    Requirements: 11.4
    """
    return [case_id for case_id, _ in matrix]


class TestAsList:
    """``FacebookGetLaunchCampaignCreativesUseCase._as_list``.

    Requirements: 5.7
    """

    def test_is_a_staticmethod_invocable_without_an_instance(self):
        """``_as_list`` is a ``@staticmethod``: it is invocable on the class.

        Requirements: 5.7
        """
        assert isinstance(
            vars(FacebookGetLaunchCampaignCreativesUseCase)['_as_list'],
            staticmethod,
        )
        assert _as_list({'data': []}, 'data') == []

    # -- The complete path (Requirement 5.7) --------------------------------

    def test_complete_path_returns_the_very_list_found_at_its_end(self):
        """The list at the end of the path is returned by reference.

        Requirements: 5.7
        """
        ad_set = make_ad_set()

        result = _as_list(ad_set, 'attributes', 'ads', 'data')

        assert result is ad_set['attributes']['ads']['data']
        assert isinstance(result, list)
        assert len(result) == 1

    def test_complete_path_of_the_ad_channels_level_returns_its_list(self):
        """The same helper walks the second nested collection of the traversal.

        Requirements: 5.7
        """
        ad = make_ad()

        result = _as_list(ad, 'attributes', 'ad_channels', 'data')

        assert result is ad['attributes']['ad_channels']['data']
        assert [ad_channel['id'] for ad_channel in result] == [9001]

    def test_an_empty_list_at_the_end_of_the_path_is_returned_as_is(self):
        """An empty list is a legitimate value, not a degraded one.

        Requirements: 5.7
        """
        ad_set = make_ad_set(ads_data=[])

        result = _as_list(ad_set, 'attributes', 'ads', 'data')

        assert result == []
        assert result is ad_set['attributes']['ads']['data']

    def test_no_key_returns_the_node_itself_when_it_is_a_list(self):
        """With no key to walk, a list node is returned and anything else
        yields ``[]``.

        Requirements: 5.7
        """
        node = [make_ad()]

        assert _as_list(node) is node
        assert _as_list({'attributes': {}}) == []
        assert _as_list(None) == []

    # -- Degraded levels (Requirement 5.7) ---------------------------------

    #: Each case degrades **one** level of ``attributes.ads.data`` to an
    #: absent key, to ``None`` or to an unexpected type.
    DEGRADED_PATH = (
        ('attributes-absent', {'attributes': ABSENT}),
        ('attributes-none', {'attributes': None}),
        ('attributes-list', {'attributes': [{'ads': {'data': []}}]}),
        ('attributes-str', {'attributes': 'oops'}),
        ('attributes-int', {'attributes': 7}),
        ('ads-absent', {'ads': ABSENT}),
        ('ads-none', {'ads': None}),
        ('ads-list', {'ads': [{'data': []}]}),
        ('ads-str', {'ads': 'oops'}),
        ('ads-int', {'ads': 7}),
        ('data-absent', {'ads_data': ABSENT}),
        ('data-none', {'ads_data': None}),
        ('data-dict', {'ads_data': {'0': 'x'}}),
        ('data-str', {'ads_data': 'oops'}),
        ('data-int', {'ads_data': 7}),
        ('data-tuple', {'ads_data': ('x',)}),
    )

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_PATH], ids=_ids(DEGRADED_PATH),
    )
    def test_degraded_level_returns_empty_list_without_raising(self, kwargs):
        """Any level absent, ``None`` or of an unexpected type yields ``[]``.

        No ``AttributeError``, ``TypeError`` nor ``KeyError`` escapes: the
        helper is the collection counterpart of ``_resolve_channel_id``.

        Requirements: 5.7
        """
        ad_set = make_ad_set(**kwargs)

        result = _as_list(ad_set, 'attributes', 'ads', 'data')

        assert result == []
        assert isinstance(result, list)

    @pytest.mark.parametrize('node', NON_DICT_VALUES, ids=NON_DICT_IDS)
    def test_non_dict_root_node_returns_empty_list(self, node):
        """The root node itself is guarded like every other level.

        Requirements: 5.7
        """
        assert _as_list(node, 'attributes', 'ads', 'data') == []

    def test_none_root_node_returns_empty_list(self):
        """A ``None`` root node yields ``[]`` instead of raising.

        Requirements: 5.7
        """
        assert _as_list(None, 'attributes', 'ads', 'data') == []

    @pytest.mark.parametrize('value', NON_LIST_VALUES, ids=NON_LIST_IDS)
    def test_non_list_final_value_returns_empty_list(self, value):
        """A final value that is not a ``list`` yields ``[]``.

        Requirements: 5.7
        """
        ad_set = make_ad_set(ads_data=value)

        assert _as_list(ad_set, 'attributes', 'ads', 'data') == []

    def test_walking_a_path_does_not_modify_the_node(self):
        """The helper is read-only: the walked structure stays untouched.

        Requirements: 5.7, 5.8
        """
        ad_set = make_ad_set()
        pristine = copy.deepcopy(ad_set)

        _as_list(ad_set, 'attributes', 'ads', 'data')
        _as_list(ad_set, 'attributes', 'missing', 'data')

        assert ad_set == pristine


class TestChannelIdResolutionUnit:
    """``FacebookGetLaunchCampaignCreativesUseCase._resolve_channel_id``.

    Requirements: 6.1, 6.2
    """

    def test_is_a_staticmethod_invocable_without_an_instance(self):
        """``_resolve_channel_id`` is a ``@staticmethod``.

        Requirements: 6.1
        """
        assert isinstance(
            vars(FacebookGetLaunchCampaignCreativesUseCase)['_resolve_channel_id'],
            staticmethod,
        )
        assert _resolve_channel_id({}) == 0

    # -- The complete path (Requirement 6.1) -------------------------------

    def test_complete_path_returns_the_declared_id(self):
        """``attributes.channel_ref.data.id`` is returned verbatim.

        Requirements: 6.1
        """
        ad_channel = make_ad_channel(channel_ref_id=77)

        assert _resolve_channel_id(ad_channel) == 77

    def test_declared_id_zero_is_returned_as_a_legitimate_value(self):
        """A declared ``0`` is indistinguishable from the default by value, and
        that is precisely why the collection stage tracks resolution with a
        flag instead of with ``if not channel_id`` (decision D-3).

        Requirements: 6.1, 6.2
        """
        ad_channel = make_ad_channel(channel_ref_id=0)

        assert _resolve_channel_id(ad_channel) == 0

    # -- Degraded levels (Requirement 6.2) ---------------------------------

    #: Each case degrades **one** level of ``attributes.channel_ref.data.id``.
    #: ``id`` is covered for the absent case, the only one Requirement 6.2
    #: fixes for the leaf: the three intermediate keys are the ones the
    #: criterion also covers for ``None`` and for a non-``dict`` value.
    DEGRADED_PATH = (
        ('attributes-absent', {'attributes': ABSENT}),
        ('attributes-none', {'attributes': None}),
        ('attributes-list', {'attributes': [{'channel_ref': {'data': {'id': 2}}}]}),
        ('attributes-str', {'attributes': 'oops'}),
        ('attributes-int', {'attributes': 7}),
        ('channel_ref-absent', {'channel_ref': ABSENT}),
        ('channel_ref-none', {'channel_ref': None}),
        ('channel_ref-list', {'channel_ref': [{'data': {'id': 2}}]}),
        ('channel_ref-str', {'channel_ref': 'oops'}),
        ('channel_ref-int', {'channel_ref': 7}),
        ('data-absent', {'channel_ref_data': ABSENT}),
        ('data-none', {'channel_ref_data': None}),
        ('data-list', {'channel_ref_data': [{'id': 2}]}),
        ('data-str', {'channel_ref_data': 'oops'}),
        ('data-int', {'channel_ref_data': 7}),
        ('id-absent', {'channel_ref_id': ABSENT}),
    )

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_PATH], ids=_ids(DEGRADED_PATH),
    )
    def test_degraded_level_returns_zero_without_raising(self, kwargs):
        """Any degraded level yields the default ``0`` instead of raising.

        The failure is deliberately left to surface later, as the
        ``DataNotFoundException`` of Requirement 7.2 raised while resolving the
        campaign setup with ``channel_id == 0``.

        Requirements: 6.2
        """
        ad_channel = make_ad_channel(**kwargs)

        assert _resolve_channel_id(ad_channel) == 0

    @pytest.mark.parametrize('ad_channel', NON_DICT_VALUES, ids=NON_DICT_IDS)
    def test_non_dict_ad_channel_returns_zero(self, ad_channel):
        """The ad-channel itself is guarded like every other level.

        Requirements: 6.2
        """
        assert _resolve_channel_id(ad_channel) == 0

    def test_none_ad_channel_returns_zero(self):
        """A ``None`` ad-channel yields ``0`` instead of raising.

        Requirements: 6.2
        """
        assert _resolve_channel_id(None) == 0

    def test_resolution_does_not_modify_the_ad_channel(self):
        """The helper is read-only, including on the degraded paths.

        Requirements: 5.8, 6.2
        """
        ad_channel = make_ad_channel(channel_ref_id=77)
        pristine = copy.deepcopy(ad_channel)

        _resolve_channel_id(ad_channel)

        assert ad_channel == pristine

        degraded = make_ad_channel(channel_ref=ABSENT)
        degraded_pristine = copy.deepcopy(degraded)

        _resolve_channel_id(degraded)

        assert degraded == degraded_pristine


class TestAdChannelSelectionUnit:
    """``FacebookGetLaunchCampaignCreativesUseCase._select_ad_channel``.

    Applies the same selection criterion as the line
    ``next((ch for ch in ad_channels_data if ch['attributes'].get("selected")), None)``
    of ``MetaAdsPayloadBuilder.build_asset_feed_spec``.

    Requirements: 5.3, 5.4, 5.7
    """

    def test_is_a_staticmethod_invocable_without_an_instance(self):
        """``_select_ad_channel`` is a ``@staticmethod``.

        Requirements: 5.3
        """
        assert isinstance(
            vars(FacebookGetLaunchCampaignCreativesUseCase)['_select_ad_channel'],
            staticmethod,
        )
        assert _select_ad_channel({}) is None

    # -- Selection of the first truthy element (Requirement 5.3) -----------

    def test_returns_the_first_selected_element_when_several_are_selected(self):
        """With several selected elements the **first** one is returned, by
        reference and not by copy.

        Requirements: 5.3
        """
        second = make_ad_channel(ad_channel_id=9002, selected=True)
        ad = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, selected=False),
            second,
            make_ad_channel(ad_channel_id=9003, selected=True),
        ])

        result = _select_ad_channel(ad)

        assert result is second
        assert result['id'] == 9002

    def test_returns_the_single_selected_element(self):
        """The canonical ad of the builders has exactly one selected channel.

        Requirements: 5.3
        """
        ad = make_ad()

        result = _select_ad_channel(ad)

        assert result is ad['attributes']['ad_channels']['data'][0]
        assert result['id'] == 9001

    @pytest.mark.parametrize(
        'selected',
        [True, 1, -1, 'true', 'false', 'False', ['x'], {'a': 1}, 0.5],
        ids=['true', 'one', 'negative-int', 'str-true', 'str-false',
             'str-False', 'list', 'dict', 'float'],
    )
    def test_any_truthy_selected_value_selects(self, selected):
        """The criterion is truthiness, not equality against ``True``: the
        string ``'false'`` selects, exactly as the launch payload builder does.

        Requirements: 5.3
        """
        ad = make_ad(ad_channels_data=[make_ad_channel(selected=selected)])

        assert _select_ad_channel(ad) is ad['attributes']['ad_channels']['data'][0]

    # -- No element selected (Requirement 5.4) -----------------------------

    @pytest.mark.parametrize(
        'selected', [False, None, 0, '', ABSENT, 0.0, [], {}, ()],
        ids=['false', 'none', 'zero', 'empty-str', 'absent', 'zero-float',
             'empty-list', 'empty-dict', 'empty-tuple'],
    )
    def test_falsy_selected_value_does_not_select(self, selected):
        """Every falsy ``selected`` value —and its absence— leaves the ad
        without a selected ad-channel, which the traversal must skip without
        raising and without logging.

        Requirements: 5.3, 5.4
        """
        ad = make_ad(ad_channels_data=[make_ad_channel(selected=selected)])

        assert _select_ad_channel(ad) is None

    def test_returns_none_when_no_element_of_several_is_selected(self):
        """Several elements, none selected: ``None``.

        Requirements: 5.4
        """
        ad = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, selected=False),
            make_ad_channel(ad_channel_id=9002, selected=None),
            make_ad_channel(ad_channel_id=9003, selected=ABSENT),
        ])

        assert _select_ad_channel(ad) is None

    def test_returns_none_when_the_ad_channels_list_is_empty(self):
        """An empty ``ad_channels.data`` yields ``None``.

        Requirements: 5.4
        """
        ad = make_ad(ad_channels_data=[])

        assert _select_ad_channel(ad) is None

    # -- Degraded elements and degraded path (Requirement 5.7) -------------

    def test_element_without_attributes_is_treated_as_not_selected(self):
        """An element whose ``attributes`` key is absent is skipped, and a
        later selected element is still found.

        Requirements: 5.4, 5.7
        """
        selected = make_ad_channel(ad_channel_id=9002, selected=True)
        ad = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, attributes=ABSENT),
            selected,
        ])

        assert _select_ad_channel(ad) is selected

        only_degraded = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, attributes=ABSENT),
        ])

        assert _select_ad_channel(only_degraded) is None

    @pytest.mark.parametrize(
        'attributes',
        [None] + list(NON_DICT_VALUES),
        ids=['none'] + list(NON_DICT_IDS),
    )
    def test_element_with_non_dict_attributes_is_treated_as_not_selected(
        self, attributes,
    ):
        """An element whose ``attributes`` is ``None`` or is not a ``dict`` is
        skipped without raising, and does not hide a later selected element.

        Requirements: 5.4, 5.7
        """
        degraded = make_ad_channel(ad_channel_id=9001, attributes=attributes)

        assert _select_ad_channel(make_ad(ad_channels_data=[degraded])) is None

        selected = make_ad_channel(ad_channel_id=9002, selected=True)
        ad = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, attributes=attributes),
            selected,
        ])

        assert _select_ad_channel(ad) is selected

    @pytest.mark.parametrize(
        'element', [None, 0, 7, '', 'oops', [], ['x'], ()],
        ids=['none', 'zero', 'int', 'empty-str', 'str', 'empty-list', 'list',
             'tuple'],
    )
    def test_non_dict_element_of_the_list_is_skipped(self, element):
        """An element of ``ad_channels.data`` that is not a ``dict`` is skipped
        without raising.

        Requirements: 5.7
        """
        selected = make_ad_channel(ad_channel_id=9002, selected=True)
        ad = make_ad(ad_channels_data=[element, selected])

        assert _select_ad_channel(ad) is selected
        assert _select_ad_channel(make_ad(ad_channels_data=[element])) is None

    #: Each case degrades **one** level of ``attributes.ad_channels.data``.
    DEGRADED_PATH = (
        ('attributes-absent', {'attributes': ABSENT}),
        ('attributes-none', {'attributes': None}),
        ('attributes-list', {'attributes': [{'ad_channels': {'data': []}}]}),
        ('attributes-str', {'attributes': 'oops'}),
        ('ad_channels-absent', {'ad_channels': ABSENT}),
        ('ad_channels-none', {'ad_channels': None}),
        ('ad_channels-list', {'ad_channels': [{'data': []}]}),
        ('ad_channels-str', {'ad_channels': 'oops'}),
        ('data-absent', {'ad_channels_data': ABSENT}),
        ('data-none', {'ad_channels_data': None}),
        ('data-dict', {'ad_channels_data': {'0': 'x'}}),
        ('data-str', {'ad_channels_data': 'oops'}),
        ('data-int', {'ad_channels_data': 7}),
    )

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_PATH], ids=_ids(DEGRADED_PATH),
    )
    def test_degraded_path_returns_none_without_raising(self, kwargs):
        """A degraded intermediate structure is treated as an empty collection.

        Requirements: 5.7
        """
        ad = make_ad(**kwargs)

        assert _select_ad_channel(ad) is None

    @pytest.mark.parametrize('ad', NON_DICT_VALUES, ids=NON_DICT_IDS)
    def test_non_dict_ad_returns_none(self, ad):
        """The ad itself is guarded like every other level.

        Requirements: 5.7
        """
        assert _select_ad_channel(ad) is None

    def test_none_ad_returns_none(self):
        """A ``None`` ad yields ``None`` instead of raising.

        Requirements: 5.7
        """
        assert _select_ad_channel(None) is None

    def test_selection_does_not_modify_the_ad(self):
        """The helper is read-only: neither the ad nor its ad-channels change.

        Requirements: 5.7, 5.8
        """
        ad = make_ad(ad_channels_data=[
            make_ad_channel(ad_channel_id=9001, selected=False),
            make_ad_channel(ad_channel_id=9002, selected=True),
        ])
        pristine = copy.deepcopy(ad)

        _select_ad_channel(ad)

        assert ad == pristine


# ---------------------------------------------------------------------------
# The resolution of the Target_Campaign (Requirements 4.1 - 4.6)
#
# ``_get_campaign`` is invoked **directly** on the instance built by
# ``patched_use_case``, so the stage is exercised in isolation while
# ``execute()`` is still not implemented. ``deny_network`` stays active in
# every case, accrediting 0 outgoing requests.
# ---------------------------------------------------------------------------

#: Values returned by the repository that must **not** be accepted as a
#: resolved campaign (Requirement 4.2): a ``None``, a value that is not a
#: ``dict`` instance, and a ``dict`` with no keys.
INVALID_CAMPAIGNS = (None, {}) + NON_DICT_VALUES
INVALID_CAMPAIGN_IDS = ('none', 'empty-dict') + NON_DICT_IDS


class _RecordingDict(dict):
    """A ``dict`` that records every key lookup performed on it.

    Used to turn Requirement 4.5 ("of the resolved campaign record only
    ``attributes.name`` is read") into an observable fact: the ``attributes``
    node of the campaign is replaced by one of these, and the test asserts
    which keys the production code consulted on it. Only *key lookups* are
    recorded (``[]``, ``.get()`` and ``in``); iterating the node is not a
    single-attribute read and is irrelevant here.

    Requirements: 4.5, 11.4
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.consulted_keys = []

    def __getitem__(self, key):
        self.consulted_keys.append(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.consulted_keys.append(key)
        return super().get(key, default)

    def __contains__(self, key):
        self.consulted_keys.append(key)
        return super().__contains__(key)


def _campaign_with_recording_attributes(campaign_id=41, name='Campaña Primavera'):
    """Build a fresh campaign record whose ``attributes`` node is a
    ``_RecordingDict`` holding exactly ``name``, and return both.

    The recording list is cleared before returning, so it only reflects the
    lookups performed by the code under test.

    Requirements: 4.5, 11.4
    """
    attributes = _RecordingDict({'name': name})
    campaign = make_campaign(campaign_id=campaign_id, attributes=attributes)
    attributes.consulted_keys.clear()
    return campaign, attributes


class TestCampaignResolution:
    """``FacebookGetLaunchCampaignCreativesUseCase._get_campaign``.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    # -- The single query and its three arguments (Requirements 4.1, 2.6) ---

    def test_repository_is_invoked_once_with_the_three_positional_arguments(self):
        """A single ``get_by_id_brand_and_account(campaign_id, brand_id,
        parent_account)`` with the three values in that order.

        Requirements: 4.1
        """
        with patched_use_case() as (use_case, _, campaign_repository, _, _):
            use_case._get_campaign(41, 7, 3)

            campaign_repository.get_by_id_brand_and_account\
                .assert_called_once_with(41, 7, 3)

    def test_the_three_arguments_are_forwarded_positionally(self):
        """The three values travel as positional arguments, with no keyword
        argument and no fourth argument.

        Requirements: 4.1
        """
        with patched_use_case() as (use_case, _, campaign_repository, _, _):
            use_case._get_campaign(41, 7, 3)

            args, kwargs = campaign_repository.get_by_id_brand_and_account.call_args
            assert args == (41, 7, 3)
            assert kwargs == {}

    def test_string_campaign_id_and_brand_id_are_not_converted(self):
        """``campaign_id`` and ``brand_id`` of type ``str`` reach the
        repository as the very same strings: the use case performs no type
        conversion and no normalisation.

        Requirements: 2.6, 4.1, 11.19
        """
        campaign_id = '41'
        brand_id = '7'
        parent_account = '3'

        with patched_use_case() as (use_case, _, campaign_repository, _, _):
            use_case._get_campaign(campaign_id, brand_id, parent_account)

            campaign_repository.get_by_id_brand_and_account\
                .assert_called_once_with('41', '7', '3')

            args = campaign_repository.get_by_id_brand_and_account.call_args[0]
            assert args[0] is campaign_id
            assert args[1] is brand_id
            assert args[2] is parent_account
            assert [type(value) for value in args] == [str, str, str]

    def test_arguments_are_forwarded_by_identity_whatever_their_type(self):
        """Any value is forwarded untouched, by identity: the stage never
        coerces, validates nor reshapes its inputs.

        Requirements: 2.6, 4.1
        """
        campaign_id = object()
        brand_id = object()
        parent_account = object()

        with patched_use_case() as (use_case, _, campaign_repository, _, _):
            use_case._get_campaign(campaign_id, brand_id, parent_account)

            args = campaign_repository.get_by_id_brand_and_account.call_args[0]
            assert args[0] is campaign_id
            assert args[1] is brand_id
            assert args[2] is parent_account

    # -- A single query, and no query to ``brands`` (Requirements 4.4, 4.6) -

    def test_no_additional_query_is_issued_by_the_stage(self):
        """The stage issues exactly one call on the ``CampaignRepository``
        double —no second query to ``campaigns`` and no query at all to
        ``brands``, which is only consumed as a filter argument— and touches
        none of the other three doubles.

        The repository instance used is the one created by ``__init__``: the
        double yielded by ``patched_use_case`` is
        ``CampaignRepository.return_value``, so a new instantiation inside the
        stage would be visible as a call recorded on a different object.

        Requirements: 4.4, 4.6
        """
        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            use_case._get_campaign(41, 7, 3)

            assert campaign_repository.get_by_id_brand_and_account.call_count == 1
            assert campaign_repository.method_calls == [
                call.get_by_id_brand_and_account(41, 7, 3),
            ]
            assert use_case.campaign_repository is campaign_repository

            for double in (account_repository, ad_set_repository,
                           publish_repository):
                assert double.mock_calls == []

    # -- The three failure scenarios (Requirements 4.2, 4.3) ----------------

    @pytest.mark.parametrize(
        'returned', INVALID_CAMPAIGNS, ids=INVALID_CAMPAIGN_IDS,
    )
    def test_invalid_returned_value_raises_data_not_found(self, returned):
        """``None``, a non-``dict`` and a ``dict`` with no keys are all
        rejected: only a ``dict`` instance with at least one key resolves.

        Requirements: 4.1, 4.2
        """
        with patched_use_case(campaign=returned) as (use_case, _,
                                                     campaign_repository, _, _):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._get_campaign(41, 7, 3)

            assert_exception_type(exc_info, DataNotFoundException)
            campaign_repository.get_by_id_brand_and_account\
                .assert_called_once_with(41, 7, 3)

    def test_the_three_failure_shapes_share_an_identical_message(self):
        """The message of the three rejected shapes —``None``, a non-``dict``
        and an empty ``dict``— is identical, so the caller cannot tell them
        apart.

        Requirements: 4.2, 4.3
        """
        messages = []
        codes = []
        for returned in (None, 'oops', {}):
            with patched_use_case(campaign=returned) as (use_case, _, _, _, _):
                with pytest.raises(DataNotFoundException) as exc_info:
                    use_case._get_campaign(41, 7, 3)
                messages.append(str(exc_info.value))
                codes.append(exc_info.value.code)

        assert len(messages) == 3
        assert len(set(messages)) == 1
        assert len(set(codes)) == 1

    def test_the_three_failure_reasons_share_an_identical_message(self):
        """An unknown campaign, a campaign of another brand and a campaign of
        another account are indistinguishable from the outside.

        The three reasons reach the stage as the very same repository answer
        (nothing matched the combined filter), so the message must not
        interpolate the arguments: doing so would let a caller probe which of
        the three filters failed and therefore learn of the existence of
        campaigns of other accounts.

        Requirements: 4.2, 4.3
        """
        scenarios = (
            (41, 7, 3),      # unknown campaign
            (41, 999, 3),    # campaign of another brand
            (41, 7, 999),    # campaign of another account
        )

        messages = []
        for campaign_id, brand_id, parent_account in scenarios:
            with patched_use_case(campaign=None) as (use_case, _, _, _, _):
                with pytest.raises(DataNotFoundException) as exc_info:
                    use_case._get_campaign(campaign_id, brand_id, parent_account)
                messages.append(str(exc_info.value))

        assert len(messages) == 3
        assert len(set(messages)) == 1
        assert '999' not in messages[0]

    def test_failure_is_logged_with_the_three_values_used(self):
        """The failure is reported through ``logger.error`` mentioning the
        three values employed, which stay available for diagnosis even though
        the exception message does not carry them.

        Requirements: 4.2
        """
        with patched_use_case(campaign=None) as (use_case, _, _, _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(DataNotFoundException):
                    use_case._get_campaign(918273, 645342, 110099)

        assert mock_logger.error.call_count == 1
        message = str(mock_logger.error.call_args[0][0])
        assert '918273' in message
        assert '645342' in message
        assert '110099' in message

    # -- A resolved campaign (Requirements 4.1, 4.5) ------------------------

    def test_degenerate_campaign_resolves_without_raising(self):
        """A ``dict`` with a single key is a resolved campaign: the criterion
        of Requirement 4.1 is "``dict`` with at least one key", not "a record
        with an ``attributes`` node".

        Requirements: 4.1
        """
        degenerate = {'id': 1}

        with patched_use_case(campaign=degenerate) as (use_case, _, _, _, _):
            result = use_case._get_campaign(41, 7, 3)

        assert result is degenerate

    def test_canonical_campaign_is_returned_by_reference(self):
        """The record returned by the repository is handed back as is, without
        copying it and without reshaping it.

        Requirements: 4.1
        """
        campaign = make_campaign()
        pristine = copy.deepcopy(campaign)

        with patched_use_case(campaign=campaign) as (use_case, _, _, _, _):
            result = use_case._get_campaign(41, 7, 3)

        assert result is campaign
        assert campaign == pristine

    def test_no_attribute_other_than_name_is_read_from_the_resolved_campaign(self):
        """A record with ``attributes.name`` resolves and no other attribute is
        read.

        Verified with an instrumented ``dict`` in place of the ``attributes``
        node, which records every key consulted on it. At this stage the
        expected record is *empty*: resolving the campaign only checks the
        shape of the record, and ``name`` is read later, when the ``campaign``
        block of the query result is composed. The assertion is therefore
        written as "no key outside ``{'name'}``", which is what Requirement 4.5
        fixes, and the final lines prove the instrumentation is live rather
        than silently recording nothing.

        Requirements: 4.1, 4.5
        """
        campaign, attributes = _campaign_with_recording_attributes()

        with patched_use_case(campaign=campaign) as (use_case, _, _, _, _):
            result = use_case._get_campaign(41, 7, 3)

        assert result is campaign
        assert set(attributes.consulted_keys) - {'name'} == set()
        assert attributes.consulted_keys == []

        assert result['attributes'].get('name') == 'Campaña Primavera'
        assert attributes.consulted_keys == ['name']


# ---------------------------------------------------------------------------
# The collection of the Published_Creatives
# (Requirements 5.1 - 5.9, 6.1, 6.2, 6.4, 6.5)
#
# ``_collect_published_creatives`` is invoked **directly** on the instance
# built by ``patched_use_case``, so the stage is exercised in isolation while
# ``execute()`` is still not implemented. The single collaborator it touches is
# the ``AdSetRepository`` double, whose return value each case pre-configures
# through the ``ad_sets_response`` argument of the context manager;
# ``deny_network`` stays active, accrediting 0 outgoing requests.
# ---------------------------------------------------------------------------

#: The single repository method the stage invokes (Requirement 5.1).
AD_SETS_QUERY = 'get_by_campaign_and_brand_with_selected_ad_channels'


def _query_double(ad_set_repository):
    """Return the double of the only ``AdSetRepository`` method the stage
    invokes, so the assertions read against a single named target.

    Requirements: 5.1, 11.4
    """
    return getattr(ad_set_repository, AD_SETS_QUERY)


def _ad_with_channel(ad_id=501, ad_channel_id=9001, selected=True,
                     channel_ref_id=2, channel_creative=_DEFAULT,
                     **ad_channel_kwargs):
    """Build a fresh element of ``ads.data`` holding exactly one ad-channel.

    By default the ad-channel carries a fresh Published_Creative whose ``id``
    equals ``ad_channel_id``, so a descriptor list can be identified by value
    in the order assertions. ``channel_creative`` and every
    ``make_ad_channel`` keyword stay available for the degraded scenarios.

    Requirements: 5.3, 5.5, 5.7, 11.4
    """
    if channel_creative is _DEFAULT:
        channel_creative = make_dynamic_creative(
            creative_id=ad_channel_id, ad_id=ad_id, ad_channel_id=ad_channel_id,
        )
    return make_ad(
        ad_id=ad_id,
        ad_channels_data=[
            make_ad_channel(
                ad_channel_id=ad_channel_id,
                selected=selected,
                channel_ref_id=channel_ref_id,
                channel_creative=channel_creative,
                **ad_channel_kwargs
            ),
        ],
    )


def _healthy_response(ad_channel_id=9001):
    """Build a fresh canonical response yielding exactly one descriptor.

    Requirements: 5.1, 11.4
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(ad_set_id=120, ads_data=[
            _ad_with_channel(ad_id=501, ad_channel_id=ad_channel_id),
        ]),
    ])


def _adchannel_ids(descriptors):
    """Return the ``adchannel_id`` of each descriptor, preserving order.

    Requirements: 7.5, 11.4
    """
    return [descriptor['adchannel_id'] for descriptor in descriptors]


def _creative_ids(descriptors):
    """Return the ``id`` of the creative of each descriptor, preserving order.

    Requirements: 7.5, 11.4
    """
    return [descriptor['creative']['id'] for descriptor in descriptors]


#: Responses the stage must reject with ``DataNotFoundException`` (Requirement
#: 5.2). Paired as ``(id, make_ad_sets_response kwargs)`` so the structure is
#: rebuilt inside each case (Requirement 11.4): ``envelope`` returns the value
#: verbatim (``None`` and the non-``dict`` shapes) and ``ad_sets`` degrades the
#: ``data`` key (absent, ``None``, empty list and non-``list``).
INVALID_AD_SETS_RESPONSES = (
    ('none', {'envelope': None}),
    ('non-dict-str', {'envelope': 'oops'}),
    ('non-dict-int', {'envelope': 7}),
    ('non-dict-list', {'envelope': ['x']}),
    ('non-dict-tuple', {'envelope': ()}),
    ('empty-dict', {'ad_sets': ABSENT, 'include_meta': False}),
    ('data-absent', {'ad_sets': ABSENT}),
    ('data-none', {'ad_sets': None}),
    ('data-empty-list', {'ad_sets': []}),
    ('data-dict', {'ad_sets': {'0': 'x'}}),
    ('data-str', {'ad_sets': 'oops'}),
    ('data-int', {'ad_sets': 7}),
    ('data-tuple', {'ad_sets': ('x',)}),
)

#: Each case degrades **one** level of the ad-set side of the traversal
#: (``attributes``, ``ads``, ``ads.data``) to an absent key, to ``None`` and to
#: an unexpected type, plus the legitimate empty list (Requirement 5.7).
DEGRADED_AD_SETS = (
    ('attributes-absent', {'attributes': ABSENT}),
    ('attributes-none', {'attributes': None}),
    ('attributes-list', {'attributes': [{'ads': {'data': []}}]}),
    ('attributes-str', {'attributes': 'oops'}),
    ('attributes-int', {'attributes': 7}),
    ('ads-absent', {'ads': ABSENT}),
    ('ads-none', {'ads': None}),
    ('ads-list', {'ads': [{'data': []}]}),
    ('ads-str', {'ads': 'oops'}),
    ('ads-int', {'ads': 7}),
    ('ads-data-absent', {'ads_data': ABSENT}),
    ('ads-data-none', {'ads_data': None}),
    ('ads-data-dict', {'ads_data': {'0': 'x'}}),
    ('ads-data-str', {'ads_data': 'oops'}),
    ('ads-data-int', {'ads_data': 7}),
    ('ads-data-empty-list', {'ads_data': []}),
)

#: Each case degrades **one** level of the ad side of the traversal
#: (``attributes``, ``ad_channels``, ``ad_channels.data``) the same way
#: (Requirement 5.7).
DEGRADED_ADS = (
    ('attributes-absent', {'attributes': ABSENT}),
    ('attributes-none', {'attributes': None}),
    ('attributes-list', {'attributes': [{'ad_channels': {'data': []}}]}),
    ('attributes-str', {'attributes': 'oops'}),
    ('attributes-int', {'attributes': 7}),
    ('ad_channels-absent', {'ad_channels': ABSENT}),
    ('ad_channels-none', {'ad_channels': None}),
    ('ad_channels-list', {'ad_channels': [{'data': []}]}),
    ('ad_channels-str', {'ad_channels': 'oops'}),
    ('ad_channels-int', {'ad_channels': 7}),
    ('ad_channels-data-absent', {'ad_channels_data': ABSENT}),
    ('ad_channels-data-none', {'ad_channels_data': None}),
    ('ad_channels-data-dict', {'ad_channels_data': {'0': 'x'}}),
    ('ad_channels-data-str', {'ad_channels_data': 'oops'}),
    ('ad_channels-data-int', {'ad_channels_data': 7}),
    ('ad_channels-data-empty-list', {'ad_channels_data': []}),
)

#: Values of ``channel_creative`` that make an ad-channel unusable: absent,
#: ``None``, not a ``dict`` and an empty ``dict`` (Requirement 5.5).
UNUSABLE_CHANNEL_CREATIVES = (ABSENT, None, {}) + NON_DICT_VALUES
UNUSABLE_CHANNEL_CREATIVE_IDS = (
    ('absent', 'none', 'empty-dict') + NON_DICT_IDS
)

#: Values of the ``ads`` key of a Published_Creative that make it unusable:
#: absent, not a ``list`` and an empty ``list`` (Requirement 5.6). ``None`` is
#: part of ``NON_LIST_VALUES``' sibling case and is listed explicitly.
UNUSABLE_CREATIVE_ADS = (ABSENT, None, []) + NON_LIST_VALUES
UNUSABLE_CREATIVE_ADS_IDS = ('absent', 'none', 'empty-list') + NON_LIST_IDS


class TestPublishedCreativesCollection:
    """``FacebookGetLaunchCampaignCreativesUseCase._collect_published_creatives``.

    Returns a two element tuple: the descriptors of the usable Published
    Creatives, in the order of Requirement 7.5, and the Channel_ID of the
    **first** selected ad-channel of the traversal.

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 6.1, 6.2, 6.4,
    6.5
    """

    # -- The single query and its two arguments (Requirement 5.1) -----------

    def test_repository_is_invoked_once_with_the_two_positional_arguments(self):
        """A single query with ``campaign_id`` and ``brand_id`` in that order.

        Requirements: 5.1
        """
        with patched_use_case(ad_sets_response=_healthy_response()) as (
                use_case, _, _, ad_set_repository, _):
            use_case._collect_published_creatives(41, 7)

            _query_double(ad_set_repository).assert_called_once_with(41, 7)

            args, kwargs = _query_double(ad_set_repository).call_args
            assert args == (41, 7)
            assert kwargs == {}

    def test_string_arguments_are_not_converted(self):
        """``campaign_id`` and ``brand_id`` of type ``str`` reach the
        repository as the very same strings: no type conversion, no
        normalisation.

        Requirements: 2.6, 5.1
        """
        campaign_id = '41'
        brand_id = '7'

        with patched_use_case(ad_sets_response=_healthy_response()) as (
                use_case, _, _, ad_set_repository, _):
            use_case._collect_published_creatives(campaign_id, brand_id)

            _query_double(ad_set_repository).assert_called_once_with('41', '7')

            args = _query_double(ad_set_repository).call_args[0]
            assert args[0] is campaign_id
            assert args[1] is brand_id
            assert [type(value) for value in args] == [str, str]

    def test_arguments_are_forwarded_by_identity_whatever_their_type(self):
        """Any value is forwarded untouched, by identity.

        Requirements: 2.6, 5.1
        """
        campaign_id = object()
        brand_id = object()

        with patched_use_case(ad_sets_response=_healthy_response()) as (
                use_case, _, _, ad_set_repository, _):
            use_case._collect_published_creatives(campaign_id, brand_id)

            args = _query_double(ad_set_repository).call_args[0]
            assert args[0] is campaign_id
            assert args[1] is brand_id

    def test_no_other_repository_is_touched_by_the_stage(self):
        """One call on the ``AdSetRepository`` double and none on the other
        three: 1 query to ``ad-sets`` and 0 queries to ``ads``,
        ``ad-channels`` and ``channel-v2s``.

        The instance used is the one created by ``__init__``, since the double
        yielded by ``patched_use_case`` is ``AdSetRepository.return_value``: a
        new instantiation inside the stage would record its call on a different
        object.

        Requirements: 5.1, 5.10, 6.3
        """
        with patched_use_case(ad_sets_response=_healthy_response()) as (
                use_case, account_repository, campaign_repository,
                ad_set_repository, publish_repository):
            use_case._collect_published_creatives(41, 7)

            assert ad_set_repository.method_calls == [
                getattr(call, AD_SETS_QUERY)(41, 7),
            ]
            assert use_case.ad_set_repository is ad_set_repository

            for double in (account_repository, campaign_repository,
                           publish_repository):
                assert double.mock_calls == []

    # -- Invalid responses (Requirement 5.2) --------------------------------

    @pytest.mark.parametrize(
        'kwargs',
        [kwargs for _, kwargs in INVALID_AD_SETS_RESPONSES],
        ids=_ids(INVALID_AD_SETS_RESPONSES),
    )
    def test_invalid_response_raises_data_not_found(self, kwargs):
        """``None``, a non-``dict``, ``{}``, ``{'data': None}``,
        ``{'data': []}`` and a ``data`` that is not a ``list`` are all
        rejected.

        Requirements: 5.2
        """
        response = make_ad_sets_response(**kwargs)

        with patched_use_case(ad_sets_response=response) as (
                use_case, _, _, ad_set_repository, _):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._collect_published_creatives(41, 7)

            assert_exception_type(exc_info, DataNotFoundException)
            _query_double(ad_set_repository).assert_called_once_with(41, 7)

    def test_invalid_response_is_logged_with_both_values(self):
        """The rejection is reported through ``logger.error`` mentioning
        ``campaign_id`` and ``brand_id``.

        Requirements: 5.2
        """
        with patched_use_case(ad_sets_response=None) as (use_case, _, _, _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(DataNotFoundException):
                    use_case._collect_published_creatives(918273, 645342)

        assert mock_logger.error.call_count == 1
        message = str(mock_logger.error.call_args[0][0])
        assert '918273' in message
        assert '645342' in message

    def test_a_single_ad_set_with_data_present_is_accepted(self):
        """A ``data`` list with one usable ad-set is not an invalid response.

        Requirements: 5.2
        """
        with patched_use_case(ad_sets_response=_healthy_response()) as (
                use_case, _, _, _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert len(descriptors) == 1
        assert channel_id == 2

    # -- Order and cardinality (Requirement 7.5) ----------------------------

    def test_two_ad_sets_with_two_ads_each_yield_four_descriptors_in_order(self):
        """Four descriptors, in ad-set appearance order and, within each
        ad-set, in ad order.

        Requirements: 5.3, 7.5
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001),
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=503, ad_channel_id=9003),
                _ad_with_channel(ad_id=504, ad_channel_id=9004),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert len(descriptors) == 4
        assert _adchannel_ids(descriptors) == [9001, 9002, 9003, 9004]
        assert _creative_ids(descriptors) == [9001, 9002, 9003, 9004]

    def test_reversed_ad_set_order_reverses_the_descriptor_order(self):
        """The order is the one of the response, not a sorted one: the same
        four records in the opposite order produce the opposite descriptor
        order.

        Requirements: 7.5
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=504, ad_channel_id=9004),
                _ad_with_channel(ad_id=503, ad_channel_id=9003),
            ]),
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
                _ad_with_channel(ad_id=501, ad_channel_id=9001),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9004, 9003, 9002, 9001]

    def test_descriptor_holds_a_reference_to_the_stored_creative(self):
        """The ``creative`` of a descriptor is the very stored
        ``channel_creative`` dict, not a copy (decision D-7), and
        ``adchannel_id`` is the ``id`` of the ad-channel record.

        Requirements: 5.8, 8.6
        """
        response = _healthy_response(ad_channel_id=9001)
        stored = (
            response['data'][0]['attributes']['ads']['data'][0]
            ['attributes']['ad_channels']['data'][0]
            ['attributes']['channel_creative']
        )

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert len(descriptors) == 1
        assert descriptors[0]['creative'] is stored
        assert descriptors[0]['adchannel_id'] == 9001
        assert set(descriptors[0]) == {'creative', 'adchannel_id'}

    def test_only_the_selected_ad_channel_of_each_ad_produces_a_descriptor(self):
        """An ad with several ad-channels contributes exactly one descriptor,
        the one of its first selected ad-channel, and an ad with none
        contributes zero, without raising and without logging.

        Requirements: 5.3, 5.4
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                make_ad(ad_id=501, ad_channels_data=[
                    make_ad_channel(ad_channel_id=9001, selected=False),
                    make_ad_channel(
                        ad_channel_id=9002, selected=True,
                        channel_creative=make_dynamic_creative(creative_id=9002),
                    ),
                    make_ad_channel(
                        ad_channel_id=9003, selected=True,
                        channel_creative=make_dynamic_creative(creative_id=9003),
                    ),
                ]),
                make_ad(ad_id=502, ad_channels_data=[
                    make_ad_channel(ad_channel_id=9004, selected=False),
                    make_ad_channel(ad_channel_id=9005, selected=None),
                ]),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

    # -- The Channel_ID (Requirements 6.1, 6.2, 6.4, 6.5) -------------------

    def test_channel_id_is_the_one_of_the_first_selected_ad_channel(self):
        """The Channel_ID is the value declared by the **first** selected
        ad-channel of the traversal.

        Requirements: 6.1, 6.4
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=77),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 77
        assert len(descriptors) == 2

    def test_degraded_first_ad_channel_keeps_zero_even_if_a_later_one_declares_a_value(self):
        """A first selected ad-channel with a degraded ``channel_ref``
        legitimately resolves ``0``, and that ``0`` is **kept** even when a
        later selected ad-channel declares a valid value (decision D-3).

        Keeping it is what lets the failure surface as the
        ``DataNotFoundException`` of Requirement 7.2 while resolving the
        campaign setup, instead of being silently repaired with the value of
        another ad-channel.

        Requirements: 6.2, 6.4
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref=ABSENT),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=88),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 0
        assert _adchannel_ids(descriptors) == [9001, 9002]

    def test_declared_zero_in_the_first_ad_channel_is_kept_as_well(self):
        """A first selected ad-channel declaring ``0`` is indistinguishable by
        value from the default, and the flag keeps it just the same.

        Requirements: 6.1, 6.2, 6.4
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=0),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=88),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            _, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 0

    def test_mismatching_later_ad_channel_is_warned_without_altering_the_value(self):
        """A later selected ad-channel declaring a different value produces a
        ``logger.warning`` with **both** values, and the returned Channel_ID
        stays the one of the first ad-channel.

        Requirements: 6.5
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77),
            ]),
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=88),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                descriptors, channel_id = use_case._collect_published_creatives(
                    41, 7,
                )

        assert channel_id == 77
        assert _adchannel_ids(descriptors) == [9001, 9002]

        assert mock_logger.warning.call_count == 1
        message = str(mock_logger.warning.call_args[0][0])
        assert '77' in message
        assert '88' in message

    def test_mismatch_of_a_degraded_later_ad_channel_is_warned_too(self):
        """A later selected ad-channel whose ``channel_ref`` is degraded
        resolves ``0``, which differs from the already resolved value and is
        therefore warned, again without altering the returned Channel_ID.

        Requirements: 6.2, 6.5
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_data=None),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                _, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 77
        assert mock_logger.warning.call_count == 1

    def test_matching_later_ad_channels_produce_no_warning(self):
        """Several selected ad-channels declaring the same value are not a
        discrepancy: no warning is emitted.

        Requirements: 6.4, 6.5
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=77),
            ]),
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=503, ad_channel_id=9003,
                                 channel_ref_id=77),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                _, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 77
        assert mock_logger.warning.call_count == 0

    def test_channel_id_comes_from_the_first_selected_ad_channel_even_if_unusable(self):
        """The Channel_ID is resolved from the first **selected** ad-channel of
        the traversal, whether or not its ``channel_creative`` turns out to be
        usable: the ad-channel is skipped as a creative source, not as the
        Channel_ID source.

        Requirements: 6.1, 6.4
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77, channel_creative=None),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=88),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert channel_id == 77
        assert _adchannel_ids(descriptors) == [9002]

    # -- Degraded ``channel_creative`` (Requirement 5.5) --------------------

    @pytest.mark.parametrize(
        'channel_creative',
        UNUSABLE_CHANNEL_CREATIVES,
        ids=UNUSABLE_CHANNEL_CREATIVE_IDS,
    )
    def test_unusable_channel_creative_is_warned_and_skipped(
        self, channel_creative,
    ):
        """An absent, ``None``, non-``dict`` or empty ``channel_creative``
        produces a ``logger.warning`` with the ``id`` of its ad-channel, is
        skipped, and the traversal continues with the remaining ads.

        Requirements: 5.5, 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_creative=channel_creative),
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                descriptors, channel_id = use_case._collect_published_creatives(
                    41, 7,
                )

        assert _adchannel_ids(descriptors) == [9002]
        assert channel_id == 2
        assert mock_logger.warning.call_count == 1
        assert '9001' in str(mock_logger.warning.call_args[0][0])

    # -- Published_Creative without usable ``ads`` (Requirement 5.6) --------

    @pytest.mark.parametrize(
        'ads', UNUSABLE_CREATIVE_ADS, ids=UNUSABLE_CREATIVE_ADS_IDS,
    )
    def test_creative_without_usable_ads_is_warned_and_skipped(self, ads):
        """A Published_Creative whose ``ads`` key is absent, is not a ``list``
        or is an empty ``list`` produces a ``logger.warning``, is skipped, and
        the traversal continues.

        Requirements: 5.6
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(
                    ad_id=501, ad_channel_id=9001,
                    channel_creative=make_dynamic_creative(
                        creative_id=9001, ads=ads,
                    ),
                ),
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert mock_logger.warning.call_count == 1
        assert '9001' in str(mock_logger.warning.call_args[0][0])

    def test_creative_with_a_non_empty_ads_list_is_kept(self):
        """A single element ``ads`` list —the shape the pre-check flow
        persists— is usable.

        Requirements: 5.6
        """
        response = _healthy_response()

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert len(descriptors) == 1
        assert isinstance(descriptors[0]['creative']['ads'], list)
        assert len(descriptors[0]['creative']['ads']) == 1

    # -- Degraded intermediate structures (Requirement 5.7) -----------------

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_AD_SETS],
        ids=_ids(DEGRADED_AD_SETS),
    )
    def test_degraded_ad_set_is_treated_as_empty_without_raising(self, kwargs):
        """An ad-set whose ``attributes``, ``ads`` or ``ads.data`` is absent,
        ``None`` or of an unexpected type is treated as an empty collection: no
        ``AttributeError``, ``TypeError`` nor ``KeyError`` escapes and the
        healthy ad-set still yields its descriptor.

        Requirements: 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, **kwargs),
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert channel_id == 2

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_ADS],
        ids=_ids(DEGRADED_ADS),
    )
    def test_degraded_ad_is_treated_as_empty_without_raising(self, kwargs):
        """An ad whose ``attributes``, ``ad_channels`` or ``ad_channels.data``
        is absent, ``None`` or of an unexpected type is skipped without
        raising, and the healthy ad of the same ad-set still yields its
        descriptor.

        Requirements: 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                make_ad(ad_id=501, **kwargs),
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert channel_id == 2

    @pytest.mark.parametrize(
        'attributes', [ABSENT, None] + list(NON_DICT_VALUES),
        ids=['absent', 'none'] + list(NON_DICT_IDS),
    )
    def test_ad_channel_element_without_usable_attributes_is_skipped(
        self, attributes,
    ):
        """An element of ``ad_channels.data`` without ``attributes``, or whose
        ``attributes`` is ``None`` or of an unexpected type, is treated as not
        selected: it neither raises nor hides a later selected element.

        Requirements: 5.4, 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                make_ad(ad_id=501, ad_channels_data=[
                    make_ad_channel(ad_channel_id=9001, attributes=attributes),
                    make_ad_channel(
                        ad_channel_id=9002, selected=True, channel_ref_id=77,
                        channel_creative=make_dynamic_creative(creative_id=9002),
                    ),
                ]),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert channel_id == 77

    @pytest.mark.parametrize(
        'element', [None, 0, 7, '', 'oops', [], ['x'], ()],
        ids=['none', 'zero', 'int', 'empty-str', 'str', 'empty-list', 'list',
             'tuple'],
    )
    def test_non_dict_elements_of_the_three_levels_are_skipped(self, element):
        """A non-``dict`` element of the ``data`` list of ad-sets, of ``ads`` or
        of ``ad_channels`` is skipped without raising.

        Requirements: 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            element,
            make_ad_set(ad_set_id=120, ads_data=[element]),
            make_ad_set(ad_set_id=121, ads_data=[
                make_ad(ad_id=501, ad_channels_data=[element]),
            ]),
            make_ad_set(ad_set_id=122, ads_data=[
                _ad_with_channel(ad_id=502, ad_channel_id=9002),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9002]
        assert channel_id == 2

    def test_every_degradation_combined_still_yields_the_healthy_descriptors(self):
        """All the degradations at once, in a single response: the traversal
        completes and returns exactly the descriptors of the healthy
        ad-channels.

        Requirements: 5.4, 5.5, 5.6, 5.7
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, attributes=None),
            make_ad_set(ad_set_id=121, ads='oops'),
            make_ad_set(ad_set_id=122, ads_data=None),
            make_ad_set(ad_set_id=123, ads_data=[
                make_ad(ad_id=501, ad_channels=ABSENT),
                make_ad(ad_id=502, ad_channels_data=7),
                make_ad(ad_id=503, ad_channels_data=[
                    make_ad_channel(ad_channel_id=9001, selected=False),
                ]),
                _ad_with_channel(ad_id=504, ad_channel_id=9002,
                                 channel_creative=ABSENT),
                _ad_with_channel(
                    ad_id=505, ad_channel_id=9003,
                    channel_creative=make_dynamic_creative(
                        creative_id=9003, ads=[],
                    ),
                ),
                _ad_with_channel(ad_id=506, ad_channel_id=9004),
            ]),
            make_ad_set(ad_set_id=124, ads_data=[
                _ad_with_channel(ad_id=507, ad_channel_id=9005),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9004, 9005]
        assert channel_id == 2

    # -- Zero descriptors after the traversal (Requirement 5.9) -------------

    def test_no_selected_ad_channel_at_all_raises_data_not_found(self):
        """A non-empty response whose ads have no selected ad-channel yields 0
        descriptors, which is reported as ``DataNotFoundException`` instead of
        as an empty creatives list.

        Requirements: 5.4, 5.9
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                make_ad(ad_id=501, ad_channels_data=[
                    make_ad_channel(ad_channel_id=9001, selected=False),
                ]),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._collect_published_creatives(41, 7)

            assert_exception_type(exc_info, DataNotFoundException)

    def test_every_creative_unusable_raises_data_not_found(self):
        """Selected ad-channels whose creatives are all unusable also yield 0
        descriptors.

        Requirements: 5.5, 5.6, 5.9
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_creative=None),
                _ad_with_channel(
                    ad_id=502, ad_channel_id=9002,
                    channel_creative=make_dynamic_creative(
                        creative_id=9002, ads=ABSENT,
                    ),
                ),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._collect_published_creatives(41, 7)

            assert_exception_type(exc_info, DataNotFoundException)

    def test_every_ad_set_degraded_raises_data_not_found(self):
        """A response whose ad-sets are all degraded yields 0 descriptors.

        Requirements: 5.7, 5.9
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, attributes=ABSENT),
            make_ad_set(ad_set_id=121, ads_data=None),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._collect_published_creatives(41, 7)

            assert_exception_type(exc_info, DataNotFoundException)

    def test_zero_descriptors_is_logged_with_both_values(self):
        """The empty outcome is reported through ``logger.error`` mentioning
        ``campaign_id`` and ``brand_id``.

        Requirements: 5.9
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                make_ad(ad_id=501, ad_channels_data=[]),
            ]),
        ])

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(DataNotFoundException):
                    use_case._collect_published_creatives(918273, 645342)

        assert mock_logger.error.call_count == 1
        message = str(mock_logger.error.call_args[0][0])
        assert '918273' in message
        assert '645342' in message

    # -- Read-only traversal (Requirement 5.8) ------------------------------

    def test_traversal_leaves_the_whole_response_untouched(self):
        """The complete fixture response equals its initial ``deepcopy`` after
        the invocation: no statement of the traversal assigns over the ad-sets,
        the ads, the ad-channels nor the creatives.

        Requirements: 5.8
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_channel(ad_id=501, ad_channel_id=9001,
                                 channel_ref_id=77),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_ref_id=88),
            ]),
            make_ad_set(ad_set_id=121, ads_data=[
                _ad_with_channel(ad_id=503, ad_channel_id=9003),
            ]),
        ])
        pristine = copy.deepcopy(response)

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, _ = use_case._collect_published_creatives(41, 7)

        assert len(descriptors) == 3
        assert response == pristine

    def test_traversal_of_a_degraded_response_is_read_only_too(self):
        """The same holds along the degraded paths, where the defensive reads
        use ``.get()`` with a default and never insert a missing key.

        Requirements: 5.7, 5.8
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, attributes=ABSENT),
            make_ad_set(ad_set_id=121, ads_data=[
                make_ad(ad_id=501, ad_channels=None),
                _ad_with_channel(ad_id=502, ad_channel_id=9002,
                                 channel_creative=ABSENT,
                                 channel_ref=ABSENT),
                _ad_with_channel(ad_id=503, ad_channel_id=9003,
                                 channel_ref=ABSENT),
            ]),
        ])
        pristine = copy.deepcopy(response)

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            descriptors, channel_id = use_case._collect_published_creatives(41, 7)

        assert _adchannel_ids(descriptors) == [9003]
        assert channel_id == 0
        assert response == pristine

    def test_invalid_response_is_left_untouched_as_well(self):
        """The rejected response is not modified either: the guard only reads
        its ``data`` key.

        Requirements: 5.2, 5.8
        """
        response = make_ad_sets_response(ad_sets=[])
        pristine = copy.deepcopy(response)

        with patched_use_case(ad_sets_response=response) as (use_case, _, _,
                                                            _, _):
            with pytest.raises(DataNotFoundException):
                use_case._collect_published_creatives(41, 7)

        assert response == pristine

# ---------------------------------------------------------------------------
# The Campaign_Setup stage (Requirements 7.1, 7.2, 7.4, 7.7, 8.5)
#
# The three methods of the stage —``_get_campaign_setup``,
# ``_validate_published`` and ``_validate_campaign_mode``— are invoked
# **directly** on the instance built by ``patched_use_case``, so the stage is
# exercised in isolation while ``execute()`` is still not implemented. The
# single collaborator involved is the ``CampaignChannelPublishRepository``
# double, whose return value each case pre-configures through the
# ``campaign_setup`` argument of the context manager; the two validation
# methods take the record as an argument and touch no collaborator at all.
# ``deny_network`` stays active, accrediting 0 outgoing requests.
# ---------------------------------------------------------------------------

#: The single repository method the stage invokes (Requirement 7.1).
CAMPAIGN_SETUP_QUERY = 'get_by_campaign_id_and_channel_id'


def _setup_double(campaign_channel_publish_repository):
    """Return the double of the only ``CampaignChannelPublishRepository``
    method the stage invokes, so the assertions read against a single named
    target.

    Requirements: 7.1, 11.4
    """
    return getattr(campaign_channel_publish_repository, CAMPAIGN_SETUP_QUERY)


def _campaign_setup_with_recording_attributes(**kwargs):
    """Build a fresh Campaign_Setup whose ``attributes`` node is a
    ``_RecordingDict`` carrying the canonical attributes of
    ``make_campaign_setup`` —the six the use case reads **and**
    ``meta_resources``— and return both.

    The recording list is cleared before returning, so it only reflects the
    lookups performed by the code under test. This is what turns Requirement
    7.7 ("0 reads of ``meta_resources``") into an observable fact instead of a
    claim.

    Requirements: 7.7, 11.4
    """
    canonical = make_campaign_setup(**kwargs)
    attributes = _RecordingDict(canonical['attributes'])
    campaign_setup = make_campaign_setup(
        campaign_setup_id=canonical['id'], attributes=attributes,
    )
    attributes.consulted_keys.clear()
    return campaign_setup, attributes


#: Values returned by the repository that the stage must reject with
#: ``DataNotFoundException`` (Requirement 7.2). Both ends of the guard
#: ``not campaign_setup or not isinstance(campaign_setup, dict)`` are covered:
#: ``{}`` is a ``dict`` but falsy, and ``True`` is truthy but not a ``dict``.
INVALID_CAMPAIGN_SETUPS = (None, False, {}) + NON_DICT_VALUES
INVALID_CAMPAIGN_SETUP_IDS = ('none', 'false', 'empty-dict') + NON_DICT_IDS

#: Values of ``meta_published`` that must be rejected with
#: ``IncorrectValidationException`` because they are not ``True`` *by
#: identity*: the absence of the attribute, ``None``, ``False``, the integer
#: ``1`` (equal to ``True`` but not the same object) and the two string spellings
#: (Requirement 7.4).
REJECTED_PUBLISHED_VALUES = (ABSENT, None, False, 1, 'True', 'true')
REJECTED_PUBLISHED_IDS = ('absent', 'none', 'false', 'int-1', 'str-True',
                          'str-true')

#: Values of ``meta_campaign_mode`` that must be rejected with
#: ``IncorrectValidationException`` because they do not belong to
#: ``_SUPPORTED_CAMPAIGN_MODES``: the absence of the attribute, ``None``, the
#: empty string, the lowercase spelling, the padded spelling and an unknown
#: mode (Requirement 8.5). The comparison is exact: neither case folding nor
#: whitespace trimming is applied.
REJECTED_CAMPAIGN_MODES = (ABSENT, None, '', 'standard', ' STANDARD ', 'OTRO')
REJECTED_CAMPAIGN_MODE_IDS = ('absent', 'none', 'empty-str', 'lowercase',
                              'padded', 'unknown')

#: The two accepted Campaign_Modes, each of which must be returned verbatim
#: (Requirement 8.5).
SUPPORTED_CAMPAIGN_MODES = (CreativeType.DYNAMIC.value,
                            CreativeType.STANDARD.value)


class TestCampaignSetupStage:
    """``_get_campaign_setup``, ``_validate_published`` and
    ``_validate_campaign_mode``.

    Requirements: 7.1, 7.2, 7.4, 7.7, 8.5
    """

    # -- The single query and its two arguments (Requirement 7.1) -----------

    def test_repository_is_invoked_once_with_the_two_positional_arguments(self):
        """A single ``get_by_campaign_id_and_channel_id(campaign_id,
        channel_id)`` with the two values in that order.

        Requirements: 7.1
        """
        with patched_use_case() as (use_case, _, _, _, publish_repository):
            use_case._get_campaign_setup(41, 2)

            _setup_double(publish_repository).assert_called_once_with(41, 2)

            args, kwargs = _setup_double(publish_repository).call_args
            assert args == (41, 2)
            assert kwargs == {}

    def test_the_query_is_emitted_with_the_default_channel_id_zero(self):
        """The query is emitted **also** when the Channel_ID keeps its default
        value ``0``: the stage does not short-circuit a degraded
        ``channel_ref``, it lets the repository answer and surfaces the failure
        as the ``DataNotFoundException`` of Requirement 7.2.

        Requirements: 6.2, 7.1
        """
        channel_id = 0

        with patched_use_case() as (use_case, _, _, _, publish_repository):
            use_case._get_campaign_setup(41, channel_id)

            _setup_double(publish_repository).assert_called_once_with(41, 0)

            args = _setup_double(publish_repository).call_args[0]
            assert args[1] is channel_id
            assert type(args[1]) is int

    def test_string_campaign_id_is_not_converted(self):
        """``campaign_id`` of type ``str`` reaches the repository as the very
        same string: the stage performs no type conversion and no
        normalisation.

        Requirements: 2.6, 7.1
        """
        campaign_id = '41'

        with patched_use_case() as (use_case, _, _, _, publish_repository):
            use_case._get_campaign_setup(campaign_id, 2)

            _setup_double(publish_repository).assert_called_once_with('41', 2)

            args = _setup_double(publish_repository).call_args[0]
            assert args[0] is campaign_id
            assert type(args[0]) is str

    def test_arguments_are_forwarded_by_identity_whatever_their_type(self):
        """Any value is forwarded untouched, by identity.

        Requirements: 2.6, 7.1
        """
        campaign_id = object()
        channel_id = object()

        with patched_use_case() as (use_case, _, _, _, publish_repository):
            use_case._get_campaign_setup(campaign_id, channel_id)

            args = _setup_double(publish_repository).call_args[0]
            assert args[0] is campaign_id
            assert args[1] is channel_id

    def test_no_other_repository_is_touched_by_the_stage(self):
        """One call on the ``CampaignChannelPublishRepository`` double and none
        on the other three.

        The instance used is the one created by ``__init__``, since the double
        yielded by ``patched_use_case`` is
        ``CampaignChannelPublishRepository.return_value``: a new instantiation
        inside the stage would record its calls on a different object.

        Requirements: 7.1
        """
        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            use_case._get_campaign_setup(41, 2)

            assert publish_repository.method_calls == [
                call.get_by_campaign_id_and_channel_id(41, 2),
            ]
            assert use_case.campaign_channel_publish_repository is publish_repository

            for double in (account_repository, campaign_repository,
                           ad_set_repository):
                assert double.mock_calls == []

    # -- The rejected repository answers (Requirement 7.2) ------------------

    @pytest.mark.parametrize(
        'returned', INVALID_CAMPAIGN_SETUPS, ids=INVALID_CAMPAIGN_SETUP_IDS,
    )
    def test_falsy_or_non_dict_answer_raises_data_not_found(self, returned):
        """Every falsy value and every non-``dict`` value is rejected: only a
        truthy ``dict`` resolves the Campaign_Setup.

        Requirements: 7.2
        """
        with patched_use_case(campaign_setup=returned) as (
                use_case, _, _, _, publish_repository):
            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._get_campaign_setup(41, 2)

            assert_exception_type(exc_info, DataNotFoundException)
            _setup_double(publish_repository).assert_called_once_with(41, 2)

    def test_failure_is_logged_with_the_campaign_id_and_the_channel_id(self):
        """The failure is reported through ``logger.error`` mentioning both
        values employed.

        Requirements: 7.2
        """
        with patched_use_case(campaign_setup=None) as (use_case, _, _, _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(DataNotFoundException):
                    use_case._get_campaign_setup(918273, 645342)

        assert mock_logger.error.call_count == 1
        message = str(mock_logger.error.call_args[0][0])
        assert '918273' in message
        assert '645342' in message

    def test_failure_with_the_default_channel_id_is_logged_as_well(self):
        """A Channel_ID of ``0`` is interpolated in the log message too, which
        is what makes a degraded ``channel_ref`` diagnosable.

        Requirements: 6.2, 7.2
        """
        with patched_use_case(campaign_setup=None) as (use_case, _, _, _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(DataNotFoundException):
                    use_case._get_campaign_setup(918273, 0)

        message = str(mock_logger.error.call_args[0][0])
        assert '918273' in message
        assert '0' in message

    # -- A resolved Campaign_Setup (Requirements 7.1, 7.2) ------------------

    def test_canonical_campaign_setup_is_returned_by_reference(self):
        """The record returned by the repository is handed back as is, without
        copying it and without reshaping it.

        Requirements: 7.1
        """
        campaign_setup = make_campaign_setup()
        pristine = copy.deepcopy(campaign_setup)

        with patched_use_case(campaign_setup=campaign_setup) as (use_case, _,
                                                                _, _, _):
            result = use_case._get_campaign_setup(41, 2)

        assert result is campaign_setup
        assert campaign_setup == pristine

    def test_degenerate_campaign_setup_resolves_without_raising(self):
        """A ``dict`` with a single key is a resolved Campaign_Setup: the guard
        of Requirement 7.2 checks truthiness and type, not the presence of an
        ``attributes`` node.

        Requirements: 7.2
        """
        degenerate = {'id': 1}

        with patched_use_case(campaign_setup=degenerate) as (use_case, _, _,
                                                            _, _):
            result = use_case._get_campaign_setup(41, 2)

        assert result is degenerate

    def test_absent_attributes_does_not_raise_in_the_query(self):
        """A record whose ``attributes`` node is absent resolves the query
        without raising, and the missing node surfaces later, as the
        ``IncorrectValidationException`` of the publication validation.

        Requirements: 7.2, 7.4
        """
        campaign_setup = make_campaign_setup(attributes=ABSENT)
        assert 'attributes' not in campaign_setup

        with patched_use_case(campaign_setup=campaign_setup) as (use_case, _,
                                                                _, _, _):
            result = use_case._get_campaign_setup(41, 2)

            assert result is campaign_setup

            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._validate_published(result)

            assert_exception_type(exc_info, IncorrectValidationException)

    # -- The publication state (Requirement 7.4) ----------------------------

    def test_published_true_does_not_raise(self):
        """``meta_published`` equal to ``True`` by identity validates, and the
        method returns ``None``.

        Requirements: 7.4
        """
        campaign_setup = make_campaign_setup(meta_published=True)

        with patched_use_case() as (use_case, _, _, _, _):
            assert use_case._validate_published(campaign_setup) is None

    @pytest.mark.parametrize(
        'meta_published', REJECTED_PUBLISHED_VALUES, ids=REJECTED_PUBLISHED_IDS,
    )
    def test_rejected_published_values_raise_incorrect_validation(
            self, meta_published):
        """The absence of the attribute and the five values that are not
        ``True`` by identity —``None``, ``False``, the integer ``1``, ``'True'``
        and ``'true'``— are all rejected.

        Requirements: 7.4
        """
        campaign_setup = make_campaign_setup(meta_published=meta_published)

        with patched_use_case() as (use_case, _, _, _, _):
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._validate_published(campaign_setup)

            assert_exception_type(exc_info, IncorrectValidationException)

    def test_integer_one_is_rejected_although_it_equals_true(self):
        """The comparison is by identity and not by equality: ``1 == True`` but
        ``1 is not True``, so the integer is rejected.

        Requirements: 7.4
        """
        campaign_setup = make_campaign_setup(meta_published=1)
        assert campaign_setup['attributes']['meta_published'] == True  # noqa: E712

        with patched_use_case() as (use_case, _, _, _, _):
            with pytest.raises(IncorrectValidationException):
                use_case._validate_published(campaign_setup)

    def test_rejected_publication_state_is_logged_as_an_error(self):
        """The rejection is reported through ``logger.error``, and no
        collaborator is touched: the validation works on the record it
        receives.

        Requirements: 7.4
        """
        campaign_setup = make_campaign_setup(meta_published=False)

        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(IncorrectValidationException):
                    use_case._validate_published(campaign_setup)

            assert mock_logger.error.call_count == 1

            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []

    # -- The Campaign_Mode (Requirement 8.5) --------------------------------

    @pytest.mark.parametrize('campaign_mode', SUPPORTED_CAMPAIGN_MODES)
    def test_supported_campaign_mode_is_returned_verbatim(self, campaign_mode):
        """``CreativeType.DYNAMIC.value`` and ``CreativeType.STANDARD.value``
        validate and are returned as their own value: the method hands back the
        mode **string**, not a callable and not an enum member.

        Requirements: 8.5
        """
        campaign_setup = make_campaign_setup(meta_campaign_mode=campaign_mode)

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._validate_campaign_mode(campaign_setup)

        assert result == campaign_mode
        assert isinstance(result, str)

    def test_the_two_supported_modes_are_the_declared_ones(self):
        """The accepted set is exactly the two values of ``CreativeType``, in
        the order declared by the class constant.

        Requirements: 8.5
        """
        assert FacebookGetLaunchCampaignCreativesUseCase._SUPPORTED_CAMPAIGN_MODES == (
            CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
        )

    @pytest.mark.parametrize(
        'campaign_mode', REJECTED_CAMPAIGN_MODES, ids=REJECTED_CAMPAIGN_MODE_IDS,
    )
    def test_rejected_campaign_modes_raise_incorrect_validation(
            self, campaign_mode):
        """The absence of the attribute, ``None``, the empty string, the
        lowercase spelling, the padded spelling and an unknown mode are all
        rejected: the comparison is exact, with no case folding and no
        whitespace trimming.

        Requirements: 8.5
        """
        campaign_setup = make_campaign_setup(meta_campaign_mode=campaign_mode)

        with patched_use_case() as (use_case, _, _, _, _):
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._validate_campaign_mode(campaign_setup)

            assert_exception_type(exc_info, IncorrectValidationException)

    def test_rejected_campaign_mode_is_logged_with_the_read_value(self):
        """The rejection is reported through ``logger.error`` mentioning the
        value read, and no collaborator is touched.

        Requirements: 8.5
        """
        campaign_setup = make_campaign_setup(meta_campaign_mode='CAROUSEL')

        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                with pytest.raises(IncorrectValidationException):
                    use_case._validate_campaign_mode(campaign_setup)

            assert mock_logger.error.call_count == 1
            assert 'CAROUSEL' in str(mock_logger.error.call_args[0][0])

            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []

    def test_absent_attributes_rejects_the_campaign_mode(self):
        """A record with no ``attributes`` node reads the mode as ``None`` and
        is rejected, without raising ``AttributeError``.

        Requirements: 8.5
        """
        campaign_setup = make_campaign_setup(attributes=ABSENT)

        with patched_use_case() as (use_case, _, _, _, _):
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._validate_campaign_mode(campaign_setup)

            assert_exception_type(exc_info, IncorrectValidationException)

    # -- ``meta_resources`` is never read (Requirement 7.7) -----------------

    def test_the_fixture_carries_meta_resources(self):
        """Guard of the three cases below: the canonical Campaign_Setup does
        include ``meta_resources``, so "it is not read" is a fact about the
        production code and not about a fixture that lacks the key.

        Requirements: 7.7
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()

        assert 'meta_resources' in dict(attributes)
        assert campaign_setup['attributes'] is attributes

    def test_the_query_reads_no_attribute_at_all(self):
        """Resolving the Campaign_Setup only checks the truthiness and the type
        of the record: not a single key of ``attributes`` is consulted, and in
        particular not ``meta_resources``.

        Requirements: 7.2, 7.7
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()

        with patched_use_case(campaign_setup=campaign_setup) as (use_case, _,
                                                                _, _, _):
            result = use_case._get_campaign_setup(41, 2)

        assert result is campaign_setup
        assert attributes.consulted_keys == []

    def test_the_publication_validation_reads_only_meta_published(self):
        """The publication validation consults exactly one key.

        Requirements: 7.4, 7.7
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()

        with patched_use_case() as (use_case, _, _, _, _):
            use_case._validate_published(campaign_setup)

        assert attributes.consulted_keys == ['meta_published']
        assert 'meta_resources' not in attributes.consulted_keys

    def test_the_mode_validation_reads_only_meta_campaign_mode(self):
        """The mode validation consults exactly one key.

        Requirements: 7.7, 8.5
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._validate_campaign_mode(campaign_setup)

        assert result == CreativeType.DYNAMIC.value
        assert attributes.consulted_keys == ['meta_campaign_mode']
        assert 'meta_resources' not in attributes.consulted_keys

    def test_the_whole_stage_never_reads_meta_resources(self):
        """Across the three methods of the stage the consulted keys are exactly
        ``meta_published`` and ``meta_campaign_mode``: 0 reads of
        ``meta_resources``, whose correlation with the creatives is out of
        scope of this specification.

        Requirements: 7.7
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()

        with patched_use_case(campaign_setup=campaign_setup) as (use_case, _,
                                                                _, _, _):
            resolved = use_case._get_campaign_setup(41, 2)
            use_case._validate_published(resolved)
            campaign_mode = use_case._validate_campaign_mode(resolved)

        assert campaign_mode == CreativeType.DYNAMIC.value
        assert attributes.consulted_keys == ['meta_published',
                                             'meta_campaign_mode']
        assert 'meta_resources' not in attributes.consulted_keys

    def test_the_stage_leaves_the_campaign_setup_untouched(self):
        """The three methods are read-only: the record equals its initial
        ``deepcopy`` afterwards, so no defensive read inserts a missing key.

        Requirements: 7.2, 7.4, 8.5
        """
        campaign_setup = make_campaign_setup()
        pristine = copy.deepcopy(campaign_setup)

        with patched_use_case(campaign_setup=campaign_setup) as (use_case, _,
                                                                _, _, _):
            resolved = use_case._get_campaign_setup(41, 2)
            use_case._validate_published(resolved)
            use_case._validate_campaign_mode(resolved)

        assert campaign_setup == pristine


# ---------------------------------------------------------------------------
# Creative_Entry composition (Requirements 7.5, 8.1, 8.2, 8.3, 8.4, 8.6, 8.7,
# 8.8, 8.9)
#
# ``_build_dynamic_creative_published``, ``_build_standard_creative_published``
# and ``_build_creatives`` are invoked **directly** on the instance built by
# ``patched_use_case``. The three methods are pure projections: they receive a
# descriptor (and the already validated Campaign_Mode, in the case of
# ``_build_creatives``) and touch no collaborator, so no repository double
# needs to be configured beyond the scaffolding the context manager already
# provides. ``deny_network`` stays active, accrediting 0 outgoing requests.
# ---------------------------------------------------------------------------

#: The ``adchannel_id`` carried by the internal descriptor. Deliberately
#: different from the ``ad_channel_id`` of both specifications, so every
#: assertion below on ``entry['adchannel_id']`` witnesses Requirement 8.6 and
#: OQ-2 at once: the exposed value is the one of the specification, never the
#: one of the descriptor, which exists only for the log messages.
DESCRIPTOR_ADCHANNEL_ID = 7777


def _descriptor(creative, adchannel_id=DESCRIPTOR_ADCHANNEL_ID):
    """Build a fresh internal descriptor of a usable Published_Creative.

    Same two-key shape the traversal accumulates (see the *Descriptor interno*
    section of ``design.md``): ``creative`` is a **reference** to the stored
    ``channel_creative`` and ``adchannel_id`` is the ``id`` of the
    ``ad-channels`` record.

    Requirements: 8.6, 11.4
    """
    return {'creative': creative, 'adchannel_id': adchannel_id}


def _dynamic_creative_with(**spec_overrides):
    """Fresh canonical ``DYNAMIC`` Published_Creative with the given leaf keys
    of ``asset_feed_spec`` degraded: an ``ABSENT`` value **removes** the key
    (which must exist in the canonical structure, so a typo fails loudly), any
    other value replaces it.

    Written as a post-build mutation instead of through the ``**spec_overrides``
    of ``make_dynamic_creative`` because ``ad_channel_id`` is a named parameter
    of that builder and could not be removed through it.

    Requirements: 8.8, 11.4
    """
    creative = make_dynamic_creative()
    spec = creative['ads'][0]['adCreative']['asset_feed_spec']
    for key, value in spec_overrides.items():
        if value is ABSENT:
            del spec[key]
        else:
            spec[key] = value
    return creative


def _standard_creative_with_spec(**spec_overrides):
    """Fresh canonical ``STANDARD`` Published_Creative with the given leaf keys
    of ``object_story_spec`` degraded, ``ABSENT`` removing the key.

    Requirements: 8.8, 11.4
    """
    creative = make_standard_creative()
    spec = creative['ads'][0]['adCreative']['object_story_spec']
    for key, value in spec_overrides.items():
        if value is ABSENT:
            del spec[key]
        else:
            spec[key] = value
    return creative


def _standard_creative_with_link_data(**link_data_overrides):
    """Fresh canonical ``STANDARD`` Published_Creative with the given leaf keys
    of ``object_story_spec.link_data`` degraded, ``ABSENT`` removing the key.

    Requirements: 8.8, 11.4
    """
    creative = make_standard_creative()
    link_data = creative['ads'][0]['adCreative']['object_story_spec']['link_data']
    for key, value in link_data_overrides.items():
        if value is ABSENT:
            del link_data[key]
        else:
            link_data[key] = value
    return creative


def _creative_with_both_specifications():
    """Fresh Published_Creative whose single ad carries **both**
    ``asset_feed_spec`` and ``object_story_spec``, with values distinguishable
    by branch: every ``DYNAMIC`` value contains the marker ``DYN`` and every
    ``STANDARD`` one the marker ``STD``.

    It is the fixture of Requirement 8.2: the dispatch is decided by the
    Campaign_Mode, so each branch must read its own specification and never a
    single value of the other one, which a marker containment check makes
    observable.

    Requirements: 8.2, 11.4
    """
    creative = make_dynamic_creative(
        ad_channel_id=1111,
        min_daily_budget=11,
        titles=[{'text': 'DYN Titular', 'valid_length': True}],
        link_urls=[{'website_url': 'https://example.test/DYN-landing'}],
        locations=[{'key': 'DYN', 'name': 'Dinámica'}],
    )
    standard = make_standard_creative(
        ad_channel_id=2222,
        spec_overrides={
            'min_daily_budget': 22,
            'locations': [{'key': 'STD', 'name': 'Estándar'}],
        },
        link='https://example.test/STD-landing',
    )
    object_story_spec = standard['ads'][0]['adCreative']['object_story_spec']
    # ``name`` is the name of the *creative* in ``make_standard_creative``, so
    # the headline of ``link_data`` is marked here instead of through a keyword.
    object_story_spec['link_data']['name'] = 'STD Titular'
    creative['ads'][0]['adCreative']['object_story_spec'] = object_story_spec
    return creative


def _meta_prefixed_keys(entry):
    """Return the keys of a Creative_Entry whose name contains ``meta_``.

    Requirement 8.7 fixes that set as empty: the entry exposes the Strapi
    identifiers and 0 keys for Meta identifiers.

    Requirements: 8.7, 11.4
    """
    return [key for key in entry if 'meta_' in key]


#: The Creative_Entry the canonical ``make_dynamic_creative()`` produces,
#: written out key by key in the order of Requirement 8.1. Spelled as a literal
#: on purpose: it pins the 31 values of the ``DYNAMIC`` branch against the
#: table of ``design.md`` instead of recomputing them from the fixture.
DYNAMIC_BASELINE_ENTRY = {
    'idx': 0,
    'name': 'Ad Set A',
    'adset_id': 120,
    'ad_id': 501,
    'adchannel_id': 9001,
    'daily_budget': 15,
    'images': [
        {'url': 'https://example.test/img-1.jpg', 'valid': True, 'error': None},
        {'url': 'https://example.test/img-2.jpg', 'valid': False, 'error': 'too small'},
    ],
    'bodies': [{'text': 'Cuerpo 1', 'valid_length': True}],
    'titles': [{'text': 'Titular 1', 'valid_length': True}],
    'descriptions': [{'text': 'Descripción 1', 'valid_length': True}],
    'call_to_action_types': [{'value': 'SHOP_NOW', 'valid': True}],
    'images_valid_amount': True,
    'titles_valid_amount': True,
    'bodies_valid_amount': True,
    'descriptions_valid_amount': True,
    'call_to_action_types_valid_amount': True,
    'images_max_amount': 10,
    'titles_max_amount': 5,
    'bodies_max_amount': 5,
    'descriptions_max_amount': 5,
    'call_to_action_types_max_amount': 5,
    'unique_titles': True,
    'unique_bodies': True,
    'unique_descriptions': True,
    'daily_budget_valid': True,
    'min_daily_budget': 10,
    'proposal_url': 'https://example.test/landing',
    'proposal_url_valid': True,
    'proposal_locations': [{'key': '1234', 'name': 'Madrid'}],
    'locations': [{'key': '1234', 'name': 'Madrid'}],
    'locations_valid': True,
}

#: The Creative_Entry the canonical ``make_standard_creative()`` produces. Same
#: 31 keys, same order (Requirement 8.1); the five ``*_max_amount`` are the
#: literal ``1`` and the three ``unique_*`` reuse the three ``*_valid``
#: (Requirement 8.4).
STANDARD_BASELINE_ENTRY = {
    'idx': 0,
    'name': 'Ad Set A',
    'adset_id': 120,
    'ad_id': 501,
    'adchannel_id': 9001,
    'daily_budget': 15,
    'images': [
        {'url': 'https://example.test/img-1.jpg', 'valid': True, 'error': None},
    ],
    'bodies': [{'text': 'Cuerpo', 'valid_length': True}],
    'titles': [{'text': 'Titular', 'valid_length': True}],
    'descriptions': [{'text': 'Descripción', 'valid_length': True}],
    'call_to_action_types': [{'value': 'SHOP_NOW', 'valid': True}],
    'images_valid_amount': True,
    'titles_valid_amount': True,
    'bodies_valid_amount': True,
    'descriptions_valid_amount': True,
    'call_to_action_types_valid_amount': True,
    'images_max_amount': 1,
    'titles_max_amount': 1,
    'bodies_max_amount': 1,
    'descriptions_max_amount': 1,
    'call_to_action_types_max_amount': 1,
    'unique_titles': True,
    'unique_bodies': True,
    'unique_descriptions': True,
    'daily_budget_valid': True,
    'min_daily_budget': 10,
    'proposal_url': 'https://example.test/landing',
    'proposal_url_valid': True,
    'proposal_locations': [{'key': '1234', 'name': 'Madrid'}],
    'locations': [{'key': '1234', 'name': 'Madrid'}],
    'locations_valid': True,
}


def _expected_dynamic_entry(idx=0, **overrides):
    """Return a fresh copy of ``DYNAMIC_BASELINE_ENTRY`` with ``idx`` set and
    the given keys replaced, so no two cases share a container (Requirement
    11.4).

    Since every override key already exists in the baseline, ``update`` keeps
    the insertion order of the 31 keys intact.

    Requirements: 8.1, 8.8, 11.4
    """
    entry = copy.deepcopy(DYNAMIC_BASELINE_ENTRY)
    entry['idx'] = idx
    entry.update(copy.deepcopy(overrides))
    return entry


def _expected_standard_entry(idx=0, **overrides):
    """Return a fresh copy of ``STANDARD_BASELINE_ENTRY`` with ``idx`` set and
    the given keys replaced.

    Requirements: 8.1, 8.8, 11.4
    """
    entry = copy.deepcopy(STANDARD_BASELINE_ENTRY)
    entry['idx'] = idx
    entry.update(copy.deepcopy(overrides))
    return entry


#: The defaults of Requirement 8.8 for every key the ``DYNAMIC`` branch reads
#: from ``asset_feed_spec``: the state of the entry when ``adCreative`` or
#: ``asset_feed_spec`` is degraded as a whole. The keys the branch reads from
#: the Published_Creative itself —``name``, ``adset_id``, ``ad_id``,
#: ``daily_budget`` and ``proposal_locations``— are unaffected.
DYNAMIC_SPEC_DEFAULTS = {
    'adchannel_id': 0,
    'images': [],
    'bodies': [],
    'titles': [],
    'descriptions': [],
    'call_to_action_types': [],
    'images_valid_amount': False,
    'titles_valid_amount': False,
    'bodies_valid_amount': False,
    'descriptions_valid_amount': False,
    'call_to_action_types_valid_amount': False,
    'images_max_amount': 0,
    'titles_max_amount': 0,
    'bodies_max_amount': 0,
    'descriptions_max_amount': 0,
    'call_to_action_types_max_amount': 0,
    'unique_titles': False,
    'unique_bodies': False,
    'unique_descriptions': False,
    'daily_budget_valid': False,
    'min_daily_budget': 0,
    'proposal_url': '',
    'proposal_url_valid': False,
    'locations': [],
    'locations_valid': False,
}

#: One case per leaf key of ``asset_feed_spec``, paired with the entry keys
#: that fall back to their default when that leaf is degraded. Every case is
#: exercised twice, with ``ABSENT`` and with ``None`` (Requirement 8.8).
DYNAMIC_SPEC_LEAVES = (
    ('ad_channel_id', {'adchannel_id': 0}),
    ('images', {'images': []}),
    ('bodies', {'bodies': []}),
    ('titles', {'titles': []}),
    ('descriptions', {'descriptions': []}),
    ('call_to_action_types', {'call_to_action_types': []}),
    ('link_urls', {'proposal_url': ''}),
    ('images_valid_amount', {'images_valid_amount': False}),
    ('titles_valid_amount', {'titles_valid_amount': False}),
    ('bodies_valid_amount', {'bodies_valid_amount': False}),
    ('descriptions_valid_amount', {'descriptions_valid_amount': False}),
    ('call_to_action_types_valid_amount', {'call_to_action_types_valid_amount': False}),
    ('images_max_amount', {'images_max_amount': 0}),
    ('titles_max_amount', {'titles_max_amount': 0}),
    ('bodies_max_amount', {'bodies_max_amount': 0}),
    ('descriptions_max_amount', {'descriptions_max_amount': 0}),
    ('call_to_action_types_max_amount', {'call_to_action_types_max_amount': 0}),
    ('unique_titles', {'unique_titles': False}),
    ('unique_bodies', {'unique_bodies': False}),
    ('unique_descriptions', {'unique_descriptions': False}),
    ('daily_budget_valid', {'daily_budget_valid': False}),
    ('min_daily_budget', {'min_daily_budget': 0}),
    # Name asymmetry replicated verbatim from the launch flow: the value of
    # 'proposal_url_valid' is read from the 'link_url_valid' leaf.
    ('link_url_valid', {'proposal_url_valid': False}),
    ('locations', {'locations': []}),
    ('locations_valid', {'locations_valid': False}),
)

#: The state of a ``STANDARD`` entry when ``link_data`` is degraded as a whole:
#: ``call_to_action`` lives inside it, so the two call-to-action keys fall back
#: too. The five ``*_max_amount`` stay at the literal ``1`` (Requirement 8.4).
STANDARD_LINK_DATA_DEFAULTS = {
    'images': [],
    'bodies': [],
    'titles': [],
    'descriptions': [],
    'call_to_action_types': [],
    'images_valid_amount': False,
    'titles_valid_amount': False,
    'bodies_valid_amount': False,
    'descriptions_valid_amount': False,
    'call_to_action_types_valid_amount': False,
    'unique_titles': False,
    'unique_bodies': False,
    'unique_descriptions': False,
    'proposal_url': '',
    'proposal_url_valid': False,
}

#: The state of a ``STANDARD`` entry when ``adCreative`` or
#: ``object_story_spec`` is degraded as a whole: the ``link_data`` defaults plus
#: the ones of the five keys read from ``object_story_spec`` itself.
STANDARD_SPEC_DEFAULTS = dict(
    STANDARD_LINK_DATA_DEFAULTS,
    adchannel_id=0,
    daily_budget_valid=False,
    min_daily_budget=0,
    locations=[],
    locations_valid=False,
)

#: One case per leaf key of ``object_story_spec``. ``page_id`` is listed with
#: an empty set of affected keys, which is precisely the point: the branch does
#: not read it.
STANDARD_SPEC_LEAVES = (
    ('ad_channel_id', {'adchannel_id': 0}),
    ('page_id', {}),
    ('daily_budget_valid', {'daily_budget_valid': False}),
    ('min_daily_budget', {'min_daily_budget': 0}),
    ('locations', {'locations': []}),
    ('locations_valid', {'locations_valid': False}),
)

#: One case per leaf key of ``object_story_spec.link_data``. ``image_error`` is
#: listed with an empty set of affected keys because its canonical value is
#: already ``None``: degrading it is indistinguishable from the baseline, which
#: is the honest expectation and not a missing assertion.
STANDARD_LINK_DATA_LEAVES = (
    ('name', {'titles': []}),
    ('title_valid', {'titles': [{'text': 'Titular', 'valid_length': False}],
                     'titles_valid_amount': False,
                     'unique_titles': False}),
    ('message', {'bodies': []}),
    ('body_valid', {'bodies': [{'text': 'Cuerpo', 'valid_length': False}],
                    'bodies_valid_amount': False,
                    'unique_bodies': False}),
    ('description', {'descriptions': []}),
    ('description_valid', {'descriptions': [{'text': 'Descripción',
                                             'valid_length': False}],
                           'descriptions_valid_amount': False,
                           'unique_descriptions': False}),
    ('image_url', {'images': []}),
    ('image_valid', {'images': [{'url': 'https://example.test/img-1.jpg',
                                 'valid': False, 'error': None}],
                     'images_valid_amount': False}),
    ('image_error', {}),
    ('link', {'proposal_url': ''}),
    ('link_url_valid', {'proposal_url_valid': False}),
)

#: The two degradations every matrix above is exercised with: the key omitted
#: and the key present with value ``None`` (Requirement 8.8).
LEAF_DEGRADATIONS = (ABSENT, None)
LEAF_DEGRADATION_IDS = ('absent', 'none')


class TestDynamicCreativeEntry:
    """``FacebookGetLaunchCampaignCreativesUseCase._build_dynamic_creative_published``.

    Requirements: 7.5, 8.1, 8.3, 8.6, 8.7, 8.8, 8.9
    """

    # -- The 31 keys, in order (Requirements 8.1, 8.7) ----------------------

    def test_canonical_creative_produces_the_31_keys_in_order(self):
        """The entry carries exactly the 31 keys of Requirement 8.1, in that
        very order: ``entry_keys_in_order`` compares the key *set* and the key
        *order* against ``CREATIVE_ENTRY_KEYS`` in a single assertion.

        Requirements: 8.1
        """
        descriptor = _descriptor(make_dynamic_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert len(entry) == 31

    def test_canonical_creative_produces_the_expected_31_values(self):
        """Value by value against the ``DYNAMIC`` table of ``design.md``.

        Requirements: 8.1, 8.3, 8.9
        """
        descriptor = _descriptor(make_dynamic_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry == _expected_dynamic_entry()

    def test_no_key_carries_a_meta_identifier(self):
        """0 keys whose name contains ``meta_``: the entry exposes the Strapi
        identifiers and no Meta one.

        Requirements: 8.7
        """
        descriptor = _descriptor(make_dynamic_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert _meta_prefixed_keys(entry) == []

    @pytest.mark.parametrize('idx', (0, 1, 7))
    def test_idx_is_the_received_index(self, idx):
        """``idx`` is the value received, not a recomputed one.

        Requirements: 7.5
        """
        descriptor = _descriptor(make_dynamic_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(idx, descriptor)

        assert entry['idx'] == idx
        assert entry_keys_in_order(entry)[0] == 'idx'

    # -- ``adchannel_id`` (Requirement 8.6, OQ-2) ---------------------------

    def test_adchannel_id_comes_from_the_specification_not_from_the_descriptor(self):
        """The exposed ``adchannel_id`` is ``asset_feed_spec.ad_channel_id``,
        even when the ``adchannel_id`` of the descriptor differs: that one only
        exists for the log messages.

        Requirements: 8.6
        """
        descriptor = _descriptor(
            _dynamic_creative_with(ad_channel_id=4242), adchannel_id=9999,
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['adchannel_id'] == 4242
        assert entry['adchannel_id'] != descriptor['adchannel_id']

    # -- Degraded levels (Requirement 8.8, decision D-4) --------------------

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_ad_creative_keeps_the_31_keys_with_their_defaults(
            self, degradation):
        """An ``adCreative`` absent or ``None`` yields the 31 keys with the
        defaults of Requirement 8.8, without raising: decision D-4 normalises
        it with ``or {}``.

        Requirements: 8.8
        """
        descriptor = _descriptor(make_dynamic_creative(ad_creative=degradation))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_dynamic_entry(**DYNAMIC_SPEC_DEFAULTS)

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_asset_feed_spec_keeps_the_31_keys_with_their_defaults(
            self, degradation):
        """The same holds one level deeper, for an ``asset_feed_spec`` absent
        or ``None``.

        Requirements: 8.8
        """
        descriptor = _descriptor(
            make_dynamic_creative(asset_feed_spec=degradation),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_dynamic_entry(**DYNAMIC_SPEC_DEFAULTS)

    # -- Degraded leaf keys (Requirement 8.8) -------------------------------

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    @pytest.mark.parametrize(
        'leaf,affected', DYNAMIC_SPEC_LEAVES, ids=_ids(DYNAMIC_SPEC_LEAVES),
    )
    def test_degraded_spec_leaf_falls_back_to_its_default(
            self, leaf, affected, degradation):
        """For each leaf key of ``asset_feed_spec`` and for each of the two
        degradations —key omitted and key present with value ``None``— the
        entry keeps its 31 keys in order, the keys derived from that leaf take
        the default of Requirement 8.8 (``False``, ``0``, ``[]`` or ``''``) and
        every other key keeps its canonical value.

        Requirements: 8.8
        """
        descriptor = _descriptor(_dynamic_creative_with(**{leaf: degradation}))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_dynamic_entry(**affected)

    # -- ``proposal_url`` (Requirement 8.3) ---------------------------------

    def test_proposal_url_joins_several_website_urls_with_a_comma(self):
        """``proposal_url`` is the ``,`` join of the ``website_url`` values of
        ``link_urls``, in their order of appearance.

        Requirements: 8.3
        """
        descriptor = _descriptor(_dynamic_creative_with(link_urls=[
            {'website_url': 'https://example.test/one'},
            {'website_url': 'https://example.test/two'},
            {'website_url': 'https://example.test/three'},
        ]))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['proposal_url'] == (
            'https://example.test/one,'
            'https://example.test/two,'
            'https://example.test/three'
        )

    @pytest.mark.parametrize(
        'link_urls,expected',
        (
            (ABSENT, ''),
            (None, ''),
            ([], ''),
            ([{}], ''),
            ([{'website_url': None}], ''),
            ([{'website_url': ''}, {'website_url': 'https://example.test/b'}],
             ',https://example.test/b'),
        ),
        ids=('absent', 'none', 'empty-list', 'empty-dict', 'none-website-url',
             'empty-website-url'),
    )
    def test_proposal_url_of_an_absent_or_empty_link_urls_is_the_empty_string(
            self, link_urls, expected):
        """An absent, ``None`` or empty ``link_urls`` joins to ``''``, and a
        missing or empty ``website_url`` contributes an empty segment.

        Requirements: 8.3, 8.8
        """
        descriptor = _descriptor(_dynamic_creative_with(link_urls=link_urls))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['proposal_url'] == expected

    def test_proposal_url_valid_is_read_from_link_url_valid(self):
        """``proposal_url_valid`` takes the value of ``link_url_valid`` and
        ignores a same-named key of the specification: it is the name asymmetry
        the launch flow already has, replicated verbatim.

        Requirements: 8.3
        """
        descriptor = _descriptor(_dynamic_creative_with(
            link_url_valid=False, proposal_url_valid=True,
        ))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['proposal_url_valid'] is False

    # -- ``images`` (Requirement 8.3) ---------------------------------------

    def test_images_are_composed_as_dicts_of_url_valid_and_error(self):
        """Each image becomes a dict of exactly the three keys ``url``,
        ``valid`` and ``error``, in that order.

        Requirements: 8.3
        """
        descriptor = _descriptor(make_dynamic_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['images'] == [
            {'url': 'https://example.test/img-1.jpg', 'valid': True,
             'error': None},
            {'url': 'https://example.test/img-2.jpg', 'valid': False,
             'error': 'too small'},
        ]
        for image in entry['images']:
            assert tuple(image.keys()) == ('url', 'valid', 'error')

    def test_image_keys_are_projected_with_none_and_extra_keys_dropped(self):
        """An image lacking the three keys yields ``None`` for each of them, and
        any additional key of the stored image is dropped: the projection is
        exactly three keys wide.

        Requirements: 8.3, 8.8
        """
        descriptor = _descriptor(_dynamic_creative_with(images=[
            {},
            {'url': 'https://example.test/img.jpg', 'valid': True,
             'error': None, 'hash': 'abc123'},
        ]))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_dynamic_creative_published(0, descriptor)

        assert entry['images'] == [
            {'url': None, 'valid': None, 'error': None},
            {'url': 'https://example.test/img.jpg', 'valid': True,
             'error': None},
        ]

    # -- No collaborator and no validator is involved (Requirement 8.9) -----

    def test_composition_touches_no_collaborator_and_no_validator(self):
        """The composition is a pure projection: 0 calls on the four repository
        doubles and 0 invocations of ``MetaAdsValidator`` and
        ``MetaAdsPayloadBuilder``, so the persisted validation values are
        delivered as they are.

        Requirements: 8.9
        """
        creative = make_dynamic_creative()
        pristine = copy.deepcopy(creative)
        descriptor = _descriptor(creative)

        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            with patch('app.v2.use_cases.meta_ads.MetaAdsValidator') as validator, \
                    patch('app.v2.use_cases.meta_ads.MetaAdsPayloadBuilder') as builder:
                entry = use_case._build_dynamic_creative_published(0, descriptor)

            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []

        assert validator.mock_calls == []
        assert builder.mock_calls == []
        assert entry == _expected_dynamic_entry()
        assert creative == pristine


class TestStandardCreativeEntry:
    """``FacebookGetLaunchCampaignCreativesUseCase._build_standard_creative_published``.

    Requirements: 7.5, 8.1, 8.4, 8.6, 8.7, 8.8, 8.9
    """

    # -- The 31 keys, in order (Requirements 8.1, 8.7) ----------------------

    def test_canonical_creative_produces_the_31_keys_in_order(self):
        """The same 31 keys, in the same order, as the ``DYNAMIC`` branch.

        Requirements: 8.1
        """
        descriptor = _descriptor(make_standard_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert len(entry) == 31

    def test_both_branches_share_the_key_set_and_the_key_order(self):
        """The invariant of Requirement 8.1 read directly off the two branches:
        the tuple of keys of a ``STANDARD`` entry equals the one of a
        ``DYNAMIC`` entry.

        Requirements: 8.1
        """
        with patched_use_case() as (use_case, _, _, _, _):
            dynamic_entry = use_case._build_dynamic_creative_published(
                0, _descriptor(make_dynamic_creative()),
            )
            standard_entry = use_case._build_standard_creative_published(
                0, _descriptor(make_standard_creative()),
            )

        assert entry_keys_in_order(standard_entry) == entry_keys_in_order(dynamic_entry)
        assert entry_keys_in_order(standard_entry) == CREATIVE_ENTRY_KEYS

    def test_canonical_creative_produces_the_expected_31_values(self):
        """Value by value against the ``STANDARD`` table of ``design.md``.

        Requirements: 8.1, 8.4, 8.9
        """
        descriptor = _descriptor(make_standard_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry == _expected_standard_entry()

    def test_no_key_carries_a_meta_identifier(self):
        """0 keys whose name contains ``meta_``.

        Requirements: 8.7
        """
        descriptor = _descriptor(make_standard_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert _meta_prefixed_keys(entry) == []

    @pytest.mark.parametrize('idx', (0, 1, 7))
    def test_idx_is_the_received_index(self, idx):
        """``idx`` is the value received.

        Requirements: 7.5
        """
        descriptor = _descriptor(make_standard_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(idx, descriptor)

        assert entry['idx'] == idx

    # -- ``adchannel_id`` (Requirement 8.6, OQ-2) ---------------------------

    def test_adchannel_id_comes_from_the_specification_not_from_the_descriptor(self):
        """The exposed ``adchannel_id`` is ``object_story_spec.ad_channel_id``,
        even when the ``adchannel_id`` of the descriptor differs.

        Requirements: 8.6
        """
        descriptor = _descriptor(
            _standard_creative_with_spec(ad_channel_id=4242),
            adchannel_id=9999,
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry['adchannel_id'] == 4242
        assert entry['adchannel_id'] != descriptor['adchannel_id']

    # -- The five literal ``*_max_amount`` (Requirement 8.4) ----------------

    MAX_AMOUNT_KEYS = (
        'images_max_amount',
        'titles_max_amount',
        'bodies_max_amount',
        'descriptions_max_amount',
        'call_to_action_types_max_amount',
    )

    def test_the_five_max_amount_keys_are_the_literal_one(self):
        """The five ``*_max_amount`` are fixed to the literal ``1``, as the
        already existing ``_build_standard_creative_published`` of the launch
        use case does.

        Requirements: 8.4
        """
        descriptor = _descriptor(make_standard_creative())

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        for key in self.MAX_AMOUNT_KEYS:
            assert entry[key] == 1

    def test_the_five_max_amount_keys_stay_one_with_a_degraded_specification(self):
        """They are literals and not reads, so a degraded ``object_story_spec``
        leaves them at ``1`` while every read key falls back to its default.

        Requirements: 8.4, 8.8
        """
        descriptor = _descriptor(make_standard_creative(object_story_spec=None))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        for key in self.MAX_AMOUNT_KEYS:
            assert entry[key] == 1

    # -- ``unique_*`` reuse the three ``*_valid`` (Requirement 8.4) ---------

    @pytest.mark.parametrize(
        'title_valid,body_valid,description_valid',
        (
            (True, True, True),
            (False, False, False),
            (True, False, True),
            (False, True, False),
        ),
    )
    def test_unique_keys_reuse_the_three_valid_flags(
            self, title_valid, body_valid, description_valid):
        """``unique_titles``, ``unique_bodies`` and ``unique_descriptions``
        reuse ``title_valid``, ``body_valid`` and ``description_valid``, which
        also feed the three ``*_valid_amount``.

        Requirements: 8.4
        """
        descriptor = _descriptor(_standard_creative_with_link_data(
            title_valid=title_valid,
            body_valid=body_valid,
            description_valid=description_valid,
        ))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry['unique_titles'] is title_valid
        assert entry['unique_bodies'] is body_valid
        assert entry['unique_descriptions'] is description_valid
        assert entry['titles_valid_amount'] is title_valid
        assert entry['bodies_valid_amount'] is body_valid
        assert entry['descriptions_valid_amount'] is description_valid

    # -- ``titles``/``bodies``/``descriptions`` (Requirement 8.4) -----------

    TEXT_LISTS = (
        ('titles', 'name', 'title_valid'),
        ('bodies', 'message', 'body_valid'),
        ('descriptions', 'description', 'description_valid'),
    )

    @pytest.mark.parametrize(
        'entry_key,link_data_key,valid_key', TEXT_LISTS,
        ids=[entry_key for entry_key, _, _ in TEXT_LISTS],
    )
    def test_present_text_yields_a_single_element_list(
            self, entry_key, link_data_key, valid_key):
        """A present text yields a list of exactly one dict of exactly the two
        keys ``text`` and ``valid_length``.

        Requirements: 8.4
        """
        descriptor = _descriptor(_standard_creative_with_link_data(
            **{link_data_key: 'Texto presente', valid_key: True},
        ))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry[entry_key] == [
            {'text': 'Texto presente', 'valid_length': True},
        ]
        assert tuple(entry[entry_key][0].keys()) == ('text', 'valid_length')

    @pytest.mark.parametrize(
        'text', (ABSENT, None, '', 0), ids=('absent', 'none', 'empty-str', 'zero'),
    )
    @pytest.mark.parametrize(
        'entry_key,link_data_key,valid_key', TEXT_LISTS,
        ids=[entry_key for entry_key, _, _ in TEXT_LISTS],
    )
    def test_falsy_text_yields_an_empty_list(
            self, entry_key, link_data_key, valid_key, text):
        """A falsy text —absent, ``None``, the empty string or ``0``— yields an
        empty list, while the corresponding ``*_valid_amount`` keeps the
        persisted flag.

        Requirements: 8.4, 8.8
        """
        descriptor = _descriptor(
            _standard_creative_with_link_data(**{link_data_key: text}),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry[entry_key] == []
        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

    # -- Degraded levels (Requirement 8.8, decision D-4) --------------------

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_ad_creative_keeps_the_31_keys_with_their_defaults(
            self, degradation):
        """An ``adCreative`` absent or ``None`` yields the 31 keys with the
        defaults of Requirement 8.8, without raising.

        Requirements: 8.8
        """
        descriptor = _descriptor(make_standard_creative(ad_creative=degradation))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(**STANDARD_SPEC_DEFAULTS)

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_object_story_spec_keeps_the_31_keys_with_their_defaults(
            self, degradation):
        """The same holds for an ``object_story_spec`` absent or ``None``.

        Requirements: 8.8
        """
        descriptor = _descriptor(
            make_standard_creative(object_story_spec=degradation),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(**STANDARD_SPEC_DEFAULTS)

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_link_data_keeps_the_31_keys_with_their_defaults(
            self, degradation):
        """A ``link_data`` absent or ``None`` degrades the eleven keys derived
        from it —``call_to_action`` included, since it lives inside— and leaves
        the five keys read from ``object_story_spec`` untouched.

        Requirements: 8.8
        """
        descriptor = _descriptor(make_standard_creative(link_data=degradation))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(**STANDARD_LINK_DATA_DEFAULTS)
        assert entry['adchannel_id'] == 9001
        assert entry['min_daily_budget'] == 10

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    def test_degraded_call_to_action_yields_an_empty_list_and_a_false_flag(
            self, degradation):
        """A ``call_to_action`` absent or ``None`` yields
        ``call_to_action_types == []`` and
        ``call_to_action_types_valid_amount is False``.

        Requirements: 8.8
        """
        descriptor = _descriptor(
            make_standard_creative(call_to_action=degradation),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(
            call_to_action_types=[],
            call_to_action_types_valid_amount=False,
        )

    @pytest.mark.parametrize(
        'call_to_action,expected_types,expected_valid',
        (
            ({'other': 'x'}, [{}], False),
            ({'type': None}, [{}], False),
            ({'type': {'value': 'SHOP_NOW'}}, [{'value': 'SHOP_NOW'}], False),
            ({'type': {'value': 'SHOP_NOW', 'valid': None}},
             [{'value': 'SHOP_NOW', 'valid': None}], False),
        ),
        ids=('type-absent', 'type-none', 'valid-absent', 'valid-none'),
    )
    def test_degraded_call_to_action_type_falls_back_without_raising(
            self, call_to_action, expected_types, expected_valid):
        """A present ``call_to_action`` with its ``type`` or its ``type.valid``
        degraded keeps ``call_to_action_types`` as a single-element list and
        falls back to ``False`` for the validity flag.

        Requirements: 8.8
        """
        descriptor = _descriptor(
            make_standard_creative(call_to_action=call_to_action),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry['call_to_action_types'] == expected_types
        assert entry['call_to_action_types_valid_amount'] is expected_valid

    # -- Degraded leaf keys (Requirement 8.8) -------------------------------

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    @pytest.mark.parametrize(
        'leaf,affected', STANDARD_SPEC_LEAVES, ids=_ids(STANDARD_SPEC_LEAVES),
    )
    def test_degraded_spec_leaf_falls_back_to_its_default(
            self, leaf, affected, degradation):
        """For each leaf key of ``object_story_spec`` and for each of the two
        degradations, the entry keeps its 31 keys in order and only the keys
        derived from that leaf change. ``page_id`` changes nothing, which is
        exactly the expectation: the branch does not read it.

        Requirements: 8.8
        """
        descriptor = _descriptor(_standard_creative_with_spec(**{leaf: degradation}))

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(**affected)

    @pytest.mark.parametrize(
        'degradation', LEAF_DEGRADATIONS, ids=LEAF_DEGRADATION_IDS,
    )
    @pytest.mark.parametrize(
        'leaf,affected', STANDARD_LINK_DATA_LEAVES,
        ids=_ids(STANDARD_LINK_DATA_LEAVES),
    )
    def test_degraded_link_data_leaf_falls_back_to_its_default(
            self, leaf, affected, degradation):
        """For each leaf key of ``object_story_spec.link_data`` and for each of
        the two degradations, the entry keeps its 31 keys in order and only the
        keys derived from that leaf change.

        Requirements: 8.8
        """
        descriptor = _descriptor(
            _standard_creative_with_link_data(**{leaf: degradation}),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(**affected)

    # -- No collaborator and no validator is involved (Requirement 8.9) -----

    def test_composition_touches_no_collaborator_and_no_validator(self):
        """0 calls on the four repository doubles, 0 invocations of
        ``MetaAdsValidator`` and ``MetaAdsPayloadBuilder``, and the stored
        creative left byte for byte as it was.

        Requirements: 8.9
        """
        creative = make_standard_creative()
        pristine = copy.deepcopy(creative)
        descriptor = _descriptor(creative)

        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    publish_repository):
            with patch('app.v2.use_cases.meta_ads.MetaAdsValidator') as validator, \
                    patch('app.v2.use_cases.meta_ads.MetaAdsPayloadBuilder') as builder:
                entry = use_case._build_standard_creative_published(0, descriptor)

            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                assert double.mock_calls == []

        assert validator.mock_calls == []
        assert builder.mock_calls == []
        assert entry == _expected_standard_entry()
        assert creative == pristine


class TestStandardCreativeEntryNonDictCallToAction:
    """``FacebookGetLaunchCampaignCreativesUseCase._build_standard_creative_published``
    with a truthy non-dict ``call_to_action`` or ``call_to_action.type``.

    Requirements: 16.1, 16.2, 16.3
    """

    @pytest.mark.parametrize(
        'call_to_action', ('LEARN_MORE', 1, ['SIGN_UP']),
        ids=('str', 'int', 'list'),
    )
    def test_non_dict_call_to_action_is_treated_as_empty(self, call_to_action):
        """A truthy non-dict ``call_to_action`` does not raise and yields
        ``call_to_action_types == []`` and
        ``call_to_action_types_valid_amount is False``; every other key keeps
        the baseline value.

        Requirements: 16.1, 16.3
        """
        descriptor = _descriptor(
            make_standard_creative(call_to_action=call_to_action),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry['call_to_action_types'] == []
        assert entry['call_to_action_types_valid_amount'] is False
        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(
            call_to_action_types=[],
            call_to_action_types_valid_amount=False,
        )

    def test_non_dict_call_to_action_type_is_treated_as_empty(self):
        """A dict ``call_to_action`` whose ``type`` is a truthy non-dict does
        not raise and yields ``call_to_action_types == [{}]`` and
        ``call_to_action_types_valid_amount is False``.

        Requirements: 16.2, 16.3
        """
        descriptor = _descriptor(
            make_standard_creative(call_to_action={'type': 'LEARN_MORE'}),
        )

        with patched_use_case() as (use_case, _, _, _, _):
            entry = use_case._build_standard_creative_published(0, descriptor)

        assert entry['call_to_action_types'] == [{}]
        assert entry['call_to_action_types_valid_amount'] is False
        assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
        assert entry == _expected_standard_entry(
            call_to_action_types=[{}],
            call_to_action_types_valid_amount=False,
        )


class TestCreativesDispatch:
    """``FacebookGetLaunchCampaignCreativesUseCase._build_creatives``.

    Requirements: 7.5, 8.1, 8.2, 8.7
    """

    # -- The dispatch is decided by the mode (Requirement 8.2) --------------

    def test_dynamic_mode_reads_the_asset_feed_spec_and_never_the_other_one(self):
        """With **both** specifications present and distinguishable, the
        ``DYNAMIC`` mode produces the values of ``asset_feed_spec`` and not a
        single one of ``object_story_spec``: the dispatch is decided by the
        already validated Campaign_Mode, not by the presence of a
        specification.

        Requirements: 8.2
        """
        descriptors = [_descriptor(_creative_with_both_specifications())]

        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives(
                descriptors, CreativeType.DYNAMIC.value,
            )

        assert len(creatives) == 1
        entry = creatives[0]
        assert entry['adchannel_id'] == 1111
        assert entry['min_daily_budget'] == 11
        assert entry['titles'] == [{'text': 'DYN Titular', 'valid_length': True}]
        assert entry['proposal_url'] == 'https://example.test/DYN-landing'
        assert entry['locations'] == [{'key': 'DYN', 'name': 'Dinámica'}]
        assert 'STD' not in repr(entry)
        assert 2222 not in entry.values()

    def test_standard_mode_reads_the_object_story_spec_and_never_the_other_one(self):
        """The mirror case: with both specifications present, the ``STANDARD``
        mode produces the values of ``object_story_spec`` and not a single one
        of ``asset_feed_spec``.

        Requirements: 8.2
        """
        descriptors = [_descriptor(_creative_with_both_specifications())]

        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives(
                descriptors, CreativeType.STANDARD.value,
            )

        assert len(creatives) == 1
        entry = creatives[0]
        assert entry['adchannel_id'] == 2222
        assert entry['min_daily_budget'] == 22
        assert entry['titles'] == [{'text': 'STD Titular', 'valid_length': True}]
        assert entry['proposal_url'] == 'https://example.test/STD-landing'
        assert entry['locations'] == [{'key': 'STD', 'name': 'Estándar'}]
        assert 'DYN' not in repr(entry)
        assert 1111 not in entry.values()

    @pytest.mark.parametrize(
        'campaign_mode,expected_adchannel_id',
        ((CreativeType.DYNAMIC.value, 1111), (CreativeType.STANDARD.value, 2222)),
    )
    def test_the_two_modes_produce_the_31_keys_in_order(
            self, campaign_mode, expected_adchannel_id):
        """Both branches produce the same 31 keys, in the same order, and 0
        keys carrying a Meta identifier.

        Requirements: 8.1, 8.7
        """
        descriptors = [_descriptor(_creative_with_both_specifications())]

        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives(descriptors, campaign_mode)

        for entry in creatives:
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
            assert _meta_prefixed_keys(entry) == []
            assert entry['adchannel_id'] == expected_adchannel_id

    # -- ``idx`` is the zero based index (Requirement 7.5) -----------------

    @pytest.mark.parametrize('campaign_mode', SUPPORTED_CAMPAIGN_MODES)
    def test_idx_is_the_zero_based_index_of_each_entry(self, campaign_mode):
        """``idx`` is the zero based position of the entry within the final
        list, which preserves the order of the descriptors received.

        Requirements: 7.5
        """
        descriptors = [
            _descriptor(_creative_with_both_specifications()) for _ in range(4)
        ]

        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives(descriptors, campaign_mode)

        assert len(creatives) == len(descriptors)
        assert [entry['idx'] for entry in creatives] == [0, 1, 2, 3]

    @pytest.mark.parametrize('campaign_mode', SUPPORTED_CAMPAIGN_MODES)
    def test_the_order_of_the_descriptors_is_preserved(self, campaign_mode):
        """Entry ``i`` is composed from descriptor ``i``: the identifiers of the
        entries follow the order of the descriptors received, not a sorted one.

        Requirements: 7.5
        """
        descriptors = [
            _descriptor(make_dynamic_creative(creative_id=creative_id,
                                              ad_id=creative_id + 1))
            if campaign_mode == CreativeType.DYNAMIC.value
            else _descriptor(make_standard_creative(creative_id=creative_id,
                                                    ad_id=creative_id + 1))
            for creative_id in (300, 100, 200)
        ]

        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives(descriptors, campaign_mode)

        assert [entry['adset_id'] for entry in creatives] == [300, 100, 200]
        assert [entry['ad_id'] for entry in creatives] == [301, 101, 201]
        assert [entry['idx'] for entry in creatives] == [0, 1, 2]

    @pytest.mark.parametrize('campaign_mode', SUPPORTED_CAMPAIGN_MODES)
    def test_an_empty_descriptor_list_produces_an_empty_creatives_list(
            self, campaign_mode):
        """A list of 0 descriptors composes 0 entries: the loop is the only
        thing the method does, so a fresh list is returned.

        Requirements: 7.5
        """
        with patched_use_case() as (use_case, _, _, _, _):
            creatives = use_case._build_creatives([], campaign_mode)

        assert creatives == []

# ---------------------------------------------------------------------------
# Query_Result composition (Requirements 4.5, 7.3, 7.6, 7.7, 7.8, 7.9)
#
# ``_build_result`` is invoked **directly** on the instance built by
# ``patched_use_case``: it is the last pure projection of the chain, it
# receives the already resolved Campaña_Objetivo, the already resolved
# Campaign_Setup and the already composed ``creatives`` list, and it touches no
# collaborator, so no repository double needs to be configured beyond the
# scaffolding the context manager already provides. ``deny_network`` stays
# active, accrediting 0 outgoing requests.
# ---------------------------------------------------------------------------

#: The three keys of the Query_Result (Requirement 7.8), with no debug,
#: pagination nor status key.
RESULT_KEYS = {'campaign', 'creatives', 'meta_url'}

#: The seven keys of the ``campaign`` block, in the exact order of Requirement
#: 7.3. Frozen as a tuple so an assertion compares the key *set* **and** the
#: key *order* in a single comparison, as ``CREATIVE_ENTRY_KEYS`` does for a
#: Creative_Entry.
CAMPAIGN_BLOCK_KEYS = (
    'name',
    'channel_name',
    'creatives_no',
    'objective',
    'optimization_goal',
    'mode',
    'conversion_event',
)

#: The fragment of the ad-set edition URL that Requirement 7.7 keeps out of
#: scope: no key of the Query_Result may carry a URL of that shape.
ADSETS_EDIT_FRAGMENT = 'adsets/edit'


def _expected_meta_url(meta_account_id='1234567890', meta_campaign_id='987654321'):
    """Return the ``meta_url`` of Requirement 7.6 for the two given
    identifiers, spelled out here as a **literal** instead of reusing the
    ``_META_CAMPAIGN_URL_TEMPLATE`` class constant.

    Written that way on purpose: pinning the URL shape against the literal of
    the requirement is the whole point of the assertion, and reading it from
    the production constant would make the test agree with any future typo in
    it.

    Requirements: 7.6, 11.4
    """
    return (
        'https://adsmanager.facebook.com/adsmanager/manager/campaigns/edit'
        '?act={}&selected_campaign_ids={}'.format(meta_account_id, meta_campaign_id)
    )


def _expected_campaign_block(name='Campaña Primavera', creatives_no=0,
                             objective='OUTCOME_TRAFFIC',
                             optimization_goal='LINK_CLICKS',
                             mode=CreativeType.DYNAMIC.value,
                             conversion_event=None):
    """Return the ``campaign`` block expected for the canonical fixtures, with
    its seven keys in the order of Requirement 7.3.

    The defaults are the canonical values of ``make_campaign()`` and
    ``make_campaign_setup()``, so a case only states what it changes;
    ``conversion_event`` defaults to ``None`` because the canonical
    ``make_campaign_setup()`` does not declare ``meta_conversion_event``.

    Requirements: 7.3, 11.4
    """
    return {
        'name': name,
        'channel_name': 'Meta',
        'creatives_no': creatives_no,
        'objective': objective,
        'optimization_goal': optimization_goal,
        'mode': mode,
        'conversion_event': conversion_event,
    }


def _creative_entries(count):
    """Return ``count`` fresh canonical ``DYNAMIC`` Creative_Entries, already
    indexed, as ``_build_creatives`` would hand them to ``_build_result``.

    Requirements: 7.3, 11.4
    """
    return [_expected_dynamic_entry(idx=idx) for idx in range(count)]


def _iter_strings(node):
    """Yield every string reachable from ``node``, keys and values alike.

    Requirement 7.7 fixes at 0 the number of keys of the Query_Result carrying
    an ad-set edition URL, so the check has to look at the whole structure and
    not only at ``meta_url``.

    Requirements: 7.7, 11.4
    """
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                yield key
            for string in _iter_strings(value):
                yield string
    elif isinstance(node, list):
        for value in node:
            for string in _iter_strings(value):
                yield string


class TestResultComposition:
    """``FacebookGetLaunchCampaignCreativesUseCase._build_result``.

    Requirements: 4.5, 7.3, 7.6, 7.7, 7.8, 7.9
    """

    # -- The three keys of the Query_Result (Requirements 7.8, 7.9) ---------

    def test_result_has_exactly_the_three_keys(self):
        """The key set is equal by exact comparison to the three keys
        ``campaign``, ``creatives`` and ``meta_url``, with no additional debug,
        pagination nor status key.

        Requirements: 7.8
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(2),
            )

        assert set(result) == RESULT_KEYS

    def test_result_is_a_plain_dict_and_not_a_tuple(self):
        """The Query_Result is returned as the single return value: a ``dict``,
        neither wrapped in a tuple nor accompanied by an HTTP status code.

        Requirements: 7.9
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(2),
            )

        assert not isinstance(result, tuple)
        assert isinstance(result, dict)
        assert len(result) == 3

    def test_the_creatives_list_received_is_the_one_exposed(self):
        """The ``creatives`` key holds the very list received, by identity: the
        stage composes the envelope and never recomposes, reorders nor copies
        the entries.

        Requirements: 7.3, 7.8
        """
        creatives = _creative_entries(3)

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), creatives,
            )

        assert result['creatives'] is creatives

    # -- The ``campaign`` block of seven keys (Requirement 7.3) ---

    def test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures(self):
        """The ``campaign`` block is equal by exact comparison to the seven-key
        dict derived from the canonical fixtures, and its keys come in the order
        fixed by Requirement 7.3.

        Requirements: 7.3
        """
        creatives = _creative_entries(2)

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), creatives,
            )

        assert result['campaign'] == _expected_campaign_block(creatives_no=2)
        assert tuple(result['campaign'].keys()) == CAMPAIGN_BLOCK_KEYS

    def test_campaign_block_reflects_the_values_of_a_non_canonical_fixture(self):
        """``name`` comes from the Campaña_Objetivo and ``objective``,
        ``optimization_goal``, ``mode`` and ``conversion_event`` from the four
        attributes of the Campaign_Setup, whatever their values.

        Requirements: 7.3
        """
        campaign = make_campaign(name='Campaña Verano')
        campaign_setup = make_campaign_setup(
            meta_campaign_objective='OUTCOME_SALES',
            meta_optimization_goal='OFFSITE_CONVERSIONS',
            meta_campaign_mode=CreativeType.STANDARD.value,
            meta_conversion_event='LEAD',
        )

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                campaign, campaign_setup, _creative_entries(1),
            )

        assert result['campaign'] == _expected_campaign_block(
            name='Campaña Verano',
            creatives_no=1,
            objective='OUTCOME_SALES',
            optimization_goal='OFFSITE_CONVERSIONS',
            mode=CreativeType.STANDARD.value,
            conversion_event='LEAD',
        )
        assert result['campaign']['conversion_event'] == 'LEAD'

    def test_channel_name_is_the_literal_meta(self):
        """``channel_name`` is the literal string ``Meta``, taken from the class
        constant and never from a fixture value.

        Requirements: 7.3
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(2),
            )

        assert result['campaign']['channel_name'] == 'Meta'
        assert FacebookGetLaunchCampaignCreativesUseCase._CHANNEL_NAME == 'Meta'

    @pytest.mark.parametrize('creatives_no', [0, 1, 2, 5])
    def test_creatives_no_equals_the_length_of_the_creatives_list(
            self, creatives_no):
        """``creatives_no`` is the number of elements of the ``creatives`` list,
        recomputed from the list itself and not read from any attribute.

        Requirements: 7.3
        """
        creatives = _creative_entries(creatives_no)

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), creatives,
            )

        assert result['campaign']['creatives_no'] == creatives_no
        assert result['campaign']['creatives_no'] == len(result['creatives'])

    def test_only_the_name_is_read_from_the_resolved_campaign(self):
        """Of the Campaña_Objetivo only ``attributes.name`` is consulted: the
        recording node registers that single key lookup.

        Requirements: 4.5, 7.3
        """
        campaign, attributes = _campaign_with_recording_attributes()

        with patched_use_case() as (use_case, _, _, _, _):
            use_case._build_result(
                campaign, make_campaign_setup(), _creative_entries(2),
            )

        assert attributes.consulted_keys == ['name']

    def test_absent_name_and_absent_attributes_yield_none_without_raising(self):
        """A campaign without ``name``, and a campaign without the whole
        ``attributes`` node, both compose ``campaign.name`` as ``None`` instead
        of raising.

        Requirements: 4.5, 7.3
        """
        with patched_use_case() as (use_case, _, _, _, _):
            without_name = use_case._build_result(
                make_campaign(name=ABSENT), make_campaign_setup(),
                _creative_entries(1),
            )
            without_attributes = use_case._build_result(
                make_campaign(attributes=ABSENT), make_campaign_setup(),
                _creative_entries(1),
            )

        assert without_name['campaign']['name'] is None
        assert without_attributes['campaign']['name'] is None

    def test_absent_setup_attributes_yield_none_in_the_four_keys(self):
        """A Campaign_Setup without the ``attributes`` node composes the four
        keys ``objective``, ``optimization_goal``, ``mode`` and
        ``conversion_event`` as ``None``, keeping the seven keys of the block.

        Requirements: 7.3
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(attributes=ABSENT),
                _creative_entries(1),
            )

        assert tuple(result['campaign'].keys()) == CAMPAIGN_BLOCK_KEYS
        assert result['campaign']['objective'] is None
        assert result['campaign']['optimization_goal'] is None
        assert result['campaign']['mode'] is None
        assert result['campaign']['conversion_event'] is None

    # -- ``meta_url`` (Requirements 7.6, 7.7) ------------------------------

    def test_meta_url_equals_the_url_built_with_the_two_setup_identifiers(self):
        """``meta_url`` is equal by exact string comparison to the URL of
        Requirement 7.6 built with the ``meta_account_id`` and the
        ``meta_campaign_id`` of the fixture, and carries no ad-set edition URL.

        Requirements: 7.6, 7.7
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(2),
            )

        assert result['meta_url'] == _expected_meta_url('1234567890', '987654321')
        assert ADSETS_EDIT_FRAGMENT not in result['meta_url']

    def test_meta_url_reflects_other_identifiers_of_the_persisted_record(self):
        """The two identifiers are read from the already persisted
        Campaign_Setup record, whatever their values, and never from a freshly
        created value.

        Requirements: 7.6
        """
        campaign_setup = make_campaign_setup(
            meta_account_id='act_555', meta_campaign_id='camp_999',
        )

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), campaign_setup, _creative_entries(1),
            )

        assert result['meta_url'] == _expected_meta_url('act_555', 'camp_999')
        assert ADSETS_EDIT_FRAGMENT not in result['meta_url']

    def test_absent_identifiers_keep_the_url_shape_without_raising(self):
        """With both identifiers absent from the Campaign_Setup the URL keeps
        its shape, interpolating the two missing values instead of raising.

        Requirements: 7.6
        """
        campaign_setup = make_campaign_setup(
            meta_account_id=ABSENT, meta_campaign_id=ABSENT,
        )

        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), campaign_setup, _creative_entries(1),
            )

        assert result['meta_url'] == _expected_meta_url(None, None)
        assert ADSETS_EDIT_FRAGMENT not in result['meta_url']

    def test_no_string_of_the_result_carries_an_adsets_edit_url(self):
        """0 keys of the Query_Result carry a URL of the form
        ``.../adsmanager/manager/adsets/edit?...``, which the specification
        keeps out of scope.

        Requirements: 7.7
        """
        with patched_use_case() as (use_case, _, _, _, _):
            result = use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(3),
            )

        assert [
            string for string in _iter_strings(result)
            if ADSETS_EDIT_FRAGMENT in string
        ] == []

    def test_meta_resources_is_never_read(self):
        """``meta_resources`` is present in the fixture and is **not** consulted:
        the composition reads the six attributes it needs and nothing else.

        Requirements: 7.3, 7.6, 7.7
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()
        assert 'meta_resources' in dict(attributes)

        with patched_use_case() as (use_case, _, _, _, _):
            use_case._build_result(
                make_campaign(), campaign_setup, _creative_entries(2),
            )

        assert 'meta_resources' not in attributes.consulted_keys
        assert set(attributes.consulted_keys) == {
            'meta_campaign_objective',
            'meta_optimization_goal',
            'meta_campaign_mode',
            'meta_conversion_event',
            'meta_account_id',
            'meta_campaign_id',
        }

    # -- Read-only, collaborator free composition (Requirements 7.8, 7.9) --

    def test_composition_touches_no_collaborator(self):
        """The stage is a pure projection: the four repository doubles register
        0 invocations, so no query and no write is emitted while composing.

        Requirements: 7.8, 7.9
        """
        with patched_use_case() as (use_case, account_repository,
                                    campaign_repository, ad_set_repository,
                                    campaign_channel_publish_repository):
            use_case._build_result(
                make_campaign(), make_campaign_setup(), _creative_entries(2),
            )

            for double in (account_repository, campaign_repository,
                           ad_set_repository,
                           campaign_channel_publish_repository):
                assert double.method_calls == []

    def test_composition_leaves_both_records_untouched(self):
        """Neither the Campaña_Objetivo nor the Campaign_Setup is modified: both
        stay equal to their initial deep copy after the composition.

        Requirements: 7.3, 7.6
        """
        campaign = make_campaign()
        campaign_setup = make_campaign_setup()
        pristine_campaign = copy.deepcopy(campaign)
        pristine_campaign_setup = copy.deepcopy(campaign_setup)

        with patched_use_case() as (use_case, _, _, _, _):
            use_case._build_result(campaign, campaign_setup, _creative_entries(2))

        assert campaign == pristine_campaign
        assert campaign_setup == pristine_campaign_setup

# ---------------------------------------------------------------------------
# End to end fixture of the main flow (Requirements 11.5, 11.6)
#
# The first scenario that goes through ``execute()``: two Ad_Sets_de_Consulta,
# two ads each and exactly one selected Ad_Channel per ad, so the walk yields
# four usable Published_Creatives whose order —the order of appearance of the
# ad-sets and, inside each of them, of the ads (Requirement 7.5)— is observable
# through the four distinct ``ad_id`` values.
# ---------------------------------------------------------------------------

#: The two arguments ``execute(brand_id, campaign_id)`` receives in every end
#: to end case, kept as module constants so each ``assert_called_once_with``
#: below reads against the very same values the fixture was built with.
MAIN_FLOW_BRAND_ID = 7
MAIN_FLOW_CAMPAIGN_ID = 41

#: The Cuenta_Padre the canonical end to end account declares through
#: ``attributes.parent_account.data.id`` (Requirement 3.4). Deliberately
#: different from the ``id`` of the account record itself (``1``), so the
#: fallback of Requirement 3.5 is distinguishable from it.
MAIN_FLOW_PARENT_ACCOUNT_ID = 3

#: The Channel_ID every selected ad-channel of the fixture declares through
#: ``attributes.channel_ref.data.id``: the second argument the Campaign_Setup
#: query must receive (Requirements 6.1, 7.1).
MAIN_FLOW_CHANNEL_ID = 2

#: The fixture, spelled out as ``(ad_set_id, ad_set_name, ((ad_id,
#: ad_channel_id), ...))``: two ad-sets, two ads each, one selected ad-channel
#: per ad. Every identifier is distinct, so an entry can be attributed to its
#: source without ambiguity and a reordering of the walk cannot pass unnoticed.
MAIN_FLOW_AD_SETS = (
    (120, 'Ad Set A', ((501, 9001), (502, 9002))),
    (121, 'Ad Set B', ((503, 9003), (504, 9004))),
)

#: The method names of the write side of a repository. Requirement 10.6 fixes
#: at 0 the number of writes of the whole use case, and the four doubles are
#: ``MagicMock`` instances, so a single accidental write would be recorded.
WRITE_METHOD_NAMES = ('update', 'create', 'put', 'post', 'delete')

#: The Published_Creative builder of each supported Modo_de_Campaña. The end to
#: end fixture is **the same** in both branches —same ad-sets, same ads, same
#: selected ad-channels, same identifiers— and only the shape of the stored
#: ``channel_creative`` changes, which is what makes the ``STANDARD`` case of
#: Requirement 11.6 the ``DYNAMIC`` case of Requirement 11.5 with a single
#: variable changed.
MAIN_FLOW_CREATIVE_BUILDERS = {
    CreativeType.DYNAMIC.value: make_dynamic_creative,
    CreativeType.STANDARD.value: make_standard_creative,
}

#: The expected-entry helper of each mode, counterpart of the builders above:
#: each one projects the literal baseline of its table of ``design.md``.
MAIN_FLOW_EXPECTED_ENTRY_BUILDERS = {
    CreativeType.DYNAMIC.value: _expected_dynamic_entry,
    CreativeType.STANDARD.value: _expected_standard_entry,
}


def _main_flow_ad(ad_set_id, ad_set_name, ad_id, ad_channel_id,
                  mode=CreativeType.DYNAMIC.value, **ad_channel_kwargs):
    """Build a fresh element of ``ads.data`` holding exactly one selected
    ad-channel whose ``channel_creative`` is the Published_Creative of the
    given ad-set and ad, in the given Modo_de_Campaña.

    The Published_Creative carries the ad-set identifiers (``creative_id`` and
    ``name``) and the ad identifiers (``ads[0].id`` and the ``ad_channel_id``
    of the specification of its mode), which is the shape the pre-check flow
    persists: one snapshot of the ad-set per ad-channel.

    Requirements: 5.3, 8.6, 11.4, 11.5, 11.6
    """
    return _ad_with_channel(
        ad_id=ad_id,
        ad_channel_id=ad_channel_id,
        channel_ref_id=MAIN_FLOW_CHANNEL_ID,
        channel_creative=MAIN_FLOW_CREATIVE_BUILDERS[mode](
            creative_id=ad_set_id,
            name=ad_set_name,
            ad_id=ad_id,
            ad_channel_id=ad_channel_id,
        ),
        **ad_channel_kwargs
    )


def _main_flow_response(mode=CreativeType.DYNAMIC.value):
    """Build a fresh ad-sets response for the two ad-sets of
    ``MAIN_FLOW_AD_SETS``, yielding four usable Published_Creatives of the
    given Modo_de_Campaña.

    Requirements: 7.5, 11.4, 11.5, 11.6
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(
            ad_set_id=ad_set_id,
            name=ad_set_name,
            ads_data=[
                _main_flow_ad(ad_set_id, ad_set_name, ad_id, ad_channel_id,
                              mode=mode)
                for ad_id, ad_channel_id in ads
            ],
        )
        for ad_set_id, ad_set_name, ads in MAIN_FLOW_AD_SETS
    ])


def _expected_main_flow_entries(mode=CreativeType.DYNAMIC.value):
    """Return the four Creative_Entries the fixture of the given mode must
    produce, already indexed, in the order of Requirement 7.5.

    Built from ``_expected_dynamic_entry`` / ``_expected_standard_entry``, so
    the 31 values stay pinned against the literal baseline of the corresponding
    table of ``design.md`` and only the four identifiers that vary per entry are
    overridden.

    Requirements: 7.5, 8.1, 11.4, 11.5, 11.6
    """
    expected_entry = MAIN_FLOW_EXPECTED_ENTRY_BUILDERS[mode]
    entries = []
    for ad_set_id, ad_set_name, ads in MAIN_FLOW_AD_SETS:
        for ad_id, ad_channel_id in ads:
            entries.append(expected_entry(
                idx=len(entries),
                name=ad_set_name,
                adset_id=ad_set_id,
                ad_id=ad_id,
                adchannel_id=ad_channel_id,
            ))
    return entries


def _fixture_channel_creatives(response):
    """Return every ``channel_creative`` of an ad-sets response, in walk order.

    Requirement 5.8 fixes the walk as read-only, so the immutability assertion
    needs a handle on the very dicts the descriptors reference.

    Requirements: 5.8, 11.4
    """
    return [
        ad_channel['attributes']['channel_creative']
        for ad_set in response['data']
        for ad in ad_set['attributes']['ads']['data']
        for ad_channel in ad['attributes']['ad_channels']['data']
    ]


@contextlib.contextmanager
def main_flow_use_case(account=_DEFAULT, campaign=_DEFAULT,
                       ad_sets_response=_DEFAULT, campaign_setup=_DEFAULT,
                       mode=CreativeType.DYNAMIC.value):
    """``patched_use_case`` pre-configured with the end to end fixture: the
    account that declares ``MAIN_FLOW_PARENT_ACCOUNT_ID``, the campaign of
    ``MAIN_FLOW_CAMPAIGN_ID``, the two ad-set response of the given
    Modo_de_Campaña and the canonical published Campaign_Setup declaring that
    very same mode.

    ``mode`` drives the two values that must agree for the dispatch of
    Requirement 8.2 to be exercised end to end —the shape of the stored
    ``channel_creative`` and the ``meta_campaign_mode`` of the Campaign_Setup—
    so a ``STANDARD`` case is the ``DYNAMIC`` one with a single argument
    changed. It is ignored for whichever of the two an explicit value is passed
    for.

    Every argument stays overridable —including with ``None``— so a case states
    only the part of the scenario it changes.

    Requirements: 11.2, 11.4, 11.5, 11.6
    """
    with patched_use_case(
        account=(
            make_account(parent_account_id=MAIN_FLOW_PARENT_ACCOUNT_ID)
            if account is _DEFAULT else account
        ),
        campaign=(
            make_campaign(campaign_id=MAIN_FLOW_CAMPAIGN_ID)
            if campaign is _DEFAULT else campaign
        ),
        ad_sets_response=(
            _main_flow_response(mode=mode) if ad_sets_response is _DEFAULT
            else ad_sets_response
        ),
        campaign_setup=(
            make_campaign_setup(meta_campaign_mode=mode)
            if campaign_setup is _DEFAULT else campaign_setup
        ),
    ) as patched:
        yield patched


class TestMainFlowDynamic:
    """``FacebookGetLaunchCampaignCreativesUseCase.execute`` in ``DYNAMIC``
    mode, end to end.

    Two Ad_Sets_de_Consulta with two ads each and one selected Ad_Channel per
    ad: the four stages of the chain resolve, the walk yields four usable
    Published_Creatives and the Resultado_de_Consulta exposes them with the 31
    keys of Requirement 8.1.

    Requirements: 3.4, 3.5, 5.8, 7.5, 7.8, 8.1, 10.6, 11.5, 11.19, 11.23
    """

    # -- The contract of the Resultado_de_Consulta (Requirements 7.8, 8.1) --

    def test_result_has_exactly_the_three_keys(self):
        """The key set of the Resultado_de_Consulta is equal by exact
        comparison to the three keys ``campaign``, ``creatives`` and
        ``meta_url``.

        Requirements: 7.8
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert set(result) == {'campaign', 'creatives', 'meta_url'}

    def test_creatives_count_equals_the_number_of_selected_ad_channels(self):
        """The ``creatives`` list holds one entry per selected Ad_Channel of the
        fixture: two ad-sets times two ads, hence four.

        Requirements: 7.5, 7.8
        """
        expected_count = sum(len(ads) for _, _, ads in MAIN_FLOW_AD_SETS)

        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert expected_count == 4
        assert len(result['creatives']) == expected_count

    def test_every_entry_exposes_the_31_keys_in_order(self):
        """Each Creative_Entry exposes the 31 keys of Requirement 8.1, as a
        *set* and in the fixed *order*.

        Requirements: 8.1
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

    def test_entries_equal_the_expected_dynamic_projection(self):
        """The four entries are equal, by exact dict comparison and in order, to
        the ``DYNAMIC`` projection of the four Published_Creatives of the
        fixture.

        Requirements: 7.5, 8.1
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['creatives'] == _expected_main_flow_entries()

    def test_idx_is_the_zero_based_index_of_each_entry(self):
        """``creatives[i]['idx'] == i`` for every ``i``: the index is the zero
        based position of the entry within the final list.

        Requirements: 7.5
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert [entry['idx'] for entry in result['creatives']] == [0, 1, 2, 3]
        for idx, entry in enumerate(result['creatives']):
            assert entry['idx'] == idx

    # -- The four read queries and their arguments (Requirements 10.6, 11.19)

    def test_the_four_repositories_are_invoked_once_with_the_expected_arguments(
            self):
        """One read query per repository, with the arguments derived from the
        fixture: the email from ``self.user_id``, the three values of the
        campaign query in order, the two of the ad-sets query and the
        ``campaign_id`` plus the resolved Channel_ID of the Campaign_Setup
        query.

        Requirements: 10.6, 11.19
        """
        with main_flow_use_case() as (use_case, account_repository,
                                      campaign_repository, ad_set_repository,
                                      publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            account_repository.get_by_email.assert_called_once_with(
                use_case.user_id,
            )
            campaign_repository.get_by_id_brand_and_account\
                .assert_called_once_with(
                    MAIN_FLOW_CAMPAIGN_ID,
                    MAIN_FLOW_BRAND_ID,
                    MAIN_FLOW_PARENT_ACCOUNT_ID,
                )
            _query_double(ad_set_repository).assert_called_once_with(
                MAIN_FLOW_CAMPAIGN_ID, MAIN_FLOW_BRAND_ID,
            )
            _setup_double(publish_repository).assert_called_once_with(
                MAIN_FLOW_CAMPAIGN_ID, MAIN_FLOW_CHANNEL_ID,
            )

    def test_the_two_arguments_are_forwarded_without_type_conversion(self):
        """``brand_id`` and ``campaign_id`` reach the two queries that consume
        them exactly as they were received, with no type conversion nor
        normalization.

        Requirements: 2.6, 11.19
        """
        with main_flow_use_case() as (use_case, _, campaign_repository,
                                      ad_set_repository, _):
            use_case.execute('7', '41')

            campaign_args = campaign_repository\
                .get_by_id_brand_and_account.call_args[0]
            ad_sets_args = _query_double(ad_set_repository).call_args[0]

        assert campaign_args == ('41', '7', MAIN_FLOW_PARENT_ACCOUNT_ID)
        assert [type(value) for value in campaign_args[:2]] == [str, str]
        assert ad_sets_args == ('41', '7')
        assert [type(value) for value in ad_sets_args] == [str, str]

    def test_exactly_four_read_queries_and_no_other_invocation(self):
        """Four read queries to Strapi per successful invocation, one per
        repository: each double registers exactly one method call.

        Requirements: 10.6
        """
        with main_flow_use_case() as (use_case, account_repository,
                                      campaign_repository, ad_set_repository,
                                      publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            doubles = (account_repository, campaign_repository,
                       ad_set_repository, publish_repository)
            assert [len(double.method_calls) for double in doubles] == [1, 1, 1, 1]

    # -- 0 writes and read-only walk (Requirements 5.8, 10.6, 11.23) --------

    def test_no_write_method_is_invoked_on_any_double(self):
        """0 invocations of ``update``, ``create``, ``put``, ``post`` and
        ``delete`` on the four doubles: the use case is read-only.

        Requirements: 10.6
        """
        with main_flow_use_case() as (use_case, account_repository,
                                      campaign_repository, ad_set_repository,
                                      publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            for double in (account_repository, campaign_repository,
                           ad_set_repository, publish_repository):
                for method_name in WRITE_METHOD_NAMES:
                    assert getattr(double, method_name).call_count == 0

    def test_every_channel_creative_stays_untouched(self):
        """Each ``channel_creative`` of the fixture stays equal, by exact
        comparison, to its initial deep copy after the execution: the walk
        neither writes on the stored structure nor mutates the descriptors it
        references.

        Requirements: 5.8, 11.23
        """
        response = _main_flow_response()
        channel_creatives = _fixture_channel_creatives(response)
        pristine_channel_creatives = copy.deepcopy(channel_creatives)
        pristine_response = copy.deepcopy(response)

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, _):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(channel_creatives) == 4
        for creative, pristine in zip(channel_creatives,
                                      pristine_channel_creatives):
            assert creative == pristine
        assert response == pristine_response

    # -- The Cuenta_Padre (Requirements 3.4, 3.5) ---------------------------

    def test_parent_account_is_the_declared_parent_when_the_node_is_present(
            self):
        """With ``attributes.parent_account.data.id`` present, the Cuenta_Padre
        forwarded to the campaign query is that identifier and not the ``id`` of
        the account record.

        Requirements: 3.4
        """
        account = make_account(
            parent_account_id=MAIN_FLOW_PARENT_ACCOUNT_ID, account_id=1,
        )

        with main_flow_use_case(account=account) as (use_case, _,
                                                     campaign_repository, _, _):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            parent_account = campaign_repository\
                .get_by_id_brand_and_account.call_args[0][2]

        assert parent_account == MAIN_FLOW_PARENT_ACCOUNT_ID
        assert parent_account != account['id']

    def test_parent_account_falls_back_to_the_own_id_without_the_node(self):
        """Without the ``attributes.parent_account`` node the Cuenta_Padre is the
        ``id`` of the account record itself, and the flow completes returning the
        four entries.

        Requirements: 3.5
        """
        account = make_account(parent_account_id=ABSENT, account_id=17)

        with main_flow_use_case(account=account) as (use_case, _,
                                                     campaign_repository, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            campaign_repository.get_by_id_brand_and_account\
                .assert_called_once_with(
                    MAIN_FLOW_CAMPAIGN_ID, MAIN_FLOW_BRAND_ID, 17,
                )

        assert len(result['creatives']) == 4

    @pytest.mark.parametrize('parent_account_node', [
        {'data': None},
        {'data': {}},
        {},
    ], ids=['data-none', 'data-empty-dict', 'parent-account-empty-dict'])
    def test_parent_account_falls_back_when_the_data_node_is_missing(
            self, parent_account_node):
        """With ``attributes.parent_account`` present but **without** a usable
        ``data`` node, the Cuenta_Padre is the ``id`` of the account record.

        Requirements: 3.5
        """
        account = make_account(account_id=17, attributes={
            'email': 'user@example.com',
            'parent_account': parent_account_node,
        })

        with main_flow_use_case(account=account) as (use_case, _,
                                                     campaign_repository, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

            parent_account = campaign_repository\
                .get_by_id_brand_and_account.call_args[0][2]

        assert parent_account == 17
        assert len(result['creatives']) == 4


# ---------------------------------------------------------------------------
# End to end main flow in ``STANDARD`` mode (Requirements 8.1, 8.4, 11.6)
#
# The very same fixture as ``TestMainFlowDynamic`` —two Ad_Sets_de_Consulta,
# two ads each, one selected Ad_Channel per ad, the same identifiers— with the
# single variable of the Modo_de_Campaña flipped: the stored
# Published_Creatives carry an ``object_story_spec`` and the Campaign_Setup
# declares ``meta_campaign_mode == CreativeType.STANDARD.value``.
# ---------------------------------------------------------------------------

#: The three keys of the Creative_Entry whose value Requirement 8.4 fixes as a
#: list of at most one dict of keys ``text`` and ``valid_length``.
STANDARD_TEXT_LIST_KEYS = ('titles', 'bodies', 'descriptions')

#: The two keys, in order, every element of those three lists carries.
TEXT_ITEM_KEYS = ('text', 'valid_length')

#: The three leaves of ``object_story_spec.link_data`` each one of those lists
#: is built from, paired with the entry key they feed.
STANDARD_TEXT_SOURCES = (
    ('name', 'titles'),
    ('message', 'bodies'),
    ('description', 'descriptions'),
)

#: The five ``*_max_amount`` keys the ``STANDARD`` branch fixes to the literal
#: ``1``, precisely because that branch exposes at most one text per key
#: (Requirement 8.4).
STANDARD_MAX_AMOUNT_KEYS = (
    'images_max_amount',
    'titles_max_amount',
    'bodies_max_amount',
    'descriptions_max_amount',
    'call_to_action_types_max_amount',
)


def _standard_main_flow_response_without_texts():
    """Build a fresh ``STANDARD`` end to end response whose four stored
    Published_Creatives have the three text leaves of
    ``object_story_spec.link_data`` **removed**.

    It is the lower bound of "at most one element" of Requirement 8.4: with no
    text to expose, the three lists must come out empty while the entry keeps
    its 31 keys.

    Requirements: 8.1, 8.4, 11.4, 11.6
    """
    response = _main_flow_response(mode=CreativeType.STANDARD.value)
    for creative in _fixture_channel_creatives(response):
        spec = creative['ads'][0]['adCreative']['object_story_spec']
        for leaf, _ in STANDARD_TEXT_SOURCES:
            del spec['link_data'][leaf]
    return response


class TestMainFlowStandard:
    """``FacebookGetLaunchCampaignCreativesUseCase.execute`` in ``STANDARD``
    mode, end to end.

    Same fixture as ``TestMainFlowDynamic`` in the other Modo_de_Campaña: the
    key contract of the Entrada_de_Creativo is invariant across branches, and
    ``titles``, ``bodies`` and ``descriptions`` come out as lists of at most one
    element of keys ``text`` and ``valid_length``.

    Requirements: 8.1, 8.4, 11.6
    """

    # -- The same 31 keys as the ``DYNAMIC`` branch (Requirement 8.1) --------

    def test_result_has_the_three_keys_and_the_four_expected_entries(self):
        """The envelope is the same in both branches: the three keys of the
        Resultado_de_Consulta and one entry per selected Ad_Channel of the
        fixture.

        Requirements: 8.1, 11.6
        """
        expected_count = sum(len(ads) for _, _, ads in MAIN_FLOW_AD_SETS)

        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert set(result) == {'campaign', 'creatives', 'meta_url'}
        assert expected_count == 4
        assert len(result['creatives']) == expected_count

    def test_every_entry_exposes_the_31_keys_in_order(self):
        """Each Creative_Entry exposes the 31 keys of Requirement 8.1, as a
        *set* and in the fixed *order*: the contract does not depend on the
        branch that composed it.

        Requirements: 8.1, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

    def test_the_key_contract_is_identical_to_the_dynamic_branch(self):
        """The same fixture executed once in each mode yields entries with the
        very same key tuple: the 31 keys of Requirement 8.1 are the same set in
        the same order in both branches.

        Requirements: 8.1, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            standard = use_case.execute(
                MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
            )
        with main_flow_use_case(mode=CreativeType.DYNAMIC.value) as (
                use_case, _, _, _, _):
            dynamic = use_case.execute(
                MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
            )

        assert len(standard['creatives']) == len(dynamic['creatives'])
        for standard_entry, dynamic_entry in zip(standard['creatives'],
                                                 dynamic['creatives']):
            assert entry_keys_in_order(standard_entry) \
                == entry_keys_in_order(dynamic_entry)

    def test_entries_equal_the_expected_standard_projection(self):
        """The four entries are equal, by exact dict comparison and in order, to
        the ``STANDARD`` projection of the four Published_Creatives of the
        fixture: the branch that ran is the one the Campaign_Setup declares.

        Requirements: 8.1, 8.4, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['creatives'] == _expected_main_flow_entries(
            mode=CreativeType.STANDARD.value,
        )

    # -- ``titles``, ``bodies`` and ``descriptions`` (Requirement 8.4) -------

    @pytest.mark.parametrize('entry_key', STANDARD_TEXT_LIST_KEYS)
    def test_text_lists_hold_at_most_one_item_of_two_keys(self, entry_key):
        """``titles``, ``bodies`` and ``descriptions`` are lists of at most one
        element, and each element carries exactly the keys ``text`` and
        ``valid_length``.

        Requirements: 8.4, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            value = entry[entry_key]
            assert isinstance(value, list)
            assert len(value) <= 1
            for item in value:
                assert tuple(item.keys()) == TEXT_ITEM_KEYS

    @pytest.mark.parametrize('entry_key', STANDARD_TEXT_LIST_KEYS)
    def test_text_lists_hold_exactly_one_item_for_the_canonical_fixture(
            self, entry_key):
        """With the three texts present in ``link_data``, each list holds
        exactly one element whose ``text`` is that of the fixture and whose
        ``valid_length`` is the corresponding ``*_valid`` flag.

        Requirements: 8.4, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        expected = STANDARD_BASELINE_ENTRY[entry_key]
        assert len(expected) == 1
        for entry in result['creatives']:
            assert entry[entry_key] == expected

    def test_text_lists_are_empty_when_the_three_texts_are_absent(self):
        """With the three text leaves removed from ``link_data`` the three lists
        come out empty —the lower bound of "at most one element"— and the entry
        keeps its 31 keys.

        Requirements: 8.1, 8.4, 11.6
        """
        response = _standard_main_flow_response_without_texts()

        with main_flow_use_case(mode=CreativeType.STANDARD.value,
                                ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 4
        for entry in result['creatives']:
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS
            for entry_key in STANDARD_TEXT_LIST_KEYS:
                assert entry[entry_key] == []

    @pytest.mark.parametrize('leaf,entry_key', STANDARD_TEXT_SOURCES)
    def test_each_text_list_is_empty_when_its_own_leaf_is_absent(
            self, leaf, entry_key):
        """Removing a single text leaf empties **its** list and leaves the other
        two with their single element: each list is built from its own leaf.

        Requirements: 8.4, 11.6
        """
        response = _main_flow_response(mode=CreativeType.STANDARD.value)
        for creative in _fixture_channel_creatives(response):
            spec = creative['ads'][0]['adCreative']['object_story_spec']
            del spec['link_data'][leaf]

        with main_flow_use_case(mode=CreativeType.STANDARD.value,
                                ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            assert entry[entry_key] == []
            for other_key in STANDARD_TEXT_LIST_KEYS:
                if other_key != entry_key:
                    assert len(entry[other_key]) == 1

    def test_the_five_max_amount_keys_are_the_literal_one(self):
        """The five ``*_max_amount`` keys are the literal ``1`` in the
        ``STANDARD`` branch, which is the counterpart of exposing at most one
        text per key.

        Requirements: 8.4, 11.6
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            for key in STANDARD_MAX_AMOUNT_KEYS:
                assert entry[key] == 1

# ---------------------------------------------------------------------------
# Parity with the launch use case (Requirements 8.3, 8.4, 8.8, 11.7)
#
# The duplication adopted in decision D of ``design.md`` is a deliberate
# technical debt: the 31 keys of the Entrada_de_Creativo are composed twice,
# once by this use case and once by
# ``FacebookLaunchCampaignUseCase._build_response()``. The class below is where
# that debt is pinned down: the comparison is made against the **real**
# production method, never against a literal baseline, so any future divergence
# in *either* of the two implementations breaks it.
#
# ``FacebookLaunchCampaignUseCase`` is **not modified** in a single line
# (Requirement 1.5): it is instantiated with test doubles and the four
# attributes ``_build_response()`` reads —``campaign_mode``,
# ``campaign_objective``, ``campaign_optimization_goal`` and
# ``ad_account_id``— are assigned directly on the instance (NFR *Testability*).
#
# Scope of the comparison: the Entrada_de_Creativo. Decision D-4 (normalizing
# ``adCreative`` and the two specifications with ``or {}``) is a strict widening
# of the launch behaviour, so the equality is only observable on the fixtures
# where the reference method does not raise. In the ``DYNAMIC`` branch that
# excludes an absent or ``None`` ``adCreative``, which the launch branch reads
# unnormalized; every other degradation of the tables of ``design.md`` is
# compared here.
# ---------------------------------------------------------------------------

#: Patch target of the only extra dependency ``FacebookLaunchCampaignUseCase``
#: resolves in its ``__init__`` beyond the two repositories this suite already
#: patches. Same rule as the four targets above: the namespace of the
#: *consuming* module.
AD_CHANNEL_REPOSITORY_TARGET = 'app.v2.use_cases.meta_ads.AdChannelRepository'

#: The values assigned to the four attributes ``_build_response()`` reads. They
#: mirror the canonical ``make_campaign_setup()`` fixture, which is what the
#: launch flow would have loaded into those attributes through its own
#: ``_get_campaign_setup()``.
PARITY_CAMPAIGN_ID = 41
PARITY_CAMPAIGN_NAME = 'Campaña Primavera'
PARITY_AD_ACCOUNT_ID = '1234567890'
PARITY_CAMPAIGN_OBJECTIVE = 'OUTCOME_TRAFFIC'
PARITY_OPTIMIZATION_GOAL = 'LINK_CLICKS'

#: Three Published_Creatives with distinct identifiers, so "the same index"
#: is a meaningful claim: an entry mixed up with another one, or a list built in
#: a different order, cannot pass the comparison.
PARITY_CREATIVES = (
    (120, 'Ad Set A', 501, 9001),
    (121, 'Ad Set B', 502, 9002),
    (122, 'Ad Set C', 503, 9003),
)

#: The leaf keys of the canonical ``asset_feed_spec``, read from the builder
#: itself so a new key of the fixture is covered without touching this list.
DYNAMIC_SPEC_KEYS = tuple(_make_dynamic_asset_feed_spec())

#: The leaf keys of the canonical ``object_story_spec`` and of its ``link_data``
#: node, each without the nested node the next list covers.
STANDARD_SPEC_KEYS = tuple(
    key for key in _make_standard_object_story_spec() if key != 'link_data'
)
STANDARD_LINK_DATA_KEYS = tuple(
    key for key in _make_standard_object_story_spec()['link_data']
    if key != 'call_to_action'
)


@contextlib.contextmanager
def launch_use_case(mode):
    """Yield a ``FacebookLaunchCampaignUseCase`` built **without real
    dependencies** and with the four attributes ``_build_response()`` reads
    assigned directly.

    Its ``__init__`` instantiates three repositories, so the three classes are
    patched in the namespace of the consuming module before the construction,
    exactly as ``patched_use_case`` does for the use case under test. Nothing
    else of the launch flow is touched: ``_build_response()`` is invoked as the
    production code invokes it, on a real instance of the real class.

    Requirements: 8.3, 8.4, 11.7
    """
    with patch(AD_CHANNEL_REPOSITORY_TARGET), \
            patch(CAMPAIGN_REPOSITORY_TARGET), \
            patch(CAMPAIGN_CHANNEL_PUBLISH_REPOSITORY_TARGET):
        use_case = FacebookLaunchCampaignUseCase('user@example.com', {})

        use_case.campaign_mode = mode
        use_case.campaign_objective = PARITY_CAMPAIGN_OBJECTIVE
        use_case.campaign_optimization_goal = PARITY_OPTIMIZATION_GOAL
        use_case.ad_account_id = PARITY_AD_ACCOUNT_ID

        yield use_case


def _launch_entries(creatives, mode):
    """Return the Creative_Entries the **real**
    ``FacebookLaunchCampaignUseCase._build_response()`` produces for the given
    Published_Creatives in the given Modo_de_Campaña.

    The launch method receives the list of stored ad-set snapshots as its third
    argument, which is precisely the list of ``channel_creative`` dicts the
    traversal of this use case accumulates, so both sides are fed the very same
    objects.

    Requirements: 8.3, 8.4, 11.7
    """
    with launch_use_case(mode) as launch:
        return launch._build_response(
            PARITY_CAMPAIGN_ID, {'name': PARITY_CAMPAIGN_NAME}, creatives,
        )['creatives']


def _use_case_entries(creatives, mode):
    """Return the Creative_Entries the use case under test composes for the same
    Published_Creatives, through the real dispatch of ``_build_creatives``.

    The descriptors carry ``DESCRIPTOR_ADCHANNEL_ID``, deliberately different
    from the ``ad_channel_id`` of both specifications: parity must hold anyway,
    because both implementations read that value from the specification
    (Requirement 8.6).

    Requirements: 8.3, 8.4, 11.7
    """
    with patched_use_case() as (use_case, _, _, _, _):
        return use_case._build_creatives(
            [_descriptor(creative) for creative in creatives], mode,
        )


def _parity_creatives(mode):
    """Build the three fresh Published_Creatives of ``PARITY_CREATIVES`` in the
    given Modo_de_Campaña.

    Requirements: 11.4, 11.7
    """
    builder = MAIN_FLOW_CREATIVE_BUILDERS[mode]
    return [
        builder(creative_id=creative_id, name=name, ad_id=ad_id,
                ad_channel_id=ad_channel_id)
        for creative_id, name, ad_id, ad_channel_id in PARITY_CREATIVES
    ]


def _assert_parity(creatives, mode):
    """Assert that both implementations compose, for the very same
    Published_Creatives, the very same Creative_Entries: equal by **exact dict
    comparison**, index by index, with the same key order.

    The same objects are handed to both sides, and the fixture is checked
    against its initial deep copy afterwards, so the agreement cannot come from
    one implementation having mutated the shared input.

    Requirements: 8.3, 8.4, 8.8, 11.7
    """
    pristine = copy.deepcopy(creatives)

    expected = _launch_entries(creatives, mode)
    actual = _use_case_entries(creatives, mode)

    assert creatives == pristine
    assert len(actual) == len(creatives)
    assert len(expected) == len(creatives)

    for idx, (entry, launch_entry) in enumerate(zip(actual, expected)):
        assert entry == launch_entry, (
            f"divergence at index {idx} in mode {mode}: "
            f"{[key for key in set(entry) | set(launch_entry) if entry.get(key) != launch_entry.get(key)]}"
        )
        assert entry_keys_in_order(entry) == entry_keys_in_order(launch_entry)
        assert entry['idx'] == idx

    assert actual == expected


class TestParityWithLaunchUseCase:
    """The Entrada_de_Creativo of this use case equals the one
    ``FacebookLaunchCampaignUseCase._build_response()`` produces.

    For the same Published_Creative fixture and the same index, the two
    compositions are compared by **exact dict comparison**, once in ``DYNAMIC``
    and once in ``STANDARD``, against the real production method and never
    against a literal baseline. It is the test carrying the technical debt of
    the duplication adopted in decision D of ``design.md``: any future
    divergence in **either** of the two implementations of the 31 keys breaks
    it.

    Requirements: 8.3, 8.4, 8.8, 11.7
    """

    # -- The canonical fixture, once per branch (Requirements 8.3, 8.4) -----

    def test_dynamic_entries_equal_the_launch_use_case_entries(self):
        """In ``DYNAMIC`` mode the three entries are equal, by exact dict
        comparison and index by index, to the three the launch use case composes
        from the same Published_Creatives.

        Requirements: 8.3, 11.7
        """
        _assert_parity(
            _parity_creatives(CreativeType.DYNAMIC.value),
            CreativeType.DYNAMIC.value,
        )

    def test_standard_entries_equal_the_launch_use_case_entries(self):
        """In ``STANDARD`` mode the three entries are equal, by exact dict
        comparison and index by index, to the ones
        ``_build_standard_creative_published()`` of the launch use case composes
        from the same Published_Creatives.

        Requirements: 8.4, 11.7
        """
        _assert_parity(
            _parity_creatives(CreativeType.STANDARD.value),
            CreativeType.STANDARD.value,
        )

    @pytest.mark.parametrize('mode', [
        CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
    ])
    def test_a_single_creative_yields_the_same_single_entry(self, mode):
        """The lower bound of the comparison: one Published_Creative, one entry,
        equal in both implementations in both modes.

        Requirements: 8.3, 8.4, 11.7
        """
        _assert_parity([MAIN_FLOW_CREATIVE_BUILDERS[mode]()], mode)

    # -- The same defaults on a degraded fixture (Requirement 8.8) ----------

    @pytest.mark.parametrize('spec_key', DYNAMIC_SPEC_KEYS)
    def test_dynamic_parity_holds_with_each_spec_leaf_absent(self, spec_key):
        """Removing any leaf key of ``asset_feed_spec`` keeps the parity: both
        implementations fall back to the very same default for that key.

        Requirements: 8.3, 8.8, 11.7
        """
        _assert_parity(
            [_dynamic_creative_with(**{spec_key: ABSENT})],
            CreativeType.DYNAMIC.value,
        )

    @pytest.mark.parametrize('degradation', [
        {'asset_feed_spec': ABSENT},
        {'asset_feed_spec': {}},
        {'proposal_locations': ABSENT},
        {'name': ABSENT},
        {'daily_budget': ABSENT},
    ], ids=['spec-absent', 'spec-empty', 'proposal-locations-absent',
            'name-absent', 'daily-budget-absent'])
    def test_dynamic_parity_holds_with_the_upper_levels_degraded(
            self, degradation):
        """The parity survives the degradation of the levels above the leaves
        that the launch branch tolerates: an absent or empty ``asset_feed_spec``
        and the three keys read from the stored ad-set itself.

        An absent or ``None`` ``adCreative`` is deliberately left out: the
        launch branch reads it unnormalized and raises, so the equality is not
        observable there. Decision D-4 widens that case and the widening is,
        by construction, not a divergence.

        Requirements: 8.3, 8.8, 11.7
        """
        _assert_parity(
            [make_dynamic_creative(**degradation)], CreativeType.DYNAMIC.value,
        )

    @pytest.mark.parametrize('spec_key', STANDARD_SPEC_KEYS)
    def test_standard_parity_holds_with_each_spec_leaf_absent(self, spec_key):
        """Removing any leaf key of ``object_story_spec`` keeps the parity.

        Requirements: 8.4, 8.8, 11.7
        """
        _assert_parity(
            [_standard_creative_with_spec(**{spec_key: ABSENT})],
            CreativeType.STANDARD.value,
        )

    @pytest.mark.parametrize('link_data_key', STANDARD_LINK_DATA_KEYS)
    def test_standard_parity_holds_with_each_link_data_leaf_absent(
            self, link_data_key):
        """Removing any leaf key of ``object_story_spec.link_data`` keeps the
        parity, including the three texts that feed ``titles``, ``bodies`` and
        ``descriptions`` and the ``image_url`` that feeds ``images``.

        Requirements: 8.4, 8.8, 11.7
        """
        _assert_parity(
            [_standard_creative_with_link_data(**{link_data_key: ABSENT})],
            CreativeType.STANDARD.value,
        )

    @pytest.mark.parametrize('degradation', [
        {'ad_creative': ABSENT},
        {'ad_creative': None},
        {'object_story_spec': ABSENT},
        {'object_story_spec': None},
        {'link_data': ABSENT},
        {'link_data': None},
        {'call_to_action': ABSENT},
        {'call_to_action': None},
        {'proposal_locations': ABSENT},
    ], ids=['ad-creative-absent', 'ad-creative-none', 'spec-absent',
            'spec-none', 'link-data-absent', 'link-data-none',
            'call-to-action-absent', 'call-to-action-none',
            'proposal-locations-absent'])
    def test_standard_parity_holds_with_the_four_levels_degraded(
            self, degradation):
        """The ``STANDARD`` branch of the launch use case already normalizes its
        four levels with ``or {}``, so the parity is observable on the whole
        degradation matrix of ``adCreative``, ``object_story_spec``,
        ``link_data`` and ``call_to_action``, absent and ``None`` alike.

        Requirements: 8.4, 8.8, 11.7
        """
        _assert_parity(
            [make_standard_creative(**degradation)],
            CreativeType.STANDARD.value,
        )

    # -- The same parity through ``execute()`` (Requirement 11.7) ----------

    @pytest.mark.parametrize('mode', [
        CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
    ])
    def test_parity_holds_for_the_creatives_returned_by_execute(self, mode):
        """The ``creatives`` list of the Resultado_de_Consulta of a full
        ``execute()`` is equal, by exact dict comparison, to the one the launch
        use case composes from the very same stored ``channel_creative`` dicts,
        in the same order and with the same indices.

        Requirements: 8.3, 8.4, 11.7
        """
        response = _main_flow_response(mode=mode)
        channel_creatives = _fixture_channel_creatives(response)
        expected = _launch_entries(channel_creatives, mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 4
        for idx, (entry, launch_entry) in enumerate(
                zip(result['creatives'], expected)):
            assert entry == launch_entry
            assert entry['idx'] == idx
        assert result['creatives'] == expected

# ---------------------------------------------------------------------------
# The ``campaign`` block and ``meta_url`` of the whole ``execute()`` result
# (Requirements 4.5, 7.3, 7.6, 7.7, 11.8, 11.9)
#
# The two classes below mirror the assertions ``TestResultComposition`` makes
# on ``_build_result`` by direct invocation, but now **end to end**: the values
# reach the envelope after travelling the four stages of the chain, so a
# regression that swapped two arguments, read the objective from the campaign
# instead of from the Campaign_Setup or interpolated a freshly built identifier
# would be caught here even while the projection stage stayed correct in
# isolation.
#
# The fixture is the canonical end to end one of ``main_flow_use_case``, so the
# expected values are the defaults of ``_expected_campaign_block`` and
# ``_expected_meta_url`` with a single figure stated per case.
# ---------------------------------------------------------------------------

#: The number of usable Published_Creatives the end to end fixture yields, and
#: therefore the ``creatives_no`` the ``campaign`` block must carry: two ad-sets
#: times two ads (Requirement 7.3).
MAIN_FLOW_CREATIVES_NO = sum(len(ads) for _, _, ads in MAIN_FLOW_AD_SETS)

#: The two identifiers the canonical ``make_campaign_setup()`` persists, which
#: are the two values ``meta_url`` must interpolate (Requirement 7.6).
MAIN_FLOW_META_ACCOUNT_ID = '1234567890'
MAIN_FLOW_META_CAMPAIGN_ID = '987654321'

#: The seven attribute names the whole chain reads from the Campaign_Setup:
#: ``meta_published`` for the publication state, ``meta_campaign_mode`` for the
#: dispatch and for the ``mode`` key, ``meta_conversion_event`` for the
#: ``conversion_event`` key, and the remaining four for the envelope.
#: ``meta_resources`` is deliberately **not** among them (Requirement 7.7).
SETUP_ATTRIBUTES_READ_END_TO_END = {
    'meta_published',
    'meta_campaign_mode',
    'meta_campaign_objective',
    'meta_optimization_goal',
    'meta_account_id',
    'meta_campaign_id',
    'meta_conversion_event',
}


class TestCampaignBlock:
    """The ``campaign`` block of the Resultado_de_Consulta returned by
    ``FacebookGetLaunchCampaignCreativesUseCase.execute``.

    Requirements: 4.5, 7.3, 11.8
    """

    # -- Exact equality of the seven keys (Requirements 7.3, 11.8) ---------

    def test_campaign_block_equals_the_seven_keys_derived_from_the_fixtures(self):
        """The ``campaign`` block of a full ``execute()`` is equal, by exact
        dict comparison, to the seven-key dict derived from the canonical end to
        end fixtures, and its keys come in the order of Requirement 7.3.

        Requirements: 7.3, 11.8
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign'] == _expected_campaign_block(
            creatives_no=MAIN_FLOW_CREATIVES_NO,
        )
        assert tuple(result['campaign'].keys()) == CAMPAIGN_BLOCK_KEYS
        assert len(result['campaign']) == 7

    @pytest.mark.parametrize('mode', [
        CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
    ])
    def test_the_block_is_the_same_in_both_modes_except_for_the_mode_key(
            self, mode):
        """The block keeps the same seven keys, in the same order, in both
        supported Modos_de_Campaña: only the ``mode`` value changes, because the
        rest of the block does not depend on the branch that composed the
        entries.

        Requirements: 7.3, 11.8
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign'] == _expected_campaign_block(
            creatives_no=MAIN_FLOW_CREATIVES_NO, mode=mode,
        )
        assert tuple(result['campaign'].keys()) == CAMPAIGN_BLOCK_KEYS

    def test_channel_name_is_the_literal_meta(self):
        """``channel_name`` is the literal string ``Meta``: it comes from the
        class constant and from no fixture value, so no ad-set, ad nor
        ad-channel of the fixture can influence it.

        Requirements: 7.3, 11.8
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign']['channel_name'] == 'Meta'

    def test_creatives_no_equals_the_length_of_the_creatives_list(self):
        """``creatives_no`` is equal to the number of elements of the
        ``creatives`` list actually returned, and hence to the number of
        selected Ad_Channels of the fixture.

        Requirements: 7.3, 11.8
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign']['creatives_no'] == len(result['creatives'])
        assert result['campaign']['creatives_no'] == MAIN_FLOW_CREATIVES_NO

    @pytest.mark.parametrize('ad_sets, expected_creatives_no', [
        (((120, 'Ad Set A', ((501, 9001),)),), 1),
        (((120, 'Ad Set A', ((501, 9001), (502, 9002))),), 2),
        (MAIN_FLOW_AD_SETS, 4),
    ], ids=['one-creative', 'two-creatives', 'four-creatives'])
    def test_creatives_no_follows_the_size_of_the_fixture(
            self, ad_sets, expected_creatives_no):
        """``creatives_no`` is recomputed from the composed list on every
        invocation: a fixture with one, two or four usable Published_Creatives
        is reported as such.

        Requirements: 7.3, 11.8
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(
                ad_set_id=ad_set_id,
                name=ad_set_name,
                ads_data=[
                    _main_flow_ad(ad_set_id, ad_set_name, ad_id, ad_channel_id)
                    for ad_id, ad_channel_id in ads
                ],
            )
            for ad_set_id, ad_set_name, ads in ad_sets
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == expected_creatives_no
        assert result['campaign']['creatives_no'] == expected_creatives_no
        assert result['campaign'] == _expected_campaign_block(
            creatives_no=expected_creatives_no,
        )

    # -- ``name`` comes from the Campaña_Objetivo (Requirements 4.5, 7.3) ---

    def test_name_is_the_name_attribute_of_the_resolved_campaign(self):
        """``name`` is ``attributes.name`` of the record the campaign query
        returned, whatever its value, and never the ``name`` of an ad-set of the
        ad-sets response.

        Requirements: 4.5, 7.3, 11.8
        """
        campaign = make_campaign(
            campaign_id=MAIN_FLOW_CAMPAIGN_ID, name='Campaña Verano',
        )

        with main_flow_use_case(campaign=campaign) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign']['name'] == 'Campaña Verano'
        assert result['campaign'] == _expected_campaign_block(
            name='Campaña Verano', creatives_no=MAIN_FLOW_CREATIVES_NO,
        )

    def test_only_the_name_is_read_from_the_resolved_campaign(self):
        """Of the Campaña_Objetivo the whole chain consults exactly one
        attribute, ``name``: the recording node registers that single lookup
        across the four stages of ``execute()``.

        Requirements: 4.5, 7.3
        """
        campaign, attributes = _campaign_with_recording_attributes(
            campaign_id=MAIN_FLOW_CAMPAIGN_ID,
        )

        with main_flow_use_case(campaign=campaign) as (use_case, _, _, _, _):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert attributes.consulted_keys == ['name']

    # -- The four keys of the Campaign_Setup (Requirements 7.3, 11.8) ------

    def test_the_four_remaining_keys_come_from_the_campaign_setup(self):
        """``objective``, ``optimization_goal``, ``mode`` and
        ``conversion_event`` are equal to ``meta_campaign_objective``,
        ``meta_optimization_goal``, ``meta_campaign_mode`` and
        ``meta_conversion_event`` of the Campaign_Setup of the fixture,
        whatever their values.

        Requirements: 7.3, 11.8
        """
        campaign_setup = make_campaign_setup(
            meta_campaign_objective='OUTCOME_SALES',
            meta_optimization_goal='OFFSITE_CONVERSIONS',
            meta_campaign_mode=CreativeType.STANDARD.value,
            meta_conversion_event='LEAD',
        )

        with main_flow_use_case(
            mode=CreativeType.STANDARD.value, campaign_setup=campaign_setup,
        ) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign'] == _expected_campaign_block(
            creatives_no=MAIN_FLOW_CREATIVES_NO,
            objective='OUTCOME_SALES',
            optimization_goal='OFFSITE_CONVERSIONS',
            mode=CreativeType.STANDARD.value,
            conversion_event='LEAD',
        )
        assert result['campaign']['conversion_event'] == 'LEAD'

    def test_mode_is_the_validated_campaign_mode_of_the_setup(self):
        """``mode`` is the very Modo_de_Campaña the validation accepted, so it
        agrees with the branch that composed the entries: the value of the
        Campaign_Setup and never a value inferred from the stored
        ``channel_creative``.

        Requirements: 7.3, 11.8
        """
        with main_flow_use_case(mode=CreativeType.STANDARD.value) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['campaign']['mode'] == CreativeType.STANDARD.value

    def test_absent_setup_attributes_would_not_reach_the_block(self):
        """A Campaign_Setup without the ``attributes`` node never reaches the
        composition: the publication validation rejects it first, so the block
        is not built with four ``None`` values end to end.

        Requirements: 7.3, 7.4
        """
        with main_flow_use_case(
            campaign_setup=make_campaign_setup(attributes=ABSENT),
        ) as (use_case, _, _, _, _):
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert_exception_type(exc_info, IncorrectValidationException)


class TestMetaUrl:
    """The ``meta_url`` key of the Resultado_de_Consulta returned by
    ``FacebookGetLaunchCampaignCreativesUseCase.execute``.

    Requirements: 7.6, 7.7, 11.9
    """

    # -- Exact string equality (Requirements 7.6, 11.9) --------------------

    def test_meta_url_equals_the_url_built_with_the_two_setup_identifiers(self):
        """``meta_url`` is equal, by exact string comparison, to the URL of
        Requirement 7.6 built with the ``meta_account_id`` and the
        ``meta_campaign_id`` of the fixture.

        Requirements: 7.6, 11.9
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['meta_url'] == _expected_meta_url(
            MAIN_FLOW_META_ACCOUNT_ID, MAIN_FLOW_META_CAMPAIGN_ID,
        )

    @pytest.mark.parametrize('mode', [
        CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
    ])
    def test_the_url_does_not_depend_on_the_campaign_mode(self, mode):
        """The URL is the same in both supported Modos_de_Campaña: it is built
        from the two persisted identifiers and from nothing the composition
        branch produces.

        Requirements: 7.6, 11.9
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['meta_url'] == _expected_meta_url(
            MAIN_FLOW_META_ACCOUNT_ID, MAIN_FLOW_META_CAMPAIGN_ID,
        )

    def test_meta_url_reflects_other_identifiers_of_the_persisted_record(self):
        """The two identifiers are read from the already persisted
        Campaign_Setup, whatever their values: no identifier is created during
        the query, which performs 0 requests to the Graph API.

        Requirements: 7.6, 11.9
        """
        campaign_setup = make_campaign_setup(
            meta_account_id='act_555', meta_campaign_id='camp_999',
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['meta_url'] == _expected_meta_url('act_555', 'camp_999')

    def test_absent_identifiers_keep_the_url_shape_without_raising(self):
        """With both identifiers absent from the Campaign_Setup the URL keeps its
        shape end to end, interpolating the two missing values instead of
        raising.

        Requirements: 7.6, 11.9
        """
        campaign_setup = make_campaign_setup(
            meta_account_id=ABSENT, meta_campaign_id=ABSENT,
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['meta_url'] == _expected_meta_url(None, None)

    # -- The ad-set edition URL stays out of scope (Requirement 7.7) -------

    def test_meta_url_carries_no_adsets_edit_url(self):
        """``meta_url`` does not contain the ``adsets/edit`` fragment: the
        per-ad-set web links of the launch flow are out of scope.

        Requirements: 7.7, 11.9
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert ADSETS_EDIT_FRAGMENT not in result['meta_url']

    @pytest.mark.parametrize('mode', [
        CreativeType.DYNAMIC.value, CreativeType.STANDARD.value,
    ])
    def test_no_string_of_the_whole_result_carries_an_adsets_edit_url(
            self, mode):
        """0 keys of the whole Resultado_de_Consulta —envelope, ``campaign``
        block and the 31 keys of each of the four entries alike— carry a URL of
        the form ``.../adsmanager/manager/adsets/edit?...``.

        Requirements: 7.7, 11.9
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert [
            string for string in _iter_strings(result)
            if ADSETS_EDIT_FRAGMENT in string
        ] == []

    def test_meta_resources_is_never_read_end_to_end(self):
        """``meta_resources`` is present in the fixture and is **not** consulted
        by any stage: the chain reads the seven attributes it needs from the
        Campaign_Setup and nothing else.

        Requirements: 7.6, 7.7, 11.9
        """
        campaign_setup, attributes = _campaign_setup_with_recording_attributes()
        assert 'meta_resources' in dict(attributes)

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert 'meta_resources' not in attributes.consulted_keys
        assert set(attributes.consulted_keys) == SETUP_ATTRIBUTES_READ_END_TO_END
        assert result['meta_url'] == _expected_meta_url(
            MAIN_FLOW_META_ACCOUNT_ID, MAIN_FLOW_META_CAMPAIGN_ID,
        )

# ---------------------------------------------------------------------------
# The Channel_ID and the ad-channel selection, end to end
# (Requirements 5.3, 5.4, 6.1, 6.2, 6.4, 6.5, 9.7, 11.10, 11.11, 11.12)
#
# The two classes below are the ``execute()`` counterparts of the unit level
# ``TestChannelIdResolutionUnit`` and ``TestAdChannelSelectionUnit``: the same
# two rules —"the Channel_ID is the one of the *first* selected ad-channel of
# the walk, with default 0" and "an ad contributes through its *selected*
# ad-channel or it does not contribute at all"— but now observed where they are
# actually consumed.
#
# That is what makes the end to end angle worth its own class: the Channel_ID is
# not exposed by the Resultado_de_Consulta, so the only way to observe it is the
# second argument the Campaign_Setup query receives (Requirement 11.10), and the
# selection is only observable through which Creative_Entries the ``creatives``
# list ends up holding (Requirements 11.11, 11.12). A regression that resolved
# the Channel_ID correctly but forwarded the wrong value, or that walked every
# ad-channel instead of the selected one, would keep the unit level classes
# green and would be caught here.
#
# Requirement 9.7 note: the new repository query filters *ad-sets* by
# ``filters[ads][ad_channels][selected][$eq]=true``, which keeps out of the
# response the ad-sets without any selected ad-channel — it does **not** prune
# the non-selected ad-channels of the ads of the ad-sets it does return. The
# per-ad selection therefore stays an in-memory responsibility of the use case,
# and that is precisely what ``TestAdChannelSelection`` pins.
# ---------------------------------------------------------------------------

#: The Channel_ID values used by the cases below, deliberately different from
#: ``MAIN_FLOW_CHANNEL_ID`` so that an assertion cannot pass by accident against
#: the canonical fixture value.
FIRST_CHANNEL_ID = 77
LATER_CHANNEL_ID = 88

#: Degradations of the ``attributes.channel_ref.data.id`` path of an ad-channel,
#: one per level and per kind of degradation (key omitted, ``None`` and an
#: unexpected type), all of which must resolve the Channel_ID as ``0``
#: (Requirement 6.2) without preventing the Campaign_Setup query
#: (Requirement 7.1).
DEGRADED_CHANNEL_REF = (
    ('channel_ref-absent', {'channel_ref': ABSENT}),
    ('channel_ref-none', {'channel_ref': None}),
    ('channel_ref-str', {'channel_ref': 'oops'}),
    ('data-absent', {'channel_ref_data': ABSENT}),
    ('data-none', {'channel_ref_data': None}),
    ('data-list', {'channel_ref_data': []}),
    ('id-absent', {'channel_ref_id': ABSENT}),
)

#: The falsy values of ``selected`` that must not select an ad-channel
#: (Requirement 5.3), including the omission of the key.
NOT_SELECTED_VALUES = (False, None, 0, '', ABSENT)
NOT_SELECTED_IDS = ('false', 'none', 'zero', 'empty-str', 'absent')

#: The two ad-channel identifiers of the selection fixture. Both the record
#: ``id`` and the ``ad_channel_id`` of the stored specification carry the same
#: value per ad-channel, so the ``adchannel_id`` of the resulting entry names
#: without ambiguity the ad-channel that produced it.
SELECTED_AD_CHANNEL_ID = 9101
UNSELECTED_AD_CHANNEL_ID = 9102


def _ad_channel_response(declarations, ad_set_id=120):
    """Build a fresh ad-sets response with a single ad-set holding one ad per
    element of ``declarations``, each element being the ``make_ad_channel``
    keyword arguments of the single ad-channel of its ad.

    Every ad gets a distinct ``ad_id`` and a distinct ``ad_channel_id``, and its
    ad-channel carries a usable ``DYNAMIC`` Published_Creative, so the order of
    the walk and the number of resulting entries stay observable while only the
    ``channel_ref`` path varies.

    Requirements: 6.1, 6.2, 6.4, 6.5, 11.4
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(ad_set_id=ad_set_id, ads_data=[
            _ad_with_channel(
                ad_id=501 + position,
                ad_channel_id=9001 + position,
                **kwargs
            )
            for position, kwargs in enumerate(declarations)
        ]),
    ])


def _ad_with_selected_and_unselected(ad_id=501, selected_first=True,
                                     selected_value=False):
    """Build a fresh element of ``ads.data`` holding **two** ad-channels: one
    with ``selected`` truthy and one with ``selected`` equal to
    ``selected_value`` (falsy by default).

    Both carry a usable ``DYNAMIC`` Published_Creative whose
    ``asset_feed_spec.ad_channel_id`` equals the ``id`` of its own ad-channel,
    so the ``adchannel_id`` of the produced Creative_Entry tells which of the two
    was used. ``selected_first`` flips the order of the two elements inside
    ``ad_channels.data``, so the assertion cannot pass merely because the
    selected one happened to come first.

    Requirements: 5.3, 8.6, 11.4, 11.11
    """
    selected = make_ad_channel(
        ad_channel_id=SELECTED_AD_CHANNEL_ID,
        selected=True,
        channel_ref_id=MAIN_FLOW_CHANNEL_ID,
        channel_creative=make_dynamic_creative(
            creative_id=120,
            name='Ad Set A',
            ad_id=ad_id,
            ad_channel_id=SELECTED_AD_CHANNEL_ID,
        ),
    )
    unselected = make_ad_channel(
        ad_channel_id=UNSELECTED_AD_CHANNEL_ID,
        selected=selected_value,
        channel_ref_id=MAIN_FLOW_CHANNEL_ID,
        channel_creative=make_dynamic_creative(
            creative_id=120,
            name='Ad Set A',
            ad_id=ad_id,
            ad_channel_id=UNSELECTED_AD_CHANNEL_ID,
        ),
    )
    return make_ad(
        ad_id=ad_id,
        ad_channels_data=(
            [selected, unselected] if selected_first else [unselected, selected]
        ),
    )


def _ad_without_any_selected_ad_channel(ad_id=501):
    """Build a fresh element of ``ads.data`` whose two ad-channels are both
    unselected, each one still carrying a perfectly usable Published_Creative.

    The creatives are usable on purpose: what must keep the ad out of the result
    is the absence of a selected ad-channel (Requirement 5.4) and nothing else.

    Requirements: 5.4, 11.4, 11.12
    """
    return make_ad(
        ad_id=ad_id,
        ad_channels_data=[
            make_ad_channel(
                ad_channel_id=UNSELECTED_AD_CHANNEL_ID + position,
                selected=selected_value,
                channel_ref_id=MAIN_FLOW_CHANNEL_ID,
                channel_creative=make_dynamic_creative(
                    creative_id=120,
                    name='Ad Set A',
                    ad_id=ad_id,
                    ad_channel_id=UNSELECTED_AD_CHANNEL_ID + position,
                ),
            )
            for position, selected_value in enumerate((False, None))
        ],
    )


def _channel_id_argument(publish_repository):
    """Return the second positional argument the Campaign_Setup query received,
    which is the only place where the resolved Channel_ID becomes observable
    from outside the use case (Requirement 11.10).

    Requirements: 7.1, 11.4, 11.10
    """
    double = _setup_double(publish_repository)
    assert double.call_count == 1, (
        f"expected exactly one Campaign_Setup query, got {double.call_count}"
    )
    args, kwargs = double.call_args
    assert kwargs == {}, f"expected positional arguments only, got {kwargs!r}"
    assert len(args) == 2, f"expected two positional arguments, got {args!r}"
    return args[1]


class TestChannelIdResolution:
    """The Channel_ID the whole chain forwards to the Campaign_Setup query.

    The Channel_ID never appears in the Resultado_de_Consulta: it is consumed as
    the second argument of
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``, and
    that argument is what every case below reads.

    Requirements: 6.1, 6.2, 6.4, 6.5, 11.10
    """

    # -- The value of the first selected ad-channel (Requirements 6.1, 6.4) --

    def test_the_query_receives_the_channel_id_declared_by_the_fixture(self):
        """The second argument of the Campaign_Setup query is the
        ``channel_ref.data.id`` the selected ad-channels of the canonical end to
        end fixture declare.

        Requirements: 6.1, 7.1, 11.10
        """
        with main_flow_use_case() as (use_case, _, _, _, publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        _setup_double(publish_repository).assert_called_once_with(
            MAIN_FLOW_CAMPAIGN_ID, MAIN_FLOW_CHANNEL_ID,
        )

    def test_the_query_receives_the_value_of_the_first_selected_ad_channel(self):
        """With every selected ad-channel declaring ``FIRST_CHANNEL_ID``, that
        is the value the query receives: the argument follows the fixture and is
        not a constant.

        Requirements: 6.1, 6.4, 11.10
        """
        response = _ad_channel_response([
            {'channel_ref_id': FIRST_CHANNEL_ID},
            {'channel_ref_id': FIRST_CHANNEL_ID},
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert _channel_id_argument(publish_repository) == FIRST_CHANNEL_ID
        assert len(result['creatives']) == 2

    def test_the_value_of_the_first_one_wins_over_the_later_ones(self):
        """Several selected ad-channels declaring different values: the argument
        is the one of the **first** of the walk, not the last one nor the most
        frequent one.

        Requirements: 6.4, 6.5, 11.10
        """
        response = _ad_channel_response([
            {'channel_ref_id': FIRST_CHANNEL_ID},
            {'channel_ref_id': LATER_CHANNEL_ID},
            {'channel_ref_id': LATER_CHANNEL_ID},
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert _channel_id_argument(publish_repository) == FIRST_CHANNEL_ID

    # -- The degraded node resolves 0 and the query is still emitted
    #    (Requirements 6.2, 7.1) ---------------------------------------------

    @pytest.mark.parametrize(
        'kwargs', [kwargs for _, kwargs in DEGRADED_CHANNEL_REF],
        ids=_ids(DEGRADED_CHANNEL_REF),
    )
    def test_degraded_channel_ref_forwards_zero_without_raising(self, kwargs):
        """With the ``channel_ref`` path of the only selected ad-channel
        degraded, the argument is ``0``, the query is emitted all the same and
        ``execute()`` completes and returns its entry.

        Requirements: 6.2, 7.1, 11.10
        """
        response = _ad_channel_response([kwargs])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        _setup_double(publish_repository).assert_called_once_with(
            MAIN_FLOW_CAMPAIGN_ID, 0,
        )
        assert len(result['creatives']) == 1

    def test_a_degraded_first_one_keeps_zero_even_with_a_valid_later_one(self):
        """The first selected ad-channel degraded and a later one declaring a
        valid value: the argument stays ``0``, because the Channel_ID is fixed
        with the first selected ad-channel and a legitimately resolved ``0`` is
        a value, not a "not yet resolved" marker (decision D-3).

        Requirements: 6.2, 6.4, 11.10
        """
        response = _ad_channel_response([
            {'channel_ref_data': None},
            {'channel_ref_id': LATER_CHANNEL_ID},
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert _channel_id_argument(publish_repository) == 0
        assert len(result['creatives']) == 2

    def test_a_declared_zero_is_forwarded_as_the_legitimate_value(self):
        """A first selected ad-channel declaring ``0`` explicitly is
        indistinguishable from the default: the argument is ``0`` and a later
        value does not replace it.

        Requirements: 6.2, 6.4, 11.10
        """
        response = _ad_channel_response([
            {'channel_ref_id': 0},
            {'channel_ref_id': LATER_CHANNEL_ID},
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert _channel_id_argument(publish_repository) == 0

    # -- The discrepancy is warned, never acted upon (Requirement 6.5) ------

    def test_a_mismatching_later_ad_channel_is_warned_with_both_values(self):
        """A later selected ad-channel declaring a different value produces a
        single ``logger.warning`` carrying **both** values, and the argument
        stays the one of the first ad-channel.

        Requirements: 6.5, 11.10
        """
        response = _ad_channel_response([
            {'channel_ref_id': FIRST_CHANNEL_ID},
            {'channel_ref_id': LATER_CHANNEL_ID},
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                result = use_case.execute(
                    MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
                )

        assert _channel_id_argument(publish_repository) == FIRST_CHANNEL_ID
        assert len(result['creatives']) == 2

        assert mock_logger.warning.call_count == 1
        message = str(mock_logger.warning.call_args[0][0])
        assert str(FIRST_CHANNEL_ID) in message
        assert str(LATER_CHANNEL_ID) in message

    def test_matching_later_ad_channels_are_not_a_discrepancy(self):
        """The canonical fixture —four selected ad-channels declaring the same
        value— emits 0 warnings: agreement is the normal case, not a
        discrepancy.

        Requirements: 6.4, 6.5, 11.10
        """
        with main_flow_use_case() as (use_case, _, _, _, publish_repository):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert _channel_id_argument(publish_repository) == MAIN_FLOW_CHANNEL_ID
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0


class TestAdChannelSelection:
    """Which ad-channel of an ad reaches the ``creatives`` list of the
    Resultado_de_Consulta returned by ``execute()``.

    The repository query filters the *ad-sets* by the ``selected`` flag of their
    ad-channels (Requirement 9.7); it does not prune the unselected ad-channels
    of the ads it returns, so the per-ad selection of Requirements 5.3 and 5.4
    is an in-memory responsibility that only the entries of the result can
    accredit.

    Requirements: 5.3, 5.4, 9.7, 11.11, 11.12
    """

    # -- One selected and one unselected ad-channel (Requirements 5.3, 9.7) --

    @pytest.mark.parametrize('selected_first', [True, False])
    def test_an_ad_with_two_ad_channels_yields_the_selected_one_only(
            self, selected_first):
        """An ad with two ad-channels, one with ``selected`` true and one with
        ``selected`` false, produces exactly **one** Creative_Entry, whose
        ``adchannel_id`` is the one of the selected ad-channel, whatever the
        order of the two inside ``ad_channels.data``.

        Requirements: 5.3, 9.7, 11.11
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_selected_and_unselected(
                    ad_id=501, selected_first=selected_first,
                ),
            ]),
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 1
        entry = result['creatives'][0]
        assert entry['adchannel_id'] == SELECTED_AD_CHANNEL_ID
        assert entry['adchannel_id'] != UNSELECTED_AD_CHANNEL_ID
        assert entry['ad_id'] == 501
        assert entry['idx'] == 0

    @pytest.mark.parametrize(
        'selected_value', NOT_SELECTED_VALUES, ids=NOT_SELECTED_IDS,
    )
    def test_no_falsy_selected_value_brings_its_ad_channel_into_the_result(
            self, selected_value):
        """Whichever falsy value —or the omission of the key— the second
        ad-channel carries in ``selected``, the result keeps holding the single
        entry of the selected one.

        Requirements: 5.3, 11.11
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_with_selected_and_unselected(
                    ad_id=501, selected_first=False,
                    selected_value=selected_value,
                ),
            ]),
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 1
        assert result['creatives'][0]['adchannel_id'] == SELECTED_AD_CHANNEL_ID

    # -- An ad without any selected ad-channel (Requirement 5.4) -----------

    def test_an_ad_without_selection_is_skipped_and_the_other_one_is_kept(self):
        """An ad without any selected ad-channel next to an ad with one produces
        **one** entry —the one of the second ad— and ``execute()`` raises no
        exception: the unselected ad is skipped, not a failure.

        Requirements: 5.4, 11.12
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_without_any_selected_ad_channel(ad_id=501),
                _ad_with_selected_and_unselected(ad_id=502),
            ]),
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, publish_repository):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 1
        entry = result['creatives'][0]
        assert entry['ad_id'] == 502
        assert entry['adchannel_id'] == SELECTED_AD_CHANNEL_ID
        assert entry['idx'] == 0
        assert result['campaign']['creatives_no'] == 1
        assert _channel_id_argument(publish_repository) == MAIN_FLOW_CHANNEL_ID

    def test_the_skipped_ad_is_neither_logged_nor_fails_the_chain(self):
        """The ad without selection is skipped **without log**: it is an
        expected shape of the data, so no warning and no error is emitted while
        the other ad travels the whole chain.

        Requirements: 5.4, 11.12
        """
        response = make_ad_sets_response(ad_sets=[
            make_ad_set(ad_set_id=120, ads_data=[
                _ad_without_any_selected_ad_channel(ad_id=501),
                _ad_with_selected_and_unselected(ad_id=502),
            ]),
        ])

        with main_flow_use_case(ad_sets_response=response) as (
                use_case, _, _, _, _):
            with patch('app.v2.use_cases.meta_ads.logger') as mock_logger:
                result = use_case.execute(
                    MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
                )

        assert len(result['creatives']) == 1
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

# ---------------------------------------------------------------------------
# The Strapi identifiers of the Entrada_de_Creativo
# (Requirements 8.6, 8.7, 11.13)
#
# The three identifier keys of the entry —``adset_id``, ``ad_id`` and
# ``adchannel_id``— are what makes the Resultado_de_Consulta actionable: the
# client reuses them as arguments of the pre-check and asset export endpoints.
# Requirement 8.6 fixes where each one comes from: ``creativo.id``,
# ``creativo.ads[0].id`` and the ``ad_channel_id`` of the stored specification
# of the Modo_de_Campaña —``asset_feed_spec`` in ``DYNAMIC``,
# ``object_story_spec`` in ``STANDARD``— with default ``0``.
#
# OQ-2 is the subtle part, and the reason this class exists on top of the key
# level assertions of ``TestDynamicCreativeEntry`` and
# ``TestStandardCreativeEntry``: the internal descriptor also carries an
# ``adchannel_id``, the ``id`` of the ``ad-channels`` record, and that one
# exists **only** for the log messages of the walk. The canonical end to end
# fixture ties both values together —``_main_flow_ad`` gives the record and the
# specification the same identifier— so the two fixtures below deliberately
# decouple them: an absent specification value must come out as ``0`` and a
# specification value different from the record ``id`` must come out as the
# specification one, in both cases proving that the descriptor value is not the
# source.
#
# Requirement 8.7 is the complement: the entry exposes Strapi identifiers and
# 0 keys for Meta identifiers, even though the chain does read
# ``meta_account_id`` and ``meta_campaign_id`` from the Campaign_Setup to build
# ``meta_url``.
# ---------------------------------------------------------------------------

#: The stored specification key of each supported Modo_de_Campaña, which is the
#: node ``adchannel_id`` is read from (Requirement 8.6).
SPEC_KEY_BY_MODE = {
    CreativeType.DYNAMIC.value: 'asset_feed_spec',
    CreativeType.STANDARD.value: 'object_story_spec',
}

#: The two supported modes, as the parametrization of every case below: the
#: rule of Requirement 8.6 is the same in both branches and only the
#: specification it reads from changes.
BOTH_MODES = (CreativeType.DYNAMIC.value, CreativeType.STANDARD.value)

#: The identifiers of the decoupling fixture. The ``id`` of the
#: ``ad-channels`` record —the value the internal descriptor carries— and the
#: ``ad_channel_id`` of the stored specification are deliberately **different**,
#: which is what makes OQ-2 observable: only one of the two may reach the entry.
RECORD_AD_CHANNEL_ID = 6001
SPEC_AD_CHANNEL_ID = 9501

#: The ad-set and ad identifiers of that same fixture.
DECOUPLED_AD_SET_ID = 131
DECOUPLED_AD_SET_NAME = 'Ad Set Desacoplado'
DECOUPLED_AD_ID = 601

#: The three identifier keys of Requirement 8.6, in the order of Requirement
#: 8.1, used by the assertions that compare them as a single tuple per entry.
IDENTIFIER_KEYS = ('adset_id', 'ad_id', 'adchannel_id')


def _stored_specification(creative, mode):
    """Return the stored specification of the given Modo_de_Campaña of a
    Published_Creative: its ``asset_feed_spec`` or its ``object_story_spec``.

    Requirements: 8.6, 11.4
    """
    return creative['ads'][0]['adCreative'][SPEC_KEY_BY_MODE[mode]]


def _fixture_identifiers(response, mode):
    """Return the ``(adset_id, ad_id, adchannel_id)`` triple **declared by the
    fixture** for each of its Published_Creatives, in walk order.

    Read from the three places Requirement 8.6 names —``creativo.id``,
    ``creativo.ads[0].id`` and the ``ad_channel_id`` of the specification of the
    mode, with default ``0``— so the expectation is derived from the fixture and
    not restated as a literal.

    Requirements: 8.6, 11.4, 11.13
    """
    return [
        (
            creative['id'],
            creative['ads'][0]['id'],
            _stored_specification(creative, mode).get('ad_channel_id', 0),
        )
        for creative in _fixture_channel_creatives(response)
    ]


def _entry_identifiers(creatives):
    """Return the ``(adset_id, ad_id, adchannel_id)`` triple **exposed by each
    Creative_Entry**, in order.

    Requirements: 8.6, 11.4, 11.13
    """
    return [
        tuple(entry[key] for key in IDENTIFIER_KEYS) for entry in creatives
    ]


def _main_flow_response_without_spec_ad_channel_id(mode):
    """Build a fresh end to end response whose four Published_Creatives have
    the ``ad_channel_id`` key **removed** from their stored specification.

    The ad-channel records keep their own ``id``, so the descriptors of the walk
    still carry one: the default of Requirement 8.6 is only reachable if the
    entry does not read it from there.

    Requirements: 8.6, 11.4, 11.13
    """
    response = _main_flow_response(mode=mode)
    for creative in _fixture_channel_creatives(response):
        del _stored_specification(creative, mode)['ad_channel_id']
    return response


def _decoupled_identifiers_response(mode, spec_ad_channel_id=SPEC_AD_CHANNEL_ID):
    """Build a fresh ad-sets response with a single ad-set, a single ad and a
    single selected ad-channel whose record ``id`` is ``RECORD_AD_CHANNEL_ID``
    while the ``ad_channel_id`` of its stored specification is
    ``spec_ad_channel_id``.

    The two values are distinct by construction, so the ``adchannel_id`` of the
    resulting entry names without ambiguity which of the two sources was read
    (OQ-2). Pass ``ABSENT`` to remove the specification value and observe the
    default of Requirement 8.6 while the descriptor still carries the record
    ``id``.

    Requirements: 8.6, 11.4, 11.13
    """
    creative = MAIN_FLOW_CREATIVE_BUILDERS[mode](
        creative_id=DECOUPLED_AD_SET_ID,
        name=DECOUPLED_AD_SET_NAME,
        ad_id=DECOUPLED_AD_ID,
        ad_channel_id=(
            0 if spec_ad_channel_id is ABSENT else spec_ad_channel_id
        ),
    )
    if spec_ad_channel_id is ABSENT:
        del _stored_specification(creative, mode)['ad_channel_id']

    return make_ad_sets_response(ad_sets=[
        make_ad_set(
            ad_set_id=DECOUPLED_AD_SET_ID,
            name=DECOUPLED_AD_SET_NAME,
            ads_data=[
                _ad_with_channel(
                    ad_id=DECOUPLED_AD_ID,
                    ad_channel_id=RECORD_AD_CHANNEL_ID,
                    channel_ref_id=MAIN_FLOW_CHANNEL_ID,
                    channel_creative=creative,
                ),
            ],
        ),
    ])


class TestStrapiIdentifiers:
    """The Strapi identifiers every Creative_Entry of ``execute()`` exposes.

    ``adset_id``, ``ad_id`` and ``adchannel_id`` are equal to the identifiers
    the fixture declares —``creativo.id``, ``creativo.ads[0].id`` and the
    ``ad_channel_id`` of the specification of the Modo_de_Campaña— and no entry
    carries a key whose name includes the substring ``meta_``.

    Requirements: 8.6, 8.7, 11.13
    """

    # -- The three identifiers come from the fixture (Requirement 8.6) -------

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_three_identifiers_equal_the_ones_declared_by_the_fixture(
            self, mode):
        """The ``(adset_id, ad_id, adchannel_id)`` triple of each entry is equal,
        in order, to the triple read from the three places Requirement 8.6 names
        in the corresponding Published_Creative of the fixture.

        Requirements: 8.6, 11.13
        """
        response = _main_flow_response(mode=mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 4
        assert _entry_identifiers(result['creatives']) \
            == _fixture_identifiers(response, mode)

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_adset_id_is_the_id_of_the_stored_published_creative(self, mode):
        """``adset_id`` is ``creativo.id``, the ``id`` of the stored ad-set
        snapshot: the two ad-sets of the fixture contribute two entries each,
        both carrying their own identifier.

        Requirements: 8.6, 11.13
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert [entry['adset_id'] for entry in result['creatives']] \
            == [120, 120, 121, 121]

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_ad_id_is_the_id_of_the_first_ad_of_the_published_creative(
            self, mode):
        """``ad_id`` is ``creativo.ads[0].id``: the four ads of the fixture carry
        four distinct identifiers and each entry exposes its own.

        Requirements: 8.6, 11.13
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert [entry['ad_id'] for entry in result['creatives']] \
            == [501, 502, 503, 504]

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_adchannel_id_is_the_one_of_the_specification_of_the_mode(
            self, mode):
        """``adchannel_id`` is the ``ad_channel_id`` of the stored specification
        of the Modo_de_Campaña, read from ``asset_feed_spec`` in ``DYNAMIC`` and
        from ``object_story_spec`` in ``STANDARD``.

        Requirements: 8.6, 11.13
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert [entry['adchannel_id'] for entry in result['creatives']] \
            == [9001, 9002, 9003, 9004]

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_three_identifiers_are_the_stored_values_unchanged(self, mode):
        """The identifiers travel the chain untransformed: each entry exposes the
        very objects of the fixture, by identity of value and of type, so the
        client can reuse them as arguments of the pre-check and export
        endpoints.

        Requirements: 8.6, 11.13
        """
        response = _main_flow_response(mode=mode)
        expected = _fixture_identifiers(response, mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry, identifiers in zip(result['creatives'], expected):
            for key, value in zip(IDENTIFIER_KEYS, identifiers):
                assert entry[key] == value
                assert type(entry[key]) is type(value)

    # -- The default 0 of an absent specification value (Requirement 8.6) ----

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_absent_spec_ad_channel_id_yields_the_default_zero(self, mode):
        """With the ``ad_channel_id`` removed from the stored specification, the
        ``adchannel_id`` of every entry is the default ``0`` —and never the
        ``id`` of the ``ad-channels`` record, which the fixture still declares—
        while the other two identifiers and the 31 keys stay intact.

        Requirements: 8.6, 11.13
        """
        response = _main_flow_response_without_spec_ad_channel_id(mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 4
        assert [entry['adchannel_id'] for entry in result['creatives']] \
            == [0, 0, 0, 0]
        assert [entry['ad_id'] for entry in result['creatives']] \
            == [501, 502, 503, 504]
        for entry in result['creatives']:
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

    # -- The specification wins over the descriptor (Requirement 8.6, OQ-2) --

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_specification_value_wins_over_the_ad_channel_record_id(
            self, mode):
        """With the ``ad_channel_id`` of the specification **different** from the
        ``id`` of the ``ad-channels`` record, the exposed ``adchannel_id`` is the
        one of the specification: the ``adchannel_id`` of the internal descriptor
        exists only for the log messages of the walk (OQ-2).

        Requirements: 8.6, 11.13
        """
        response = _decoupled_identifiers_response(mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert SPEC_AD_CHANNEL_ID != RECORD_AD_CHANNEL_ID
        assert len(result['creatives']) == 1
        entry = result['creatives'][0]
        assert entry['adchannel_id'] == SPEC_AD_CHANNEL_ID
        assert entry['adchannel_id'] != RECORD_AD_CHANNEL_ID
        assert (entry['adset_id'], entry['ad_id']) \
            == (DECOUPLED_AD_SET_ID, DECOUPLED_AD_ID)

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_descriptor_value_is_not_used_as_a_fallback_either(self, mode):
        """The strongest form of OQ-2: with the specification value **absent**
        and the ``ad-channels`` record declaring one, the entry exposes the
        default ``0`` and not the record ``id``, so the descriptor value is not
        read even as a fallback.

        Requirements: 8.6, 11.13
        """
        response = _decoupled_identifiers_response(
            mode, spec_ad_channel_id=ABSENT,
        )

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 1
        entry = result['creatives'][0]
        assert entry['adchannel_id'] == 0
        assert entry['adchannel_id'] != RECORD_AD_CHANNEL_ID

    # -- 0 keys for Meta identifiers (Requirement 8.7) ----------------------

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_no_entry_carries_a_key_including_the_meta_substring(self, mode):
        """No Creative_Entry has a key whose name includes the substring
        ``meta_``: the entry exposes the Strapi identifiers and 0 keys for Meta
        identifiers.

        Requirements: 8.7, 11.13
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert len(result['creatives']) == 4
        for entry in result['creatives']:
            assert _meta_prefixed_keys(entry) == []
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_meta_identifiers_of_the_setup_reach_no_entry(self, mode):
        """The chain does read ``meta_account_id`` and ``meta_campaign_id`` from
        the Campaign_Setup —they build ``meta_url``— and neither of them, nor any
        ``meta_``-named key of the record, leaks into a Creative_Entry.

        Requirements: 8.7, 11.13
        """
        campaign_setup = make_campaign_setup(
            meta_campaign_mode=mode,
            meta_account_id='act_555',
            meta_campaign_id='camp_999',
        )
        setup_meta_keys = [
            key for key in campaign_setup['attributes'] if 'meta_' in key
        ]
        assert len(setup_meta_keys) == 7

        with main_flow_use_case(mode=mode, campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert result['meta_url'] == _expected_meta_url('act_555', 'camp_999')
        for entry in result['creatives']:
            assert _meta_prefixed_keys(entry) == []
            assert set(entry) & set(setup_meta_keys) == set()
            assert 'act_555' not in _iter_strings(entry)
            assert 'camp_999' not in _iter_strings(entry)

    @pytest.mark.parametrize('mode', BOTH_MODES)
    def test_the_degraded_fixtures_keep_the_meta_free_key_contract(self, mode):
        """The absence of the specification value does not add nor rename a
        single key: the ``meta_``-free contract of Requirement 8.7 holds on the
        degraded fixture too.

        Requirements: 8.6, 8.7, 11.13
        """
        response = _main_flow_response_without_spec_ad_channel_id(mode)

        with main_flow_use_case(mode=mode, ad_sets_response=response) as (
                use_case, _, _, _, _):
            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        for entry in result['creatives']:
            assert _meta_prefixed_keys(entry) == []
            assert entry_keys_in_order(entry) == CREATIVE_ENTRY_KEYS

# ---------------------------------------------------------------------------
# Task 12.8 — the six failure scenarios of ``execute()`` (Requirements 11.14,
# 11.15)
#
# One case per failure scenario of the normative chain, all of them going
# through ``execute()`` and all of them asserting **only the type** of the
# raised exception through ``assert_exception_type``, never the text of its
# message (Requirement 11.14):
#
#   stage 1  account not found ................... ``DataNotFoundException``
#   stage 2  campaign not found .................. ``DataNotFoundException``
#   stage 3  ad-sets query without results ....... ``DataNotFoundException``
#   stage 4  Campaign_Setup not found ............ ``DataNotFoundException``
#   stage 5  ``meta_published`` other than ``True``
#            ............................. ``IncorrectValidationException``
#   stage 6  Modo_de_Campaña not recognised
#            ............................. ``IncorrectValidationException``
#
# Requirement 11.15 adds the parametrized form of stage 5: the five rejected
# values ``False``, ``None``, ``1``, ``'True'``, ``'true'`` and the absence of
# the attribute, all of them rejected by the identity comparison against
# ``True`` of Requirement 7.4.
#
# Stages 5 and 6 carry one extra obligation (Requirements 10.4, 10.5): they are
# evaluated **before** any Creative_Entry is composed, so besides the exception
# type each of those cases asserts that 0 entries were composed and that
# ``execute()`` returned no value at all.
# ---------------------------------------------------------------------------

#: Marker of "``execute()`` did not return": the local the failing invocation
#: would have bound is pre-set to this object, so an assertion can tell "no
#: value was returned" from "``None`` was returned" (Requirements 10.4, 10.5).
NOT_RETURNED = object()

#: The three composition methods of the use case. Requirements 10.4 and 10.5
#: fix at 0 the number of Creative_Entries composed when the publication state
#: or the Modo_de_Campaña is rejected, and these are the only three places
#: where an entry can come into existence.
COMPOSITION_METHOD_NAMES = (
    '_build_creatives',
    '_build_dynamic_creative_published',
    '_build_standard_creative_published',
)

#: Falsy values ``AccountRepository.get_by_email`` may return, each one making
#: the ``if not account`` guard of the already existing ``_get_account()`` fail
#: (Requirement 3.3).
MISSING_ACCOUNT_MATRIX = (
    ('none', None),
    ('empty-dict', {}),
    ('empty-str', ''),
    ('zero', 0),
    ('empty-list', []),
)

#: Values of ``CampaignRepository.get_by_id_brand_and_account`` that leave the
#: Campaña_Objetivo unresolved: ``None``, a non-dict and a dict without keys
#: (Requirement 4.2).
MISSING_CAMPAIGN_MATRIX = (
    ('none', None),
    ('empty-dict', {}),
    ('non-dict-str', 'nope'),
    ('non-dict-list', [{'id': 41}]),
)

#: Values of the new ``AdSetRepository`` query that carry no ad-set at all
#: (Requirement 5.2).
EMPTY_AD_SETS_MATRIX = (
    ('none', None),
    ('non-dict', 'nope'),
    ('no-data-key', {}),
    ('data-none', {'data': None}),
    ('data-empty-list', {'data': []}),
    ('data-non-list', {'data': {'id': 120}}),
)

#: Values of ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``
#: that leave the Campaign_Setup unresolved: falsy or non-dict (Requirement
#: 7.2).
MISSING_CAMPAIGN_SETUP_MATRIX = (
    ('none', None),
    ('empty-dict', {}),
    ('zero', 0),
    ('false', False),
    ('non-dict-str', 'nope'),
    ('non-dict-list', [{'id': 55}]),
)

#: The five rejected values of ``meta_published`` plus the absence of the
#: attribute, which ``ABSENT`` expresses (Requirements 7.4, 11.15). ``1`` and
#: ``'True'``/``'true'`` are the interesting ones: they are truthy, and only an
#: identity comparison against ``True`` rejects them.
REJECTED_META_PUBLISHED_MATRIX = (
    ('false', False),
    ('none', None),
    ('int-one', 1),
    ('str-True', 'True'),
    ('str-true', 'true'),
    ('absent', ABSENT),
)

#: Values of ``meta_campaign_mode`` outside ``_SUPPORTED_CAMPAIGN_MODES``
#: (Requirement 8.5). The lowercase and padded spellings of a supported mode
#: are included on purpose: the membership test is exact, with no normalisation.
UNSUPPORTED_CAMPAIGN_MODE_MATRIX = (
    ('absent', ABSENT),
    ('none', None),
    ('empty-str', ''),
    ('lowercase', 'standard'),
    ('padded', ' STANDARD '),
    ('unknown', 'OTRO'),
)


def _execute_expecting(use_case, expected_type):
    """Invoke ``execute()`` with the end to end arguments expecting it to fail,
    assert **only** that the raised exception is exactly ``expected_type`` and
    that no value was returned, and give the ``exc_info`` back.

    The message text is never inspected: ``assert_exception_type`` compares the
    type and nothing else, which is precisely what Requirement 11.14 asks for.

    Requirements: 10.4, 10.5, 11.14
    """
    returned = NOT_RETURNED

    with pytest.raises(expected_type) as exc_info:
        returned = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

    assert_exception_type(exc_info, expected_type)
    assert returned is NOT_RETURNED
    return exc_info


@contextlib.contextmanager
def _composition_spies(use_case):
    """Wrap the three composition methods of ``use_case`` in spies that keep
    their real behaviour, and yield them as a tuple.

    ``wraps`` is used instead of a plain double so the spies cannot change the
    outcome of the case: if the chain ever reached the composition, the entries
    would still be built exactly as in production and the assertion would fail
    on the recorded call rather than on a corrupted result.

    Requirements: 10.4, 10.5
    """
    with contextlib.ExitStack() as stack:
        yield tuple(
            stack.enter_context(patch.object(
                use_case, name, wraps=getattr(use_case, name),
            ))
            for name in COMPOSITION_METHOD_NAMES
        )


def _assert_no_entry_composed(spies):
    """Assert that none of the three composition methods was invoked, i.e. that
    the number of composed Creative_Entries is 0.

    Requirements: 10.4, 10.5
    """
    for spy in spies:
        assert spy.call_count == 0


def _response_without_usable_creatives():
    """Build a fresh ad-sets response whose single selected Ad_Channel has no
    ``channel_creative`` at all: the query does return an ad-set, so stage 3
    fails later, at the "0 usable Published_Creatives" guard of Requirement
    5.9, instead of at the empty-response guard of Requirement 5.2.

    Requirements: 5.5, 5.9, 11.4
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(ad_set_id=120, ads_data=[
            _ad_with_channel(
                ad_id=501,
                ad_channel_id=9001,
                channel_ref_id=MAIN_FLOW_CHANNEL_ID,
                channel_creative=ABSENT,
            ),
        ]),
    ])


class TestFailureScenarios:
    """The six failure scenarios of ``execute()``, one case each.

    Every case asserts **only the type** of the exception, never the text of
    its message (Requirement 11.14). The two scenarios of the last two stages
    assert in addition that 0 Creative_Entries were composed and that
    ``execute()`` returned no value (Requirements 10.4, 10.5).

    Requirements: 3.3, 4.2, 5.2, 5.9, 7.2, 7.4, 8.5, 10.4, 10.5, 11.14, 11.15
    """

    # -- Scenario 1: account not found (Requirement 3.3) --------------------

    def test_missing_account_raises_data_not_found(self):
        """With no ``accounts`` record for ``self.user_id``, ``execute()``
        raises ``DataNotFoundException``: the ``DataNotFoundException`` of the
        already existing ``_get_account()`` propagates unchanged.

        Requirements: 3.3, 11.14
        """
        with main_flow_use_case(account=None) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    @pytest.mark.parametrize(
        'account', [value for _, value in MISSING_ACCOUNT_MATRIX],
        ids=_ids(MISSING_ACCOUNT_MATRIX),
    )
    def test_every_falsy_account_raises_data_not_found(self, account):
        """Every falsy value the account query may return fails the guard of
        ``_get_account()`` and yields ``DataNotFoundException``.

        Requirements: 3.3, 11.14
        """
        with main_flow_use_case(account=account) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    # -- Scenario 2: campaign not found (Requirement 4.2) -------------------

    def test_missing_campaign_raises_data_not_found(self):
        """With no campaign for the ``(campaign_id, brand_id, parent_account)``
        triple, ``execute()`` raises ``DataNotFoundException``.

        Requirements: 4.2, 11.14
        """
        with main_flow_use_case(campaign=None) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    @pytest.mark.parametrize(
        'campaign', [value for _, value in MISSING_CAMPAIGN_MATRIX],
        ids=_ids(MISSING_CAMPAIGN_MATRIX),
    )
    def test_every_unresolved_campaign_raises_data_not_found(self, campaign):
        """``None``, a dict without keys and a non-dict all leave the
        Campaña_Objetivo unresolved and yield ``DataNotFoundException``.

        Requirements: 4.2, 11.14
        """
        with main_flow_use_case(campaign=campaign) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    # -- Scenario 3: ad-sets query without results (Requirements 5.2, 5.9) --

    def test_empty_ad_sets_query_raises_data_not_found(self):
        """With an ad-sets query returning no results, ``execute()`` raises
        ``DataNotFoundException``.

        Requirements: 5.2, 11.14
        """
        with main_flow_use_case(ad_sets_response=None) as (
                use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    @pytest.mark.parametrize(
        'ad_sets_response', [value for _, value in EMPTY_AD_SETS_MATRIX],
        ids=_ids(EMPTY_AD_SETS_MATRIX),
    )
    def test_every_empty_ad_sets_response_raises_data_not_found(
            self, ad_sets_response):
        """Each response of the matrix of Requirement 5.2 —``None``, a non-dict
        and the four degradations of the ``data`` key— yields
        ``DataNotFoundException``.

        Requirements: 5.2, 11.14
        """
        with main_flow_use_case(ad_sets_response=ad_sets_response) as (
                use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    def test_zero_usable_published_creatives_raises_data_not_found(self):
        """With ad-sets present but no usable Published_Creative in any of
        them, ``execute()`` raises ``DataNotFoundException`` instead of
        returning a Resultado_de_Consulta with an empty ``creatives`` list.

        Requirements: 5.9, 11.14
        """
        with main_flow_use_case(
            ad_sets_response=_response_without_usable_creatives(),
        ) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    # -- Scenario 4: Campaign_Setup not found (Requirement 7.2) -------------

    def test_missing_campaign_setup_raises_data_not_found(self):
        """With no ``campaign-channel-publishes`` record for the
        ``(campaign_id, channel_id)`` pair, ``execute()`` raises
        ``DataNotFoundException``.

        Requirements: 7.2, 11.14
        """
        with main_flow_use_case(campaign_setup=None) as (
                use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    @pytest.mark.parametrize(
        'campaign_setup',
        [value for _, value in MISSING_CAMPAIGN_SETUP_MATRIX],
        ids=_ids(MISSING_CAMPAIGN_SETUP_MATRIX),
    )
    def test_every_unresolved_campaign_setup_raises_data_not_found(
            self, campaign_setup):
        """Every falsy and every non-dict return value of the Campaign_Setup
        query yields ``DataNotFoundException``.

        Requirements: 7.2, 11.14
        """
        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    # -- Scenario 5: meta_published other than True (Requirements 7.4, 11.15)

    def test_unpublished_campaign_raises_incorrect_validation(self):
        """With ``meta_published`` equal to ``False``, ``execute()`` raises
        ``IncorrectValidationException`` and composes 0 Creative_Entries.

        Requirements: 7.4, 10.4, 11.14
        """
        campaign_setup = make_campaign_setup(meta_published=False)

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _composition_spies(use_case) as spies:
                _execute_expecting(use_case, IncorrectValidationException)

        _assert_no_entry_composed(spies)

    @pytest.mark.parametrize(
        'meta_published',
        [value for _, value in REJECTED_META_PUBLISHED_MATRIX],
        ids=_ids(REJECTED_META_PUBLISHED_MATRIX),
    )
    def test_every_rejected_meta_published_value_raises_incorrect_validation(
            self, meta_published):
        """The five rejected values of ``meta_published`` and the absence of the
        attribute all yield ``IncorrectValidationException``, and none of them
        composes a single Creative_Entry: the comparison against ``True`` is by
        identity, so the truthy ``1``, ``'True'`` and ``'true'`` are rejected
        too.

        Requirements: 7.4, 10.4, 11.14, 11.15
        """
        campaign_setup = make_campaign_setup(meta_published=meta_published)

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _composition_spies(use_case) as spies:
                _execute_expecting(use_case, IncorrectValidationException)

        _assert_no_entry_composed(spies)

    # -- Scenario 6: Modo_de_Campaña not recognised (Requirement 8.5) -------

    def test_unsupported_campaign_mode_raises_incorrect_validation(self):
        """With a published Campaign_Setup declaring a Modo_de_Campaña outside
        the two supported ones, ``execute()`` raises
        ``IncorrectValidationException`` and composes 0 Creative_Entries.

        Requirements: 8.5, 10.5, 11.14
        """
        campaign_setup = make_campaign_setup(
            meta_published=True, meta_campaign_mode='OTRO',
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _composition_spies(use_case) as spies:
                _execute_expecting(use_case, IncorrectValidationException)

        _assert_no_entry_composed(spies)

    @pytest.mark.parametrize(
        'meta_campaign_mode',
        [value for _, value in UNSUPPORTED_CAMPAIGN_MODE_MATRIX],
        ids=_ids(UNSUPPORTED_CAMPAIGN_MODE_MATRIX),
    )
    def test_every_unsupported_campaign_mode_raises_incorrect_validation(
            self, meta_campaign_mode):
        """Every unsupported spelling of the Modo_de_Campaña —absent, ``None``,
        empty, lowercase, padded and unknown— yields
        ``IncorrectValidationException`` with 0 Creative_Entries composed: the
        membership test is exact and performs no normalisation.

        Requirements: 8.5, 10.5, 11.14
        """
        campaign_setup = make_campaign_setup(
            meta_published=True, meta_campaign_mode=meta_campaign_mode,
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _composition_spies(use_case) as spies:
                _execute_expecting(use_case, IncorrectValidationException)

        _assert_no_entry_composed(spies)

    # -- The six scenarios as a single table (Requirement 11.14) ------------

    @pytest.mark.parametrize('stage, kwargs, expected_type', [
        (
            'account-not-found',
            {'account': None},
            DataNotFoundException,
        ),
        (
            'campaign-not-found',
            {'campaign': None},
            DataNotFoundException,
        ),
        (
            'ad-sets-query-without-results',
            {'ad_sets_response': {'data': []}},
            DataNotFoundException,
        ),
        (
            'campaign-setup-not-found',
            {'campaign_setup': None},
            DataNotFoundException,
        ),
        (
            'meta-published-not-true',
            {'campaign_setup': None},  # replaced below by a built record
            IncorrectValidationException,
        ),
        (
            'campaign-mode-not-recognised',
            {'campaign_setup': None},  # replaced below by a built record
            IncorrectValidationException,
        ),
    ], ids=[
        'account-not-found',
        'campaign-not-found',
        'ad-sets-query-without-results',
        'campaign-setup-not-found',
        'meta-published-not-true',
        'campaign-mode-not-recognised',
    ])
    def test_the_six_scenarios_raise_their_own_exception_type(
            self, stage, kwargs, expected_type):
        """The six failure scenarios of Requirement 11.14 side by side: the
        first four raise ``DataNotFoundException`` and the last two
        ``IncorrectValidationException``, with the type as the only thing
        asserted.

        The two Campaign_Setup based scenarios build their record here, so the
        table above stays readable while the fixture is rebuilt per case
        (Requirement 11.4).

        Requirements: 3.3, 4.2, 5.2, 7.2, 7.4, 8.5, 11.14
        """
        if stage == 'meta-published-not-true':
            kwargs = {'campaign_setup': make_campaign_setup(
                meta_published=False,
            )}
        elif stage == 'campaign-mode-not-recognised':
            kwargs = {'campaign_setup': make_campaign_setup(
                meta_published=True, meta_campaign_mode='OTRO',
            )}

        with main_flow_use_case(**kwargs) as (use_case, _, _, _, _):
            _execute_expecting(use_case, expected_type)


# ---------------------------------------------------------------------------
# Task 12.9 — the order of the validations and their short circuits
# (Requirement 11.16)
#
# Requirement 10.2 fixes at 0 the number of invocations of the repositories of
# the *later* stages when a stage of the normative chain fails. The three cases
# Requirement 11.16 enumerates are, therefore, about what does **not** happen:
#
#   account failure ....... 0 invocations of ``CampaignRepository``,
#                           ``AdSetRepository`` and
#                           ``CampaignChannelPublishRepository``
#   campaign failure ...... 0 invocations of ``AdSetRepository`` and
#                           ``CampaignChannelPublishRepository``
#   ad-sets without result  0 invocations of
#                           ``CampaignChannelPublishRepository``
#
# Each one is asserted with ``assert_not_called`` on the double of the single
# method each later stage invokes, plus an empty ``mock_calls`` record on the
# repository instance as a whole, which also covers a hypothetical call to any
# other method of it.
#
# Three normative precedences complete the class, all of them expressed as an
# absence too:
#
#   Requirement 10.2  0 usable Published_Creatives short-circuits the
#                     Campaign_Setup query
#   Requirement 10.3  a missing Campaign_Setup yields exactly one
#                     ``DataNotFoundException``, with ``meta_published`` never
#                     evaluated
#   Requirement 10.5  a Campaign_Setup that is both unpublished and declares an
#                     unrecognised Modo_de_Campaña yields the
#                     ``IncorrectValidationException`` of the publication
#                     state, not the one of the mode
#
# The last two cannot be told apart by the exception type —both stages raise the
# very same class— so they are told apart by which validation ran: the spies of
# ``_validate_published`` and ``_validate_campaign_mode`` wrap the real methods,
# so the outcome of the case is production behaviour and only the call record is
# added.
# ---------------------------------------------------------------------------

#: The two validation methods of stages 5 and 6, in the order Requirement 10.5
#: fixes: the publication state first, the Modo_de_Campaña afterwards.
VALIDATION_METHOD_NAMES = ('_validate_published', '_validate_campaign_mode')

#: The four stages that reach Strapi, in the order of the normative chain of
#: Requirement 10.1, paired with the single repository method each one invokes.
#: The tuple drives the ordering case below, so the expected sequence is
#: spelled out once.
STRAPI_STAGES = (
    ('account', 'get_by_email'),
    ('campaign', 'get_by_id_brand_and_account'),
    ('ad-sets', AD_SETS_QUERY),
    ('campaign-setup', CAMPAIGN_SETUP_QUERY),
)


def _campaign_double(campaign_repository):
    """Return the double of the only ``CampaignRepository`` method the chain
    invokes, so the assertions read against a single named target, as
    ``_query_double`` and ``_setup_double`` already do for the other two
    stages.

    Requirements: 4.1, 11.4
    """
    return campaign_repository.get_by_id_brand_and_account


def _assert_stages_not_reached(*doubles):
    """Assert, with ``assert_not_called`` on each one, that none of the method
    doubles of the later stages was invoked.

    Requirements: 10.2, 11.16
    """
    for double in doubles:
        double.assert_not_called()


def _assert_repositories_untouched(*repositories):
    """Assert that the repository instances as a whole record no invocation at
    all, not even of a method other than the one of their stage.

    ``_assert_stages_not_reached`` pins the expected method; this one closes the
    door on an unexpected one, which is what keeps "0 invocations of the
    repository" of Requirement 10.2 literal.

    Requirements: 10.2, 11.16
    """
    for repository in repositories:
        assert repository.mock_calls == []
        assert repository.method_calls == []


@contextlib.contextmanager
def _validation_spies(use_case):
    """Wrap ``_validate_published`` and ``_validate_campaign_mode`` in spies
    that keep their real behaviour, and yield them as a tuple.

    ``wraps`` matters here for the same reason it does in
    ``_composition_spies``: the two stages must keep raising exactly what they
    raise in production, so the case is decided by the call record and never by
    a neutered validation.

    Requirements: 10.3, 10.5
    """
    with contextlib.ExitStack() as stack:
        yield tuple(
            stack.enter_context(patch.object(
                use_case, name, wraps=getattr(use_case, name),
            ))
            for name in VALIDATION_METHOD_NAMES
        )


def _recording_return(order, stage, double):
    """Return a ``side_effect`` for ``double`` that appends ``stage`` to
    ``order`` and then returns the value the double was configured with, so the
    global order of the four Strapi stages becomes observable without altering
    any of them.

    Requirements: 10.1, 11.4
    """
    configured = double.return_value

    def _record(*args, **kwargs):
        order.append(stage)
        return configured

    return _record


class TestValidationOrder:
    """The sequential order of the five validation stages and the short
    circuits it implies.

    Every case here asserts an absence: the repositories of the stages after
    the failing one record 0 invocations (Requirement 10.2), and the
    validations after the failing one never run (Requirements 10.3, 10.5).

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.16
    """

    # -- Short circuit 1: the account fails (Requirement 11.16) -------------

    def test_account_failure_leaves_the_three_later_stages_uninvoked(self):
        """With the account unresolved, the doubles of ``CampaignRepository``,
        ``AdSetRepository`` and ``CampaignChannelPublishRepository`` record 0
        invocations: stage 1 raises before stage 2 is even attempted.

        Requirements: 10.2, 11.16
        """
        with main_flow_use_case(account=None) as (
                use_case, account_repository, campaign_repository,
                ad_set_repository, publish_repository):
            _execute_expecting(use_case, DataNotFoundException)

            _assert_stages_not_reached(
                _campaign_double(campaign_repository),
                _query_double(ad_set_repository),
                _setup_double(publish_repository),
            )
            _assert_repositories_untouched(
                campaign_repository, ad_set_repository, publish_repository,
            )
            assert account_repository.get_by_email.call_count == 1

    # -- Short circuit 2: the campaign fails (Requirement 11.16) ------------

    def test_campaign_failure_leaves_the_two_later_stages_uninvoked(self):
        """With the Campaña_Objetivo unresolved, the doubles of
        ``AdSetRepository`` and ``CampaignChannelPublishRepository`` record 0
        invocations, while stage 1 did run exactly once.

        Requirements: 10.2, 11.16
        """
        with main_flow_use_case(campaign=None) as (
                use_case, account_repository, campaign_repository,
                ad_set_repository, publish_repository):
            _execute_expecting(use_case, DataNotFoundException)

            _assert_stages_not_reached(
                _query_double(ad_set_repository),
                _setup_double(publish_repository),
            )
            _assert_repositories_untouched(
                ad_set_repository, publish_repository,
            )
            assert account_repository.get_by_email.call_count == 1
            assert _campaign_double(campaign_repository).call_count == 1

    # -- Short circuit 3: the ad-sets query returns nothing (Req. 11.16) ----

    def test_empty_ad_sets_query_leaves_the_campaign_setup_uninvoked(self):
        """With an ad-sets query returning no results, the double of
        ``CampaignChannelPublishRepository`` records 0 invocations: stage 3
        raises before the Channel_ID it would need can exist.

        Requirements: 10.2, 11.16
        """
        with main_flow_use_case(ad_sets_response=None) as (
                use_case, account_repository, campaign_repository,
                ad_set_repository, publish_repository):
            _execute_expecting(use_case, DataNotFoundException)

            _assert_stages_not_reached(_setup_double(publish_repository))
            _assert_repositories_untouched(publish_repository)
            assert _query_double(ad_set_repository).call_count == 1

    @pytest.mark.parametrize(
        'ad_sets_response', [value for _, value in EMPTY_AD_SETS_MATRIX],
        ids=_ids(EMPTY_AD_SETS_MATRIX),
    )
    def test_every_empty_ad_sets_response_short_circuits_the_setup_query(
            self, ad_sets_response):
        """Each response of the matrix of Requirement 5.2 short-circuits stage
        4 identically: none of them reaches the Campaign_Setup query.

        Requirements: 5.2, 10.2, 11.16
        """
        with main_flow_use_case(ad_sets_response=ad_sets_response) as (
                use_case, _, _, _, publish_repository):
            _execute_expecting(use_case, DataNotFoundException)

            _assert_stages_not_reached(_setup_double(publish_repository))
            _assert_repositories_untouched(publish_repository)

    # -- Precedence 1: 0 usable creatives before stage 4 (Req. 10.2) --------

    def test_zero_usable_creatives_leaves_the_campaign_setup_uninvoked(self):
        """With ad-sets present but no usable Published_Creative in any of them,
        the ``DataNotFoundException`` of Requirement 5.9 is raised **inside**
        stage 3, so the Campaign_Setup query of stage 4 records 0 invocations
        even though the ad-sets query did return data.

        Requirements: 5.9, 10.2, 11.16
        """
        with main_flow_use_case(
            ad_sets_response=_response_without_usable_creatives(),
        ) as (use_case, _, _, ad_set_repository, publish_repository):
            _execute_expecting(use_case, DataNotFoundException)

            _assert_stages_not_reached(_setup_double(publish_repository))
            _assert_repositories_untouched(publish_repository)
            assert _query_double(ad_set_repository).call_count == 1

    # -- Precedence 2: stage 4 before stage 5 (Requirement 10.3) ------------

    def test_missing_campaign_setup_never_evaluates_the_publication_state(self):
        """A missing Campaign_Setup produces **exactly one**
        ``DataNotFoundException`` and the publication state is never evaluated:
        stage 4 precedes stage 5, so ``_validate_published`` —which would raise
        its own ``IncorrectValidationException`` against the absent record— is
        never reached, and neither is the validation of the Modo_de_Campaña nor
        any composition.

        Requirements: 10.3, 10.4, 11.16
        """
        with main_flow_use_case(campaign_setup=None) as (
                use_case, _, _, _, publish_repository):
            with _validation_spies(use_case) as (published_spy, mode_spy):
                with _composition_spies(use_case) as spies:
                    exc_info = _execute_expecting(
                        use_case, DataNotFoundException,
                    )

        published_spy.assert_not_called()
        mode_spy.assert_not_called()
        _assert_no_entry_composed(spies)

        # One raised exception, and one only: the single failing stage is
        # stage 4, whose query did run exactly once.
        assert _setup_double(publish_repository).call_count == 1
        assert exc_info.value.__context__ is None
        assert exc_info.value.__cause__ is None

    # -- Precedence 3: stage 5 before the mode validation (Req. 10.5) -------

    def test_unpublished_setup_with_unsupported_mode_raises_the_publish_error(
            self):
        """A Campaign_Setup that is **both** unpublished and declares an
        unrecognised Modo_de_Campaña yields the ``IncorrectValidationException``
        of the publication state and not the one of the mode: the two failures
        raise the same class, so what distinguishes them is that
        ``_validate_campaign_mode`` records 0 invocations while
        ``_validate_published`` ran exactly once.

        Requirements: 10.4, 10.5, 11.16
        """
        campaign_setup = make_campaign_setup(
            meta_published=False, meta_campaign_mode='OTRO',
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _validation_spies(use_case) as (published_spy, mode_spy):
                with _composition_spies(use_case) as spies:
                    _execute_expecting(use_case, IncorrectValidationException)

        mode_spy.assert_not_called()
        assert published_spy.call_count == 1
        _assert_no_entry_composed(spies)

    def test_published_setup_with_unsupported_mode_reaches_the_mode_check(self):
        """Counterpart of the case above, which is what makes it meaningful:
        with the very same unrecognised Modo_de_Campaña but a published
        Campaign_Setup, stage 5 passes and the validation of the mode **is**
        reached, raising from there with still 0 Creative_Entries composed.

        Requirements: 8.5, 10.5, 11.16
        """
        campaign_setup = make_campaign_setup(
            meta_published=True, meta_campaign_mode='OTRO',
        )

        with main_flow_use_case(campaign_setup=campaign_setup) as (
                use_case, _, _, _, _):
            with _validation_spies(use_case) as (published_spy, mode_spy):
                with _composition_spies(use_case) as spies:
                    _execute_expecting(use_case, IncorrectValidationException)

        assert published_spy.call_count == 1
        assert mode_spy.call_count == 1
        _assert_no_entry_composed(spies)

    # -- The order of the four Strapi stages (Requirement 10.1) -------------

    def test_the_four_strapi_stages_run_in_the_order_of_the_chain(self):
        """On a successful invocation the four read queries happen in the order
        of the normative chain: ``accounts``, ``campaigns``, ``ad-sets`` and
        ``campaign-channel-publishes``, each exactly once.

        The recorders keep the configured return value of each double, so the
        flow is the production one and only the global order is observed.

        Requirements: 10.1, 10.6, 11.16
        """
        order = []

        with main_flow_use_case() as (use_case, account_repository,
                                      campaign_repository, ad_set_repository,
                                      publish_repository):
            doubles = (
                account_repository.get_by_email,
                _campaign_double(campaign_repository),
                _query_double(ad_set_repository),
                _setup_double(publish_repository),
            )
            for (stage, _), double in zip(STRAPI_STAGES, doubles):
                double.side_effect = _recording_return(order, stage, double)

            result = use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert order == [stage for stage, _ in STRAPI_STAGES]
        assert set(result) == {'campaign', 'creatives', 'meta_url'}

# ---------------------------------------------------------------------------
# The degraded structures, end to end
# (Requirements 5.5, 5.6, 5.7, 5.9, 11.17, 11.18)
#
# The ``execute()`` counterparts of the degradation cases already covered at
# unit level by ``TestPublishedCreativesCollection``: the same five degraded
# structures of Requirements 5.5, 5.6 and 5.7, but now observed through the
# Resultado_de_Consulta instead of through the descriptor list.
#
# What the end to end angle adds is tolerance *of the whole chain*: the walk of
# stage 3 is not the only place a degraded structure can break things. A
# regression that skipped the degraded ad correctly but then composed an entry
# out of it, or that let the Channel_ID of stage 4 be resolved from an ad-channel
# the walk had discarded, would keep the unit level class green and would be
# caught here, because the assertions are made against the ``creatives`` list
# that ``execute()`` actually returns.
#
# Every case degrades **one** structure of **one** target and leaves the rest of
# the end to end fixture healthy, so the expectation is never the trivial "it
# did not blow up": it is the exact list of Creative_Entries the surviving ads
# must still produce, re-indexed from 0 (Requirement 7.5). A degradation that
# silently swallowed a healthy sibling would fail the case just as loudly as an
# ``AttributeError``.
#
# The single exception is the closing case of Requirement 11.18, where *every*
# ``channel_creative`` is degraded: there the expectation is the
# ``DataNotFoundException`` of Requirement 5.9 and, above all, that no
# Resultado_de_Consulta with an empty ``creatives`` list is ever returned.
# ---------------------------------------------------------------------------

#: The end to end fixture flattened to one tuple per Creative_Entry the healthy
#: response yields, in walk order: ``(ad_set_id, ad_set_name, ad_id,
#: ad_channel_id)``. Derived from ``MAIN_FLOW_AD_SETS`` so the cases below stay
#: in step with the fixture instead of restating it.
MAIN_FLOW_ENTRY_SOURCES = tuple(
    (ad_set_id, ad_set_name, ad_id, ad_channel_id)
    for ad_set_id, ad_set_name, ads in MAIN_FLOW_AD_SETS
    for ad_id, ad_channel_id in ads
)

#: The coordinates of the degraded target: the **first ad of the second
#: ad-set**. Neither the first ad-set nor the last one, which is what makes the
#: cases discriminating in both directions: the ads walked *before* the target
#: prove the walk reached it, the ones walked *after* prove it resumed, and the
#: Channel_ID of stage 4 keeps coming from the healthy first ad-channel of the
#: first ad-set, so a degraded target cannot silently move it (Requirement 6.4).
DEGRADED_AD_SET_POSITION = 1
DEGRADED_AD_POSITION = 0


def _flat_position(ad_set_position, ad_position):
    """Return the index the ad at the given coordinates occupies in
    ``MAIN_FLOW_ENTRY_SOURCES``.

    Requirements: 7.5, 11.4
    """
    walked = sum(
        len(ads) for _, _, ads in MAIN_FLOW_AD_SETS[:ad_set_position]
    )
    return walked + ad_position


#: The index of the degraded target inside ``MAIN_FLOW_ENTRY_SOURCES``.
DEGRADED_TARGET_POSITION = _flat_position(
    DEGRADED_AD_SET_POSITION, DEGRADED_AD_POSITION,
)

#: The sources that must survive a degradation of the **target ad**: the four
#: of the healthy fixture minus the target one.
SOURCES_WITHOUT_THE_TARGET_AD = tuple(
    source for position, source in enumerate(MAIN_FLOW_ENTRY_SOURCES)
    if position != DEGRADED_TARGET_POSITION
)

#: The sources that must survive a degradation of the **target ad-set** as a
#: whole: the two ads of the other ad-set.
SOURCES_WITHOUT_THE_TARGET_AD_SET = tuple(
    (ad_set_id, ad_set_name, ad_id, ad_channel_id)
    for position, (ad_set_id, ad_set_name, ads) in enumerate(MAIN_FLOW_AD_SETS)
    if position != DEGRADED_AD_SET_POSITION
    for ad_id, ad_channel_id in ads
)

#: The ``id`` of the extra, broken ad-channel used by the case that pins that a
#: broken element does not hide the selected one of its own ad. Distinct from
#: every ``ad_channel_id`` of the fixture, so it cannot be mistaken for one.
BROKEN_AD_CHANNEL_ID = 9999

#: The two supported Modos_de_Campaña, for the cases that run a degradation in
#: both branches.
BOTH_CAMPAIGN_MODES = (CreativeType.DYNAMIC.value, CreativeType.STANDARD.value)


def _healthy_target_ad(mode):
    """Return a target-ad builder that produces the **healthy** ad, i.e. the
    very ad ``_main_flow_response`` would have placed at the target position.

    Used as the control of the degraded builders: the response it produces must
    yield the four entries of the untouched fixture, which is what accredits
    that ``_response_with_degraded_ad`` itself degrades nothing.

    Requirements: 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return _main_flow_ad(
            ad_set_id, ad_set_name, ad_id, ad_channel_id, mode=mode,
        )

    return build


def _ad_with_degraded_channel_creative(channel_creative):
    """Return a target-ad builder whose single selected ad-channel carries the
    given unusable ``channel_creative`` — absent, ``None``, an empty ``dict`` or
    a non-``dict`` (Requirement 5.5).

    The ad-channel itself stays healthy and *selected*, and keeps declaring
    ``MAIN_FLOW_CHANNEL_ID``: what is degraded is only the Published_Creative it
    stores, so the ad is skipped at the guard of Requirement 5.5 and nowhere
    else.

    Requirements: 5.5, 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return _ad_with_channel(
            ad_id=ad_id,
            ad_channel_id=ad_channel_id,
            channel_ref_id=MAIN_FLOW_CHANNEL_ID,
            channel_creative=channel_creative,
        )

    return build


def _ad_with_creative_without_usable_ads(ads, mode):
    """Return a target-ad builder whose Published_Creative is usable as a
    ``dict`` but has its ``ads`` key degraded — absent, ``None``, an empty
    ``list`` or a non-``list`` (Requirement 5.6).

    The creative keeps every other key of its mode, so it passes the guard of
    Requirement 5.5 and is skipped one step later, at the guard of Requirement
    5.6: the two degradations are told apart by construction and not by luck.

    Requirements: 5.6, 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return _ad_with_channel(
            ad_id=ad_id,
            ad_channel_id=ad_channel_id,
            channel_ref_id=MAIN_FLOW_CHANNEL_ID,
            channel_creative=MAIN_FLOW_CREATIVE_BUILDERS[mode](
                creative_id=ad_set_id,
                name=ad_set_name,
                ad_id=ad_id,
                ad_channel_id=ad_channel_id,
                ads=ads,
            ),
        )

    return build


def _ad_with_degraded_ad_channels(**ad_kwargs):
    """Return a target-ad builder that degrades the ad side of the walk —
    ``attributes``, ``ad_channels`` or ``ad_channels.data`` — through the
    ``make_ad`` keyword arguments received (Requirement 5.7).

    The resulting ad carries no reachable ad-channel at all, so it contributes
    no Creative_Entry and the walk must resume with the next ad.

    Requirements: 5.7, 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return make_ad(ad_id=ad_id, **ad_kwargs)

    return build


def _ad_whose_ad_channel_has_no_attributes():
    """Return a target-ad builder whose single element of ``ad_channels.data``
    has **no** ``attributes`` node at all (Requirement 5.7).

    Such an element cannot declare ``selected``, so it is treated as not
    selected and its ad is skipped without raising.

    Requirements: 5.7, 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return _ad_with_channel(
            ad_id=ad_id,
            ad_channel_id=ad_channel_id,
            channel_ref_id=MAIN_FLOW_CHANNEL_ID,
            attributes=ABSENT,
        )

    return build


def _ad_with_a_broken_element_before_the_selected_one(mode):
    """Return a target-ad builder whose ``ad_channels.data`` holds **two**
    elements: a broken one without ``attributes`` first, and the healthy
    selected one second.

    The counterpart of ``_ad_whose_ad_channel_has_no_attributes``: a broken
    element must be skipped, not turned into a reason to discard the ad, so the
    target keeps producing its own Creative_Entry and the four entries of the
    healthy fixture survive intact.

    Requirements: 5.3, 5.7, 11.4, 11.17
    """
    def build(ad_set_id, ad_set_name, ad_id, ad_channel_id):
        return make_ad(ad_id=ad_id, ad_channels_data=[
            make_ad_channel(
                ad_channel_id=BROKEN_AD_CHANNEL_ID, attributes=ABSENT,
            ),
            make_ad_channel(
                ad_channel_id=ad_channel_id,
                selected=True,
                channel_ref_id=MAIN_FLOW_CHANNEL_ID,
                channel_creative=MAIN_FLOW_CREATIVE_BUILDERS[mode](
                    creative_id=ad_set_id,
                    name=ad_set_name,
                    ad_id=ad_id,
                    ad_channel_id=ad_channel_id,
                ),
            ),
        ])

    return build


def _response_with_degraded_ad(build_target_ad, mode=CreativeType.DYNAMIC.value):
    """Build a fresh end to end ad-sets response in which the **target ad** is
    the one ``build_target_ad`` returns and every other ad is the healthy one of
    ``_main_flow_response``.

    Requirements: 5.5, 5.6, 5.7, 11.4, 11.17
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(
            ad_set_id=ad_set_id,
            name=ad_set_name,
            ads_data=[
                build_target_ad(ad_set_id, ad_set_name, ad_id, ad_channel_id)
                if (ad_set_position, ad_position) == (
                    DEGRADED_AD_SET_POSITION, DEGRADED_AD_POSITION,
                )
                else _main_flow_ad(
                    ad_set_id, ad_set_name, ad_id, ad_channel_id, mode=mode,
                )
                for ad_position, (ad_id, ad_channel_id) in enumerate(ads)
            ],
        )
        for ad_set_position, (ad_set_id, ad_set_name, ads)
        in enumerate(MAIN_FLOW_AD_SETS)
    ])


def _response_with_degraded_ad_set(mode=CreativeType.DYNAMIC.value,
                                   **ad_set_kwargs):
    """Build a fresh end to end ad-sets response in which the **target ad-set**
    is degraded as a whole through the ``make_ad_set`` keyword arguments
    received —``attributes``, ``ads`` or ``ads_data``— and the other ad-set
    stays healthy (Requirement 5.7).

    Both ads of the degraded ad-set become unreachable, so the expectation of
    these cases is ``SOURCES_WITHOUT_THE_TARGET_AD_SET`` and not
    ``SOURCES_WITHOUT_THE_TARGET_AD``.

    Requirements: 5.7, 11.4, 11.17
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(ad_set_id=ad_set_id, name=ad_set_name, **ad_set_kwargs)
        if position == DEGRADED_AD_SET_POSITION
        else make_ad_set(
            ad_set_id=ad_set_id,
            name=ad_set_name,
            ads_data=[
                _main_flow_ad(
                    ad_set_id, ad_set_name, ad_id, ad_channel_id, mode=mode,
                )
                for ad_id, ad_channel_id in ads
            ],
        )
        for position, (ad_set_id, ad_set_name, ads)
        in enumerate(MAIN_FLOW_AD_SETS)
    ])


def _response_with_every_channel_creative_degraded(
        channel_creative=ABSENT, mode=CreativeType.DYNAMIC.value):
    """Build a fresh end to end ad-sets response whose **every** selected
    ad-channel carries an unusable ``channel_creative``.

    The two ad-sets and their four ads are present and their ad-channels are
    selected, so the query does return data and the empty-response guard of
    Requirement 5.2 is passed: the failure can only come from the "0 usable
    Published_Creatives" guard of Requirement 5.9, which is the scenario
    Requirement 11.18 asks for.

    Requirements: 5.5, 5.9, 11.4, 11.18
    """
    return make_ad_sets_response(ad_sets=[
        make_ad_set(
            ad_set_id=ad_set_id,
            name=ad_set_name,
            ads_data=[
                _ad_with_channel(
                    ad_id=ad_id,
                    ad_channel_id=ad_channel_id,
                    channel_ref_id=MAIN_FLOW_CHANNEL_ID,
                    channel_creative=channel_creative,
                )
                for ad_id, ad_channel_id in ads
            ],
        )
        for ad_set_id, ad_set_name, ads in MAIN_FLOW_AD_SETS
    ])


def _expected_entries_of(sources, mode=CreativeType.DYNAMIC.value):
    """Return the Creative_Entries the given sources must produce, re-indexed
    from 0 in their own order (Requirement 7.5).

    Built with the same ``_expected_dynamic_entry`` / ``_expected_standard_entry``
    baselines ``_expected_main_flow_entries`` uses, so a degraded case pins the
    31 values of every surviving entry and not merely how many survived.

    Requirements: 7.5, 8.1, 11.4, 11.17
    """
    expected_entry = MAIN_FLOW_EXPECTED_ENTRY_BUILDERS[mode]
    return [
        expected_entry(
            idx=idx,
            name=ad_set_name,
            adset_id=ad_set_id,
            ad_id=ad_id,
            adchannel_id=ad_channel_id,
        )
        for idx, (ad_set_id, ad_set_name, ad_id, ad_channel_id)
        in enumerate(sources)
    ]


def _execute_tolerating_degradation(use_case):
    """Invoke ``execute()`` with the end to end arguments and return its
    result, failing the case if a degraded structure leaked out as an
    ``AttributeError``, a ``TypeError`` or a ``KeyError``.

    Requirement 11.17 names those three types explicitly, so they are caught
    and reported as what they are —a broken defensive read— instead of reaching
    the report as an incidental error of the test.

    Requirements: 5.7, 11.17
    """
    try:
        return use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)
    except (AttributeError, TypeError, KeyError) as error:
        pytest.fail(
            'execute() let a degraded structure surface as '
            '{0}: {1}'.format(type(error).__name__, error)
        )


def _assert_entries_of(result, sources, mode=CreativeType.DYNAMIC.value):
    """Assert that the Resultado_de_Consulta exposes exactly the
    Creative_Entries of the given sources, in their order and re-indexed from 0.

    Three assertions in one, from the coarsest to the finest, so a failure says
    *what* diverged: the shape of the result, then how many entries survived,
    then their 31 values each.

    Requirements: 7.5, 7.8, 8.1, 11.17
    """
    assert set(result) == {'campaign', 'creatives', 'meta_url'}

    creatives = result['creatives']
    assert len(creatives) == len(sources)
    assert [entry['idx'] for entry in creatives] == list(range(len(sources)))
    assert creatives == _expected_entries_of(sources, mode=mode)
    assert result['campaign']['creatives_no'] == len(sources)


#: The five degraded structures of Requirement 11.17, each paired with the
#: factory that builds its response for a given Modo_de_Campaña and with the
#: sources that must survive it. Drives the case that runs the five in both
#: branches, so the five focused cases below stay readable one degradation at a
#: time while the matrix keeps them from being ``DYNAMIC``-only.
DEGRADED_STRUCTURES = (
    (
        'channel_creative-absent',
        lambda mode: _response_with_degraded_ad(
            _ad_with_degraded_channel_creative(ABSENT), mode=mode,
        ),
        SOURCES_WITHOUT_THE_TARGET_AD,
    ),
    (
        'creative-ads-absent',
        lambda mode: _response_with_degraded_ad(
            _ad_with_creative_without_usable_ads(ABSENT, mode), mode=mode,
        ),
        SOURCES_WITHOUT_THE_TARGET_AD,
    ),
    (
        'ads-data-absent',
        lambda mode: _response_with_degraded_ad_set(mode=mode, ads_data=ABSENT),
        SOURCES_WITHOUT_THE_TARGET_AD_SET,
    ),
    (
        'ad_channels-data-absent',
        lambda mode: _response_with_degraded_ad(
            _ad_with_degraded_ad_channels(ad_channels_data=ABSENT), mode=mode,
        ),
        SOURCES_WITHOUT_THE_TARGET_AD,
    ),
    (
        'ad_channel-without-attributes',
        lambda mode: _response_with_degraded_ad(
            _ad_whose_ad_channel_has_no_attributes(), mode=mode,
        ),
        SOURCES_WITHOUT_THE_TARGET_AD,
    ),
)


class TestDegradedStructures:
    """The five degraded structures of Requirements 5.5, 5.6 and 5.7, through
    ``execute()``.

    Each case degrades one structure of one target of the end to end fixture and
    asserts that ``execute()`` neither raises ``AttributeError``, ``TypeError``
    nor ``KeyError`` and that the ``creatives`` list holds exactly the entries
    the surviving ads must still produce (Requirement 11.17). The closing case
    degrades every ``channel_creative`` at once and asserts the
    ``DataNotFoundException`` of Requirement 5.9 (Requirement 11.18).

    Requirements: 5.5, 5.6, 5.7, 5.9, 11.17, 11.18
    """

    # -- The control of the degraded builders (Requirement 11.17) -----------

    @pytest.mark.parametrize('mode', BOTH_CAMPAIGN_MODES)
    def test_the_undegraded_target_yields_the_four_entries_of_the_fixture(
            self, mode):
        """With the target ad built as the healthy one, the response of
        ``_response_with_degraded_ad`` is the end to end fixture itself and the
        four entries of ``MAIN_FLOW_ENTRY_SOURCES`` come out untouched.

        The control the five cases below rest on: it is what tells "the
        degradation removed the target entry" from "the helper never built that
        entry in the first place".

        Requirements: 7.5, 8.1, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _healthy_target_ad(mode), mode=mode,
            ),
            mode=mode,
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, MAIN_FLOW_ENTRY_SOURCES, mode=mode)
        assert result['creatives'] == _expected_main_flow_entries(mode=mode)

    # -- 1. channel_creative absent or non-dict (Requirement 5.5) -----------

    @pytest.mark.parametrize(
        'channel_creative', UNUSABLE_CHANNEL_CREATIVES,
        ids=UNUSABLE_CHANNEL_CREATIVE_IDS,
    )
    def test_degraded_channel_creative_skips_only_its_own_ad(
            self, channel_creative):
        """A selected Ad_Channel whose ``channel_creative`` is absent, ``None``,
        an empty ``dict`` or a non-``dict`` contributes no Creative_Entry, and
        the three healthy ads keep contributing theirs: ``execute()`` returns a
        Resultado_de_Consulta of three entries without raising.

        Requirements: 5.5, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_degraded_channel_creative(channel_creative),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD)

    def test_the_degraded_channel_creative_reaches_no_entry(self):
        """Complement of the case above, stated as an absence: no Creative_Entry
        of the result carries the ``adset_id``, the ``ad_id`` or the
        ``adchannel_id`` of the degraded target.

        Requirements: 5.5, 8.6, 11.17
        """
        ad_set_id, _, ad_id, ad_channel_id = MAIN_FLOW_ENTRY_SOURCES[
            DEGRADED_TARGET_POSITION
        ]

        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_degraded_channel_creative(ABSENT),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        assert ad_id not in [entry['ad_id'] for entry in result['creatives']]
        assert ad_channel_id not in [
            entry['adchannel_id'] for entry in result['creatives']
        ]
        # The ad-set of the target does keep its other ad, so its identifier is
        # still present: what disappears is the ad, not the whole ad-set.
        assert ad_set_id in [entry['adset_id'] for entry in result['creatives']]

    # -- 2. ads absent or empty in the Published_Creative (Req. 5.6) --------

    @pytest.mark.parametrize(
        'ads', UNUSABLE_CREATIVE_ADS, ids=UNUSABLE_CREATIVE_ADS_IDS,
    )
    def test_creative_without_usable_ads_skips_only_its_own_ad(self, ads):
        """A Published_Creative whose ``ads`` key is absent, ``None``, an empty
        ``list`` or a non-``list`` contributes no Creative_Entry, and the three
        healthy ads keep contributing theirs.

        Requirements: 5.6, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_creative_without_usable_ads(
                    ads, CreativeType.DYNAMIC.value,
                ),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD)

    # -- 3. attributes.ads.data absent in the ad-set (Requirement 5.7) ------

    def test_ad_set_without_ads_data_keeps_the_other_ad_set(self):
        """An Ad_Set_de_Consulta whose ``attributes.ads.data`` is absent is
        treated as an empty collection: both of its ads become unreachable, the
        other ad-set keeps its two entries and ``execute()`` does not raise.

        Requirements: 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad_set(ads_data=ABSENT),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD_SET)

    @pytest.mark.parametrize(
        'kwargs', [value for _, value in DEGRADED_AD_SETS],
        ids=_ids(DEGRADED_AD_SETS),
    )
    def test_every_degraded_ad_set_keeps_the_other_ad_set(self, kwargs):
        """The whole matrix of the ad-set side of the walk —``attributes``,
        ``ads`` and ``ads.data``, each absent, ``None`` and of an unexpected
        type— behaves identically end to end: the degraded ad-set yields
        nothing, the healthy one yields its two entries.

        Requirements: 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad_set(**kwargs),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD_SET)

    # -- 4. ad_channels.data absent in the ad (Requirement 5.7) -------------

    def test_ad_without_ad_channels_data_skips_only_itself(self):
        """An Ad whose ``attributes.ad_channels.data`` is absent is treated as
        an empty collection: it contributes no Creative_Entry and the walk
        resumes with the remaining ads.

        Requirements: 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_degraded_ad_channels(ad_channels_data=ABSENT),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD)

    @pytest.mark.parametrize(
        'kwargs', [value for _, value in DEGRADED_ADS], ids=_ids(DEGRADED_ADS),
    )
    def test_every_degraded_ad_skips_only_itself(self, kwargs):
        """The whole matrix of the ad side of the walk —``attributes``,
        ``ad_channels`` and ``ad_channels.data``, each absent, ``None`` and of
        an unexpected type— behaves identically end to end: the degraded ad
        yields nothing and the three healthy ones yield their entries.

        Requirements: 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_degraded_ad_channels(**kwargs),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD)

    # -- 5. an element of ad_channels.data without attributes (Req. 5.7) ----

    def test_ad_channel_element_without_attributes_skips_only_its_ad(self):
        """An element of ``ad_channels.data`` without an ``attributes`` node
        cannot declare ``selected``, so it is treated as not selected: its ad
        contributes no Creative_Entry and ``execute()`` does not raise.

        Requirements: 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_whose_ad_channel_has_no_attributes(),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, SOURCES_WITHOUT_THE_TARGET_AD)

    def test_a_broken_element_does_not_hide_the_selected_one_of_its_ad(self):
        """With a broken element **before** the healthy selected one inside the
        same ``ad_channels.data``, the broken one is skipped and the selected one
        is still found: the four entries of the fixture survive, the target one
        included.

        The case that keeps the one above honest: "the ad was skipped" must be a
        consequence of having no selected ad-channel, not of having met a broken
        element.

        Requirements: 5.3, 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_degraded_ad(
                _ad_with_a_broken_element_before_the_selected_one(
                    CreativeType.DYNAMIC.value,
                ),
            ),
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, MAIN_FLOW_ENTRY_SOURCES)
        assert BROKEN_AD_CHANNEL_ID not in [
            entry['adchannel_id'] for entry in result['creatives']
        ]

    # -- The five structures, in both branches (Requirement 11.17) ----------

    @pytest.mark.parametrize('mode', BOTH_CAMPAIGN_MODES)
    @pytest.mark.parametrize(
        'build_response, expected_sources',
        [(factory, sources) for _, factory, sources in DEGRADED_STRUCTURES],
        ids=[case_id for case_id, _, _ in DEGRADED_STRUCTURES],
    )
    def test_the_five_degraded_structures_hold_in_both_modes(
            self, build_response, expected_sources, mode):
        """The five degraded structures of Requirement 11.17 behave the same in
        ``DYNAMIC`` and in ``STANDARD``: the tolerance of the walk is a property
        of the traversal and not of the branch that composes the entries.

        Requirements: 5.5, 5.6, 5.7, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=build_response(mode), mode=mode,
        ) as (use_case, _, _, _, _):
            result = _execute_tolerating_degradation(use_case)

        _assert_entries_of(result, expected_sources, mode=mode)

    # -- The Channel_ID survives the degradation (Requirement 6.4) ----------

    @pytest.mark.parametrize(
        'build_response, expected_sources',
        [(factory, sources) for _, factory, sources in DEGRADED_STRUCTURES],
        ids=[case_id for case_id, _, _ in DEGRADED_STRUCTURES],
    )
    def test_the_channel_id_of_the_setup_query_survives_the_degradation(
            self, build_response, expected_sources):
        """Whatever the degradation, the Campaign_Setup query still receives the
        Channel_ID of the **first** selected Ad_Channel of the walk, which the
        degraded target never is.

        Requirements: 6.4, 7.1, 11.17
        """
        with main_flow_use_case(
            ad_sets_response=build_response(CreativeType.DYNAMIC.value),
        ) as (use_case, _, _, _, publish_repository):
            _execute_tolerating_degradation(use_case)

            _setup_double(publish_repository).assert_called_once_with(
                MAIN_FLOW_CAMPAIGN_ID, MAIN_FLOW_CHANNEL_ID,
            )

    # -- Every channel_creative degraded (Requirements 5.9, 11.18) ----------

    def test_every_channel_creative_degraded_raises_data_not_found(self):
        """With **every** ``channel_creative`` of the fixture degraded, the walk
        ends with 0 usable Published_Creatives: ``execute()`` raises
        ``DataNotFoundException`` and returns no value at all, so a
        Resultado_de_Consulta with an empty ``creatives`` list is never exposed.

        Requirements: 5.9, 11.18
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_every_channel_creative_degraded(),
        ) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    @pytest.mark.parametrize(
        'channel_creative', UNUSABLE_CHANNEL_CREATIVES,
        ids=UNUSABLE_CHANNEL_CREATIVE_IDS,
    )
    @pytest.mark.parametrize('mode', BOTH_CAMPAIGN_MODES)
    def test_every_unusable_channel_creative_value_raises_data_not_found(
            self, channel_creative, mode):
        """Each unusable value of ``channel_creative`` —absent, ``None``, an
        empty ``dict`` and the non-``dict`` shapes— yields the very same
        outcome when it affects every Ad_Channel_Seleccionado, in both branches.

        Requirements: 5.5, 5.9, 11.18
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_every_channel_creative_degraded(
                channel_creative=channel_creative, mode=mode,
            ),
            mode=mode,
        ) as (use_case, _, _, _, _):
            _execute_expecting(use_case, DataNotFoundException)

    def test_no_entry_is_composed_when_every_creative_is_degraded(self):
        """The counterpart stated over the composition: with no usable
        Published_Creative the three composition methods record 0 invocations,
        so the empty ``creatives`` list of Requirement 5.9 does not even get
        built before being rejected.

        Requirements: 5.9, 10.4, 11.18
        """
        with main_flow_use_case(
            ad_sets_response=_response_with_every_channel_creative_degraded(),
        ) as (use_case, _, _, _, publish_repository):
            with _composition_spies(use_case) as spies:
                _execute_expecting(use_case, DataNotFoundException)

        _assert_no_entry_composed(spies)
        _assert_stages_not_reached(_setup_double(publish_repository))


# ---------------------------------------------------------------------------
# Absence of external traffic (Requirements 2.7, 2.8, 11.3)
#
# The use case is read-only over four Strapi read queries, so it must issue 0
# outbound HTTP requests, 0 Graph API invocations and 0 Redis accesses. The two
# module-level names of ``app.v2.use_cases.meta_ads`` through which such
# traffic would necessarily flow are ``requests`` and ``redis_client``: the
# spies below replace them **only to observe** them, and every case that
# installs them asserts 0 recorded invocations. That is the opposite of mocking
# an HTTP client to make a flow work (Requirement 11.3): a spy that must stay
# empty is an assertion, not a substitute.
# ---------------------------------------------------------------------------

#: The ``requests`` module as the use case resolves it. Patched only to be
#: asserted empty (Requirement 11.3).
REQUESTS_TARGET = 'app.v2.use_cases.meta_ads.requests'

#: The Redis client as the use case resolves it. Patched only to be asserted
#: empty (Requirement 2.7).
REDIS_CLIENT_TARGET = 'app.v2.use_cases.meta_ads.redis_client'

#: The single seam the ``deny_network`` fixture replaces: every request of
#: ``requests``, whatever its entry point, funnels through it.
NETWORK_GUARD_TARGET = 'requests.sessions.Session.request'

#: The name of the function ``deny_network`` installs on that seam, used to
#: recognise the guard as active from inside a running test case.
NETWORK_GUARD_NAME = '_raise_on_network_access'

#: An address no case may reach. Points at the discard port of the loopback
#: interface, so even if the guard were ever removed the case would fail loudly
#: instead of talking to a real endpoint.
UNREACHABLE_URL = 'http://127.0.0.1:9/never-reached'


@contextlib.contextmanager
def _external_traffic_spies():
    """Replace ``requests`` and ``redis_client`` in the namespace of the use
    case with two spies and yield them::

        with _external_traffic_spies() as (requests_spy, redis_client_spy):
            ...

    Both are ``MagicMock`` instances, so any attribute access that ends in a
    call —``requests.get(...)``, ``redis_client.get(...)``— is recorded instead
    of performed, and a recorded call is exactly what the cases below assert
    the absence of.

    This is the **only** place of the suite where an HTTP client or a Redis
    client is patched, and the audit of ``TestNoExternalTraffic`` pins that
    fact, so Requirement 11.3 stays verifiable from inside the suite.

    Requirements: 2.7, 2.8, 11.3
    """
    with patch(REQUESTS_TARGET) as requests_spy, \
            patch(REDIS_CLIENT_TARGET) as redis_client_spy:
        yield requests_spy, redis_client_spy


def _assert_no_external_traffic(requests_spy, redis_client_spy):
    """Assert that neither spy recorded a single interaction.

    ``mock_calls`` is compared against the empty list instead of checking a
    handful of method names, so an invocation of *any* member —a method never
    thought of, an attribute access that ends in a call, a nested one— is
    caught too.

    Requirements: 2.7, 11.3
    """
    assert requests_spy.mock_calls == [], (
        'the use case invoked the requests module: {0!r}'.format(
            requests_spy.mock_calls
        )
    )
    assert redis_client_spy.mock_calls == [], (
        'the use case touched the Redis client: {0!r}'.format(
            redis_client_spy.mock_calls
        )
    )


# ---------------------------------------------------------------------------
# Self-inspection machinery of the suite (Requirements 11.3, 11.20, 11.22)
#
# Requirements 11.3 and 11.22 are claims about the *suite itself*, not about
# the use case: "no HTTP client is mocked", "there is at least one case per
# criterion", "0 cases are skipped or expected to fail". They are therefore
# verified by parsing this very module with ``ast`` and asserting over the
# resulting tree, which keeps the audit exact —the syntax tree cannot be
# fooled by a comment or by a string that merely looks like a decorator— and
# keeps it honest, because the audit never matches its own literals: it only
# looks at decorators, at call expressions and at docstrings.
# ---------------------------------------------------------------------------

#: Absolute path of this very module: the object every self-audit inspects.
SUITE_PATH = os.path.realpath(__file__)

#: The path of the suite relative to the working directory of the validation
#: command of Requirement 11.20 (``sinergia/``), i.e. the literal argument that
#: command passes to ``pytest``.
SUITE_RELATIVE_PATH = os.path.join(
    'tests', 'v2', 'unit', 'use_cases',
    'test_facebook_get_launch_campaign_creatives.py',
)

#: The name of the project directory the whole specification is confined to
#: (Requirement 1.1) and the working directory of the command of Requirement
#: 11.20.
PROJECT_DIRECTORY_NAME = 'sinergia'

#: The interpreter of that command, relative to the project directory.
PROJECT_INTERPRETER_PATH = os.path.join('venv', 'bin', 'python')


def _read_suite_source():
    """Return the source text of this module.

    Requirements: 11.22
    """
    with open(SUITE_PATH, encoding='utf-8') as handle:
        return handle.read()


#: The syntax tree of this module, parsed once at import time.
SUITE_TREE = ast.parse(_read_suite_source(), filename=SUITE_PATH)

#: The criteria of Requirement 11, i.e. the 23 numbers that must each be
#: covered by at least one case of the suite (Requirement 11.22).
REQUIREMENT_11_CRITERIA = tuple(range(1, 24))

#: Matches a reference to a criterion of Requirement 11 inside a docstring.
CRITERION_REFERENCE = re.compile(r'\b11\.(\d{1,2})\b')

#: Matches a reference to any acceptance criterion, used to pin that every case
#: of the suite declares the traceability the audit rests on.
REQUIREMENT_REFERENCE = re.compile(r'\b\d{1,2}\.\d{1,2}\b')

#: The three marker names that would make a case be reported as skipped or as
#: an expected failure, which Requirement 11.22 fixes at 0.
SKIPPING_MARK_NAMES = ('skip', 'skipif', 'xfail')

#: The imperative counterparts of those markers, i.e. the calls that skip a
#: case from its own body.
SKIPPING_CALL_NAMES = ('skip', 'xfail', 'importorskip')

#: Every patch target the suite is allowed to install, spelled out so that a
#: new one cannot appear unnoticed. Eight of them are collaborators of the
#: module under test —the five repository classes of the two use cases, the
#: logger and the two builders the composition must never invoke— and the last
#: three are the observation-only seams of the section above.
EXPECTED_PATCH_TARGETS = frozenset((
    ACCOUNT_REPOSITORY_TARGET,
    CAMPAIGN_REPOSITORY_TARGET,
    AD_SET_REPOSITORY_TARGET,
    CAMPAIGN_CHANNEL_PUBLISH_REPOSITORY_TARGET,
    AD_CHANNEL_REPOSITORY_TARGET,
    'app.v2.use_cases.meta_ads.logger',
    'app.v2.use_cases.meta_ads.MetaAdsValidator',
    'app.v2.use_cases.meta_ads.MetaAdsPayloadBuilder',
    REQUESTS_TARGET,
    REDIS_CLIENT_TARGET,
    NETWORK_GUARD_TARGET,
))

#: The two targets that may be patched **only** to be asserted empty, together
#: with the single helper allowed to patch them.
OBSERVATION_ONLY_TARGETS = frozenset((REQUESTS_TARGET, REDIS_CLIENT_TARGET))
OBSERVATION_ONLY_OWNER = '_external_traffic_spies'

#: The single fixture of the suite and the owner of the network guard.
NETWORK_GUARD_OWNER = 'deny_network'


def _dotted_name(node):
    """Return the dotted source name of an expression —``patch``,
    ``patch.object``, ``monkeypatch.setattr``, ``pytest.mark.parametrize``— or
    the empty string when it is not a plain name chain.

    Requirements: 11.3, 11.22
    """
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ''
    parts.append(node.id)
    return '.'.join(reversed(parts))


def _resolved_string_literal(node):
    """Return the string an expression stands for: the literal itself, or the
    value of the module-level constant it names, or ``None``.

    The four repository targets are passed to ``patch`` through the module
    constants of ``patched_use_case``, so resolving names is what lets the
    audit see the dotted paths and not merely the identifiers.

    Requirements: 11.3
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        value = globals().get(node.id)
        if isinstance(value, str):
            return value
    return None


def _decorator_expression(decorator):
    """Return the name expression of a decorator, whether it is applied bare
    (``@pytest.fixture``) or called (``@pytest.fixture(autouse=True)``).

    Requirements: 11.3, 11.22
    """
    if isinstance(decorator, ast.Call):
        return decorator.func
    return decorator


def _iter_calls_with_owner(node, owner=''):
    """Yield ``(owner, call_node)`` for every call expression of ``node``,
    where ``owner`` is the dotted chain of the enclosing definitions
    (``'TestNoExternalTraffic.test_x'``, ``'_external_traffic_spies'``, or the
    empty string at module level).

    Requirements: 11.3, 11.22
    """
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)):
            child_owner = (
                '{0}.{1}'.format(owner, child.name) if owner else child.name
            )
        else:
            child_owner = owner
        if isinstance(child, ast.Call):
            yield owner, child
        for pair in _iter_calls_with_owner(child, child_owner):
            yield pair


def _suite_patch_sites():
    """Return every ``patch(<target>)`` and ``monkeypatch.setattr(<target>)``
    site of the suite as ``(owner, target, line)``.

    ``patch.object`` sites are deliberately excluded here and audited apart:
    they take an object and an attribute name instead of a dotted path.

    Requirements: 11.2, 11.3
    """
    sites = []
    for owner, node in _iter_calls_with_owner(SUITE_TREE):
        dotted = _dotted_name(node.func)
        if dotted == 'patch' or dotted.endswith('.setattr'):
            if not node.args:
                continue
            sites.append((
                owner, _resolved_string_literal(node.args[0]), node.lineno,
            ))
    return tuple(sites)


def _suite_patch_object_sites():
    """Return every ``patch.object(...)`` site of the suite as
    ``(owner, first_argument, keywords, line)``.

    Requirements: 11.3
    """
    sites = []
    for owner, node in _iter_calls_with_owner(SUITE_TREE):
        if _dotted_name(node.func) != 'patch.object' or not node.args:
            continue
        sites.append((
            owner,
            _dotted_name(node.args[0]),
            tuple(keyword.arg for keyword in node.keywords),
            node.lineno,
        ))
    return tuple(sites)


def _suite_fixture_markers():
    """Return the ``{name: FixtureFunctionMarker}`` mapping of every fixture
    **declared** by this module.

    The declarations are read from the syntax tree —a module-level function
    decorated with ``pytest.fixture``— instead of by scanning the namespace for
    the marker attribute: some objects of the namespace, ``unittest.mock.call``
    among them, fabricate any attribute asked of them and would be reported as
    fixtures.

    Requirements: 11.2, 11.3
    """
    markers = {}
    for node in SUITE_TREE.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            expression = _decorator_expression(decorator)
            if _dotted_name(expression) == 'pytest.fixture':
                markers[node.name] = getattr(
                    globals()[node.name], '_pytestfixturefunction',
                )
    return markers


def _criteria_of(docstring):
    """Return the criteria of Requirement 11 a docstring refers to.

    Requirements: 11.22
    """
    return {
        int(number) for number in CRITERION_REFERENCE.findall(docstring or '')
    }


def _suite_test_cases():
    """Return every test case of the suite as
    ``(class_name, test_name, docstring, criteria)``.

    The criteria of a case are the ones of its own docstring **plus** the ones
    of the docstring of its class: a class states the criteria the whole class
    characterises and each case narrows them down, which is the convention
    every class of this module follows. Counting both is therefore what makes
    the audit agree with how the suite documents itself.

    Requirements: 11.22
    """
    cases = []
    for node in SUITE_TREE.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith('test'):
            docstring = ast.get_docstring(node)
            cases.append((
                '', node.name, docstring, frozenset(_criteria_of(docstring)),
            ))
        if not isinstance(node, ast.ClassDef):
            continue
        if not node.name.startswith('Test'):
            continue
        class_criteria = _criteria_of(ast.get_docstring(node))
        for item in node.body:
            if not isinstance(item, ast.FunctionDef):
                continue
            if not item.name.startswith('test'):
                continue
            docstring = ast.get_docstring(item)
            cases.append((
                node.name,
                item.name,
                docstring,
                frozenset(_criteria_of(docstring) | class_criteria),
            ))
    return tuple(cases)


def _suite_skipping_decorators():
    """Return every decorator of the suite that would skip a case or mark it as
    an expected failure, as ``(definition, decorator, line)``.

    Requirements: 11.22
    """
    found = []
    for node in ast.walk(SUITE_TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
            continue
        for decorator in node.decorator_list:
            dotted = _dotted_name(_decorator_expression(decorator))
            if set(dotted.split('.')) & set(SKIPPING_MARK_NAMES):
                found.append((node.name, dotted, decorator.lineno))
    return tuple(found)


def _suite_skipping_calls():
    """Return every imperative skip of the suite —``pytest.skip``,
    ``pytest.xfail``, ``pytest.importorskip``— as ``(owner, call, line)``.

    Requirements: 11.22
    """
    found = []
    for owner, node in _iter_calls_with_owner(SUITE_TREE):
        dotted = _dotted_name(node.func)
        if dotted.split('.')[-1] in SKIPPING_CALL_NAMES:
            found.append((owner, dotted, node.lineno))
    return tuple(found)


def _suite_module_level_marks():
    """Return the lines where the suite assigns ``pytestmark``, which would
    apply a marker —a skip among them— to every case at once.

    Requirements: 11.22
    """
    return tuple(
        node.lineno for node in SUITE_TREE.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == 'pytestmark'
            for target in node.targets
        )
    )


def _suite_imported_modules():
    """Return every module name the suite imports.

    Requirements: 11.1
    """
    imported = []
    for node in ast.walk(SUITE_TREE):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            imported.append(module)
            imported.extend(
                '{0}.{1}'.format(module, alias.name) for alias in node.names
            )
    return tuple(imported)


def _project_directory():
    """Return the project directory the suite lives in, i.e. the working
    directory of the validation command of Requirement 11.20.

    Requirements: 11.20
    """
    tail = os.sep + SUITE_RELATIVE_PATH
    assert SUITE_PATH.endswith(tail), (
        'the suite is not at the path the validation command of Requirement '
        '11.20 passes to pytest: {0}'.format(SUITE_PATH)
    )
    return SUITE_PATH[:-len(tail)]


class TestNoExternalTraffic:
    """The query issues no external traffic at all.

    Four Strapi read queries through four test doubles and nothing else: 0
    outbound HTTP requests, 0 Graph API invocations, 0 Redis accesses and no
    reachable ``NotAccessException``. The spies of ``_external_traffic_spies``
    observe the two seams that would carry such traffic and must stay empty,
    and the ``deny_network`` fixture —autouse over every case of the suite— is
    the safety net that turns a leak into an immediate failure instead of real
    traffic.

    Requirements: 2.7, 2.8, 11.3
    """

    # -- The requests module is never invoked (Requirement 11.3) ------------

    def test_requests_is_never_invoked_during_a_main_flow(self):
        """A complete, successful main flow records **0** invocations on the
        ``requests`` module of the namespace of the use case, and still returns
        the four Creative_Entries of the end to end fixture.

        Both halves matter: the absence of traffic is only meaningful next to
        the evidence that the flow did run to completion.

        Requirements: 2.7, 11.3
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            with _external_traffic_spies() as (requests_spy, redis_client_spy):
                result = use_case.execute(
                    MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
                )

        _assert_entries_of(result, MAIN_FLOW_ENTRY_SOURCES)
        _assert_no_external_traffic(requests_spy, redis_client_spy)

    @pytest.mark.parametrize('mode', BOTH_CAMPAIGN_MODES)
    def test_no_external_traffic_in_either_campaign_mode(self, mode):
        """Neither branch of the composition reaches for the network: the
        ``DYNAMIC`` and the ``STANDARD`` flows both record 0 invocations on the
        two seams.

        Requirements: 2.7, 11.3
        """
        with main_flow_use_case(mode=mode) as (use_case, _, _, _, _):
            with _external_traffic_spies() as (requests_spy, redis_client_spy):
                result = use_case.execute(
                    MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID,
                )

        _assert_entries_of(result, MAIN_FLOW_ENTRY_SOURCES, mode=mode)
        _assert_no_external_traffic(requests_spy, redis_client_spy)

    def test_no_external_traffic_when_the_flow_fails_either(self):
        """A flow that fails at its first stage records 0 invocations too: the
        absence of traffic is a property of the whole use case and not of its
        happy path.

        Requirements: 2.7, 3.3, 11.3
        """
        with main_flow_use_case(account=None) as (use_case, _, _, _, _):
            with _external_traffic_spies() as (requests_spy, redis_client_spy):
                _execute_expecting(use_case, DataNotFoundException)

        _assert_no_external_traffic(requests_spy, redis_client_spy)

    def test_the_two_spies_do_record_an_invocation_when_touched(self):
        """The control of the three cases above: touching the two patched seams
        **is** recorded, so an empty ``mock_calls`` means "nobody touched them"
        and not "the spy was blind".

        Requirements: 2.7, 11.3
        """
        with _external_traffic_spies() as (requests_spy, redis_client_spy):
            meta_ads_module.requests.get(UNREACHABLE_URL)
            meta_ads_module.redis_client.get('facebook_access_token:someone')

            assert requests_spy.mock_calls != []
            assert redis_client_spy.mock_calls != []

        with pytest.raises(AssertionError):
            _assert_no_external_traffic(requests_spy, redis_client_spy)

    def test_the_two_seams_are_the_real_names_of_the_module_under_test(self):
        """``requests`` and ``redis_client`` are real module-level names of
        ``app.v2.use_cases.meta_ads``, and the patches are installed without
        ``create=True``, so the two cases above cannot be passing against
        attributes that do not exist.

        Requirements: 2.7, 11.3
        """
        assert hasattr(meta_ads_module, 'requests')
        assert hasattr(meta_ads_module, 'redis_client')

        original_requests = meta_ads_module.requests
        original_redis_client = meta_ads_module.redis_client

        with _external_traffic_spies() as (requests_spy, redis_client_spy):
            assert meta_ads_module.requests is requests_spy
            assert meta_ads_module.redis_client is redis_client_spy

        assert meta_ads_module.requests is original_requests
        assert meta_ads_module.redis_client is original_redis_client

    # -- The Redis client is never touched (Requirements 2.7, 2.8) ----------

    def test_the_access_token_key_of_redis_is_never_read(self):
        """The Redis client records 0 invocations of any kind during a main
        flow, hence 0 accesses to the ``facebook_access_token:{user_id}`` key:
        the query never needs a Meta access token.

        Requirements: 2.7, 2.8
        """
        with main_flow_use_case() as (use_case, _, _, _, _):
            with _external_traffic_spies() as (_, redis_client_spy):
                use_case.execute(MAIN_FLOW_BRAND_ID, MAIN_FLOW_CAMPAIGN_ID)

        assert redis_client_spy.mock_calls == []
        assert redis_client_spy.get.call_count == 0
        assert redis_client_spy.set.call_count == 0

    def test_the_source_of_the_use_case_names_no_token_no_redis_and_no_client(
            self):
        """Stated over the production source instead of over an execution: the
        class under test mentions neither the Redis client, nor a token, nor an
        HTTP request, nor the Graph API, so **no** execution path of
        ``execute()`` could reach them and ``NotAccessException`` is
        unreachable.

        Requirements: 2.7, 2.8
        """
        source = inspect.getsource(
            FacebookGetLaunchCampaignCreativesUseCase
        ).lower()

        assert 'redis' not in source
        assert 'token' not in source
        assert 'request' not in source
        assert 'graph.facebook.com' not in source
        assert 'notaccessexception' not in source

    # -- The network guard covers the whole suite (Requirement 11.3) --------

    def test_deny_network_is_an_autouse_function_scoped_fixture(self):
        """``deny_network`` is declared ``autouse=True`` at function scope, so
        it wraps **every** case of the suite without any of them having to ask
        for it.

        Requirements: 11.2, 11.3
        """
        marker = getattr(deny_network, '_pytestfixturefunction')

        assert marker.autouse is True
        assert marker.scope == 'function'

    def test_deny_network_is_the_only_fixture_of_the_suite(self):
        """It is also the **only** fixture this module defines, and therefore
        the only autouse one: no other fixture can undo the guard, and the
        scaffolding of every case goes through the two explicit context
        managers instead.

        Requirements: 11.2, 11.3
        """
        markers = _suite_fixture_markers()

        assert set(markers) == {NETWORK_GUARD_OWNER}
        assert {
            name for name, marker in markers.items() if marker.autouse
        } == {NETWORK_GUARD_OWNER}

    def test_the_guard_is_installed_while_a_case_of_the_suite_runs(self):
        """Seen from inside a running case: the single seam of ``requests``
        every request funnels through is the guard function of this module and
        not the real implementation.

        Requirements: 11.2, 11.3
        """
        guard = requests.sessions.Session.request

        assert getattr(guard, '__name__', '') == NETWORK_GUARD_NAME
        assert getattr(guard, '__module__', '') == __name__

    def test_a_request_through_the_public_api_raises_instead_of_connecting(
            self):
        """A request issued through the public API of ``requests`` raises
        ``AssertionError`` before any socket is opened, which is what accredits
        that 0 cases of the suite open a real connection.

        Requirements: 11.2, 11.3
        """
        with pytest.raises(AssertionError) as exc_info:
            requests.get(UNREACHABLE_URL, timeout=0.001)

        assert 'Network access is forbidden' in str(exc_info.value)

    def test_a_request_through_a_session_raises_as_well(self):
        """And so does one issued through a ``Session`` built by hand, the
        lower level entry point the public API delegates to.

        Requirements: 11.2, 11.3
        """
        with pytest.raises(AssertionError):
            requests.sessions.Session().request('GET', UNREACHABLE_URL)

    # -- No client is substituted for behaviour (Requirement 11.3) ---------

    def test_the_suite_patches_only_the_expected_targets(self):
        """Every patch target of the suite belongs to the declared allowlist:
        the five repository classes of the two use cases, the logger, the two
        builders the composition must never invoke, the two observation-only
        seams and the network guard. Nothing else is replaced anywhere.

        Requirements: 11.2, 11.3
        """
        sites = _suite_patch_sites()
        assert sites

        unresolved = [site for site in sites if site[1] is None]
        assert unresolved == [], (
            'a patch target could not be resolved to a dotted path: '
            '{0!r}'.format(unresolved)
        )

        targets = {target for _, target, _ in sites}
        assert targets == set(EXPECTED_PATCH_TARGETS), (
            'unexpected patch targets: {0!r}; missing ones: {1!r}'.format(
                sorted(targets - set(EXPECTED_PATCH_TARGETS)),
                sorted(set(EXPECTED_PATCH_TARGETS) - targets),
            )
        )

    def test_no_http_client_is_patched_outside_the_observation_spies(self):
        """The ``requests`` module and the Redis client are patched **only** by
        ``_external_traffic_spies``, whose every user asserts 0 recorded calls,
        and the network guard is patched only by ``deny_network``.

        That is the difference Requirement 11.3 draws: the suite never mocks an
        HTTP client to make a flow work, it installs spies that must stay
        empty.

        Requirements: 11.3
        """
        for owner, target, line in _suite_patch_sites():
            if target in OBSERVATION_ONLY_TARGETS:
                assert owner == OBSERVATION_ONLY_OWNER, (
                    '{0} patched at line {1} outside {2}'.format(
                        target, line, OBSERVATION_ONLY_OWNER,
                    )
                )
            if target == NETWORK_GUARD_TARGET:
                assert owner == NETWORK_GUARD_OWNER, (
                    'the network guard is installed outside {0} at line '
                    '{1}'.format(NETWORK_GUARD_OWNER, line)
                )

    def test_the_observation_spies_are_used_only_by_this_class(self):
        """And ``_external_traffic_spies`` itself is entered only by the cases
        of this class, so no other case of the suite can be silently relying on
        a neutered ``requests`` or on a neutered Redis client.

        Requirements: 11.3
        """
        owners = {
            owner for owner, node in _iter_calls_with_owner(SUITE_TREE)
            if _dotted_name(node.func) == OBSERVATION_ONLY_OWNER
        }
        assert owners

        for owner in owners:
            assert owner.split('.')[0] == 'TestNoExternalTraffic', (
                '{0} is entered from {1}'.format(OBSERVATION_ONLY_OWNER, owner)
            )

    def test_every_patch_object_site_wraps_the_object_under_test(self):
        """The only attribute-level patches of the suite are the spies that
        wrap methods **of the use case instance itself** —the composition and
        validation spies of Requirements 10.3, 10.4 and 10.5— and every one of
        them keeps the real behaviour through ``wraps``. None of them replaces
        a collaborator.

        Requirements: 11.3
        """
        sites = _suite_patch_object_sites()
        assert sites

        for owner, first_argument, keywords, line in sites:
            assert first_argument == 'use_case', (
                'patch.object at line {0} targets {1!r} instead of the use '
                'case'.format(line, first_argument)
            )
            assert 'wraps' in keywords, (
                'the spy at line {0} of {1} does not keep the real '
                'behaviour'.format(line, owner)
            )


class TestSuiteSelfAudit:
    """The suite audits itself against Requirement 11.

    Two claims of Requirement 11 are about the suite and not about the use
    case, so they are verified here by inspecting this very module: every one
    of the 23 criteria of Requirement 11 is covered by at least one case
    (Requirement 11.22), and the number of cases marked as skipped or as
    expected failures is 0, which is also what the validation command of
    Requirement 11.20 must report.

    Requirements: 11.1, 11.20, 11.22
    """

    # -- One case per criterion (Requirement 11.22) -------------------------

    def test_the_suite_is_made_of_test_cases_inside_test_classes(self):
        """The audit sees the suite it means to audit: a non-empty set of cases
        grouped in classes, every one of them with a docstring.

        Requirements: 11.22
        """
        cases = _suite_test_cases()

        assert len(cases) > 200
        assert {class_name for class_name, _, _, _ in cases} == {
            node.name for node in SUITE_TREE.body
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test')
        }
        assert all(docstring for _, _, docstring, _ in cases)

    def test_every_case_declares_the_criteria_it_covers(self):
        """Every case documents at least one acceptance criterion in its
        docstring, which is the traceability the coverage audit below rests on.

        Requirements: 11.22
        """
        undeclared = [
            (class_name, test_name)
            for class_name, test_name, docstring, _ in _suite_test_cases()
            if not REQUIREMENT_REFERENCE.search(docstring or '')
        ]

        assert undeclared == [], (
            'these cases declare no requirement: {0!r}'.format(undeclared)
        )

    def test_every_criterion_of_requirement_11_has_at_least_one_case(self):
        """The heart of Requirement 11.22: each of the 23 criteria of
        Requirement 11 is covered by at least one case of the suite.

        Requirements: 11.22
        """
        cases = _suite_test_cases()
        coverage = {
            criterion: [
                '{0}.{1}'.format(class_name, test_name)
                for class_name, test_name, _, criteria in cases
                if criterion in criteria
            ]
            for criterion in REQUIREMENT_11_CRITERIA
        }

        uncovered = sorted(
            criterion for criterion, covering in coverage.items()
            if not covering
        )
        assert uncovered == [], (
            'these criteria of Requirement 11 have no test case: '
            '{0!r}'.format(uncovered)
        )

    def test_the_criteria_covered_are_exactly_the_ones_enumerated(self):
        """And no case claims a criterion number beyond the enumeration, so a
        typo in a docstring cannot masquerade as coverage.

        Requirements: 11.22
        """
        claimed = set()
        for _, _, _, criteria in _suite_test_cases():
            claimed |= criteria

        assert claimed == set(REQUIREMENT_11_CRITERIA), (
            'criteria claimed outside the enumeration: {0!r}'.format(
                sorted(claimed - set(REQUIREMENT_11_CRITERIA))
            )
        )

    # -- Zero skips and zero expected failures (Requirements 11.20, 11.22) --

    def test_the_suite_declares_no_skipping_decorator(self):
        """No decorator of the suite skips a case or marks it as an expected
        failure: the only markers in use are ``parametrize`` ones.

        Requirements: 11.20, 11.22
        """
        found = _suite_skipping_decorators()

        assert found == (), (
            'these definitions carry a skipping decorator: {0!r}'.format(found)
        )

    def test_the_suite_skips_no_case_from_its_own_body(self):
        """Nor does any case skip itself imperatively, through ``pytest.skip``,
        ``pytest.xfail`` or ``pytest.importorskip``.

        Requirements: 11.20, 11.22
        """
        found = _suite_skipping_calls()

        assert found == (), (
            'these call sites skip a case: {0!r}'.format(found)
        )

    def test_the_suite_applies_no_module_level_marker(self):
        """And it declares no ``pytestmark``, which would apply a marker —a
        skip among them— to the 23 classes at once.

        Requirements: 11.20, 11.22
        """
        assert _suite_module_level_marks() == ()

    def test_no_collected_case_of_the_suite_carries_a_skipping_marker(
            self, request):
        """The same claim at runtime, over the items pytest actually collected
        from this module: none of them carries a ``skip``, a ``skipif`` or an
        ``xfail`` marker, so the run of Requirement 11.20 reports 0 skipped and
        0 expected failures.

        Requirements: 11.20, 11.22
        """
        items = [
            item for item in request.session.items
            if os.path.realpath(
                str(getattr(item, 'path', getattr(item, 'fspath', '')))
            ) == SUITE_PATH
        ]

        assert items
        assert request.node in items

        for item in items:
            for mark_name in SKIPPING_MARK_NAMES:
                assert item.get_closest_marker(mark_name) is None, (
                    '{0} carries the marker {1}'.format(item.nodeid, mark_name)
                )

    # -- The single new file, at the path of the command (Req. 11.1, 11.20) -

    def test_the_suite_lives_at_the_path_of_the_validation_command(self):
        """The suite is the very file the validation command of Requirement
        11.20 names —``SUITE_RELATIVE_PATH`` relative to ``sinergia/``— and
        that project directory holds the interpreter the command invokes.

        Requirements: 11.1, 11.20
        """
        project_directory = _project_directory()

        assert os.path.basename(project_directory) == PROJECT_DIRECTORY_NAME
        assert os.path.isfile(
            os.path.join(project_directory, PROJECT_INTERPRETER_PATH)
        )
        assert os.path.isfile(SUITE_PATH)

    def test_no_conftest_module_applies_to_the_suite(self):
        """No ``conftest.py`` exists between the suite and the ``tests``
        directory: the scaffolding of every case lives in this module, which is
        what keeps the specification at exactly one new file and honours the
        scope protocol.

        Requirements: 11.1
        """
        directory = os.path.dirname(SUITE_PATH)
        visited = []

        for _ in range(len(SUITE_RELATIVE_PATH.split(os.sep)) + 1):
            visited.append(directory)
            conftest = os.path.join(directory, 'conftest.py')
            assert not os.path.exists(conftest), (
                'an unexpected {0} applies to the suite'.format(conftest)
            )
            if os.path.basename(directory) == 'tests':
                break
            directory = os.path.dirname(directory)

        assert os.path.basename(visited[-1]) == 'tests'

    def test_the_suite_imports_no_other_test_module(self):
        """And it imports no other test module and no ``conftest``: every
        builder, fixture and helper it uses is defined in this file, so the
        suite stands alone.

        Requirements: 11.1
        """
        for name in _suite_imported_modules():
            parts = name.split('.')
            assert not any(part.startswith('test_') for part in parts), (
                'the suite imports the test module {0!r}'.format(name)
            )
            assert 'conftest' not in parts
            assert 'tests' not in parts
