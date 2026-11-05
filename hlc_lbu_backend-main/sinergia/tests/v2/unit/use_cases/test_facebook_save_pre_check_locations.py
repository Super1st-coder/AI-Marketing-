"""Characterization test suite for ``FacebookSavePreCheckLocationsUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookSavePreCheckLocationsUseCase``
(its Rama_STANDARD, inline within ``execute()``) and the inherited subset of
``FacebookSavePreCheckBaseUseCase`` that it invokes: the constructor,
``_get_ad_channel``, ``_get_campaign_setup``, ``_set_channel_id`` and
``_build_response``.

This module fixes the current observable behaviour, including already
existing quirks (the always-``{}`` ``complete_campaign_data`` passed to the
grandparent constructor, the mutable default ``pre_check_data: PreCheckDataDict
= {}`` in the constructor signature, and the transparent
``try/except Exception as e: raise e`` pass-through in ``execute()``).
Unlike its sibling suites, this Rama_STANDARD does NOT wrap
``creative['targeting']['geo_locations'] = geo_locations`` in any additional
``try/except`` beyond the one already present in ``execute()``: a missing
``targeting`` key, or a non-dict ``targeting`` value, propagates the same
uncontrolled exception (``KeyError``/``TypeError``) that the pre-existing
Rama_DYNAMIC already propagates today for that same scenario. No production
code is modified or "fixed" by this suite.

Builders/fixtures below replicate, verbatim in style, the ones already used
by the sibling suites ``test_facebook_save_pre_check_ctas.py``,
``test_facebook_save_pre_check_budget.py`` and
``test_facebook_save_pre_check_proposal_url.py``. Like
``FacebookSavePreCheckCTAsUseCase``/``FacebookSavePreCheckProposalURLUseCase``,
this use case requires no extra collaborators beyond
``AdChannelRepository``/``CampaignChannelPublishRepository`` (unlike
``FacebookSavePreCheckBudgetUseCase``, which additionally needs
``FacebookGetAdAccountDetailsUseCase``/``FacebookMinimumBudgetUseCase``).

Requirements: 8.2
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.exceptions.base import DataNotFoundException, NotAccessException
from app.v2.use_cases.facebook_validator_service import MetaAdsValidator
from app.v2.use_cases.meta_ads import (
    FacebookSavePreCheckBaseUseCase,
    FacebookSavePreCheckLocationsUseCase,
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


def make_pre_check_locations_data(**overrides):
    """Build a fresh ``pre_check_locations_data`` (``PreCheckDataDict``-like)
    dict.

    Every invocation returns a brand new dict, with brand new list objects
    for every collection field (including ``locations``); no mutable
    default arguments are used, so callers can freely mutate the returned
    value (or its nested lists) without affecting other tests.

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


def make_campaign_setup(meta_campaign_mode="DYNAMIC", **overrides):
    """Build a fresh ``campaign_setup`` dict as returned by
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``.

    Pass ``meta_campaign_mode=None`` or ``meta_campaign_mode=""`` explicitly
    to characterize unknown-mode scenarios. ``**overrides`` are merged into
    the top-level dict.

    Requirements: 8.2
    """
    data = {"attributes": {"meta_campaign_mode": meta_campaign_mode}}
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

    Empty by default; callers compose it with the fields Caso_de_Uso_Locations
    reads/writes (``locations``, ``locations_valid``) to characterize the
    Rama_STANDARD scenarios of Caso_de_Uso_Locations.

    Requirements: 8.2
    """
    data = {}
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict (``object_story_spec['link_data']``).

    Kept for style-parity with the sibling suites even though
    Caso_de_Uso_Locations's Rama_STANDARD never reads/writes ``link_data``
    itself; every field defaults to ``None``.

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


def make_creative(
    name="Creative", ads=None, proposal_locations=ABSENT, targeting=ABSENT, **overrides
):
    """Build a fresh ``creative`` dict (``ad_channel['attributes']['channel_creative']``).

    ``ads`` defaults to a brand new list containing a single fresh
    ``make_ad()`` when omitted (``None``); pass ``ads=[]`` explicitly to
    characterize an empty-``ads`` scenario. ``proposal_locations`` defaults
    to the ``ABSENT`` sentinel: when left untouched, the key is omitted
    entirely, matching the ``creative.get('proposal_locations', [])``
    default in ``_build_response``.

    ``targeting`` defaults to the ``ABSENT`` sentinel as well, but unlike
    ``proposal_locations``, ``ABSENT`` here resolves to a brand new, empty
    ``{}`` dict rather than an omitted key: Caso_de_Uso_Locations's
    Rama_STANDARD (unlike its Rama_DYNAMIC-adjacent siblings) always does
    ``creative['targeting']['geo_locations'] = geo_locations`` with no
    additional ``try/except`` of its own, so most scenarios need a present,
    mutable ``targeting`` dict to exercise the happy path. Pass
    ``targeting=None`` explicitly (or any other non-dict value) to
    characterize the "``targeting`` is not a dict" propagation scenario, or
    pop the key from the returned dict (``del creative['targeting']``) to
    characterize the "``targeting`` key is absent" propagation scenario.

    Requirements: 8.2
    """
    data = {
        "name": name,
        "id": "adset-1",
        "daily_budget": 100,
        "ads": ads if ads is not None else [make_ad()],
        "targeting": {} if targeting is ABSENT else targeting,
    }
    if proposal_locations is not ABSENT:
        data["proposal_locations"] = proposal_locations
    data.update(overrides)
    return data


@pytest.fixture
def use_case_factory():
    """Fixture that builds a factory for ``FacebookSavePreCheckLocationsUseCase``
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

    If ``pre_check_locations_data`` is omitted, a fresh
    ``make_pre_check_locations_data()`` is used so accidental constructor
    edge-case scenarios (explicit ``None``, mutable defaults) are not
    triggered here; dedicated tests for those construct the use case
    directly, without this fixture.

    Requirements: 8.2
    """

    def _factory(user_id="user-1", pre_check_locations_data=None):
        if pre_check_locations_data is None:
            pre_check_locations_data = make_pre_check_locations_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookSavePreCheckLocationsUseCase(
                user_id, pre_check_locations_data
            )
            mock_ad_channel_repo_instance = mock_ad_channel_repository_cls.return_value
            mock_campaign_publish_repo_instance = (
                mock_campaign_publish_repository_cls.return_value
            )

        return use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance

    return _factory


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

    This is additional defense even though no code path reachable by
    ``FacebookSavePreCheckLocationsUseCase`` performs any network request:
    ``_build_geo_locations`` is a pure, in-memory function. Its inclusion
    keeps this suite consistent in style with its sibling suites and
    protects against a future regression that accidentally introduced a
    network call in this file.

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


class TestStandardBranchAtLeastOneLocationCandidate:
    """Tests for the success scenario of the Rama_STANDARD locations
    validation performed inline within ``execute()``: at least one
    Ubicación_Candidata (``self.locations``).

    Mirrors the sibling suites' first STANDARD-branch success scenario
    (e.g. ``TestStandardBranchProposalURLValidationSuccess`` in
    ``test_facebook_save_pre_check_proposal_url.py``): exercises
    ``execute()`` end to end (with ``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real, against the
    mocked ``AdChannelRepository``/``CampaignChannelPublishRepository``)
    and asserts on the resulting ``story_spec``/``creative`` mutation.

    ``_build_geo_locations`` is exercised for real (not patched): it is a
    pure, in-memory function that groups ``self.locations`` by ``type``
    into ``{'countries': [...], 'regions': [...], 'cities': [...]}``.

    Requirements: 6.1, 6.2
    """

    def test_at_least_one_location_marks_locations_valid_and_builds_geo_locations(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and a non-empty ``self.locations`` (a single ``country`` location),
        verify that ``execute()``:

            story_spec['locations_valid'] is True
            creative['targeting']['geo_locations'] == use_case._build_geo_locations()

        i.e. ``creative['targeting']['geo_locations']`` reflects exactly
        the result ``_build_geo_locations()`` would produce for that same
        ``self.locations`` input.

        Requirements: 6.1, 6.2
        """
        locations = [{"type": "country", "key": "US"}]
        pre_check_locations_data = make_pre_check_locations_data(locations=locations)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        expected_geo_locations = use_case._build_geo_locations()
        assert expected_geo_locations == {
            "countries": ["US"],
            "regions": [],
            "cities": [],
        }

        story_spec = make_object_story_spec(headline="Some headline")
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert story_spec["locations_valid"] is True
        assert story_spec["locations"] == locations
        assert creative["targeting"]["geo_locations"] == expected_geo_locations


class TestStandardBranchZeroLocationCandidates:
    """Tests for the failure scenario of the Rama_STANDARD locations
    validation performed inline within ``execute()``: zero
    Ubicaciones_Candidatas (``self.locations == []``, the default returned
    by ``make_pre_check_locations_data()``).

    Mirrors ``TestStandardBranchAtLeastOneLocationCandidate`` above:
    exercises ``execute()`` end to end (with ``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real, against the
    mocked ``AdChannelRepository``/``CampaignChannelPublishRepository``)
    and asserts on the resulting ``story_spec`` mutation.

    Requirements: 6.1, 6.2
    """

    def test_zero_locations_marks_locations_valid_false(self, use_case_factory):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and an empty ``self.locations`` (the default), verify that
        ``execute()``:

            story_spec['locations_valid'] is False

        Requirements: 6.1, 6.2
        """
        pre_check_locations_data = make_pre_check_locations_data()
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        story_spec = make_object_story_spec(headline="Some headline")
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert story_spec["locations_valid"] is False
        assert story_spec["locations"] == []


class TestStandardBranchMissingOrNonDictTargeting:
    """Tests for the propagation scenario of the Rama_STANDARD locations
    validation performed inline within ``execute()``: ``creative`` lacks the
    ``targeting`` key entirely, or its value is not a dict.

    ``execute()`` wraps the whole STANDARD/DYNAMIC block in a
    ``try/except Exception as e: raise e`` (a transparent pass-through, not
    a swallow), so a missing ``targeting`` key still raises ``KeyError``
    (``creative['targeting']`` lookup fails before the assignment can even
    be attempted) and a non-dict ``targeting`` value (e.g. ``None``) still
    raises ``TypeError`` (``None['geo_locations'] = ...`` is not
    subscriptable for assignment) -- exactly like the pre-existing
    Rama_DYNAMIC of this same class already does today for the identical
    scenario (same code shape, just against the ``asset_feed`` guard
    instead of the ``story_spec`` guard). ``story_spec['locations']``/
    ``['locations_valid']`` are asserted to remain unannotated, since the
    exception happens before those two lines run.

    Requirements: 6.4
    """

    @pytest.mark.parametrize(
        "build_creative, expected_exception",
        [
            pytest.param(
                lambda: _make_creative_without_targeting(),
                KeyError,
                id="targeting-key-absent",
            ),
            pytest.param(
                lambda: make_creative(targeting=None),
                TypeError,
                id="targeting-is-none",
            ),
        ],
    )
    def test_missing_or_non_dict_targeting_propagates_uncontrolled_exception(
        self, use_case_factory, build_creative, expected_exception
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``,
        at least one location candidate, and a ``creative`` whose
        ``targeting`` key is either absent entirely or set to a non-dict
        value (``None``), verify that ``execute()``:

            raises ``expected_exception`` (``KeyError``/``TypeError``)

        and that ``story_spec['locations']``/``['locations_valid']`` were
        NOT annotated (the exception happens before those two lines run).

        Requirements: 6.4
        """
        locations = [{"type": "country", "key": "US"}]
        pre_check_locations_data = make_pre_check_locations_data(locations=locations)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        story_spec = make_object_story_spec(headline="Some headline")
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = build_creative()
        creative["ads"] = [ad]
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(expected_exception):
                use_case.execute()

        assert "locations" not in story_spec
        assert "locations_valid" not in story_spec


def _make_creative_without_targeting():
    """Build a fresh ``creative`` dict with the ``targeting`` key deleted
    entirely, to characterize the "``targeting`` key is absent" propagation
    scenario described by ``make_creative``'s docstring.

    Requirements: 6.4
    """
    creative = make_creative()
    del creative["targeting"]
    return creative


class TestStandardBranchFullExecuteResponse:
    """Tests for the full ``execute()`` round trip in STANDARD mode: with a
    truthy ``story_spec`` (via an unrelated key, e.g. ``headline``) and a
    non-empty ``self.locations`` (a single ``country`` location), verify
    that the dict *returned* by ``execute()`` (not just the mutated
    ``story_spec``) reflects ``locations``/``locations_valid`` conforme a
    las anotaciones esperadas.

    Mirrors ``TestStandardBranchFullExecuteResponse`` in
    ``test_facebook_save_pre_check_texts.py``: unlike
    ``TestStandardBranchAtLeastOneLocationCandidate`` above (which only
    asserts on the mutated ``story_spec``/``creative``), this class
    exercises ``execute()`` completely unpatched (real
    ``_build_geo_locations``, real ``_save_creative_to_publish``, real
    ``_build_response``) and asserts on its return value, characterizing
    the STANDARD-mode branch of ``_build_response`` (inherited from the
    Caso_de_Uso_Padre), which maps
    ``object_story_spec.get('locations', [])``/
    ``object_story_spec.get('locations_valid', False)`` directly into the
    response's ``locations``/``locations_valid`` keys.

    Requirements: 8.3
    """

    def test_execute_returns_response_reflecting_locations_annotations(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        (via an unrelated key) and exactly one location candidate
        (a single ``country`` location), verify that the dict returned by
        ``execute()`` has:

        - ``response["locations"] == [{'type': 'country', 'key': 'US'}]``
        - ``response["locations_valid"] is True``

        conforming exactly to ``_build_response``'s
        ``object_story_spec.get('locations', [])``/
        ``object_story_spec.get('locations_valid', False)`` mapping for
        the STANDARD-mode (``object_story_spec``) branch.

        Requirements: 8.3
        """
        locations = [{"type": "country", "key": "US"}]
        pre_check_locations_data = make_pre_check_locations_data(locations=locations)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        story_spec = make_object_story_spec(headline="Some headline")
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            response = use_case.execute()

        # Sanity check: the STANDARD-mode branch was actually exercised
        # (``story_spec`` was annotated as expected), before asserting on
        # the returned response itself.
        assert story_spec["locations"] == locations
        assert story_spec["locations_valid"] is True

        assert response["locations"] == [{"type": "country", "key": "US"}]
        assert response["locations_valid"] is True


class TestStandardSpecDoesNotRegressDynamicBranch:
    """Tests for Requirement 7.1/7.3/7.4 (no regresión): confirm that adding
    the Rama_STANDARD ``elif`` block to
    ``FacebookSavePreCheckLocationsUseCase.execute()`` did not change the
    observable behaviour of the pre-existing Rama_DYNAMIC (the inline
    ``if campaign_setup...DYNAMIC.value and asset_feed:`` block that
    annotates ``asset_feed``/``creative['targeting']['geo_locations']``),
    and that the STANDARD logic never runs when
    ``meta_campaign_mode == "DYNAMIC"``.

    Like Caso_de_Uso_Budget's Rama_STANDARD, Caso_de_Uso_Locations's
    Rama_STANDARD is entirely inline within ``execute()``: there is no
    private method to patch to prove it never ran. Instead, this class
    exercises ``execute()`` end to end (with ``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real, against the
    mocked ``AdChannelRepository``/``CampaignChannelPublishRepository``)
    and asserts directly on the observable side effects: the DYNAMIC branch
    still annotates ``asset_feed``/``creative`` exactly as before, and a
    pre-existing, truthy ``story_spec`` is left completely untouched (no
    ``locations``/``locations_valid`` added to it), proving the STANDARD
    ``elif`` never ran because the ``if`` (DYNAMIC) condition already
    matched first.

    Requirements: 7.1, 7.3, 7.4
    """

    def test_dynamic_branch_asset_feed_annotations_still_work_as_before(
        self, use_case_factory
    ):
        """When ``meta_campaign_mode == "DYNAMIC"`` and ``asset_feed``
        (``ad_creative['asset_feed_spec']``) is a truthy dict, verify that
        ``execute()`` annotates, exactly as it already did before this
        specification introduced the STANDARD ``elif`` block::

            asset_feed['locations'] == self.locations
            asset_feed['locations_valid'] == (len(self.locations) > 0)
            creative['targeting']['geo_locations'] == use_case._build_geo_locations()

        Requirements: 7.1
        """
        locations = [{"type": "country", "key": "US"}]
        pre_check_locations_data = make_pre_check_locations_data(locations=locations)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        expected_geo_locations = use_case._build_geo_locations()
        assert expected_geo_locations == {
            "countries": ["US"],
            "regions": [],
            "cities": [],
        }

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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert asset_feed["locations"] == locations
        assert asset_feed["locations_valid"] is True
        assert creative["targeting"]["geo_locations"] == expected_geo_locations

    def test_standard_logic_does_not_execute_when_mode_is_dynamic(
        self, use_case_factory
    ):
        """Build a scenario where ``story_spec`` IS present and truthy, in
        addition to a truthy ``asset_feed``, with
        ``meta_campaign_mode="DYNAMIC"``, and verify that ``story_spec``
        (specifically ``locations``/``locations_valid``, which the STANDARD
        branch would have written) is left completely untouched: the
        STANDARD ``elif`` never ran because the ``if`` (DYNAMIC) condition
        already matched first.

        Requirements: 7.3, 7.4
        """
        locations = [{"type": "country", "key": "US"}]
        pre_check_locations_data = make_pre_check_locations_data(locations=locations)
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_locations_data=pre_check_locations_data)
        )

        asset_feed = make_asset_feed_spec()
        story_spec = make_object_story_spec(headline="Some headline")
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert "locations" not in story_spec
        assert "locations_valid" not in story_spec
        assert story_spec == story_spec_snapshot
        assert story_spec["headline"] == "Some headline"


_COMBINATION_LEADS_OFFSITE = ("OUTCOME_LEADS", "OFFSITE_CONVERSIONS")
_COMBINATION_LEAD_GENERATION = ("OUTCOME_LEADS", "LEAD_GENERATION")
_COMBINATION_SALES_OFFSITE = ("OUTCOME_SALES", "OFFSITE_CONVERSIONS")

_LEADS_OFFSITE_LOCATIONS = [
    {"type": "country", "key": "US"},
    {"type": "region", "key": "3847"},
    {"type": "city", "key": "2418779"},
]
_LEADS_OFFSITE_GEO_LOCATIONS = {
    "countries": ["US"],
    "regions": [{"key": "3847"}],
    "cities": [{"key": "2418779"}],
}


class TestLeadsOffsiteSaveLocations:
    """Coverage of ``FacebookSavePreCheckLocationsUseCase.execute()`` for the
    Combinación_Leads_Offsite (``OUTCOME_LEADS`` + ``OFFSITE_CONVERSIONS``)
    in both Rama_DYNAMIC and Rama_STANDARD, plus the field-by-field
    differential against ``OUTCOME_LEADS`` + ``LEAD_GENERATION`` and the
    non-regression cases for Otras_Combinaciones.

    Every scenario is a full, unpatched ``execute()`` run: only the
    repositories (``use_case_factory``) and Redis (``patch_redis_client``)
    are doubled. ``_save_creative_to_publish`` is wrapped by a spy that
    delegates to the real implementation, so persistence reaches the mocked
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
                titles=[{"text": "title", "valid_length": True}],
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
        return make_creative(
            ads=[make_ad(ad_creative=ad_creative)],
            targeting={"age_min": 18},
        )

    def _run(self, use_case_factory, mode, combination, promoted_object_valid=True):
        """Run a full ``execute()`` and return
        ``(result, creative, update_mock, save_spy)``."""
        objective, goal = combination
        creative = self._build_creative(mode, promoted_object_valid)
        pre_check_locations_data = make_pre_check_locations_data(
            locations=[dict(location) for location in _LEADS_OFFSITE_LOCATIONS]
        )
        campaign_setup = make_campaign_setup(
            attributes={
                "meta_campaign_mode": mode,
                "meta_campaign_objective": objective,
                "meta_optimization_goal": goal,
                "meta_pixel_id": "123456789",
                "meta_conversion_event": "LEAD",
            }
        )
        use_case, mock_ad_channel_repo, mock_campaign_publish_repo = use_case_factory(
            pre_check_locations_data=pre_check_locations_data
        )
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel(channel_creative=creative)
        )
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )
        with patch_redis_client() as mock_redis_client, patch.object(
            use_case,
            "_save_creative_to_publish",
            wraps=use_case._save_creative_to_publish,
        ) as save_spy:
            mock_redis_client.get.return_value = b"some-access-token"
            result = use_case.execute()
        return result, creative, mock_ad_channel_repo.update, save_spy

    # ------------------------------------------------------------------
    # Expected annotations (shared by every combination)
    # ------------------------------------------------------------------

    @staticmethod
    def _assert_dynamic_outcome(result, creative, update_mock, save_spy):
        asset_feed = creative["ads"][0]["adCreative"]["asset_feed_spec"]
        assert asset_feed["locations"] == _LEADS_OFFSITE_LOCATIONS
        assert asset_feed["locations_valid"] is True
        assert creative["targeting"] == {
            "age_min": 18,
            "geo_locations": _LEADS_OFFSITE_GEO_LOCATIONS,
        }
        save_spy.assert_called_once_with(creative)
        update_mock.assert_called_once_with(7, {"channel_creative": creative})
        assert result["adchannel_id"] == 7
        assert result["locations"] == _LEADS_OFFSITE_LOCATIONS
        assert result["locations_valid"] is True

    @staticmethod
    def _assert_standard_outcome(result, creative, update_mock, save_spy):
        ad = creative["ads"][0]
        story_spec = ad["adCreative"]["object_story_spec"]
        assert story_spec["locations"] == _LEADS_OFFSITE_LOCATIONS
        assert story_spec["locations_valid"] is True
        assert creative["targeting"] == {
            "age_min": 18,
            "geo_locations": _LEADS_OFFSITE_GEO_LOCATIONS,
        }
        save_spy.assert_called_once_with(creative)
        update_mock.assert_called_once_with(
            8, {"channel_creative": {**creative, "ads": [ad]}}
        )
        assert result["adchannel_id"] == 8
        assert result["locations"] == _LEADS_OFFSITE_LOCATIONS
        assert result["locations_valid"] is True

    # ------------------------------------------------------------------
    # Happy paths for Combinación_Leads_Offsite (Req 10.6, 14.9)
    # ------------------------------------------------------------------

    def test_dynamic_happy_path_leads_offsite(self, use_case_factory):
        """DYNAMIC + Combinación_Leads_Offsite finishes without exception,
        annotates ``asset_feed_spec``/``targeting.geo_locations`` and
        persists through ``AdChannelRepository`` via exactly one
        ``_save_creative_to_publish`` call.

        Requirements: 10.6, 14.9
        """
        outcome = self._run(use_case_factory, "DYNAMIC", _COMBINATION_LEADS_OFFSITE)
        self._assert_dynamic_outcome(*outcome)

    def test_standard_happy_path_leads_offsite(self, use_case_factory):
        """STANDARD + Combinación_Leads_Offsite finishes without exception,
        annotates ``object_story_spec``/``targeting.geo_locations`` and
        persists through ``AdChannelRepository`` via exactly one
        ``_save_creative_to_publish`` call.

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
        assert offsite_creative["targeting"] == leadgen_creative["targeting"]
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
