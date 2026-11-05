"""Unit test suite for the STANDARD branch of ``FacebookLaunchCampaignUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookLaunchCampaignUseCase``,
specifically the three parity gaps closed by the
``meta-ads-standard-launch-campaign`` spec:

- ``_is_campaign_valid`` STANDARD branch (Requirement 2),
- ``_build_response``/``_build_standard_creative_published`` (Requirement 3),
- the hardened ``except`` block of ``execute()`` plus ``_is_meta_auth_error``
  (Requirement 5).

This module holds the shared test infrastructure of the suite: the private
``ABSENT`` sentinel, the state-free payload builders, the ``EXPECTED_KEYS``
constant with the 31 fixed keys of Requirement 3.2, the ``use_case_factory``
fixture (which patches the *three* repository classes the constructor
instantiates), the ``patch_redis_client`` context manager, and the
module-level ``deny_network`` autouse guard. The behavioural test cases
themselves live in the ``Test*`` classes added by the subsequent tasks.

Conventions replicated from the sibling suite
``tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py``:

- Every builder returns brand new dicts and brand new lists on each call; no
  mutable default arguments, nothing shared between invocations.
- Any builder keyword whose value is the ``ABSENT`` sentinel removes that key
  from the produced dict entirely, which is what distinguishes "key omitted"
  from "key present with value ``None``" (needed by Requirements 6.5, 6.15).
- Assertions about ``SinergiaException`` subclasses are made on
  ``exc_info.value.text``/``exc_info.value.code``, never on
  ``str(exc_info.value)``: ``SinergiaException.__init__`` calls
  ``super().__init__(args)`` with the *tuple* ``args`` instead of the
  unpacked ``text`` (verified in ``app/exceptions/base.py``), so
  ``str(exc)`` is always the literal ``"()"`` regardless of the text.
- No external dependency is exercised: Strapi repositories, Redis and the
  Meta Graph API are all replaced by test doubles. For ``execute()``
  scenarios the ``_publish_campaign``/``_publish_adset``/``_publish_media``/
  ``_publish_ad_creative``/``_publish_ad`` helpers are patched with
  ``patch.object`` rather than building full HTTP responses.

Requirements: 6.1, 6.16
"""

import itertools
from contextlib import ExitStack, contextmanager
from unittest.mock import call, patch

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from app.exceptions.base import RESTClientException, SinergiaException
from app.v2.use_cases.facebook_validator_service import CreativeType
from app.v2.use_cases.meta_ads import FacebookLaunchCampaignUseCase


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided, omit it from the resulting dict" from "this key was provided
    with the value ``None``". Passing ``some_key=ABSENT`` to any builder in
    this module removes ``some_key`` from the produced dict.

    Requirements: 6.1, 6.16
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


def _merge(base, overrides):
    """Merge ``overrides`` into ``base`` and drop every key whose final
    value is the ``ABSENT`` sentinel.

    Shared by all builders below so that ``builder(key=ABSENT)`` uniformly
    means "omit this key entirely".

    Requirements: 6.1
    """
    base.update(overrides)
    return {key: value for key, value in base.items() if value is not ABSENT}


# The 31 fixed keys of the Creative_Publicado (Requirement 3.2), in the
# order in which `_build_standard_creative_published` emits them. Used for
# the exact set comparisons of tasks 9.1 and 9.2
# (`assert set(entry.keys()) == EXPECTED_KEYS`), never for subset checks.
EXPECTED_KEYS = frozenset(
    {
        "idx",
        "name",
        "adset_id",
        "ad_id",
        "adchannel_id",
        "daily_budget",
        "images",
        "bodies",
        "titles",
        "descriptions",
        "call_to_action_types",
        "images_valid_amount",
        "titles_valid_amount",
        "bodies_valid_amount",
        "descriptions_valid_amount",
        "call_to_action_types_valid_amount",
        "images_max_amount",
        "titles_max_amount",
        "bodies_max_amount",
        "descriptions_max_amount",
        "call_to_action_types_max_amount",
        "unique_titles",
        "unique_bodies",
        "unique_descriptions",
        "daily_budget_valid",
        "min_daily_budget",
        "proposal_url",
        "proposal_url_valid",
        "proposal_locations",
        "locations",
        "locations_valid",
    }
)


ACCESS_TOKEN_BYTES = b"some-access-token"
ACCESS_TOKEN = "some-access-token"


def make_standard_link_data(**overrides):
    """Build a fresh STANDARD ``link_data`` dict.

    Defaults satisfy the five ``link_data``-level conditions of Requirement
    2.1 (``title_valid``, ``body_valid``, ``description_valid``,
    ``image_valid``, ``link_url_valid`` all exactly ``True``) plus the
    nested ``call_to_action['type']['valid'] is True``, so an invalidation
    matrix only has to override the single field under test.

    Pass ``call_to_action=ABSENT`` (or ``call_to_action=None``, or a
    non-dict value) to exercise the malformed-chain scenarios of
    Requirement 2.5/6.15.

    Requirements: 6.1
    """
    data = {
        "name": "Standard title",
        "message": "Standard body",
        "description": "Standard description",
        "image_url": "https://example.test/standard.jpg",
        "image_error": None,
        "link": "https://example.test/landing",
        "title_valid": True,
        "body_valid": True,
        "description_valid": True,
        "image_valid": True,
        "link_url_valid": True,
        "call_to_action": {"type": {"value": "SHOP_NOW", "valid": True}},
    }
    return _merge(data, overrides)


def make_standard_object_story_spec(**overrides):
    """Build a fresh STANDARD ``object_story_spec`` dict.

    ``link_data`` defaults to a fresh ``make_standard_link_data()`` and the
    two top-level conditions of Requirement 2.1 (``daily_budget_valid``,
    ``locations_valid``) default to exactly ``True``.

    Pass ``link_data=ABSENT``/``None``/a non-dict to exercise Requirement
    2.5, and ``object_story_spec=ABSENT`` on ``make_ad_creative`` for the
    fully-absent scenario of Requirement 6.5(a).

    Requirements: 6.1
    """
    data = {
        "page_id": "page-1",
        "ad_channel_id": 7,
        "daily_budget_valid": True,
        "min_daily_budget": 5,
        "locations": [{"key": "ES", "name": "Spain"}],
        "locations_valid": True,
        "link_data": make_standard_link_data(),
    }
    return _merge(data, overrides)


def make_dynamic_asset_feed_spec(**overrides):
    """Build a fresh DYNAMIC ``asset_feed_spec`` dict.

    Defaults satisfy every field the existing DYNAMIC branch of
    ``_is_campaign_valid`` requires to be truthy, and carry the annotation
    fields the DYNAMIC branch of ``_build_response`` reads, so the
    non-regression cases of Requirement 6.14 and the DYNAMIC rollback
    mirror of Requirement 6.13 can build on it.

    Requirements: 6.1
    """
    data = {
        "images": [
            {
                "url": "https://example.test/dynamic.jpg",
                "hash": "image-hash-1",
                "valid": True,
                "error": None,
            }
        ],
        "bodies": [{"text": "Dynamic body"}],
        "titles": [{"text": "Dynamic title"}],
        "descriptions": [{"text": "Dynamic description"}],
        "call_to_action_types": [{"value": "SHOP_NOW", "valid": True}],
        "link_urls": [{"website_url": "https://example.test/landing"}],
        "ad_formats": [],
        "ad_channel_id": 7,
        "unique_titles": True,
        "unique_bodies": True,
        "unique_descriptions": True,
        "link_url_valid": True,
        "locations": [{"key": "ES", "name": "Spain"}],
        "locations_valid": True,
        "daily_budget_valid": True,
        "min_daily_budget": 5,
        "images_valid_amount": True,
        "titles_valid_amount": True,
        "bodies_valid_amount": True,
        "descriptions_valid_amount": True,
        "call_to_action_types_valid_amount": True,
        "images_max_amount": 10,
        "titles_max_amount": 5,
        "bodies_max_amount": 5,
        "descriptions_max_amount": 5,
        "call_to_action_types_max_amount": 5,
    }
    return _merge(data, overrides)


def make_ad_creative(
    object_story_spec=ABSENT, asset_feed_spec=ABSENT, name="Ad creative", **overrides
):
    """Build a fresh ``adCreative`` dict.

    Both ``object_story_spec`` and ``asset_feed_spec`` default to the
    ``ABSENT`` sentinel, so the key is omitted unless the caller supplies
    it; pass ``object_story_spec=None`` explicitly to include the key with
    value ``None``.

    Requirements: 6.1
    """
    data = {
        "name": name,
        "object_story_spec": object_story_spec,
        "asset_feed_spec": asset_feed_spec,
    }
    return _merge(data, overrides)


def make_ad(ad_creative=ABSENT, ad_id="ad-1", **overrides):
    """Build a fresh ``ad`` dict (an element of ``ad_set['ads']``).

    ``ad_creative`` defaults to the ``ABSENT`` sentinel, so the
    ``adCreative`` key is omitted unless supplied; pass
    ``ad_creative=None`` explicitly to include it with value ``None``
    (Requirement 6.15).

    Requirements: 6.1
    """
    data = {
        "id": ad_id,
        "name": f"Ad {ad_id}",
        "status": "PAUSED",
        "adCreative": ad_creative,
    }
    return _merge(data, overrides)


def make_ad_set_to_publish(name="Ad set 1", adset_id="adset-1", ads=None, **overrides):
    """Build a fresh Ad_Set_a_Publicar dict (a ``channel_creative``, i.e. an
    element of the ``creatives_to_publish`` list built by ``execute()``).

    ``ads`` defaults to a brand new list holding a single fresh
    ``make_ad()``; pass ``ads=[]`` explicitly to exercise the
    empty-``ads`` guard of ``_is_campaign_valid``. Carries the ad set level
    fields ``_publish_adset`` reads so ``execute()`` scenarios can run with
    only the publishing helpers patched.

    Requirements: 6.1
    """
    data = {
        "name": name,
        "id": adset_id,
        "daily_budget": 100,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "LINK_CLICKS",
        "status": "PAUSED",
        "targeting": {"geo_locations": {"countries": ["ES"]}, "age_max": 65},
        "proposal_locations": [{"key": "ES", "name": "Spain"}],
        "ads": ads if ads is not None else [make_ad()],
    }
    return _merge(data, overrides)


def make_fully_valid_standard_ad_set(name="Ad set 1", adset_id="adset-1", **overrides):
    """Convenience builder: a fresh Ad_Set_a_Publicar whose single ad has the
    eight conditions of Requirement 2.1 all set to exactly ``True``.

    Base of the individual-invalidation matrix of Requirement 6.2: a test
    takes this ad set and flips exactly one of the eight annotations to
    absent/``None``/``False``.

    Requirements: 6.1
    """
    return make_ad_set_to_publish(
        name=name,
        adset_id=adset_id,
        ads=[
            make_ad(
                ad_creative=make_ad_creative(
                    object_story_spec=make_standard_object_story_spec()
                )
            )
        ],
        **overrides,
    )


def make_fully_valid_dynamic_ad_set(name="Ad set 1", adset_id="adset-1", **overrides):
    """Convenience builder mirroring ``make_fully_valid_standard_ad_set`` for
    the DYNAMIC branch: a fresh Ad_Set_a_Publicar whose single ad carries a
    complete ``asset_feed_spec``.

    Used by the DYNAMIC non-regression cases (Requirement 6.14) and by the
    DYNAMIC rollback mirror (Requirement 6.13).

    Requirements: 6.1
    """
    return make_ad_set_to_publish(
        name=name,
        adset_id=adset_id,
        ads=[
            make_ad(
                ad_creative=make_ad_creative(
                    asset_feed_spec=make_dynamic_asset_feed_spec()
                )
            )
        ],
        **overrides,
    )


def make_ad_channel(channel_ref_id=1, channel_creative=ABSENT, **overrides):
    """Build a fresh ``ad_channel`` dict as returned by
    ``AdChannelRepository.get_by_campaign_and_ad_channel_id``.

    ``channel_creative`` defaults to the ``ABSENT`` sentinel, so the key is
    omitted from ``attributes`` unless supplied. ``**overrides`` are merged
    into the top-level dict (not into ``attributes``), so callers can
    replace or omit ``attributes`` entirely.

    Requirements: 6.1
    """
    attributes = {
        "channel_ref": {"data": {"id": channel_ref_id}},
        "channel_creative": channel_creative,
    }
    data = {
        "id": "ad-channel-1",
        "attributes": _merge(attributes, {}),
    }
    return _merge(data, overrides)


def make_campaign_setup(
    meta_campaign_mode=CreativeType.STANDARD.value, setup_id=55, **overrides
):
    """Build a fresh ``campaign_setup`` dict as returned by
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``.

    ``meta_campaign_mode`` drives ``self.campaign_mode`` (assigned by
    ``_get_campaign_setup``), which is the sole dispatch key of both the
    ``_is_campaign_valid`` gate and the ``_build_response`` branch.
    ``**overrides`` are merged into the top-level dict.

    Requirements: 6.1
    """
    attributes = {
        "meta_account_id": "1234567890",
        "meta_campaign_mode": meta_campaign_mode,
        "meta_campaign_objective": "OUTCOME_TRAFFIC",
        "meta_optimization_goal": "LINK_CLICKS",
        "meta_lead_form_id": None,
        "meta_whatsapp_id": None,
        "meta_page_id": "page-1",
        "meta_pixel_id": None,
    }
    data = {"id": setup_id, "attributes": _merge(attributes, {})}
    return _merge(data, overrides)


def make_campaign(name="Campaign 1", **overrides):
    """Build a fresh ``campaign`` dict as returned by
    ``CampaignRepository.get_by_id``, from which ``_build_meta_campaign``
    reads ``attributes.name``.

    Requirements: 6.1
    """
    data = {"id": "campaign-1", "attributes": {"name": name}}
    return _merge(data, overrides)


def make_launch_data(campaign_id="campaign-1", creatives=None, **overrides):
    """Build a fresh ``data`` dict for the ``FacebookLaunchCampaignUseCase``
    constructor.

    ``creatives`` defaults to a brand new list holding one selector triple
    (``adset_id``/``ad_id``/``adchannel_id``), which is what ``execute()``
    resolves through ``_get_ad_channel``.

    Requirements: 6.1
    """
    data = {
        "brand_id": "brand-1",
        "campaign_id": campaign_id,
        "creatives": creatives
        if creatives is not None
        else [{"adset_id": "adset-1", "ad_id": "ad-1", "adchannel_id": "adchannel-1"}],
    }
    return _merge(data, overrides)


@pytest.fixture
def use_case_factory():
    """Fixture returning a factory of ``FacebookLaunchCampaignUseCase``
    instances with the **three** repository classes its constructor
    instantiates replaced by test doubles.

    Each call patches ``app.v2.use_cases.meta_ads.AdChannelRepository``,
    ``app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`` and
    ``app.v2.use_cases.meta_ads.CampaignRepository`` *before* constructing
    the use case, then returns::

        (use_case, mock_ad_channel_repo, mock_campaign_publish_repo, mock_campaign_repo)

    Every invocation produces a brand new use case and brand new mock
    repository instances; nothing is shared across calls. ``campaign_mode``
    can be set directly for tests that exercise ``_is_campaign_valid``/
    ``_build_response`` without going through ``_get_campaign_setup``.

    Requirements: 6.16
    """

    def _factory(user_id="user-1", data=None, campaign_mode=None):
        if data is None:
            data = make_launch_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignRepository"
        ) as mock_campaign_repository_cls:
            use_case = FacebookLaunchCampaignUseCase(user_id, data)
            mock_ad_channel_repo = mock_ad_channel_repository_cls.return_value
            mock_campaign_publish_repo = (
                mock_campaign_publish_repository_cls.return_value
            )
            mock_campaign_repo = mock_campaign_repository_cls.return_value

        if campaign_mode is not None:
            use_case.campaign_mode = campaign_mode

        return (
            use_case,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
            mock_campaign_repo,
        )

    return _factory


@contextmanager
def patch_redis_client(access_token=ACCESS_TOKEN_BYTES):
    """Context manager patching ``app.v2.use_cases.meta_ads.redis_client``
    and yielding the resulting ``MagicMock`` with
    ``.get.return_value = b"some-access-token"`` preconfigured, so
    ``_get_decoded_access_token`` returns ``"some-access-token"`` without
    touching Redis::

        with patch_redis_client() as mock_redis_client:
            ...

    Pass ``access_token=None`` to exercise the ``NotAccessException``
    short-circuit, or reconfigure ``.get`` on the yielded mock directly.

    Requirements: 6.16
    """
    with patch("app.v2.use_cases.meta_ads.redis_client") as mock_redis_client:
        mock_redis_client.get.return_value = access_token
        yield mock_redis_client


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Module-level ``autouse`` guard (not a global ``conftest.py`` fixture)
    that replaces ``requests.sessions.Session.request`` with a function
    raising ``AssertionError`` immediately.

    Safety net against any accidental leak towards the Meta Graph API: the
    publishing helpers are always patched with ``patch.object`` in this
    suite, so no test should ever reach the network. If one does, it fails
    loudly here instead of hitting a real endpoint.

    Requirements: 6.16
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr("requests.sessions.Session.request", _raise_on_network_access)


def assert_sinergia_exception(exc_info, expected_code, expected_text):
    """Assert that the ``SinergiaException`` captured by ``pytest.raises``
    carries exactly ``expected_code`` and ``expected_text``.

    Deliberately inspects ``exc_info.value.code``/``exc_info.value.text``
    and never ``str(exc_info.value)``: ``SinergiaException.__init__``
    forwards the ``args`` *tuple* to ``Exception.__init__`` instead of the
    unpacked ``text``, so ``str(exc)`` is always the literal ``"()"``.

    Requirements: 6.1
    """
    assert exc_info.value.code == expected_code, (
        f"expected exception code {expected_code!r}, got {exc_info.value.code!r}"
    )
    assert exc_info.value.text == expected_text, (
        f"expected exception text {expected_text!r}, got {exc_info.value.text!r}"
    )


def test_infrastructure_smoke(use_case_factory):
    """Smoke test for the infrastructure above: builders produce fresh,
    independent structures; the ``ABSENT`` sentinel omits keys while an
    explicit ``None`` keeps them; ``EXPECTED_KEYS`` holds the 31 keys of
    Requirement 3.2; the factory wires the three mocked repositories onto
    the instance; and ``patch_redis_client`` feeds
    ``_get_decoded_access_token`` without any Flask app/request context.

    Requirements: 6.1, 6.16
    """
    assert len(EXPECTED_KEYS) == 31

    first = make_fully_valid_standard_ad_set()
    second = make_fully_valid_standard_ad_set()
    assert first is not second
    assert first["ads"] is not second["ads"]
    assert first["ads"][0] is not second["ads"][0]

    first["ads"].append(make_ad(ad_id="ad-2"))
    assert len(second["ads"]) == 1

    link_data = first["ads"][0]["adCreative"]["object_story_spec"]["link_data"]
    assert link_data["title_valid"] is True
    assert link_data["call_to_action"]["type"]["valid"] is True

    assert "call_to_action" not in make_standard_link_data(call_to_action=ABSENT)
    assert make_standard_link_data(call_to_action=None)["call_to_action"] is None
    assert "adCreative" not in make_ad()
    assert make_ad(ad_creative=None)["adCreative"] is None

    use_case, ad_channel_repo, campaign_publish_repo, campaign_repo = use_case_factory()
    assert ad_channel_repo is use_case.ad_channel_repository
    assert campaign_publish_repo is use_case.campaign_publish_repository
    assert campaign_repo is use_case.campaign_repository

    with patch_redis_client() as mock_redis_client:
        assert use_case._get_decoded_access_token() == ACCESS_TOKEN
        mock_redis_client.get.assert_called_once_with(
            f"facebook_access_token:{use_case.user_id}"
        )

# The eight conditions of Requirement 2.1, expressed as
# ``(container, field)`` pairs where ``container`` names the dict of the
# ``object_story_spec`` -> ``link_data`` -> ``call_to_action['type']`` chain
# that holds the annotation:
#
# - ``link_data``:         title_valid, body_valid, description_valid,
#                          image_valid, link_url_valid
# - ``object_story_spec``: daily_budget_valid, locations_valid
# - ``cta_type``:          valid  (i.e. link_data.call_to_action.type.valid)
STANDARD_GATE_CONDITIONS = (
    ("link_data", "title_valid"),
    ("link_data", "body_valid"),
    ("link_data", "description_valid"),
    ("link_data", "image_valid"),
    ("link_data", "link_url_valid"),
    ("object_story_spec", "daily_budget_valid"),
    ("object_story_spec", "locations_valid"),
    ("cta_type", "valid"),
)


# The three invalidity variants Requirement 2.2 enumerates for every single
# condition: the key is absent, the key is present with value ``None``, and
# the key is present with value ``False``. ``ABSENT`` means "delete the key".
INVALID_VARIANTS = (
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param(False, id="false"),
)


def _condition_container(ad_set, container):
    """Return the live dict of ``ad_set`` that holds the annotation named by
    ``container`` (``"link_data"``, ``"object_story_spec"`` or
    ``"cta_type"``), so a test can mutate exactly one condition in place.

    Indexes with ``[...]`` on purpose: the chain is fully populated by
    ``make_fully_valid_standard_ad_set()``, so a ``KeyError`` here would
    mean the builder drifted, which is worth failing on loudly rather than
    silently mutating a throw-away dict.

    Requirements: 6.2
    """
    object_story_spec = ad_set["ads"][0]["adCreative"]["object_story_spec"]

    if container == "object_story_spec":
        return object_story_spec

    link_data = object_story_spec["link_data"]

    if container == "link_data":
        return link_data

    assert container == "cta_type", f"unknown container {container!r}"
    return link_data["call_to_action"]["type"]


def _invalidate(ad_set, container, field, variant):
    """Apply a single invalidity ``variant`` to ``container[field]`` of
    ``ad_set``, leaving the other seven conditions of Requirement 2.1
    untouched at exactly ``True``.

    Requirements: 6.2
    """
    target = _condition_container(ad_set, container)

    assert target[field] is True, (
        f"builder drift: {container}.{field} should start as True, "
        f"got {target[field]!r}"
    )

    if variant is ABSENT:
        del target[field]
    else:
        target[field] = variant

    return ad_set


# Malformed ``adCreative`` chains of Requirement 2.5/6.15. Every entry is a
# zero-argument factory returning a fresh ``ad`` dict whose
# ``adCreative`` -> ``object_story_spec`` -> ``link_data`` -> ``call_to_action``
# chain is broken at exactly one link, either because the key is absent, or
# because it is present with the value ``None``, or because it is present with
# a truthy value of a type other than ``dict`` (the case ``or {}`` alone does
# not cover and which forces the ``isinstance(..., dict)`` guard).
#
# Every other annotation of the chain stays at exactly ``True``, so a `False`
# result can only come from the broken link and never from an unrelated
# invalid condition.
MALFORMED_CHAIN_CASES = (
    pytest.param(lambda: make_ad(), id="ad_creative_absent"),
    pytest.param(lambda: make_ad(ad_creative=None), id="ad_creative_none"),
    pytest.param(
        lambda: make_ad(ad_creative=make_ad_creative()),
        id="object_story_spec_absent",
    ),
    pytest.param(
        lambda: make_ad(ad_creative=make_ad_creative(object_story_spec=None)),
        id="object_story_spec_none",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(object_story_spec=["object_story_spec"])
        ),
        id="object_story_spec_not_dict",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(link_data=ABSENT)
            )
        ),
        id="link_data_absent",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(link_data=None)
            )
        ),
        id="link_data_none",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(
                    link_data="link_data"
                )
            )
        ),
        id="link_data_not_dict",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(
                    link_data=make_standard_link_data(call_to_action=ABSENT)
                )
            )
        ),
        id="call_to_action_absent",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(
                    link_data=make_standard_link_data(call_to_action=None)
                )
            )
        ),
        id="call_to_action_none",
    ),
    pytest.param(
        lambda: make_ad(
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec(
                    link_data=make_standard_link_data(call_to_action="SHOP_NOW")
                )
            )
        ),
        id="call_to_action_not_dict",
    ),
)


class TestIsCampaignValidStandard:
    """Behaviour of the STANDARD branch of
    ``FacebookLaunchCampaignUseCase._is_campaign_valid`` (Requirement 2).
    """

    @pytest.mark.parametrize("container,field", STANDARD_GATE_CONDITIONS)
    @pytest.mark.parametrize("variant", INVALID_VARIANTS)
    def test_single_false_condition_invalidates(
        self, use_case_factory, container, field, variant
    ):
        """Each of the eight conditions of Requirement 2.1, invalidated on
        its own while the other seven stay at exactly ``True``, makes
        ``_is_campaign_valid`` return ``False``.

        The matrix is 8 conditions x 3 invalidity variants (key absent, key
        present with ``None``, key present with ``False``) = 24 cases, which
        is what pins the strict ``is not True`` comparison of the
        implementation: a looser truthiness check would still reject
        ``None``/``False`` but would silently accept a missing key in some
        rewrites, and a plain ``not ...`` check would not distinguish
        ``True`` from other truthy values.

        Requirements: 6.2
        """
        use_case, _, _, _ = use_case_factory(
            campaign_mode=CreativeType.STANDARD.value
        )
        ad_set = _invalidate(
            make_fully_valid_standard_ad_set(), container, field, variant
        )

        assert use_case._is_campaign_valid([ad_set]) is False

    def test_all_eight_conditions_true_returns_true(self, use_case_factory):
        """Two Ad_Set_a_Publicar whose ads carry the eight conditions of
        Requirement 2.1 at exactly ``True`` simultaneously make
        ``_is_campaign_valid`` return ``True``.

        The second ad set deliberately holds two ads, so the positive case
        exercises the full nested iteration (every ad of every ad set) and
        not just the single-ad happy path.

        Requirements: 6.3
        """
        use_case, _, _, _ = use_case_factory(
            campaign_mode=CreativeType.STANDARD.value
        )

        first_ad_set = make_fully_valid_standard_ad_set(
            name="Ad set 1", adset_id="adset-1"
        )
        second_ad_set = make_fully_valid_standard_ad_set(
            name="Ad set 2", adset_id="adset-2"
        )
        second_ad_set["ads"].append(
            make_ad(
                ad_id="ad-2",
                ad_creative=make_ad_creative(
                    object_story_spec=make_standard_object_story_spec()
                ),
            )
        )

        creatives_to_publish = [first_ad_set, second_ad_set]

        # Guard against builder drift: the eight conditions must really be
        # `True` on every ad before the gate is exercised, otherwise the
        # assertion below would pass (or fail) for the wrong reason.
        for ad_set in creatives_to_publish:
            for ad in ad_set["ads"]:
                object_story_spec = ad["adCreative"]["object_story_spec"]
                link_data = object_story_spec["link_data"]
                cta_type = link_data["call_to_action"]["type"]

                for container, field in STANDARD_GATE_CONDITIONS:
                    source = {
                        "link_data": link_data,
                        "object_story_spec": object_story_spec,
                        "cta_type": cta_type,
                    }[container]
                    assert source[field] is True, (
                        f"builder drift: {container}.{field} should be True, "
                        f"got {source[field]!r}"
                    )

        assert use_case._is_campaign_valid(creatives_to_publish) is True

    @pytest.mark.parametrize("make_malformed_ad", MALFORMED_CHAIN_CASES)
    def test_malformed_ad_creative_chain(self, use_case_factory, make_malformed_ad):
        """A STANDARD ad whose ``adCreative`` chain is broken at any single
        link is treated as non launchable: ``_is_campaign_valid`` returns
        ``False`` and never lets an unhandled exception escape.

        The matrix covers the whole chain of Requirement 2.5 -- ``adCreative``,
        ``object_story_spec``, ``link_data``, ``call_to_action`` -- with the
        key absent, the key present with ``None``, and (for the three
        dict-valued links) the key present with a truthy value of a type
        other than ``dict``. The last variant is the one that pins the
        ``isinstance(..., dict)`` guards: ``or {}`` alone would leave a
        string or a list in place and the subsequent ``.get`` would raise
        ``AttributeError``.

        No ``pytest.raises`` wrapper is needed for the "without raising"
        half of the criterion: any exception escaping ``_is_campaign_valid``
        propagates out of the test body and fails the case outright, which
        is exactly what distinguishes a normalized ``False`` from a crash.

        Requirements: 6.15
        """
        use_case, _, _, _ = use_case_factory(
            campaign_mode=CreativeType.STANDARD.value
        )
        ad_set = make_ad_set_to_publish(ads=[make_malformed_ad()])

        assert use_case._is_campaign_valid([ad_set]) is False


# The documented default of every Creative_Publicado key that is *derived
# from* `object_story_spec`/`link_data`/`call_to_action` (Requirement 3.3 and
# the "Valor cuando el dato está ausente" column of the mapping table in
# `design.md`): `[]` for lists, `False` for validity booleans, `0`/`''` for
# scalars.
#
# Deliberately excludes the six structural keys (`idx`, `name`, `adset_id`,
# `ad_id`, `daily_budget`, `proposal_locations`), which come from the ad set /
# ad and not from `object_story_spec`, and the five `*_max_amount` keys, which
# are constants of the STANDARD branch. 20 + 6 + 5 = the 31 keys of
# Requirement 3.2.
DOCUMENTED_DEFAULTS = {
    "adchannel_id": 0,
    "images": [],
    "bodies": [],
    "titles": [],
    "descriptions": [],
    "call_to_action_types": [],
    "images_valid_amount": False,
    "titles_valid_amount": False,
    "bodies_valid_amount": False,
    "descriptions_valid_amount": False,
    "call_to_action_types_valid_amount": False,
    "unique_titles": False,
    "unique_bodies": False,
    "unique_descriptions": False,
    "daily_budget_valid": False,
    "min_daily_budget": 0,
    "proposal_url": "",
    "proposal_url_valid": False,
    "locations": [],
    "locations_valid": False,
}


# The five constants of the STANDARD branch: `1`, not `0` (a STANDARD creative
# takes exactly one asset per field). See the corresponding design note.
MAX_AMOUNT_KEYS = (
    "images_max_amount",
    "titles_max_amount",
    "bodies_max_amount",
    "descriptions_max_amount",
    "call_to_action_types_max_amount",
)


# Keys sourced from `link_data` (including the CTA ones, which live nested
# inside it), from `object_story_spec` itself, and from `call_to_action`.
LINK_DATA_DERIVED_KEYS = frozenset(
    {
        "images",
        "bodies",
        "titles",
        "descriptions",
        "call_to_action_types",
        "images_valid_amount",
        "titles_valid_amount",
        "bodies_valid_amount",
        "descriptions_valid_amount",
        "call_to_action_types_valid_amount",
        "unique_titles",
        "unique_bodies",
        "unique_descriptions",
        "proposal_url",
        "proposal_url_valid",
    }
)

OBJECT_STORY_SPEC_DERIVED_KEYS = frozenset(
    {
        "adchannel_id",
        "daily_budget_valid",
        "min_daily_budget",
        "locations",
        "locations_valid",
    }
)

CALL_TO_ACTION_DERIVED_KEYS = frozenset(
    {"call_to_action_types", "call_to_action_types_valid_amount"}
)


# The three scenarios of Requirement 6.5. Each entry pairs a zero-argument
# factory returning a fresh Ad_Set_a_Publicar with the exact set of
# data-derived keys expected to fall back to their documented default; every
# other key of `DOCUMENTED_DEFAULTS` must keep carrying real input data.
ABSENT_DATA_CASES = (
    pytest.param(
        lambda: make_ad_set_to_publish(ads=[make_ad(ad_creative=make_ad_creative())]),
        LINK_DATA_DERIVED_KEYS | OBJECT_STORY_SPEC_DERIVED_KEYS,
        id="object_story_spec_absent",
    ),
    pytest.param(
        lambda: make_ad_set_to_publish(
            ads=[
                make_ad(
                    ad_creative=make_ad_creative(
                        object_story_spec=make_standard_object_story_spec(
                            link_data=ABSENT
                        )
                    )
                )
            ]
        ),
        LINK_DATA_DERIVED_KEYS,
        id="link_data_absent",
    ),
    pytest.param(
        lambda: make_ad_set_to_publish(
            ads=[
                make_ad(
                    ad_creative=make_ad_creative(
                        object_story_spec=make_standard_object_story_spec(
                            link_data=make_standard_link_data(call_to_action=ABSENT)
                        )
                    )
                )
            ]
        ),
        CALL_TO_ACTION_DERIVED_KEYS,
        id="call_to_action_absent",
    ),
)


def _assert_documented_default(entry, key):
    """Assert that ``entry[key]`` holds exactly the documented default of
    ``key``, discriminating by the default's type so that Python's
    ``False == 0`` equivalence cannot let one stand in for the other.

    - list default: compared with ``== []`` plus an exact ``list`` type check;
    - boolean default: compared with ``is False``;
    - numeric default: compared with ``== 0`` and rejected if it is a ``bool``;
    - string default: compared with ``== ''`` plus an exact ``str`` type check.

    Requirements: 6.5
    """
    expected = DOCUMENTED_DEFAULTS[key]
    actual = entry[key]

    if isinstance(expected, list):
        assert isinstance(actual, list), f"{key} should be a list, got {actual!r}"
        assert actual == [], f"{key} should default to [], got {actual!r}"
    elif isinstance(expected, bool):
        assert actual is False, f"{key} should default to False, got {actual!r}"
    elif isinstance(expected, int):
        assert not isinstance(actual, bool), (
            f"{key} should default to the number 0, got the boolean {actual!r}"
        )
        assert actual == 0, f"{key} should default to 0, got {actual!r}"
    else:
        assert isinstance(actual, str), f"{key} should be a str, got {actual!r}"
        assert actual == "", f"{key} should default to '', got {actual!r}"


class TestBuildResponseStandard:
    """Behaviour of the STANDARD branch of
    ``FacebookLaunchCampaignUseCase._build_response`` and of the
    ``_build_standard_creative_published`` constructor it dispatches to
    (Requirement 3).
    """

    def test_full_object_story_spec_maps_every_field(self, use_case_factory):
        """A fully populated STANDARD Ad_Set_a_Publicar produces a
        Creative_Publicado holding *exactly* the 31 fixed keys of
        Requirement 3.2, each one equal to the input value the mapping table
        of ``design.md`` ("Mapeo exacto fuente->campo del Creative_Publicado
        STANDARD") assigns to it.

        The key check is an exact set equality against ``EXPECTED_KEYS``,
        never a subset comparison: a subset check would pass both if the
        branch dropped a key and if it emitted an extra one (for instance
        ``promoted_object_valid``, which ``_build_standard_creative_entry``
        does emit and which this branch deliberately must not), and key
        parity with the DYNAMIC entry is precisely what Requirement 3.2
        demands.

        Every value assertion reads the expected value back from the fixture
        structure instead of repeating a literal, so the test pins the
        *mapping* (source expression -> target key) rather than the specific
        sample data. Booleans are compared with ``is`` so a truthy stand-in
        cannot pass for ``True``.

        Requirements: 6.4
        """
        use_case, _, _, _ = use_case_factory(
            campaign_mode=CreativeType.STANDARD.value
        )

        ad_set_published = make_fully_valid_standard_ad_set(
            name="Ad set 1", adset_id="adset-1"
        )
        ad_published = ad_set_published["ads"][0]
        object_story_spec = ad_published["adCreative"]["object_story_spec"]
        link_data = object_story_spec["link_data"]
        call_to_action = link_data["call_to_action"]

        response = use_case._build_response(
            "meta-campaign-1", make_campaign()["attributes"], [ad_set_published]
        )

        # Requirement 3.1: exactly one entry per Ad_Set_a_Publicar.
        assert len(response["creatives"]) == 1
        entry = response["creatives"][0]

        # Requirement 3.2: the fixed key set, compared exactly.
        assert set(entry.keys()) == EXPECTED_KEYS
        assert len(entry) == 31

        # 1-6: identity/ad-set level fields.
        assert entry["idx"] == 0
        assert entry["name"] == ad_set_published["name"]
        assert entry["adset_id"] == ad_set_published["id"]
        assert entry["ad_id"] == ad_published["id"]
        assert entry["adchannel_id"] == object_story_spec["ad_channel_id"]
        assert entry["daily_budget"] == ad_set_published["daily_budget"]

        # 7-11: the five single-item asset lists.
        assert entry["images"] == [
            {
                "url": link_data["image_url"],
                "valid": link_data["image_valid"],
                "error": link_data["image_error"],
            }
        ]
        assert entry["bodies"] == [
            {"text": link_data["message"], "valid_length": link_data["body_valid"]}
        ]
        assert entry["titles"] == [
            {"text": link_data["name"], "valid_length": link_data["title_valid"]}
        ]
        assert entry["descriptions"] == [
            {
                "text": link_data["description"],
                "valid_length": link_data["description_valid"],
            }
        ]
        assert entry["call_to_action_types"] == [call_to_action["type"]]

        # 12-16: the five validity flags.
        assert entry["images_valid_amount"] is link_data["image_valid"]
        assert entry["titles_valid_amount"] is link_data["title_valid"]
        assert entry["bodies_valid_amount"] is link_data["body_valid"]
        assert entry["descriptions_valid_amount"] is link_data["description_valid"]
        assert entry["call_to_action_types_valid_amount"] is call_to_action["type"][
            "valid"
        ]

        # 17-21: the five `*_max_amount` constants, which are `1` and not `0`
        # for a STANDARD creative (exactly one asset per field).
        assert entry["images_max_amount"] == 1
        assert entry["titles_max_amount"] == 1
        assert entry["bodies_max_amount"] == 1
        assert entry["descriptions_max_amount"] == 1
        assert entry["call_to_action_types_max_amount"] == 1

        # 22-24: `unique_*` are aliases of the corresponding `*_valid`
        # annotations, there being at most one value per text field.
        assert entry["unique_titles"] is link_data["title_valid"]
        assert entry["unique_bodies"] is link_data["body_valid"]
        assert entry["unique_descriptions"] is link_data["description_valid"]

        # 25-31: budget, proposal URL and locations.
        assert entry["daily_budget_valid"] is object_story_spec["daily_budget_valid"]
        assert entry["min_daily_budget"] == object_story_spec["min_daily_budget"]
        assert entry["proposal_url"] == link_data["link"]
        assert entry["proposal_url_valid"] is link_data["link_url_valid"]
        assert entry["proposal_locations"] == ad_set_published["proposal_locations"]
        assert entry["locations"] == object_story_spec["locations"]
        assert entry["locations_valid"] is object_story_spec["locations_valid"]
    @pytest.mark.parametrize(
        "make_ad_set,defaulted_keys", ABSENT_DATA_CASES
    )
    def test_absent_data_uses_documented_defaults(
        self, use_case_factory, make_ad_set, defaulted_keys
    ):
        """A STANDARD Ad_Set_a_Publicar whose ``object_story_spec`` chain is
        incomplete still yields a Creative_Publicado: no exception escapes,
        the 31 fixed keys of Requirement 3.2 are all present, and every key
        derived from the missing data carries the default documented in the
        mapping table of ``design.md``.

        Three scenarios (Requirement 6.5): (a) ``object_story_spec``
        completely absent, (b) ``object_story_spec`` present but
        ``link_data`` absent, (c) ``link_data`` present but
        ``call_to_action`` absent. Each declares the exact subset of
        data-derived keys that must fall back to a default, and the test
        asserts the complement did *not* fall back, so a scenario cannot
        pass by defaulting more than it should: the whole point of (b) and
        (c) is that the surviving levels of the chain keep feeding real
        values while only the missing level defaults.

        The five ``*_max_amount`` keys are checked as the constant ``1``, not
        ``0``: they are constants of the STANDARD branch (a STANDARD creative
        takes exactly one asset per field), not values derived from
        ``object_story_spec``, so the ``0``/``''`` defaults of Requirement
        3.3 do not apply to them. ``design.md`` calls this out explicitly so
        that this very verification does not read it as a deviation.

        Requirements: 6.5
        """
        use_case, _, _, _ = use_case_factory(
            campaign_mode=CreativeType.STANDARD.value
        )

        ad_set_published = make_ad_set()
        ad_published = ad_set_published["ads"][0]

        # Requirement 3.3: the call must not raise. Any exception escaping
        # here propagates out of the test body and fails the case, which is
        # exactly the "no unhandled exception" half of the criterion.
        response = use_case._build_response(
            "meta-campaign-1", make_campaign()["attributes"], [ad_set_published]
        )

        assert len(response["creatives"]) == 1
        entry = response["creatives"][0]

        # Requirement 3.2: the fixed key set survives incomplete input,
        # compared exactly and never by subset.
        assert set(entry.keys()) == EXPECTED_KEYS
        assert len(entry) == 31

        # The six structural keys never depend on `object_story_spec`, so
        # they keep reporting the real ad set / ad they came from.
        assert entry["idx"] == 0
        assert entry["name"] == ad_set_published["name"]
        assert entry["adset_id"] == ad_set_published["id"]
        assert entry["ad_id"] == ad_published["id"]
        assert entry["daily_budget"] == ad_set_published["daily_budget"]
        assert entry["proposal_locations"] == ad_set_published["proposal_locations"]

        # The five `*_max_amount` constants stay at `1` in every scenario.
        for key in MAX_AMOUNT_KEYS:
            assert entry[key] == 1, (
                f"{key} should be the STANDARD constant 1, got {entry[key]!r}"
            )

        # Keys derived from the missing level fall back to their documented
        # default (`[]` for lists, `False` for validity booleans, `0`/`''`
        # for scalars).
        for key in sorted(defaulted_keys):
            _assert_documented_default(entry, key)

        # Keys derived from a level that is still present must NOT have
        # fallen back: every builder default differs from the documented
        # default, so an equal value here means the branch over-defaulted.
        for key in sorted(set(DOCUMENTED_DEFAULTS) - defaulted_keys):
            assert entry[key] != DOCUMENTED_DEFAULTS[key], (
                f"{key} was derived from data that is present, so it should "
                f"not equal its default {DOCUMENTED_DEFAULTS[key]!r}"
            )


# ---------------------------------------------------------------------------
# Shared infrastructure for the end-to-end `execute()` scenarios
# (rollback, Meta auth classification, DYNAMIC parity).
#
# `execute()` needs four collaborators resolved before it reaches the
# publishing loop (`_get_decoded_access_token`, `_get_campaign`,
# `_get_ad_channel`, `_get_campaign_setup`) and then talks to the Graph API
# through five helpers (`_publish_campaign`, `_publish_adset`,
# `_publish_media`, `_publish_ad_creative`, `_publish_ad`). `launch_scenario`
# below wires the first group onto the three mocked repositories and replaces
# the second group (plus `_delete_object` and `_update_campaign_setup`) with
# `patch.object` doubles, so a test only has to declare *which* helper fails
# and *how*.
#
# `_rollback_publish` is deliberately NOT patched: the scenarios patch
# `_delete_object` instead, so the real rollback routine runs and its
# deletion order is what gets observed (Requirements 5.1, 6.6c).
# ---------------------------------------------------------------------------

# Fixed id the default `_publish_campaign` double returns; the id
# `_rollback_publish` must delete first.
META_CAMPAIGN_ID = "meta-campaign-100"


class LaunchScenario:
    """Wiring returned by :func:`launch_scenario`.

    Exposes the use case under test, the three mocked repositories, the seven
    patched method doubles, and the ids the doubles handed out, so a test can
    assert against the exact objects that were really created:

    - ``meta_campaign_id``: the campaign id ``_publish_campaign`` returned;
    - ``created_ad_creative_ids``: the ad creative ids ``_publish_ad_creative``
      actually handed out, in order, i.e. exactly the list ``execute()``
      accumulated in ``created_ad_creative_ids`` before the failure. Anything
      the scenario never created is absent from it, which is what makes the
      "no more, no less" deletion count of Requirement 6.6b verifiable.

    Requirements: 6.6
    """

    def __init__(self, use_case, repositories, mocks, created_ad_creative_ids,
                 published_adset_ids):
        self.use_case = use_case
        (
            self.ad_channel_repository,
            self.campaign_publish_repository,
            self.campaign_repository,
        ) = repositories
        self.mocks = mocks
        self.created_ad_creative_ids = created_ad_creative_ids
        self.published_adset_ids = published_adset_ids
        self.meta_campaign_id = META_CAMPAIGN_ID

    @property
    def mock_delete_object(self):
        return self.mocks["_delete_object"]

    @property
    def mock_update_campaign_setup(self):
        return self.mocks["_update_campaign_setup"]

    def expected_delete_calls(self):
        """The ``_delete_object`` call list a full rollback must produce: the
        campaign first (its ad sets and ads cascade in Meta), then every ad
        creative that was really created, each exactly once.

        Requirements: 6.6
        """
        return [call(self.meta_campaign_id, ACCESS_TOKEN)] + [
            call(ad_creative_id, ACCESS_TOKEN)
            for ad_creative_id in self.created_ad_creative_ids
        ]


@contextmanager
def launch_scenario(
    use_case_factory,
    ad_sets=None,
    campaign_mode=CreativeType.STANDARD.value,
    side_effects=None,
):
    """Context manager yielding a :class:`LaunchScenario` ready to run
    ``execute()`` without touching Strapi, Redis or the Graph API.

    ``ad_sets`` is the list of Ad_Set_a_Publicar the repositories will serve
    (one ``channel_creative`` per entry of ``data['creatives']``, which is
    how ``execute()`` builds ``creatives_to_publish``); it defaults to a
    single fully valid STANDARD ad set.

    ``side_effects`` maps a method name of the use case to the ``side_effect``
    its double should carry, and overrides the defaults below. Any method name
    is accepted, not just the publishing helpers, so a test can also make
    ``_get_campaign``/``_get_ad_channel``/``_get_campaign_setup`` fail.

    Defaults:

    - ``_publish_campaign`` returns ``META_CAMPAIGN_ID``;
    - ``_publish_adset``/``_publish_ad`` return fresh sequential ids;
    - ``_publish_media`` is a no-op;
    - ``_publish_ad_creative`` returns fresh sequential ids and records them;
    - ``_delete_object``/``_update_campaign_setup`` are no-ops recording calls.

    Requirements: 6.6
    """
    if ad_sets is None:
        ad_sets = [make_fully_valid_standard_ad_set()]

    creatives = [
        {
            "adset_id": ad_set.get("id"),
            "ad_id": ad_set.get("ads")[0].get("id"),
            "adchannel_id": f"adchannel-{index + 1}",
        }
        for index, ad_set in enumerate(ad_sets)
    ]

    use_case, ad_channel_repo, campaign_publish_repo, campaign_repo = use_case_factory(
        data=make_launch_data(creatives=creatives)
    )

    # `_get_ad_channel` is called once per selector, in order, and each call
    # must yield the matching Ad_Set_a_Publicar as its `channel_creative`.
    ad_channel_repo.get_by_campaign_and_ad_channel_id.side_effect = [
        make_ad_channel(channel_creative=ad_set) for ad_set in ad_sets
    ]
    campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
        make_campaign_setup(meta_campaign_mode=campaign_mode)
    )
    campaign_repo.get_by_id.return_value = make_campaign()

    created_ad_creative_ids = []
    published_adset_ids = []
    adset_counter = itertools.count(1)
    ad_creative_counter = itertools.count(1)
    ad_counter = itertools.count(1)

    def _publish_adset(adset, access_token):
        meta_adset_id = f"meta-adset-{next(adset_counter)}"
        published_adset_ids.append(meta_adset_id)
        return meta_adset_id

    def _publish_ad_creative(ad, access_token):
        ad_creative_id = f"meta-adcreative-{next(ad_creative_counter)}"
        created_ad_creative_ids.append(ad_creative_id)
        return ad_creative_id

    def _publish_ad(ad, access_token):
        return f"meta-ad-{next(ad_counter)}"

    doubles = {
        "_publish_campaign": lambda meta_campaign: META_CAMPAIGN_ID,
        "_publish_adset": _publish_adset,
        "_publish_media": lambda ad, access_token: None,
        "_publish_ad_creative": _publish_ad_creative,
        "_publish_ad": _publish_ad,
        "_delete_object": lambda object_id, access_token: None,
        "_update_campaign_setup": lambda *args, **kwargs: None,
    }
    doubles.update(side_effects or {})

    mocks = {}
    with ExitStack() as stack:
        for name, side_effect in doubles.items():
            mocks[name] = stack.enter_context(
                patch.object(use_case, name, side_effect=side_effect)
            )
        stack.enter_context(patch_redis_client())

        yield LaunchScenario(
            use_case,
            (ad_channel_repo, campaign_publish_repo, campaign_repo),
            mocks,
            created_ad_creative_ids,
            published_adset_ids,
        )


class TestRollbackOnPartialFailure:
    """Behaviour of the Rollback_de_Lanzamiento when ``execute()`` fails after
    the Meta campaign already exists (Requirement 5).
    """

    def test_rest_client_exception_after_creatives_triggers_full_rollback(
        self, use_case_factory
    ):
        """A non-authentication ``RESTClientException`` raised by
        ``_publish_ad`` after ``_publish_campaign`` succeeded and at least one
        ad creative was created rolls the whole launch back and re-raises the
        original exception untouched.

        The fixture holds one ad set with three ads and ``_publish_ad``
        succeeds once and then raises, so at the moment of failure exactly two
        ad creatives exist and the third one was never created. That is what
        makes the count assertions meaningful: a rollback that deleted the
        creatives of the whole fixture (three) or that skipped one (one) would
        both fail here, while a single-ad fixture could not tell the
        difference.

        ``_delete_object`` is patched instead of ``_rollback_publish`` on
        purpose (Requirements 5.1, 6.6c): the real rollback routine runs, so
        its deletion order -- campaign first, because deleting it cascades to
        its ad sets and ads in Meta, and only then the orphaned ad creatives --
        is what the ``call_args_list`` assertion observes.

        Requirements: 6.6
        """
        publish_error = RESTClientException({"error": {"code": 100}})

        ad_set = make_fully_valid_standard_ad_set(name="Ad set 1", adset_id="adset-1")
        ad_set["ads"] = [
            make_ad(
                ad_id=f"ad-{index}",
                ad_creative=make_ad_creative(
                    object_story_spec=make_standard_object_story_spec()
                ),
            )
            for index in (1, 2, 3)
        ]

        with launch_scenario(
            use_case_factory,
            ad_sets=[ad_set],
            side_effects={"_publish_ad": ["meta-ad-1", publish_error]},
        ) as scenario:
            with pytest.raises(RESTClientException) as exc_info:
                scenario.use_case.execute()

            # (d) The original exception reaches the caller unchanged: same
            # object, not a copy and not a re-wrapped equivalent. Identity is
            # the only comparison that rules out a re-raise that rebuilt the
            # exception (`RESTClientException` carries no `__eq__`, so an
            # equality check would silently degrade to identity anyway).
            assert exc_info.value is publish_error
            assert exc_info.value.text == {"error": {"code": 100}}

            # Precondition of the scenario: the failure really happened after
            # the campaign existed and after some -- but not all -- ad
            # creatives had been created.
            assert scenario.created_ad_creative_ids == [
                "meta-adcreative-1",
                "meta-adcreative-2",
            ]

            delete_calls = scenario.mock_delete_object.call_args_list

            # (a) + (b): the campaign exactly once, and each created ad
            # creative exactly once -- no more, no less. The exact list
            # equality covers the count, the arguments and the order in one
            # assertion; the per-id counts below pin down *which* half broke
            # when it does not hold.
            assert delete_calls == scenario.expected_delete_calls()
            assert scenario.mock_delete_object.call_count == 3

            deleted_ids = [
                delete_call.args[0] for delete_call in delete_calls
            ]
            assert deleted_ids.count(scenario.meta_campaign_id) == 1
            for ad_creative_id in scenario.created_ad_creative_ids:
                assert deleted_ids.count(ad_creative_id) == 1

            # The ad creative that was never created is never deleted either.
            assert "meta-adcreative-3" not in deleted_ids

            # (c) Campaign before creatives: deleting the campaign cascades to
            # its ad sets and ads, so it has to come first.
            campaign_index = deleted_ids.index(scenario.meta_campaign_id)
            creative_indexes = [
                deleted_ids.index(ad_creative_id)
                for ad_creative_id in scenario.created_ad_creative_ids
            ]
            assert campaign_index == 0
            assert campaign_index < min(creative_indexes)

            # (e) A failed launch never marks the campaign as published.
            scenario.mock_update_campaign_setup.assert_not_called()

    def test_key_error_without_text_attribute(self, use_case_factory):
        """A plain Python exception with no ``text`` attribute -- the
        ``KeyError`` ``_publish_media`` can still raise per Requirement 4.3 --
        rolls the whole launch back and reaches the caller as itself.

        This is the regression this spec exists for: the previous handler read
        ``e.text`` unguarded, so a ``KeyError`` turned into an ``AttributeError``
        *inside* the handler, which masked the original error and skipped
        ``_rollback_publish`` entirely, leaving orphan objects in Meta.

        ``execute()`` publishes each ad as ``_publish_media`` ->
        ``_publish_ad_creative`` -> ``_publish_ad``, so a failure in
        ``_publish_media`` happens *before* that ad's own creative exists. The
        fixture therefore holds one ad set with three ads and ``_publish_media``
        succeeds twice before raising: at the moment of failure exactly two ad
        creatives exist (those of the first two ads) and the third one was never
        created, which is what makes "each ad creative already created" a
        meaningful count rather than a vacuous one.

        ``_delete_object`` is patched instead of ``_rollback_publish``
        (Requirements 5.1, 6.6c), so the real rollback routine runs.

        Requirements: 6.8
        """
        media_error = KeyError("link_data")

        # Precondition of the whole scenario: the exception carries no `text`
        # attribute at all, which is exactly the shape that used to break the
        # handler.
        assert not hasattr(media_error, "text")

        ad_set = make_fully_valid_standard_ad_set(name="Ad set 1", adset_id="adset-1")
        ad_set["ads"] = [
            make_ad(
                ad_id=f"ad-{index}",
                ad_creative=make_ad_creative(
                    object_story_spec=make_standard_object_story_spec()
                ),
            )
            for index in (1, 2, 3)
        ]

        with launch_scenario(
            use_case_factory,
            ad_sets=[ad_set],
            side_effects={"_publish_media": [None, None, media_error]},
        ) as scenario:
            with pytest.raises(KeyError) as exc_info:
                scenario.use_case.execute()

            # (b) The propagated exception is the original `KeyError` itself --
            # same object, not a copy and not a re-wrapped equivalent -- and
            # emphatically not the `AttributeError` the old handler produced
            # while classifying it.
            assert exc_info.value is media_error
            assert not isinstance(exc_info.value, AttributeError)
            assert exc_info.value.args == ("link_data",)

            # Precondition of the scenario: the failure really happened after
            # the campaign existed and after some -- but not all -- ad
            # creatives had been created.
            assert scenario.mocks["_publish_campaign"].call_count == 1
            assert scenario.created_ad_creative_ids == [
                "meta-adcreative-1",
                "meta-adcreative-2",
            ]

            delete_calls = scenario.mock_delete_object.call_args_list

            # (a) Full rollback: the campaign first (deleting it cascades to
            # its ad sets and ads in Meta), then each ad creative that was
            # really created, each exactly once -- no more, no less.
            assert delete_calls == scenario.expected_delete_calls()
            assert scenario.mock_delete_object.call_count == 3

            deleted_ids = [delete_call.args[0] for delete_call in delete_calls]
            assert deleted_ids.count(scenario.meta_campaign_id) == 1
            for ad_creative_id in scenario.created_ad_creative_ids:
                assert deleted_ids.count(ad_creative_id) == 1

            # The third ad's creative was never created, so it is never
            # deleted either.
            assert "meta-adcreative-3" not in deleted_ids

            # (c) A failed launch never marks the campaign as published.
            scenario.mock_update_campaign_setup.assert_not_called()

    def test_delete_object_failure_does_not_mask_original(self, use_case_factory):
        """A rollback that itself blows up never replaces the exception the
        caller sees: ``execute()`` still propagates the original publishing
        failure, not the rollback one.

        The real ``_delete_object`` already swallows every deletion error
        internally (Requirement 5.13), so this scenario is deliberately
        *harsher* than production: the double raises straight out of
        ``_delete_object``, which propagates through the real
        ``_rollback_publish`` (it has no handler of its own and is preserved
        unmodified per Requirement 5.1) and lands on the bounded
        ``try/except Exception as rollback_error`` that wraps the
        ``_rollback_publish`` *invocation site* in the ``except`` block of
        ``execute()``. That bounded handler is the single reason the original
        exception survives, which is exactly what this test pins: without it,
        ``Exception('rollback boom')`` would escape the handler and the real
        cause of the failed launch would be lost.

        The first deletion is the one that blows up, so the campaign deletion
        is attempted and the ad creative deletions are not reached. That is the
        expected consequence of the raise, not an assertion about rollback
        completeness -- the full-rollback ordering is covered by
        ``test_rest_client_exception_after_creatives_triggers_full_rollback``.

        Requirements: 6.12
        """
        publish_error = RESTClientException({"error": {"code": 100}})
        rollback_error = Exception("rollback boom")

        with launch_scenario(
            use_case_factory,
            side_effects={
                "_publish_ad": publish_error,
                "_delete_object": rollback_error,
            },
        ) as scenario:
            with pytest.raises(RESTClientException) as exc_info:
                scenario.use_case.execute()

            # The caller sees the *publishing* failure, by identity: same
            # object, not a copy and not a re-wrapped equivalent.
            assert exc_info.value is publish_error
            assert exc_info.value.text == {"error": {"code": 100}}

            # And emphatically not the rollback failure, neither propagated in
            # its place nor chained in front of it.
            assert exc_info.value is not rollback_error
            assert exc_info.value.__cause__ is None
            assert exc_info.value.__context__ is not rollback_error

            # Preconditions: the failure really happened after the campaign
            # existed and after an ad creative had been created, so the
            # rollback had something to delete and really was attempted.
            assert scenario.mocks["_publish_campaign"].call_count == 1
            assert scenario.created_ad_creative_ids == ["meta-adcreative-1"]
            assert scenario.mock_delete_object.call_args_list[0] == call(
                scenario.meta_campaign_id, ACCESS_TOKEN
            )

            # A failed launch never marks the campaign as published, not even
            # when the rollback itself failed (Requirement 5.12).
            scenario.mock_update_campaign_setup.assert_not_called()

    def test_dynamic_mode_rollback_is_identical(self, use_case_factory):
        """The Rollback_de_Lanzamiento does not depend on the creative type:
        the same partial failure under ``CreativeType.DYNAMIC.value`` produces
        exactly the same ``_delete_object`` invocations as under
        ``CreativeType.STANDARD.value`` (Requirement 5.11).

        Mirror of
        ``test_rest_client_exception_after_creatives_triggers_full_rollback``:
        one ad set with three ads, ``_publish_ad`` succeeding once and then
        raising a non-authentication ``RESTClientException``, so at the moment
        of failure exactly two ad creatives exist and the third one was never
        created.

        The two runs are executed here side by side and the recorded call
        lists compared against each other, not just against a hardcoded
        expectation: that is what makes "identical" an assertion about the two
        modes rather than two independent assertions that happen to agree
        today. Only the creative payload differs between the runs
        (``asset_feed_spec`` vs ``object_story_spec``) and
        ``self.campaign_mode`` is asserted on the live instance, so a handler
        that started branching on the mode would break here.

        ``_delete_object`` is patched instead of ``_rollback_publish``
        (Requirements 5.1, 6.6c), so the real rollback routine runs in both
        modes and its deletion order -- campaign first, then the orphaned ad
        creatives -- is what the ``call_args_list`` comparison observes.

        Requirements: 6.13
        """

        def run_partial_failure(campaign_mode, build_ad_creative):
            """Run the Requirement 6.6 partial failure under ``campaign_mode``
            and return the rollback footprint it produced.
            """
            publish_error = RESTClientException({"error": {"code": 100}})

            ad_set = make_ad_set_to_publish(
                name="Ad set 1",
                adset_id="adset-1",
                ads=[
                    make_ad(ad_id=f"ad-{index}", ad_creative=build_ad_creative())
                    for index in (1, 2, 3)
                ],
            )

            with launch_scenario(
                use_case_factory,
                ad_sets=[ad_set],
                campaign_mode=campaign_mode,
                side_effects={"_publish_ad": ["meta-ad-1", publish_error]},
            ) as scenario:
                with pytest.raises(RESTClientException) as exc_info:
                    scenario.use_case.execute()

                # The original exception reaches the caller unchanged in both
                # modes: same object, not a copy and not a re-wrapped
                # equivalent.
                assert exc_info.value is publish_error

                # The mode really was the one under test: `_get_campaign_setup`
                # assigned it from the campaign setup the repositories served,
                # so the gate and the handler ran on that branch.
                assert scenario.use_case.campaign_mode == campaign_mode

                return {
                    "delete_calls": list(scenario.mock_delete_object.call_args_list),
                    "expected_delete_calls": scenario.expected_delete_calls(),
                    "created_ad_creative_ids": list(scenario.created_ad_creative_ids),
                    "update_campaign_setup_call_count": (
                        scenario.mock_update_campaign_setup.call_count
                    ),
                }

        dynamic = run_partial_failure(
            CreativeType.DYNAMIC.value,
            lambda: make_ad_creative(asset_feed_spec=make_dynamic_asset_feed_spec()),
        )
        standard = run_partial_failure(
            CreativeType.STANDARD.value,
            lambda: make_ad_creative(
                object_story_spec=make_standard_object_story_spec()
            ),
        )

        # Precondition of the DYNAMIC scenario: the failure really happened
        # after the campaign existed and after some -- but not all -- ad
        # creatives had been created.
        assert dynamic["created_ad_creative_ids"] == [
            "meta-adcreative-1",
            "meta-adcreative-2",
        ]

        # (a) + (b): the campaign exactly once, and each created ad creative
        # exactly once -- no more, no less.
        assert dynamic["delete_calls"] == dynamic["expected_delete_calls"]
        assert dynamic["delete_calls"] == [
            call(META_CAMPAIGN_ID, ACCESS_TOKEN),
            call("meta-adcreative-1", ACCESS_TOKEN),
            call("meta-adcreative-2", ACCESS_TOKEN),
        ]
        assert len(dynamic["delete_calls"]) == 3

        deleted_ids = [delete_call.args[0] for delete_call in dynamic["delete_calls"]]
        assert deleted_ids.count(META_CAMPAIGN_ID) == 1
        for ad_creative_id in dynamic["created_ad_creative_ids"]:
            assert deleted_ids.count(ad_creative_id) == 1

        # The ad creative that was never created is never deleted either.
        assert "meta-adcreative-3" not in deleted_ids

        # (c) Campaign before creatives: deleting the campaign cascades to its
        # ad sets and ads, so it has to come first.
        assert deleted_ids.index(META_CAMPAIGN_ID) == 0

        # (e) A failed DYNAMIC launch never marks the campaign as published
        # either (Requirement 5.12).
        assert dynamic["update_campaign_setup_call_count"] == 0

        # Requirement 5.11: the rollback footprint of the two modes is the
        # very same list of calls, in the very same order.
        assert dynamic["delete_calls"] == standard["delete_calls"]
        assert dynamic["created_ad_creative_ids"] == standard["created_ad_creative_ids"]
        assert (
            dynamic["update_campaign_setup_call_count"]
            == standard["update_campaign_setup_call_count"]
        )


# The two zones of Requirement 5.10, i.e. the two ways a launch can fail while
# no Meta campaign exists yet, in which case the Rollback_de_Lanzamiento must
# not delete a single object:
#
# - ``outside_try``: the failure happens *before* the ``try`` block of
#   ``execute()`` (during ``_get_decoded_access_token``, ``_get_campaign``,
#   ``_get_ad_channel``, ``_get_campaign_setup``, ``_is_campaign_valid`` or
#   ``_build_meta_campaign``), so the ``except`` handler is never entered and
#   ``_rollback_publish`` is never even invoked. ``_get_campaign_setup`` is
#   the representative chosen here because it is the last collaborator
#   resolved before the gate, so it is the latest point at which the handler
#   is still structurally unreachable.
# - ``inside_try_no_campaign_id``: the failure happens *inside* the ``try``
#   block, on its very first Graph API call ``_publish_campaign``, so the
#   handler does run -- but with ``meta_campaign_id is None`` and an empty
#   ``created_ad_creative_ids``, which makes the real ``_rollback_publish``
#   a no-op (its ``if meta_campaign_id:`` guard is false and its loop has
#   nothing to iterate).
#
# The two zones are therefore verified for the same observable outcome
# through two structurally different paths: one that skips the handler and
# one that runs it end to end.
NO_CAMPAIGN_FAILURE_ZONES = (
    pytest.param("_get_campaign_setup", id="outside_try"),
    pytest.param("_publish_campaign", id="inside_try_no_campaign_id"),
)


class TestRollbackNotReachable:
    """Behaviour of ``execute()`` when the launch fails before a Meta campaign
    exists: nothing to roll back, nothing marked as published, and the
    original exception reaching the caller intact (Requirements 5.10, 5.12).
    """

    @pytest.mark.parametrize("failing_method", NO_CAMPAIGN_FAILURE_ZONES)
    def test_failure_before_campaign_creation(self, use_case_factory, failing_method):
        """A failure in either zone of Requirement 5.10 leaves Meta untouched:
        ``_delete_object`` is not invoked a single time, ``_update_campaign_setup``
        is not invoked, and the original exception is re-raised unmodified.

        ``_delete_object`` is patched rather than ``_rollback_publish``
        (consistently with the partial-failure scenarios above), so the real
        rollback routine runs in the ``inside_try_no_campaign_id`` zone and its
        ``if meta_campaign_id:`` guard plus its empty creative loop are what
        produce the zero deletions -- rather than the assertion passing because
        the routine itself was stubbed away.

        Requirements: 6.7
        """
        launch_error = RESTClientException({"error": {"code": 100}})

        with launch_scenario(
            use_case_factory,
            side_effects={failing_method: launch_error},
        ) as scenario:
            with pytest.raises(RESTClientException) as exc_info:
                scenario.use_case.execute()

            # The original exception reaches the caller unchanged: same object,
            # not a copy and not a re-wrapped equivalent. Identity is the only
            # comparison that rules out a re-raise which rebuilt the exception.
            assert exc_info.value is launch_error
            assert exc_info.value.text == {"error": {"code": 100}}

            # No object is deleted in Meta, because none was ever created.
            scenario.mock_delete_object.assert_not_called()
            assert scenario.mock_delete_object.call_count == 0

            # Requirement 5.12: a failed launch never marks the campaign as
            # published.
            scenario.mock_update_campaign_setup.assert_not_called()

            # Precondition of both zones: no ad creative was created either,
            # so "zero deletions" cannot be passing because the rollback had
            # nothing recorded to delete *by accident*.
            assert scenario.created_ad_creative_ids == []

            # Zone-specific preconditions, so a regression that moved the
            # failure point would fail here instead of silently satisfying the
            # assertions above from the wrong zone.
            if failing_method == "_get_campaign_setup":
                scenario.mocks["_publish_campaign"].assert_not_called()
            else:
                scenario.mocks["_publish_campaign"].assert_called_once()
                scenario.mocks["_publish_adset"].assert_not_called()


# ---------------------------------------------------------------------------
# Meta authentication error classification (Requirement 5.6, 5.7)
#
# The exact code/text pair `execute()` must surface when the captured
# exception carries one of the recognised authentication markers. Kept as
# module constants because the classification cases assert on the very same
# pair, and a drift in either value is a user-visible contract change.
# ---------------------------------------------------------------------------

META31_CODE = "META31"
META31_TEXT = "Autentica tu cuenta en el administrador de anuncios"

# The two *other* recognised shapes of Requirement 5.6, beyond the nested
# `code == 31` already covered by `test_nested_code_31_raises_meta31`:
#
# - the nested `error_subcode` marker, which Meta returns for the
#   "user needs to re-authenticate in Ads Manager" family of responses even
#   when the outer `code` is something else entirely, and
# - the flat shape, where the markers sit at the top level of `text` because
#   the exception was built from an already-unwrapped payload instead of from
#   the raw `response.json()`.
#
# Both must reach the same META31 outcome as the nested `code == 31` case:
# the classifier searches `text` and `text['error']` for either marker.
RECOGNISED_AUTH_ERROR_TEXTS = [
    pytest.param({"error": {"error_subcode": 3858385}}, id="nested_error_subcode"),
    pytest.param({"code": 31}, id="flat_code_31"),
]

# Counterexample of Requirement 6.10: a well-formed nested Meta error whose
# code is *not* an authentication marker. `190` is deliberately close to the
# real thing (it is Meta's generic OAuth error) precisely because a classifier
# that keyed off "there is an `error` dict with a `code`" instead of off the
# exact marker values would swallow it and report META31 to the user.
UNRECOGNISED_AUTH_ERROR_TEXT = {"error": {"code": 190}}


class TestMetaAuthErrorClassification:
    """Behaviour of the Meta authentication error classification of the
    ``except`` block of ``execute()`` (Requirements 5.6, 5.7).
    """

    def test_nested_code_31_raises_meta31(self, use_case_factory):
        """A failure carrying ``text = {'error': {'code': 31}}`` after
        ``_publish_campaign`` succeeded and at least one ad creative was
        created is classified as a Meta authentication error: ``execute()``
        raises ``SinergiaException`` with code ``'META31'`` and the text
        ``'Autentica tu cuenta en el administrador de anuncios'``.

        This is the *outer nested* shape, i.e. the one
        ``RESTClientException(response.json())`` really produces in
        ``_publish_campaign``/``_publish_adset``/``_publish_ad_creative``/
        ``_publish_ad`` when Meta answers with a status other than 200: the
        marker lives in ``text['error']['code']``, not at the top level of
        ``text``. A classifier that only looked at ``text.get('code')`` would
        miss it and re-raise the raw ``RESTClientException`` instead.

        ``RESTClientException`` is itself a ``SinergiaException`` subclass, so
        the assertions below deliberately pin down *which* exception came out:
        the exact type ``SinergiaException`` (not a subclass) and a non-identity
        check against the original error, which together rule out the
        "original exception re-raised" path passing this test by accident.

        Requirements: 6.9
        """
        auth_error = RESTClientException({"error": {"code": 31}})

        with launch_scenario(
            use_case_factory,
            side_effects={"_publish_ad": auth_error},
        ) as scenario:
            with pytest.raises(SinergiaException) as exc_info:
                scenario.use_case.execute()

            # Preconditions of the scenario: the campaign already existed and
            # the failing ad's creative had already been created when the
            # authentication error surfaced, which is the state Requirement
            # 6.9 describes.
            scenario.mocks["_publish_campaign"].assert_called_once()
            assert scenario.created_ad_creative_ids == ["meta-adcreative-1"]

            # The classification really replaced the exception: a re-raise of
            # the original `RESTClientException` would also be caught by
            # `pytest.raises(SinergiaException)` above, so identity and exact
            # type are what separate the two paths.
            assert exc_info.value is not auth_error
            assert type(exc_info.value) is SinergiaException

            assert_sinergia_exception(exc_info, META31_CODE, META31_TEXT)

    @pytest.mark.parametrize("error_text", RECOGNISED_AUTH_ERROR_TEXTS)
    def test_recognized_forms(self, use_case_factory, error_text):
        """Both remaining recognised marker shapes of Requirement 5.6 trigger
        the classification just like the nested ``code == 31`` case does:
        ``text = {'error': {'error_subcode': 3858385}}`` (nested subcode) and
        ``text = {'code': 31}`` (flat form).

        The failure is injected at the same point as in
        ``test_nested_code_31_raises_meta31`` -- after ``_publish_campaign``
        succeeded and one ad creative exists -- so the only difference between
        the three cases is the shape of ``text``, which is what makes them a
        statement about the classifier rather than about the failure point.

        As in the nested case, identity and exact type are what separate the
        classification path from the "original exception re-raised" path:
        ``RESTClientException`` is itself a ``SinergiaException`` subclass, so
        ``pytest.raises(SinergiaException)`` alone would accept either.

        Requirements: 6.10
        """
        auth_error = RESTClientException(error_text)

        with launch_scenario(
            use_case_factory,
            side_effects={"_publish_ad": auth_error},
        ) as scenario:
            with pytest.raises(SinergiaException) as exc_info:
                scenario.use_case.execute()

            # Preconditions of the scenario: the campaign already existed and
            # the failing ad's creative had already been created when the
            # authentication error surfaced.
            scenario.mocks["_publish_campaign"].assert_called_once()
            assert scenario.created_ad_creative_ids == ["meta-adcreative-1"]

            assert exc_info.value is not auth_error
            assert type(exc_info.value) is SinergiaException

            assert_sinergia_exception(exc_info, META31_CODE, META31_TEXT)

    def test_unrecognized_form_reraises_original(self, use_case_factory):
        """Counterexample of Requirement 6.10: ``text = {'error': {'code':
        190}}`` carries neither marker, so the classification does *not* fire
        and ``execute()`` re-raises the original ``RESTClientException``
        itself.

        This is the assertion that gives the three positive cases above their
        meaning: without it, a classifier that returned ``True`` for every
        exception carrying a dict ``text`` would pass them all while reporting
        "authenticate your account" for unrelated Meta failures.

        Identity is the comparison that matters here -- the same object the
        publishing double raised has to come out, not a rebuilt equivalent --
        and the code/text pair is checked to be the raw one, not META31.

        Requirements: 6.10
        """
        publish_error = RESTClientException(UNRECOGNISED_AUTH_ERROR_TEXT)

        with launch_scenario(
            use_case_factory,
            side_effects={"_publish_ad": publish_error},
        ) as scenario:
            with pytest.raises(RESTClientException) as exc_info:
                scenario.use_case.execute()

            # Same scenario as the recognised forms: the classification had a
            # dict `text` to inspect and still declined it.
            scenario.mocks["_publish_campaign"].assert_called_once()
            assert scenario.created_ad_creative_ids == ["meta-adcreative-1"]

            assert exc_info.value is publish_error
            assert exc_info.value.text == UNRECOGNISED_AUTH_ERROR_TEXT
            assert exc_info.value.code != META31_CODE

    def test_rollback_runs_before_meta31(self, use_case_factory):
        """The Rollback_de_Lanzamiento is not skipped by the authentication
        path: for the very scenario of Requirement 6.9 (``text = {'error':
        {'code': 31}}`` raised by ``_publish_ad`` after the campaign and some
        ad creatives already exist), ``execute()`` deletes the campaign and
        every ad creative it had created *before* raising
        ``SinergiaException('META31', ...)``, and never marks the campaign as
        published.

        This is the criterion that pins the *ordering* of the hardened
        handler: the rollback is invoked unconditionally and ahead of the
        classification, so an implementation that classified first and raised
        META31 straight away would leave a live campaign and orphaned ad
        creatives behind in Meta while still passing
        ``test_nested_code_31_raises_meta31``.

        The fixture holds one ad set with three ads and ``_publish_ad``
        succeeds once and then raises, so at the moment of failure exactly two
        of the three ad creatives exist. That is what gives "each ad creative
        already created" a verifiable count: a rollback that deleted the
        creatives of the whole fixture (three) or that skipped one (one) would
        both fail the exact call-list comparison below, which a single-ad
        fixture could not distinguish.

        ``_delete_object`` is patched rather than ``_rollback_publish``
        (Requirements 5.1, 6.6c), so the real rollback routine runs and the
        deletions observed are the ones it really performed.

        Requirements: 6.11
        """
        auth_error = RESTClientException({"error": {"code": 31}})

        ad_set = make_fully_valid_standard_ad_set(name="Ad set 1", adset_id="adset-1")
        ad_set["ads"] = [
            make_ad(
                ad_id=f"ad-{index}",
                ad_creative=make_ad_creative(
                    object_story_spec=make_standard_object_story_spec()
                ),
            )
            for index in (1, 2, 3)
        ]

        with launch_scenario(
            use_case_factory,
            ad_sets=[ad_set],
            side_effects={"_publish_ad": ["meta-ad-1", auth_error]},
        ) as scenario:
            with pytest.raises(SinergiaException) as exc_info:
                scenario.use_case.execute()

            # The scenario really went down the authentication path -- and not
            # through the plain re-raise -- so the assertions below are about
            # the rollback that precedes META31. `RESTClientException` is a
            # `SinergiaException` subclass, hence the identity and exact-type
            # checks.
            assert exc_info.value is not auth_error
            assert type(exc_info.value) is SinergiaException
            assert_sinergia_exception(exc_info, META31_CODE, META31_TEXT)

            # Preconditions: the campaign existed and only two of the three ad
            # creatives had been created when the authentication error surfaced.
            scenario.mocks["_publish_campaign"].assert_called_once()
            assert scenario.created_ad_creative_ids == [
                "meta-adcreative-1",
                "meta-adcreative-2",
            ]

            delete_calls = scenario.mock_delete_object.call_args_list

            # (a) The rollback did run before META31 was raised: the campaign
            # exactly once, then every created ad creative exactly once.
            assert delete_calls == scenario.expected_delete_calls()
            assert scenario.mock_delete_object.call_count == 3

            deleted_ids = [delete_call.args[0] for delete_call in delete_calls]
            assert deleted_ids.count(scenario.meta_campaign_id) == 1
            for ad_creative_id in scenario.created_ad_creative_ids:
                assert deleted_ids.count(ad_creative_id) == 1

            # The ad creative that was never created is never deleted either.
            assert "meta-adcreative-3" not in deleted_ids

            # (b) An authentication failure never marks the campaign as
            # published (Requirement 5.12).
            scenario.mock_update_campaign_setup.assert_not_called()


# ---------------------------------------------------------------------------
# Task 12.1 -- DYNAMIC non-regression (Requirement 6.14)
# ---------------------------------------------------------------------------
# The Creative_Publicado that the untouched DYNAMIC branch of
# `_build_response` must keep producing for the fixed fixture
# `make_fully_valid_dynamic_ad_set()`, written out as a literal rather than
# derived from the fixture: a golden value computed from the same expressions
# the branch uses would drift together with any change to those expressions,
# which is exactly what this non-regression check has to catch.
#
# Every value below is the DYNAMIC mapping applied by hand to the fixture:
# ad-set level fields from `make_ad_set_to_publish` defaults, everything else
# from `make_dynamic_asset_feed_spec` defaults. Note the two DYNAMIC-only
# shapes this pins: `images` keeps only `url`/`valid`/`error` (the fixture's
# `hash` is dropped), and `proposal_url` is the comma-join of the
# `link_urls[*].website_url` values.
EXPECTED_DYNAMIC_CREATIVE_PUBLISHED = {
    "idx": 0,
    "name": "Ad set 1",
    "adset_id": "adset-1",
    "ad_id": "ad-1",
    "adchannel_id": 7,
    "daily_budget": 100,
    "images": [
        {"url": "https://example.test/dynamic.jpg", "valid": True, "error": None}
    ],
    "bodies": [{"text": "Dynamic body"}],
    "titles": [{"text": "Dynamic title"}],
    "descriptions": [{"text": "Dynamic description"}],
    "call_to_action_types": [{"value": "SHOP_NOW", "valid": True}],
    "images_valid_amount": True,
    "titles_valid_amount": True,
    "bodies_valid_amount": True,
    "descriptions_valid_amount": True,
    "call_to_action_types_valid_amount": True,
    "images_max_amount": 10,
    "titles_max_amount": 5,
    "bodies_max_amount": 5,
    "descriptions_max_amount": 5,
    "call_to_action_types_max_amount": 5,
    "unique_titles": True,
    "unique_bodies": True,
    "unique_descriptions": True,
    "daily_budget_valid": True,
    "min_daily_budget": 5,
    "proposal_url": "https://example.test/landing",
    "proposal_url_valid": True,
    "proposal_locations": [{"key": "ES", "name": "Spain"}],
    "locations": [{"key": "ES", "name": "Spain"}],
    "locations_valid": True,
}


def _dynamic_ad_set_with_asset_feed_spec(**asset_feed_spec_overrides):
    """Return a fresh DYNAMIC Ad_Set_a_Publicar whose ``asset_feed_spec``
    carries ``asset_feed_spec_overrides`` on top of the complete fixture.

    Requirements: 6.14
    """
    return make_ad_set_to_publish(
        ads=[
            make_ad(
                ad_creative=make_ad_creative(
                    asset_feed_spec=make_dynamic_asset_feed_spec(
                        **asset_feed_spec_overrides
                    )
                )
            )
        ]
    )


class TestDynamicNonRegression:
    """The DYNAMIC branches of ``_is_campaign_valid`` and ``_build_response``
    are unchanged by this spec (Requirements 2.4, 3.4).

    Both cases are pinned by exact equality against a fixed expected value on
    a fixed DYNAMIC fixture, so any drift in the untouched branches -- an
    added or dropped key, a changed default, a relaxed or tightened gate
    condition -- fails here instead of silently reaching production.

    Requirements: 6.14
    """

    @pytest.mark.parametrize(
        "asset_feed_spec_overrides,expected",
        (
            pytest.param({}, True, id="complete-asset-feed-spec"),
            pytest.param({"unique_bodies": ABSENT}, False, id="missing-unique-bodies"),
        ),
    )
    def test_is_campaign_valid_dynamic_is_unchanged(
        self, use_case_factory, asset_feed_spec_overrides, expected
    ):
        """``_is_campaign_valid`` keeps returning exactly the boolean the
        DYNAMIC branch returned before this spec: ``True`` for the complete
        fixed fixture, ``False`` when a single one of the eleven annotations
        the branch requires to be truthy is missing.

        Both polarities are checked because a comparison against ``True``
        alone would also pass for an implementation that answered ``True``
        unconditionally -- which is precisely what the pre-existing
        ``else: valid = True`` fallback does and what the new STANDARD
        ``elif`` had to avoid disturbing. Comparison is with ``is`` so no
        truthy stand-in can pass for the boolean.

        Requirements: 6.14
        """
        use_case, _, _, _ = use_case_factory(campaign_mode=CreativeType.DYNAMIC.value)

        result = use_case._is_campaign_valid(
            [_dynamic_ad_set_with_asset_feed_spec(**asset_feed_spec_overrides)]
        )

        assert result is expected

    def test_build_response_dynamic_is_unchanged(self, use_case_factory):
        """``_build_response`` keeps producing, for the fixed DYNAMIC
        fixture, exactly the Creative_Publicado dict of
        ``EXPECTED_DYNAMIC_CREATIVE_PUBLISHED``.

        The whole dict is compared at once against a hand-written literal, so
        the check covers the key set, every value and every DYNAMIC-specific
        shape (``images`` reduced to ``url``/``valid``/``error``,
        ``proposal_url`` joined from ``link_urls``) in one assertion. Building
        the expectation from the fixture instead would let a change to the
        branch's source expressions go unnoticed.

        Requirements: 6.14
        """
        use_case, _, _, _ = use_case_factory(campaign_mode=CreativeType.DYNAMIC.value)

        ad_set_published = make_fully_valid_dynamic_ad_set(
            name="Ad set 1", adset_id="adset-1"
        )

        response = use_case._build_response(
            META_CAMPAIGN_ID, make_campaign()["attributes"], [ad_set_published]
        )

        assert len(response["creatives"]) == 1
        assert response["creatives"][0] == EXPECTED_DYNAMIC_CREATIVE_PUBLISHED


# --------------------------------------------------------------------------
# Optional property-based test (task 14.1).
#
# Both `requirements.md` ("Property-Based Tests") and `design.md`
# ("Correctness Properties") resolve that a Hypothesis property set is NOT a
# mandatory requirement of this spec; Property 1 is documented there as a
# useful optional candidate because the STANDARD gate is a pure, in-memory,
# I/O-free boolean function. This section complements -- it does not replace
# -- the parametrized matrices of `TestIsCampaignValidStandard` above.
# --------------------------------------------------------------------------


# Truthy values of a type other than `bool`, i.e. exactly the class of values
# that a loose `if not field` check would happily accept while the strict
# `is not True` comparison of the implementation must reject. All of them are
# immutable, so the same sampled object can be safely reused across Hypothesis
# examples: it is only ever stored into a freshly built dict, never mutated.
TRUTHY_NON_BOOLEAN_ANNOTATIONS = (1, 2.5, "yes", "False", (1,))


# The per-field domain of Property 1: absent (`ABSENT` deletes the key),
# `None`, `False`, exactly `True`, or a truthy non-boolean value.
ANNOTATION_VALUES = st.sampled_from(
    (ABSENT, None, False, True) + TRUTHY_NON_BOOLEAN_ANNOTATIONS
)


# One ad's worth of annotations: a tuple of eight values positionally aligned
# with `STANDARD_GATE_CONDITIONS`.
#
# Smart generator: a uniform draw over the eight-fold product would make the
# all-`True` combination appear with probability (1/8)**8, so the `True` side
# of the "if and only if" would essentially never be exercised. Branching
# explicitly on `st.just((True,) * 8)` puts roughly half the examples on the
# valid side while the other branch still covers the whole product space,
# including all-`True` combinations reached by chance.
AD_ANNOTATIONS = st.one_of(
    st.just((True,) * len(STANDARD_GATE_CONDITIONS)),
    st.tuples(*([ANNOTATION_VALUES] * len(STANDARD_GATE_CONDITIONS))),
)


# A whole `creatives_to_publish` list: 1-3 Ad_Set_a_Publicar, each holding 1-2
# ads, each ad with its own independent annotation combination. Small bounds
# on purpose: the invariant is per-ad, so wider lists only slow the run down
# without reaching new behaviour, while >1 ad and >1 ad set are what actually
# exercise the "all or nothing" quantification of Requirement 2.2.
STANDARD_AD_SET_ANNOTATIONS = st.lists(
    st.lists(AD_ANNOTATIONS, min_size=1, max_size=2),
    min_size=1,
    max_size=3,
)


def _build_standard_ad_set_from_annotations(idx, ads_annotations):
    """Build a fresh STANDARD Ad_Set_a_Publicar whose i-th ad carries the
    i-th annotation combination of ``ads_annotations``.

    Each ad starts from the fully valid chain of
    ``make_standard_object_story_spec()`` (all eight conditions of Requirement
    2.1 at exactly ``True``) and every non-``True`` generated value is applied
    through the existing ``_invalidate`` helper, which resolves the annotation's
    container via ``_condition_container`` and either deletes the key
    (``ABSENT``) or overwrites it. Reusing that helper keeps a single
    description of the ``object_story_spec`` -> ``link_data`` ->
    ``call_to_action['type']`` chain in this module.

    Validates: Requirements 2.1, 2.2, 2.5
    """
    ads = []

    for ad_idx, annotation_values in enumerate(ads_annotations):
        ad = make_ad(
            ad_id=f"ad-{idx}-{ad_idx}",
            ad_creative=make_ad_creative(
                object_story_spec=make_standard_object_story_spec()
            ),
        )
        # `_invalidate` expects an Ad_Set_a_Publicar shaped dict and works on
        # `ads[0]`, so each ad is handed over on its own single-ad wrapper.
        single_ad_wrapper = {"ads": [ad]}

        for (container, field), value in zip(
            STANDARD_GATE_CONDITIONS, annotation_values
        ):
            if value is True:
                # Already exactly `True` from the builder.
                continue

            _invalidate(single_ad_wrapper, container, field, value)

        ads.append(ad)

    return make_ad_set_to_publish(
        name=f"Ad set {idx}", adset_id=f"adset-{idx}", ads=ads
    )


class TestIsCampaignValidStandardProperty:
    """Optional property-based coverage of the STANDARD gate
    (``design.md`` -> Correctness Properties -> Property 1).
    """

    # Feature: meta-ads-standard-launch-campaign, Property 1: El gate STANDARD
    # es exactamente la conjuncion de las 8 condiciones
    @settings(
        max_examples=100,
        deadline=None,
        # `use_case_factory` is function scoped: the use case is built once per
        # test function and reused across examples. That is sound here because
        # `_is_campaign_valid` only reads `self.campaign_mode` and the ad sets
        # it receives -- it keeps no state and mutates nothing on the instance
        # -- and every example builds brand new ad sets. Same suppression
        # already used by the sibling suites `test_funnel_flow_validator.py`
        # and `test_pin_format_ad_variant.py`.
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(ad_sets_annotations=STANDARD_AD_SET_ANNOTATIONS)
    def test_property_standard_gate_is_conjunction_of_eight_conditions(
        self, use_case_factory, ad_sets_annotations
    ):
        """For every STANDARD ``creatives_to_publish`` list and every
        combination of the eight annotations of Requirement 2.1 -- each one
        absent, ``None``, ``False``, ``True``, or a truthy non-boolean value --
        ``_is_campaign_valid`` returns ``True`` if and only if all eight
        annotations are present with the exact value ``True`` on every ad of
        every Ad_Set_a_Publicar, and ``False`` in every other case, without
        raising.

        ``_is_campaign_valid`` is invoked directly on the instance, never
        through ``execute()``: the gate is a pure in-memory function, so no
        publishing helper, repository or Redis double takes part beyond the
        three repositories ``use_case_factory`` already replaces. Any
        exception escaping the call fails the example, which is what pins the
        totality half of the property (Requirement 2.5): the chain
        normalisation must absorb every generated shape instead of letting an
        ``AttributeError``/``TypeError`` through.

        The expected value is computed from the generated annotations alone,
        independently of the implementation's short-circuit order, so the
        property also pins "all or nothing" (Requirement 2.2): a single
        non-``True`` annotation on a single ad of a single ad set invalidates
        the whole set.

        Validates: Requirements 2.1, 2.2, 2.5
        """
        use_case, _, _, _ = use_case_factory(campaign_mode=CreativeType.STANDARD.value)

        ad_sets = [
            _build_standard_ad_set_from_annotations(idx, ads_annotations)
            for idx, ads_annotations in enumerate(ad_sets_annotations)
        ]

        expected = all(
            value is True
            for ads_annotations in ad_sets_annotations
            for annotation_values in ads_annotations
            for value in annotation_values
        )

        assert use_case._is_campaign_valid(ad_sets) is expected

# --------------------------------------------------------------------------
# Optional property-based test (task 14.2).
#
# Property 2 of `design.md` ("Correctness Properties"): the STANDARD
# Creative_Publicado constructor is *total* (never raises, whatever is missing
# from the `adCreative` -> `object_story_spec` -> `link_data` ->
# `call_to_action` chain) and *fixed key* (always the same 31 keys of
# Requirement 3.2, the very set the DYNAMIC branch produces), falling back to
# the documented default for every key whose source datum is absent.
#
# `_build_standard_creative_published` is invoked directly on the instance,
# never through `_build_response` or `execute()`: it is a pure in-memory
# function, so no publishing helper, repository or Redis double takes part
# beyond the three repositories `use_case_factory` already replaces. This
# section complements -- it does not replace -- the parametrized
# `ABSENT_DATA_CASES` matrix of `TestBuildResponseStandard` above, which pins
# the three named scenarios of Requirement 6.5 by example.
# --------------------------------------------------------------------------


# The leaf keys of each link of the chain, read back from the very builders
# the example based tests use, so the generator cannot drift away from them.
# The nested container key is excluded from each list (it is drawn separately
# as a shape below): `link_data` from `object_story_spec`, `call_to_action`
# from `link_data`.
_OBJECT_STORY_SPEC_LEAF_KEYS = tuple(make_standard_object_story_spec(link_data=ABSENT))
_LINK_DATA_LEAF_KEYS = tuple(make_standard_link_data(call_to_action=ABSENT))
_CALL_TO_ACTION_KEYS = ("type",)


# The three shapes each link of the chain can take, covering the whole domain
# of Property 2: the key omitted altogether, the key present with the value
# `None`, or the key present with a dict holding an arbitrary subset of its
# keys (the empty subset included).
_CHAIN_LINK_SHAPES = st.sampled_from(("absent", "none", "present"))


def _keep(full_dict, keys):
    """Return a fresh dict holding only the ``keys`` of ``full_dict``.

    The vehicle for the "any subset of the keys" quantification of Property 2:
    a builder produces the complete dict and this drops everything the
    generator did not draw.

    Validates: Requirements 3.2, 3.3
    """
    return {key: value for key, value in full_dict.items() if key in keys}


def _key_subsets(keys):
    """Strategy over every subset of ``keys`` (the empty one included).

    Drawn as one independent boolean per key rather than through
    ``st.sets(st.sampled_from(keys))``: a fixed-width tuple of flags needs no
    uniqueness retries and gives every subset the same weight, which matters
    for a pool as small as ``_CALL_TO_ACTION_KEYS`` (a single key).

    Validates: Requirements 3.2, 3.3
    """
    return st.tuples(*([st.booleans()] * len(keys))).map(
        lambda flags: {key for key, keep in zip(keys, flags) if keep}
    )


@st.composite
def _standard_published_ads(draw):
    """Draw a STANDARD ``ads_published`` dict whose ``adCreative`` chain is
    mutilated in an arbitrary way, and report which containers survive.

    Returns the 4-tuple ``(ads_published, object_story_spec, link_data,
    call_to_action)``, where the last three are the *effective* containers,
    i.e. the dict the implementation ends up normalizing to, or ``{}`` when
    that link of the chain is unreachable (absent, ``None``, or nested under
    an absent/``None`` parent). Returning them alongside the payload lets the
    property decide, without re-deriving the normalization, which keys are
    expected to fall back to their documented default.

    Leaf values always come from the builders (all truthy, all different from
    their documented default), so presence of a key is the only generated
    dimension for leaves. That is what makes the bidirectional check of the
    property possible: an absent datum must yield exactly the documented
    default and a present one must yield something else, so a constructor
    defaulting everything unconditionally would be caught.

    Validates: Requirements 3.2, 3.3
    """
    ad_creative_shape = draw(_CHAIN_LINK_SHAPES)
    object_story_spec_shape = draw(_CHAIN_LINK_SHAPES)
    link_data_shape = draw(_CHAIN_LINK_SHAPES)
    call_to_action_shape = draw(_CHAIN_LINK_SHAPES)

    object_story_spec_keys = draw(_key_subsets(_OBJECT_STORY_SPEC_LEAF_KEYS))
    link_data_keys = draw(_key_subsets(_LINK_DATA_LEAF_KEYS))
    call_to_action_keys = draw(_key_subsets(_CALL_TO_ACTION_KEYS))

    if call_to_action_shape == "present":
        call_to_action = _keep(
            make_standard_link_data()["call_to_action"], call_to_action_keys
        )
    else:
        call_to_action = None if call_to_action_shape == "none" else ABSENT

    if link_data_shape == "present":
        link_data = _keep(
            make_standard_link_data(call_to_action=ABSENT), link_data_keys
        )
        if call_to_action is not ABSENT:
            link_data["call_to_action"] = call_to_action
    else:
        link_data = None if link_data_shape == "none" else ABSENT

    if object_story_spec_shape == "present":
        object_story_spec = _keep(
            make_standard_object_story_spec(link_data=ABSENT), object_story_spec_keys
        )
        if link_data is not ABSENT:
            object_story_spec["link_data"] = link_data
    else:
        object_story_spec = None if object_story_spec_shape == "none" else ABSENT

    if ad_creative_shape == "present":
        # `make_ad_creative` omits `object_story_spec` when handed `ABSENT`
        # and keeps it with the value `None` otherwise.
        ad_creative = make_ad_creative(object_story_spec=object_story_spec)
    else:
        ad_creative = None if ad_creative_shape == "none" else ABSENT

    ads_published = make_ad(ad_creative=ad_creative)

    # A link is only effective when every link above it is a present dict.
    object_story_spec_reachable = (
        ad_creative_shape == "present" and object_story_spec_shape == "present"
    )
    link_data_reachable = object_story_spec_reachable and link_data_shape == "present"
    call_to_action_reachable = link_data_reachable and call_to_action_shape == "present"

    return (
        ads_published,
        object_story_spec if object_story_spec_reachable else {},
        link_data if link_data_reachable else {},
        call_to_action if call_to_action_reachable else {},
    )


# For every key of `DOCUMENTED_DEFAULTS`, the predicate deciding whether its
# source datum is present in the effective containers. Mirrors the "Expresión
# fuente" column of the mapping table of `design.md`: keys read through
# `.get(field, default)` count as present as soon as the key exists, while
# keys guarded by a truthiness check (`images`/`bodies`/`titles`/
# `descriptions`, sourced from a text or URL, `proposal_url` from `ld.get('link')
# or ''`, and the two CTA keys, guarded by `if cta`) count as present only when
# the datum they are guarded by is truthy.
_PROPERTY2_DATUM_PRESENT = {
    # `object_story_spec` sourced keys.
    "adchannel_id": lambda osp, ld, cta: "ad_channel_id" in osp,
    "daily_budget_valid": lambda osp, ld, cta: "daily_budget_valid" in osp,
    "min_daily_budget": lambda osp, ld, cta: "min_daily_budget" in osp,
    "locations": lambda osp, ld, cta: "locations" in osp,
    "locations_valid": lambda osp, ld, cta: "locations_valid" in osp,
    # `link_data` sourced single-item lists, each guarded by the truthiness of
    # the text/URL it carries.
    "images": lambda osp, ld, cta: bool(ld.get("image_url")),
    "bodies": lambda osp, ld, cta: bool(ld.get("message")),
    "titles": lambda osp, ld, cta: bool(ld.get("name")),
    "descriptions": lambda osp, ld, cta: bool(ld.get("description")),
    # `link_data` sourced annotations.
    "images_valid_amount": lambda osp, ld, cta: "image_valid" in ld,
    "titles_valid_amount": lambda osp, ld, cta: "title_valid" in ld,
    "bodies_valid_amount": lambda osp, ld, cta: "body_valid" in ld,
    "descriptions_valid_amount": lambda osp, ld, cta: "description_valid" in ld,
    "unique_titles": lambda osp, ld, cta: "title_valid" in ld,
    "unique_bodies": lambda osp, ld, cta: "body_valid" in ld,
    "unique_descriptions": lambda osp, ld, cta: "description_valid" in ld,
    "proposal_url": lambda osp, ld, cta: bool(ld.get("link")),
    "proposal_url_valid": lambda osp, ld, cta: "link_url_valid" in ld,
    # `call_to_action` sourced keys, both guarded by `if cta`.
    "call_to_action_types": lambda osp, ld, cta: bool(cta),
    "call_to_action_types_valid_amount": (
        lambda osp, ld, cta: bool(cta) and "valid" in (cta.get("type") or {})
    ),
}


def _assert_not_documented_default(entry, key):
    """Assert that ``entry[key]`` is *not* the documented default of ``key``,
    discriminating by the default's type exactly like
    :func:`_assert_documented_default` does, so Python's ``False == 0``
    equivalence cannot make one stand in for the other.

    The complement of :func:`_assert_documented_default`: applied to every key
    whose source datum the generator did supply, it is what stops the property
    from being satisfied by a constructor that defaults every key
    unconditionally.

    Validates: Requirements 3.2, 3.3
    """
    expected_default = DOCUMENTED_DEFAULTS[key]
    actual = entry[key]

    if isinstance(expected_default, bool):
        assert actual is not False, (
            f"{key} carries input data, it must not fall back to False"
        )
    elif isinstance(expected_default, list):
        assert actual != [], f"{key} carries input data, it must not fall back to []"
    elif isinstance(expected_default, int):
        assert actual != 0, f"{key} carries input data, it must not fall back to 0"
    else:
        assert actual != "", f"{key} carries input data, it must not fall back to ''"


class TestBuildStandardCreativePublishedProperty:
    """Optional property-based coverage of the STANDARD Creative_Publicado
    constructor (``design.md`` -> Correctness Properties -> Property 2).
    """

    # Feature: meta-ads-standard-launch-campaign, Property 2: La construccion
    # del Creative_Publicado STANDARD es total y de clave fija
    @settings(
        max_examples=100,
        deadline=None,
        # `use_case_factory` is function scoped: the use case is built once per
        # test function and reused across examples. That is sound here because
        # `_build_standard_creative_published` only reads its three arguments
        # -- it keeps no state and mutates nothing on the instance -- and every
        # example builds a brand new payload. Same suppression already used by
        # the Property 1 class above.
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        payload=_standard_published_ads(),
        idx=st.integers(min_value=0, max_value=5),
    )
    def test_property_standard_creative_published_is_total_and_fixed_key(
        self, use_case_factory, payload, idx
    ):
        """For every STANDARD ``adCreative`` holding any subset of the keys of
        ``object_story_spec``/``link_data``/``call_to_action`` -- the empty
        subset, a ``None`` link, or no ``adCreative`` at all included --
        ``_build_standard_creative_published`` returns a dict whose key set is
        exactly the 31 fixed keys of Requirement 3.2 (the very set the DYNAMIC
        entry carries), never raises, and uses the default documented in the
        mapping table of ``design.md`` for every key derived from a datum the
        payload does not supply.

        No ``pytest.raises`` wrapper is needed for the totality half: any
        exception escaping the call propagates out of the test body and fails
        the example, which is exactly what pins Requirement 3.3 -- the four
        ``or {}`` normalizations must absorb every generated shape instead of
        letting an ``AttributeError``/``TypeError`` through.

        Key fixity is checked against ``EXPECTED_KEYS`` *and* against the key
        set of ``EXPECTED_DYNAMIC_CREATIVE_PUBLISHED``, since key parity with
        the DYNAMIC entry is what Requirement 3.2 actually demands. A subset
        comparison would pass both if a key were dropped and if an extra one
        were emitted (``promoted_object_valid``, for instance, which this
        branch deliberately must not emit).

        Validates: Requirements 3.2, 3.3
        """
        use_case, _, _, _ = use_case_factory(campaign_mode=CreativeType.STANDARD.value)

        ads_published, object_story_spec, link_data, call_to_action = payload
        ad_set_published = make_ad_set_to_publish(ads=[ads_published])

        # The presence table must decide every defaulted key, or the property
        # would silently stop checking some of them.
        assert set(_PROPERTY2_DATUM_PRESENT) == set(DOCUMENTED_DEFAULTS)

        entry = use_case._build_standard_creative_published(
            idx, ad_set_published, ads_published
        )

        # Requirement 3.2: the fixed key set, compared exactly, and identical
        # to the DYNAMIC one.
        assert set(entry.keys()) == EXPECTED_KEYS
        assert set(entry.keys()) == set(EXPECTED_DYNAMIC_CREATIVE_PUBLISHED)
        assert len(entry) == 31

        # The six structural keys never depend on the `adCreative` chain.
        assert entry["idx"] == idx
        assert entry["name"] == ad_set_published["name"]
        assert entry["adset_id"] == ad_set_published["id"]
        assert entry["ad_id"] == ads_published["id"]
        assert entry["daily_budget"] == ad_set_published["daily_budget"]
        assert entry["proposal_locations"] == ad_set_published["proposal_locations"]

        # The five STANDARD constants stay `1` whatever is missing.
        for key in MAX_AMOUNT_KEYS:
            assert entry[key] == 1

        # Requirement 3.3: documented default exactly when the datum is
        # absent, real input data otherwise.
        for key, datum_present in _PROPERTY2_DATUM_PRESENT.items():
            if datum_present(object_story_spec, link_data, call_to_action):
                _assert_not_documented_default(entry, key)
            else:
                _assert_documented_default(entry, key)


# --------------------------------------------------------------------------
# Optional property-based test (task 14.3).
#
# Property 3 of `design.md` ("Correctness Properties"): the exception
# classification is *total* -- for every captured exception, whatever the type
# of its `text` attribute and even with no `text` attribute at all, it returns
# a boolean and never produces a secondary exception -- and it answers `False`
# for every `text` that is not a `dict` instance.
#
# `_is_meta_auth_error` is a `staticmethod`, so it is invoked directly on
# `FacebookLaunchCampaignUseCase` rather than through `execute()` or an
# instance: the classification reads nothing but its single argument, so no
# use case instance, repository, publishing helper or Redis double takes part
# and the `use_case_factory` fixture is not needed here. This section
# complements -- it does not replace -- `TestMetaAuthErrorClassification` and
# `TestRollbackOnPartialFailure` above, which pin the *positive* side of the
# classification (Requirements 5.6, 5.7) end to end through `execute()`.
# --------------------------------------------------------------------------


class _DictImpostor:
    """A non-``dict`` object that quacks like one.

    Generated as a ``text`` value to pin the ``isinstance(text, dict)`` half of
    Property 3 on the only implementation detail that matters: the
    classification must *type check* ``text`` and stop, never duck-type it.
    Both trap doors below turn a classifier that reached for ``text.get(...)``
    or compared ``text`` by equality into a failing example instead of a
    silently passing one.
    """

    def get(self, key, default=None):  # pragma: no cover - must never run
        raise AssertionError(
            "`_is_meta_auth_error` must type check `text` with isinstance, "
            "not duck-type it via .get()"
        )

    def __eq__(self, other):  # pragma: no cover - must never run
        raise AssertionError(
            "`_is_meta_auth_error` must not compare a non-dict `text` by "
            "equality"
        )

    __hash__ = None

    def __repr__(self):
        return "_DictImpostor()"


# Marker-ish values for the `code`/`error_subcode` keys of a generated Meta
# error dict. The two real markers of Requirement 5.6 (`31`, `3858385`) sit
# next to near misses that a sloppy comparison would confuse with them: the
# string `'31'`, the bool `True` (which `== 1` in Python), Meta's generic OAuth
# `190`, `None`, and a nested dict where a scalar was expected.
_MARKER_LIKE_VALUES = st.sampled_from(
    (31, 3858385, "31", True, 190, 0, None, {"code": 31})
)


# A Meta-shaped error dict: any subset of `code`/`error_subcode`/`message`,
# the empty dict included. `st.fixed_dictionaries(optional=...)` is what makes
# "key absent" as reachable as "key present with a marker-like value", which
# is the distinction the classification's two `.get()` calls must absorb.
_META_ERROR_DICTS = st.fixed_dictionaries(
    {},
    optional={
        "code": _MARKER_LIKE_VALUES,
        "error_subcode": _MARKER_LIKE_VALUES,
        "message": st.text(max_size=8),
    },
)


# Every non-`dict` shape Property 3 enumerates -- `str`, `None`, `list`,
# numeric -- plus an arbitrary object, a bare `object()`, a tuple and a bool,
# so the "SHALL return False for every text that is not a dict instance" half
# is exercised across the whole non-dict domain rather than on one token type.
_NON_DICT_TEXTS = st.one_of(
    st.none(),
    st.text(max_size=20),
    st.integers(),
    st.floats(allow_nan=True, allow_infinity=True),
    st.booleans(),
    st.lists(st.integers(), max_size=3),
    st.tuples(st.integers()),
    st.builds(object),
    st.builds(_DictImpostor),
)


# A `dict` `text`: a flat Meta error dict, optionally carrying a nested
# `error` key whose value is itself either a Meta error dict (the outer shape
# `RESTClientException(response.json())` produces) or *any* non-dict value, so
# the nested-candidate branch is fed malformed payloads too.
_DICT_TEXTS = st.builds(
    lambda flat, nested: (
        flat if nested is ABSENT else {**flat, "error": nested}
    ),
    flat=_META_ERROR_DICTS,
    nested=st.one_of(st.just(ABSENT), _META_ERROR_DICTS, _NON_DICT_TEXTS),
)


# Any `text` value at all: dict shapes and non-dict shapes, drawn with
# comparable weight so neither half of the property starves.
_ANY_TEXT_VALUES = st.one_of(_DICT_TEXTS, _NON_DICT_TEXTS)


# Exception classes used as carriers of a `text` attribute. `RESTClientException`
# is the real production carrier (raised by `_publish_campaign`,
# `_publish_adset`, `_publish_ad_creative` and `_publish_ad`); the builtins are
# there because the classification must not assume any particular exception
# type, only the attribute.
_TEXT_CARRIER_CLASSES = (RESTClientException, SinergiaException, ValueError,
                         RuntimeError, KeyError)


# Exception classes that carry no `text` attribute whatsoever -- the
# Requirement 5.4 family: the `KeyError` `_publish_media` can raise per
# Requirement 4.3, plus the `AttributeError`/`TypeError`/network-style
# exceptions a failing publish can surface.
_TEXTLESS_EXCEPTION_CLASSES = (KeyError, AttributeError, TypeError, ValueError,
                               RuntimeError, ZeroDivisionError, Exception)


def _build_text_carrier(exception_class, text):
    """Return a fresh ``exception_class`` instance whose ``text`` attribute
    holds exactly ``text``.

    ``text`` is assigned *after* construction on purpose. ``SinergiaException``
    (and therefore ``RESTClientException``) resolves a missing ``text`` through
    ``gettext``, and its ``if text == None`` guard would itself blow up on the
    ``_DictImpostor`` this property needs to generate; assigning the attribute
    directly keeps the fixture honest -- the classification reads an attribute,
    and that is precisely what is being set -- without dragging a Flask/Babel
    context into a pure unit test.
    """
    if exception_class is RESTClientException:
        exception = exception_class({"placeholder": True})
    elif exception_class is SinergiaException:
        exception = exception_class("AIR001", "placeholder")
    else:
        exception = exception_class("boom")

    exception.text = text

    return exception


@st.composite
def _classifiable_exceptions(draw):
    """Draw an exception for ``_is_meta_auth_error`` together with the ``text``
    datum it was built from.

    Returns the pair ``(exception, text)``, where ``text`` is the ``ABSENT``
    sentinel when the exception carries no ``text`` attribute at all. The
    expected outcome is derived from that returned datum rather than from
    re-reading ``exception.text`` inside the test, so the property never
    restates the implementation's own ``getattr(exception, 'text', None)``.
    """
    if draw(st.booleans()):
        exception_class = draw(st.sampled_from(_TEXTLESS_EXCEPTION_CLASSES))
        exception = exception_class("boom")
        # The Requirement 5.4 family must really be attribute-less, otherwise
        # this branch would quietly stop testing anything.
        assert not hasattr(exception, "text")

        return exception, ABSENT

    exception_class = draw(st.sampled_from(_TEXT_CARRIER_CLASSES))
    text = draw(_ANY_TEXT_VALUES)

    return _build_text_carrier(exception_class, text), text


class TestIsMetaAuthErrorProperty:
    """Optional property-based coverage of the exception classification
    (``design.md`` -> Correctness Properties -> Property 3).
    """

    # Feature: meta-ads-standard-launch-campaign, Property 3: La clasificacion
    # de la excepcion es total y nunca produce una excepcion secundaria
    @settings(
        max_examples=100,
        deadline=None,
        # No fixture is requested by this test, but the module-level `autouse`
        # `deny_network` guard is function scoped and therefore visible to
        # Hypothesis all the same. Same suppression already used by the
        # Property 1 and Property 2 classes above.
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(payload=_classifiable_exceptions())
    def test_property_classification_is_total_and_never_raises(self, payload):
        """For every captured exception -- with a ``text`` attribute of any
        type (``dict``, ``str``, ``None``, ``list``, numeric, or an arbitrary
        object) or with no ``text`` attribute at all --
        ``_is_meta_auth_error`` returns a boolean without raising, and returns
        ``False`` for every ``text`` that is not a ``dict`` instance.

        No ``pytest.raises`` wrapper is needed for the totality half: any
        exception escaping the call propagates out of the test body and fails
        the example, which is exactly what pins Requirements 5.3 and 5.5 --
        the safe ``getattr(exception, 'text', None)`` plus the
        ``isinstance(text, dict)`` type check must absorb every generated
        shape instead of letting an ``AttributeError``/``TypeError`` through
        while the original publishing failure is still being handled.

        The result is asserted to be one of the two singleton ``bool`` objects
        rather than merely truthy or falsy: the ``except`` block feeds it
        straight into an ``if``, so a truthy non-boolean would be an
        implementation leak the caller could not rely on.

        This property is deliberately silent about *which* dicts classify as
        authentication errors -- that is Requirement 5.6, pinned by example in
        ``TestMetaAuthErrorClassification`` above. Here the dict branch only
        has to answer with a boolean and stay quiet.

        Validates: Requirements 5.3, 5.4, 5.5
        """
        exception, text = payload

        result = FacebookLaunchCampaignUseCase._is_meta_auth_error(exception)

        # Requirement 5.3: a boolean, always, and never a secondary exception.
        assert result is True or result is False, (
            f"classification returned {result!r}, expected a bool"
        )

        # Requirements 5.4 and 5.5: no `text` attribute at all (`ABSENT`), or a
        # `text` that is not a dict, is not an authentication error.
        if text is ABSENT or not isinstance(text, dict):
            assert result is False, (
                f"a non-dict text ({text!r}) must never classify as a Meta "
                "authentication error"
            )


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions: Payload_AdSet (task 10.3, Property 13)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock  # noqa: E402

from app.exceptions.base import ParametersNotFoundException  # noqa: E402
from app.v2.use_cases.facebook_validator_service import (  # noqa: E402
    LEADS_ALLOWED_CONVERSION_EVENTS,
)

_LEADS_OFFSITE_EVENTS = sorted(LEADS_ALLOWED_CONVERSION_EVENTS)

# Blank per Requirement 11.1: key absent, None, "" or whitespace-only.
_blank_values = st.one_of(
    st.just(ABSENT),
    st.none(),
    st.just(""),
    st.text(alphabet=" \t\n\r", min_size=1, max_size=5),
)
_non_blank_text = st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != "")
_pixel_values = st.one_of(
    st.tuples(st.just("blank"), _blank_values),
    st.tuples(st.just("valid"), _non_blank_text),
)
_event_values = st.one_of(
    st.tuples(st.just("blank"), _blank_values),
    # Not in Eventos_Conversion_Leads (exact comparison: lowercase/padded too).
    st.tuples(
        st.just("invalid"),
        st.one_of(
            _non_blank_text,
            st.sampled_from(["PURCHASE", "ADD_TO_CART", "VIEW_CONTENT"]),
            st.sampled_from(_LEADS_OFFSITE_EVENTS).map(str.lower),
            st.sampled_from(_LEADS_OFFSITE_EVENTS).map(lambda e: f" {e} "),
        ).filter(lambda s: s not in LEADS_ALLOWED_CONVERSION_EVENTS),
    ),
    st.tuples(st.just("valid"), st.sampled_from(_LEADS_OFFSITE_EVENTS)),
)
# Noisy `promoted_object` in the ad set's channel_creative; must be ignored.
_noisy_promoted_object = st.one_of(
    st.just(ABSENT),
    st.none(),
    st.fixed_dictionaries(
        {},
        optional={
            "pixel_id": st.one_of(st.none(), st.text(max_size=10)),
            "custom_event_type": st.one_of(
                st.none(), st.sampled_from(["PURCHASE", "LEAD", "CONTACT"]), st.text(max_size=10)
            ),
            "page_id": st.one_of(st.none(), st.text(max_size=10)),
            "application_id": st.text(max_size=10),
        },
    ),
)


class TestLeadsOffsiteAdsetPayload:
    """Property 13 over the real ``_publish_adset`` with ``requests.post`` and
    ``_get_account_details`` patched; state loaded through the real
    ``_get_campaign_setup``."""

    # Feature: meta-ads-leads-offsite-conversions, Property 13: Payload_AdSet de Combinación_Leads_Offsite — blanco/inválido lanza ParametersNotFoundException sin POST; válido envía un único POST con WEBSITE, OFFSITE_CONVERSIONS, IMPRESSIONS y promoted_object exacto del Campaign_Setup
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        pixel=_pixel_values,
        event=_event_values,
        promoted_object=_noisy_promoted_object,
        mode=st.sampled_from([CreativeType.DYNAMIC.value, CreativeType.STANDARD.value]),
    )
    def test_leads_offsite_adset_payload(
        self, use_case_factory, pixel, event, promoted_object, mode
    ):
        """**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.7, 11.9**"""
        pixel_kind, pixel_value = pixel
        event_kind, event_value = event

        use_case, _, mock_publish_repo, _ = use_case_factory()
        mock_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_campaign_mode=mode,
                attributes=_merge(
                    {
                        "meta_account_id": "1234567890",
                        "meta_campaign_mode": mode,
                        "meta_campaign_objective": "OUTCOME_LEADS",
                        "meta_optimization_goal": "OFFSITE_CONVERSIONS",
                        "meta_lead_form_id": "form-1",
                        "meta_whatsapp_id": None,
                        "meta_page_id": "page-1",
                    },
                    {
                        "meta_pixel_id": pixel_value,
                        "meta_conversion_event": event_value,
                    },
                ),
            )
        )
        use_case._get_campaign_setup()

        adset = make_ad_set_to_publish(
            campaign_id="meta-campaign-1",
            promoted_object=promoted_object,
        )

        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "meta-adset-1"}

        with patch.object(
            use_case, "_get_account_details", return_value={"currency": "USD"}
        ), patch(
            "app.v2.use_cases.meta_ads.requests.post", return_value=response
        ) as mock_post:
            should_fail = pixel_kind == "blank" or event_kind != "valid"
            if should_fail:
                with pytest.raises(ParametersNotFoundException) as exc_info:
                    use_case._publish_adset(adset, ACCESS_TOKEN)
                assert exc_info.value.code == "PAR001"
                # Message identifies the offending field (11.5) / invalid event (11.9).
                if pixel_kind == "blank":
                    assert "meta_pixel_id" in exc_info.value.text
                else:
                    assert "meta_conversion_event" in exc_info.value.text
                mock_post.assert_not_called()
                return

            adset_id = use_case._publish_adset(adset, ACCESS_TOKEN)

        assert adset_id == "meta-adset-1"
        assert mock_post.call_count == 1
        payload = mock_post.call_args.kwargs["json"]
        assert payload["destination_type"] == "WEBSITE"
        assert payload["optimization_goal"] == "OFFSITE_CONVERSIONS"
        assert payload["billing_event"] == "IMPRESSIONS"
        assert payload["promoted_object"] == {
            "pixel_id": pixel_value,
            "custom_event_type": event_value,
        }
        assert "page_id" not in payload["promoted_object"]


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions: Payload_Ad (task 10.5, Property 14)
# ---------------------------------------------------------------------------

_KNOWN_OBJECTIVES = [
    "OUTCOME_LEADS",
    "OUTCOME_SALES",
    "OUTCOME_TRAFFIC",
    "OUTCOME_AWARENESS",
    "OUTCOME_ENGAGEMENT",
    "OUTCOME_APP_PROMOTION",
]
_KNOWN_GOALS = [
    "OFFSITE_CONVERSIONS",
    "LEAD_GENERATION",
    "CONVERSATIONS",
    "LINK_CLICKS",
    "VALUE",
    "REACH",
    "IMPRESSIONS",
    "LANDING_PAGE_VIEWS",
]
# Arbitrary combination; the Leads_Offsite pair is drawn explicitly often enough
# and near-misses (lowercase / padded) must NOT count as Leads_Offsite.
_ad_combinations = st.one_of(
    st.just(("OUTCOME_LEADS", "OFFSITE_CONVERSIONS")),
    st.tuples(
        st.one_of(
            st.none(),
            st.sampled_from(_KNOWN_OBJECTIVES),
            st.sampled_from(_KNOWN_OBJECTIVES).map(str.lower),
            st.text(max_size=15),
        ),
        st.one_of(
            st.none(),
            st.sampled_from(_KNOWN_GOALS),
            st.sampled_from(_KNOWN_GOALS).map(lambda g: f" {g}"),
            st.text(max_size=15),
        ),
    ),
)


class TestLeadsOffsiteAdPayload:
    """Property 14 over the real ``_publish_ad`` with ``requests.post``
    patched; state loaded through the real ``_get_campaign_setup``."""

    # Feature: meta-ads-leads-offsite-conversions, Property 14: tracking_specs en Payload_Ad solo para Combinación_Leads_Offsite — name, adset_id, creative, status y access_token se conservan; tracking_specs == [{"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}] si y solo si la combinación es OUTCOME_LEADS + OFFSITE_CONVERSIONS
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        combination=_ad_combinations,
        pixel=_non_blank_text,
        ad_name=st.text(max_size=20),
        creative_id=st.text(min_size=1, max_size=20),
        status=st.sampled_from(["PAUSED", "ACTIVE"]),
    )
    def test_tracking_specs_only_for_leads_offsite(
        self, use_case_factory, combination, pixel, ad_name, creative_id, status
    ):
        """**Validates: Requirements 12.1, 12.2, 12.4**"""
        objective, goal = combination
        use_case, _, mock_publish_repo, _ = use_case_factory()
        mock_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                attributes={
                    "meta_account_id": "1234567890",
                    "meta_campaign_mode": CreativeType.STANDARD.value,
                    "meta_campaign_objective": objective,
                    "meta_optimization_goal": goal,
                    "meta_lead_form_id": None,
                    "meta_whatsapp_id": None,
                    "meta_page_id": "page-1",
                    "meta_pixel_id": pixel,
                    "meta_conversion_event": "LEAD",
                },
            )
        )
        use_case._get_campaign_setup()

        ad = {
            "name": ad_name,
            "adset_id": "meta-adset-1",
            "creative": {"creative_id": creative_id},
            "status": status,
        }
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "meta-ad-1"}

        with patch(
            "app.v2.use_cases.meta_ads.requests.post", return_value=response
        ) as mock_post:
            ad_id = use_case._publish_ad(ad, ACCESS_TOKEN)

        assert ad_id == "meta-ad-1"
        assert mock_post.call_count == 1
        payload = mock_post.call_args.kwargs["json"]

        # Requirement 12.2: pre-existing keys preserved with their values.
        assert payload["name"] == ad_name
        assert payload["adset_id"] == "meta-adset-1"
        assert payload["creative"] == {"creative_id": creative_id}
        assert payload["status"] == status
        assert payload["access_token"] == ACCESS_TOKEN

        is_leads_offsite = (
            objective == "OUTCOME_LEADS" and goal == "OFFSITE_CONVERSIONS"
        )
        if is_leads_offsite:
            # Requirement 12.1: exactly one spec with exactly the Campaign_Setup pixel.
            assert payload["tracking_specs"] == [
                {"action.type": ["offsite_conversion"], "fb_pixel": [pixel]}
            ]
            assert set(payload) == {
                "name", "adset_id", "creative", "status", "access_token", "tracking_specs"
            }
        else:
            # Requirement 12.4: no tracking_specs for Otras_Combinaciones.
            assert "tracking_specs" not in payload
            assert set(payload) == {
                "name", "adset_id", "creative", "status", "access_token"
            }


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions: creative builders (task 10.6, Property 15)
# ---------------------------------------------------------------------------

_lead_gen_form_ids = st.one_of(st.none(), st.text(max_size=20))
_cta_types = st.one_of(
    st.sampled_from(["LEARN_MORE", "SIGN_UP", "APPLY_NOW", "GET_QUOTE", "CONTACT_US"]),
    st.text(max_size=15),
)
# Arbitrary CTA `value` coming from the creative (never a lead form / WhatsApp
# destination itself, so any such key in the output can only be injected).
_cta_values = st.one_of(
    st.just(ABSENT),
    st.dictionaries(
        st.sampled_from(["link", "link_caption", "link_format"]),
        st.text(max_size=20),
        max_size=3,
    ),
)
_extra_link_data_keys = st.dictionaries(
    st.sampled_from(["image_url", "picture", "caption", "foo"]),
    st.text(max_size=10),
    max_size=2,
)


@st.composite
def _leads_offsite_link_data(draw):
    """Draw an arbitrary STANDARD ``link_data`` with CTA and ``link``."""
    cta_value = draw(_cta_values)
    call_to_action = _merge({"type": {"value": draw(_cta_types)}}, {"value": cta_value})
    link_data = {
        "link": draw(st.text(max_size=40)),
        "call_to_action": call_to_action,
        **draw(_extra_link_data_keys),
    }
    for key in ("message", "name", "description", "image_hash"):
        if draw(st.booleans()):
            link_data[key] = draw(st.text(max_size=20))
    return link_data


_leads_offsite_asset_feed_specs = st.fixed_dictionaries(
    {
        "call_to_action_types": st.lists(
            st.fixed_dictionaries({"value": _cta_types}), max_size=3
        ),
        "link_urls": st.lists(
            st.fixed_dictionaries(
                {"website_url": st.one_of(st.none(), st.text(max_size=30))}
            ),
            max_size=2,
        ),
    },
    optional={
        "bodies": st.lists(st.fixed_dictionaries({"text": st.text(max_size=10)}), max_size=2),
        "titles": st.lists(st.fixed_dictionaries({"text": st.text(max_size=10)}), max_size=2),
        "descriptions": st.lists(
            st.fixed_dictionaries({"text": st.text(max_size=10)}), max_size=2
        ),
        "ad_formats": st.lists(
            st.sampled_from(["SINGLE_IMAGE", "CAROUSEL", "AUTOMATIC_FORMAT"]), max_size=2
        ),
        "images": st.lists(st.fixed_dictionaries({"hash": st.text(max_size=10)}), max_size=2),
    },
)


class TestLeadsOffsiteCreativeBuilders:
    """Property 15 over the real ``_build_object_story_spec`` and
    ``_build_asset_feed_spec``; state loaded through the real
    ``_get_campaign_setup``."""

    @staticmethod
    def _leads_offsite_use_case(use_case_factory, mode):
        use_case, _, mock_publish_repo, _ = use_case_factory()
        mock_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_campaign_mode=mode,
                attributes={
                    "meta_account_id": "1234567890",
                    "meta_campaign_mode": mode,
                    "meta_campaign_objective": "OUTCOME_LEADS",
                    "meta_optimization_goal": "OFFSITE_CONVERSIONS",
                    "meta_lead_form_id": "form-1",
                    "meta_whatsapp_id": None,
                    "meta_page_id": "page-1",
                    "meta_pixel_id": "pixel-1",
                    "meta_conversion_event": "LEAD",
                },
            )
        )
        use_case._get_campaign_setup()
        return use_case

    # Feature: meta-ads-leads-offsite-conversions, Property 15: El creativo de Combinación_Leads_Offsite no se convierte en lead form — _build_object_story_spec conserva link y call_to_action == {'type': type.value, 'value': value o {}} sin lead_gen_form_id ni app_destination; _build_asset_feed_spec no agrega call_to_actions
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        lead_gen_form_id=_lead_gen_form_ids,
        link_data=_leads_offsite_link_data(),
        asset_feed_spec=_leads_offsite_asset_feed_specs,
        page_id=st.text(max_size=15),
    )
    def test_leads_offsite_creative_is_not_a_lead_form(
        self, use_case_factory, lead_gen_form_id, link_data, asset_feed_spec, page_id
    ):
        """**Validates: Requirements 12.5**"""
        # STANDARD: object_story_spec.link_data
        use_case = self._leads_offsite_use_case(use_case_factory, CreativeType.STANDARD.value)
        input_cta = link_data["call_to_action"]
        expected_cta = {
            "type": input_cta["type"]["value"],
            "value": input_cta.get("value", {}),
        }

        result = use_case._build_object_story_spec(
            {"page_id": page_id, "link_data": link_data}, lead_gen_form_id
        )

        assert result["page_id"] == page_id
        out_link_data = result["link_data"]
        assert out_link_data["link"] == link_data["link"]
        assert out_link_data["call_to_action"] == expected_cta
        assert "lead_gen_form_id" not in out_link_data["call_to_action"]["value"]
        assert "app_destination" not in out_link_data["call_to_action"]["value"]
        assert out_link_data["call_to_action"]["type"] != "WHATSAPP_MESSAGE" or (
            input_cta["type"]["value"] == "WHATSAPP_MESSAGE"
        )

        # DYNAMIC: asset_feed_spec
        use_case = self._leads_offsite_use_case(use_case_factory, CreativeType.DYNAMIC.value)
        feed = use_case._build_asset_feed_spec(asset_feed_spec, lead_gen_form_id)

        assert "call_to_actions" not in feed
        assert feed["call_to_action_types"] == [
            c["value"] for c in asset_feed_spec["call_to_action_types"]
        ]
        assert feed["link_urls"] == asset_feed_spec["link_urls"]
        assert feed["ad_formats"] == asset_feed_spec.get("ad_formats", [])


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions: Launch happy paths and rollback (task 10.7)
# ---------------------------------------------------------------------------

_LO_PIXEL_ID = "pixel-123"
_LO_CONVERSION_EVENT = "LEAD"


def _leads_offsite_campaign_setup(mode, **attribute_overrides):
    """Campaign_Setup for Combinación_Leads_Offsite; ``attribute_overrides``
    replace ``meta_pixel_id`` / ``meta_conversion_event`` (``ABSENT`` omits)."""
    attributes = _merge(
        {
            "meta_account_id": "1234567890",
            "meta_campaign_mode": mode,
            "meta_campaign_objective": "OUTCOME_LEADS",
            "meta_optimization_goal": "OFFSITE_CONVERSIONS",
            "meta_lead_form_id": "form-1",
            "meta_whatsapp_id": None,
            "meta_page_id": "page-1",
            "meta_pixel_id": _LO_PIXEL_ID,
            "meta_conversion_event": _LO_CONVERSION_EVENT,
        },
        attribute_overrides,
    )
    return make_campaign_setup(meta_campaign_mode=mode, attributes=attributes)


def _leads_offsite_ad_set(mode, ad_count=1):
    """Fully valid Ad_Set_a_Publicar with ``ad_count`` ads, carrying a noisy
    ``promoted_object`` and a ``lead_gen_form_id`` that must both be ignored."""
    if mode == CreativeType.DYNAMIC.value:
        def _creative():
            return make_ad_creative(
                object_story_spec={"page_id": "page-1"},
                asset_feed_spec=make_dynamic_asset_feed_spec(),
            )
    else:
        def _creative():
            return make_ad_creative(object_story_spec=make_standard_object_story_spec())

    return make_ad_set_to_publish(
        name="Ad set 1",
        adset_id="adset-1",
        optimization_goal="OFFSITE_CONVERSIONS",
        promoted_object={"page_id": "page-noise", "pixel_id": "noise", "custom_event_type": "PURCHASE"},
        lead_gen_form_id="form-adset",
        ads=[make_ad(ad_id=f"ad-{i}", ad_creative=_creative()) for i in range(1, ad_count + 1)],
    )


def _graph_post_double():
    """``requests.post`` double answering 200 with a fresh id per endpoint."""
    counter = itertools.count(1)

    def _post(url, json=None, headers=None, **kwargs):
        response = MagicMock()
        response.status_code = 200
        kind = url.rsplit("/", 1)[-1]
        response.json.return_value = {"id": f"meta-{kind}-{next(counter)}"}
        return response

    return MagicMock(side_effect=_post)


def _posted_payloads(mock_post, endpoint):
    return [
        c.kwargs["json"] for c in mock_post.call_args_list
        if c.args[0].endswith(f"/{endpoint}")
    ]


_MODES = [CreativeType.DYNAMIC.value, CreativeType.STANDARD.value]


class TestLeadsOffsiteLaunchRollback:
    """``execute()`` for Combinación_Leads_Offsite via ``launch_scenario`` with
    the real ``_publish_adset`` (and, in the happy paths, the real
    ``_publish_ad_creative`` / ``_publish_ad``); only ``requests.post`` and
    ``_get_account_details`` are replaced at the HTTP boundary."""

    @staticmethod
    def _use_real(scenario, *method_names):
        """Route the patched doubles to the real methods, keeping them as spies."""
        for name in method_names:
            real = getattr(FacebookLaunchCampaignUseCase, name)
            scenario.mocks[name].side_effect = (
                lambda *args, _real=real, **kwargs: _real(scenario.use_case, *args, **kwargs)
            )

    @pytest.mark.parametrize("mode", _MODES)
    @pytest.mark.parametrize("blank_value", [None, ""])
    @pytest.mark.parametrize("field", ["meta_pixel_id", "meta_conversion_event"])
    def test_blank_setup_field_raises_and_rolls_back(
        self, use_case_factory, field, blank_value, mode
    ):
        """**Validates: Requirements 11.6, 12.6, 14.11**"""
        with launch_scenario(
            use_case_factory,
            ad_sets=[_leads_offsite_ad_set(mode)],
            campaign_mode=mode,
        ) as scenario:
            scenario.campaign_publish_repository.get_by_campaign_id_and_channel_id.return_value = (
                _leads_offsite_campaign_setup(mode, **{field: blank_value})
            )
            self._use_real(scenario, "_publish_adset")
            use_case = scenario.use_case

            with patch.object(
                use_case, "_rollback_publish", wraps=use_case._rollback_publish
            ) as spy_rollback, patch.object(
                use_case, "_get_account_details", return_value={"currency": "USD"}
            ), patch(
                "app.v2.use_cases.meta_ads.requests.post", _graph_post_double()
            ) as mock_post:
                with pytest.raises(ParametersNotFoundException) as exc_info:
                    use_case.execute()

            assert exc_info.value.code == "PAR001"
            assert field in exc_info.value.text

            # The real `_publish_adset` ran and failed before its POST.
            assert scenario.mocks["_publish_adset"].call_count == 1
            mock_post.assert_not_called()

            # Rollback exactly once over the created campaign (no creatives yet).
            spy_rollback.assert_called_once_with(META_CAMPAIGN_ID, [], ACCESS_TOKEN)
            assert scenario.mock_delete_object.call_args_list == [
                call(META_CAMPAIGN_ID, ACCESS_TOKEN)
            ]

            # Requirement 12.6: no Payload_Ad is ever sent.
            scenario.mocks["_publish_ad"].assert_not_called()
            scenario.mocks["_publish_ad_creative"].assert_not_called()
            assert _posted_payloads(mock_post, "ads") == []
            scenario.mock_update_campaign_setup.assert_not_called()

    @pytest.mark.parametrize("mode", _MODES)
    def test_happy_path_publishes_website_adset_and_tracked_ads(
        self, use_case_factory, mode
    ):
        """**Validates: Requirements 12.3, 14.10**"""
        with launch_scenario(
            use_case_factory,
            ad_sets=[_leads_offsite_ad_set(mode, ad_count=2)],
            campaign_mode=mode,
        ) as scenario:
            scenario.campaign_publish_repository.get_by_campaign_id_and_channel_id.return_value = (
                _leads_offsite_campaign_setup(mode)
            )
            self._use_real(scenario, "_publish_adset", "_publish_ad_creative", "_publish_ad")
            use_case = scenario.use_case

            with patch.object(
                use_case, "_rollback_publish", wraps=use_case._rollback_publish
            ) as spy_rollback, patch.object(
                use_case, "_get_account_details", return_value={"currency": "USD"}
            ), patch(
                "app.v2.use_cases.meta_ads.requests.post", _graph_post_double()
            ) as mock_post:
                use_case.execute()

            spy_rollback.assert_not_called()
            scenario.mock_delete_object.assert_not_called()
            scenario.mock_update_campaign_setup.assert_called_once()

            adset_payloads = _posted_payloads(mock_post, "adsets")
            assert len(adset_payloads) == 1
            adset_payload = adset_payloads[0]
            assert adset_payload["destination_type"] == "WEBSITE"
            assert adset_payload["optimization_goal"] == "OFFSITE_CONVERSIONS"
            assert adset_payload["billing_event"] == "IMPRESSIONS"
            assert adset_payload["promoted_object"] == {
                "pixel_id": _LO_PIXEL_ID,
                "custom_event_type": _LO_CONVERSION_EVENT,
            }

            ad_payloads = _posted_payloads(mock_post, "ads")
            assert len(ad_payloads) == 2
            for ad_payload in ad_payloads:
                assert ad_payload["tracking_specs"] == [
                    {"action.type": ["offsite_conversion"], "fb_pixel": [_LO_PIXEL_ID]}
                ]

            # The creatives never become lead forms (guard in the builders).
            creative_payloads = _posted_payloads(mock_post, "adcreatives")
            assert len(creative_payloads) == 2
            for creative_payload in creative_payloads:
                assert "lead_gen_form_id" not in str(creative_payload)
                assert "call_to_actions" not in creative_payload.get("asset_feed_spec", {})


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions: payload regression for
# Otras_Combinaciones (task 11.1)
# ---------------------------------------------------------------------------

from app.v2.use_cases.meta_ads import _get_meta_currency_offset  # noqa: E402

# Leads_Offsite-only Campaign_Setup values present as noise: none of them may
# leak into the payloads of Otras_Combinaciones (SALES keeps its own pixel rule).
_REG_SETUP_PIXEL = "pixel-setup"
_REG_SETUP_EVENT = "LEAD"
_REG_ADSET_FORM = "form-adset"
_REG_SETUP_FORM = "form-setup"
_REG_TARGETING = {"geo_locations": {"countries": ["ES"]}, "age_max": 65}

_LEAD_FORM_CTA = "lead_form"
_WHATSAPP_CTA = "whatsapp"
_PLAIN_CTA = "plain"

# (objective, goal, ad set overrides, Campaign_Setup overrides,
#  expected promoted_object (ABSENT = key omitted), expected destination_type
#  (ABSENT = key omitted), expected targeting, creative CTA kind, form id)
_REGRESSION_CASES = [
    pytest.param(
        "OUTCOME_LEADS", "LEAD_GENERATION",
        {"promoted_object": {"page_id": "page-adset"}, "lead_gen_form_id": _REG_ADSET_FORM},
        {"meta_lead_form_id": _REG_SETUP_FORM},
        {"page_id": "page-adset"}, "ON_AD",
        {**_REG_TARGETING, "targeting_automation": {"advantage_audience": 0}},
        _LEAD_FORM_CTA, _REG_ADSET_FORM,
        id="leads-lead_generation",
    ),
    pytest.param(
        "OUTCOME_LEADS", "LEAD_GENERATION",
        {"promoted_object": ABSENT},
        {"meta_lead_form_id": _REG_SETUP_FORM},
        # page_id falls back to meta_page_id of the Campaign_Setup (Req 11.8).
        {"page_id": "page-1"}, "ON_AD",
        {**_REG_TARGETING, "targeting_automation": {"advantage_audience": 0}},
        _LEAD_FORM_CTA, _REG_SETUP_FORM,
        id="leads-lead_generation-page_fallback",
    ),
    pytest.param(
        "OUTCOME_LEADS", "CONVERSATIONS",
        {"promoted_object": {"page_id": "page-adset"}},
        {"meta_lead_form_id": None, "meta_whatsapp_id": "wa-1"},
        {"page_id": "page-adset"}, "WHATSAPP",
        # advantage_audience = 1 and age_max removed (Req 11.10).
        {"geo_locations": {"countries": ["ES"]}, "targeting_automation": {"advantage_audience": 1}},
        _WHATSAPP_CTA, None,
        id="leads-conversations",
    ),
    pytest.param(
        "OUTCOME_SALES", "OFFSITE_CONVERSIONS",
        {"promoted_object": ABSENT},
        {},
        # Pixel from the Campaign_Setup, PURCHASE by default; meta_conversion_event ignored.
        {"pixel_id": _REG_SETUP_PIXEL, "custom_event_type": "PURCHASE"}, ABSENT,
        {**_REG_TARGETING, "targeting_automation": {"advantage_audience": 0}},
        _PLAIN_CTA, None,
        id="sales-offsite_conversions",
    ),
    pytest.param(
        "OUTCOME_SALES", "OFFSITE_CONVERSIONS",
        {"promoted_object": {"pixel_id": "pixel-adset"}},
        {},
        # Ad set pixel wins over the Campaign_Setup one (pre-existing precedence).
        {"pixel_id": "pixel-adset", "custom_event_type": "PURCHASE"}, ABSENT,
        {**_REG_TARGETING, "targeting_automation": {"advantage_audience": 0}},
        _PLAIN_CTA, None,
        id="sales-offsite_conversions-adset_pixel",
    ),
    pytest.param(
        "OUTCOME_AWARENESS", "REACH",
        {"promoted_object": {"page_id": "page-adset"}},
        {},
        ABSENT, ABSENT,
        {**_REG_TARGETING, "targeting_automation": {"advantage_audience": 0}},
        _PLAIN_CTA, None,
        id="awareness-reach",
    ),
]


def _regression_campaign_setup(mode, objective, goal, **attribute_overrides):
    attributes = _merge(
        {
            "meta_account_id": "1234567890",
            "meta_campaign_mode": mode,
            "meta_campaign_objective": objective,
            "meta_optimization_goal": goal,
            "meta_lead_form_id": None,
            "meta_whatsapp_id": None,
            "meta_page_id": "page-1",
            "meta_pixel_id": _REG_SETUP_PIXEL,
            "meta_conversion_event": _REG_SETUP_EVENT,
        },
        attribute_overrides,
    )
    return make_campaign_setup(meta_campaign_mode=mode, attributes=attributes)


def _regression_ad_set(mode, goal, ad_count=2, **overrides):
    if mode == CreativeType.DYNAMIC.value:
        def _creative():
            return make_ad_creative(
                object_story_spec={"page_id": "page-1"},
                asset_feed_spec=make_dynamic_asset_feed_spec(),
            )
    else:
        def _creative():
            return make_ad_creative(object_story_spec=make_standard_object_story_spec())

    return make_ad_set_to_publish(
        name="Ad set 1",
        adset_id="adset-1",
        optimization_goal=goal,
        targeting={"geo_locations": {"countries": ["ES"]}, "age_max": 65},
        ads=[make_ad(ad_id=f"ad-{i}", ad_creative=_creative()) for i in range(1, ad_count + 1)],
        **overrides,
    )


def _expected_cta(kind, form_id, cta_type="SHOP_NOW"):
    if kind == _LEAD_FORM_CTA:
        return {"type": cta_type, "value": {"lead_gen_form_id": form_id}}
    if kind == _WHATSAPP_CTA:
        return {"type": "WHATSAPP_MESSAGE", "value": {"app_destination": "WHATSAPP"}}
    return {"type": cta_type, "value": {}}


class TestLaunchPayloadRegression:
    """Otras_Combinaciones keep the pre-existing Payload_AdSet, Payload_Ad and
    creative payloads. ``execute()`` runs through ``launch_scenario`` with the
    real ``_publish_adset`` / ``_publish_ad_creative`` / ``_publish_ad``; only
    ``requests.post`` and ``_get_account_details`` are replaced. Expected
    values are literals derived from the code prior to this spec."""

    @pytest.mark.parametrize("mode", _MODES)
    @pytest.mark.parametrize(
        "objective, goal, adset_overrides, setup_overrides, expected_promoted_object, "
        "expected_destination_type, expected_targeting, cta_kind, form_id",
        _REGRESSION_CASES,
    )
    def test_other_combinations_payloads_unchanged(
        self, use_case_factory, mode, objective, goal, adset_overrides, setup_overrides,
        expected_promoted_object, expected_destination_type, expected_targeting,
        cta_kind, form_id,
    ):
        """**Validates: Requirements 11.8, 11.10, 11.11, 13.1, 13.2, 14.12**"""
        with launch_scenario(
            use_case_factory,
            ad_sets=[_regression_ad_set(mode, goal, **adset_overrides)],
            campaign_mode=mode,
        ) as scenario:
            scenario.campaign_publish_repository.get_by_campaign_id_and_channel_id.return_value = (
                _regression_campaign_setup(mode, objective, goal, **setup_overrides)
            )
            TestLeadsOffsiteLaunchRollback._use_real(
                scenario, "_publish_adset", "_publish_ad_creative", "_publish_ad"
            )
            use_case = scenario.use_case

            with patch.object(
                use_case, "_rollback_publish", wraps=use_case._rollback_publish
            ) as spy_rollback, patch.object(
                use_case, "_get_account_details", return_value={"currency": "USD"}
            ), patch(
                "app.v2.use_cases.meta_ads.requests.post", _graph_post_double()
            ) as mock_post:
                use_case.execute()

            spy_rollback.assert_not_called()
            scenario.mock_update_campaign_setup.assert_called_once()

        is_dynamic = mode == CreativeType.DYNAMIC.value

        # --- Payload_AdSet: exact pre-existing shape -----------------------
        adset_payloads = _posted_payloads(mock_post, "adsets")
        assert len(adset_payloads) == 1
        adset_payload = dict(adset_payloads[0])
        assert {"start_time", "end_time"} <= set(adset_payload)
        adset_payload.pop("start_time")
        adset_payload.pop("end_time")
        expected_adset_payload = _merge(
            {
                "name": "Ad set 1",
                "campaign_id": META_CAMPAIGN_ID,
                "daily_budget": 100 * _get_meta_currency_offset("USD"),
                "billing_event": "IMPRESSIONS",
                "optimization_goal": goal,
                "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
                "is_dynamic_creative": is_dynamic,
                "has_dynamic_creative": is_dynamic,
                "targeting": expected_targeting,
                "status": "PAUSED",
                "access_token": ACCESS_TOKEN,
            },
            {
                "promoted_object": expected_promoted_object,
                "destination_type": expected_destination_type,
            },
        )
        assert adset_payload == expected_adset_payload
        # Leads_Offsite fields never leak into Otras_Combinaciones.
        assert adset_payload.get("destination_type") != "WEBSITE"
        if objective != "OUTCOME_SALES":
            assert _REG_SETUP_PIXEL not in str(adset_payload)
            assert "custom_event_type" not in str(adset_payload)

        # --- Payload_Ad: no tracking_specs (Req 12.4 / 13.2) ---------------
        ad_payloads = _posted_payloads(mock_post, "ads")
        assert len(ad_payloads) == 2
        creative_ids = []
        for ad_payload in ad_payloads:
            assert "tracking_specs" not in ad_payload
            assert set(ad_payload) == {"name", "adset_id", "creative", "status", "access_token"}
            assert ad_payload["adset_id"] == "meta-adsets-1"
            assert ad_payload["status"] == "PAUSED"
            assert ad_payload["access_token"] == ACCESS_TOKEN
            creative_ids.append(ad_payload["creative"]["creative_id"])
        assert [p["name"] for p in ad_payloads] == ["Ad ad-1", "Ad ad-2"]

        # --- Creative payloads: pre-existing lead form / WhatsApp injection --
        creative_payloads = _posted_payloads(mock_post, "adcreatives")
        assert len(creative_payloads) == 2
        assert len(set(creative_ids)) == 2
        for creative_payload in creative_payloads:
            if is_dynamic:
                assert creative_payload["object_story_spec"] == {"page_id": "page-1"}
                feed = creative_payload["asset_feed_spec"]
                assert feed["call_to_action_types"] == ["SHOP_NOW"]
                assert feed["link_urls"] == [{"website_url": "https://example.test/landing"}]
                if cta_kind == _LEAD_FORM_CTA:
                    assert feed["call_to_actions"] == [_expected_cta(cta_kind, form_id)]
                    assert feed["ad_formats"] == []
                elif cta_kind == _WHATSAPP_CTA:
                    assert feed["call_to_actions"] == [_expected_cta(cta_kind, form_id)]
                    assert feed["ad_formats"] == ["AUTOMATIC_FORMAT"]
                else:
                    assert "call_to_actions" not in feed
                    assert feed["ad_formats"] == []
            else:
                assert "asset_feed_spec" not in creative_payload
                assert creative_payload["object_story_spec"] == {
                    "page_id": "page-1",
                    "link_data": {
                        "link": "https://example.test/landing",
                        "message": "Standard body",
                        "name": "Standard title",
                        "description": "Standard description",
                        "call_to_action": _expected_cta(cta_kind, form_id),
                    },
                }
