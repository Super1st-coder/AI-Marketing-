"""Characterization test suite for ``FacebookSavePreCheckBudgetUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookSavePreCheckBudgetUseCase``
(its Rama_STANDARD, inline within ``execute()``) and the inherited subset of
``FacebookSavePreCheckBaseUseCase``/``FacebookGeneratePreCheckCreativeUseCase``
that it invokes: the constructor, ``_get_ad_channel``, ``_get_campaign_setup``,
``_set_channel_id``, ``_build_response``, ``_get_account_details`` and
``_get_minimum_budget``.

This module fixes the current observable behaviour, including already
existing quirks (the always-``{}`` ``complete_campaign_data`` passed to the
grandparent constructor, the mutable default ``pre_check_data: PreCheckDataDict
= {}`` in the constructor signature, and the transparent
``try/except Exception as e: raise e`` pass-through in ``execute()``). No
production code is modified or "fixed" by this suite.

Builders/fixtures below replicate, verbatim in style, the ones already used
by the sibling suites ``test_facebook_save_pre_check_texts.py``,
``test_facebook_save_pre_check_ctas.py`` and
``test_facebook_save_pre_check_images.py``.

``_get_account_details``/``_get_minimum_budget`` are inherited unchanged from
``FacebookGeneratePreCheckCreativeUseCase`` (the Caso_de_Uso_Abuelo) and, in
turn, each of them delegates to a single module-level collaborator class of
its own: ``FacebookGetAdAccountDetailsUseCase().execute(...)`` and
``FacebookMinimumBudgetUseCase().execute(...)`` respectively. Rather than
mocking ``_get_account_details``/``_get_minimum_budget`` directly on the use
case instance (which would bypass the real, already-characterized
collaborator logic those two methods implement -- error-code branching for
the former, currency matching/``/100`` conversion for the latter), this
suite mocks at the same level as
``test_facebook_generate_pre_check_creative.py`` does for the same two
methods: it patches
``app.v2.use_cases.meta_ads.FacebookGetAdAccountDetailsUseCase`` and
``app.v2.use_cases.meta_ads.FacebookMinimumBudgetUseCase`` (the two
module-level symbols ``_get_account_details``/``_get_minimum_budget``
actually reach through), via the ``patch_budget_dependencies`` context
manager below. This lets a scenario control the exact ``min_budget`` that
reaches the Rama_STANDARD logic under test (by setting
``FacebookMinimumBudgetUseCase.return_value.execute.return_value``) while
keeping ``_get_account_details``/``_get_minimum_budget`` themselves
completely real and unmocked, consistent with how the sibling
``test_facebook_save_pre_check_ctas.py``/``test_facebook_save_pre_check_texts.py``
suites mock ``AdChannelRepository``/``CampaignChannelPublishRepository`` at
the collaborator level rather than stubbing the use case's own methods.

Requirements: 8.2
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.exceptions.base import DataNotFoundException, NotAccessException
from app.v2.use_cases.facebook_validator_service import MetaAdsValidator
from app.v2.use_cases.meta_ads import (
    FacebookSavePreCheckBaseUseCase,
    FacebookSavePreCheckBudgetUseCase,
)


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it from the resulting dict" from "this key
    was provided by the caller with the value ``None``".

    Requirements: 8.2
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


def make_pre_check_budget_data(**overrides):
    """Build a fresh ``pre_check_budget_data`` (``PreCheckDataDict``-like) dict.

    Every invocation returns a brand new dict, with brand new list objects
    for every collection field; no mutable default arguments are used, so
    callers can freely mutate the returned value (or its nested lists)
    without affecting other tests.

    Requirements: 8.2
    """
    data = {
        "campaign_id": "campaign-1",
        "adset_id": "adset-1",
        "ad_id": "ad-1",
        "adchannel_id": "adchannel-1",
        "images": [],
        "bodies": [],
        "titles": [],
        "descriptions": [],
        "call_to_action_types": [],
        "daily_budget": 0,
        "proposal_url": "",
        "locations": [],
    }
    data.update(overrides)
    return data


def make_ad_channel(channel_ref_id=1, channel_creative=ABSENT, **overrides):
    """Build a fresh ``ad_channel`` dict as returned by
    ``AdChannelRepository.get_by_campaign_and_ad_channel_id``.

    ``channel_creative`` defaults to the ``ABSENT`` sentinel: when left
    untouched, the ``channel_creative`` key is omitted entirely from the
    resulting ``attributes`` dict. ``**overrides`` are merged into the
    top-level dict (not into ``attributes``), allowing callers to omit or
    replace nested keys (``attributes``, ``channel_ref``, ``data``, ``id``)
    to exercise absence scenarios individually.

    Requirements: 8.2
    """
    attributes = {"channel_ref": {"data": {"id": channel_ref_id}}}
    if channel_creative is not ABSENT:
        attributes["channel_creative"] = channel_creative
    data = {"attributes": attributes}
    data.update(overrides)
    return data


def make_campaign_setup(meta_campaign_mode="DYNAMIC", meta_account_id="act-1", **overrides):
    """Build a fresh ``campaign_setup`` dict as returned by
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``.

    Pass ``meta_campaign_mode=None`` or ``meta_campaign_mode=""`` explicitly
    to characterize unknown-mode scenarios. ``meta_account_id`` defaults to
    a non-empty value because ``execute()`` reads
    ``self.ad_account_id = campaign_setup.get('attributes', {}).get('meta_account_id')``
    before the ``try`` block, and both ``_get_account_details``/
    ``_get_minimum_budget`` use ``self.ad_account_id``. ``**overrides`` are
    merged into the top-level dict.

    Requirements: 8.2
    """
    data = {
        "attributes": {
            "meta_campaign_mode": meta_campaign_mode,
            "meta_account_id": meta_account_id,
        }
    }
    data.update(overrides)
    return data


def make_asset_feed_spec(**overrides):
    """Build a fresh ``asset_feed_spec`` dict with empty collections.

    Requirements: 8.2
    """
    data = {
        "images": [],
        "bodies": [],
        "titles": [],
        "descriptions": [],
        "call_to_action_types": [],
        "link_urls": [],
        "ad_channel_id": 0,
    }
    data.update(overrides)
    return data


def make_object_story_spec(**overrides):
    """Build a fresh ``object_story_spec`` dict.

    Empty by default; callers compose it with ``link_data=make_link_data(...)``
    when a scenario needs to assert that Caso_de_Uso_Budget's Rama_STANDARD
    (which never reads/writes ``link_data``) leaves it untouched.

    Requirements: 8.2
    """
    data = {}
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict (``object_story_spec['link_data']``).

    Every field any sibling STANDARD branch reads/writes (``name``,
    ``message``, ``description``, ``image_url``, ``link``,
    ``call_to_action``) defaults to ``None``. Caso_de_Uso_Budget's own
    Rama_STANDARD never touches ``link_data`` (it annotates exclusively on
    ``object_story_spec``/``creative``), so this builder exists here only to
    let a scenario assert that a pre-existing ``link_data`` is left
    completely untouched, consistent with the sibling suites.

    Requirements: 8.2
    """
    data = {
        "name": None,
        "message": None,
        "description": None,
        "image_url": None,
        "link": None,
        "call_to_action": None,
    }
    data.update(overrides)
    return data


def make_ad_creative(asset_feed_spec=ABSENT, object_story_spec=ABSENT, **overrides):
    """Build a fresh ``adCreative`` dict.

    ``asset_feed_spec``/``object_story_spec`` default to the private
    ``ABSENT`` sentinel: when left untouched, the corresponding key is
    omitted entirely from the returned dict, distinguishing "key omitted"
    from "key present with value ``None``".

    Requirements: 8.2
    """
    data = {}
    if asset_feed_spec is not ABSENT:
        data["asset_feed_spec"] = asset_feed_spec
    if object_story_spec is not ABSENT:
        data["object_story_spec"] = object_story_spec
    data.update(overrides)
    return data


def make_ad(ad_creative=ABSENT, ad_id="ad-1", **overrides):
    """Build a fresh ``ad`` dict.

    ``ad_creative`` defaults to the ``ABSENT`` sentinel: when left
    untouched, the ``adCreative`` key is omitted entirely from the returned
    dict. Pass ``ad_creative=None`` explicitly to include the key with
    value ``None``.

    Requirements: 8.2
    """
    data = {"id": ad_id}
    if ad_creative is not ABSENT:
        data["adCreative"] = ad_creative
    data.update(overrides)
    return data


def make_creative(name="Creative", ads=None, proposal_locations=ABSENT, **overrides):
    """Build a fresh ``creative`` dict (``ad_channel['attributes']['channel_creative']``).

    ``ads`` defaults to a brand new list containing a single fresh
    ``make_ad()`` when omitted (``None``); pass ``ads=[]`` explicitly to
    characterize an empty-``ads`` scenario. ``proposal_locations`` defaults
    to the ``ABSENT`` sentinel: when left untouched, the key is omitted
    entirely, matching the ``creative.get('proposal_locations', [])``
    default in ``_build_response``.

    Requirements: 8.2
    """
    data = {
        "name": name,
        "id": "adset-1",
        "daily_budget": 100,
        "ads": ads if ads is not None else [make_ad()],
    }
    if proposal_locations is not ABSENT:
        data["proposal_locations"] = proposal_locations
    data.update(overrides)
    return data


def make_ad_account_info(currency="USD", **overrides):
    """Build a fresh ad account info dict as returned by
    ``FacebookGetAdAccountDetailsUseCase.execute``.

    Used by ``patch_budget_dependencies`` scenarios to control the
    ``currency`` that ``_get_minimum_budget`` matches against.

    Requirements: 8.2
    """
    data = {"currency": currency}
    data.update(overrides)
    return data


def make_minimum_budget_response(currency="USD", min_daily_budget_imp=1000, **overrides):
    """Build a fresh minimum budget response of the form ``{"data": [...]}``
    as returned by ``FacebookMinimumBudgetUseCase.execute``.

    ``**overrides`` are merged into the single ``data`` entry. The real
    ``_get_minimum_budget`` divides ``min_daily_budget_imp`` by ``100``
    (cents to units), so a scenario wanting a specific ``min_budget`` value
    should pass ``min_daily_budget_imp=min_budget * 100``.

    Requirements: 8.2
    """
    entry = {
        "currency": currency,
        "min_daily_budget_imp": min_daily_budget_imp,
    }
    entry.update(overrides)
    return {"data": [entry]}


@pytest.fixture
def use_case_factory():
    """Fixture that builds a factory for ``FacebookSavePreCheckBudgetUseCase``
    instances with ``AdChannelRepository``/``CampaignChannelPublishRepository``
    substituted by test doubles.

    Each call to the returned factory patches
    ``app.v2.use_cases.meta_ads.AdChannelRepository`` and
    ``app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`` before
    constructing the use case, then returns::

        (use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance)

    Calling the factory multiple times (within the same test or across
    tests) always produces a brand new use case instance and brand new mock
    repository instances; nothing is shared between invocations.

    Note that ``FacebookGetAdAccountDetailsUseCase``/``FacebookMinimumBudgetUseCase``
    (reached only from within ``execute()``, via the inherited
    ``_get_account_details``/``_get_minimum_budget``) are deliberately NOT
    patched here: they are irrelevant to construction and are instead
    patched, per-scenario, via ``patch_budget_dependencies`` below.

    If ``pre_check_budget_data`` is omitted, a fresh
    ``make_pre_check_budget_data()`` is used so accidental constructor
    edge-case scenarios (explicit ``None``, mutable defaults) are not
    triggered here; dedicated tests for those construct the use case
    directly, without this fixture.

    Requirements: 8.2
    """

    def _factory(user_id="user-1", pre_check_budget_data=None):
        if pre_check_budget_data is None:
            pre_check_budget_data = make_pre_check_budget_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookSavePreCheckBudgetUseCase(
                user_id, pre_check_budget_data
            )
            mock_ad_channel_repo_instance = mock_ad_channel_repository_cls.return_value
            mock_campaign_publish_repo_instance = (
                mock_campaign_publish_repository_cls.return_value
            )

        return use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance

    return _factory


@contextmanager
def patch_budget_dependencies():
    """Context manager that patches
    ``app.v2.use_cases.meta_ads.FacebookGetAdAccountDetailsUseCase`` and
    ``app.v2.use_cases.meta_ads.FacebookMinimumBudgetUseCase`` -- the two
    module-level collaborator classes that the inherited
    ``_get_account_details``/``_get_minimum_budget`` methods instantiate and
    invoke -- and yields a ``SimpleNamespace``-like pair of ``MagicMock``\\ s
    exposing each under its original name, so a scenario can configure
    ``.return_value.execute.return_value`` directly, for example::

        with patch_budget_dependencies() as deps:
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(), 200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(min_daily_budget_imp=5000), 200,
            )

    This mirrors, in both name and shape, the ``patch_execute_dependencies``
    context manager already used by
    ``test_facebook_generate_pre_check_creative.py`` to control the exact
    same two collaborators for the Caso_de_Uso_Abuelo. ``_get_account_details``
    and ``_get_minimum_budget`` themselves are never mocked directly: their
    real, already-characterized logic (HTTP-status/error-code branching and
    currency-matching/cents-to-units conversion, respectively) keeps running
    unmodified, only the two Facebook Graph API-backed collaborator classes
    they depend on are replaced with test doubles.

    Requirements: 8.2
    """
    with patch(
        "app.v2.use_cases.meta_ads.FacebookGetAdAccountDetailsUseCase"
    ) as mock_get_ad_account_details_use_case, patch(
        "app.v2.use_cases.meta_ads.FacebookMinimumBudgetUseCase"
    ) as mock_minimum_budget_use_case:
        yield SimpleNamespace(
            FacebookGetAdAccountDetailsUseCase=mock_get_ad_account_details_use_case,
            FacebookMinimumBudgetUseCase=mock_minimum_budget_use_case,
        )


@contextmanager
def patch_redis_client():
    """Context manager that patches ``app.v2.use_cases.meta_ads.redis_client``
    and yields the resulting ``MagicMock``, so a scenario can configure
    ``.get.return_value``/``.get.side_effect`` directly, for example::

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"token"

    Used by tests of ``_get_decoded_access_token`` and by ``execute()``
    scenarios that verify the short-circuit on a missing token.

    Requirements: 8.2
    """
    with patch("app.v2.use_cases.meta_ads.redis_client") as mock_redis_client:
        yield mock_redis_client


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Local, module-scoped guard (not a global ``conftest.py`` fixture),
    ``autouse=True`` at function scope, that replaces
    ``requests.sessions.Session.request`` with a function that fails
    immediately.

    This is additional defense even though no code path exercised by this
    suite performs a real network request: ``FacebookGetAdAccountDetailsUseCase``
    and ``FacebookMinimumBudgetUseCase`` are always patched via
    ``patch_budget_dependencies`` wherever ``_get_account_details``/
    ``_get_minimum_budget`` would otherwise be reached. Its inclusion keeps
    this suite consistent in style with its sibling suites and protects
    against a future regression that accidentally introduced a real network
    call in this file.

    Requirements: 8.2
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request", _raise_on_network_access
    )


class TestStandardBranchSufficientBudget:
    """Tests for the scenario in which ``self.daily_budget`` is comparable
    (a non-``bool`` ``int``/``float``) and sufficient (``>= min_budget``).

    Exercises ``execute()`` end to end, with ``_get_account_details``/
    ``_get_minimum_budget`` reaching through to their real,
    already-characterized logic while the two Facebook Graph API-backed
    collaborators they depend on (``FacebookGetAdAccountDetailsUseCase``/
    ``FacebookMinimumBudgetUseCase``) are replaced by
    ``patch_budget_dependencies``, so this scenario controls the exact
    ``min_budget`` value that reaches the Rama_STANDARD logic under test.

    Requirements: 4.3
    """

    def test_daily_budget_at_or_above_minimum_is_annotated_as_valid(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and ``self.daily_budget`` a non-``bool`` numeric value ``>=
        min_budget``, verify that ``execute()`` annotates::

            story_spec['daily_budget_valid'] is True
            story_spec['min_daily_budget'] == min_budget
            creative['daily_budget'] == self.daily_budget

        Requirements: 4.3
        """
        min_budget = 1000
        daily_budget = 1500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        story_spec = make_object_story_spec(link_data=make_link_data())
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            use_case.execute()

        assert story_spec["daily_budget_valid"] is True
        assert story_spec["min_daily_budget"] == min_budget
        assert creative["daily_budget"] == daily_budget


class TestStandardBranchInsufficientBudget:
    """Tests for the scenario in which ``self.daily_budget`` is comparable
    (a non-``bool`` ``int``/``float``) and insufficient (``< min_budget``).

    Exercises ``execute()`` end to end, with ``_get_account_details``/
    ``_get_minimum_budget`` reaching through to their real,
    already-characterized logic while the two Facebook Graph API-backed
    collaborators they depend on (``FacebookGetAdAccountDetailsUseCase``/
    ``FacebookMinimumBudgetUseCase``) are replaced by
    ``patch_budget_dependencies``, so this scenario controls the exact
    ``min_budget`` value that reaches the Rama_STANDARD logic under test.

    Requirements: 4.3
    """

    def test_daily_budget_below_minimum_is_annotated_as_invalid(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and ``self.daily_budget`` a non-``bool`` numeric value ``<
        min_budget``, verify that ``execute()`` annotates::

            story_spec['daily_budget_valid'] is False

        Requirements: 4.3
        """
        min_budget = 1000
        daily_budget = 500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        story_spec = make_object_story_spec(link_data=make_link_data())
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            use_case.execute()

        assert story_spec["daily_budget_valid"] is False


class TestStandardBranchNonComparableBudget:
    """Tests for the scenario in which ``self.daily_budget`` is not a
    comparable numeric value: it is either ``None`` or a ``bool`` (a type
    the production code's
    ``isinstance(self.daily_budget, (int, float)) and not isinstance(self.daily_budget, bool)``
    guard deliberately excludes from the comparison, even though ``bool``
    is technically an ``int`` subclass in Python).

    Exercises ``execute()`` end to end, with ``_get_account_details``/
    ``_get_minimum_budget`` reaching through to their real,
    already-characterized logic while the two Facebook Graph API-backed
    collaborators they depend on (``FacebookGetAdAccountDetailsUseCase``/
    ``FacebookMinimumBudgetUseCase``) are replaced by
    ``patch_budget_dependencies``.

    Requirements: 4.4
    """

    @pytest.mark.parametrize("daily_budget", [None, True])
    def test_non_comparable_daily_budget_is_never_annotated_but_min_daily_budget_is(
        self, use_case_factory, daily_budget
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and ``self.daily_budget`` set to ``None`` or ``True``, verify that
        ``execute()``:

        - completes without propagating an exception
        - never annotates ``story_spec['daily_budget_valid']``
        - still annotates ``story_spec['min_daily_budget']`` with the
          configured ``min_budget``

        Requirements: 4.4
        """
        min_budget = 1000
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        story_spec = make_object_story_spec(link_data=make_link_data())
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            use_case.execute()

        assert "daily_budget_valid" not in story_spec
        assert story_spec["min_daily_budget"] == min_budget


class TestStandardBranchEmptyObjectStorySpec:
    """Tests for the scenario in which ``story_spec`` (``Object_Story_Spec``)
    starts essentially empty: it carries no ``link_data`` key and none of
    the budget-related keys this Rama_STANDARD itself annotates
    (``min_daily_budget``/``daily_budget_valid``) yet.

    ``make_object_story_spec()`` defaults to ``{}``, which would be falsy
    and would prevent the ``elif ... STANDARD.value and story_spec:`` guard
    in ``execute()`` from firing at all (the ``DYNAMIC`` branch would be
    skipped too, since ``asset_feed`` is also absent, and the whole ``try``
    block would be a no-op). To keep ``story_spec`` truthy while still
    empty of any budget-related prior value, this scenario adds a single
    unrelated key (``headline="Some headline"``), mirroring exactly the
    same technique already used by
    ``test_facebook_save_pre_check_locations.py`` (see
    ``TestStandardBranchAtLeastOneLocationCandidate``/
    ``TestStandardBranchZeroLocationCandidates``) to characterize the same
    "truthy but otherwise empty ``story_spec``" scenario.

    Exercises ``execute()`` end to end, with ``_get_account_details``/
    ``_get_minimum_budget`` reaching through to their real,
    already-characterized logic while the two Facebook Graph API-backed
    collaborators they depend on (``FacebookGetAdAccountDetailsUseCase``/
    ``FacebookMinimumBudgetUseCase``) are replaced by
    ``patch_budget_dependencies``.

    Requirements: 4.5
    """

    def test_empty_story_spec_with_no_prior_values_raises_no_exception(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a ``story_spec`` that is
        truthy (via an unrelated ``headline`` key) but carries no
        ``link_data`` and no prior ``min_daily_budget``/
        ``daily_budget_valid`` keys, and ``self.daily_budget`` a valid
        comparable numeric value ``>= min_budget``, verify that
        ``execute()``:

        - completes without propagating an exception
        - annotates ``story_spec['min_daily_budget'] == min_budget``
        - annotates ``story_spec['daily_budget_valid'] is True``
        - annotates ``creative['daily_budget'] == self.daily_budget``

        Requirements: 4.5
        """
        min_budget = 1000
        daily_budget = 1500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        story_spec = make_object_story_spec(headline="Some headline")
        assert "link_data" not in story_spec
        assert "min_daily_budget" not in story_spec
        assert "daily_budget_valid" not in story_spec

        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            creative_to_publish = use_case.execute()

        assert story_spec["min_daily_budget"] == min_budget
        assert story_spec["daily_budget_valid"] is True
        assert creative["daily_budget"] == daily_budget
        assert creative_to_publish is not None


class TestStandardBranchFullExecuteResponse:
    """Tests for the full ``execute()`` round trip in STANDARD mode: with a
    truthy ``story_spec`` built via ``make_link_data()`` and
    ``self.daily_budget`` a comparable numeric value ``>= min_budget``,
    verify that the dict *returned* by ``execute()`` (not just the mutated
    ``story_spec``) reflects ``daily_budget_valid`` conforme a la anotación
    esperada.

    Unlike the sibling classes above (which only assert on the mutated
    ``story_spec``), this class exercises ``execute()`` completely, with
    ``_get_account_details``/``_get_minimum_budget`` reaching through to
    their real, already-characterized logic while the two Facebook Graph
    API-backed collaborators they depend on
    (``FacebookGetAdAccountDetailsUseCase``/``FacebookMinimumBudgetUseCase``)
    are replaced by ``patch_budget_dependencies``, and asserts on the
    return value, characterizing the STANDARD-mode branch of
    ``_build_response`` (inherited from the Caso_de_Uso_Padre), which maps
    ``object_story_spec.get('daily_budget_valid', False)`` directly into
    the returned response's ``daily_budget_valid`` key.

    Requirements: 8.3
    """

    def test_execute_returns_response_reflecting_daily_budget_valid(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        (via ``make_link_data()``) and ``self.daily_budget`` a comparable
        numeric value ``>= min_budget``, verify that the dict returned by
        ``execute()`` has ``response["daily_budget_valid"] is True``,
        conforming exactly to ``_build_response``'s
        ``object_story_spec.get('daily_budget_valid', False)`` mapping for
        the STANDARD-mode (``object_story_spec``/``link_data``) branch.

        Requirements: 8.3
        """
        min_budget = 1000
        daily_budget = 1500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        story_spec = make_object_story_spec(link_data=make_link_data())
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative, ad_id="ad-1")
        creative = make_creative(ads=[ad], name="My Creative", id="adset-1")
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            response = use_case.execute()

        # Sanity check: the STANDARD-mode branch of ``execute()`` was
        # actually exercised (``story_spec`` was annotated as expected),
        # before asserting on the returned response itself.
        assert story_spec["daily_budget_valid"] is True

        assert response["daily_budget_valid"] is True


class TestStandardSpecDoesNotRegressDynamicBranch:
    """Tests for Requirement 7.1/7.3/7.4 (no regresión): confirm that adding
    the Rama_STANDARD ``elif`` block to
    ``FacebookSavePreCheckBudgetUseCase.execute()`` did not change the
    observable behaviour of the pre-existing Rama_DYNAMIC (the inline
    ``if campaign_setup...DYNAMIC.value and asset_feed:`` block that
    annotates ``asset_feed``), and that the STANDARD logic never runs when
    ``meta_campaign_mode == "DYNAMIC"``.

    Unlike Caso_de_Uso_CTAs (whose STANDARD logic lives inside a dedicated
    private method, ``_validate_ctas_standard``, that can be patched on the
    instance), Caso_de_Uso_Budget's Rama_STANDARD is entirely inline within
    ``execute()``: there is no private method to patch to prove it never
    ran. Instead, this class exercises ``execute()`` end to end (with
    ``_get_account_details``/``_get_minimum_budget`` reaching through to
    their real logic while ``FacebookGetAdAccountDetailsUseCase``/
    ``FacebookMinimumBudgetUseCase`` are replaced by
    ``patch_budget_dependencies``, exactly as the STANDARD-branch classes
    above already do) and asserts directly on the observable side effects:
    the DYNAMIC branch still annotates ``asset_feed``/``creative`` exactly
    as before, and a pre-existing, truthy ``story_spec``/``link_data`` is
    left completely untouched (no ``min_daily_budget``/``daily_budget_valid``
    added to it), proving the STANDARD ``elif`` never ran because the ``if``
    (DYNAMIC) condition already matched first.

    Requirements: 7.1, 7.3, 7.4
    """

    def test_dynamic_branch_asset_feed_annotations_still_work_as_before(
        self, use_case_factory
    ):
        """When ``meta_campaign_mode == "DYNAMIC"`` and ``asset_feed``
        (``ad_creative['asset_feed_spec']``) is a truthy dict, verify that
        ``execute()`` annotates, exactly as it already did before this
        specification introduced the STANDARD ``elif`` block::

            asset_feed['min_daily_budget'] == min_budget
            asset_feed['daily_budget_valid'] == (self.daily_budget >= min_budget)
            creative['daily_budget'] == self.daily_budget

        Requirements: 7.1
        """
        min_budget = 1000
        daily_budget = 1500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        asset_feed = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            use_case.execute()

        assert asset_feed["min_daily_budget"] == min_budget
        assert asset_feed["daily_budget_valid"] is True
        assert creative["daily_budget"] == daily_budget

    def test_standard_logic_does_not_execute_when_mode_is_dynamic(
        self, use_case_factory
    ):
        """Build a scenario where ``story_spec``/``link_data`` IS present
        and truthy, in addition to a truthy ``asset_feed``, with
        ``meta_campaign_mode="DYNAMIC"``, and verify that ``story_spec``
        (specifically ``min_daily_budget``/``daily_budget_valid``, which
        the STANDARD branch would have written) is left completely
        untouched: the STANDARD ``elif`` never ran because the ``if``
        (DYNAMIC) condition already matched first.

        Requirements: 7.3, 7.4
        """
        min_budget = 1000
        daily_budget = 1500
        pre_check_budget_data = make_pre_check_budget_data(daily_budget=daily_budget)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_budget_data=pre_check_budget_data)
        )

        asset_feed = make_asset_feed_spec()
        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed, object_story_spec=story_spec
        )
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        story_spec_snapshot = dict(story_spec)

        with patch_redis_client() as mock_redis_client, patch_budget_dependencies() as deps:
            mock_redis_client.get.return_value = b"some-access-token"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(currency="USD"),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    currency="USD", min_daily_budget_imp=min_budget * 100
                ),
                200,
            )

            use_case.execute()

        assert "min_daily_budget" not in story_spec
        assert "daily_budget_valid" not in story_spec
        assert story_spec == story_spec_snapshot
        assert story_spec["link_data"] is link_data


_COMBINATION_LEADS_OFFSITE = ("OUTCOME_LEADS", "OFFSITE_CONVERSIONS")
_COMBINATION_LEAD_GENERATION = ("OUTCOME_LEADS", "LEAD_GENERATION")
_COMBINATION_SALES_OFFSITE = ("OUTCOME_SALES", "OFFSITE_CONVERSIONS")

_LEADS_OFFSITE_MIN_BUDGET = 10.0
_LEADS_OFFSITE_DAILY_BUDGET = 15


class TestLeadsOffsiteSaveBudget:
    """Coverage of ``FacebookSavePreCheckBudgetUseCase.execute()`` for the
    Combinación_Leads_Offsite (``OUTCOME_LEADS`` + ``OFFSITE_CONVERSIONS``)
    in both Rama_DYNAMIC and Rama_STANDARD, plus the field-by-field
    differential against ``OUTCOME_LEADS`` + ``LEAD_GENERATION`` and the
    non-regression cases for Otras_Combinaciones.

    Only the repositories (``use_case_factory``), Redis
    (``patch_redis_client``) and the instance methods
    ``_get_account_details``/``_get_minimum_budget`` are doubled.
    ``_save_creative_to_publish`` is wrapped by a spy that delegates to the
    real implementation, so persistence reaches the mocked
    ``AdChannelRepository.update``.

    Requirements: 10.5, 10.6, 10.7, 10.8, 14.9
    """

    @staticmethod
    def _build_creative(mode, promoted_object_valid=True):
        """Build the initial ``channel_creative`` for ``mode``; identical
        (by value) for every combination, so runs are comparable."""
        if mode == "DYNAMIC":
            asset_feed = make_asset_feed_spec(
                ad_channel_id=7,
                promoted_object_valid=promoted_object_valid,
            )
            ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        else:
            story_spec = make_object_story_spec(
                ad_channel_id=8,
                link_data=make_link_data(
                    name="title", message="body", link="https://example.test"
                ),
            )
            ad_creative = make_ad_creative(object_story_spec=story_spec)
        return make_creative(ads=[make_ad(ad_creative=ad_creative)])

    def _run(self, use_case_factory, mode, combination, promoted_object_valid=True):
        """Run a full ``execute()`` and return
        ``(result, creative, update_mock, save_spy)``; also checks that the
        patched budget lookups were each invoked exactly once."""
        objective, goal = combination
        creative = self._build_creative(mode, promoted_object_valid)
        campaign_setup = make_campaign_setup(
            attributes={
                "meta_campaign_mode": mode,
                "meta_account_id": "act-1",
                "meta_campaign_objective": objective,
                "meta_optimization_goal": goal,
                "meta_pixel_id": "123456789",
                "meta_conversion_event": "LEAD",
            }
        )
        use_case, mock_ad_channel_repo, mock_campaign_publish_repo = use_case_factory(
            pre_check_budget_data=make_pre_check_budget_data(
                daily_budget=_LEADS_OFFSITE_DAILY_BUDGET
            )
        )
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel(channel_creative=creative)
        )
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )
        account_info = make_ad_account_info(currency="USD")
        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_get_account_details", return_value=account_info
        ) as account_mock, patch.object(
            use_case, "_get_minimum_budget", return_value=_LEADS_OFFSITE_MIN_BUDGET
        ) as minimum_mock, patch.object(
            use_case,
            "_save_creative_to_publish",
            wraps=use_case._save_creative_to_publish,
        ) as save_spy:
            mock_redis_client.get.return_value = b"some-access-token"
            result = use_case.execute()
        account_mock.assert_called_once_with()
        minimum_mock.assert_called_once_with(account_info)
        return result, creative, mock_ad_channel_repo.update, save_spy

    # ------------------------------------------------------------------
    # Expected annotations (shared by every combination)
    # ------------------------------------------------------------------

    @staticmethod
    def _assert_dynamic_outcome(result, creative, update_mock, save_spy):
        asset_feed = creative["ads"][0]["adCreative"]["asset_feed_spec"]
        assert asset_feed["min_daily_budget"] == _LEADS_OFFSITE_MIN_BUDGET
        assert asset_feed["daily_budget_valid"] is True
        assert creative["daily_budget"] == _LEADS_OFFSITE_DAILY_BUDGET
        save_spy.assert_called_once_with(creative)
        update_mock.assert_called_once_with(7, {"channel_creative": creative})
        assert result["adchannel_id"] == 7
        assert result["daily_budget"] == _LEADS_OFFSITE_DAILY_BUDGET
        assert result["daily_budget_valid"] is True
        assert result["min_daily_budget"] == _LEADS_OFFSITE_MIN_BUDGET

    @staticmethod
    def _assert_standard_outcome(result, creative, update_mock, save_spy):
        ad = creative["ads"][0]
        story_spec = ad["adCreative"]["object_story_spec"]
        assert story_spec["min_daily_budget"] == _LEADS_OFFSITE_MIN_BUDGET
        assert story_spec["daily_budget_valid"] is True
        assert story_spec["link_data"] == make_link_data(
            name="title", message="body", link="https://example.test"
        )
        assert creative["daily_budget"] == _LEADS_OFFSITE_DAILY_BUDGET
        save_spy.assert_called_once_with(creative)
        update_mock.assert_called_once_with(
            8, {"channel_creative": {**creative, "ads": [ad]}}
        )
        assert result["adchannel_id"] == 8
        assert result["daily_budget"] == _LEADS_OFFSITE_DAILY_BUDGET
        assert result["daily_budget_valid"] is True
        assert result["min_daily_budget"] == _LEADS_OFFSITE_MIN_BUDGET

    # ------------------------------------------------------------------
    # Happy paths for Combinación_Leads_Offsite (Req 10.6, 14.9)
    # ------------------------------------------------------------------

    def test_dynamic_happy_path_leads_offsite(self, use_case_factory):
        """DYNAMIC + Combinación_Leads_Offsite finishes without exception,
        annotates the budget on ``asset_feed_spec`` and persists through
        ``AdChannelRepository`` via exactly one ``_save_creative_to_publish``
        call.

        Requirements: 10.6, 14.9
        """
        outcome = self._run(use_case_factory, "DYNAMIC", _COMBINATION_LEADS_OFFSITE)
        self._assert_dynamic_outcome(*outcome)

    def test_standard_happy_path_leads_offsite(self, use_case_factory):
        """STANDARD + Combinación_Leads_Offsite finishes without exception,
        annotates the budget on ``object_story_spec`` and persists through
        ``AdChannelRepository`` via exactly one ``_save_creative_to_publish``
        call.

        Requirements: 10.6, 14.9
        """
        outcome = self._run(use_case_factory, "STANDARD", _COMBINATION_LEADS_OFFSITE)
        self._assert_standard_outcome(*outcome)

    # ------------------------------------------------------------------
    # Field-by-field differential vs LEAD_GENERATION (Req 10.5)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("mode", ["DYNAMIC", "STANDARD"])
    def test_identical_to_lead_generation_field_by_field(self, use_case_factory, mode):
        """With the same input and the same initial ``channel_creative``,
        Combinación_Leads_Offsite produces the same annotated creative, the
        same ``ad-channels`` persistence call and the same response as
        ``OUTCOME_LEADS`` + ``LEAD_GENERATION``, key by key.

        Requirements: 10.5
        """
        offsite_result, offsite_creative, offsite_update, _ = self._run(
            use_case_factory, mode, _COMBINATION_LEADS_OFFSITE
        )
        leadgen_result, leadgen_creative, leadgen_update, _ = self._run(
            use_case_factory, mode, _COMBINATION_LEAD_GENERATION
        )

        assert offsite_result.keys() == leadgen_result.keys()
        for key in leadgen_result:
            assert offsite_result[key] == leadgen_result[key], key

        offsite_spec = offsite_creative["ads"][0]["adCreative"]
        leadgen_spec = leadgen_creative["ads"][0]["adCreative"]
        assert offsite_spec.keys() == leadgen_spec.keys()
        for spec_key in leadgen_spec:
            assert offsite_spec[spec_key].keys() == leadgen_spec[spec_key].keys()
            for field in leadgen_spec[spec_key]:
                assert offsite_spec[spec_key][field] == leadgen_spec[spec_key][field], (
                    spec_key,
                    field,
                )
        assert offsite_creative == leadgen_creative

        assert offsite_update.call_count == leadgen_update.call_count == 1
        assert offsite_update.call_args == leadgen_update.call_args

    # ------------------------------------------------------------------
    # promoted_object_valid preserved (Req 10.7)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("promoted_object_valid", [True, False])
    def test_dynamic_persists_promoted_object_valid_untouched(
        self, use_case_factory, promoted_object_valid
    ):
        """In Rama_DYNAMIC the persisted ``asset_feed_spec.promoted_object_valid``
        keeps the value written by Caso_PreCheck.

        Requirements: 10.7
        """
        _, _, update_mock, _ = self._run(
            use_case_factory,
            "DYNAMIC",
            _COMBINATION_LEADS_OFFSITE,
            promoted_object_valid=promoted_object_valid,
        )
        persisted = update_mock.call_args.args[1]["channel_creative"]
        persisted_feed = persisted["ads"][0]["adCreative"]["asset_feed_spec"]
        assert persisted_feed["promoted_object_valid"] is promoted_object_valid

    # ------------------------------------------------------------------
    # Otras_Combinaciones non-regression (Req 10.8)
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "combination",
        [_COMBINATION_LEAD_GENERATION, _COMBINATION_SALES_OFFSITE],
        ids=["OUTCOME_LEADS-LEAD_GENERATION", "OUTCOME_SALES-OFFSITE_CONVERSIONS"],
    )
    @pytest.mark.parametrize("mode", ["DYNAMIC", "STANDARD"])
    def test_other_combinations_keep_previous_behaviour(
        self, use_case_factory, mode, combination
    ):
        """``OUTCOME_LEADS`` + ``LEAD_GENERATION`` and ``OUTCOME_SALES`` +
        ``OFFSITE_CONVERSIONS`` keep the same annotations, persistence and
        response as before this change.

        Requirements: 10.8
        """
        outcome = self._run(use_case_factory, mode, combination)
        if mode == "DYNAMIC":
            self._assert_dynamic_outcome(*outcome)
        else:
            self._assert_standard_outcome(*outcome)
