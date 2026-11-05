"""Characterization test suite for ``FacebookSavePreCheckCTAsUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookSavePreCheckCTAsUseCase``
(its Rama_DYNAMIC ``_validate_ctas``, its new Rama_STANDARD private method
``_validate_ctas_standard`` and its ``execute()``) and the inherited subset of
``FacebookSavePreCheckBaseUseCase`` that it invokes: the constructor,
``_get_ad_channel``, ``_get_campaign_setup``, ``_set_channel_id`` and
``_build_response``.

This module fixes the current observable behaviour, including already
existing quirks (the always-``{}`` ``complete_campaign_data`` passed to the
grandparent constructor, the mutable default ``pre_check_data: PreCheckDataDict
= {}`` in the constructor signature, and the transparent
``try/except Exception as e: raise e`` pass-through in ``execute()``). No
production code is modified or "fixed" by this suite.

Builders/fixtures below replicate, verbatim in style, the ones already used
by the sibling suites ``test_facebook_save_pre_check_texts.py`` and
``test_facebook_save_pre_check_images.py``.

Requirements: 8.2
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.exceptions.base import DataNotFoundException, NotAccessException
from app.v2.use_cases.facebook_validator_service import MetaAdsValidator
from app.v2.use_cases.meta_ads import (
    FacebookSavePreCheckBaseUseCase,
    FacebookSavePreCheckCTAsUseCase,
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


def make_pre_check_ctas_data(**overrides):
    """Build a fresh ``pre_check_ctas_data`` (``PreCheckDataDict``-like) dict.

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

    Empty by default; callers compose it with ``link_data=make_link_data(...)``
    to characterize the Rama_STANDARD scenarios of Caso_de_Uso_CTAs.

    Requirements: 8.2
    """
    data = {}
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict (``object_story_spec['link_data']``).

    Every field the STANDARD branch of Caso_de_Uso_CTAs reads/writes
    (``name``, ``message``, ``description``, ``image_url``, ``link``,
    ``call_to_action``) defaults to ``None``, so a scenario can override
    only the field(s) it cares about (typically ``call_to_action``) while
    still asserting that the rest were left untouched by
    ``_validate_ctas_standard``.

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


@pytest.fixture
def use_case_factory():
    """Fixture that builds a factory for ``FacebookSavePreCheckCTAsUseCase``
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

    If ``pre_check_ctas_data`` is omitted, a fresh
    ``make_pre_check_ctas_data()`` is used so accidental constructor
    edge-case scenarios (explicit ``None``, mutable defaults) are not
    triggered here; dedicated tests for those construct the use case
    directly, without this fixture.

    Requirements: 8.2
    """

    def _factory(user_id="user-1", pre_check_ctas_data=None):
        if pre_check_ctas_data is None:
            pre_check_ctas_data = make_pre_check_ctas_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookSavePreCheckCTAsUseCase(
                user_id, pre_check_ctas_data
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
    ``FacebookSavePreCheckCTAsUseCase`` performs any network request:
    ``MetaAdsValidator.validate_cta_for_goal`` is a pure, in-memory
    function. Its inclusion keeps this suite consistent in style with its
    sibling suites and protects against a future regression that
    accidentally introduced a network call in this file.

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


class TestStandardBranchCTAValidationSuccess:
    """Tests for the success scenario of the Rama_STANDARD CTA validation
    performed by ``_validate_ctas_standard`` (invoked from ``execute()``):
    exactly one CTA_Candidato (``Valor_Candidato == 1``) for which
    ``MetaAdsValidator.validate_cta_for_goal`` resolves to ``valid=True``.

    Like ``FacebookSavePreCheckTextsUseCase``'s inline STANDARD branch,
    this scenario exercises ``execute()`` end to end (with
    ``_save_creative_to_publish``/``_build_response`` left unpatched,
    running for real) and asserts on the resulting ``Link_Data``
    (``object_story_spec['link_data']``) mutation, conforme al
    Contrato_de_Anotación_STANDARD.

    ``MetaAdsValidator.validate_cta_for_goal`` is exercised for real
    (not patched): ``OUTCOME_LEADS``/``QUALITY_LEAD`` is a combination
    for which ``LEARN_MORE`` is a known-allowed CTA
    (``facebook_validator_service.LEADS_GOAL_ALLOWED_CTAS``), so the real
    validator deterministically returns ``True`` for it, without needing
    to patch the collaborator.

    Requirements: 3.2, 3.3
    """

    def test_single_candidate_with_valid_cta_is_annotated_onto_link_data(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and exactly one CTA_Candidato (``Valor_Candidato == 1``) whose
        ``value`` is allowed for the given objective/optimization goal,
        verify that ``execute()`` annotates the pre-existing ``Link_Data``
        dict, by identity, with::

            link_data['call_to_action'] == {
                'type': {'value': cta_value, 'valid': True},
            }

        Requirements: 3.2, 3.3
        """
        cta_value = "LEARN_MORE"
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": cta_value}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="STANDARD",
            attributes={
                "meta_campaign_mode": "STANDARD",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert story_spec["link_data"] is link_data
        assert link_data["call_to_action"] == {
            "type": {"value": cta_value, "valid": True},
        }


class TestStandardBranchCTAValidationFailure:
    """Tests for the failure scenario of the Rama_STANDARD CTA validation
    performed by ``_validate_ctas_standard`` (invoked from ``execute()``):
    exactly one CTA_Candidato (``Valor_Candidato == 1``) for which
    ``MetaAdsValidator.validate_cta_for_goal`` resolves to ``valid=False``.

    Mirrors ``TestStandardBranchCTAValidationSuccess`` in every respect
    (same builders, same end-to-end ``execute()`` exercise) except for the
    chosen CTA value, which is deliberately outside the allowed list for
    the given objective/optimization goal.

    ``MetaAdsValidator.validate_cta_for_goal`` is exercised for real
    (not patched): ``OUTCOME_LEADS``/``QUALITY_LEAD`` only allows
    ``{"SIGN_UP", "APPLY_NOW", "BOOK_NOW", "DOWNLOAD", "GET_QUOTE",
    "LEARN_MORE"}`` (``facebook_validator_service.LEADS_GOAL_ALLOWED_CTAS``);
    ``SHOP_NOW`` is not a member of that set, so the real validator
    deterministically returns ``False`` for it, without needing to patch
    the collaborator.

    Requirements: 3.2, 3.3
    """

    def test_single_candidate_with_invalid_cta_is_annotated_onto_link_data(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and exactly one CTA_Candidato (``Valor_Candidato == 1``) whose
        ``value`` is NOT allowed for the given objective/optimization goal,
        verify that ``execute()`` annotates the pre-existing ``Link_Data``
        dict, by identity, with::

            link_data['call_to_action'] == {
                'type': {'value': cta_value, 'valid': False},
            }

        Requirements: 3.2, 3.3
        """
        cta_value = "SHOP_NOW"
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": cta_value}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="STANDARD",
            attributes={
                "meta_campaign_mode": "STANDARD",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert story_spec["link_data"] is link_data
        assert link_data["call_to_action"] == {
            "type": {"value": cta_value, "valid": False},
        }


class TestStandardBranchCTAValidationSkipped:
    """Tests for the two Rama_STANDARD scenarios of Caso_de_Uso_CTAs in
    which ``_validate_ctas_standard`` deliberately does not invoke
    ``MetaAdsValidator.validate_cta_for_goal`` at all:

    - ``Valor_Candidato == 0`` (``call_to_action_types = []``):
      ``link_data['call_to_action']`` is removed/absent (via ``.pop``),
      even when a previous truthy value was present.
    - ``Valor_Candidato > 1`` (``call_to_action_types`` with two or more
      entries): ``link_data['call_to_action']`` is preserved unmodified,
      by identity/equality, regardless of the previous value.

    Both scenarios exercise ``execute()`` end to end (with
    ``_validate_ctas_standard``/``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real); only
    ``MetaAdsValidator.validate_cta_for_goal`` is patched, exclusively to
    assert it was never called.

    Requirements: 3.4
    """

    @pytest.mark.parametrize(
        "call_to_action_types, expected_call_to_action",
        [
            pytest.param(
                [],
                None,
                id="zero_candidates_removes_call_to_action",
            ),
            pytest.param(
                [{"value": "LEARN_MORE"}, {"value": "SHOP_NOW"}],
                {"some": "previous-value"},
                id="more_than_one_candidate_preserves_call_to_action",
            ),
        ],
    )
    def test_validate_cta_for_goal_not_invoked(
        self, use_case_factory, call_to_action_types, expected_call_to_action
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and either zero or more-than-one CTA_Candidato, verify that
        ``execute()`` never invokes
        ``MetaAdsValidator.validate_cta_for_goal``, and that
        ``link_data['call_to_action']`` ends up either absent (zero
        candidates) or unchanged (more than one candidate).

        Requirements: 3.4
        """
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=call_to_action_types
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        link_data = make_link_data(call_to_action={"some": "previous-value"})
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="STANDARD",
            attributes={
                "meta_campaign_mode": "STANDARD",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch.object(
            MetaAdsValidator, "validate_cta_for_goal"
        ) as mock_validate_cta_for_goal:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_validate_cta_for_goal.assert_not_called()
        assert story_spec["link_data"] is link_data
        if expected_call_to_action is None:
            assert "call_to_action" not in link_data
        else:
            assert link_data["call_to_action"] == expected_call_to_action


class TestStandardBranchCTAsMissingLinkData:
    """Tests for the Rama_STANDARD CTA validation block within
    ``execute()`` when ``story_spec`` lacks the ``link_data`` key
    entirely, or carries it with an explicit ``None`` value.

    Like its siblings ``TestStandardBranchCTAValidationSuccess``,
    ``TestStandardBranchCTAValidationFailure`` and
    ``TestStandardBranchCTAValidationSkipped``, this class exercises
    ``execute()`` end to end (with ``_validate_ctas_standard``/
    ``_save_creative_to_publish``/``_build_response`` left unpatched,
    running for real). ``story_spec`` itself is built directly via
    ``make_object_story_spec()`` (not via the ``link_data=...`` override
    used by the sibling classes above), with an unrelated key added when
    ``link_data`` is meant to be absent entirely, so ``story_spec`` stays
    truthy (an empty dict would make the surrounding
    ``elif ... and story_spec:`` guard in ``execute()`` skip the
    STANDARD branch altogether, which would make this scenario vacuous).

    Each scenario provides exactly one CTA_Candidato (``Valor_Candidato ==
    1``) whose ``value`` (``LEARN_MORE``) is deterministically valid for
    the chosen ``OUTCOME_LEADS``/``QUALITY_LEAD`` objective/optimization
    goal combination (per ``TestStandardBranchCTAValidationSuccess``), so
    the STANDARD logic actually writes into ``link_data``, letting the
    assertions below confirm that a brand new ``link_data`` dict is
    created and reassigned onto ``story_spec['link_data']``.

    Requirements: 3.5
    """

    @pytest.mark.parametrize(
        "build_story_spec",
        [
            pytest.param(
                lambda: make_object_story_spec(some_key="some_value"),
                id="missing-link-data-key",
            ),
            pytest.param(
                lambda: make_object_story_spec(link_data=None),
                id="explicit-none-link-data",
            ),
        ],
    )
    def test_missing_or_none_link_data_is_replaced_by_new_dict(
        self, use_case_factory, build_story_spec
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        that either omits the ``link_data`` key entirely or carries it
        with an explicit ``None`` value, and exactly one CTA_Candidato
        whose ``value`` is valid for the given objective/optimization
        goal, verify that ``execute()``:

        - Raises no exception.
        - Creates a brand new dict and reassigns it onto
          ``story_spec['link_data']`` (it is a real dict, not ``None``
          and not absent, once ``execute()`` returns).
        - Annotates ``call_to_action`` onto that same new dict.

        Requirements: 3.5
        """
        cta_value = "LEARN_MORE"
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": cta_value}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        story_spec = build_story_spec()
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="STANDARD",
            attributes={
                "meta_campaign_mode": "STANDARD",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        link_data = story_spec["link_data"]
        assert isinstance(link_data, dict)
        assert link_data is not None

        assert link_data["call_to_action"] == {
            "type": {"value": cta_value, "valid": True},
        }


class TestStandardBranchFullExecuteResponse:
    """Tests for the full ``execute()`` round trip in STANDARD mode: with a
    truthy ``story_spec`` built via ``make_link_data()`` and exactly one
    CTA_Candidato (``Valor_Candidato == 1``) whose ``value`` is allowed for
    the given objective/optimization goal, verify that the dict *returned*
    by ``execute()`` (not just the mutated ``link_data``) reflects
    ``call_to_action_types`` conforme a la anotación esperada.

    Unlike the sibling classes above (which only assert on the mutated
    ``story_spec['link_data']``), this class exercises ``execute()``
    completely unpatched -- ``_validate_ctas_standard`` is NOT patched,
    ``MetaAdsValidator.validate_cta_for_goal`` runs for real, and so do
    ``_save_creative_to_publish``/``_build_response`` -- and asserts on
    ``execute()``'s return value, characterizing the STANDARD-mode branch
    of ``_build_response`` (inherited from the Caso_de_Uso_Padre), which
    maps ``link_data.get('call_to_action')`` into
    ``[call_to_action.get('type', {})] if call_to_action else []``.

    ``MetaAdsValidator.validate_cta_for_goal`` is exercised for real (not
    patched): ``OUTCOME_LEADS``/``QUALITY_LEAD`` is a combination for
    which ``LEARN_MORE`` is a known-allowed CTA
    (``facebook_validator_service.LEADS_GOAL_ALLOWED_CTAS``), so the real
    validator deterministically returns ``True`` for it, without needing
    to patch the collaborator.

    Requirements: 8.3
    """

    def test_execute_returns_response_reflecting_call_to_action_types_annotation(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        (via ``make_link_data()``) and exactly one CTA_Candidato whose
        ``value`` is allowed for the given objective/optimization goal,
        verify that the dict returned by ``execute()`` has::

            response["call_to_action_types"] == [
                {"value": cta_value, "valid": True},
            ]

        conforming exactly to ``_build_response``'s
        ``[call_to_action.get('type', {})] if call_to_action else []``
        mapping for the STANDARD-mode (``object_story_spec``/``link_data``)
        branch, where ``call_to_action = link_data.get('call_to_action') or {}``.

        Requirements: 8.3
        """
        cta_value = "LEARN_MORE"
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": cta_value}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        ad = make_ad(ad_creative=ad_creative, ad_id="ad-1")
        creative = make_creative(ads=[ad], name="My Creative", id="adset-1")
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="STANDARD",
            attributes={
                "meta_campaign_mode": "STANDARD",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

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
        # (``link_data`` was annotated as expected), before asserting on
        # the returned response itself.
        assert story_spec["link_data"] is link_data
        assert link_data["call_to_action"] == {
            "type": {"value": cta_value, "valid": True},
        }

        assert response["call_to_action_types"] == [
            {"value": cta_value, "valid": True},
        ]


class TestStandardSpecDoesNotRegressDynamicBranch:
    """Tests for Requirement 7.1/7.3/7.4 (no regresión): confirm that adding
    the Rama_STANDARD ``_validate_ctas_standard`` method and its ``elif``
    block to ``FacebookSavePreCheckCTAsUseCase.execute()`` did not change
    the observable behaviour of the pre-existing Rama_DYNAMIC
    (``_validate_ctas``), and that the STANDARD ``elif`` never runs when
    ``meta_campaign_mode == "DYNAMIC"``.

    Unlike its sibling suite ``test_facebook_save_pre_check_texts.py``
    (which already had pre-existing DYNAMIC-branch test classes to extend
    without modifying), this file has no pre-existing DYNAMIC-branch test
    classes: this is the sole DYNAMIC-branch coverage for
    ``FacebookSavePreCheckCTAsUseCase`` in this suite, added specifically
    to characterize the no-regression guarantee required by this
    specification. It mirrors the pattern already used by the
    DYNAMIC-branch invocation tests of ``test_facebook_save_pre_check_images.py``
    (patching the DYNAMIC-branch private method on the instance and
    asserting on the exact call/arguments), since ``_validate_ctas``'s own
    internal behaviour is already characterized end to end by the sibling
    ``meta-ads-standard-precheck-validation`` suite, not by this one.

    Requirements: 7.1, 7.3, 7.4
    """

    def test_dynamic_branch_validate_ctas_still_invoked_exactly_as_before(
        self, use_case_factory
    ):
        """When ``meta_campaign_mode == "DYNAMIC"`` and ``asset_feed``
        (``ad_creative['asset_feed_spec']``) is a truthy dict, ``execute()``
        invokes ``_validate_ctas`` with that exact same ``asset_feed``
        object (by identity), plus the ``campaign_objective``/
        ``optimization_goal`` read from ``campaign_setup['attributes']``,
        exactly as it already did before this specification introduced the
        STANDARD ``elif`` block.

        ``_validate_ctas`` is patched on the instance so this test stays
        focused purely on the invocation and its arguments, independent of
        its internal behaviour; ``_save_creative_to_publish``/
        ``_build_response`` are left unpatched and run for real, since
        neither depends on ``_validate_ctas`` having actually mutated
        ``asset_feed``.

        Requirements: 7.1
        """
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": "LEARN_MORE"}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
        )

        asset_feed = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(
            meta_campaign_mode="DYNAMIC",
            attributes={
                "meta_campaign_mode": "DYNAMIC",
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "QUALITY_LEAD",
            },
        )

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_validate_ctas"
        ) as mock_validate_ctas:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_validate_ctas.assert_called_once_with(
            asset_feed, "OUTCOME_LEADS", "QUALITY_LEAD"
        )
        assert mock_validate_ctas.call_args.args[0] is asset_feed

    def test_standard_logic_does_not_execute_when_mode_is_dynamic(
        self, use_case_factory
    ):
        """Build a scenario where ``story_spec``/``link_data`` IS present
        and truthy, in addition to a truthy ``asset_feed``, with
        ``meta_campaign_mode="DYNAMIC"``, and verify that
        ``_validate_ctas_standard`` is never invoked and ``link_data`` is
        left completely untouched (no ``call_to_action`` annotation
        added): the STANDARD ``elif`` never ran because the ``if``
        (DYNAMIC) condition already matched first.

        ``_validate_ctas`` is also patched on the instance so ``execute()``
        does not need a fully-shaped ``asset_feed`` beyond what the
        extraction/validation block reads, keeping this test focused
        exclusively on confirming ``_validate_ctas_standard`` is skipped.

        Requirements: 7.3, 7.4
        """
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=[{"value": "LEARN_MORE"}]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_ctas_data=pre_check_ctas_data)
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

        link_data_snapshot = dict(link_data)

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_validate_ctas"
        ), patch.object(
            use_case, "_validate_ctas_standard"
        ) as mock_validate_ctas_standard:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_validate_ctas_standard.assert_not_called()
        assert link_data == link_data_snapshot
        assert link_data["call_to_action"] is None
        assert story_spec["link_data"] is link_data


# ---------------------------------------------------------------------------
# Combinación_Leads_Offsite (OUTCOME_LEADS + OFFSITE_CONVERSIONS)
# ---------------------------------------------------------------------------

LEADS_OBJECTIVE = "OUTCOME_LEADS"
LEADS_OFFSITE_GOAL = "OFFSITE_CONVERSIONS"
LEAD_GENERATION_GOAL = "LEAD_GENERATION"
SALES_OBJECTIVE = "OUTCOME_SALES"

# CTAs_Leads_Offsite, as defined in the Glossary of the spec (literal on
# purpose, so the tests do not just echo the production constant).
LEADS_OFFSITE_CTAS = frozenset({
    "LEARN_MORE", "SIGN_UP", "SUBSCRIBE", "ORDER_NOW", "SHOP_NOW", "APPLY_NOW",
    "BOOK_NOW", "CONTACT_US", "GET_OFFER", "GET_QUOTE", "DOWNLOAD", "SEE_MENU",
    "SEE_DETAILS", "GET_SHOWTIMES", "REQUEST_TIME", "BUY_TICKETS", "LISTEN_NOW",
    "PLAY_GAME", "WATCH_MORE", "NO_BUTTON",
})

DYNAMIC_AD_CHANNEL_ID = 101
STANDARD_AD_CHANNEL_ID = 202

# Hypothesis strategies for Property 12.
# Members of CTAs_Leads_Offsite, optionally lowercased / with spaces instead
# of underscores / with surrounding whitespace, so normalization is exercised.
_LEADS_OFFSITE_CTA_VALUES = st.builds(
    lambda cta, lower, spaces, pad: (
        pad
        + (cta.lower() if lower else cta).replace("_", " " if spaces else "_")
        + pad
    ),
    st.sampled_from(sorted(LEADS_OFFSITE_CTAS)),
    st.booleans(),
    st.booleans(),
    st.sampled_from(["", " ", "  "]),
)
# Arbitrary values: known non-members plus free text (which may, rarely,
# normalize to a member; the oracle in the test handles that).
_NON_LEADS_OFFSITE_CTA_VALUES = st.one_of(
    st.sampled_from(["WHATSAPP_MESSAGE", "MESSAGE_PAGE", "CALL_NOW", "INSTALL_APP"]),
    st.text(max_size=20),
)
# Missing key (``ABSENT``), explicit ``None`` or empty string.
_ABSENT_OR_EMPTY_CTA_VALUES = st.sampled_from([ABSENT, None, ""])


class TestLeadsOffsiteSaveCtas:
    """Save PreCheck of CTAs for Combinación_Leads_Offsite.

    ``execute()`` runs end to end: ``_validate_ctas``,
    ``_validate_ctas_standard``, ``_save_creative_to_publish``,
    ``_build_response`` and ``MetaAdsValidator`` are real; only the
    repositories (``use_case_factory``) and ``redis_client`` are doubles.

    ``_run_scenario`` is the shared entry point for the example tests below
    and for the property test of this class (Property 12): it accepts any
    list of CTA dicts and returns the mutated structures plus the mocked
    ``AdChannelRepository``.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.6, 10.7, 10.8, 14.9
    """

    @staticmethod
    def _campaign_setup(mode, objective=LEADS_OBJECTIVE, goal=LEADS_OFFSITE_GOAL):
        return make_campaign_setup(
            meta_campaign_mode=mode,
            attributes={
                "meta_campaign_mode": mode,
                "meta_campaign_objective": objective,
                "meta_optimization_goal": goal,
                "meta_pixel_id": "123456789",
                "meta_conversion_event": "LEAD",
            },
        )

    @classmethod
    def _run_scenario(
        cls,
        use_case_factory,
        mode,
        call_to_action_types,
        objective=LEADS_OBJECTIVE,
        goal=LEADS_OFFSITE_GOAL,
        previous_call_to_action=None,
    ):
        """Build a fresh creative for ``mode``, execute the use case and
        return a dict with ``result``, ``creative``, ``asset_feed``
        (DYNAMIC), ``link_data`` (STANDARD) and ``ad_channel_repo``.
        """
        pre_check_ctas_data = make_pre_check_ctas_data(
            call_to_action_types=call_to_action_types
        )
        use_case, ad_channel_repo, campaign_publish_repo = use_case_factory(
            pre_check_ctas_data=pre_check_ctas_data
        )

        asset_feed = None
        link_data = None
        if mode == "DYNAMIC":
            asset_feed = make_asset_feed_spec(
                ad_channel_id=DYNAMIC_AD_CHANNEL_ID,
                promoted_object_valid=True,
            )
            ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        else:
            link_data = make_link_data(call_to_action=previous_call_to_action)
            story_spec = make_object_story_spec(
                link_data=link_data, ad_channel_id=STANDARD_AD_CHANNEL_ID
            )
            ad_creative = make_ad_creative(object_story_spec=story_spec)

        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel(channel_creative=creative)
        )
        campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            cls._campaign_setup(mode, objective, goal)
        )

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"
            result = use_case.execute()

        return {
            "result": result,
            "creative": creative,
            "asset_feed": asset_feed,
            "link_data": link_data,
            "ad_channel_repo": ad_channel_repo,
        }

    # -- Rama_DYNAMIC -------------------------------------------------------

    def test_dynamic_happy_path_annotates_ctas_and_persists_once(
        self, use_case_factory
    ):
        """Allowed, normalizable, disallowed and missing values are all
        kept in order and annotated per CTAs_Leads_Offsite; the valid
        amount is set and ``promoted_object_valid`` is left untouched.

        Requirements: 10.1, 10.2, 10.6, 10.7, 14.9
        """
        ctas = [
            {"value": "SHOP_NOW"},
            {"value": " see menu "},
            {"value": "WHATSAPP_MESSAGE"},
            {"value": None},
            {},
        ]
        expected_values = [cta.get("value") for cta in ctas]

        out = self._run_scenario(use_case_factory, "DYNAMIC", ctas)

        asset_feed = out["asset_feed"]
        annotated = asset_feed["call_to_action_types"]
        assert [cta.get("value") for cta in annotated] == expected_values
        assert [cta["valid"] for cta in annotated] == [True, True, False, False, False]
        assert asset_feed["call_to_action_types_valid_amount"] is True
        assert asset_feed["promoted_object_valid"] is True

        out["ad_channel_repo"].update.assert_called_once_with(
            DYNAMIC_AD_CHANNEL_ID, {"channel_creative": out["creative"]}
        )
        persisted_feed = out["ad_channel_repo"].update.call_args.args[1][
            "channel_creative"
        ]["ads"][0]["adCreative"]["asset_feed_spec"]
        assert persisted_feed["promoted_object_valid"] is True
        assert out["result"] is not None

    def test_dynamic_all_leads_offsite_ctas_are_valid(self, use_case_factory):
        """Every member of CTAs_Leads_Offsite is annotated ``valid=True``.

        Requirements: 10.1
        """
        ctas = [{"value": value} for value in sorted(LEADS_OFFSITE_CTAS)]

        out = self._run_scenario(use_case_factory, "DYNAMIC", ctas)

        assert all(
            cta["valid"] is True
            for cta in out["asset_feed"]["call_to_action_types"]
        )

    @pytest.mark.parametrize(
        "amount, expected_valid_amount",
        [
            pytest.param(0, False, id="zero_ctas"),
            pytest.param(1, True, id="one_cta"),
            pytest.param(5, True, id="max_ctas"),
            pytest.param(6, False, id="above_max_ctas"),
        ],
    )
    def test_dynamic_valid_amount_matches_lead_generation(
        self, use_case_factory, amount, expected_valid_amount
    ):
        """``call_to_action_types_valid_amount`` follows
        ``is_valid_ctas_amount`` with the same result as ``LEAD_GENERATION``.

        Requirements: 10.2
        """
        offsite = self._run_scenario(
            use_case_factory, "DYNAMIC", [{"value": "LEARN_MORE"} for _ in range(amount)]
        )
        lead_gen = self._run_scenario(
            use_case_factory,
            "DYNAMIC",
            [{"value": "LEARN_MORE"} for _ in range(amount)],
            goal=LEAD_GENERATION_GOAL,
        )

        offsite_amount = offsite["asset_feed"]["call_to_action_types_valid_amount"]
        lead_gen_amount = lead_gen["asset_feed"]["call_to_action_types_valid_amount"]
        assert offsite_amount is expected_valid_amount
        assert offsite_amount == lead_gen_amount
        assert len(offsite["asset_feed"]["call_to_action_types"]) == amount
        offsite["ad_channel_repo"].update.assert_called_once()
        assert offsite["asset_feed"]["promoted_object_valid"] is True

    # -- Rama_STANDARD ------------------------------------------------------

    @pytest.mark.parametrize(
        "cta_value, expected_valid",
        [
            pytest.param("SHOP_NOW", True, id="allowed"),
            pytest.param("learn more", True, id="allowed_normalized"),
            pytest.param("WHATSAPP_MESSAGE", False, id="not_allowed"),
        ],
    )
    def test_standard_happy_path_single_cta(
        self, use_case_factory, cta_value, expected_valid
    ):
        """Exactly one CTA writes ``{'type': {'value', 'valid'}}`` onto
        ``link_data`` and persists the creative once.

        Requirements: 10.3, 10.6, 14.9
        """
        out = self._run_scenario(
            use_case_factory, "STANDARD", [{"value": cta_value}]
        )

        assert out["link_data"]["call_to_action"] == {
            "type": {"value": cta_value, "valid": expected_valid},
        }
        out["ad_channel_repo"].update.assert_called_once()
        ad_channel_id, data = out["ad_channel_repo"].update.call_args.args
        assert ad_channel_id == STANDARD_AD_CHANNEL_ID
        persisted_link_data = data["channel_creative"]["ads"][0]["adCreative"][
            "object_story_spec"
        ]["link_data"]
        assert persisted_link_data["call_to_action"] == {
            "type": {"value": cta_value, "valid": expected_valid},
        }
        assert out["result"] is not None

    @pytest.mark.parametrize(
        "call_to_action_types",
        [
            pytest.param([], id="zero_ctas"),
            pytest.param(
                [{"value": "LEARN_MORE"}, {"value": "SHOP_NOW"}],
                id="more_than_one_cta",
            ),
        ],
    )
    def test_standard_zero_or_many_ctas_match_lead_generation(
        self, use_case_factory, call_to_action_types
    ):
        """Zero CTAs removes ``call_to_action``; more than one leaves it
        unchanged; both identical to ``LEAD_GENERATION``.

        Requirements: 10.4, 10.6
        """
        previous = {"type": {"value": "SIGN_UP", "valid": True}}

        offsite = self._run_scenario(
            use_case_factory,
            "STANDARD",
            [dict(cta) for cta in call_to_action_types],
            previous_call_to_action=dict(previous),
        )
        lead_gen = self._run_scenario(
            use_case_factory,
            "STANDARD",
            [dict(cta) for cta in call_to_action_types],
            goal=LEAD_GENERATION_GOAL,
            previous_call_to_action=dict(previous),
        )

        if not call_to_action_types:
            assert "call_to_action" not in offsite["link_data"]
        else:
            assert offsite["link_data"]["call_to_action"] == previous
        assert offsite["link_data"] == lead_gen["link_data"]
        assert offsite["result"] == lead_gen["result"]
        offsite["ad_channel_repo"].update.assert_called_once()

    # -- Otras_Combinaciones (regression) -----------------------------------

    @pytest.mark.parametrize(
        "objective, goal, expected_valid",
        [
            pytest.param(
                LEADS_OBJECTIVE, LEAD_GENERATION_GOAL, [False, False, True],
                id="leads_lead_generation",
            ),
            pytest.param(
                SALES_OBJECTIVE, LEADS_OFFSITE_GOAL, [True, False, True],
                id="sales_offsite_conversions",
            ),
        ],
    )
    @pytest.mark.parametrize("mode", ["DYNAMIC", "STANDARD"])
    def test_other_combinations_keep_their_cta_rules(
        self, use_case_factory, mode, objective, goal, expected_valid
    ):
        """Otras_Combinaciones keep annotating against their own allowed
        CTA set (``SHOP_NOW``/``SEE_MENU``/``SIGN_UP``), not against
        CTAs_Leads_Offsite, where all three would be valid.

        Requirements: 10.8
        """
        values = ["SHOP_NOW", "SEE_MENU", "SIGN_UP"]
        if mode == "DYNAMIC":
            out = self._run_scenario(
                use_case_factory,
                mode,
                [{"value": value} for value in values],
                objective=objective,
                goal=goal,
            )
            annotated = out["asset_feed"]["call_to_action_types"]
            assert [cta["valid"] for cta in annotated] == expected_valid
            assert out["asset_feed"]["call_to_action_types_valid_amount"] is True
            assert out["asset_feed"]["promoted_object_valid"] is True
            out["ad_channel_repo"].update.assert_called_once()
        else:
            for value, expected in zip(values, expected_valid):
                out = self._run_scenario(
                    use_case_factory,
                    mode,
                    [{"value": value}],
                    objective=objective,
                    goal=goal,
                )
                assert out["link_data"]["call_to_action"] == {
                    "type": {"value": value, "valid": expected},
                }
                out["ad_channel_repo"].update.assert_called_once()

    # -- Property 12 --------------------------------------------------------

    @staticmethod
    def _expected_valid(value):
        """Oracle: ``True`` iff ``value`` is a string whose normalized form
        (``strip().upper().replace(' ', '_')``) belongs to the literal
        CTAs_Leads_Offsite; absent/``None``/empty/non-string are ``False``.
        """
        if not isinstance(value, str):
            return False
        return value.strip().upper().replace(" ", "_") in LEADS_OFFSITE_CTAS

    # Feature: meta-ads-leads-offsite-conversions, Property 12: Save PreCheck de CTAs para Combinación_Leads_Offsite
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(
        values=st.lists(
            st.one_of(
                _LEADS_OFFSITE_CTA_VALUES,
                _NON_LEADS_OFFSITE_CTA_VALUES,
                _ABSENT_OR_EMPTY_CTA_VALUES,
            ),
            min_size=0,
            max_size=8,
        ),
        standard_value=st.one_of(
            _LEADS_OFFSITE_CTA_VALUES,
            _NON_LEADS_OFFSITE_CTA_VALUES,
            st.none(),
        ),
    )
    def test_property_save_ctas_leads_offsite(
        self, use_case_factory, values, standard_value
    ):
        """DYNAMIC keeps length/order, annotates membership in
        CTAs_Leads_Offsite and sets the valid amount; STANDARD with exactly
        one CTA writes ``{'type': {'value', 'valid'}}``. Both persist once.

        **Validates: Requirements 10.1, 10.2, 10.3, 10.6**
        """
        # Rama_DYNAMIC
        ctas = [
            {} if value is ABSENT else {"value": value} for value in values
        ]
        expected_values = [cta.get("value") for cta in ctas]

        out = self._run_scenario(use_case_factory, "DYNAMIC", ctas)

        annotated = out["asset_feed"]["call_to_action_types"]
        assert [cta.get("value") for cta in annotated] == expected_values
        assert [cta["valid"] for cta in annotated] == [
            self._expected_valid(value) for value in expected_values
        ]
        assert out["asset_feed"]["call_to_action_types_valid_amount"] is (
            MetaAdsValidator.is_valid_ctas_amount(annotated)
        )
        out["ad_channel_repo"].update.assert_called_once_with(
            DYNAMIC_AD_CHANNEL_ID, {"channel_creative": out["creative"]}
        )

        # Rama_STANDARD (exactly one CTA)
        out = self._run_scenario(
            use_case_factory, "STANDARD", [{"value": standard_value}]
        )

        assert out["link_data"]["call_to_action"] == {
            "type": {
                "value": standard_value,
                "valid": self._expected_valid(standard_value),
            },
        }
        out["ad_channel_repo"].update.assert_called_once_with(
            STANDARD_AD_CHANNEL_ID, {"channel_creative": out["creative"]}
        )
