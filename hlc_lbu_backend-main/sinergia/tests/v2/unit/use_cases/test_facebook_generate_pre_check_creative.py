"""Characterization test suite for ``FacebookGeneratePreCheckCreativeUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookGeneratePreCheckCreativeUseCase``
(and the inherited ``__init__``, ``_get_decoded_access_token`` and
``_build_meta_payload`` from ``FacebookTestCreativeUploadUseCase``).

This module fixes the current observable behaviour, including already
existing quirks (e.g. the duplicated ``assets-budget-error`` slug, the
inconsistent ``ad_sets`` default, the ``TypeError`` at the end of
``execute()`` when ``objective`` is not present in ``META_ODAX_CTA_MAPPING``,
and the ``AttributeError`` raised by the constructor when
``complete_campaign_data=None``). No production code is modified or "fixed"
by this suite.

Requirements: 1.1, 1.8, 14.1, 14.2, 14.3
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import call, patch

import pytest

from app.exceptions.base import (
    DataNotFoundException,
    MetaException,
    NotAccessException,
    ParametersNotFoundException,
    PermissionDeniedException,
    RateLimitExceededException,
    RESTClientException,
    StrapiException,
)
from hypothesis import HealthCheck, given, settings, strategies as st

from app.v2.use_cases.meta_ads import (
    AwarenessOptimizationGoal,
    CampaignObjective,
    FacebookGeneratePreCheckCreativeUseCase,
    LeadsOptimizationGoal,
    MetaAdsValidator,
    SalesOptimizationGoal,
)


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it from the resulting dict" from "this key
    was provided by the caller with the value ``None``".

    Requirements: 1.1, 14.3
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


def make_campaign_data_dict(**overrides):
    """Build a fresh ``complete_campaign_data`` (``CampaignDataDict``-like) dict.

    Every invocation returns a brand new dict; no mutable default arguments
    are used, so callers can freely mutate the returned value without
    affecting other tests.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {
        "ad_account_id": "act-1",
        "page_id": "page-1",
        "objective": "OUTCOME_AWARENESS",
        "optimization_goal": "REACH",
        "lead_gen_form_id": None,
        "whatsapp_number_id": None,
        # Inert for Otras_Combinaciones; required by the
        # OUTCOME_LEADS/OFFSITE_CONVERSIONS combination (avoids META013).
        # Requirements: 13.3, 13.4
        "conversion_event": "LEAD",
    }
    data.update(overrides)
    return data


def make_asset_feed_spec(**overrides):
    """Build a fresh ``asset_feed_spec`` dict with empty collections.

    Requirements: 1.1, 14.1, 14.2, 14.3
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

    ``link_data`` defaults to ``None``; pass ``link_data=make_link_data(...)``
    to populate it.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {
        "link_data": None,
    }
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {
        "call_to_action": None,
        "image_url": None,
        "name": None,
        "message": None,
    }
    data.update(overrides)
    return data


def make_ad_creative(asset_feed_spec=ABSENT, object_story_spec=ABSENT, name="Creative", **overrides):
    """Build a fresh ``adCreative`` dict.

    ``asset_feed_spec``/``object_story_spec`` default to the private
    ``ABSENT`` sentinel: when left untouched, the corresponding key is
    omitted entirely from the returned dict. Pass ``None`` explicitly to
    include the key with value ``None``.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {"name": name}
    if asset_feed_spec is not ABSENT:
        data["asset_feed_spec"] = asset_feed_spec
    if object_story_spec is not ABSENT:
        data["object_story_spec"] = object_story_spec
    data.update(overrides)
    return data


def make_ad(ad_creative=ABSENT, name="Ad", **overrides):
    """Build a fresh ``ad`` dict.

    ``ad_creative`` defaults to the ``ABSENT`` sentinel: when left untouched,
    the ``adCreative`` key is omitted entirely, matching the ``ad.get('adCreative')``
    falsy-value scenario. Pass ``None`` explicitly to include the key with
    value ``None``.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {"name": name}
    if ad_creative is not ABSENT:
        data["adCreative"] = ad_creative
    data.update(overrides)
    return data


def make_ad_set(ads=None, daily_budget=100, name="AdSet", **overrides):
    """Build a fresh ``ad_set`` dict.

    ``ads`` defaults to a brand new empty list when ``None`` is passed (or
    omitted), never a shared mutable default.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {
        "name": name,
        "daily_budget": daily_budget,
        "ads": ads if ads is not None else [],
    }
    data.update(overrides)
    return data


def make_meta_payload(ad_sets=None, campaign_name="Campaign", **overrides):
    """Build a fresh Meta payload of the form ``{"campaign": {...}}``.

    ``ad_sets`` defaults to a brand new empty list when ``None`` is passed
    (or omitted). Additional ``**overrides`` are merged into the inner
    ``campaign`` dict, allowing callers to omit the ``ad_sets`` key entirely
    by passing ``ad_sets=ABSENT`` from the caller side is not supported here;
    callers who need to characterize the missing-``ad_sets``-key scenario
    should build the ``campaign`` dict directly instead.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    campaign = {
        "name": campaign_name,
        "ad_sets": ad_sets if ad_sets is not None else [],
    }
    campaign.update(overrides)
    return {"campaign": campaign}


def make_ad_account_info(currency="USD", **overrides):
    """Build a fresh ad account info dict as returned by
    ``FacebookGetAdAccountDetailsUseCase.execute``.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    data = {"currency": currency}
    data.update(overrides)
    return data


def make_minimum_budget_response(currency="USD", min_daily_budget_imp=1000, **overrides):
    """Build a fresh minimum budget response of the form ``{"data": [...]}``
    as returned by ``FacebookMinimumBudgetUseCase.execute``.

    ``**overrides`` are merged into the single ``data`` entry.

    Requirements: 1.1, 14.1, 14.2, 14.3
    """
    entry = {
        "currency": currency,
        "min_daily_budget_imp": min_daily_budget_imp,
    }
    entry.update(overrides)
    return {"data": [entry]}


STANDARD_SUPPORTED_COMBINATIONS = sorted(
    FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS
)
"""The 5 ``(objective, optimization_goal)`` tuples supported by the
STANDARD branch, imported directly from
``FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS``
(rather than hand-copied) so this suite can never silently drift out of
sync with the production constant. Sorted for a deterministic
parametrization order across runs.

Requirements: 15.1, 15.2
"""

STANDARD_SUPPORTED_COMBINATIONS_IDS = [
    f"{objective}-{optimization_goal}".lower().replace("outcome_", "").replace(
        "_", "-"
    )
    for objective, optimization_goal in STANDARD_SUPPORTED_COMBINATIONS
]
"""Human-readable ``ids`` for ``STANDARD_SUPPORTED_COMBINATIONS``, e.g.
``"awareness-reach"``/``"leads-lead-generation"``/``"leads-conversations"``/
``"sales-offsite-conversions"``, derived mechanically from the tuple values
(never hand-typed) so they cannot drift out of sync with the combinations
themselves. Used as the ``ids=`` argument of
``@pytest.mark.parametrize("objective, optimization_goal", ...)`` in the
success-scenario tests, following the same
``ids=[...]``/``ids=["...", ...]`` convention already used throughout this
file (see ``test_min_daily_budget_and_daily_budget_valid_assigned_when_daily_budget_comparable``
above).

Requirements: 15.1, 15.2
"""


def make_standard_link_data_full(**overrides):
    """Build a fresh, fully-valid STANDARD ``link_data`` dict: a valid
    title (``name``), body (``message``), description, image URL, landing
    URL (``link``) and a ``call_to_action`` built with ``make_standard_cta``
    in the canonical nested shape
    ``{'type': {'value': 'LEARN_MORE', 'valid': True}}`` -- ``"LEARN_MORE"``
    is a CTA value present in every one of the 5
    ``STANDARD_SUPPORTED_COMBINATIONS`` allow-lists
    (``AWARENESS_GOAL_ALLOWED_CTAS[REACH]``,
    ``LEADS_GOAL_ALLOWED_CTAS[LEAD_GENERATION]``,
    ``LEADS_GOAL_ALLOWED_CTAS[OFFSITE_CONVERSIONS]``,
    ``SALES_GOAL_ALLOWED_CTAS[OFFSITE_CONVERSIONS]``), except
    ``LEADS_GOAL_ALLOWED_CTAS[CONVERSATIONS]`` which only allows
    ``"WHATSAPP_MESSAGE"``; callers exercising that specific combination
    should pass
    ``call_to_action=make_standard_cta("WHATSAPP_MESSAGE", valid=True)``
    as an override.

    The inner ``valid=True`` mirrors the shape the real CTAs pre-check
    (``_validate_ctas_standard``) leaves in the production flow, but it is
    not relied upon: ``_validate_standard_cta`` overwrites
    ``type['valid']`` with the real result of ``validate_cta_for_goal`` and
    writes the same boolean at the ROOT of the CTA (``cta['valid']``)
    (Requirement 15 of meta-ads-leads-offsite-conversions).
    ``_build_standard_creative_entry`` reads
    ``call_to_action['type']['valid']`` for
    ``call_to_action_types_valid_amount``, so that value now comes from
    ``_validate_standard_cta``, not from the input.

    Delegates to ``make_link_data`` (reused unmodified, per design.md) so
    every invocation returns a brand new dict built from
    ``**overrides``-friendly building blocks; no shared mutable defaults.

    Requirements: 15.2
    """
    data = make_link_data(
        name="Título válido",
        message="Cuerpo válido",
        description="Descripción válida",
        image_url="https://example.com/imagen.jpg",
        link="https://example.com/destino",
        call_to_action=make_standard_cta("LEARN_MORE", valid=True),
    )
    data.update(overrides)
    return data


def make_standard_cta(value, valid=ABSENT):
    """Build a ``call_to_action`` in the canonical nested shape
    ``{'type': {'value': <value>, 'valid': <valid>}}``.

    That shape is the one written by
    ``FacebookSavePreCheckCTAsUseCase._validate_ctas_standard``
    (``link_data['call_to_action'] = {'type': {'value': cta_value, 'valid': valid_cta}}``,
    ``app/v2/use_cases/meta_ads.py`` line 2766) and the one read back by:

    - ``_validate_standard_cta`` via ``cta.get('type', {}).get('value')``
      (``meta_ads.py`` line 1360), which is where the CTA text comes from; and
    - ``_build_standard_creative_entry`` via
      ``call_to_action.get('type', {}).get('valid', False)`` (``meta_ads.py``
      line 1478), which is where ``call_to_action_types_valid_amount`` comes
      from.

    ``valid`` defaults to the private ``ABSENT`` sentinel, in which case the
    ``valid`` key is omitted entirely from the inner ``type`` dict. That makes
    the helper usable both for pre-validation entries (not yet annotated, as
    ``_validate_standard_cta`` receives them) and for already-annotated entries
    (as the CTAs pre-check leaves them in the real flow). Pass ``valid=None``
    explicitly to include the key with value ``None``.

    Note that ``_validate_standard_cta`` writes the same boolean both inside
    ``type`` (``cta['type']['valid']``, overwriting any input ``valid``) and
    at the ROOT of the CTA (``cta['valid']``) (Requirement 15 of
    meta-ads-leads-offsite-conversions); after it runs, the two annotations
    are always equal, whatever ``valid`` this helper pre-loaded.

    This is a brand new helper: no shared builder is modified by it. In
    particular ``make_link_data`` keeps its ``call_to_action=None`` default, so
    the nodes characterizing an absent/falsy CTA and a truthy non-``dict`` CTA
    keep their semantics (design.md, risk R2).

    Requirements: 9.1, 15.2
    """
    cta_type = {"value": value}
    if valid is not ABSENT:
        cta_type["valid"] = valid
    return {"type": cta_type}


@st.composite
def _unsupported_objective_optimization_pair(draw):
    """Hypothesis composite building block for
    ``unsupported_objective_optimization_pairs``: draws one of several
    disjoint shapes of ``(objective, optimization_goal)`` pair and filters
    out anything that happens to collide with a supported combination.

    Requirements: 15.6
    """
    shape = draw(
        st.sampled_from(
            [
                "both_none",
                "objective_none",
                "optimization_goal_none",
                "known_enum_values",
                "arbitrary_strings",
            ]
        )
    )

    if shape == "both_none":
        return (None, None)
    if shape == "objective_none":
        return (
            None,
            draw(
                st.sampled_from(
                    [g.value for g in AwarenessOptimizationGoal]
                    + [g.value for g in LeadsOptimizationGoal]
                    + [g.value for g in SalesOptimizationGoal]
                    + [""]
                )
            ),
        )
    if shape == "optimization_goal_none":
        return (
            draw(st.sampled_from([o.value for o in CampaignObjective] + [""])),
            None,
        )
    if shape == "known_enum_values":
        # Any (objective, optimization_goal) pair built from the real Enums
        # used by the production code, filtered below to exclude the 5
        # actually-supported combinations (e.g. valid Enum values paired
        # across mismatched objectives/goals, such as SALES + REACH).
        objective = draw(st.sampled_from([o.value for o in CampaignObjective]))
        optimization_goal = draw(
            st.sampled_from(
                [g.value for g in AwarenessOptimizationGoal]
                + [g.value for g in LeadsOptimizationGoal]
                + [g.value for g in SalesOptimizationGoal]
            )
        )
        return (objective, optimization_goal)

    # arbitrary_strings: values not recognized by any Enum of the domain.
    return (
        draw(st.text(min_size=1, max_size=30)),
        draw(st.text(min_size=1, max_size=30)),
    )


def unsupported_objective_optimization_pairs():
    """Hypothesis strategy generating ``(objective, optimization_goal)``
    pairs guaranteed to NOT belong to ``STANDARD_SUPPORTED_COMBINATIONS``,
    for Property 1 (unsupported-combination guard, ``design.md``).

    Covers, per Requirement 2.2/15.6: both ``None``; one of the two
    ``None`` with the other a recognized Enum value or an empty string;
    combinations built entirely from the real domain Enums but not among
    the 5 supported ones (e.g. mismatched objective/goal pairs); and
    entirely arbitrary strings unrecognized by any Enum.

    Every generated pair is filtered so it can never accidentally collide
    with one of the 5 real supported combinations.

    Requirements: 2.2, 13.1, 13.2, 13.4, 15.6
    """
    return _unsupported_objective_optimization_pair().filter(
        lambda pair: pair not in STANDARD_SUPPORTED_COMBINATIONS
    )


def standard_candidate_values_with_wrong_count():
    """Hypothesis strategy generating raw values whose
    ``_standard_candidate_values`` result (per the real implementation in
    ``meta_ads.py``:
    ``return value if isinstance(value, list) else ([value] if value else [])``)
    has a length different from 1 -- either 0 (falsy scalars: ``None``,
    ``""``, ``[]``, ``False``, ``0``) or >= 2 (lists of 2+ arbitrary
    elements) -- for Property 2 (candidate count != 1, ``design.md``).

    The two branches are generated separately (rather than derived
    independently of ``_standard_candidate_values``) precisely so this
    strategy stays anchored to the real function's behaviour:

    - Zero-candidate branch: any of ``None``, ``""``, ``[]``, ``False``,
      ``0`` is falsy and not a list, so ``_standard_candidate_values``
      returns ``[]`` (length 0) for every one of them.
    - Two-or-more-candidates branch: any list built with 2 or more
      elements is returned as-is by ``_standard_candidate_values``
      (``isinstance(value, list)`` short-circuits before the truthiness
      check), so its length always matches the list's own length, which is
      >= 2 by construction here.

    Requirements: 3.2, 3.3, 4.2, 4.3, 5.2, 5.3, 6.2, 6.3
    """
    zero_candidates = st.sampled_from([None, "", [], False, 0])
    two_or_more_candidates = st.lists(
        st.one_of(st.text(), st.integers(), st.booleans(), st.none()),
        min_size=2,
        max_size=6,
    )
    return st.one_of(zero_candidates, two_or_more_candidates)


def arbitrary_text():
    """General-purpose Hypothesis text strategy for Property 3 (length
    equivalence with ``MetaAdsValidator.is_valid_length``, ``design.md``).

    Includes the empty string (candidate length 0 after being wrapped as a
    single-item list -- still exercises ``is_valid_length`` itself, whose
    own ``len(text) == 0`` branch is part of what Property 3 asserts) and
    strings well beyond the largest field limit (1024 for ``bodies``, 255
    for ``titles``/``descriptions``), so both the "exceeds max length" and
    the "within range" branches of ``is_valid_length`` are reachable by
    generated examples.

    Requirements: 3.1, 3.4, 3.5, 4.1, 4.4, 4.5, 5.1, 5.4, 5.5
    """
    return st.text(max_size=1100)


_STANDARD_LINK_DATA_FIELD_STRATEGIES = {
    "name": st.one_of(st.none(), st.text(max_size=50)),
    "message": st.one_of(st.none(), st.text(max_size=50)),
    "description": st.one_of(st.none(), st.text(max_size=50)),
    "image_url": st.one_of(st.none(), st.text(max_size=50)),
    "link": st.one_of(st.none(), st.text(max_size=50)),
    "call_to_action": st.one_of(
        st.none(),
        st.fixed_dictionaries(
            {
                "type": st.fixed_dictionaries(
                    {"value": st.text(max_size=20), "valid": st.booleans()}
                )
            }
        ),
    ),
    "title_valid": st.booleans(),
    "body_valid": st.booleans(),
    "description_valid": st.booleans(),
    "image_valid": st.booleans(),
    "image_error": st.one_of(st.none(), st.text(max_size=30)),
    "link_url_valid": st.booleans(),
}
"""Per-key value strategies for every ``link_data`` field the design's
mapping table reads from (``name``/``message``/``description``/
``image_url``/``link``/``call_to_action``) together with every annotation
key Requirement 10 writes onto ``link_data`` (``title_valid``/``body_valid``/
``description_valid``/``image_valid``/``image_error``/``link_url_valid``),
each generating a value of the type that field is actually expected to
hold, used to build valid-shaped partial/total ``link_data`` dicts for
Property 8 (``design.md``).

``call_to_action`` generates the canonical **nested** shape
``{'type': {'value': <text>, 'valid': <bool>}}`` -- the one
``FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`` writes and the
one ``_validate_standard_cta`` (``cta['type']['value']``) and
``_build_standard_creative_entry`` (``cta['type']['valid']``) read. A flat
``{'type': <text>}`` would make those readers raise ``AttributeError``, so
it is deliberately not generated (see ``make_standard_cta``).

Requirements: 12.2, 12.3, 12.4
"""

_STANDARD_OBJECT_STORY_SPEC_TOP_LEVEL_FIELD_STRATEGIES = {
    "ad_channel_id": st.one_of(st.none(), st.integers(min_value=0, max_value=10_000)),
    "daily_budget_valid": st.booleans(),
    "min_daily_budget": st.integers(min_value=0, max_value=10_000),
    "locations": st.lists(st.text(max_size=10), max_size=3),
    "locations_valid": st.booleans(),
}
"""Per-key value strategies for every ``object_story_spec`` (top-level, not
nested under ``link_data``) field the design's mapping table reads from,
used together with ``_STANDARD_LINK_DATA_FIELD_STRATEGIES`` for Property 8.

Requirements: 12.2, 12.3, 12.4
"""


@st.composite
def _standard_partial_dict(draw, field_strategies):
    """Hypothesis composite building block: draws a random subset of the
    keys of ``field_strategies`` (from the empty subset up to every key),
    and for each drawn key, draws a value from its own per-key strategy.

    Used to build "some keys present, some absent" ``link_data``/
    ``object_story_spec`` shapes for Property 8, rather than a single
    monolithic ``st.fixed_dictionaries`` (which would require every key to
    be present, defeating the purpose of exercising the "absent" branch of
    ``.get(key, default)`` for an arbitrary subset of keys).

    Requirements: 12.2, 12.3, 12.4
    """
    keys = draw(
        st.lists(
            st.sampled_from(sorted(field_strategies)),
            unique=True,
            max_size=len(field_strategies),
        )
    )
    return {key: draw(field_strategies[key]) for key in keys}


@st.composite
def standard_object_story_spec_shapes(draw):
    """Hypothesis strategy generating the value to pass as the
    ``object_story_spec`` kwarg of ``make_ad_creative`` (via
    ``**overrides``, e.g. ``make_ad_creative(object_story_spec=<drawn>)``),
    ranging over every shape Property 8 (``design.md``) requires:

    - ``object_story_spec`` entirely absent from ``adCreative`` (the
      private ``ABSENT`` sentinel, so ``make_ad_creative`` omits the key).
    - ``object_story_spec`` present with the value ``None``.
    - ``object_story_spec`` present as a dict with ``link_data`` absent.
    - ``object_story_spec`` present as a dict with ``link_data=None``.
    - ``object_story_spec`` present as a dict with ``link_data={}``
      (present but empty).
    - ``object_story_spec`` present as a dict with ``link_data`` partially
      populated (a random subset of its known fields, each with a
      valid-shaped value).
    - ``object_story_spec`` present as a dict with ``link_data`` fully
      populated (every known field present).

    In every "present as a dict" shape, the top-level ``object_story_spec``
    fields (``ad_channel_id``/``daily_budget_valid``/``min_daily_budget``/
    ``locations``/``locations_valid``) are also drawn as a random partial
    subset, independently of the ``link_data`` shape chosen.

    Requirements: 12.2, 12.3, 12.4, 15.7
    """
    shape = draw(
        st.sampled_from(
            [
                "absent_key",
                "none_value",
                "link_data_absent",
                "link_data_none",
                "link_data_empty",
                "link_data_partial",
                "link_data_full",
            ]
        )
    )

    if shape == "absent_key":
        return ABSENT
    if shape == "none_value":
        return None

    top_level = draw(
        _standard_partial_dict(_STANDARD_OBJECT_STORY_SPEC_TOP_LEVEL_FIELD_STRATEGIES)
    )

    if shape == "link_data_absent":
        return top_level
    if shape == "link_data_none":
        return {**top_level, "link_data": None}
    if shape == "link_data_empty":
        return {**top_level, "link_data": {}}
    if shape == "link_data_partial":
        return {
            **top_level,
            "link_data": draw(
                _standard_partial_dict(_STANDARD_LINK_DATA_FIELD_STRATEGIES)
            ),
        }

    # link_data_full: every known link_data field present.
    return {
        **top_level,
        "link_data": {
            key: draw(strategy)
            for key, strategy in _STANDARD_LINK_DATA_FIELD_STRATEGIES.items()
        },
    }


@pytest.fixture
def use_case_factory():
    """Fixture that builds a factory for ``FacebookGeneratePreCheckCreativeUseCase``
    instances with ``AdChannelRepository``/``CampaignChannelPublishRepository``
    substituted by test doubles.

    Each call to the returned factory patches
    ``app.v2.use_cases.meta_ads.AdChannelRepository`` and
    ``app.v2.use_cases.meta_ads.CampaignChannelPublishRepository`` before
    constructing the use case, then returns::

        (use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance)

    Calling the factory multiple times (within the same test or across
    tests) always produces a brand new use case instance and brand new
    mock repository instances; nothing is shared between invocations.

    If ``complete_campaign_data`` is omitted, a fresh
    ``make_campaign_data_dict()`` is used so the ``AttributeError``
    characterized in Requirement 2.5 is not accidentally triggered here;
    the dedicated test for that criterion constructs the use case directly,
    without this fixture.

    Requirements: 1.2, 14.3
    """

    def _factory(
        campaign_id="campaign-1",
        user_id="user-1",
        complete_campaign_data=None,
        creative_type="DYNAMIC",
    ):
        if complete_campaign_data is None:
            complete_campaign_data = make_campaign_data_dict()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookGeneratePreCheckCreativeUseCase(
                campaign_id=campaign_id,
                user_id=user_id,
                complete_campaign_data=complete_campaign_data,
                creative_type=creative_type,
            )
            mock_ad_channel_repo_instance = mock_ad_channel_repository_cls.return_value
            mock_campaign_publish_repo_instance = mock_campaign_publish_repository_cls.return_value

        return use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance

    return _factory


@contextmanager
def patch_execute_dependencies():
    """Context manager that jointly patches every collaborator ``execute()``
    reaches through module-level symbols in ``app.v2.use_cases.meta_ads``:
    ``redis_client``, ``MetaAdsPayloadBuilder``,
    ``FacebookGetAdAccountDetailsUseCase`` and ``FacebookMinimumBudgetUseCase``.

    Yields a ``SimpleNamespace`` exposing each ``MagicMock`` under its
    original name, so a scenario can configure ``return_value``/``side_effect``
    directly, for example::

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = payload
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (info, 200)
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (budget, 200)

    Requirements: 1.3, 1.4, 14.3
    """
    with patch("app.v2.use_cases.meta_ads.redis_client") as mock_redis_client, patch(
        "app.v2.use_cases.meta_ads.MetaAdsPayloadBuilder"
    ) as mock_meta_ads_payload_builder, patch(
        "app.v2.use_cases.meta_ads.FacebookGetAdAccountDetailsUseCase"
    ) as mock_get_ad_account_details_use_case, patch(
        "app.v2.use_cases.meta_ads.FacebookMinimumBudgetUseCase"
    ) as mock_minimum_budget_use_case:
        yield SimpleNamespace(
            redis_client=mock_redis_client,
            MetaAdsPayloadBuilder=mock_meta_ads_payload_builder,
            FacebookGetAdAccountDetailsUseCase=mock_get_ad_account_details_use_case,
            FacebookMinimumBudgetUseCase=mock_minimum_budget_use_case,
        )


@pytest.fixture(autouse=True)
def _deny_real_network_requests(monkeypatch):
    """Local, module-scoped guard (not a global ``conftest.py`` fixture)
    that replaces ``requests.sessions.Session.request`` with a function
    that fails immediately, so any accidental real network leak (for
    example from an unpatched ``MetaAdsValidator.validate_images_precheck``/
    ``validate_images`` call) is reported as a clear test failure instead
    of attempting a real HTTP request.

    Requirements: 1.5, 1.6, 14.3
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request", _raise_on_network_access
    )


def test_smoke_use_case_construction_and_exception_capture_need_no_flask_context(
    use_case_factory,
):
    """Smoke test for Requirement 1.7: building the use case with
    ``use_case_factory`` and capturing ``NotAccessException``/
    ``PermissionDeniedException`` (both raised in production code with an
    explicit ``text`` argument) works as a pure unit test, with no Flask
    application/request context and no ``tests/conftest.py``.

    If this assumption turned out to be false, the implementation of this
    task would have to stop and report the problem instead of adding Flask
    app/context infrastructure or a ``tests/conftest.py`` file; running this
    test green is exactly what confirms that stop condition was never
    reached.

    Requirements: 1.7, 14.3
    """
    use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
        use_case_factory()
    )

    assert mock_ad_channel_repo_instance is use_case.ad_channel_repository
    assert mock_campaign_publish_repo_instance is use_case.campaign_publish_repository

    with patch_execute_dependencies() as deps:
        deps.redis_client.get.return_value = None

        with pytest.raises(NotAccessException) as exc_info:
            use_case._get_decoded_access_token()
        assert (
            exc_info.value.text
            == "No access token found in Redis. Please re-authenticate."
        )

        deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
            {"error": {"code": 200}},
            400,
        )
        with pytest.raises(PermissionDeniedException) as exc_info:
            use_case._get_account_details()
        assert exc_info.value.text == (
            "Insufficient permissions to access ad account details. "
            "Please check your Facebook app permissions."
        )


class TestConstructorAndInheritedState:
    """Requirement 2: construction of the use case and the state inherited
    from ``FacebookTestCreativeUploadUseCase.__init__``.

    Requirements: 2.1, 2.2, 2.3, 2.4
    """

    def test_constructor_assigns_attributes_from_complete_campaign_data(
        self, use_case_factory
    ):
        """When constructed with complete campaign data, every simple
        attribute derived from ``complete_campaign_data``/``creative_type``
        is assigned exactly to the provided value.

        Requirements: 2.1
        """
        campaign_data = make_campaign_data_dict(
            ad_account_id="act-123",
            page_id="page-456",
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            lead_gen_form_id="lead-form-1",
            whatsapp_number_id="whatsapp-1",
        )

        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )

        assert use_case.ad_account_id == "act-123"
        assert use_case.page_id == "page-456"
        assert use_case.objective == "OUTCOME_LEADS"
        assert use_case.optimization_goal == "LEAD_GENERATION"
        assert use_case.lead_gen_form_id == "lead-form-1"
        assert use_case.whatsapp_number_id == "whatsapp-1"
        assert use_case.creative_type == "DYNAMIC"

    def test_constructor_initializes_billing_event_and_channel_id_to_none(
        self, use_case_factory
    ):
        """The constructor always initializes ``billing_event`` and
        ``channel_id`` to ``None``, regardless of the supplied campaign data.

        Requirements: 2.2
        """
        use_case, _, _ = use_case_factory(
            complete_campaign_data=make_campaign_data_dict(
                lead_gen_form_id="lead-form-1", whatsapp_number_id="whatsapp-1"
            )
        )

        assert use_case.billing_event is None
        assert use_case.channel_id is None

    def test_constructor_instantiates_each_patched_repository_exactly_once(self):
        """Both ``AdChannelRepository`` and ``CampaignChannelPublishRepository``,
        patched on ``app.v2.use_cases.meta_ads``, are instantiated exactly
        once each when the use case is constructed, with no arguments.

        Requirements: 2.3
        """
        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            FacebookGeneratePreCheckCreativeUseCase(
                campaign_id="campaign-1",
                user_id="user-1",
                complete_campaign_data=make_campaign_data_dict(),
                creative_type="DYNAMIC",
            )

            mock_ad_channel_repository_cls.assert_called_once_with()
            mock_campaign_publish_repository_cls.assert_called_once_with()

    @pytest.mark.parametrize(
        "omitted_field", ["lead_gen_form_id", "whatsapp_number_id"]
    )
    def test_constructor_defaults_omitted_lead_form_or_whatsapp_id_to_none(
        self, use_case_factory, omitted_field
    ):
        """When ``complete_campaign_data`` omits ``lead_gen_form_id`` or
        ``whatsapp_number_id`` entirely (key not present, as opposed to
        present with value ``None``), the corresponding use case attribute
        is ``None``.

        Requirements: 2.4
        """
        campaign_data = make_campaign_data_dict()
        del campaign_data[omitted_field]
        assert omitted_field not in campaign_data

        use_case, _, _ = use_case_factory(complete_campaign_data=campaign_data)

        assert getattr(use_case, omitted_field) is None

    def test_constructor_propagates_attribute_error_when_complete_campaign_data_is_none(
        self,
    ):
        """When constructed with ``complete_campaign_data=None`` (the
        constructor default), the ``AttributeError`` raised by
        ``None.get(...)`` while assigning ``ad_account_id`` propagates
        unmodified, characterizing the current behaviour in which only
        ``lead_gen_form_id`` and ``whatsapp_number_id`` are guarded against a
        missing ``complete_campaign_data``.

        Constructed directly (not through ``use_case_factory``), patching
        ``AdChannelRepository``/``CampaignChannelPublishRepository`` inline,
        per Requirement 2.5.

        Requirements: 2.5
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            with pytest.raises(AttributeError):
                FacebookGeneratePreCheckCreativeUseCase(
                    campaign_id="campaign-1",
                    user_id="user-1",
                    complete_campaign_data=None,
                    creative_type="DYNAMIC",
                )


class TestGetDecodedAccessToken:
    """Requirement 3: obtaining the decoded Facebook access token from Redis,
    inherited from ``FacebookTestCreativeUploadUseCase._get_decoded_access_token``.

    Requirements: 3.1, 3.2, 3.3
    """

    def test_returns_decoded_token_and_calls_redis_get_with_exact_key(
        self, use_case_factory
    ):
        """When the Redis client returns a truthy value for the
        ``facebook_access_token:{user_id}`` key, ``_get_decoded_access_token``
        returns that value decoded with ``utf-8``, and ``redis_client.get``
        was called exactly once with that exact key.

        Requirements: 3.1
        """
        use_case, _, _ = use_case_factory(user_id="user-42")

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = "token-value".encode("utf-8")

            result = use_case._get_decoded_access_token()

        assert result == "token-value"
        deps.redis_client.get.assert_called_once_with(
            "facebook_access_token:user-42"
        )

    @pytest.mark.parametrize(
        "falsy_token",
        [None, b"", ""],
        ids=["none", "empty-bytes", "empty-string"],
    )
    def test_raises_not_access_exception_when_token_is_falsy(
        self, use_case_factory, falsy_token
    ):
        """When the Redis client returns a falsy value, ``_get_decoded_access_token``
        propagates ``NotAccessException`` with the exact expected message,
        without ever reaching the ``.decode("utf-8")`` call.

        Requirements: 3.2
        """
        use_case, _, _ = use_case_factory()

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = falsy_token

            with pytest.raises(NotAccessException) as exc_info:
                use_case._get_decoded_access_token()

        assert (
            exc_info.value.text
            == "No access token found in Redis. Please re-authenticate."
        )

    def test_execute_propagates_missing_token_exception_without_invoking_downstream_collaborators(
        self, use_case_factory
    ):
        """When ``execute()`` obtains a missing token in its very first step
        (the call to ``_get_decoded_access_token()``), the ``NotAccessException``
        propagates out of ``execute()`` without ``MetaAdsPayloadBuilder``,
        ``FacebookGetAdAccountDetailsUseCase`` nor ``FacebookMinimumBudgetUseCase``
        ever being instantiated/invoked.

        Requirements: 3.3
        """
        use_case, _, _ = use_case_factory()

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = None

            with pytest.raises(NotAccessException) as exc_info:
                use_case.execute()

        assert (
            exc_info.value.text
            == "No access token found in Redis. Please re-authenticate."
        )
        deps.MetaAdsPayloadBuilder.assert_not_called()
        deps.FacebookGetAdAccountDetailsUseCase.assert_not_called()
        deps.FacebookMinimumBudgetUseCase.assert_not_called()


class TestBuildMetaPayload:
    """Requirement 4: construction of the Meta payload via ``_build_meta_payload``,
    inherited from ``FacebookTestCreativeUploadUseCase._build_meta_payload``::

        def _build_meta_payload(self):
            builder = MetaAdsPayloadBuilder(self.campaign_id, self.objective, self.optimization_goal, self.creative_type)

            if self.ad_account_id: builder.select_ad_account(self.ad_account_id)
            if self.page_id: builder.select_page(self.page_id)
            self.billing_event = builder.get_billing_event()

            try:
                payload = builder.build_meta_payload()
                self.channel_id = builder.get_channel_id()
                return payload
            except Exception as e:
                logger.error(f"Error fetching/building Strapi payload: {e}")
                raise StrapiException(f"Failed to build payload from Strapi: {str(e)}")

    Requirements: 4.1, 4.2, 4.3, 4.4
    """

    def test_instantiates_builder_and_calls_select_ad_account_and_select_page_when_both_truthy(
        self, use_case_factory
    ):
        """When both ``ad_account_id`` and ``page_id`` are truthy,
        ``MetaAdsPayloadBuilder`` is instantiated with
        ``(campaign_id, objective, optimization_goal, creative_type)`` and
        both ``select_ad_account(ad_account_id)``/``select_page(page_id)``
        are called exactly once each, before ``build_meta_payload()``.

        Requirements: 4.1
        """
        campaign_data = make_campaign_data_dict(
            ad_account_id="act-777", page_id="page-888"
        )
        use_case, _, _ = use_case_factory(
            campaign_id="campaign-99",
            complete_campaign_data=campaign_data,
            creative_type="DYNAMIC",
        )

        with patch_execute_dependencies() as deps:
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            payload = {"campaign": {"name": "Campaign"}}
            builder_mock.build_meta_payload.return_value = payload

            use_case._build_meta_payload()

        deps.MetaAdsPayloadBuilder.assert_called_once_with(
            "campaign-99", "OUTCOME_AWARENESS", "REACH", "DYNAMIC"
        )
        builder_mock.select_ad_account.assert_called_once_with("act-777")
        builder_mock.select_page.assert_called_once_with("page-888")
        # select_ad_account/select_page must be called before build_meta_payload
        assert builder_mock.method_calls.index(
            next(c for c in builder_mock.method_calls if c[0] == "select_ad_account")
        ) < builder_mock.method_calls.index(
            next(c for c in builder_mock.method_calls if c[0] == "build_meta_payload")
        )
        assert builder_mock.method_calls.index(
            next(c for c in builder_mock.method_calls if c[0] == "select_page")
        ) < builder_mock.method_calls.index(
            next(c for c in builder_mock.method_calls if c[0] == "build_meta_payload")
        )

    @pytest.mark.parametrize(
        "ad_account_id, page_id, expect_select_ad_account, expect_select_page",
        [
            (None, "page-1", False, True),
            ("", "page-1", False, True),
            ("act-1", None, True, False),
            ("act-1", "", True, False),
            (None, None, False, False),
        ],
        ids=[
            "ad_account_id-none",
            "ad_account_id-empty-string",
            "page_id-none",
            "page_id-empty-string",
            "both-falsy",
        ],
    )
    def test_skips_select_ad_account_or_select_page_when_falsy(
        self,
        use_case_factory,
        ad_account_id,
        page_id,
        expect_select_ad_account,
        expect_select_page,
    ):
        """When ``ad_account_id`` and/or ``page_id`` are falsy,
        ``select_ad_account``/``select_page`` are not invoked for the
        corresponding falsy value.

        Requirements: 4.2
        """
        campaign_data = make_campaign_data_dict(
            ad_account_id=ad_account_id, page_id=page_id
        )
        use_case, _, _ = use_case_factory(complete_campaign_data=campaign_data)

        with patch_execute_dependencies() as deps:
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = {"campaign": {}}

            use_case._build_meta_payload()

        if expect_select_ad_account:
            builder_mock.select_ad_account.assert_called_once_with(ad_account_id)
        else:
            builder_mock.select_ad_account.assert_not_called()

        if expect_select_page:
            builder_mock.select_page.assert_called_once_with(page_id)
        else:
            builder_mock.select_page.assert_not_called()

    def test_assigns_billing_event_and_channel_id_and_returns_payload_by_identity(
        self, use_case_factory
    ):
        """When ``build_meta_payload()`` returns a payload,
        ``_build_meta_payload`` assigns ``self.billing_event`` from
        ``get_billing_event()``, assigns ``self.channel_id`` from
        ``get_channel_id()`` and returns the exact same payload object by
        identity.

        Requirements: 4.3
        """
        use_case, _, _ = use_case_factory()

        with patch_execute_dependencies() as deps:
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.get_billing_event.return_value = "IMPRESSIONS"
            builder_mock.get_channel_id.return_value = "channel-123"
            payload = {"campaign": {"name": "Campaign"}}
            builder_mock.build_meta_payload.return_value = payload

            result = use_case._build_meta_payload()

        assert result is payload
        assert use_case.billing_event == "IMPRESSIONS"
        assert use_case.channel_id == "channel-123"
        builder_mock.get_billing_event.assert_called_once_with()
        builder_mock.get_channel_id.assert_called_once_with()

    def test_wraps_build_meta_payload_exception_in_strapi_exception_with_original_text(
        self, use_case_factory
    ):
        """When ``build_meta_payload()`` raises an exception,
        ``_build_meta_payload`` propagates ``StrapiException`` (not the
        original exception) with a message that contains the original
        exception's text.

        Requirements: 4.4
        """
        use_case, _, _ = use_case_factory()

        with patch_execute_dependencies() as deps:
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.side_effect = ValueError(
                "strapi is unreachable"
            )

            with pytest.raises(StrapiException) as exc_info:
                use_case._build_meta_payload()

        assert "strapi is unreachable" in exc_info.value.text
        # channel_id must not have been assigned since build_meta_payload raised
        # before get_channel_id() could be reached.
        assert use_case.channel_id is None


class TestGetAccountDetails:
    """Requirement 5: obtaining ad account details via ``_get_account_details``,
    which mirrors::

        def _get_account_details(self):
            ad_account_info, status_details = FacebookGetAdAccountDetailsUseCase().execute(self.user_id, self.ad_account_id)
            if status_details != 200:
                if ad_account_info.get('error', {}).get('code') == 190:
                    raise NotAccessException(...)
                elif ad_account_info.get('error', {}).get('code') == 200:
                    raise PermissionDeniedException(...)
                elif ad_account_info.get('error', {}).get('code') == 100:
                    raise ParametersNotFoundException(...)
                elif ad_account_info.get('error', {}).get('code') == 613:
                    raise RateLimitExceededException(...)
                else:
                    raise RESTClientException(f"Failed to fetch ad account details: {ad_account_info.get('error', {}).get('message', 'Unknown error')}")
            return ad_account_info

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6
    """

    def test_returns_ad_account_info_by_identity_and_calls_execute_with_exact_args(
        self, use_case_factory
    ):
        """When the Ad Account use case double returns ``status_details=200``,
        ``_get_account_details`` returns the exact same dict by identity
        (not an equal copy), and ``execute`` was invoked exactly once with
        ``(self.user_id, self.ad_account_id)`` as positional arguments.

        Requirements: 5.1
        """
        campaign_data = make_campaign_data_dict(ad_account_id="act-account-details")
        use_case, _, _ = use_case_factory(
            user_id="user-account-details", complete_campaign_data=campaign_data
        )

        with patch_execute_dependencies() as deps:
            ad_account_info = make_ad_account_info()
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                ad_account_info,
                200,
            )

            result = use_case._get_account_details()

        assert result is ad_account_info
        deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.assert_called_once_with(
            "user-account-details", "act-account-details"
        )

    @pytest.mark.parametrize(
        "ad_account_info, expected_exception_type, expected_message",
        [
            (
                {"error": {"code": 190, "message": "token expired"}},
                NotAccessException,
                "Access token is invalid or expired. Please re-authenticate.",
            ),
            (
                {"error": {"code": 200, "message": "missing scope"}},
                PermissionDeniedException,
                "Insufficient permissions to access ad account details. "
                "Please check your Facebook app permissions.",
            ),
            (
                {"error": {"code": 100, "message": "bad param"}},
                ParametersNotFoundException,
                "Invalid parameters provided for fetching ad account details. "
                "Please check the ad account ID and try again.",
            ),
            (
                {"error": {"code": 613, "message": "too many calls"}},
                RateLimitExceededException,
                "Facebook API rate limit exceeded. Please try again later.",
            ),
            (
                {"error": {"code": 999, "message": "some unexpected failure"}},
                RESTClientException,
                "Failed to fetch ad account details: some unexpected failure",
            ),
            (
                {},
                RESTClientException,
                "Failed to fetch ad account details: Unknown error",
            ),
        ],
        ids=[
            "error-code-190-not-access",
            "error-code-200-permission-denied",
            "error-code-100-parameters-not-found",
            "error-code-613-rate-limit-exceeded",
            "error-code-unmapped-rest-client",
            "error-absent-rest-client-unknown-error-fallback",
        ],
    )
    def test_raises_mapped_exception_for_each_error_code_with_exact_message(
        self,
        use_case_factory,
        ad_account_info,
        expected_exception_type,
        expected_message,
    ):
        """For each combination of ``status_details != 200`` and
        ``error.code`` (``190``, ``200``, ``100``, ``613``, an unmapped
        code, and ``error`` entirely absent from the response), the
        corresponding exception type is propagated with the exact expected
        message, including the ``"Unknown error"`` fallback text used when
        ``error.message`` is missing.

        Requirements: 5.2, 5.3, 5.4, 5.5, 5.6
        """
        use_case, _, _ = use_case_factory()

        with patch_execute_dependencies() as deps:
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                ad_account_info,
                400,
            )

            with pytest.raises(expected_exception_type) as exc_info:
                use_case._get_account_details()

        assert exc_info.value.text == expected_message


class TestGetMinimumBudget:
    """Requirement 6: obtaining the minimum daily budget via
    ``_get_minimum_budget``, which mirrors::

        def _get_minimum_budget(self, ad_account_info):
            minimum_budgets_allowed, status_budgets = FacebookMinimumBudgetUseCase().execute(self.user_id, self.ad_account_id)
            if status_budgets != 200:
                raise PermissionDeniedException("Insufficient permissions to access minimum budget details. Please check your Facebook app permissions.")

            minimum = next((item for item in minimum_budgets_allowed.get('data', []) if item.get('currency') == ad_account_info.get('currency')), None)

            if minimum:
                return minimum.get('min_daily_budget_imp', 0) / 100  # This value is in cents
            else:
                raise DataNotFoundException("Minimum budget not found for account currency")

    Requirements: 6.1, 6.2, 6.3, 6.4
    """

    def test_raises_permission_denied_exception_when_status_budgets_is_not_200(
        self, use_case_factory
    ):
        """When the Minimum Budget use case double returns a status
        different from ``200``, ``_get_minimum_budget`` propagates
        ``PermissionDeniedException`` with the exact expected message,
        regardless of the ``data`` payload returned alongside it.

        Requirements: 6.1
        """
        use_case, _, _ = use_case_factory()
        ad_account_info = make_ad_account_info(currency="USD")

        with patch_execute_dependencies() as deps:
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(currency="USD"),
                400,
            )

            with pytest.raises(PermissionDeniedException) as exc_info:
                use_case._get_minimum_budget(ad_account_info)

        assert exc_info.value.text == (
            "Insufficient permissions to access minimum budget details. "
            "Please check your Facebook app permissions."
        )

    def test_returns_first_matching_currency_entry_converted_from_cents(
        self, use_case_factory
    ):
        """When the response contains several ``data`` entries and more than
        one matches the account currency, ``_get_minimum_budget`` returns
        ``min_daily_budget_imp / 100`` for the first matching entry in
        appearance order, ignoring any later matching entry.

        Requirements: 6.2
        """
        use_case, _, _ = use_case_factory()
        ad_account_info = make_ad_account_info(currency="EUR")

        minimum_budgets_allowed = {
            "data": [
                {"currency": "USD", "min_daily_budget_imp": 500},
                {"currency": "EUR", "min_daily_budget_imp": 1500},
                {"currency": "EUR", "min_daily_budget_imp": 9999},
            ]
        }

        with patch_execute_dependencies() as deps:
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                minimum_budgets_allowed,
                200,
            )

            result = use_case._get_minimum_budget(ad_account_info)

        assert result == 15.0
        deps.FacebookMinimumBudgetUseCase.return_value.execute.assert_called_once_with(
            use_case.user_id, use_case.ad_account_id
        )

    def test_returns_zero_when_matching_entry_omits_min_daily_budget_imp(
        self, use_case_factory
    ):
        """When the first matching-currency entry omits
        ``min_daily_budget_imp`` entirely, ``_get_minimum_budget`` returns
        ``0`` (the ``.get(..., 0)`` default) divided by ``100``, i.e. ``0.0``.

        Requirements: 6.4
        """
        use_case, _, _ = use_case_factory()
        ad_account_info = make_ad_account_info(currency="USD")

        minimum_budgets_allowed = {"data": [{"currency": "USD"}]}
        assert "min_daily_budget_imp" not in minimum_budgets_allowed["data"][0]

        with patch_execute_dependencies() as deps:
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                minimum_budgets_allowed,
                200,
            )

            result = use_case._get_minimum_budget(ad_account_info)

        assert result == 0.0

    def test_raises_data_not_found_exception_when_no_entry_matches_currency(
        self, use_case_factory
    ):
        """When the response has status ``200`` but no entry in ``data``
        has a ``currency`` matching ``ad_account_info.currency``,
        ``_get_minimum_budget`` propagates ``DataNotFoundException`` with
        the exact expected message.

        Requirements: 6.3
        """
        use_case, _, _ = use_case_factory()
        ad_account_info = make_ad_account_info(currency="GBP")

        minimum_budgets_allowed = make_minimum_budget_response(currency="USD")

        with patch_execute_dependencies() as deps:
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                minimum_budgets_allowed,
                200,
            )

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._get_minimum_budget(ad_account_info)

        assert exc_info.value.text == "Minimum budget not found for account currency"

    def test_raises_data_not_found_exception_when_data_list_is_empty(
        self, use_case_factory
    ):
        """When ``data`` is an empty list, ``_get_minimum_budget`` also
        propagates ``DataNotFoundException`` with the exact expected
        message, since ``next(..., None)`` over an empty iterable yields the
        default ``None``.

        Requirements: 6.3
        """
        use_case, _, _ = use_case_factory()
        ad_account_info = make_ad_account_info(currency="USD")

        with patch_execute_dependencies() as deps:
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                {"data": []},
                200,
            )

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._get_minimum_budget(ad_account_info)

        assert exc_info.value.text == "Minimum budget not found for account currency"


class TestExecuteMissingCreative:
    """Requirement 7: ads without ``adCreative`` (or with a falsy ``adCreative``)
    inside ``execute()``.

    ``results`` (the list of ``AdResultEntry`` built inside ``execute()``) is
    **not** part of the Final Response returned by ``execute()`` on
    ``FacebookGeneratePreCheckCreativeUseCase`` (unlike its parent class). So
    none of the tests below inspect any ``slug``/``message`` string; they only
    observe ``ok``, mock call assertions on ``MetaAdsValidator``, and the
    ``AttributeError`` exception type/timing.

    Requirements: 7.1, 7.2, 7.3
    """

    @pytest.mark.parametrize(
        "ad_creative_value, ad_creative_key_present",
        [(ABSENT, False), (None, True), ({}, True)],
        ids=["ad_creative-absent", "ad_creative-none", "ad_creative-empty-dict"],
    )
    def test_ad_without_creative_as_non_first_ad_yields_ok_1_without_invoking_validator(
        self, use_case_factory, ad_creative_value, ad_creative_key_present
    ):
        """For each falsy ``adCreative`` value (absent, ``None``, ``{}``),
        when that ad is placed *after* a valid filler ad in the same ad set
        (so it is not ``ads[0]`` and Requirement 7.3's ``AttributeError`` is
        not triggered), the Final Response contains ``ok=1`` -- the literal
        returned for every run, because the conditional that consumed
        ``has_errors`` is commented out -- and
        ``MetaAdsValidator`` is never invoked for/because of the
        creativeless ad. A ``creative_type`` outside ``DYNAMIC``/``STANDARD``
        is used for the filler ad so it reaches the creation block without
        requiring any ``MetaAdsValidator`` call at all, keeping this
        assertion unambiguous: any call recorded on the patched
        ``MetaAdsValidator`` must have come only from the module-level
        ``META_ODAX_CTA_MAPPING`` lookup at the end of ``execute()``, not
        from validating the creativeless ad.

        Requirements: 7.1, 7.2
        """
        campaign_data = make_campaign_data_dict()
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="UNRECOGNIZED_TYPE"
        )

        filler_ad = make_ad(ad_creative=make_ad_creative(name="FillerCreative"))
        if ad_creative_key_present:
            creativeless_ad = make_ad(ad_creative=ad_creative_value)
        else:
            creativeless_ad = make_ad()
        ad_set = make_ad_set(ads=[filler_ad, creativeless_ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator"
        ) as mock_meta_ads_validator:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1
        # The only calls reaching the patched MetaAdsValidator come from the
        # unconditional `validate_optimization_goal_for_objective` guard and
        # the `META_ODAX_CTA_MAPPING.get(...)`/`get_allowed_ctas_for_goal`
        # lookup used to build `valid_ctas` (both run once per `execute()`
        # call regardless of any ad's contents), not from validating the
        # creativeless ad's contents.
        allowed_call_prefixes = (
            "META_ODAX_CTA_MAPPING",
            "validate_optimization_goal_for_objective",
            "get_allowed_ctas_for_goal",
        )
        for call in mock_meta_ads_validator.mock_calls:
            call_name = call[0]
            assert call_name.startswith(
                allowed_call_prefixes
            ), f"Unexpected MetaAdsValidator call for the creativeless ad: {call}"

    @pytest.mark.parametrize(
        "ad_creative_value, ad_creative_key_present",
        [(ABSENT, False), (None, True), ({}, True)],
        ids=["ad_creative-absent", "ad_creative-none", "ad_creative-empty-dict"],
    )
    def test_iteration_continues_to_next_ad_after_missing_creative(
        self, use_case_factory, ad_creative_value, ad_creative_key_present
    ):
        """When a creativeless ad is placed between two valid DYNAMIC ads
        within the same ad set (not as ``ads[0]``, so Requirement 7.3's
        ``AttributeError`` is not triggered), the ad *after* the creativeless
        one is still reached and validated: its ``asset_feed_spec`` receives
        the same success mutations (``unique_titles``, etc.) as an ad
        processed on its own, and ``MetaAdsValidator.is_unique_texts`` is
        invoked for its texts too. This is only possible if the ``for ad in
        ads`` loop's ``continue`` (triggered by the creativeless ad) does not
        interrupt the ad set nor the campaign: ``asset_feed_after
        ["unique_titles"] is True`` and ``is_unique_texts.call_count == 6``
        are the evidence the trailing ad was actually reached and validated.
        The isolated execution kept below (only that same valid trailing ad,
        no creativeless ad at all) also yields ``ok=1``, but since
        ``execute()`` returns ``ok=1`` unconditionally that check no longer
        discriminates between the isolated and the combined run; it is kept
        as a deliberate redundancy, not as evidence this test rests on.

        Requirements: 7.2
        """
        campaign_data = make_campaign_data_dict()

        def _make_valid_dynamic_ad(name):
            asset_feed = make_asset_feed_spec(
                titles=[{"text": "Title"}],
                bodies=[{"text": "Body"}],
                descriptions=[{"text": "Description"}],
            )
            return make_ad(
                name=name,
                ad_creative=make_ad_creative(
                    name=f"{name}Creative", asset_feed_spec=asset_feed
                ),
            ), asset_feed

        # Isolation check: the trailing ad, on its own, yields ok=1. Kept as
        # a deliberate redundancy (see the docstring): it no longer contrasts
        # with the combined run, which yields ok=1 as well.
        use_case_isolated, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )
        isolated_ad, _ = _make_valid_dynamic_ad("AdAfter")
        isolated_payload = make_meta_payload(
            ad_sets=[make_ad_set(ads=[isolated_ad])]
        )
        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ):
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                isolated_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            isolated_result, _ = use_case_isolated.execute()

        assert isolated_result["ok"] == 1

        # Combined check: ad_before (ads[0]) -> creativeless ad -> ad_after,
        # all within the same ad set.
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )
        ad_before, asset_feed_before = _make_valid_dynamic_ad("AdBefore")
        ad_after, asset_feed_after = _make_valid_dynamic_ad("AdAfter")
        if ad_creative_key_present:
            creativeless_ad = make_ad(name="NoCreativeAd", ad_creative=ad_creative_value)
        else:
            creativeless_ad = make_ad(name="NoCreativeAd")
        ad_set = make_ad_set(ads=[ad_before, creativeless_ad, ad_after])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            return_value=True,
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ):
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, _ = use_case.execute()

        # ad_after (processed after the creativeless ad was skipped via
        # `continue`) received the same success mutations as ad_before,
        # proving the loop reached it.
        assert asset_feed_before["unique_titles"] is True
        assert asset_feed_after["unique_titles"] is True
        # is_unique_texts is called 3 times per valid ad (titles/bodies/
        # descriptions); 6 total calls confirms both ad_before and ad_after
        # were validated, with none skipped due to the creativeless ad in
        # between.
        assert mock_is_unique_texts.call_count == 6
        # The Final Response's ok is the literal 1 no matter what the
        # creativeless ad left in the internal results list, so this only
        # documents the aggregate outcome; the proof that `continue` did not
        # interrupt the loop is the pair of assertions above.
        assert result["ok"] == 1

    def test_missing_creative_as_ads_zero_absent_or_none_propagates_attribute_error_after_save_or_update(
        self, use_case_factory
    ):
        """When the creativeless ad (``adCreative`` absent or ``None``) is
        ``ads[0]`` of its (only) ad set, ``execute()`` propagates
        ``AttributeError`` while building ``creatives``, since that loop
        unconditionally evaluates ``ad_creative.get('asset_feed_spec', {})``
        on ``ads_to_publish.get('adCreative')`` without checking that the
        result is truthy first: for ``adCreative`` absent or ``None``,
        ``ad.get('adCreative')`` yields ``None``, and ``None.get(...)``
        raises ``AttributeError``. ``campaign_publish_repository.save_or_update``
        has already been invoked exactly once by the time the exception is
        raised, since ``_save_campaign_channel_publish`` runs before the
        ``creatives``-building loop.

        This is characterized as current behaviour, not a pending fix.

        Requirements: 7.3
        """
        for ad_creative_value, ad_creative_key_present in [(ABSENT, False), (None, True)]:
            campaign_data = make_campaign_data_dict()
            use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
                complete_campaign_data=campaign_data, creative_type="DYNAMIC"
            )

            if ad_creative_key_present:
                creativeless_ad = make_ad(ad_creative=ad_creative_value)
            else:
                creativeless_ad = make_ad()
            ad_set = make_ad_set(ads=[creativeless_ad])
            meta_payload = make_meta_payload(ad_sets=[ad_set])

            with patch_execute_dependencies() as deps:
                deps.redis_client.get.return_value = b"token"
                deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                    meta_payload
                )
                deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                    make_ad_account_info(),
                    200,
                )
                deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                    make_minimum_budget_response(),
                    200,
                )

                with pytest.raises(AttributeError):
                    use_case.execute()

            mock_campaign_publish_repo_instance.save_or_update.assert_called_once()

    def test_missing_creative_as_ads_zero_empty_dict_does_not_raise_and_yields_ok_1(
        self, use_case_factory
    ):
        """Characterization of a discrepancy versus a literal reading of
        Requirement 7.3: when the creativeless ad is ``ads[0]`` of its ad
        set and its ``adCreative`` is an empty dict ``{}`` (as opposed to
        absent or ``None``), ``execute()`` does **not** raise
        ``AttributeError``. ``{}.get('asset_feed_spec', {})`` is a valid
        call on a real (empty) dict, so the ``creatives``-building loop
        completes normally for this value; only ``adCreative`` absent or
        ``None`` (verified above) make ``ad.get('adCreative')`` yield
        ``None``, whose ``.get(...)`` call is what actually raises
        ``AttributeError``. For ``adCreative={}`` as the only/first ad,
        ``execute()`` instead returns normally with ``ok=1``: the
        creativeless-ad failure is still recorded as a ``Failed`` entry in
        the internal, non-observable ``results`` list, but that entry no
        longer reaches the Final Response. This confirms the return is
        current behaviour and not a test bug.

        Requirements: 7.3
        """
        campaign_data = make_campaign_data_dict()
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )

        creativeless_ad = make_ad(ad_creative={})
        ad_set = make_ad_set(ads=[creativeless_ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1
        mock_campaign_publish_repo_instance.save_or_update.assert_called_once()

class TestExecuteDynamicBranch:
    """Requirement 8: the DYNAMIC branch of ``execute()``.

    This class only covers the titles/bodies/descriptions text-validation
    try/except blocks at the top of the DYNAMIC branch (task 7.1)::

        if self.creative_type == "DYNAMIC" and asset_feed:

            try:
                titles = asset_feed.get('titles', [])
                titles_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in titles])
                asset_feed['unique_titles'] = titles_inique_texts
                MetaAdsValidator.is_valid_length('titles', titles)
            except ValueError as e:
                current_ad_errors.append({'slug': 'title-error', ...})

            try:
                bodies = asset_feed.get('bodies', [])
                bodies_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in bodies])
                asset_feed['unique_bodies'] = bodies_inique_texts
                MetaAdsValidator.is_valid_length('bodies', bodies)
            except ValueError as e:
                current_ad_errors.append({'slug': 'body-error', ...})

            try:
                descriptions = asset_feed.get('descriptions', [])
                descriptions_inique_texts = MetaAdsValidator.is_unique_texts([t.get('text') for t in descriptions])
                asset_feed['unique_descriptions'] = descriptions_inique_texts
                MetaAdsValidator.is_valid_length('descriptions', descriptions)
            except ValueError as e:
                current_ad_errors.append({'slug': 'description-error', ...})

    CTAs, images, assets-amount, budget and link URL validations (the rest
    of Requirement 8) are covered by later tasks in this same class.

    Requirements: 8.1, 8.2, 8.3
    """

    @staticmethod
    def _run_single_dynamic_text_ad(use_case_factory, asset_feed, daily_budget=100, min_daily_budget=50):
        """Drive a full ``execute()`` call for a single DYNAMIC ad whose
        ``asset_feed_spec`` is the exact ``asset_feed`` dict passed in by
        the caller, so it can be inspected for in-place mutations after
        ``execute()`` returns (production code mutates the very same dict
        object it receives through ``MetaAdsPayloadBuilder.build_meta_payload``,
        never a copy).

        ``call_to_action_types``, ``images`` and ``link_urls`` are left at
        their ``make_asset_feed_spec`` defaults (empty lists), and
        ``daily_budget``/``min_daily_budget`` default to comparable numeric
        values, so the CTA/images/assets-amount/budget/link-url
        sub-validations (out of scope for this task) stay inert and do not
        add unrelated errors that could confound the scenario.

        Requirements: 8.1, 8.2, 8.3, 14.3
        """
        campaign_data = make_campaign_data_dict()
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        ad = make_ad(ad_creative=ad_creative)
        ad_set = make_ad_set(ads=[ad], daily_budget=daily_budget)
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    min_daily_budget_imp=int(min_daily_budget * 100)
                ),
                200,
            )
            result, status_code = use_case.execute()

        return result, status_code

    def test_calls_is_unique_texts_and_is_valid_length_exactly_once_per_collection_and_assigns_unique_keys(
        self, use_case_factory
    ):
        """When ``creative_type="DYNAMIC"`` and ``asset_feed_spec`` is
        present, ``MetaAdsValidator.is_unique_texts`` is invoked exactly
        once per collection with ``[t.get('text') for t in <collection>]``
        for ``titles``, ``bodies`` and ``descriptions`` respectively (in
        that order), ``MetaAdsValidator.is_valid_length`` is invoked exactly
        once per collection with ``('<type>', <collection>)`` (the very same
        list object read from ``asset_feed``), and ``asset_feed['unique_titles']``,
        ``asset_feed['unique_bodies']`` and ``asset_feed['unique_descriptions']``
        each end up holding the value returned by their own
        ``is_unique_texts`` call, not a value shared across collections.

        Requirements: 8.1, 8.2
        """
        asset_feed = make_asset_feed_spec(
            titles=[{"text": "Title A"}],
            bodies=[{"text": "Body A"}],
            descriptions=[{"text": "Description A"}],
        )
        titles_list = asset_feed["titles"]
        bodies_list = asset_feed["bodies"]
        descriptions_list = asset_feed["descriptions"]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            side_effect=[True, False, True],
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ) as mock_is_valid_length:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert mock_is_unique_texts.call_args_list == [
            call(["Title A"]),
            call(["Body A"]),
            call(["Description A"]),
        ]
        assert mock_is_valid_length.call_args_list == [
            call("titles", titles_list),
            call("bodies", bodies_list),
            call("descriptions", descriptions_list),
        ]
        assert asset_feed["unique_titles"] is True
        assert asset_feed["unique_bodies"] is False
        assert asset_feed["unique_descriptions"] is True

    @pytest.mark.parametrize(
        "collection, unique_key",
        [
            ("titles", "unique_titles"),
            ("bodies", "unique_bodies"),
            ("descriptions", "unique_descriptions"),
        ],
        ids=["titles", "bodies", "descriptions"],
    )
    def test_is_unique_texts_raising_removes_only_the_corresponding_unique_key_and_yields_ok_1(
        self, use_case_factory, collection, unique_key
    ):
        """When ``MetaAdsValidator.is_unique_texts`` raises ``ValueError``
        for exactly one collection (``titles``, ``bodies`` or
        ``descriptions``), the exception is raised *before* the
        ``asset_feed['unique_<collection>'] = ...`` assignment for that
        collection's try block is reached, so that specific key is absent
        from the ``asset_feed`` dict the test constructed and passed into
        the run, while the other two collections' ``unique_*`` keys (whose
        try blocks ran without any forced failure) are present as usual.
        For a run where this is the only ad, the Final Response's ``ok`` is
        ``0``.

        Requirements: 8.3
        """
        asset_feed = make_asset_feed_spec(
            titles=[{"text": "Title A"}],
            bodies=[{"text": "Body A"}],
            descriptions=[{"text": "Description A"}],
        )

        order = ["titles", "bodies", "descriptions"]
        side_effect = [
            ValueError(f"{name} are not unique") if name == collection else True
            for name in order
        ]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            side_effect=side_effect,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ):
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert unique_key not in asset_feed
        for other_key in ("unique_titles", "unique_bodies", "unique_descriptions"):
            if other_key != unique_key:
                assert other_key in asset_feed
        assert result["ok"] == 1

    @pytest.mark.parametrize(
        "collection, unique_key",
        [
            ("titles", "unique_titles"),
            ("bodies", "unique_bodies"),
            ("descriptions", "unique_descriptions"),
        ],
        ids=["titles", "bodies", "descriptions"],
    )
    def test_is_valid_length_raising_still_leaves_the_unique_key_present_and_yields_ok_1(
        self, use_case_factory, collection, unique_key
    ):
        """Characterization of a nuance in the current code that a purely
        literal reading of Requirement 8.3 does not distinguish: within each
        collection's try block, ``asset_feed['unique_<collection>']`` is
        assigned *before* ``MetaAdsValidator.is_valid_length`` is called, so
        when the forced ``ValueError`` originates from ``is_valid_length``
        itself (rather than from ``is_unique_texts``), the success
        assignment for that same collection has already happened by the
        time the exception is caught, and remains present in ``asset_feed``
        afterwards -- unlike the ``is_unique_texts``-raises case exercised
        above, where the assignment is never reached. This mirrors the kind
        of documented current-behaviour nuance already characterized
        elsewhere in this suite (e.g. Requirement 7.3's ``{}`` vs
        absent/``None`` distinction, and the ``assets-budget-error`` slug
        reuse for Requirement 8.11/8.13). What holds for both doubles, and
        what this test verifies, is that a run where this is the only ad
        still ends up with ``ok=1``: the caught ``ValueError`` does not
        propagate, and ``execute()`` returns the literal ``ok=1`` for every
        run because the conditional that consumed ``has_errors`` is
        commented out.

        Requirements: 8.3
        """
        asset_feed = make_asset_feed_spec(
            titles=[{"text": "Title A"}],
            bodies=[{"text": "Body A"}],
            descriptions=[{"text": "Description A"}],
        )

        order = ["titles", "bodies", "descriptions"]
        side_effect = [
            ValueError(f"{name} length invalid") if name == collection else None
            for name in order
        ]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            side_effect=side_effect,
        ):
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        # Unlike the is_unique_texts-raises scenario above, the assignment
        # already happened before is_valid_length was called, for every
        # collection, including the one whose is_valid_length call raised.
        assert asset_feed["unique_titles"] is True
        assert asset_feed["unique_bodies"] is True
        assert asset_feed["unique_descriptions"] is True
        assert result["ok"] == 1

    def test_calls_validate_cta_once_per_cta_entry_with_throw_false_and_assigns_valid_key(
        self, use_case_factory
    ):
        """When ``asset_feed['call_to_action_types']`` contains one or more
        entries, ``MetaAdsValidator.validate_cta_for_goal`` is invoked
        exactly once per entry, in order, with the exact keyword arguments
        ``cta_text=cta.get('value')``, ``objective=self.objective``,
        ``goal=self.optimization_goal``, ``throw=False``, and ``cta['valid']``
        ends up holding the exact boolean value returned by that entry's
        own call, mutated in place on the very same ``cta`` dict object the
        test constructed and passed into the run (``self.objective``/
        ``self.optimization_goal`` default to ``"OUTCOME_AWARENESS"``/
        ``"REACH"`` via ``make_campaign_data_dict``, used unmodified by
        ``_run_single_dynamic_text_ad``).

        Note: production code (``execute()``'s DYNAMIC branch) calls
        ``MetaAdsValidator.validate_cta_for_goal``, not ``validate_cta``
        (which is only used by the STANDARD branch); this test patches the
        collaborator that is actually invoked here.

        Requirements: 8.4
        """
        asset_feed = make_asset_feed_spec(
            call_to_action_types=[
                {"value": "LEARN_MORE"},
                {"value": "SIGN_UP"},
            ],
        )
        cta_entries = asset_feed["call_to_action_types"]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal",
            side_effect=[True, False],
        ) as mock_validate_cta_for_goal:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert mock_validate_cta_for_goal.call_args_list == [
            call(
                cta_text="LEARN_MORE",
                objective="OUTCOME_AWARENESS",
                goal="REACH",
                throw=False,
            ),
            call(
                cta_text="SIGN_UP",
                objective="OUTCOME_AWARENESS",
                goal="REACH",
                throw=False,
            ),
        ]
        assert cta_entries[0]["valid"] is True
        assert cta_entries[1]["valid"] is False

    def test_validate_cta_raising_for_every_entry_leaves_no_valid_key_and_iteration_continues(
        self, use_case_factory
    ):
        """Characterization of Requirement 8.5: when the objective/
        optimization goal combination is unsupported,
        ``MetaAdsValidator.validate_cta_for_goal`` never reaches the
        ``cta['valid'] = valid_cta`` success assignment for any entry,
        because the per-CTA ``try/except ValueError`` block inside the
        ``for cta in ctas`` loop of ``execute()`` catches the failure and
        lets the loop continue to the next entry rather than aborting the
        whole ad.

        This is exercised with ``MetaAdsValidator.validate_cta_for_goal``
        patched with a ``side_effect`` that always raises ``ValueError``
        (simulating the unsupported-combination failure regardless of the
        ``throw=False`` argument production code passes), rather than by
        relying on the real, unpatched implementation. The fact that
        ``validate_cta_for_goal`` is called once per CTA entry -- not just
        for the first one -- is itself the evidence that the iteration
        continued past each failure instead of stopping there.

        Requirements: 8.5
        """
        asset_feed = make_asset_feed_spec(
            call_to_action_types=[
                {"value": "LEARN_MORE"},
                {"value": "SIGN_UP"},
                {"value": "SHOP_NOW"},
            ],
        )
        cta_entries = asset_feed["call_to_action_types"]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal",
            side_effect=ValueError(
                "Optimization goal is not valid for objective"
            ),
        ) as mock_validate_cta_for_goal:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert mock_validate_cta_for_goal.call_count == len(cta_entries)
        for cta in cta_entries:
            assert "valid" not in cta
        assert result["ok"] == 1

    def test_calls_validate_images_precheck_once_with_the_full_images_list(
        self, use_case_factory
    ):
        """When ``asset_feed['images']`` contains entries with ``url``,
        ``MetaAdsValidator.validate_images_precheck`` is invoked exactly
        once with the full ``images`` list -- the very same list object read
        from ``asset_feed.get('images', [])``, verified by identity -- with
        the call patched so no real HTTP request is attempted.

        Production code also builds a derived ``images_urls`` list
        (``[img.get('url') for img in images if img.get('url')]``) right
        before this call, but that derived list is never actually passed to
        ``validate_images_precheck``; only the original ``images`` list is,
        as confirmed by reading ``app/v2/use_cases/meta_ads.py`` directly.

        Requirements: 8.6
        """
        asset_feed = make_asset_feed_spec(
            images=[
                {"url": "https://example.com/a.jpg"},
                {"url": "https://example.com/b.jpg"},
            ],
        )
        images_list = asset_feed["images"]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            return_value=None,
        ) as mock_validate_images_precheck:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        mock_validate_images_precheck.assert_called_once()
        (called_images,), called_kwargs = mock_validate_images_precheck.call_args
        assert called_images is images_list
        assert called_kwargs == {}

    def test_validate_images_precheck_raising_yields_ok_1(self, use_case_factory):
        """When a double substitutes ``validate_images_precheck`` and it
        raises ``ValueError``, the Final Response still contains ``ok=1``
        for a run where this is the only ad: ``execute()`` returns the
        literal ``ok=1`` because the conditional that consumed
        ``has_errors`` is commented out. This validation has no success-path
        mutation whatsoever (not even on the non-error path), so the
        call-argument assertion of the previous test carries the
        discriminating evidence for this scenario, while what this test pins
        down is that the raised ``ValueError`` is caught and leaves the
        Final Response untouched.

        Requirements: 8.7
        """
        asset_feed = make_asset_feed_spec(
            images=[{"url": "https://example.com/a.jpg"}],
        )

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            side_effect=ValueError("image is invalid"),
        ):
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert result["ok"] == 1

    def test_calls_is_valid_amount_exactly_once_with_asset_feed_creative_type_and_none(
        self, use_case_factory
    ):
        """``MetaAdsValidator.is_valid_amount`` is invoked exactly once with
        the exact positional arguments ``(asset_feed, self.creative_type,
        None)``, where ``asset_feed`` is the very same dict object the test
        constructed and passed into the run, verified by identity.

        Requirements: 8.8
        """
        asset_feed = make_asset_feed_spec()

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ) as mock_is_valid_amount:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        mock_is_valid_amount.assert_called_once()
        (called_asset_feed, called_creative_type, called_story_spec), called_kwargs = (
            mock_is_valid_amount.call_args
        )
        assert called_asset_feed is asset_feed
        assert called_creative_type == "DYNAMIC"
        assert called_story_spec is None
        assert called_kwargs == {}

    def test_is_valid_amount_raising_yields_ok_1(self, use_case_factory):
        """When a double substitutes ``is_valid_amount`` and it raises
        ``ValueError``, the Final Response still contains ``ok=1`` for a run
        where this is the only ad: ``execute()`` returns the literal
        ``ok=1`` because the conditional that consumed ``has_errors`` is
        commented out. ``is_valid_amount`` assigns nothing on either the
        success or the failure path, so the call-argument assertion of the
        previous test carries the discriminating evidence for this scenario,
        while what this test pins down is that the raised ``ValueError`` is
        caught and leaves the Final Response untouched.

        Requirements: 8.9
        """
        asset_feed = make_asset_feed_spec()

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            side_effect=ValueError("too many assets"),
        ):
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        assert result["ok"] == 1

    @pytest.mark.parametrize(
        "daily_budget, min_daily_budget, expected_valid",
        [
            (100, 50, True),
            (10, 50, False),
        ],
        ids=["daily-budget-above-min", "daily-budget-below-min"],
    )
    def test_min_daily_budget_and_daily_budget_valid_assigned_when_daily_budget_comparable(
        self, use_case_factory, daily_budget, min_daily_budget, expected_valid
    ):
        """When ``ad_set.get('daily_budget', 0)`` is a value comparable with
        ``min_budget`` (an ``int``/``float`` on both sides), the try block
        never raises: ``asset_feed['min_daily_budget']`` is assigned the
        exact ``min_budget`` value returned by ``_get_minimum_budget`` (the
        ``min_daily_budget_imp / 100`` conversion), and
        ``asset_feed['daily_budget_valid']`` is assigned the exact boolean
        result of the ``ad_set.get('daily_budget', 0) >= min_budget``
        comparison -- ``True`` when the ad set's budget is at or above the
        minimum, ``False`` when it is below.

        Requirements: 8.10
        """
        asset_feed = make_asset_feed_spec()

        result, status_code = self._run_single_dynamic_text_ad(
            use_case_factory,
            asset_feed,
            daily_budget=daily_budget,
            min_daily_budget=min_daily_budget,
        )

        assert status_code == 200
        assert asset_feed["min_daily_budget"] == pytest.approx(min_daily_budget)
        assert asset_feed["daily_budget_valid"] is expected_valid

    def test_non_comparable_daily_budget_leaves_min_daily_budget_present_but_daily_budget_valid_absent(
        self, use_case_factory
    ):
        """When ``ad_set['daily_budget']`` is an explicit value that is not
        comparable with ``min_budget`` (``None`` here, which raises
        ``TypeError`` when compared with ``>=`` against a ``float``), the
        ``asset_feed['min_daily_budget'] = min_budget`` assignment on the
        line *before* the raising comparison still runs and is present
        afterwards, while ``asset_feed['daily_budget_valid']`` -- assigned
        on the very next line, only reached if the comparison succeeds --
        is absent. The generic ``except Exception`` (not just
        ``except ValueError``) around this try block is what catches the
        ``TypeError`` here, appending an ``assets-budget-error`` entry to
        the local ``results``/``current_ad_errors`` list. That entry no
        longer reaches the Final Response's ``ok`` field: ``execute()``
        returns the literal ``ok=1`` for every run because the conditional
        that consumed ``has_errors`` is commented out.

        Requirements: 8.11
        """
        asset_feed = make_asset_feed_spec()

        result, status_code = self._run_single_dynamic_text_ad(
            use_case_factory,
            asset_feed,
            daily_budget=None,
            min_daily_budget=50,
        )

        assert status_code == 200
        assert asset_feed["min_daily_budget"] == pytest.approx(50)
        assert "daily_budget_valid" not in asset_feed
        assert result["ok"] == 1

    def test_calls_is_valid_link_url_with_comma_joined_website_urls_and_assigns_link_url_valid(
        self, use_case_factory
    ):
        """When ``asset_feed['link_urls']`` contains valid entries with a
        ``website_url`` key, ``MetaAdsValidator.is_valid_link_url`` is
        invoked exactly once with the comma-joined string of every entry's
        ``website_url`` -- ``','.join([u.get('website_url') for u in
        asset_feed.get('link_urls', [])])``, built in that exact order --
        and ``asset_feed['link_url_valid']`` ends up holding the exact
        value returned by that call.

        Requirements: 8.12
        """
        asset_feed = make_asset_feed_spec(
            link_urls=[
                {"website_url": "https://example.com/a"},
                {"website_url": "https://example.com/b"},
            ],
        )

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ) as mock_is_valid_link_url:
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory, asset_feed
            )

        assert status_code == 200
        mock_is_valid_link_url.assert_called_once_with(
            "https://example.com/a,https://example.com/b"
        )
        assert asset_feed["link_url_valid"] is True

    def test_invalid_link_urls_entry_leaves_link_url_valid_absent_while_daily_budget_valid_stays_present(
        self, use_case_factory
    ):
        """Characterization of the internal ``assets-budget-error`` slug
        reuse documented in the design (section "Slug duplicado
        assets-budget-error"): a ``None`` entry inside
        ``asset_feed['link_urls']`` makes the list comprehension's
        ``u.get('website_url')`` raise ``AttributeError`` (``None`` has no
        ``.get``), which is caught by the *same* generic
        ``except Exception`` pattern used by the budget try/except right
        above it in ``execute()``. Both try/except blocks append a
        ``current_ad_errors`` entry with the exact same
        ``slug='assets-budget-error'`` string, so that slug is *not*
        observable or distinguishable from outside ``execute()`` (``results``
        never becomes part of the Final Response). The only way this test
        can tell "the URL validation failed" apart from "the budget
        validation failed" is the combination of mutation keys left behind
        on the ``asset_feed`` dict: this scenario keeps the daily budget
        comparable (so the earlier try/except succeeds and leaves
        ``daily_budget_valid`` present), while ``link_url_valid`` is absent
        because the URL try/except's assignment line is never reached.

        The failing ad is placed as the *second* ad of its ad set rather
        than as ``ads[0]`` (unlike ``_run_single_dynamic_text_ad``'s usual
        single-ad shape). This is necessary because the ``creatives``-
        building loop that runs later in ``execute()`` unconditionally
        re-reads ``ad_creative.get('asset_feed_spec', {}).get('link_urls',
        [])`` from ``ads_to_publish = ad_set_to_publish.get('ads')[0]`` and
        re-executes the very same unguarded ``u.get('website_url')`` list
        comprehension *outside* of any try/except. If the failing ad were
        ``ads[0]``, that second, unrelated occurrence of the same unguarded
        comprehension would also raise ``AttributeError``, this time
        uncaught, propagating out of ``execute()`` entirely instead of being
        caught and recorded in the internal ``results`` list while
        ``execute()`` still returns its Final Response. This is the same
        "unconditional ``ads[0]``
        read" caveat already characterized for Requirement 7.3's
        ``creatives``-building loop, here triggered by a different unguarded
        expression reading the same malformed ``link_urls`` list. Placing
        the failing ad as a non-first ad (with a fully valid filler ad as
        ``ads[0]``) keeps the scenario within the per-ad validation loop's
        own try/except, which is what Requirement 8.13 is actually
        characterizing.

        Requirements: 8.13
        """
        campaign_data = make_campaign_data_dict()
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )

        filler_asset_feed = make_asset_feed_spec(
            link_urls=[{"website_url": "https://example.com/filler"}],
        )
        filler_ad = make_ad(
            name="FillerAd",
            ad_creative=make_ad_creative(
                name="FillerCreative", asset_feed_spec=filler_asset_feed
            ),
        )

        asset_feed = make_asset_feed_spec(
            link_urls=[{"website_url": "https://example.com/a"}, None],
        )
        target_ad = make_ad(
            name="TargetAd",
            ad_creative=make_ad_creative(
                name="TargetCreative", asset_feed_spec=asset_feed
            ),
        )

        ad_set = make_ad_set(ads=[filler_ad, target_ad], daily_budget=100)
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ):
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(min_daily_budget_imp=5000),
                200,
            )

            result, status_code = use_case.execute()

        assert status_code == 200
        assert asset_feed["daily_budget_valid"] is True
        assert "link_url_valid" not in asset_feed
        assert result["ok"] == 1

    def test_fully_valid_dynamic_ad_yields_ok_one_with_every_success_mutation_present(
        self, use_case_factory
    ):
        """When every DYNAMIC validation in this class and in tasks 7.1/7.2
        succeeds -- no double is configured to raise, and the daily budget
        and link URLs are both valid/comparable -- the Final Response
        contains ``ok=1`` for a run where this is the only ad, and all six
        success mutations end up present simultaneously on the very same
        ``asset_feed``/``cta`` objects the test constructed:
        ``unique_titles``, ``unique_bodies``, ``unique_descriptions``,
        ``cta['valid']`` (for the single CTA entry), ``daily_budget_valid``
        and ``link_url_valid``.

        Requirements: 8.14
        """
        asset_feed = make_asset_feed_spec(
            titles=[{"text": "Title A"}],
            bodies=[{"text": "Body A"}],
            descriptions=[{"text": "Description A"}],
            call_to_action_types=[{"value": "LEARN_MORE"}],
            images=[{"url": "https://example.com/a.jpg"}],
            link_urls=[{"website_url": "https://example.com/a"}],
        )
        cta_entry = asset_feed["call_to_action_types"][0]

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ):
            result, status_code = self._run_single_dynamic_text_ad(
                use_case_factory,
                asset_feed,
                daily_budget=100,
                min_daily_budget=50,
            )

        assert status_code == 200
        assert result["ok"] == 1
        assert asset_feed["unique_titles"] is True
        assert asset_feed["unique_bodies"] is True
        assert asset_feed["unique_descriptions"] is True
        assert cta_entry["valid"] is True
        assert asset_feed["daily_budget_valid"] is True
        assert asset_feed["link_url_valid"] is True


class TestExecuteStandardBranch:
    """Shared STANDARD-branch test infrastructure (Requirement 9's branch is
    now driven entirely through ``self._validate_standard_creative(...)``,
    wired in by task 5.1, replacing the old inline ``validate_cta``/
    ``validate_images``/``validate_assets_amount`` logic this class used to
    characterize).

    Per the design decision recorded in ``design.md`` ("Reemplazo de
    `TestExecuteStandardBranch`"), the 9 tests that characterized the old
    logic (fixed to a single, then-unsupported-under-the-new-guard
    objective/optimization_goal pair, and to ``validate_cta``/
    ``validate_images``/``validate_assets_amount``) are removed wholesale
    rather than amended: they are not protected by Requirement 14's
    no-regression guarantee (which only covers invocations without
    STANDARD ads, Requirement 14.5). The new STANDARD test coverage lives
    in the dedicated classes added by tasks 11-20 (
    ``TestStandardCombinationSupport``, ``TestStandardTextFieldValidation``,
    ``TestStandardImageValidation``, ``TestStandardUrlValidation``,
    ``TestStandardDailyBudgetValidation``, ``TestStandardCtaValidation``,
    ``TestStandardAnnotationContract``, ``TestStandardCreativesEntry``,
    ``TestStandardCombinationSuccessScenarios``).

    Only the ``_run_single_standard_ad`` helper survives here, reused by
    those new classes (analogous to
    ``TestExecuteDynamicBranch._run_single_dynamic_text_ad`` for the
    DYNAMIC branch), reworked to accept an explicit ``objective``/
    ``optimization_goal`` pair defaulting to one of the 5 tuples in
    ``_STANDARD_SUPPORTED_COMBINATIONS`` (``OUTCOME_LEADS``/
    ``LEAD_GENERATION``) instead of relying on ``make_campaign_data_dict()``'s
    incidental default.

    Requirements: 14.5, 15.1
    """

    @staticmethod
    def _run_single_standard_ad(
        use_case_factory,
        object_story_spec,
        objective=CampaignObjective.LEADS.value,
        optimization_goal=LeadsOptimizationGoal.LEAD_GENERATION.value,
        min_daily_budget=50,
    ):
        """Drive a full ``execute()`` call for a single STANDARD ad whose
        ``object_story_spec`` is the exact dict passed in by the caller
        (mirrors ``TestExecuteDynamicBranch._run_single_dynamic_text_ad``,
        adapted for the STANDARD branch: no ``asset_feed_spec`` is built,
        since STANDARD reads exclusively from ``object_story_spec``).

        ``objective``/``optimization_goal`` default to a combination
        belonging to ``_STANDARD_SUPPORTED_COMBINATIONS`` (``OUTCOME_LEADS``/
        ``LEAD_GENERATION``) rather than ``make_campaign_data_dict()``'s
        incidental default, so callers that don't care about the
        combination-support guard (Requirement 2) get a supported
        combination out of the box; callers exercising unsupported
        combinations pass their own values explicitly.

        Requirements: 14.5, 15.1
        """
        campaign_data = make_campaign_data_dict(
            objective=objective, optimization_goal=optimization_goal
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="STANDARD"
        )
        ad_creative = make_ad_creative(object_story_spec=object_story_spec)
        ad = make_ad(ad_creative=ad_creative)
        ad_set = make_ad_set(ads=[ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(
                    min_daily_budget_imp=int(min_daily_budget * 100)
                ),
                200,
            )
            result, status_code = use_case.execute()

        return result, status_code


class TestStandardCombinationSupport:
    """Requirement 13: the guard, evaluated once in ``execute()`` before
    ``results = []``/``for ad_set in ad_sets:``, that verifies
    ``(self.objective, self.optimization_goal)`` belongs to
    ``_STANDARD_SUPPORTED_COMBINATIONS`` whenever
    ``self.creative_type == "STANDARD"``::

        if self.creative_type == CreativeType.STANDARD.value and not self._is_standard_combination_supported():
            raise MetaException("META011", ...)

    Feature: meta-ads-standard-precheck-validation, Property 1: Excepción
    única y previa al bucle ante combinación no soportada -- para toda
    combinación ``(objective, optimization_goal)`` no soportada,
    ``execute()`` SHALL lanzar ``MetaException(code="META011")`` antes de
    iterar sobre ``ad_sets``/``ads``, SHALL NOT invocar ninguno de
    ``MetaAdsValidator.is_valid_length``/``validate_images_precheck``/
    ``is_valid_link_url``/``validate_cta_for_goal``, ni
    ``_save_campaign_channel_publish``/``_save_creative_to_publish``.

    Validates: Property 1 -- Requirements 2.2, 13.1, 13.2, 13.4, 15.6
    """

    @staticmethod
    def _run_execute_for_combination(use_case_factory, objective, optimization_goal):
        """Drive a full ``execute()`` call for a STANDARD use case whose
        ``objective``/``optimization_goal`` are exactly the values passed
        in, with every guard unrelated to Property 1 bypassed so the only
        exception that can possibly propagate is the one under test:

        - ``pixel_id``/``lead_gen_form_id``/``whatsapp_number_id`` are all
          populated on ``complete_campaign_data`` so ``META001``/``META007``/
          ``META008`` (missing-value guards) never fire regardless of the
          generated ``objective``/``optimization_goal``.
        - ``_validate_pixel_eligibility``/``_validate_page_whatsapp_eligibility``
          (both real HTTP calls in production) are patched on the instance
          to return ``True``, so ``META006``/``META009`` never fire and no
          network request is attempted.
        - ``MetaAdsValidator.validate_optimization_goal_for_objective`` is
          patched to return ``True``, so ``META002`` never fires -- the same
          pattern already used elsewhere in this file (see
          ``test_valid_ctas_matches_recommended_ctas_set_for_valid_objective``)
          to isolate a scenario from that unrelated guard.
        - ``creative_type`` is always ``"STANDARD"``, so ``META010`` (which
          requires ``DYNAMIC``) never fires.

        ``ad_sets`` is left at its default empty list: Property 1 requires
        the guard to fire (or, for a supported combination, execute() to
        complete) before any iteration over ``ad_sets``/``ads``, so no ad
        payload is needed at all to exercise it.

        Returns a 4-tuple ``(exception, result, status_code, collaborators)``:
        ``exception`` is the caught ``MetaException`` (or ``None`` if
        ``execute()`` completed normally); ``result``/``status_code`` are
        ``execute()``'s return value (or ``None``/``None`` if it raised);
        ``collaborators`` is a ``SimpleNamespace`` exposing the 4 patched
        ``MetaAdsValidator`` collaborators and the 2 patched persistence
        methods as ``MagicMock``s, for ``assert_not_called()`` assertions.
        """
        campaign_data = make_campaign_data_dict(
            objective=objective,
            optimization_goal=optimization_goal,
            pixel_id="pixel-1",
            lead_gen_form_id="lead-1",
            whatsapp_number_id="whatsapp-1",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="STANDARD"
        )
        meta_payload = make_meta_payload()

        with patch.object(
            use_case, "_validate_pixel_eligibility", return_value=True
        ), patch.object(
            use_case, "_validate_page_whatsapp_eligibility", return_value=True
        ), patch.object(
            use_case, "_save_campaign_channel_publish"
        ) as mock_save_campaign_channel_publish, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_optimization_goal_for_objective",
            return_value=True,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url"
        ) as mock_is_valid_link_url, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal"
        ) as mock_validate_cta_for_goal, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            collaborators = SimpleNamespace(
                is_valid_length=mock_is_valid_length,
                validate_images_precheck=mock_validate_images_precheck,
                is_valid_link_url=mock_is_valid_link_url,
                validate_cta_for_goal=mock_validate_cta_for_goal,
                save_campaign_channel_publish=mock_save_campaign_channel_publish,
                save_creative_to_publish=mock_save_creative_to_publish,
            )

            exception = None
            result = None
            status_code = None
            try:
                result, status_code = use_case.execute()
            except MetaException as exc:
                exception = exc

        return exception, result, status_code, collaborators

    # Feature: meta-ads-standard-precheck-validation, Property 1: para toda
    # combinación (objective, optimization_goal) no soportada, execute()
    # SHALL lanzar MetaException(code="META011") antes de iterar sobre
    # ad_sets/ads, y SHALL NOT invocar ninguno de los 4 colaboradores de
    # MetaAdsValidator ni _save_campaign_channel_publish/_save_creative_to_publish.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(pair=unsupported_objective_optimization_pairs())
    def test_property_unsupported_combination_raises_meta011_before_loop(
        self, use_case_factory, pair
    ):
        """For any ``(objective, optimization_goal)`` pair not present in
        ``_STANDARD_SUPPORTED_COMBINATIONS``, ``execute()`` raises
        ``MetaException(code="META011")`` without ever invoking any of the
        4 ``MetaAdsValidator`` collaborators nor
        ``_save_campaign_channel_publish``/``_save_creative_to_publish``.

        Validates: Property 1 -- Requirements 2.2, 13.1, 13.2, 13.4, 15.6
        """
        objective, optimization_goal = pair

        exception, result, status_code, collaborators = (
            self._run_execute_for_combination(
                use_case_factory, objective, optimization_goal
            )
        )

        assert exception is not None
        assert exception.code == "META011"
        assert result is None
        assert status_code is None
        collaborators.is_valid_length.assert_not_called()
        collaborators.validate_images_precheck.assert_not_called()
        collaborators.is_valid_link_url.assert_not_called()
        collaborators.validate_cta_for_goal.assert_not_called()
        collaborators.save_campaign_channel_publish.assert_not_called()
        collaborators.save_creative_to_publish.assert_not_called()

    @pytest.mark.parametrize(
        "objective, optimization_goal",
        STANDARD_SUPPORTED_COMBINATIONS,
        ids=STANDARD_SUPPORTED_COMBINATIONS_IDS,
    )
    def test_supported_combination_does_not_raise_meta011(
        self, use_case_factory, objective, optimization_goal
    ):
        """Explicit example (Requirement 15.2, one per supported
        combination): for each of the 5 tuples in
        ``_STANDARD_SUPPORTED_COMBINATIONS``, ``execute()`` does not raise
        ``MetaException("META011", ...)`` and completes normally instead.

        Requirements: 2.2, 13.1, 13.3, 15.2
        """
        exception, result, status_code, _ = self._run_execute_for_combination(
            use_case_factory, objective, optimization_goal
        )

        assert exception is None
        assert result is not None
        assert status_code == 200

    def test_objective_and_optimization_goal_both_none_raises_meta011(
        self, use_case_factory
    ):
        """Explicit example: ``objective``/``optimization_goal`` both
        ``None`` -- trivially not a member of
        ``_STANDARD_SUPPORTED_COMBINATIONS`` -- raises
        ``MetaException(code="META011")`` before any iteration over
        ``ad_sets``/``ads``, without invoking any of the 4
        ``MetaAdsValidator`` collaborators nor
        ``_save_campaign_channel_publish``/``_save_creative_to_publish``.

        Requirements: 2.2, 13.1, 13.2, 13.4, 15.6
        """
        exception, result, status_code, collaborators = (
            self._run_execute_for_combination(use_case_factory, None, None)
        )

        assert exception is not None
        assert exception.code == "META011"
        assert result is None
        assert status_code is None
        collaborators.is_valid_length.assert_not_called()
        collaborators.validate_images_precheck.assert_not_called()
        collaborators.is_valid_link_url.assert_not_called()
        collaborators.validate_cta_for_goal.assert_not_called()
        collaborators.save_campaign_channel_publish.assert_not_called()
        collaborators.save_creative_to_publish.assert_not_called()


class TestStandardTextFieldValidation:
    """Requirements 3, 4, 5: título/cuerpo/descripción (Título_STANDARD/
    Cuerpo_STANDARD/Descripción_STANDARD) validation, driven directly
    through ``_validate_standard_text_field``::

        def _validate_standard_text_field(self, link_data, raw_value, field_name, annotation_key, error_slug, current_ad_errors):
            candidates = self._standard_candidate_values(raw_value)
            if len(candidates) != 1:
                link_data[annotation_key] = False
                current_ad_errors.append({...})
                return
            text_items = [{'text': candidates[0]}]
            MetaAdsValidator.is_valid_length(field_name, text_items)
            valid = text_items[0].get('valid_length', False)
            link_data[annotation_key] = valid
            if not valid:
                current_ad_errors.append({...})

    Parametrized by field, using the exact ``(field_name, link_data_key,
    annotation_key, max_length)`` tuples that ``_validate_standard_creative``
    itself uses for its 3 calls to ``_validate_standard_text_field`` (see
    ``meta_ads.py``): ``("title", "name", "title_valid", 255)``,
    ``("body", "message", "body_valid", 1024)``,
    ``("description", "description", "description_valid", 255)`` (the
    255/1024 limits come from ``TEXT_ASSET_MAX_LENGTH`` in
    ``facebook_validator_service.py``).

    Per the design decision recorded in ``design.md`` ("Las Properties 2 a
    6 y 8 se ejercitan invocando directamente los métodos privados
    nuevos... sin pasar por ``execute()`` completo, para mantener la
    generación de casos rápida y desacoplada de
    ``MetaAdsPayloadBuilder``/Redis/Strapi"), every test here calls
    ``_validate_standard_text_field`` directly on a use case instance built
    via ``use_case_factory``, instead of driving a full ``execute()``. This
    also isolates this field's behaviour from the other STANDARD
    validations (image/URL/budget/CTA), none of which
    ``_validate_standard_text_field`` ever touches.

    Feature: meta-ads-standard-precheck-validation, Property 2: conteo de
    candidatos distinto de 1 produce error controlado sin excepción -- para
    todo valor candidato cuya longitud de Valor_Candidato (según
    ``_standard_candidate_values``) sea distinta de 1, la validación
    correspondiente SHALL anotar el campo booleano asociado como ``False``,
    SHALL agregar exactamente un error a ``current_ad_errors``, y SHALL NOT
    invocar ``MetaAdsValidator.is_valid_length``, ni lanzar ninguna
    excepción no controlada.

    Feature: meta-ads-standard-precheck-validation, Property 3: la validez
    de longitud de un texto único equivale a ``is_valid_length`` -- para
    toda cadena de texto arbitraria usada como único Valor_Candidato de
    título, cuerpo o descripción, el valor anotado SHALL ser idéntico al
    que produciría invocar directamente
    ``MetaAdsValidator.is_valid_length(tipo, [{'text': cadena}])`` y leer
    ``valid_length``, y SHALL agregarse un error a ``current_ad_errors`` si
    y solo si ese valor es ``False``.

    Validates: Properties 2, 3 -- Requirements 3.1-3.5, 4.1-4.5, 5.1-5.5,
    15.3, 15.4
    """

    _FIELD_PARAMS = [
        ("title", "name", "title_valid", 255),
        ("body", "message", "body_valid", 1024),
        ("description", "description", "description_valid", 255),
    ]
    _FIELD_IDS = ["title", "body", "description"]

    @staticmethod
    def _run_text_field_validation(
        use_case_factory, field_name, link_data_key, annotation_key, raw_value
    ):
        """Build a STANDARD use case and drive
        ``_validate_standard_text_field`` directly for a single field,
        mirroring exactly how ``_validate_standard_creative`` itself
        invokes it (``link_data.get(link_data_key)`` as ``raw_value``,
        ``f"{field_name}-error"`` as the error slug).

        A brand new ``link_data``/``current_ad_errors`` list is built on
        every call (via ``make_link_data``, reused unmodified); nothing is
        shared across invocations. Returns ``(link_data, current_ad_errors)``
        so callers can inspect both the mutated ``link_data`` dict and the
        accumulated errors.

        Requirements: 3.1-3.5, 4.1-4.5, 5.1-5.5
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        link_data = make_link_data()
        link_data[link_data_key] = raw_value
        current_ad_errors = []

        use_case._validate_standard_text_field(
            link_data,
            link_data.get(link_data_key),
            field_name,
            annotation_key,
            f"{field_name}-error",
            current_ad_errors,
        )

        return link_data, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 2: para todo
    # valor candidato cuya longitud de Valor_Candidato sea distinta de 1
    # (longitud 0, o cualquier lista de longitud >= 2), la validación de
    # texto SHALL anotar el campo booleano asociado como False, SHALL
    # agregar exactamente un error a current_ad_errors, y SHALL NOT invocar
    # MetaAdsValidator.is_valid_length.
    @pytest.mark.parametrize(
        "field_name, link_data_key, annotation_key, max_length",
        _FIELD_PARAMS,
        ids=_FIELD_IDS,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(raw_value=standard_candidate_values_with_wrong_count())
    def test_property_candidate_count_not_one_short_circuits_without_calling_is_valid_length(
        self,
        use_case_factory,
        field_name,
        link_data_key,
        annotation_key,
        max_length,
        raw_value,
    ):
        """For any raw value whose ``_standard_candidate_values`` yields a
        candidate count different from 1 (0, or 2+), the field is annotated
        ``False`` and exactly one error is recorded, without
        ``MetaAdsValidator.is_valid_length`` ever being invoked -- the
        count-mismatch branch returns before reaching it.

        Validates: Property 2 -- Requirements 3.2, 3.3, 4.2, 4.3, 5.2, 5.3
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length:
            link_data, current_ad_errors = self._run_text_field_validation(
                use_case_factory, field_name, link_data_key, annotation_key, raw_value
            )

        assert link_data[annotation_key] is False
        assert len(current_ad_errors) == 1
        mock_is_valid_length.assert_not_called()

    # Feature: meta-ads-standard-precheck-validation, Property 3: para toda
    # cadena de texto arbitraria usada como único Valor_Candidato, el valor
    # anotado en title_valid/body_valid/description_valid SHALL ser
    # idéntico al que produciría invocar directamente
    # MetaAdsValidator.is_valid_length(tipo, [{'text': cadena}]) y leer
    # valid_length, y SHALL agregarse un error si y solo si ese valor es
    # False.
    @pytest.mark.parametrize(
        "field_name, link_data_key, annotation_key, max_length",
        _FIELD_PARAMS,
        ids=_FIELD_IDS,
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(text=arbitrary_text())
    def test_property_length_validity_mirrors_is_valid_length(
        self,
        use_case_factory,
        field_name,
        link_data_key,
        annotation_key,
        max_length,
        text,
    ):
        """For any text (including the empty string and strings well
        beyond the field's limit), wrapped as the sole element of a
        single-item list -- guaranteeing exactly 1 candidate regardless of
        whether ``text`` itself is falsy -- the annotated field mirrors
        exactly what invoking the real (unmocked)
        ``MetaAdsValidator.is_valid_length`` on an equivalent
        ``[{'text': text}]`` list produces, and an error is recorded if and
        only if that mirrored value is ``False``.

        Requirements: 3.1, 3.4, 3.5, 4.1, 4.4, 4.5, 5.1, 5.4, 5.5

        Validates: Property 3 -- Requirements 3.1, 3.4, 3.5, 4.1, 4.4, 4.5,
        5.1, 5.4, 5.5
        """
        link_data, current_ad_errors = self._run_text_field_validation(
            use_case_factory, field_name, link_data_key, annotation_key, [text]
        )

        control_items = [{"text": text}]
        MetaAdsValidator.is_valid_length(field_name, control_items)
        expected_valid = control_items[0]["valid_length"]

        assert link_data[annotation_key] == expected_valid
        if expected_valid:
            assert current_ad_errors == []
        else:
            assert len(current_ad_errors) == 1

    # Explicit example (Requirement 15.3): one exact text value 1
    # character over each field's max length.
    @pytest.mark.parametrize(
        "field_name, link_data_key, annotation_key, max_length",
        _FIELD_PARAMS,
        ids=_FIELD_IDS,
    )
    def test_length_exceeded_by_one_character_marks_invalid(
        self, use_case_factory, field_name, link_data_key, annotation_key, max_length
    ):
        """Explicit example: a single-candidate text exactly 1 character
        longer than the field's maximum length (255 for title/description,
        1024 for body) is annotated ``False`` and records exactly one
        error.

        Requirements: 3.4, 4.4, 5.4, 15.3
        """
        text = "a" * (max_length + 1)

        link_data, current_ad_errors = self._run_text_field_validation(
            use_case_factory, field_name, link_data_key, annotation_key, [text]
        )

        assert link_data[annotation_key] is False
        assert len(current_ad_errors) == 1

    # Explicit example (Requirement 15.4): candidate count == 0.
    @pytest.mark.parametrize(
        "field_name, link_data_key, annotation_key, max_length",
        _FIELD_PARAMS,
        ids=_FIELD_IDS,
    )
    def test_zero_candidates_example_marks_invalid_without_calling_is_valid_length(
        self, use_case_factory, field_name, link_data_key, annotation_key, max_length
    ):
        """Explicit example: a raw value producing exactly 0 candidates
        (``None``, per ``_standard_candidate_values``'s falsy-scalar
        branch) is annotated ``False``, records exactly one error, and
        never invokes ``MetaAdsValidator.is_valid_length``.

        Requirements: 3.2, 4.2, 5.2, 15.4
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length:
            link_data, current_ad_errors = self._run_text_field_validation(
                use_case_factory, field_name, link_data_key, annotation_key, None
            )

        assert link_data[annotation_key] is False
        assert len(current_ad_errors) == 1
        mock_is_valid_length.assert_not_called()

    # Explicit example (Requirement 15.4): candidate count >= 2.
    @pytest.mark.parametrize(
        "field_name, link_data_key, annotation_key, max_length",
        _FIELD_PARAMS,
        ids=_FIELD_IDS,
    )
    def test_two_or_more_candidates_example_marks_invalid_without_calling_is_valid_length(
        self, use_case_factory, field_name, link_data_key, annotation_key, max_length
    ):
        """Explicit example: a raw value that is already a list of 2
        elements (``_standard_candidate_values`` returns it as-is, per its
        ``isinstance(value, list)`` branch) is annotated ``False``, records
        exactly one error, and never invokes
        ``MetaAdsValidator.is_valid_length``.

        Requirements: 3.3, 4.3, 5.3, 15.4
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length:
            link_data, current_ad_errors = self._run_text_field_validation(
                use_case_factory,
                field_name,
                link_data_key,
                annotation_key,
                ["Valor A", "Valor B"],
            )

        assert link_data[annotation_key] is False
        assert len(current_ad_errors) == 1
        mock_is_valid_length.assert_not_called()


class TestStandardImageValidation:
    """Requirement 6: imagen (Imagen_STANDARD) validation, driven directly
    through ``_validate_standard_image``::

        def _validate_standard_image(self, link_data, current_ad_errors):
            candidates = self._standard_candidate_values(link_data.get('image_url'))
            if len(candidates) != 1:
                link_data['image_valid'] = False
                current_ad_errors.append({...})
                return
            images = [{'url': candidates[0]}]
            MetaAdsValidator.validate_images_precheck(images)
            valid = images[0].get('valid', False)
            error = images[0].get('error')
            link_data['image_valid'] = valid
            link_data['image_error'] = error
            if not valid:
                current_ad_errors.append({...})

    Per the design decision recorded in ``design.md`` (see
    ``TestStandardTextFieldValidation`` above), every test here calls
    ``_validate_standard_image`` directly on a use case instance built via
    ``use_case_factory``, instead of driving a full ``execute()``.

    ``MetaAdsValidator.validate_images_precheck`` (real implementation in
    ``facebook_validator_service.py``) mutates each dict of the ``images``
    list it receives in place, setting ``valid``/``error`` keys on it, and
    returns ``None`` -- it has no return value the caller reads. Every test
    below that patches it therefore uses a ``side_effect`` that mutates the
    passed-in list in place, mirroring that exact contract, rather than
    setting ``return_value`` (which the real collaborator's callers never
    read).

    Feature: meta-ads-standard-precheck-validation, Property 2: conteo de
    candidatos distinto de 1 produce error controlado sin excepción -- para
    todo valor candidato cuya longitud de Valor_Candidato (según
    ``_standard_candidate_values``) sea distinta de 1, la validación de
    imagen SHALL anotar ``image_valid`` como ``False``, SHALL agregar
    exactamente un error a ``current_ad_errors``, y SHALL NOT invocar
    ``MetaAdsValidator.validate_images_precheck``, ni lanzar ninguna
    excepción no controlada.

    Feature: meta-ads-standard-precheck-validation, Property 4: espejo
    (mirroring) del resultado de un colaborador externo hacia la anotación
    y los errores -- para todo valor booleano ``resultado`` devuelto
    (simulado mediante un doble de prueba) por
    ``MetaAdsValidator.validate_images_precheck`` (vía el campo ``valid``
    de la imagen sintética), cuando la validación sí se invoca (imagen con
    exactamente 1 candidato), la anotación ``image_valid`` SHALL ser
    exactamente igual a ``resultado``, y SHALL agregarse un error a
    ``current_ad_errors`` si y solo si ``resultado`` es ``False``.

    Validates: Properties 2, 4 -- Requirements 6.1-6.7, 15.4, 15.12
    """

    @staticmethod
    def _run_image_validation(use_case_factory, image_url):
        """Build a STANDARD use case and drive ``_validate_standard_image``
        directly, mirroring exactly how ``_validate_standard_creative``
        itself invokes it.

        A brand new ``link_data``/``current_ad_errors`` list is built on
        every call (via ``make_link_data``, reused unmodified); nothing is
        shared across invocations. Returns ``(link_data, current_ad_errors)``
        so callers can inspect both the mutated ``link_data`` dict and the
        accumulated errors.

        Requirements: 6.1-6.7
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        link_data = make_link_data(image_url=image_url)
        current_ad_errors = []

        use_case._validate_standard_image(link_data, current_ad_errors)

        return link_data, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 2 (rama
    # imagen): para todo valor candidato cuya longitud de Valor_Candidato
    # sea distinta de 1 (longitud 0, o cualquier lista de longitud >= 2),
    # la validación de imagen SHALL anotar image_valid como False, SHALL
    # agregar exactamente un error a current_ad_errors, y SHALL NOT invocar
    # MetaAdsValidator.validate_images_precheck.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(image_url=standard_candidate_values_with_wrong_count())
    def test_property_candidate_count_not_one_short_circuits_without_calling_validate_images_precheck(
        self, use_case_factory, image_url
    ):
        """For any raw ``image_url`` whose ``_standard_candidate_values``
        yields a candidate count different from 1 (0, or 2+), ``image_valid``
        is annotated ``False`` and exactly one ``image-error`` is recorded,
        without ``MetaAdsValidator.validate_images_precheck`` ever being
        invoked -- the count-mismatch branch returns before reaching it.

        ``link_data.get('image_error')`` (the auxiliary, non-boolean field)
        is also asserted absent: per ``design.md``'s annotation contract
        table, ``image_error`` is only assigned in the branch that actually
        calls ``validate_images_precheck``, which this short-circuit branch
        never reaches.

        Validates: Property 2 -- Requirements 6.2, 6.3
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
            link_data, current_ad_errors = self._run_image_validation(
                use_case_factory, image_url
            )

        assert link_data["image_valid"] is False
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "image-error"
        mock_validate_images_precheck.assert_not_called()
        assert "image_error" not in link_data

    # Feature: meta-ads-standard-precheck-validation, Property 4 (rama
    # imagen): para todo valor booleano resultado devuelto (simulado) por
    # validate_images_precheck vía el campo valid de la imagen sintética,
    # cuando la validación sí se invoca (imagen con exactamente 1
    # candidato), image_valid SHALL ser exactamente igual a resultado,
    # image_error SHALL ser exactamente igual al error simulado, y SHALL
    # agregarse un error a current_ad_errors si y solo si resultado es
    # False.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        valid=st.booleans(),
        error=st.one_of(st.none(), st.text()),
    )
    def test_property_annotation_mirrors_validate_images_precheck_result(
        self, use_case_factory, valid, error
    ):
        """For any ``valid``/``error`` pair reported by (a test double
        standing in for) ``MetaAdsValidator.validate_images_precheck`` on
        the single-element synthetic ``images`` list, ``image_valid``
        mirrors ``valid`` exactly, ``image_error`` mirrors ``error``
        exactly, and an error is recorded in ``current_ad_errors`` if and
        only if ``valid`` is ``False``.

        The patched ``side_effect`` mutates the ``images`` list it
        receives in place (setting ``valid``/``error`` on
        ``images[0]``), mirroring the real collaborator's contract (which
        mutates in place and returns ``None``), rather than relying on a
        ``return_value`` the real caller never reads.

        Validates: Property 4 -- Requirements 6.1, 6.4, 6.5, 6.6, 6.7
        """

        def _mutate_images_in_place(images):
            images[0]["valid"] = valid
            images[0]["error"] = error

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            side_effect=_mutate_images_in_place,
        ) as mock_validate_images_precheck:
            link_data, current_ad_errors = self._run_image_validation(
                use_case_factory, "https://example.com/imagen.jpg"
            )

        mock_validate_images_precheck.assert_called_once()
        assert link_data["image_valid"] == valid
        assert link_data["image_error"] == error
        if valid:
            assert current_ad_errors == []
        else:
            assert len(current_ad_errors) == 1
            assert current_ad_errors[0]["slug"] == "image-error"

    # Explicit example (Requirement 15.12): exactly one valid candidate,
    # marked invalid by validate_images_precheck with a specific error
    # message -- distinguishable from the count != 1 error, since Requirement
    # 6's design.md annotation contract states image_error is only present
    # when validate_images_precheck was actually invoked (i.e. count == 1).
    def test_image_marked_invalid_by_validate_images_precheck_is_distinguishable_from_count_error(
        self, use_case_factory
    ):
        """Explicit example: exactly one candidate ``image_url``, marked
        ``valid=False`` with a specific ``error`` message by (a double
        standing in for) ``MetaAdsValidator.validate_images_precheck``.

        This failure mode is asserted to be observably distinct from the
        count != 1 scenario in two ways that matter precisely because
        ``design.md``'s annotation contract documents ``image_error`` as
        "solo presente cuando ``validate_images_precheck`` fue invocado":

        1. ``validate_images_precheck`` WAS called here (unlike the
           count != 1 scenario, where it is asserted ``not_called``).
        2. The exact ``image_error`` message is present here (``link_data``
           has the key with the specific message), whereas the count != 1
           scenario never sets ``image_error`` on ``link_data`` at all.

        Requirements: 6.4, 6.5, 15.12
        """
        specific_error_message = "some specific message"

        def _mark_invalid(images):
            images[0]["valid"] = False
            images[0]["error"] = specific_error_message

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            side_effect=_mark_invalid,
        ) as mock_validate_images_precheck:
            link_data, current_ad_errors = self._run_image_validation(
                use_case_factory, "https://example.com/imagen.jpg"
            )

        assert link_data["image_valid"] is False
        assert link_data["image_error"] == specific_error_message
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "image-error"

        # Distinction #1: unlike the count != 1 scenario, the collaborator
        # was actually invoked here.
        mock_validate_images_precheck.assert_called_once()

        # Distinction #2: re-run the count != 1 scenario (image_url=None,
        # 0 candidates) to confirm image_error is absent there, proving the
        # two failure modes are observably different from one another --
        # not just both "image_valid is False".
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck_count_branch:
            count_link_data, count_current_ad_errors = self._run_image_validation(
                use_case_factory, None
            )

        assert count_link_data["image_valid"] is False
        assert "image_error" not in count_link_data
        assert len(count_current_ad_errors) == 1
        mock_validate_images_precheck_count_branch.assert_not_called()


class TestStandardUrlValidation:
    """Requirement 7: URL de destino (URL_STANDARD) validation, driven
    directly through ``_validate_standard_url``::

        def _validate_standard_url(self, link_data, current_ad_errors):
            url = link_data.get('link')
            if not url:
                current_ad_errors.append({...})
                return
            valid = MetaAdsValidator.is_valid_link_url(url)
            link_data['link_url_valid'] = valid
            if not valid:
                current_ad_errors.append({...})

    Per the design decision recorded in ``design.md`` (see
    ``TestStandardImageValidation`` above), every test here calls
    ``_validate_standard_url`` directly on a use case instance built via
    ``use_case_factory``, instead of driving a full ``execute()``.

    Unlike ``title_valid``/``body_valid``/``description_valid``/
    ``image_valid`` (which the design's annotation contract table
    documents as always assigned, success or failure), ``link_url_valid``
    is the documented exception for URL (Requirement 7.3): when ``url`` is
    absent/falsy, ``link_url_valid`` is left entirely unassigned on
    ``link_data`` -- there's no "ausente" boolean state for this field, only
    the "ausente" branch is not evaluated (``is_valid_link_url`` is never
    invoked), avoiding the ``AttributeError`` that
    ``is_valid_link_url(None)`` would otherwise raise.

    Feature: meta-ads-standard-precheck-validation, Property 4: espejo
    (mirroring) del resultado de un colaborador externo hacia la anotación
    y los errores -- para todo valor booleano ``resultado`` devuelto
    (simulado mediante un doble de prueba) por
    ``MetaAdsValidator.is_valid_link_url``, cuando la validación
    correspondiente sí se invoca (URL truthy), la anotación
    ``link_url_valid`` SHALL ser exactamente igual a ``resultado``, y SHALL
    agregarse un error a ``current_ad_errors`` si y solo si ``resultado``
    es ``False``.

    Validates: Property 4 -- Requirements 7.1-7.4, 15.5
    """

    @staticmethod
    def _run_url_validation(use_case_factory, **link_data_overrides):
        """Build a STANDARD use case and drive ``_validate_standard_url``
        directly, mirroring exactly how ``_validate_standard_creative``
        itself invokes it.

        A brand new ``link_data``/``current_ad_errors`` list is built on
        every call (via ``make_link_data``, reused unmodified); nothing is
        shared across invocations. Returns ``(link_data, current_ad_errors)``
        so callers can inspect both the mutated ``link_data`` dict and the
        accumulated errors.

        Requirements: 7.1-7.4
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        link_data = make_link_data(**link_data_overrides)
        current_ad_errors = []

        use_case._validate_standard_url(link_data, current_ad_errors)

        return link_data, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 4 (rama URL):
    # para todo valor booleano resultado devuelto (simulado) por
    # is_valid_link_url, cuando la validación sí se invoca (URL truthy),
    # link_url_valid SHALL ser exactamente igual a resultado, y SHALL
    # agregarse un error a current_ad_errors si y solo si resultado es
    # False.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        url=arbitrary_text().filter(bool),
        valid=st.booleans(),
    )
    def test_property_annotation_mirrors_is_valid_link_url_result(
        self, use_case_factory, url, valid
    ):
        """For any truthy ``url`` and any boolean ``valid`` reported by (a
        test double standing in for) ``MetaAdsValidator.is_valid_link_url``,
        ``link_url_valid`` mirrors ``valid`` exactly, and an error is
        recorded in ``current_ad_errors`` if and only if ``valid`` is
        ``False``.

        Validates: Property 4 -- Requirements 7.1, 7.2, 7.4
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=valid,
        ) as mock_is_valid_link_url:
            link_data, current_ad_errors = self._run_url_validation(
                use_case_factory, link=url
            )

        mock_is_valid_link_url.assert_called_once_with(url)
        assert link_data["link_url_valid"] == valid
        if valid:
            assert current_ad_errors == []
        else:
            assert len(current_ad_errors) == 1
            assert current_ad_errors[0]["slug"] == "url-error"

    # Explicit example (Requirement 15.5): a concrete truthy URL, marked
    # invalid by is_valid_link_url.
    def test_url_marked_invalid_by_is_valid_link_url(self, use_case_factory):
        """Explicit example: a concrete ``link`` value, marked
        ``valid=False`` by (a double standing in for)
        ``MetaAdsValidator.is_valid_link_url``.

        Requirements: 7.1, 7.2, 15.5
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=False,
        ) as mock_is_valid_link_url:
            link_data, current_ad_errors = self._run_url_validation(
                use_case_factory, link="not-a-valid-url"
            )

        mock_is_valid_link_url.assert_called_once_with("not-a-valid-url")
        assert link_data["link_url_valid"] is False
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "url-error"

    # Explicit example (Requirement 7.3): url absent/falsy -- link_url_valid
    # is left entirely unassigned (not even False), is_valid_link_url is
    # never invoked (avoiding the AttributeError is_valid_link_url(None)
    # would otherwise raise), and exactly one url-error with the "ausente"
    # message is recorded.
    @pytest.mark.parametrize(
        "link_value",
        [None, "", ABSENT],
        ids=["link-none", "link-empty-string", "link-key-absent"],
    )
    def test_url_absent_leaves_link_url_valid_unassigned_and_never_calls_is_valid_link_url(
        self, use_case_factory, link_value
    ):
        """Explicit example: ``link_data['link']`` absent/``None``/empty
        string (per the falsy check ``if not url:``) -- ``link_url_valid``
        is NOT set on ``link_data`` (key absent), exactly one ``url-error``
        is recorded with the "ausente" message, and
        ``MetaAdsValidator.is_valid_link_url`` is never called, confirming
        the falsy-avoidance behaviour that prevents the ``AttributeError``
        ``is_valid_link_url(None)`` would otherwise raise.

        Requirements: 7.3, 7.4, 15.5
        """
        overrides = {} if link_value is ABSENT else {"link": link_value}

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url"
        ) as mock_is_valid_link_url:
            link_data, current_ad_errors = self._run_url_validation(
                use_case_factory, **overrides
            )

        assert "link_url_valid" not in link_data
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "url-error"
        assert "ausente" in current_ad_errors[0]["message"]
        mock_is_valid_link_url.assert_not_called()


class TestStandardDailyBudgetValidation:
    """Requirement 8: presupuesto mínimo diario (Presupuesto_STANDARD)
    validation, driven directly through ``_validate_standard_daily_budget``::

        def _validate_standard_daily_budget(self, ad_set, object_story_spec, min_budget, current_ad_errors):
            object_story_spec['min_daily_budget'] = min_budget
            try:
                object_story_spec['daily_budget_valid'] = (ad_set.get('daily_budget', 0) >= min_budget)
            except TypeError:
                current_ad_errors.append({...})

    Per the design decision recorded in ``design.md`` (see
    ``TestStandardUrlValidation`` above), every test here calls
    ``_validate_standard_daily_budget`` directly on a use case instance
    built via ``use_case_factory``, instead of driving a full ``execute()``.

    ``min_daily_budget`` (the auxiliary, non-boolean field) is assigned
    unconditionally on the line *before* the ``>=`` comparison is attempted,
    so it is present in every scenario below, whether the comparison
    succeeds or raises ``TypeError``. ``daily_budget_valid`` is the
    documented exception to the general "always annotate True/False" rule
    (Requirement 8.2): when ``ad_set.get('daily_budget', 0)`` is not
    comparable with ``min_budget`` via ``>=``, the comparison never
    completes, so ``daily_budget_valid`` is left entirely unassigned on
    ``object_story_spec`` -- not even ``False`` -- and exactly one
    ``daily-budget-error`` is recorded instead.

    A quick sanity check (outside Hypothesis, run once against the real
    Python ``>=`` operator) confirms which values are actually
    non-comparable with a ``float`` via ``>=``: ``None``, strings, lists
    and dicts all raise ``TypeError`` when compared against a ``float``
    with ``>=``, while ``bool`` (a subtype of ``int`` in Python) is fully
    comparable and never raises. The non-comparable strategy below
    therefore excludes booleans explicitly.

    Feature: meta-ads-standard-precheck-validation, Property 6: comparación
    numérica válida vs. tipo no comparable -- *para todo* valor numérico
    (``int``/``float``) de ``ad_set['daily_budget']`` y todo valor numérico
    de ``min_budget``, ``_validate_standard_daily_budget`` SHALL anotar
    ``min_daily_budget = min_budget`` y ``daily_budget_valid`` exactamente
    igual al resultado de ``daily_budget >= min_budget``, sin agregar
    ningún error. *Para todo* valor de ``ad_set['daily_budget']`` que no
    sea comparable con ``min_budget`` mediante ``>=`` (por ejemplo
    ``None``, una cadena, una lista o un diccionario),
    ``_validate_standard_daily_budget`` SHALL anotar igualmente
    ``min_daily_budget = min_budget``, SHALL omitir ``daily_budget_valid``
    del diccionario, SHALL agregar exactamente un error a
    ``current_ad_errors``, y SHALL NOT propagar ninguna excepción fuera de
    ``_validate_standard_daily_budget``.

    Validates: Property 6 -- Requirements 8.1, 8.2, 15.13
    """

    @staticmethod
    def _run_daily_budget_validation(use_case_factory, daily_budget, min_budget):
        """Build a STANDARD use case and drive
        ``_validate_standard_daily_budget`` directly, mirroring exactly how
        ``_validate_standard_creative`` itself invokes it.

        A brand new ``ad_set``/``object_story_spec``/``current_ad_errors``
        list is built on every call (via ``make_ad_set``/
        ``make_object_story_spec``, reused unmodified); nothing is shared
        across invocations. Returns ``(object_story_spec, current_ad_errors)``
        so callers can inspect both the mutated ``object_story_spec`` dict
        and the accumulated errors.

        Requirements: 8.1, 8.2, 8.3
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        ad_set = make_ad_set(daily_budget=daily_budget)
        object_story_spec = make_object_story_spec()
        current_ad_errors = []

        use_case._validate_standard_daily_budget(
            ad_set, object_story_spec, min_budget, current_ad_errors
        )

        return object_story_spec, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 6 (rama
    # numérica comparable): para todo valor numérico de daily_budget y todo
    # valor numérico de min_budget, daily_budget_valid SHALL ser exactamente
    # igual a daily_budget >= min_budget, min_daily_budget SHALL ser
    # exactamente min_budget, y no SHALL agregarse ningún error.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        daily_budget=st.one_of(
            st.integers(min_value=-10_000_000, max_value=10_000_000),
            st.floats(allow_nan=False, allow_infinity=False, width=32),
        ),
        min_budget=st.one_of(
            st.integers(min_value=-10_000_000, max_value=10_000_000),
            st.floats(allow_nan=False, allow_infinity=False, width=32),
        ),
    )
    def test_property_numeric_daily_budget_mirrors_comparison_result(
        self, use_case_factory, daily_budget, min_budget
    ):
        """For any numeric ``daily_budget``/``min_budget`` pair,
        ``daily_budget_valid`` mirrors ``daily_budget >= min_budget``
        exactly, ``min_daily_budget`` equals ``min_budget``, and no error
        is recorded.

        Validates: Property 6 -- Requirements 8.1, 8.3
        """
        object_story_spec, current_ad_errors = self._run_daily_budget_validation(
            use_case_factory, daily_budget, min_budget
        )

        assert object_story_spec["min_daily_budget"] == min_budget
        assert object_story_spec["daily_budget_valid"] == (daily_budget >= min_budget)
        assert current_ad_errors == []

    # Feature: meta-ads-standard-precheck-validation, Property 6 (rama no
    # comparable): para todo valor de daily_budget no comparable con
    # min_budget mediante >= (None, texto, lista o diccionario),
    # min_daily_budget SHALL seguir siendo anotado, daily_budget_valid
    # SHALL quedar ausente, y SHALL agregarse exactamente un
    # daily-budget-error, sin propagar ninguna excepción.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        daily_budget=st.one_of(
            st.none(),
            st.text(),
            st.lists(st.integers(), max_size=5),
            st.dictionaries(st.text(), st.integers(), max_size=3),
        ),
        min_budget=st.one_of(
            st.integers(min_value=-10_000_000, max_value=10_000_000),
            st.floats(allow_nan=False, allow_infinity=False, width=32),
        ),
    )
    def test_property_non_comparable_daily_budget_leaves_daily_budget_valid_unassigned(
        self, use_case_factory, daily_budget, min_budget
    ):
        """For any ``daily_budget`` value that is not comparable with
        ``min_budget`` via ``>=`` (``None``, text, a list or a dict),
        ``min_daily_budget`` is still annotated, ``daily_budget_valid`` is
        left entirely unassigned, exactly one ``daily-budget-error`` is
        recorded, and no exception propagates out of
        ``_validate_standard_daily_budget``.

        Validates: Property 6 -- Requirements 8.1, 8.2
        """
        object_story_spec, current_ad_errors = self._run_daily_budget_validation(
            use_case_factory, daily_budget, min_budget
        )

        assert object_story_spec["min_daily_budget"] == min_budget
        assert "daily_budget_valid" not in object_story_spec
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "daily-budget-error"

    # Explicit example (Requirement 15.13): daily_budget=None, the concrete
    # scenario the design/requirements documents call out by name.
    def test_daily_budget_none_leaves_daily_budget_valid_unassigned(
        self, use_case_factory
    ):
        """Explicit example: ``ad_set['daily_budget'] = None`` (the key is
        explicitly present with value ``None``, not absent -- per
        ``design.md``, ``.get('daily_budget', 0)``'s default of ``0`` only
        applies when the key is absent entirely; an explicit ``None``
        value is returned as-is). ``None >= <numeric min_budget>`` raises
        ``TypeError``, so ``min_daily_budget`` is still annotated,
        ``daily_budget_valid`` is left unassigned, and exactly one
        ``daily-budget-error`` is recorded.

        Requirements: 8.1, 8.2, 15.13
        """
        object_story_spec, current_ad_errors = self._run_daily_budget_validation(
            use_case_factory, None, 100
        )

        assert object_story_spec["min_daily_budget"] == 100
        assert "daily_budget_valid" not in object_story_spec
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "daily-budget-error"


class TestStandardCtaValidation:
    """Requirement 9: llamado a la acción (CTA_STANDARD) validation, driven
    directly through ``_validate_standard_cta``::

        def _validate_standard_cta(self, link_data, current_ad_errors):
            cta = link_data.get('call_to_action')
            if not cta:
                return  # Requirement 9.3: se omite sin error y sin anotación.
            if not isinstance(cta, dict):
                current_ad_errors.append({...})
                return  # Requirement 9.4
            cta_type = cta.get('type')
            if not isinstance(cta_type, dict):
                cta_text = cta_type
                cta['type'] = {'value': cta_text, 'valid': False}
                valid = False  # Req 15.3: validator not invoked
            else:
                cta_text = cta_type.get('value')
                valid = MetaAdsValidator.validate_cta_for_goal(
                    cta_text=cta_text, objective=self.objective, goal=self.optimization_goal, throw=False,
                )
                cta_type['valid'] = valid  # Req 15.1
            cta['valid'] = valid  # Req 15.2: same boolean at the root
            if not valid:
                current_ad_errors.append({...})

    Per the design decision recorded in ``design.md`` (see
    ``TestStandardDailyBudgetValidation`` above), every test here calls
    ``_validate_standard_cta`` directly on a use case instance built via
    ``use_case_factory``, instead of driving a full ``execute()``.

    The CTA text is read from the canonical NESTED shape
    ``{'type': {'value': <str>, 'valid': <bool>}}`` -- the one written by
    ``FacebookSavePreCheckCTAsUseCase._validate_ctas_standard`` -- via
    ``cta.get('type', {}).get('value')``. Every test here that reaches the
    ``validate_cta_for_goal`` call therefore builds its ``call_to_action``
    with the module-level helper ``make_standard_cta``; a flat
    ``{'type': <str>}`` would blow up with
    ``AttributeError: 'str' object has no attribute 'get'``.

    Unlike the other STANDARD validations, the ``valid`` annotation is
    written on the ``call_to_action`` dict itself (nested inside
    ``link_data``), not on ``link_data`` directly: the same boolean goes
    both to ``cta['type']['valid']`` (overwriting any value the CTAs
    pre-check may have left there) and to the ROOT ``cta['valid']``
    (Requirement 15 of meta-ads-leads-offsite-conversions). The tests here
    assert on the root annotation, which keeps being written. There are two documented
    exceptions to the general "always annotate True/False" rule
    (Requirement 10.4): CTA absent/falsy (Requirement 9.3, no annotation at
    all -- there's no ``call_to_action`` dict to mutate) and CTA truthy but
    not a ``dict`` (Requirement 9.4, no valid location to write ``valid``
    on, e.g. a string or a list).

    Feature: meta-ads-standard-precheck-validation, Property 4: espejo
    (mirroring) del resultado de un colaborador externo hacia la anotación
    y los errores -- para todo valor booleano ``resultado`` devuelto
    (simulado mediante un doble de prueba) por
    ``MetaAdsValidator.validate_cta_for_goal``, cuando la validación
    correspondiente sí se invoca (CTA truthy y ``dict``), la anotación
    ``call_to_action['valid']`` SHALL ser exactamente igual a ``resultado``,
    y SHALL agregarse un error a ``current_ad_errors`` si y solo si
    ``resultado`` es ``False``. Adicionalmente, para todo valor de CTA
    ausente/falsy, ``validate_cta_for_goal`` SHALL NOT ser invocado y no
    SHALL agregarse ningún error; y para todo valor de CTA truthy que no
    sea un ``dict``, ``validate_cta_for_goal`` SHALL NOT ser invocado y
    SHALL agregarse exactamente un error.

    Validates: Property 4 -- Requirements 9.1-9.5, 15.11
    """

    @staticmethod
    def _run_cta_validation(use_case_factory, **link_data_overrides):
        """Build a STANDARD use case and drive ``_validate_standard_cta``
        directly, mirroring exactly how ``_validate_standard_creative``
        itself invokes it.

        A brand new ``link_data``/``current_ad_errors`` list is built on
        every call (via ``make_link_data``, reused unmodified); nothing is
        shared across invocations. Returns ``(link_data, current_ad_errors)``
        so callers can inspect both the mutated ``link_data`` dict (and,
        through it, its own ``call_to_action`` dict when present) and the
        accumulated errors.

        Requirements: 9.1-9.5
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        link_data = make_link_data(**link_data_overrides)
        current_ad_errors = []

        use_case._validate_standard_cta(link_data, current_ad_errors)

        return use_case, link_data, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 4 (rama CTA):
    # para todo valor booleano resultado devuelto (simulado) por
    # validate_cta_for_goal, cuando la validación sí se invoca (CTA truthy
    # y dict), call_to_action['valid'] SHALL ser exactamente igual a
    # resultado, y SHALL agregarse un error a current_ad_errors si y solo
    # si resultado es False.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        cta_text=st.text(min_size=1),
        valid=st.booleans(),
    )
    def test_property_annotation_mirrors_validate_cta_for_goal_result(
        self, use_case_factory, cta_text, valid
    ):
        """For any non-empty ``cta_text`` and any boolean ``valid`` reported
        by (a test double standing in for)
        ``MetaAdsValidator.validate_cta_for_goal``, ``call_to_action['valid']``
        mirrors ``valid`` exactly (mutated on the CTA dict itself, per the
        design's annotation contract), an error is recorded in
        ``current_ad_errors`` if and only if ``valid`` is ``False``, and
        ``validate_cta_for_goal`` was called with the exact keyword
        arguments dictated by the design.

        Validates: Property 4 -- Requirements 9.1, 9.2, 9.5
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal",
            return_value=valid,
        ) as mock_validate_cta_for_goal:
            use_case, link_data, current_ad_errors = self._run_cta_validation(
                use_case_factory, call_to_action=make_standard_cta(cta_text)
            )

        mock_validate_cta_for_goal.assert_called_once_with(
            cta_text=cta_text,
            objective=use_case.objective,
            goal=use_case.optimization_goal,
            throw=False,
        )
        assert link_data["call_to_action"]["valid"] == valid
        if valid:
            assert current_ad_errors == []
        else:
            assert len(current_ad_errors) == 1
            assert current_ad_errors[0]["slug"] == "cta-error"

    # Explicit scenario 1/3 (Requirement 15.11): a concrete, valid CTA.
    def test_cta_valid_scenario(self, use_case_factory):
        """Explicit example: a concrete ``call_to_action`` marked
        ``valid=True`` by (a double standing in for)
        ``MetaAdsValidator.validate_cta_for_goal``. ``call_to_action['valid']``
        is ``True`` and no error is recorded.

        Requirements: 9.1, 9.2, 15.11
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal",
            return_value=True,
        ) as mock_validate_cta_for_goal:
            use_case, link_data, current_ad_errors = self._run_cta_validation(
                use_case_factory, call_to_action=make_standard_cta("LEARN_MORE")
            )

        mock_validate_cta_for_goal.assert_called_once_with(
            cta_text="LEARN_MORE",
            objective=use_case.objective,
            goal=use_case.optimization_goal,
            throw=False,
        )
        assert link_data["call_to_action"]["valid"] is True
        assert current_ad_errors == []

    # Explicit scenario 2/3 (Requirement 15.11): a concrete, invalid CTA.
    def test_cta_invalid_scenario(self, use_case_factory):
        """Explicit example: a concrete ``call_to_action`` marked
        ``valid=False`` by (a double standing in for)
        ``MetaAdsValidator.validate_cta_for_goal``. ``call_to_action['valid']``
        is ``False`` and exactly one ``cta-error`` is recorded, without any
        uncontrolled exception being raised.

        Requirements: 9.1, 9.2, 9.5, 15.11
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal",
            return_value=False,
        ) as mock_validate_cta_for_goal:
            use_case, link_data, current_ad_errors = self._run_cta_validation(
                use_case_factory, call_to_action=make_standard_cta("LEARN_MORE")
            )

        mock_validate_cta_for_goal.assert_called_once_with(
            cta_text="LEARN_MORE",
            objective=use_case.objective,
            goal=use_case.optimization_goal,
            throw=False,
        )
        assert link_data["call_to_action"]["valid"] is False
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "cta-error"

    # Explicit scenario 3/3 (Requirement 15.11): CTA absent/falsy -- no
    # annotation whatsoever (no call_to_action dict exists to mutate), no
    # error, and validate_cta_for_goal is never invoked.
    @pytest.mark.parametrize(
        "call_to_action_value",
        [None, {}, False, "", ABSENT],
        ids=[
            "call-to-action-none",
            "call-to-action-empty-dict",
            "call-to-action-false",
            "call-to-action-empty-string",
            "call-to-action-key-absent",
        ],
    )
    def test_cta_absent_scenario(self, use_case_factory, call_to_action_value):
        """Explicit example: ``link_data['call_to_action']`` absent/falsy
        (``None``, an empty dict, ``False``, an empty string, or the key
        missing entirely). ``_validate_standard_cta`` returns early without
        any mutation at all: no ``valid`` key appears anywhere (there is no
        ``call_to_action`` dict to mutate), ``link_data`` itself gains no
        new keys, no error is recorded, and
        ``MetaAdsValidator.validate_cta_for_goal`` is never called.

        Requirements: 9.3, 15.11
        """
        overrides = (
            {}
            if call_to_action_value is ABSENT
            else {"call_to_action": call_to_action_value}
        )

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal"
        ) as mock_validate_cta_for_goal:
            use_case, link_data, current_ad_errors = self._run_cta_validation(
                use_case_factory, **overrides
            )

        keys_before = set(make_link_data(**overrides).keys())
        assert set(link_data.keys()) == keys_before
        if isinstance(call_to_action_value, dict):
            assert "valid" not in link_data["call_to_action"]
        assert current_ad_errors == []
        mock_validate_cta_for_goal.assert_not_called()

    # Explicit example (Requirement 9.4): CTA truthy but not a dict --
    # exactly one cta-error is recorded, validate_cta_for_goal is never
    # called, and no AttributeError/TypeError is raised from attempting
    # .get('type')/['valid'] on a non-dict value.
    @pytest.mark.parametrize(
        "call_to_action_value",
        ["LEARN_MORE", ["LEARN_MORE"], 1, True],
        ids=[
            "call-to-action-string",
            "call-to-action-list",
            "call-to-action-int",
            "call-to-action-bool-true",
        ],
    )
    def test_cta_truthy_non_dict_adds_error_without_crashing(
        self, use_case_factory, call_to_action_value
    ):
        """Explicit example: a truthy, non-``dict`` ``call_to_action``
        value (a string, a list, an int or ``True``). Exactly one
        ``cta-error`` with the "debe ser un diccionario" message is
        recorded, ``MetaAdsValidator.validate_cta_for_goal`` is never
        called, and no ``AttributeError``/``TypeError`` is raised -- which
        would otherwise happen if the implementation attempted
        ``call_to_action.get('type')`` or ``call_to_action['valid'] = ...``
        on a non-dict value such as a string.

        Requirements: 9.4, 15.11
        """
        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta_for_goal"
        ) as mock_validate_cta_for_goal:
            use_case, link_data, current_ad_errors = self._run_cta_validation(
                use_case_factory, call_to_action=call_to_action_value
            )

        assert link_data["call_to_action"] == call_to_action_value
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "cta-error"
        assert "debe ser un diccionario" in current_ad_errors[0]["message"]
        mock_validate_cta_for_goal.assert_not_called()


class TestStandardAnnotationContract:
    """Requirement 10: the combined annotation contract over
    ``object_story_spec``/``link_data``, exercised through
    ``_validate_standard_creative`` as the STANDARD branch's *orchestrator*
    (título → cuerpo → descripción → imagen → URL → presupuesto → CTA, in
    that exact order)::

        def _validate_standard_creative(self, ad_set, object_story_spec, min_budget, current_ad_errors):
            link_data = object_story_spec.get('link_data')
            if link_data is None:
                link_data = {}
                object_story_spec['link_data'] = link_data
            self._validate_standard_text_field(link_data, link_data.get('name'), 'title', 'title_valid', 'title-error', current_ad_errors)
            self._validate_standard_text_field(link_data, link_data.get('message'), 'body', 'body_valid', 'body-error', current_ad_errors)
            self._validate_standard_text_field(link_data, link_data.get('description'), 'description', 'description_valid', 'description-error', current_ad_errors)
            self._validate_standard_image(link_data, current_ad_errors)
            self._validate_standard_url(link_data, current_ad_errors)
            self._validate_standard_daily_budget(ad_set, object_story_spec, min_budget, current_ad_errors)
            self._validate_standard_cta(link_data, current_ad_errors)

    Unlike ``TestStandardTextFieldValidation``/``TestStandardImageValidation``/
    ``TestStandardUrlValidation``/``TestStandardDailyBudgetValidation``/
    ``TestStandardCtaValidation`` above -- each of which calls exactly one
    of the 5 per-field collaborators in isolation, with ``MetaAdsValidator``
    patched method-by-method -- this class drives the *whole* orchestrator
    in a single call, with the entire ``MetaAdsValidator`` class reference
    replaced by a single mock (``patch("app.v2.use_cases.meta_ads.MetaAdsValidator")``,
    not the real length-check implementation), and a single-candidate,
    fully-populated ``link_data``/``ad_set`` so every one of the 7
    sub-validations actually reaches its "evaluated" branch (the
    count-!=-1/absent branches belong to Properties 2-4 above, already
    covered by ``TestStandardTextFieldValidation``/``TestStandardImageValidation``/
    ``TestStandardUrlValidation``/``TestStandardCtaValidation``, and are not
    the focus here).

    The objective is to prove there is no cross-contamination between the
    7 fields when they are driven *together* by the orchestrator: a
    failing título must not affect the cuerpo's own annotation, a failing
    imagen must not affect the URL's own annotation, and so on -- each of
    the 7 annotations SHALL equal exactly its own, independently generated
    boolean result, and ``current_ad_errors`` SHALL contain exactly one
    entry per failing field among título/cuerpo/descripción/imagen/URL/CTA
    (never more, never fewer). Presupuesto is the documented exception
    (Property 6, ``design.md``): when ``daily_budget`` is numerically
    comparable with ``min_budget`` (as it always is here, per
    ``_run_full_standard_validation``'s numeric pair below),
    ``daily_budget_valid`` mirrors the comparison result exactly but SHALL
    NOT add a ``daily-budget-error`` regardless of whether that result is
    ``True`` or ``False`` -- only a non-comparable ``daily_budget`` (a
    case already covered on its own by ``TestStandardDailyBudgetValidation``
    and out of scope here) would add one.

    Feature: meta-ads-standard-precheck-validation, Property 5: contrato de
    tres estados observables sobre las anotaciones -- *para toda*
    combinación de resultado booleano simulado de cada colaborador de
    ``MetaAdsValidator`` relevante, y para todo ``object_story_spec``/
    ``link_data`` arbitrario, invocado ``_validate_standard_creative`` bajo
    una combinación objetivo/optimización ya soportada, cada campo de
    anotación definido en la tabla de contrato de ``design.md`` SHALL
    encontrarse en exactamente uno de tres estados: ausente, presente con
    valor ``True``, o presente con valor ``False``.

    Validates: Property 5 -- Requirements 10.1, 10.2, 10.3, 10.4
    """

    @staticmethod
    def _run_full_standard_validation(
        use_case_factory,
        title_valid,
        body_valid,
        description_valid,
        image_valid,
        url_valid,
        budget_valid,
        cta_valid,
    ):
        """Build a STANDARD use case under a supported objective/optimization
        combination (``OUTCOME_LEADS``/``LEAD_GENERATION``, the same default
        used elsewhere in this suite for the STANDARD branch), fully mock
        the ``MetaAdsValidator`` *class reference* so each of its 4
        collaborators reports the independently-generated boolean result
        dictated by the caller, and drive ``_validate_standard_creative``
        directly with a single-candidate, fully-populated ``link_data``/
        ``ad_set`` so every one of the 7 sub-validations reaches its
        "evaluated" branch.

        ``is_valid_length`` is mocked with a ``side_effect`` that dispatches
        on the ``field_name`` positional argument (``'title'``/``'body'``/
        ``'description'``) so the 3 independent text results are honored
        even though the 3 calls share the same mocked method.
        ``validate_images_precheck`` is mocked with a ``side_effect`` that
        mutates ``images[0]['valid']`` in place, exactly like the real
        implementation does. ``is_valid_link_url``/``validate_cta_for_goal``
        are mocked with a plain ``return_value``, since each is called at
        most once per invocation.

        The daily budget pair is chosen so the *real* (unmocked) ``>=``
        comparison inside ``_validate_standard_daily_budget`` produces
        exactly ``budget_valid`` (``daily_budget=100``/``min_budget=100``
        when ``True``, ``daily_budget=0``/``min_budget=100`` when ``False``)
        -- Property 6 already covers this comparison's own edge cases
        (non-numeric values, etc.) in ``TestStandardDailyBudgetValidation``,
        so here a simple, always-comparable numeric pair suffices.

        A brand new use case/``link_data``/``object_story_spec``/``ad_set``/
        ``current_ad_errors`` list is built on every call; nothing is
        shared across invocations. Returns
        ``(link_data, object_story_spec, current_ad_errors)``.

        Requirements: 10.1, 10.2, 10.3, 10.4
        """
        use_case, _, _ = use_case_factory(
            complete_campaign_data=make_campaign_data_dict(
                objective=CampaignObjective.LEADS.value,
                optimization_goal=LeadsOptimizationGoal.LEAD_GENERATION.value,
            ),
            creative_type="STANDARD",
        )

        def _is_valid_length_side_effect(field_name, text_items):
            result = {
                "title": title_valid,
                "body": body_valid,
                "description": description_valid,
            }[field_name]
            text_items[0]["valid_length"] = result

        def _validate_images_precheck_side_effect(images):
            images[0]["valid"] = image_valid
            if not image_valid:
                images[0]["error"] = "imagen-invalida-simulada"

        link_data = make_link_data(
            name="Título",
            message="Cuerpo",
            description="Descripción",
            image_url="https://example.com/imagen.jpg",
            link="https://example.com/destino",
            call_to_action=make_standard_cta("LEARN_MORE"),
        )
        object_story_spec = make_object_story_spec(link_data=link_data)
        ad_set = make_ad_set(daily_budget=100 if budget_valid else 0)
        min_budget = 100
        current_ad_errors = []

        with patch("app.v2.use_cases.meta_ads.MetaAdsValidator") as mock_validator:
            mock_validator.is_valid_length.side_effect = _is_valid_length_side_effect
            mock_validator.validate_images_precheck.side_effect = (
                _validate_images_precheck_side_effect
            )
            mock_validator.is_valid_link_url.return_value = url_valid
            mock_validator.validate_cta_for_goal.return_value = cta_valid

            use_case._validate_standard_creative(
                ad_set, object_story_spec, min_budget, current_ad_errors
            )

        return link_data, object_story_spec, current_ad_errors

    # Feature: meta-ads-standard-precheck-validation, Property 5: para toda
    # combinación de resultado booleano independiente por colaborador, cada
    # una de las 7 anotaciones SHALL ser exactamente igual a su propio
    # resultado generado (sin contaminación cruzada entre campos), y
    # current_ad_errors SHALL contener exactamente una entrada por campo
    # fallido.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        title_valid=st.booleans(),
        body_valid=st.booleans(),
        description_valid=st.booleans(),
        image_valid=st.booleans(),
        url_valid=st.booleans(),
        budget_valid=st.booleans(),
        cta_valid=st.booleans(),
    )
    def test_property_combined_annotation_contract_holds_independently_per_field(
        self,
        use_case_factory,
        title_valid,
        body_valid,
        description_valid,
        image_valid,
        url_valid,
        budget_valid,
        cta_valid,
    ):
        """For any combination of 7 independently-generated boolean results
        (one per sub-validation collaborator), each of the 7 annotations
        written by ``_validate_standard_creative`` -- ``title_valid``,
        ``body_valid``, ``description_valid``, ``image_valid`` and
        ``link_url_valid`` on ``link_data``, ``daily_budget_valid`` on
        ``object_story_spec``, and ``call_to_action['valid']`` nested
        inside ``link_data`` -- equals exactly its own, independently
        generated result: no failing field ever contaminates another
        field's own annotation. ``current_ad_errors`` contains exactly one
        entry per ``False`` result among the 6 error-producing fields
        (título/cuerpo/descripción/imagen/URL/CTA -- never more, never
        fewer); presupuesto never contributes an error here since
        ``daily_budget``/``min_budget`` are always numerically comparable
        (Property 6's documented exception, out of scope for this test).

        Validates: Property 5 -- Requirements 10.1, 10.2, 10.3, 10.4
        """
        link_data, object_story_spec, current_ad_errors = (
            self._run_full_standard_validation(
                use_case_factory,
                title_valid,
                body_valid,
                description_valid,
                image_valid,
                url_valid,
                budget_valid,
                cta_valid,
            )
        )

        assert link_data["title_valid"] == title_valid
        assert link_data["body_valid"] == body_valid
        assert link_data["description_valid"] == description_valid
        assert link_data["image_valid"] == image_valid
        assert link_data["link_url_valid"] == url_valid
        assert object_story_spec["daily_budget_valid"] == budget_valid
        assert link_data["call_to_action"]["valid"] == cta_valid

        error_producing_results = [
            title_valid,
            body_valid,
            description_valid,
            image_valid,
            url_valid,
            cta_valid,
        ]
        expected_error_count = sum(1 for result in error_producing_results if not result)
        assert len(current_ad_errors) == expected_error_count


class TestStandardCreativesEntry:
    """Requirement 12: construction of a ``creatives[]`` entry for a
    STANDARD ad, driven directly through ``_build_standard_creative_entry``::

        def _build_standard_creative_entry(self, idx, ad_set_to_publish, ad):
            ad_creative = ad.get('adCreative') or {}
            object_story_spec = ad_creative.get('object_story_spec') or {}
            link_data = object_story_spec.get('link_data') or {}
            call_to_action = link_data.get('call_to_action') or {}

            image_url = link_data.get('image_url')
            images = [{
                'url': image_url,
                'valid': link_data.get('image_valid', False),
                'error': link_data.get('image_error'),
            }] if image_url else []

            def _as_single_item_list(value, valid_length):
                return [{'text': value, 'valid_length': valid_length}] if value else []

            title_valid = link_data.get('title_valid', False)
            body_valid = link_data.get('body_valid', False)
            description_valid = link_data.get('description_valid', False)

            return {
                'idx': idx,
                'name': f"{ad_set_to_publish.get('name')} - {ad.get('name')}",
                ... (32 keys total, see EXPECTED_KEYS below)
            }

    The third argument is the full *ad* dict, not its ``adCreative``: the
    method descends into ``ad.get('adCreative') or {}`` by itself, and it
    also reads ``ad.get('name')``/``ad.get('id')`` straight off that same
    dict, so ``name`` is the composition of the ad set's name and the ad's
    name.

    Every test here calls ``_build_standard_creative_entry`` directly on a
    use case instance built via ``use_case_factory``, mirroring exactly how
    ``execute()``'s ``creatives[]``-construction loop invokes it (Requirement
    12.2's dispatch), rather than driving a full ``execute()``.

    Feature: meta-ads-standard-precheck-validation, Property 8: construcción
    total (sin excepciones) de ``CreativeToPublish`` para STANDARD -- para
    todo ``object_story_spec`` generado aleatoriamente con cualquier
    subconjunto (incluyendo el conjunto vacío o ``None``) de sus claves
    esperadas, ``_build_standard_creative_entry`` SHALL retornar un
    diccionario que contiene exactamente el mismo conjunto fijo de claves
    que produce ``_build_dynamic_creative_entry``, nunca lanzando una
    excepción, y usando los defaults documentados para toda clave ausente.

    Validates: Property 8 -- Requirements 12.2, 12.3, 12.4, 15.7
    """

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
            "promoted_object_valid",
        }
    )
    """The fixed set of keys ``_build_standard_creative_entry`` SHALL
    always return, mirroring exactly ``design.md``'s mapping table (the
    same fixed set already produced by ``_build_dynamic_creative_entry``,
    per Requirement 12.2).

    Requirements: 12.2
    """

    @staticmethod
    def _make_ad_set_to_publish(object_story_spec=ABSENT, ad_id="ad-1", **ad_set_overrides):
        """Build a minimal but valid ``ad_set_to_publish`` dict: a single
        ad (with the given ``ad_id``) carrying an ``adCreative`` whose
        ``object_story_spec`` is the given value (``ABSENT`` by default, so
        the key is omitted entirely from ``adCreative``, matching the
        ``ad_creative.get('object_story_spec')`` absent-key scenario).

        ``make_ad_set``/``make_ad``/``make_ad_creative`` are reused
        unmodified (per ``design.md``'s "Builders reutilizados sin
        cambios" section); none of their DYNAMIC-shaped defaults
        (``asset_feed_spec``) leak in here since ``make_ad_creative``
        defaults that kwarg to the ``ABSENT`` sentinel too.

        Requirements: 12.2, 12.3
        """
        ad_creative = make_ad_creative(object_story_spec=object_story_spec)
        ad = make_ad(ad_creative=ad_creative, id=ad_id)
        return make_ad_set(ads=[ad], **ad_set_overrides)

    # Feature: meta-ads-standard-precheck-validation, Property 8: para todo
    # object_story_spec generado aleatoriamente con cualquier subconjunto de
    # sus claves esperadas (incluyendo el conjunto vacío o None),
    # _build_standard_creative_entry SHALL retornar un diccionario con
    # exactamente el mismo conjunto fijo de claves, nunca lanzando una
    # excepción.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(object_story_spec=standard_object_story_spec_shapes(), idx=st.integers(min_value=0, max_value=1000))
    def test_property_construction_never_raises_and_always_returns_the_fixed_key_set(
        self, use_case_factory, object_story_spec, idx
    ):
        """For any ``object_story_spec`` shape -- entirely absent from
        ``adCreative``, present as ``None``, present with ``link_data``
        absent/``None``/empty/partially populated/fully populated, and any
        random partial subset of the top-level ``object_story_spec``
        fields -- calling ``_build_standard_creative_entry`` raises no
        exception, always returns a dict containing exactly
        ``EXPECTED_KEYS`` (no more, no fewer), and always echoes back the
        given ``idx`` verbatim under the ``idx`` key.

        The third argument is the whole ``ad`` dict, matching the real
        signature ``(self, idx, ad_set_to_publish, ad)``: the method
        performs the descent itself with ``ad.get('adCreative') or {}``.
        Passing the already-extracted ``adCreative`` instead would make
        that descent yield ``{}`` for every generated example, degenerating
        the whole result to its documented defaults and leaving this
        property vacuous -- the generated ``object_story_spec`` shapes
        would never be reached. Passing ``ad`` is what makes the generated
        shapes genuinely flow through the production code path.

        Validates: Property 8 -- Requirements 12.2, 12.3, 12.4
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        ad_set_to_publish = self._make_ad_set_to_publish(object_story_spec=object_story_spec)
        ad = ad_set_to_publish["ads"][0]

        result = use_case._build_standard_creative_entry(idx, ad_set_to_publish, ad)

        assert isinstance(result, dict)
        assert set(result.keys()) == self.EXPECTED_KEYS
        assert result["idx"] == idx

    # Explicit example (Requirement 15.7): object_story_spec completely
    # absent from adCreative -- every documented default applies at once.
    def test_object_story_spec_completely_absent_uses_every_documented_default(
        self, use_case_factory
    ):
        """Explicit example (Requirement 15.7): when ``adCreative`` has no
        ``object_story_spec`` key at all, ``_build_standard_creative_entry``
        raises no exception and returns the full dict of documented
        defaults for every field that would otherwise be extracted from
        ``object_story_spec``/``link_data``: empty collections for
        ``images``/``bodies``/``titles``/``descriptions``/
        ``call_to_action_types``/``proposal_locations``/``locations``,
        ``False`` for every ``*_valid_amount``/``unique_*``/
        ``daily_budget_valid``/``proposal_url_valid``/``locations_valid``/
        ``promoted_object_valid`` flag, ``0`` for ``adchannel_id`` and every
        ``*_max_amount``/``min_daily_budget``, and ``''`` for
        ``proposal_url``. ``adset_id``/``daily_budget`` come from
        ``ad_set_to_publish`` (not from ``object_story_spec``), ``ad_id``
        from its single ad, and ``name`` from *both*: it is the composition
        ``f"{ad_set_to_publish.get('name')} - {ad.get('name')}"``, so the
        ad set's ``"AdSet-Absent-OSS"`` carries the ``" - Ad"`` suffix of
        ``make_ad``'s default ad name. Those four are asserted against the
        concrete values built by ``_make_ad_set_to_publish`` instead of a
        "default".

        Requirements: 12.2, 12.3, 15.7
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        ad_set_to_publish = self._make_ad_set_to_publish(
            object_story_spec=ABSENT,
            ad_id="ad-absent-oss",
            name="AdSet-Absent-OSS",
            id="adset-absent-oss",
            daily_budget=250,
        )
        ad = ad_set_to_publish["ads"][0]
        assert "object_story_spec" not in ad["adCreative"]

        result = use_case._build_standard_creative_entry(0, ad_set_to_publish, ad)

        assert result == {
            "idx": 0,
            "name": "AdSet-Absent-OSS - Ad",
            "adset_id": "adset-absent-oss",
            "ad_id": "ad-absent-oss",
            "adchannel_id": 0,
            "daily_budget": 250,
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
            "images_max_amount": 1,
            "titles_max_amount": 1,
            "bodies_max_amount": 1,
            "descriptions_max_amount": 1,
            "call_to_action_types_max_amount": 1,
            "unique_titles": False,
            "unique_bodies": False,
            "unique_descriptions": False,
            "daily_budget_valid": False,
            "min_daily_budget": 0,
            "proposal_url": "",
            "proposal_url_valid": False,
            "proposal_locations": [],
            "locations": [],
            "locations_valid": False,
            "promoted_object_valid": False,
        }


class TestStandardCombinationSuccessScenarios:
    """Requirement 15.2: a full, end-to-end success scenario for each of the
    5 ``STANDARD_SUPPORTED_COMBINATIONS``, driving a complete ``execute()``
    call (not an isolated private method) over a genuinely valid STANDARD
    ``link_data`` built with ``make_standard_link_data_full``, with every
    unrelated guard (``META001``/``META006``/``META007``/``META008``/
    ``META009``) bypassed so the STANDARD validation/creation blocks are
    reached cleanly for every combination.

    Unlike ``TestStandardTextFieldValidation``/``TestStandardImageValidation``/
    etc. (which drive the private ``_validate_standard_*`` methods directly
    against a mocked-or-real ``MetaAdsValidator`` in isolation), this class
    exercises the real, unmocked ``MetaAdsValidator.is_valid_length``/
    ``is_valid_link_url``/``validate_cta_for_goal`` collaborators end to end
    through ``execute()``; only ``MetaAdsValidator.validate_images_precheck``
    is patched, since its real implementation performs a genuine
    ``requests.get`` HTTP call to fetch and inspect the image (forbidden by
    the ``_deny_real_network_requests`` autouse fixture), and it is patched
    with a ``side_effect`` that mutates the passed-in ``images`` list in
    place exactly like the real collaborator does (setting ``valid=True``),
    rather than being handed a fake return value it never actually returns.

    Requirements: 2.1, 10.2, 15.2
    """

    @staticmethod
    def _run_success_scenario(use_case_factory, objective, optimization_goal):
        """Drive a full ``execute()`` call for a single STANDARD ad set/ad
        whose ``object_story_spec``/``link_data`` is a genuinely valid
        creative (via ``make_standard_link_data_full``), under the given
        supported ``objective``/``optimization_goal`` combination, with
        every guard unrelated to the STANDARD validation/creation blocks
        bypassed:

        - ``pixel_id``/``lead_gen_form_id``/``whatsapp_number_id`` are all
          populated on ``complete_campaign_data`` so ``META001``/``META007``/
          ``META008`` never fire regardless of which combination is under
          test.
        - ``_validate_pixel_eligibility``/``_validate_page_whatsapp_eligibility``
          (both real HTTP calls in production) are patched on the instance
          to return ``True``, so ``META006``/``META009`` never fire and no
          network request is attempted.
        - The ``LEADS``/``CONVERSATIONS`` combination requires its
          ``call_to_action`` to be
          ``make_standard_cta("WHATSAPP_MESSAGE", valid=True)`` (the
          only CTA type allowed by ``LEADS_GOAL_ALLOWED_CTAS[CONVERSATIONS]``,
          per ``make_standard_link_data_full``'s documented caveat); every
          other combination uses ``make_standard_link_data_full``'s default
          ``"LEARN_MORE"`` CTA unmodified.
        - ``ad_set``'s ``daily_budget`` (100, ``make_ad_set``'s default) is
          kept comfortably above ``min_budget`` (10, derived from
          ``make_minimum_budget_response``'s default
          ``min_daily_budget_imp=1000`` cents), so the budget validation
          succeeds.
        - ``MetaAdsValidator.validate_images_precheck`` is patched (network
          isolation, see class docstring); every other ``MetaAdsValidator``
          collaborator invoked by the STANDARD branch runs unmocked/real.

        Returns ``(result, status_code, link_data, object_story_spec)``:
        ``result``/``status_code`` are ``execute()``'s return value, and
        ``link_data``/``object_story_spec`` are the exact (mutated in
        place) dicts built for this scenario, so callers can assert on the
        7 success annotations directly.

        Requirements: 2.1, 15.2
        """
        call_to_action = (
            make_standard_cta("WHATSAPP_MESSAGE", valid=True)
            if (objective, optimization_goal)
            == (CampaignObjective.LEADS.value, LeadsOptimizationGoal.CONVERSATIONS.value)
            else ABSENT
        )
        link_data_overrides = (
            {"call_to_action": call_to_action} if call_to_action is not ABSENT else {}
        )
        link_data = make_standard_link_data_full(**link_data_overrides)
        object_story_spec = make_object_story_spec(link_data=link_data)

        campaign_data = make_campaign_data_dict(
            objective=objective,
            optimization_goal=optimization_goal,
            pixel_id="pixel-1",
            lead_gen_form_id="lead-1",
            whatsapp_number_id="whatsapp-1",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="STANDARD"
        )

        ad_creative = make_ad_creative(object_story_spec=object_story_spec)
        ad = make_ad(ad_creative=ad_creative)
        ad_set = make_ad_set(ads=[ad], daily_budget=100)
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        def _mark_images_valid(images):
            for image in images:
                image["valid"] = True
                image["error"] = None

        with patch.object(
            use_case, "_validate_pixel_eligibility", return_value=True
        ), patch.object(
            use_case, "_validate_page_whatsapp_eligibility", return_value=True
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            side_effect=_mark_images_valid,
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, status_code = use_case.execute()

        return result, status_code, link_data, object_story_spec

    # Explicit example (Requirement 15.2): one full success scenario per
    # supported combination, verifying ok=1 and all 7 success annotations
    # present and True simultaneously.
    @pytest.mark.parametrize(
        "objective, optimization_goal",
        STANDARD_SUPPORTED_COMBINATIONS,
        ids=STANDARD_SUPPORTED_COMBINATIONS_IDS,
    )
    def test_full_success_scenario_yields_ok_1_and_all_seven_success_annotations_true(
        self, use_case_factory, objective, optimization_goal
    ):
        """For each of the 5 ``STANDARD_SUPPORTED_COMBINATIONS``, a fully
        valid STANDARD ad (built via ``make_standard_link_data_full``)
        driven through a complete ``execute()`` call yields ``ok=1`` and
        all 7 success annotations (``title_valid``/``body_valid``/
        ``description_valid``/``image_valid``/``link_url_valid`` on
        ``link_data``, ``daily_budget_valid`` on ``object_story_spec``, and
        ``call_to_action['valid']`` on ``link_data['call_to_action']``)
        present and ``True`` simultaneously.

        The emitted creative entry additionally carries
        ``call_to_action_types_valid_amount is True``, which
        ``_build_standard_creative_entry`` reads from
        ``call_to_action['type']['valid']``, written by
        ``_validate_standard_cta`` with the same boolean as the root-level
        annotation (Requirement 15 of meta-ads-leads-offsite-conversions);
        it is ``True`` because ``LEARN_MORE``/``WHATSAPP_MESSAGE`` are
        allowed CTAs for each combination.

        Requirements: 2.1, 10.2, 15.2
        """
        result, status_code, link_data, object_story_spec = (
            self._run_success_scenario(use_case_factory, objective, optimization_goal)
        )

        assert status_code == 200
        assert result["ok"] == 1
        assert link_data["title_valid"] is True
        assert link_data["body_valid"] is True
        assert link_data["description_valid"] is True
        assert link_data["image_valid"] is True
        assert link_data["link_url_valid"] is True
        assert object_story_spec["daily_budget_valid"] is True
        assert link_data["call_to_action"]["valid"] is True
        assert (
            result["data"]["creatives"][0]["call_to_action_types_valid_amount"] is True
        )


class TestExecuteCreationBlock:
    """Requirement 10: the "creation" (dry-run) block of ``execute()``, and
    the direct-to-creation-block path taken by any ``creative_type`` other
    than ``"DYNAMIC"``/``"STANDARD"``::

        if current_ad_errors:
            results.append({"ad_name": ad_name, "status": "Failed", "errors": current_ad_errors})
            continue

        try:
            if self.page_id and ad_creative.get('object_story_spec'):
                ad_creative['object_story_spec']['page_id'] = self.page_id

            payload_asset_feed = asset_feed
            if ad_creative.get('object_story_spec') and ad_creative['object_story_spec'].get('link_data'):
                payload_asset_feed = None

            creative_payload = {
                "name": f"TEST_API_{ad_creative.get('name')}",
                "object_story_spec": ad_creative.get('object_story_spec'),
                "asset_feed_spec": payload_asset_feed,
                "access_token": None
            }
            creative_payload = {k: v for k, v in creative_payload.items() if v is not None}

            results.append({"ad_name": ad_name, "status": "Created"})
        except Exception as e:
            results.append({
                "ad_name": ad_name,
                "status": "Failed",
                "errors": [{'slug': 'execution-error', 'message': f"Execution Error: {str(e)}"}]
            })

    Only ``creative_type in ("DYNAMIC", "STANDARD")`` (combined with a
    truthy ``asset_feed``/``story_spec`` respectively) ever reaches the
    validation blocks covered by Requirements 8/9. Any other
    ``creative_type`` -- including the empty string -- leaves
    ``current_ad_errors`` empty unconditionally for every ad and lands
    directly on this creation block, per Requirement 10.5.

    Per the general note preceding Requirement 10 in ``requirements.md``,
    ``creatives`` is built (after this per-ad loop finishes) by
    unconditionally reading ``ad_sets[i]['ads'][0]``, so a ``Failed`` ad
    that happens to be ``ads[0]`` of its ad set still contributes an entry
    to ``creatives``, built from that failed ad's own
    ``adCreative``/``asset_feed_spec`` -- this is exercised directly below.

    Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
    """

    @staticmethod
    def _run_single_creation_block_ad(
        use_case_factory,
        ad_creative_kwargs=None,
        creative_type="UNRECOGNIZED_TYPE",
        page_id="page-1",
    ):
        """Drive a full ``execute()`` call for a single ad whose
        ``creative_type`` is outside DYNAMIC/STANDARD by default, so
        ``current_ad_errors`` stays empty unconditionally and the ad lands
        directly on the creation block. Returns ``(result, status_code,
        ad_creative)`` so callers can inspect the exact ``adCreative`` dict
        (and, through it, its own ``object_story_spec``) after ``execute()``
        returns -- production code mutates that very same dict object it
        receives through ``MetaAdsPayloadBuilder.build_meta_payload``, never
        a copy.

        Requirements: 10.1, 10.2, 10.3, 10.5, 14.3
        """
        campaign_data = make_campaign_data_dict(page_id=page_id)
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type=creative_type
        )
        ad_creative = make_ad_creative(**(ad_creative_kwargs or {}))
        ad = make_ad(ad_creative=ad_creative)
        ad_set = make_ad_set(ads=[ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result, status_code = use_case.execute()

        return result, status_code, ad_creative

    def test_page_id_mutation_applied_when_page_id_and_object_story_spec_are_truthy(
        self, use_case_factory
    ):
        """When ``self.page_id`` is truthy and ``ad_creative['object_story_spec']``
        is a truthy dict, the creation block mutates that very same dict
        object in place, setting ``object_story_spec['page_id']`` to
        ``self.page_id``. The ad's ``creative_type`` is unrecognized, so no
        DYNAMIC/STANDARD validation runs and ``current_ad_errors`` stays
        empty going into this block.

        Requirements: 10.1
        """
        object_story_spec = make_object_story_spec()

        result, status_code, ad_creative = self._run_single_creation_block_ad(
            use_case_factory,
            ad_creative_kwargs={"object_story_spec": object_story_spec},
            page_id="page-xyz",
        )

        assert status_code == 200
        # Same dict object identity: production code never copies it.
        assert ad_creative["object_story_spec"] is object_story_spec
        assert object_story_spec["page_id"] == "page-xyz"

    @pytest.mark.parametrize(
        "page_id, object_story_spec_absent",
        [(None, False), ("", False), ("page-1", True)],
        ids=[
            "page_id-none",
            "page_id-empty-string",
            "object_story_spec-absent",
        ],
    )
    def test_page_id_mutation_not_attempted_when_page_id_or_object_story_spec_falsy(
        self, use_case_factory, page_id, object_story_spec_absent
    ):
        """When ``self.page_id`` is falsy (``None``/empty string) or
        ``ad_creative['object_story_spec']`` is absent entirely, the ``if
        self.page_id and ad_creative.get('object_story_spec'):`` guard
        short-circuits and no ``page_id`` mutation is attempted. No error
        is appended for that reason either: the ad still completes the
        creation block and the Final Response contains ``ok=1`` for a run
        where this is the only ad, characterizing this as a silent no-op
        rather than a failure.

        Requirements: 10.2
        """
        if object_story_spec_absent:
            ad_creative_kwargs = {}
            object_story_spec = None
        else:
            object_story_spec = make_object_story_spec()
            ad_creative_kwargs = {"object_story_spec": object_story_spec}

        result, status_code, ad_creative = self._run_single_creation_block_ad(
            use_case_factory,
            ad_creative_kwargs=ad_creative_kwargs,
            page_id=page_id,
        )

        assert status_code == 200
        assert result["ok"] == 1
        if object_story_spec_absent:
            assert "object_story_spec" not in ad_creative
        else:
            assert "page_id" not in object_story_spec

    def test_ad_without_validation_errors_completing_creation_block_yields_ok_one(
        self, use_case_factory
    ):
        """When an ad without validation errors (``creative_type`` outside
        DYNAMIC/STANDARD, so ``current_ad_errors`` stays empty
        unconditionally) completes the creation block without raising, the
        Final Response contains ``ok=1`` for a run where this is the only
        ad -- the detailed ``AdResultEntry`` (``{"ad_name": ...,
        "status": "Created"}``, without ``creative_id``/``meta_response``/
        ``errors``) is part of the internal, non-observable ``results``
        list, not of the Final Response.

        Requirements: 10.3
        """
        result, status_code, _ = self._run_single_creation_block_ad(use_case_factory)

        assert status_code == 200
        assert result["ok"] == 1

    def test_object_story_spec_as_string_raises_type_error_inside_creation_block_and_yields_ok_1(
        self, use_case_factory
    ):
        """When ``ad_creative['object_story_spec']`` is a truthy value that
        does not support item assignment (a plain string here), and
        ``self.page_id`` is truthy, ``ad_creative['object_story_spec']['page_id']
        = self.page_id`` raises ``TypeError`` (strings do not support item
        assignment). That exception is caught by the creation block's own
        ``except Exception`` clause (appending an ``execution-error``-slugged
        entry to the internal, non-observable ``results`` list), while the
        Final Response still contains the literal ``ok=1`` -- the conditional
        that consumed ``has_errors`` is commented out, so that entry does not
        influence it. ``adCreative`` itself stays present and truthy
        throughout (only
        its ``object_story_spec`` value is invalid), so Requirement 7.3's
        ``AttributeError`` in the ``creatives``-building loop is not
        triggered here.

        Requirements: 10.4
        """
        result, status_code, ad_creative = self._run_single_creation_block_ad(
            use_case_factory,
            ad_creative_kwargs={"object_story_spec": "not-a-dict"},
            page_id="page-1",
        )

        assert status_code == 200
        assert ad_creative["object_story_spec"] == "not-a-dict"
        assert result["ok"] == 1

    def test_unrecognized_creative_type_skips_dynamic_and_standard_validation_and_reaches_creation_block(
        self, use_case_factory
    ):
        """A ``creative_type`` that is neither ``"DYNAMIC"`` nor
        ``"STANDARD"`` (the empty string here) makes ``execute()`` skip the
        entire ``if self.creative_type == "DYNAMIC" ...`` / ``elif
        self.creative_type == "STANDARD" ...`` block unconditionally,
        regardless of the ad's actual ``asset_feed_spec``/
        ``object_story_spec`` contents -- even when those contents would
        otherwise trigger validation failures under DYNAMIC (duplicated
        titles) or STANDARD (missing ``image_url``). None of
        ``MetaAdsValidator.is_unique_texts``, ``is_valid_length``,
        ``validate_cta``, ``validate_images_precheck``, ``validate_images``,
        ``is_valid_amount``, ``validate_assets_amount`` nor
        ``is_valid_link_url`` is ever invoked, ``current_ad_errors`` stays
        empty, and the ad advances straight to the creation block,
        producing ``ok=1`` for a run where this is the only ad.

        Requirements: 10.5
        """
        asset_feed = make_asset_feed_spec(
            titles=[{"text": "Same"}, {"text": "Same"}],
            call_to_action_types=[{"value": "LEARN_MORE"}],
            images=[{"url": "https://example.com/a.jpg"}],
            link_urls=[{"website_url": "https://example.com/landing"}],
        )
        link_data = make_link_data()  # image_url falsy -> would fail under STANDARD
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed, object_story_spec=story_spec
        )
        ad = make_ad(ad_creative=ad_creative)
        ad_set = make_ad_set(ads=[ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        campaign_data = make_campaign_data_dict(page_id="page-1")
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type=""
        )

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_cta"
        ) as mock_validate_cta, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images"
        ) as mock_validate_images, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount"
        ) as mock_is_valid_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_assets_amount"
        ) as mock_validate_assets_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url"
        ) as mock_is_valid_link_url, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1
        mock_is_unique_texts.assert_not_called()
        mock_is_valid_length.assert_not_called()
        mock_validate_cta.assert_not_called()
        mock_validate_images_precheck.assert_not_called()
        mock_validate_images.assert_not_called()
        mock_is_valid_amount.assert_not_called()
        mock_validate_assets_amount.assert_not_called()
        mock_is_valid_link_url.assert_not_called()

    def test_failed_ad_as_ads_zero_still_contributes_to_creatives_alongside_a_created_ad(
        self, use_case_factory
    ):
        """Per the general note preceding Requirement 10 in
        ``requirements.md``: since ``creatives`` is built by unconditionally
        reading ``ad_sets[i]['ads'][0]``, a ``Failed`` ad that happens to be
        ``ads[0]`` of its ad set still contributes an entry to
        ``creatives`` -- built from that very same failed ad's
        ``adCreative``/``asset_feed_spec`` -- even though it never reached
        the creation block itself. This scenario combines, within a single
        ``ad_set``: ``ads[0]``, a DYNAMIC ad whose title/body/description
        validation is forced to fail (``Failed``, via
        ``MetaAdsValidator.is_unique_texts`` raising for every collection),
        and ``ads[1]``, a second ad whose ``asset_feed_spec`` is an empty
        dict (falsy), which skips the DYNAMIC validation block entirely and
        reaches the creation block untouched, producing ``Created``.
        ``ads[0]``'s ``adCreative``/``asset_feed_spec`` stay present
        (non-falsy) throughout, so Requirement 7.3's ``AttributeError`` is
        never triggered.

        ``execute()`` does not raise, the aggregate ``ok`` is ``0`` (the
        ``Failed`` ad's presence flips it, per Requirement 11.2), and
        ``creatives`` contains exactly one entry for the single ad set,
        documenting that this entry was built from ``ads[0]`` -- the failed
        ad -- rather than being skipped or built from ``ads[1]`` instead.

        Requirements: 10.5
        """
        campaign_data = make_campaign_data_dict()
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )

        failed_asset_feed = make_asset_feed_spec(
            titles=[{"text": "Title"}],
            bodies=[{"text": "Body"}],
            descriptions=[{"text": "Description"}],
        )
        failed_ad_creative = make_ad_creative(
            asset_feed_spec=failed_asset_feed, name="FailedCreative"
        )
        failed_ad = make_ad(name="FailedAd", ad_creative=failed_ad_creative)

        # A falsy (empty) asset_feed_spec skips the whole DYNAMIC validation
        # block (`if self.creative_type == "DYNAMIC" and asset_feed:` is
        # False), so this second ad reaches the creation block untouched.
        created_ad_creative = make_ad_creative(
            asset_feed_spec={}, name="CreatedCreative"
        )
        created_ad = make_ad(name="CreatedAd", ad_creative=created_ad_creative)

        ad_set = make_ad_set(ads=[failed_ad, created_ad])
        meta_payload = make_meta_payload(ad_sets=[ad_set])

        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            side_effect=ValueError("titles are not unique"),
        ) as mock_is_unique_texts:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1
        # is_unique_texts is only invoked for the failed ad's titles/bodies/
        # descriptions try blocks (3 calls); the created ad's falsy
        # asset_feed_spec skips the DYNAMIC validation block entirely, so
        # it never contributes any call.
        assert mock_is_unique_texts.call_count == 3
        creatives = result["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["idx"] == 0


class TestExecuteAggregationAndStatus:
    """Requirement 11: aggregation of every ad's own outcome into the
    internal ``results`` list, plus the ``ok`` field and the HTTP status code
    of the Final Response returned alongside it::

        has_errors = any(item.get('status') == 'Failed' for item in results)
        ...
        return {
            "ok": 1, # if has_errors else 1,
            "data": data # creatives # results
        }, 200

    ``has_errors`` is still computed from ``results``, but the conditional
    that consumed it is commented out, so ``ok`` is the literal ``1`` for
    every run, whatever the mix of ``Created``/``Failed`` entries. What the
    scenarios below exercise is therefore the aggregation itself -- each ad
    contributes its own entry to ``results``, and every ad is reached -- and
    the ``ok``/``status_code`` pair actually returned, not a mapping from
    ``results`` onto ``ok``.

    Every scenario below uses ``creative_type="UNRECOGNIZED_TYPE"`` (outside
    ``DYNAMIC``/``STANDARD``) so each ad's own validation block is skipped
    unconditionally and lands directly on the creation block (Requirement
    10.5), keeping ``Created``/``Failed`` fully controlled by two mechanisms
    that are safe regardless of an ad's position within its ad set:

    - ``Created``: ``adCreative`` present with a plain dict
      ``object_story_spec`` (page_id mutation succeeds, or is skipped when
      ``page_id`` is falsy -- either way no exception is raised).
    - ``Failed``: ``adCreative`` present with ``object_story_spec`` set to a
      non-dict truthy value (a string), so
      ``object_story_spec['page_id'] = self.page_id`` raises ``TypeError``,
      caught by the creation block's own ``except Exception`` and recorded
      as an ``execution-error``-slugged ``Failed`` entry -- without ever
      making ``adCreative`` itself falsy, so Requirement 7.3's
      ``AttributeError`` in the ``creatives``-building loop is never
      triggered, even when this ad is ``ads[0]`` of its ad set.

    Requirements: 11.1, 11.2, 11.3
    """

    @staticmethod
    def _make_created_ad(name):
        """Build an ad whose creation block completes without raising,
        producing a ``Created`` entry in the internal ``results`` list.

        Requirements: 11.1, 11.2, 14.3
        """
        ad_creative = make_ad_creative(
            object_story_spec=make_object_story_spec(), name=f"{name}Creative"
        )
        return make_ad(name=name, ad_creative=ad_creative)

    @staticmethod
    def _make_failed_ad(name):
        """Build an ad whose creation block raises ``TypeError`` (via a
        non-dict ``object_story_spec``), producing a ``Failed`` entry in
        the internal ``results`` list, without ever making ``adCreative``
        itself falsy -- safe even when this ad is ``ads[0]`` of its ad set.

        Requirements: 11.1, 11.2, 14.3
        """
        ad_creative = make_ad_creative(
            object_story_spec="not-a-dict", name=f"{name}Creative"
        )
        return make_ad(name=name, ad_creative=ad_creative)

    @staticmethod
    def _run_multi_ad_set_execute(use_case_factory, ad_sets, page_id="page-1"):
        """Drive a full ``execute()`` call across one or more ad sets, each
        possibly containing multiple ads, with ``creative_type`` outside
        DYNAMIC/STANDARD so every ad lands directly on the creation block.

        Requirements: 11.1, 11.2, 11.3, 14.3
        """
        campaign_data = make_campaign_data_dict(page_id=page_id)
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="UNRECOGNIZED_TYPE"
        )
        meta_payload = make_meta_payload(ad_sets=ad_sets)

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result, status_code = use_case.execute()

        return result, status_code

    def test_all_created_results_yield_ok_one_and_status_200(self, use_case_factory):
        """When every ad across multiple ad sets completes the creation
        block without raising (every ``AdResultEntry.status == "Created"``),
        the Final Response contains ``ok=1`` and the HTTP status code is
        ``200``.

        Requirements: 11.1, 11.3
        """
        ad_set_one = make_ad_set(
            name="AdSetOne",
            ads=[
                self._make_created_ad("AdOne"),
                self._make_created_ad("AdTwo"),
            ],
        )
        ad_set_two = make_ad_set(
            name="AdSetTwo",
            ads=[self._make_created_ad("AdThree")],
        )

        result, status_code = self._run_multi_ad_set_execute(
            use_case_factory, ad_sets=[ad_set_one, ad_set_two]
        )

        assert status_code == 200
        assert result["ok"] == 1

    def test_all_failed_results_yield_ok_1_and_status_200(self, use_case_factory):
        """When every ad across multiple ad sets fails inside the creation
        block (every ``AdResultEntry.status == "Failed"``), the Final
        Response still contains ``ok=1`` -- the conditional that consumed
        ``has_errors`` is commented out -- and the HTTP status code is
        ``200``. Each failing ad is placed as ``ads[0]`` of its own ad set
        (one ad per ad set) using the execution-error mechanism, which is
        safe regardless of ad position since ``adCreative`` itself stays
        truthy throughout, never triggering Requirement 7.3's
        ``AttributeError``.

        Requirements: 11.2, 11.3
        """
        ad_set_one = make_ad_set(
            name="AdSetOne", ads=[self._make_failed_ad("AdOne")]
        )
        ad_set_two = make_ad_set(
            name="AdSetTwo", ads=[self._make_failed_ad("AdTwo")]
        )

        result, status_code = self._run_multi_ad_set_execute(
            use_case_factory, ad_sets=[ad_set_one, ad_set_two]
        )

        assert status_code == 200
        assert result["ok"] == 1

    def test_mixed_created_and_failed_results_yield_ok_1_and_status_200(
        self, use_case_factory
    ):
        """When a run mixes ``Created`` and ``Failed`` ads across different
        ad sets (one ad set with a fully ``Created`` ad, another ad set
        whose sole/first ad is ``Failed`` via the execution-error
        mechanism), the Final Response contains ``ok=1`` -- the ``Failed``
        entry does not flip the aggregate, since ``ok`` is returned as the
        literal ``1`` -- and the HTTP status code is ``200``.

        Requirements: 11.2, 11.3
        """
        created_ad_set = make_ad_set(
            name="CreatedAdSet", ads=[self._make_created_ad("CreatedAd")]
        )
        failed_ad_set = make_ad_set(
            name="FailedAdSet", ads=[self._make_failed_ad("FailedAd")]
        )

        result, status_code = self._run_multi_ad_set_execute(
            use_case_factory, ad_sets=[created_ad_set, failed_ad_set]
        )

        assert status_code == 200
        assert result["ok"] == 1


class TestExecutePersistenceSideEffects:
    """Requirement 12: exact side effects of ``execute()`` on the Strapi
    repositories via ``_save_campaign_channel_publish``::

        campaign_channel_publish = {
            'meta_campaign_objective': self.objective,
            'meta_optimization_goal': self.optimization_goal,
            'meta_billing_event': self.billing_event,
            'meta_campaign_mode': self.creative_type,
            'meta_account_id': self.ad_account_id,
            'meta_page_id': self.page_id
        }
        if self.lead_gen_form_id:
            campaign_channel_publish['meta_lead_form_id'] = self.lead_gen_form_id
        if self.whatsapp_number_id:
            campaign_channel_publish['meta_whatsapp_id'] = self.whatsapp_number_id

        self._save_campaign_channel_publish(campaign_channel_publish)

    where ``_save_campaign_channel_publish`` calls::

        self.campaign_publish_repository.save_or_update(
            {'campaign_id': self.campaign_id, 'channel_id': self.channel_id},
            campaign_channel_publish_data,
        )

    Every scenario below uses ``creative_type="UNRECOGNIZED_TYPE"`` (outside
    ``DYNAMIC``/``STANDARD``, mirroring ``TestExecuteAggregationAndStatus``)
    with a single ad set containing a single ad whose creation block
    completes without raising, so ``save_or_update`` is reached deterministically
    and exactly once regardless of the ``lead_gen_form_id``/``whatsapp_number_id``
    combination under test.

    Requirements: 12.1, 12.2, 12.5
    """

    @staticmethod
    def _make_single_ad_set():
        """Build a single ad set containing a single ad whose creation
        block completes without raising (mirrors
        ``TestExecuteAggregationAndStatus._make_created_ad``).

        Requirements: 12.1, 14.3
        """
        ad_creative = make_ad_creative(
            object_story_spec=make_object_story_spec(), name="AdCreative"
        )
        ad = make_ad(name="Ad", ad_creative=ad_creative)
        return make_ad_set(name="AdSet", ads=[ad])

    @staticmethod
    def _run_execute_for_persistence(
        use_case_factory,
        lead_gen_form_id=None,
        whatsapp_number_id=None,
        billing_event="IMPRESSIONS",
        channel_id="channel-persist",
        campaign_id="campaign-persist",
    ):
        """Drive a full ``execute()`` call with a single, deterministically
        ``Created`` ad set/ad, returning ``(use_case, mock_campaign_publish_repo_instance,
        result, status_code)`` so a scenario can assert on ``save_or_update``'s
        exact call arguments afterwards.

        ``get_billing_event()`` is explicitly configured (instead of being
        left as a default ``MagicMock``) so ``meta_billing_event`` in the
        resulting dict is a precise, assertable value, mirroring the pattern
        used in ``TestBuildMetaPayload``.

        Requirements: 12.1, 12.2, 12.5, 14.3
        """
        campaign_data = make_campaign_data_dict(
            lead_gen_form_id=lead_gen_form_id,
            whatsapp_number_id=whatsapp_number_id,
        )
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            campaign_id=campaign_id,
            complete_campaign_data=campaign_data,
            creative_type="UNRECOGNIZED_TYPE",
        )
        meta_payload = make_meta_payload(
            ad_sets=[TestExecutePersistenceSideEffects._make_single_ad_set()]
        )

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = meta_payload
            builder_mock.get_billing_event.return_value = billing_event
            builder_mock.get_channel_id.return_value = channel_id
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result, status_code = use_case.execute()

        return use_case, mock_campaign_publish_repo_instance, result, status_code

    @pytest.mark.parametrize(
        "lead_gen_form_id, whatsapp_number_id",
        [
            (None, None),
            ("lead-form-99", None),
            (None, "whatsapp-99"),
            ("lead-form-99", "whatsapp-99"),
        ],
        ids=[
            "neither-lead-form-nor-whatsapp",
            "lead-form-only",
            "whatsapp-only",
            "both-lead-form-and-whatsapp",
        ],
    )
    def test_save_or_update_called_once_with_exact_filter_and_publish_data(
        self, use_case_factory, lead_gen_form_id, whatsapp_number_id
    ):
        """``campaign_publish_repository.save_or_update`` is invoked exactly
        once with ``filter_data={'campaign_id': ..., 'channel_id': ...}`` and
        a second dict containing exactly ``meta_campaign_objective``,
        ``meta_optimization_goal``, ``meta_billing_event``, ``meta_campaign_mode``,
        ``meta_account_id`` and ``meta_page_id``, plus ``meta_lead_form_id``
        and/or ``meta_whatsapp_id`` only when the corresponding use case
        attribute is truthy -- and absent entirely otherwise.

        Requirements: 12.1, 12.2, 12.5
        """
        (
            use_case,
            mock_campaign_publish_repo_instance,
            result,
            status_code,
        ) = self._run_execute_for_persistence(
            use_case_factory,
            lead_gen_form_id=lead_gen_form_id,
            whatsapp_number_id=whatsapp_number_id,
            billing_event="IMPRESSIONS",
            channel_id="channel-persist",
            campaign_id="campaign-persist",
        )

        assert status_code == 200

        expected_filter_data = {
            "campaign_id": "campaign-persist",
            "channel_id": "channel-persist",
        }
        expected_publish_data = {
            "meta_campaign_objective": use_case.objective,
            "meta_optimization_goal": use_case.optimization_goal,
            "meta_billing_event": "IMPRESSIONS",
            "meta_campaign_mode": "UNRECOGNIZED_TYPE",
            "meta_account_id": use_case.ad_account_id,
            "meta_page_id": use_case.page_id,
        }
        if lead_gen_form_id:
            expected_publish_data["meta_lead_form_id"] = lead_gen_form_id
        if whatsapp_number_id:
            expected_publish_data["meta_whatsapp_id"] = whatsapp_number_id

        mock_campaign_publish_repo_instance.save_or_update.assert_called_once_with(
            expected_filter_data, expected_publish_data
        )

        actual_publish_data = (
            mock_campaign_publish_repo_instance.save_or_update.call_args.args[1]
        )
        if lead_gen_form_id:
            assert "meta_lead_form_id" in actual_publish_data
        else:
            assert "meta_lead_form_id" not in actual_publish_data
        if whatsapp_number_id:
            assert "meta_whatsapp_id" in actual_publish_data
        else:
            assert "meta_whatsapp_id" not in actual_publish_data

    @staticmethod
    def _make_ad_set_with_asset_feed_spec(
        asset_feed_spec, ad_creative_overrides=None, ad_overrides=None, ad_set_overrides=None
    ):
        """Build a single ad set containing a single ad whose ``adCreative``
        carries the caller-supplied ``asset_feed_spec`` (instead of the fixed
        minimal one used by ``_make_single_ad_set``), so a scenario can
        inspect the full ``creatives`` entry built from it.

        ``object_story_spec`` is intentionally omitted (left ``ABSENT``):
        with ``creative_type="UNRECOGNIZED_TYPE"`` the DYNAMIC/STANDARD
        validation branches never run (Requirement 10.5), and the creation
        block only *conditionally* reads ``object_story_spec`` (mutating it
        when both ``self.page_id`` and it are truthy), so the ad still
        reaches the creation block and completes as ``"Created"`` without it.

        Requirements: 12.3, 12.6, 14.3
        """
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed_spec,
            name="AdCreative",
            **(ad_creative_overrides or {}),
        )
        ad = make_ad(ad_creative=ad_creative, name="Ad", **(ad_overrides or {}))
        return make_ad_set(ads=[ad], **(ad_set_overrides or {}))

    @staticmethod
    def _run_execute_with_ad_sets(
        use_case_factory,
        ad_sets,
        creative_type="UNRECOGNIZED_TYPE",
        campaign_name="Campaign",
        **campaign_data_overrides
    ):
        """Drive a full ``execute()`` call against caller-supplied ``ad_sets``,
        returning ``(use_case, mock_ad_channel_repo_instance,
        mock_campaign_publish_repo_instance, result, status_code)``.

        Unlike ``_run_execute_for_persistence`` (which always builds the same
        fixed minimal ad set via ``_make_single_ad_set``), this helper accepts
        arbitrary ``ad_sets`` so a scenario can inspect
        ``ad_channel_repository.update`` call arguments and the full
        ``creatives``/``campaign`` sections of the response. ``creative_type``
        defaults to ``"UNRECOGNIZED_TYPE"`` for the same reason documented in
        the class docstring: it reaches the creation block deterministically
        without exercising the DYNAMIC/STANDARD validation branches.

        Requirements: 12.3, 12.6, 12.7, 14.3
        """
        campaign_data = make_campaign_data_dict(**campaign_data_overrides)
        (
            use_case,
            mock_ad_channel_repo_instance,
            mock_campaign_publish_repo_instance,
        ) = use_case_factory(
            complete_campaign_data=campaign_data,
            creative_type=creative_type,
        )
        meta_payload = make_meta_payload(ad_sets=ad_sets, campaign_name=campaign_name)

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = meta_payload
            builder_mock.get_billing_event.return_value = "IMPRESSIONS"
            builder_mock.get_channel_id.return_value = "channel-persist"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result, status_code = use_case.execute()

        return (
            use_case,
            mock_ad_channel_repo_instance,
            mock_campaign_publish_repo_instance,
            result,
            status_code,
        )

    def test_ad_channel_repository_update_called_once_per_ad_set_in_order_with_exact_args(
        self, use_case_factory
    ):
        """``ad_channel_repository.update`` is invoked exactly once per ad
        set, in the same order as ``meta_payload['campaign']['ad_sets']``,
        with the ``ad_channel_id`` extracted from
        ``ads[0].adCreative.asset_feed_spec.ad_channel_id`` (or ``0`` by
        default when that path is absent/omitted) as the first positional
        argument, and ``{'channel_creative': <that ad_set>}`` as the second
        positional argument (``_save_creative_to_publish`` calls
        ``self.ad_channel_repository.update(ad_channel_id, data)``
        positionally, not via a ``data=`` keyword).

        Requirements: 12.3
        """
        ad_set_1 = self._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(ad_channel_id=111),
            ad_set_overrides={"name": "AdSet-1"},
        )
        ad_set_2 = self._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(),
            ad_set_overrides={"name": "AdSet-2"},
        )

        (
            use_case,
            mock_ad_channel_repo_instance,
            _,
            result,
            status_code,
        ) = self._run_execute_with_ad_sets(use_case_factory, [ad_set_1, ad_set_2])

        assert status_code == 200
        assert mock_ad_channel_repo_instance.update.call_count == 2
        assert mock_ad_channel_repo_instance.update.call_args_list == [
            call(111, {"channel_creative": ad_set_1}),
            call(0, {"channel_creative": ad_set_2}),
        ]

    def test_creatives_entry_contains_all_fields_with_expected_values_from_rich_asset_feed_spec(
        self, use_case_factory
    ):
        """Every field of a ``creatives`` entry, as listed in the design
        document, is populated from ``asset_feed_spec`` (and from the ad
        set/ad themselves for ``name``/``adset_id``/``ad_id``/``daily_budget``/
        ``proposal_locations``) with the exact expected value when a rich
        ``asset_feed_spec`` supplies every field.

        Requirements: 12.6
        """
        asset_feed_spec = make_asset_feed_spec(
            ad_channel_id=222,
            images=[
                {"url": "http://img1", "valid": True, "error": None},
                {"url": "http://img2", "valid": False, "error": "bad-image"},
            ],
            bodies=["body-1", "body-2"],
            titles=["title-1"],
            descriptions=["desc-1", "desc-2"],
            call_to_action_types=[{"value": "SHOP_NOW"}],
            images_valid_amount=True,
            titles_valid_amount=True,
            bodies_valid_amount=True,
            descriptions_valid_amount=True,
            call_to_action_types_valid_amount=True,
            images_max_amount=10,
            titles_max_amount=5,
            bodies_max_amount=6,
            descriptions_max_amount=7,
            call_to_action_types_max_amount=1,
            unique_titles=True,
            unique_bodies=True,
            unique_descriptions=True,
            daily_budget_valid=True,
            min_daily_budget=50,
            link_urls=[
                {"website_url": "http://a.example"},
                {"website_url": "http://b.example"},
            ],
            link_url_valid=True,
            locations=["NY", "LA"],
            locations_valid=True,
        )
        ad_set = self._make_ad_set_with_asset_feed_spec(
            asset_feed_spec,
            ad_overrides={"id": "ad-rich-1"},
            ad_set_overrides={
                "name": "AdSet-Rich",
                "id": "adset-rich-1",
                "daily_budget": 555,
                "proposal_locations": ["loc-a", "loc-b"],
            },
        )

        (
            use_case,
            _,
            _,
            result,
            status_code,
        ) = self._run_execute_with_ad_sets(use_case_factory, [ad_set])

        assert status_code == 200
        assert result["ok"] == 1
        creative = result["data"]["creatives"][0]
        assert creative == {
            "idx": 0,
            "name": "AdSet-Rich",
            "adset_id": "adset-rich-1",
            "ad_id": "ad-rich-1",
            "adchannel_id": 222,
            "daily_budget": 555,
            "images": [
                {"url": "http://img1", "valid": True, "error": None},
                {"url": "http://img2", "valid": False, "error": "bad-image"},
            ],
            "bodies": ["body-1", "body-2"],
            "titles": ["title-1"],
            "descriptions": ["desc-1", "desc-2"],
            "call_to_action_types": [{"value": "SHOP_NOW"}],
            "images_valid_amount": True,
            "titles_valid_amount": True,
            "bodies_valid_amount": True,
            "descriptions_valid_amount": True,
            "call_to_action_types_valid_amount": True,
            "images_max_amount": 10,
            "titles_max_amount": 5,
            "bodies_max_amount": 6,
            "descriptions_max_amount": 7,
            "call_to_action_types_max_amount": 1,
            "unique_titles": True,
            "unique_bodies": True,
            "unique_descriptions": True,
            "daily_budget_valid": True,
            "min_daily_budget": 50,
            "proposal_url": "http://a.example,http://b.example",
            "proposal_url_valid": True,
            "proposal_locations": ["loc-a", "loc-b"],
            "locations": ["NY", "LA"],
            "locations_valid": True,
            "promoted_object_valid": False,
        }

    def test_creatives_entry_uses_documented_defaults_for_missing_asset_feed_spec_fields(
        self, use_case_factory
    ):
        """When ``asset_feed_spec`` only supplies the minimal collections
        (``make_asset_feed_spec()`` defaults: empty lists and
        ``ad_channel_id=0``), every other ``creatives`` field falls back to
        its documented default: ``False`` for the ``*_valid_amount``/
        ``unique_*``/``daily_budget_valid``/``proposal_url_valid``/
        ``locations_valid`` flags, ``0`` for the ``*_max_amount`` values and
        ``min_daily_budget``, and ``[]``/``""`` for the collection/joined
        fields.

        Requirements: 12.6
        """
        asset_feed_spec = make_asset_feed_spec()
        ad_set = self._make_ad_set_with_asset_feed_spec(
            asset_feed_spec,
            ad_overrides={"id": "ad-minimal-1"},
            ad_set_overrides={
                "name": "AdSet-Minimal",
                "id": "adset-minimal-1",
                "daily_budget": 100,
            },
        )

        (
            use_case,
            _,
            _,
            result,
            status_code,
        ) = self._run_execute_with_ad_sets(use_case_factory, [ad_set])

        assert status_code == 200
        assert result["ok"] == 1
        creative = result["data"]["creatives"][0]
        assert creative == {
            "idx": 0,
            "name": "AdSet-Minimal",
            "adset_id": "adset-minimal-1",
            "ad_id": "ad-minimal-1",
            "adchannel_id": 0,
            "daily_budget": 100,
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
            "images_max_amount": 0,
            "titles_max_amount": 0,
            "bodies_max_amount": 0,
            "descriptions_max_amount": 0,
            "call_to_action_types_max_amount": 0,
            "unique_titles": False,
            "unique_bodies": False,
            "unique_descriptions": False,
            "daily_budget_valid": False,
            "min_daily_budget": 0,
            "proposal_url": "",
            "proposal_url_valid": False,
            "proposal_locations": [],
            "locations": [],
            "locations_valid": False,
            "promoted_object_valid": False,
        }

    def test_campaign_section_contains_exact_expected_fields(self, use_case_factory):
        """The ``campaign`` section of the final response contains exactly
        ``name`` (from ``meta_payload['campaign']['name']``),
        ``channel_name="Meta"``, ``creatives_no=len(creatives)``,
        ``objective``, ``optimization_goal`` and ``mode=self.creative_type``,
        with no extra/missing keys.

        Requirements: 12.7
        """
        ad_set_1 = self._make_ad_set_with_asset_feed_spec(make_asset_feed_spec())
        ad_set_2 = self._make_ad_set_with_asset_feed_spec(make_asset_feed_spec())

        (
            use_case,
            _,
            _,
            result,
            status_code,
        ) = self._run_execute_with_ad_sets(
            use_case_factory,
            [ad_set_1, ad_set_2],
            campaign_name="Campaign-Persist",
            objective="OUTCOME_LEADS",
            optimization_goal="LEAD_GENERATION",
            lead_gen_form_id="lead-form-1",
        )

        assert status_code == 200
        assert result["ok"] == 1
        assert result["data"]["campaign"] == {
            "name": "Campaign-Persist",
            "channel_name": "Meta",
            "creatives_no": 2,
            "objective": "OUTCOME_LEADS",
            "optimization_goal": "LEAD_GENERATION",
            "mode": "UNRECOGNIZED_TYPE",
        }
        assert use_case.creative_type == "UNRECOGNIZED_TYPE"

    def test_valid_ctas_matches_recommended_ctas_set_for_valid_objective(
        self, use_case_factory
    ):
        """When ``self.objective`` is a valid key of ``META_ODAX_CTA_MAPPING``,
        ``valid_ctas`` in the Final Response contains exactly the same set
        of values as ``META_ODAX_CTA_MAPPING[self.objective]["recommended_ctas"]``
        (``valid_ctas = list(MetaAdsValidator.META_ODAX_CTA_MAPPING.get(self.objective)["recommended_ctas"])``),
        compared by set membership, not list order.

        ``"OUTCOME_TRAFFIC"`` is deliberately kept here (rather than swapped
        for a currently-supported objective) because it is the only
        ``META_ODAX_CTA_MAPPING`` key that is not also a key of
        ``OBJECTIVE_TO_GOALS`` (i.e. the only objective whose CTAs are
        resolved through ``get_allowed_ctas_for_goal``'s
        ``META_ODAX_CTA_MAPPING`` fallback rather than through one of the
        ``SALES_GOAL_ALLOWED_CTAS``/``AWARENESS_GOAL_ALLOWED_CTAS``/
        ``LEADS_GOAL_ALLOWED_CTAS`` tables); no other objective exercises
        that fallback branch. Since ``"OUTCOME_TRAFFIC"`` is not a key of
        ``OBJECTIVE_TO_GOALS`` at all (Meta does not currently support this
        combination for Sinergia), any optimization goal paired with it
        would raise ``MetaException("META002", ...)`` before ``execute()``
        ever reaches the ``valid_ctas`` computation this test is about.
        ``MetaAdsValidator.validate_optimization_goal_for_objective`` is
        patched to bypass that unrelated guard, isolating the scenario to
        the ``valid_ctas`` fallback behaviour under test.

        Requirements: 12.4
        """
        ad_set = self._make_ad_set_with_asset_feed_spec(make_asset_feed_spec())

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_optimization_goal_for_objective",
            return_value=True,
        ):
            (
                use_case,
                _,
                _,
                result,
                status_code,
            ) = self._run_execute_with_ad_sets(
                use_case_factory, [ad_set], objective="OUTCOME_TRAFFIC"
            )

        assert status_code == 200
        assert result["ok"] == 1
        assert use_case.objective == "OUTCOME_TRAFFIC"
        assert set(result["data"]["valid_ctas"]) == set(
            MetaAdsValidator.META_ODAX_CTA_MAPPING["OUTCOME_TRAFFIC"][
                "recommended_ctas"
            ]
        )

    def test_execute_yields_empty_valid_ctas_for_unrecognized_objective_after_persistence_completes(
        self, use_case_factory
    ):
        """When ``self.objective`` is not a key of ``META_ODAX_CTA_MAPPING``
        (e.g. an unsupported objective), the final
        ``MetaAdsValidator.get_allowed_ctas_for_goal(objective=self.objective,
        goal=self.optimization_goal)`` call returns an empty ``set()``
        instead of raising: it has no matching entry in
        ``SALES_GOAL_ALLOWED_CTAS``/``AWARENESS_GOAL_ALLOWED_CTAS``/
        ``LEADS_GOAL_ALLOWED_CTAS`` nor in the ``META_ODAX_CTA_MAPPING``
        fallback, so ``valid_ctas = list(...)`` in the Final Response is
        ``[]`` and ``execute()`` completes normally with ``status_code=200``.

        ``MetaAdsValidator.validate_optimization_goal_for_objective`` is
        patched to bypass the unrelated ``OBJECTIVE_TO_GOALS`` guard (which
        would otherwise raise ``MetaException("META002", ...)`` for this
        unrecognized objective before ``execute()`` ever reaches the
        ``valid_ctas`` computation), isolating the scenario to the
        ``valid_ctas`` fallback behaviour under test -- the same pattern used
        by ``test_valid_ctas_matches_recommended_ctas_set_for_valid_objective``
        above.

        This also characterizes that ``campaign_publish_repository.save_or_update``
        is invoked exactly once, and ``ad_channel_repository.update`` is
        invoked once per ad set (both calls happen earlier in ``execute()``,
        well before the ``valid_ctas`` computation at the very end), i.e. the
        persistence side effects fully complete regardless of the
        unrecognized objective.

        Requirements: 12.4
        """
        ad_set_1 = self._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(), ad_set_overrides={"name": "AdSet-1"}
        )
        ad_set_2 = self._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(), ad_set_overrides={"name": "AdSet-2"}
        )
        campaign_data = make_campaign_data_dict(objective="UNKNOWN_OBJECTIVE")
        (
            use_case,
            mock_ad_channel_repo_instance,
            mock_campaign_publish_repo_instance,
        ) = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="UNRECOGNIZED_TYPE"
        )
        meta_payload = make_meta_payload(ad_sets=[ad_set_1, ad_set_2])

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_optimization_goal_for_objective",
            return_value=True,
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = meta_payload
            builder_mock.get_billing_event.return_value = "IMPRESSIONS"
            builder_mock.get_channel_id.return_value = "channel-persist"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1
        assert result["data"]["valid_ctas"] == []

        mock_campaign_publish_repo_instance.save_or_update.assert_called_once()
        assert mock_ad_channel_repo_instance.update.call_count == 2
        assert mock_ad_channel_repo_instance.update.call_args_list == [
            call(0, {"channel_creative": ad_set_1}),
            call(0, {"channel_creative": ad_set_2}),
        ]

    def test_execute_propagates_type_error_when_ad_sets_key_is_absent_after_save_or_update(
        self, use_case_factory
    ):
        """When the ``ad_sets`` key is completely absent from
        ``meta_payload['campaign']`` (as opposed to being present as an
        empty list), the first iteration -- ``campaign_data.get('ad_sets', [])``,
        which has a default -- succeeds with an empty list, so no ad is
        processed and ``_save_campaign_channel_publish`` (hence
        ``save_or_update``) runs normally and is invoked exactly once.

        The *second* iteration further down, ``enumerate(campaign_data.get('ad_sets'))``
        (with no default), receives ``None`` for the absent key, and
        ``enumerate(None)`` raises ``TypeError`` immediately, before its loop
        body ever executes for any ad set. ``execute()`` propagates that
        ``TypeError`` unmodified, and ``ad_channel_repository.update`` is
        never invoked in this scenario.

        Requirements: 12.9
        """
        campaign_data = make_campaign_data_dict()
        (
            use_case,
            mock_ad_channel_repo_instance,
            mock_campaign_publish_repo_instance,
        ) = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="UNRECOGNIZED_TYPE"
        )
        meta_payload = {"campaign": {"name": "Campaign"}}

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = meta_payload
            builder_mock.get_billing_event.return_value = "IMPRESSIONS"
            builder_mock.get_channel_id.return_value = "channel-persist"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            with pytest.raises(TypeError):
                use_case.execute()

        mock_campaign_publish_repo_instance.save_or_update.assert_called_once()
        mock_ad_channel_repo_instance.update.assert_not_called()


class TestExecuteCombinedScenarios:
    """Requirement 13: combined scenarios exercising multiple ad sets/ads
    together inside a single ``execute()`` call -- an empty/absent
    ``ad_sets`` collection, a mix of independently-processed valid/invalid
    ads across ad sets, and the ordering of ``creatives`` entries.

    This class reuses the multi-ad-set/creation-block helpers already
    defined on ``TestExecuteAggregationAndStatus`` (``_make_created_ad``,
    ``_make_failed_ad``, ``_run_multi_ad_set_execute``) and on
    ``TestExecutePersistenceSideEffects`` (``_make_ad_set_with_asset_feed_spec``,
    ``_run_execute_with_ad_sets``) instead of duplicating their boilerplate.

    **Discrepancy between Requirement 13.1's literal wording and actual code
    behaviour** (documented here, and mirroring the precedent already set for
    Requirements 7.3, 8.13 and 12.9 in this same file): Requirement 13.1
    states that ``ad_sets`` *ausente o vacía* ("absent or empty") both
    produce ``ok=1`` with no ``Resultado_de_Ad`` produced. Reading
    ``execute()`` shows this holds only for ``ad_sets`` present as an empty
    list. When the ``ad_sets`` key is completely absent from
    ``meta_payload['campaign']``, the *first* iteration --
    ``campaign_data.get('ad_sets', [])``, which has a default -- does
    succeed with an empty list and produces no ``Resultado_de_Ad``, exactly
    as 13.1 describes; but ``execute()`` never gets to return a Final
    Response for that scenario, because the later, independent
    ``creatives``-building loop reads the very same key via
    ``enumerate(campaign_data.get('ad_sets'))`` with *no* default. That
    receives ``None`` for the absent key, and ``enumerate(None)`` raises
    ``TypeError`` before returning anything -- the exact same
    first-iteration/second-iteration default inconsistency already
    characterized in Requirement 12.9. So "ausente" cannot actually be
    verified to yield ``ok=1``: this suite verifies the empty-list form
    exactly as specified, and verifies the fully-absent-key form as raising
    ``TypeError`` instead, matching actual code behaviour over the literal
    requirement wording, per the same precedent as Requirement 12.9.

    Requirements: 13.1, 13.2, 13.3
    """

    def test_ad_sets_empty_list_yields_ok_one_with_no_ad_processed(
        self, use_case_factory
    ):
        """When ``meta_payload['campaign']['ad_sets']`` is present as an
        empty list, ``execute()`` does not raise, no ``Resultado_de_Ad`` is
        produced (there is nothing to iterate in either ad-processing loop),
        the Final Response contains ``ok=1``, and ``creatives`` is an empty
        list (``creatives_no=0``).

        Requirements: 13.1
        """
        (
            use_case,
            mock_ad_channel_repo_instance,
            mock_campaign_publish_repo_instance,
            result,
            status_code,
        ) = TestExecutePersistenceSideEffects._run_execute_with_ad_sets(
            use_case_factory, []
        )

        assert status_code == 200
        assert result["ok"] == 1
        assert result["data"]["creatives"] == []
        assert result["data"]["campaign"]["creatives_no"] == 0
        mock_campaign_publish_repo_instance.save_or_update.assert_called_once()
        mock_ad_channel_repo_instance.update.assert_not_called()

    def test_ad_sets_key_completely_absent_raises_type_error_instead_of_ok_one(
        self, use_case_factory
    ):
        """When the ``ad_sets`` key is completely absent from
        ``meta_payload['campaign']`` (as opposed to being present as an
        empty list), ``execute()`` does not reach a Final Response at all:
        it propagates ``TypeError`` from the ``creatives``-building loop's
        unguarded ``enumerate(campaign_data.get('ad_sets'))``, after
        ``_save_campaign_channel_publish`` (hence ``save_or_update``) has
        already run exactly once from the first, defaulted iteration.

        This characterizes, for the combined-scenarios requirement, the same
        discrepancy already documented in this class's docstring and in
        Requirement 12.9: Requirement 13.1's literal wording ("ausente o
        vacía" both yielding ``ok=1``) does not hold for the genuinely
        absent-key case, only for the present-as-empty-list case verified by
        ``test_ad_sets_empty_list_yields_ok_one_with_no_ad_processed`` above.

        Requirements: 13.1
        """
        campaign_data = make_campaign_data_dict()
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(
                complete_campaign_data=campaign_data, creative_type="UNRECOGNIZED_TYPE"
            )
        )
        meta_payload = {"campaign": {"name": "Campaign"}}

        with patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder_mock = deps.MetaAdsPayloadBuilder.return_value
            builder_mock.build_meta_payload.return_value = meta_payload
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )

            with pytest.raises(TypeError):
                use_case.execute()

        mock_campaign_publish_repo_instance.save_or_update.assert_called_once()
        mock_ad_channel_repo_instance.update.assert_not_called()

    def test_multiple_ad_sets_with_valid_and_invalid_ads_process_independently_yield_ok_1(
        self, use_case_factory
    ):
        """When two ad sets each contain a single DYNAMIC ad -- one whose
        titles are valid, one whose titles are (simulated as) not unique --
        the Final Response contains ``ok=1`` overall -- the literal returned
        for every run, because the conditional that consumed ``has_errors``
        is commented out -- and each ad's own
        validation outcome is driven strictly by its own data, never the
        other ad's: ``MetaAdsValidator.is_unique_texts`` is patched with a
        ``side_effect`` callable that raises ``ValueError`` only when it
        receives the *second* ad's own duplicate title texts, and returns a
        success value for every other call (including the first ad's own
        title texts, and both ads' empty ``bodies``/``descriptions`` lists).

        Call-argument assertions on the patched double show that the calls
        carrying each ad's own title texts occurred (``call(["Ad1 Title"])``
        for the first ad, ``call(["Ad2 Duplicate", "Ad2 Duplicate"])`` for
        the second), proving neither call received the other ad's data.
        Additionally, the first ad's own ``asset_feed_spec`` ends up with
        ``unique_titles=True`` (the success mutation reached), while the
        second ad's own ``asset_feed_spec`` never receives ``unique_titles``
        at all (its title try/except raised before that assignment), showing
        the two ads' outcomes were not mixed into each other's state.

        Requirements: 13.2
        """

        def _is_unique_texts_side_effect(texts):
            if texts == ["Ad2 Duplicate", "Ad2 Duplicate"]:
                raise ValueError("Ad2 titles are not unique")
            return True

        asset_feed_1 = make_asset_feed_spec(titles=[{"text": "Ad1 Title"}])
        asset_feed_2 = make_asset_feed_spec(
            titles=[{"text": "Ad2 Duplicate"}, {"text": "Ad2 Duplicate"}]
        )

        ad_1 = make_ad(
            name="Ad1",
            ad_creative=make_ad_creative(
                name="Ad1Creative", asset_feed_spec=asset_feed_1
            ),
        )
        ad_2 = make_ad(
            name="Ad2",
            ad_creative=make_ad_creative(
                name="Ad2Creative", asset_feed_spec=asset_feed_2
            ),
        )
        ad_set_1 = make_ad_set(name="AdSet1", ads=[ad_1], daily_budget=100)
        ad_set_2 = make_ad_set(name="AdSet2", ads=[ad_2], daily_budget=100)

        campaign_data = make_campaign_data_dict()
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="DYNAMIC"
        )
        meta_payload = make_meta_payload(ad_sets=[ad_set_1, ad_set_2])

        with patch_execute_dependencies() as deps, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            side_effect=_is_unique_texts_side_effect,
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_amount",
            return_value=None,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_link_url",
            return_value=True,
        ):
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(min_daily_budget_imp=1000),
                200,
            )
            result, status_code = use_case.execute()

        assert status_code == 200
        assert result["ok"] == 1

        assert call(["Ad1 Title"]) in mock_is_unique_texts.call_args_list
        assert (
            call(["Ad2 Duplicate", "Ad2 Duplicate"])
            in mock_is_unique_texts.call_args_list
        )

        assert asset_feed_1["unique_titles"] is True
        assert "unique_titles" not in asset_feed_2

    def test_creatives_entries_have_sequential_idx_in_ad_set_order_for_multiple_valid_ad_sets(
        self, use_case_factory
    ):
        """When multiple ad sets are all valid (each reaches the creation
        block without raising), ``creatives`` contains one entry per ad set,
        with ``idx`` sequential starting at ``0``, in the same order as
        ``meta_payload['campaign']['ad_sets']`` -- verified both via ``idx``
        and via ``adset_id``/``name`` matching each ad set's own identity in
        input order.

        Requirements: 13.3
        """
        ad_set_a = TestExecutePersistenceSideEffects._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(),
            ad_set_overrides={"name": "AdSet-A", "id": "adset-a"},
        )
        ad_set_b = TestExecutePersistenceSideEffects._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(),
            ad_set_overrides={"name": "AdSet-B", "id": "adset-b"},
        )
        ad_set_c = TestExecutePersistenceSideEffects._make_ad_set_with_asset_feed_spec(
            make_asset_feed_spec(),
            ad_set_overrides={"name": "AdSet-C", "id": "adset-c"},
        )

        (
            use_case,
            _,
            _,
            result,
            status_code,
        ) = TestExecutePersistenceSideEffects._run_execute_with_ad_sets(
            use_case_factory, [ad_set_a, ad_set_b, ad_set_c]
        )

        assert status_code == 200
        assert result["ok"] == 1
        creatives = result["data"]["creatives"]
        assert [c["idx"] for c in creatives] == [0, 1, 2]
        assert [c["adset_id"] for c in creatives] == [
            "adset-a",
            "adset-b",
            "adset-c",
        ]
        assert [c["name"] for c in creatives] == ["AdSet-A", "AdSet-B", "AdSet-C"]


class TestExecuteStandardAdChannelIdReading:
    """Requirement 11: reading ``ad_channel_id`` from ``object_story_spec``
    for a STANDARD creative, on both of its two read sites::

        def _save_creative_to_publish(self, creative):
            if self.creative_type == CreativeType.STANDARD.value:
                for item in creative.get('ads', []):
                    ad_creative = item.get('adCreative', {})

                    object_story_spec = ad_creative.get('object_story_spec') or {}
                    ad_channel_id = object_story_spec.get('ad_channel_id', 0)

                    data = {
                        'channel_creative': {**creative, 'ads': [item]} # creative
                    }
                    self.ad_channel_repository.update(ad_channel_id, data)
            else:
                ad_creative = creative.get('ads')[0].get('adCreative', {})
                ad_channel_id = ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0)

                data = {
                    'channel_creative': creative
                }
                self.ad_channel_repository.update(ad_channel_id, data)

    and::

        def _build_standard_creative_entry(self, idx, ad_set_to_publish, ad):
            ad_creative = ad.get('adCreative') or {}
            object_story_spec = ad_creative.get('object_story_spec') or {}
            ...
            return {
                ...
                'adchannel_id': object_story_spec.get('ad_channel_id', 0),
                ...
            }

    The two read sites do NOT share their third-argument contract:
    ``_save_creative_to_publish`` receives the whole ``creative`` and, on the
    STANDARD branch this class characterises, iterates
    ``creative.get('ads', [])`` descending per ad through
    ``item.get('adCreative', {})`` and issuing one
    ``ad_channel_repository.update`` call per ad (the
    ``creative.get('ads')[0].get('adCreative', {})`` descent lives in the
    DYNAMIC ``else`` branch only), while ``_build_standard_creative_entry``
    receives the full *ad* dict (not its ``adCreative``) and descends into
    ``ad.get('adCreative') or {}`` by itself. Passing an ``adCreative`` to
    the latter would make
    ``ad.get('adCreative')`` return ``None``, collapsing
    ``object_story_spec`` to ``{}`` and degenerating ``adchannel_id`` to the
    default ``0`` regardless of the value under test -- which is precisely
    the distinction this class exists to characterise.

    Feature: meta-ads-standard-precheck-validation, Property 7 (rama de
    lectura): para todo ``object_story_spec`` con o sin la clave
    ``ad_channel_id`` presente, ``_save_creative_to_publish`` (rama
    STANDARD) y ``_build_standard_creative_entry`` SHALL leer exactamente
    ese valor cuando está presente, y SHALL usar ``0`` como valor por
    defecto únicamente cuando la clave está genuinamente ausente del
    diccionario (no cuando está presente con valor ``None`` explícito). El
    default ``0`` de ``dict.get('ad_channel_id', 0)`` solo se aplica cuando
    la clave está ausente por completo -- no cuando está presente con valor
    ``None`` -- por lo que ``{'ad_channel_id': None}`` produce ``None``,
    mientras que ``{}`` produce ``0`` (documentado en ``design.md`` como una
    sutileza deliberada y cubierta con una prueba dedicada).

    Validates: Property 7 (lectura) -- Requirements 11.3, 11.4, 11.5
    """

    @staticmethod
    def _make_standard_creative(object_story_spec, ad_id="ad-1"):
        """Build a minimal ``creative`` dict shaped exactly like
        ``_save_creative_to_publish`` expects: ``{'ads': [{'adCreative':
        {'object_story_spec': ...}}]}``, so it can be passed directly to
        ``use_case._save_creative_to_publish(creative)`` without going
        through a full ``execute()`` call.

        Requirements: 11.3, 11.4
        """
        ad_creative = make_ad_creative(object_story_spec=object_story_spec)
        ad = make_ad(ad_creative=ad_creative, id=ad_id)
        return {"ads": [ad]}

    @pytest.mark.parametrize(
        "ad_channel_id, expected_ad_channel_id",
        [
            (None, None),
            (ABSENT, 0),
            (42, 42),
        ],
        ids=["explicit-none", "absent-key", "positive-integer"],
    )
    def test_save_creative_to_publish_distinguishes_explicit_none_from_absent_key(
        self, use_case_factory, ad_channel_id, expected_ad_channel_id
    ):
        """``_save_creative_to_publish`` calls
        ``self.ad_channel_repository.update(ad_channel_id, data)`` with
        ``ad_channel_id`` read from ``object_story_spec.get('ad_channel_id', 0)``:
        when ``ad_channel_id`` is present in ``object_story_spec`` with the
        explicit value ``None``, the call receives ``None`` as its first
        positional argument (not ``0``); when the key is entirely absent
        from ``object_story_spec``, the call receives ``0``; and a concrete
        positive integer (``42``) passes through unchanged in either case,
        bookending the ``None``/absent distinction with the "normal" case.

        Requirements: 11.3, 11.4, 11.5
        """
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory(
            creative_type="STANDARD"
        )
        object_story_spec = make_object_story_spec()
        if ad_channel_id is not ABSENT:
            object_story_spec["ad_channel_id"] = ad_channel_id

        creative = self._make_standard_creative(object_story_spec)

        use_case._save_creative_to_publish(creative)

        mock_ad_channel_repo_instance.update.assert_called_once_with(
            expected_ad_channel_id, {"channel_creative": creative}
        )

    @pytest.mark.parametrize(
        "ad_channel_id, expected_adchannel_id",
        [
            (None, None),
            (ABSENT, 0),
            (42, 42),
        ],
        ids=["explicit-none", "absent-key", "positive-integer"],
    )
    def test_build_standard_creative_entry_distinguishes_explicit_none_from_absent_key(
        self, use_case_factory, ad_channel_id, expected_adchannel_id
    ):
        """``_build_standard_creative_entry`` populates ``adchannel_id`` from
        ``object_story_spec.get('ad_channel_id', 0)``: when ``ad_channel_id``
        is present in ``object_story_spec`` with the explicit value ``None``,
        the returned dict's ``adchannel_id`` key is ``None`` (not ``0``);
        when the key is entirely absent, ``adchannel_id`` is ``0``; and a
        concrete positive integer (``42``) passes through unchanged in
        either case.

        The third argument is the full *ad* dict taken from
        ``ad_set_to_publish["ads"][0]``, so the method reaches
        ``object_story_spec`` through its own
        ``ad.get('adCreative') or {}`` descent; the ``absent-key`` case
        therefore observes ``0`` because ``ad_channel_id`` is genuinely
        missing from ``object_story_spec``, not because the spec was never
        reached.

        Requirements: 11.3, 11.4, 11.5
        """
        use_case, _, _ = use_case_factory(creative_type="STANDARD")
        object_story_spec = make_object_story_spec()
        if ad_channel_id is not ABSENT:
            object_story_spec["ad_channel_id"] = ad_channel_id

        ad_set_to_publish = TestStandardCreativesEntry._make_ad_set_to_publish(
            object_story_spec=object_story_spec
        )
        ad = ad_set_to_publish["ads"][0]

        result = use_case._build_standard_creative_entry(0, ad_set_to_publish, ad)

        assert result["adchannel_id"] == expected_adchannel_id


_WHITESPACE_CHARS = " \t\n\r\x0b\x0c"
_LEADS_CONVERSION_EVENT_SAMPLES = (
    "LEAD",
    "COMPLETE_REGISTRATION",
    "CONTACT",
    "SUBMIT_APPLICATION",
    "SCHEDULE",
    "START_TRIAL",
    "SUBSCRIBE",
    "PURCHASE",
)


@st.composite
def _case_mangled_event(draw):
    """A known event name with random per-character casing."""
    base = draw(st.sampled_from(_LEADS_CONVERSION_EVENT_SAMPLES))
    flags = draw(st.lists(st.booleans(), min_size=len(base), max_size=len(base)))
    return "".join(c.lower() if f else c for c, f in zip(base, flags))


def raw_conversion_events():
    """Hypothesis strategy for raw ``complete_campaign_data['conversion_event']``
    values, covering every shape Requirement 3.5/3.6 distinguishes:

    - ``ABSENT`` (the caller must drop the key from the dict),
    - ``None``,
    - non-``str`` values (int, float, bool, bytes, list, dict),
    - ``""`` and whitespace-only strings,
    - strings with content, optionally padded with whitespace (known
      Meta event names with random casing and arbitrary text).

    Module-level so later property tests can reuse it.

    Requirements: 3.5, 3.6
    """
    whitespace = st.text(alphabet=_WHITESPACE_CHARS, max_size=4)
    content = st.one_of(
        _case_mangled_event(),
        st.text(min_size=1, max_size=30).filter(lambda s: s.strip() != ""),
    )
    padded_content = st.tuples(whitespace, content, whitespace).map(lambda t: "".join(t))
    non_str = st.one_of(
        st.integers(),
        st.floats(allow_nan=False),
        st.booleans(),
        st.binary(max_size=10),
        st.lists(st.text(max_size=5), max_size=3),
        st.dictionaries(st.text(max_size=5), st.text(max_size=5), max_size=2),
    )
    return st.one_of(
        st.just(ABSENT),
        st.none(),
        non_str,
        st.just(""),
        whitespace,
        padded_content,
    )


def _arbitrary_objective_optimization_pairs():
    """Known enum values plus arbitrary text / ``None`` for both fields."""
    objectives = st.one_of(
        st.sampled_from([o.value for o in CampaignObjective]),
        st.none(),
        st.text(max_size=20),
    )
    goals = st.one_of(
        st.sampled_from(
            [g.value for g in AwarenessOptimizationGoal]
            + [g.value for g in LeadsOptimizationGoal]
            + [g.value for g in SalesOptimizationGoal]
        ),
        st.none(),
        st.text(max_size=20),
    )
    return st.tuples(objectives, goals)


class TestLeadsOffsiteConversionEventNormalization:
    """Property 2 over ``FacebookTestCreativeUploadUseCase.__init__`` (inherited
    by ``FacebookGeneratePreCheckCreativeUseCase``).

    Requirements: 3.5, 3.6, 3.7
    """

    # Feature: meta-ads-leads-offsite-conversions, Property 2: Normalización de Conversion_Event en la construcción
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        raw_value=raw_conversion_events(),
        pair=_arbitrary_objective_optimization_pairs(),
        creative_type=st.sampled_from(["DYNAMIC", "STANDARD"]),
    )
    def test_constructor_normalizes_conversion_event(
        self, use_case_factory, raw_value, pair, creative_type
    ):
        """**Validates: Requirements 3.5, 3.6, 3.7**

        For every raw ``conversion_event`` and every (objective,
        optimization_goal) pair, construction does not raise and leaves
        ``conversion_event == v.strip().upper()`` when ``v`` is a ``str``
        with a non-blank character, ``None`` otherwise. No validation
        against Eventos_Conversion_Leads happens here (e.g. ``PURCHASE``
        survives normalization).
        """
        objective, optimization_goal = pair
        data = make_campaign_data_dict(objective=objective, optimization_goal=optimization_goal)
        if raw_value is ABSENT:
            data.pop("conversion_event")
        else:
            data["conversion_event"] = raw_value

        use_case, _, _ = use_case_factory(
            complete_campaign_data=data, creative_type=creative_type
        )

        if isinstance(raw_value, str) and raw_value.strip():
            expected = raw_value.strip().upper()
        else:
            expected = None
        assert use_case.conversion_event == expected
        # The raw input dict is not mutated by normalization.
        if raw_value is not ABSENT:
            assert data["conversion_event"] is raw_value


class TestLeadsOffsiteCampaignDataDictAndConstruction:
    """Unit tests for ``CampaignDataDict.conversion_event`` and its
    normalization in ``FacebookTestCreativeUploadUseCase.__init__``.

    Requirements: 3.4, 3.5, 3.6
    """

    def test_campaign_data_dict_declares_optional_str_conversion_event(self):
        """Requirements: 3.4"""
        from typing import Optional

        from app.v2.use_cases.meta_ads import CampaignDataDict

        assert CampaignDataDict.__annotations__["conversion_event"] == Optional[str]

    def test_constructor_strips_and_uppercases_lead_example(self, use_case_factory):
        """``"  lead "`` produces ``"LEAD"``. Requirements: 3.5"""
        data = make_campaign_data_dict(
            objective="OUTCOME_LEADS",
            optimization_goal="OFFSITE_CONVERSIONS",
            conversion_event="  lead ",
        )

        use_case, _, _ = use_case_factory(complete_campaign_data=data)

        assert use_case.conversion_event == "LEAD"

    @pytest.mark.parametrize("raw_value", [ABSENT, None, "", "   ", 123])
    def test_constructor_assigns_none_for_absent_none_blank_or_non_str(
        self, use_case_factory, raw_value
    ):
        """Requirements: 3.6"""
        data = make_campaign_data_dict()
        if raw_value is ABSENT:
            data.pop("conversion_event")
        else:
            data["conversion_event"] = raw_value

        use_case, _, _ = use_case_factory(complete_campaign_data=data)

        assert use_case.conversion_event is None

    def test_constructor_still_raises_attribute_error_when_complete_campaign_data_is_none(
        self,
    ):
        """The ``conversion_event`` guard does not alter the pre-existing
        ``AttributeError`` with ``complete_campaign_data=None``.

        Requirements: 3.5, 3.6
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            with pytest.raises(AttributeError):
                FacebookGeneratePreCheckCreativeUseCase(
                    campaign_id="campaign-1",
                    user_id="user-1",
                    complete_campaign_data=None,
                    creative_type="DYNAMIC",
                )


_LEADS_ALLOWED_EVENTS_FOR_TESTS = (
    "LEAD",
    "COMPLETE_REGISTRATION",
    "CONTACT",
    "SUBMIT_APPLICATION",
    "SCHEDULE",
    "START_TRIAL",
    "SUBSCRIBE",
)


def pixel_ids():
    """Hypothesis strategy for ``complete_campaign_data['pixel_id']``:
    ``ABSENT`` (key dropped), ``None``, ``""``, whitespace-only strings and
    non-blank strings (optionally padded with whitespace).

    Module-level so later property tests can reuse it.
    Requirements: 4.1
    """
    whitespace = st.text(alphabet=_WHITESPACE_CHARS, max_size=4)
    non_blank = st.tuples(
        whitespace,
        st.text(min_size=1, max_size=20).filter(lambda s: s.strip() != ""),
        whitespace,
    ).map(lambda t: "".join(t))
    return st.one_of(
        st.just(ABSENT),
        st.none(),
        st.just(""),
        whitespace,
        non_blank,
    )


def _expected_leads_offsite_code(pixel, event):
    """Reference model for Property 3: first failing mandatory validation."""
    if pixel is ABSENT or pixel is None or (isinstance(pixel, str) and pixel.strip() == ""):
        return "META012"
    normalized = event.strip().upper() if isinstance(event, str) and event.strip() else None
    if normalized is None:
        return "META013"
    if normalized not in _LEADS_ALLOWED_EVENTS_FOR_TESTS:
        return "META014"
    return None


class TestLeadsOffsiteMandatoryParams:
    """Property 3 over ``FacebookGeneratePreCheckCreativeUseCase.execute()``
    for Combinación_Leads_Offsite in both branches.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.5, 9.6
    """

    @staticmethod
    def _make_ad_payload(creative_type):
        if creative_type == "DYNAMIC":
            creative = make_ad_creative(
                asset_feed_spec=make_asset_feed_spec(
                    images=[{"url": "https://example.com/imagen.jpg"}],
                    link_urls=[{"website_url": "https://example.com/destino"}],
                )
            )
        else:
            creative = make_ad_creative(
                object_story_spec=make_object_story_spec(
                    link_data=make_standard_link_data_full()
                )
            )
        return make_meta_payload(ad_sets=[make_ad_set(ads=[make_ad(ad_creative=creative)])])

    @classmethod
    def _run(cls, use_case_factory, pixel, event, creative_type):
        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
        )
        if pixel is not ABSENT:
            data["pixel_id"] = pixel
        if event is ABSENT:
            data.pop("conversion_event")
        else:
            data["conversion_event"] = event
        use_case, ad_channel_repo, publish_repo = use_case_factory(
            complete_campaign_data=data, creative_type=creative_type
        )
        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(f"{validator}.validate_images_precheck") as mock_images, patch(
            f"{validator}.is_valid_link_url"
        ), patch(f"{validator}.is_valid_length"), patch(
            f"{validator}.validate_cta_for_goal", return_value=True
        ), patch(f"{validator}.is_unique_texts"), patch(
            f"{validator}.is_valid_amount"
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                cls._make_ad_payload(creative_type)
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            exception = None
            try:
                use_case.execute()
            except MetaException as exc:
                exception = exc
            except Exception as exc:  # noqa: BLE001 - unrelated downstream errors
                exception = exc
        return exception, mock_images, ad_channel_repo, publish_repo

    # Feature: meta-ads-leads-offsite-conversions, Property 3: Validaciones obligatorias del PreCheck como modelo de referencia
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        pixel=pixel_ids(),
        event=raw_conversion_events(),
        creative_type=st.sampled_from(["DYNAMIC", "STANDARD"]),
    )
    def test_execute_raises_exactly_expected_code(
        self, use_case_factory, pixel, event, creative_type
    ):
        """**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 8.5, 9.6**

        ``execute()`` raises exactly ``expected(pixel, event)``; when it
        raises, no persistence and no image validation happen. For
        ``META014`` the message carries the value and the 7 allowed events.
        """
        expected = _expected_leads_offsite_code(pixel, event)
        exception, mock_images, ad_channel_repo, publish_repo = self._run(
            use_case_factory, pixel, event, creative_type
        )
        raised_code = getattr(exception, "code", None) if isinstance(exception, MetaException) else None
        if raised_code not in ("META012", "META013", "META014"):
            raised_code = None
        assert raised_code == expected, f"exception={exception!r}"

        if expected is None:
            # Valid pixel + allowed event: execute() completes and reaches the loop.
            assert exception is None, f"exception={exception!r}"
            if creative_type == "DYNAMIC":
                mock_images.assert_called()
        else:
            publish_repo.save_or_update.assert_not_called()
            ad_channel_repo.update.assert_not_called()
            mock_images.assert_not_called()
            if expected == "META014":
                message = str(exception.text if hasattr(exception, "text") else exception)
                assert event.strip().upper() in message
                for allowed in _LEADS_ALLOWED_EVENTS_FOR_TESTS:
                    assert allowed in message

    @classmethod
    def _run_without_http(cls, use_case_factory, pixel, event, creative_type):
        """``_run`` with ``requests.get`` patched so tests can assert that no
        HTTP call (e.g. pixel eligibility) happens."""
        with patch("app.v2.use_cases.meta_ads.requests.get") as mock_get:
            result = cls._run(use_case_factory, pixel, event, creative_type)
        return result + (mock_get,)

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    @pytest.mark.parametrize("pixel", [ABSENT, None, ""], ids=["omitted", "none", "empty"])
    def test_missing_pixel_id_raises_meta012(self, use_case_factory, pixel, creative_type):
        """Requirements: 4.1, 4.2, 14.5"""
        exception, mock_images, ad_channel_repo, publish_repo, mock_get = self._run_without_http(
            use_case_factory, pixel, "LEAD", creative_type
        )

        assert isinstance(exception, MetaException), f"exception={exception!r}"
        assert exception.code == "META012"
        publish_repo.save_or_update.assert_not_called()
        ad_channel_repo.update.assert_not_called()
        mock_images.assert_not_called()
        mock_get.assert_not_called()

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    @pytest.mark.parametrize("event", [ABSENT, None, ""], ids=["omitted", "none", "empty"])
    def test_missing_conversion_event_raises_meta013(self, use_case_factory, event, creative_type):
        """Requirements: 4.3, 4.5, 14.5"""
        exception, mock_images, ad_channel_repo, publish_repo, mock_get = self._run_without_http(
            use_case_factory, "pixel-1", event, creative_type
        )

        assert isinstance(exception, MetaException), f"exception={exception!r}"
        assert exception.code == "META013"
        publish_repo.save_or_update.assert_not_called()
        ad_channel_repo.update.assert_not_called()
        mock_images.assert_not_called()
        mock_get.assert_not_called()

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    @pytest.mark.parametrize(
        "event, persisted_event",
        [(e, e) for e in _LEADS_ALLOWED_EVENTS_FOR_TESTS] + [("  lead ", "LEAD")],
    )
    def test_allowed_events_are_accepted_and_persisted_normalized(
        self, use_case_factory, event, persisted_event, creative_type
    ):
        """Requirements: 4.6, 14.6"""
        exception, _, _, publish_repo, _ = self._run_without_http(
            use_case_factory, "pixel-1", event, creative_type
        )

        assert exception is None, f"exception={exception!r}"
        publish_repo.save_or_update.assert_called_once()
        _, persisted = publish_repo.save_or_update.call_args.args
        assert persisted["meta_conversion_event"] == persisted_event

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    @pytest.mark.parametrize("event", ["PURCHASE", "FOO"])
    def test_disallowed_event_raises_meta014(self, use_case_factory, event, creative_type):
        """Requirements: 4.6, 14.6"""
        exception, mock_images, ad_channel_repo, publish_repo, mock_get = self._run_without_http(
            use_case_factory, "pixel-1", event, creative_type
        )

        assert isinstance(exception, MetaException), f"exception={exception!r}"
        assert exception.code == "META014"
        assert event in str(exception.text)
        publish_repo.save_or_update.assert_not_called()
        ad_channel_repo.update.assert_not_called()
        mock_images.assert_not_called()
        mock_get.assert_not_called()

    def test_standard_supported_combinations_has_exactly_five_tuples(self):
        """Requirements: 5.1, 14.14"""
        assert FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS == {
            (CampaignObjective.AWARENESS.value, AwarenessOptimizationGoal.REACH.value),
            (CampaignObjective.LEADS.value, LeadsOptimizationGoal.LEAD_GENERATION.value),
            (CampaignObjective.LEADS.value, LeadsOptimizationGoal.CONVERSATIONS.value),
            (CampaignObjective.SALES.value, SalesOptimizationGoal.OFFSITE_CONVERSIONS.value),
            (CampaignObjective.LEADS.value, LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value),
        }
        assert len(FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS) == 5

    def test_leads_offsite_standard_does_not_raise_meta011_or_meta002(self, use_case_factory):
        """Requirements: 5.1, 5.2, 14.14"""
        exception, _, _, publish_repo, _ = self._run_without_http(
            use_case_factory, "pixel-1", "LEAD", "STANDARD"
        )

        assert exception is None, f"exception={exception!r}"
        publish_repo.save_or_update.assert_called_once()


_OTHER_COMBINATIONS_BY_BRANCH = {
    # STANDARD: every supported pair except Combinación_Leads_Offsite.
    "STANDARD": sorted(
        pair
        for pair in FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS
        if pair
        != (CampaignObjective.LEADS.value, LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value)
    ),
    # DYNAMIC: same pairs minus CONVERSATIONS (META010 for DYNAMIC).
    "DYNAMIC": sorted(
        pair
        for pair in FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS
        if pair
        not in (
            (CampaignObjective.LEADS.value, LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value),
            (CampaignObjective.LEADS.value, LeadsOptimizationGoal.CONVERSATIONS.value),
        )
    ),
}


@st.composite
def _other_combination_cases(draw):
    """(creative_type, objective, optimization_goal) for Otras_Combinaciones
    supported by the chosen branch."""
    creative_type = draw(st.sampled_from(["DYNAMIC", "STANDARD"]))
    objective, optimization_goal = draw(
        st.sampled_from(_OTHER_COMBINATIONS_BY_BRANCH[creative_type])
    )
    return creative_type, objective, optimization_goal


class TestLeadsOffsiteOtherCombinationsIgnoreEvent:
    """Property 4 over ``FacebookGeneratePreCheckCreativeUseCase.execute()``:
    ``conversion_event`` is inert for Otras_Combinaciones in both branches.

    Requirements: 4.7, 9.3, 13.4
    """

    @staticmethod
    def _make_campaign_data(objective, optimization_goal, event):
        data = make_campaign_data_dict(
            objective=objective,
            optimization_goal=optimization_goal,
            # Prerequisites of each supported combination (META001/007/008).
            pixel_id="pixel-1" if objective == CampaignObjective.SALES.value else None,
            lead_gen_form_id=(
                "form-1"
                if optimization_goal == LeadsOptimizationGoal.LEAD_GENERATION.value
                else None
            ),
            whatsapp_number_id=(
                "wa-1"
                if optimization_goal == LeadsOptimizationGoal.CONVERSATIONS.value
                else None
            ),
        )
        if event is ABSENT:
            data.pop("conversion_event")
        else:
            data["conversion_event"] = event
        return data

    @classmethod
    def _run(cls, use_case_factory, creative_type, objective, optimization_goal, event):
        data = cls._make_campaign_data(objective, optimization_goal, event)
        use_case, ad_channel_repo, publish_repo = use_case_factory(
            complete_campaign_data=data, creative_type=creative_type
        )
        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        # Concrete return values (not MagicMocks) so two independent runs
        # produce comparable annotations.
        with patch(f"{validator}.validate_images_precheck", return_value=None), patch(
            f"{validator}.is_valid_link_url", return_value=True
        ), patch(f"{validator}.is_valid_length", return_value=None), patch(
            f"{validator}.validate_cta_for_goal", return_value=True
        ), patch(f"{validator}.is_unique_texts", return_value=True), patch(
            f"{validator}.is_valid_amount", return_value=None
        ), patch.object(
            FacebookGeneratePreCheckCreativeUseCase,
            "_validate_page_whatsapp_eligibility",
            return_value=True,
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = (
                TestLeadsOffsiteMandatoryParams._make_ad_payload(creative_type)
            )
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            result = use_case.execute()
        return result, ad_channel_repo, publish_repo

    # Feature: meta-ads-leads-offsite-conversions, Property 4: conversion_event es inerte para Otras_Combinaciones
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(case=_other_combination_cases(), event=raw_conversion_events())
    def test_conversion_event_is_inert_for_other_combinations(
        self, use_case_factory, case, event
    ):
        """**Validates: Requirements 4.7, 9.3, 13.4**

        For every Otras_Combinaciones pair supported by the branch and every
        ``conversion_event``, ``execute()`` does not raise (in particular no
        ``META012``/``META013``/``META014``), ``save_or_update`` never gets
        ``meta_conversion_event`` and response/persistence equal the same
        run without ``conversion_event``.
        """
        creative_type, objective, optimization_goal = case

        try:
            result, ad_channel_repo, publish_repo = self._run(
                use_case_factory, creative_type, objective, optimization_goal, event
            )
        except MetaException as exc:  # pragma: no cover - failure path
            pytest.fail(f"Unexpected MetaException {getattr(exc, 'code', None)}: {exc!r}")

        baseline, base_ad_channel_repo, base_publish_repo = self._run(
            use_case_factory, creative_type, objective, optimization_goal, ABSENT
        )

        publish_repo.save_or_update.assert_called_once()
        _, persisted = publish_repo.save_or_update.call_args.args
        assert "meta_conversion_event" not in persisted

        assert result == baseline
        assert (
            publish_repo.save_or_update.call_args_list
            == base_publish_repo.save_or_update.call_args_list
        )
        assert ad_channel_repo.update.call_args_list == base_ad_channel_repo.update.call_args_list

    @pytest.mark.parametrize("event", ["PURCHASE", "FOO"])
    @pytest.mark.parametrize(
        "creative_type, objective, optimization_goal",
        [
            (branch, objective, goal)
            for branch, pairs in sorted(_OTHER_COMBINATIONS_BY_BRANCH.items())
            for objective, goal in pairs
        ],
    )
    def test_disallowed_event_is_ignored_for_other_combinations(
        self, use_case_factory, creative_type, objective, optimization_goal, event
    ):
        """Requirements: 4.7, 14.6"""
        try:
            _, _, publish_repo = self._run(
                use_case_factory, creative_type, objective, optimization_goal, event
            )
        except MetaException as exc:  # pragma: no cover - failure path
            pytest.fail(f"Unexpected MetaException {getattr(exc, 'code', None)}: {exc!r}")

        publish_repo.save_or_update.assert_called_once()
        _, persisted = publish_repo.save_or_update.call_args.args
        assert "meta_conversion_event" not in persisted


_VALID_DYNAMIC_URLS = (
    "https://example.com",
    "https://www.example.com/landing",
    "https://sub.domain.co/path?x=1",
)


@st.composite
def _link_url_entry(draw, string_only=False):
    """One ``asset_feed_spec.link_urls`` entry.

    ``string_only=False``: ``website_url`` is absent, ``None``, ``""``, a
    valid URL or arbitrary text. ``string_only=True``: only ``str`` values
    (``""``, valid URL or arbitrary text), for Otras_Combinaciones.
    """
    kinds = ["empty", "valid", "text"] if string_only else ["absent", "none", "empty", "valid", "text"]
    kind = draw(st.sampled_from(kinds))
    entry = {"display_url": draw(st.sampled_from(["", "example.com"]))}
    if kind == "absent":
        return entry
    if kind == "none":
        entry["website_url"] = None
    elif kind == "empty":
        entry["website_url"] = ""
    elif kind == "valid":
        entry["website_url"] = draw(st.sampled_from(_VALID_DYNAMIC_URLS))
    else:
        entry["website_url"] = draw(st.text(max_size=40))
    return entry


def link_urls_lists(string_only=False):
    """Hypothesis strategy for ``asset_feed_spec.link_urls`` lists of 0 to 3
    entries (see ``_link_url_entry``). Reused by Property 5 and Property 6.
    """
    return st.lists(_link_url_entry(string_only=string_only), min_size=0, max_size=3)


def _expected_dynamic_link_url_valid(link_urls):
    """Reference for Property 5 / Requirement 7.1: ``True`` iff the non-empty
    ``website_url`` values joined by ``,`` form exactly one URL matching
    ``URL_PATTERN``."""
    import re

    from app.v2.use_cases.facebook_validator_service import URL_PATTERN

    urls = [e.get("website_url") for e in link_urls if e.get("website_url")]
    if not urls:
        return False
    joined = ",".join(urls)
    return len(joined.split(",")) == 1 and re.match(URL_PATTERN, joined) is not None


class TestLeadsOffsiteDynamicUrl:
    """Properties 5 and 6: ``asset_feed_spec.link_urls`` validation in the
    DYNAMIC branch of the PreCheck.

    Requirements: 7.1, 7.2, 7.3, 7.6
    """

    # Feature: meta-ads-leads-offsite-conversions, Property 5: URL DYNAMIC de Combinación_Leads_Offsite
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(link_urls=link_urls_lists(), drop_key=st.booleans())
    def test_leads_offsite_dynamic_url_matches_reference(
        self, use_case_factory, link_urls, drop_key
    ):
        """**Validates: Requirements 7.1, 7.2, 7.3**

        ``link_url_valid == ref(link_urls)``; exactly one ``url-error`` iff
        ``link_url_valid`` is ``False``; ``is_valid_link_url`` is not invoked
        when there is no non-empty URL.
        """
        use_case, _, _ = use_case_factory(creative_type="DYNAMIC")
        # Absent key behaves like an empty list (Requirement 7.2).
        effective = [] if drop_key else link_urls
        asset_feed = {} if drop_key else {"link_urls": [dict(e) for e in link_urls]}
        current_ad_errors = []
        expected = _expected_dynamic_link_url_valid(effective)
        non_empty = [e["website_url"] for e in effective if e.get("website_url")]

        with patch.object(
            MetaAdsValidator,
            "is_valid_link_url",
            wraps=MetaAdsValidator.is_valid_link_url,
        ) as spy:
            use_case._validate_leads_offsite_dynamic_url(asset_feed, current_ad_errors)

        assert asset_feed["link_url_valid"] is expected
        url_errors = [e for e in current_ad_errors if e.get("slug") == "url-error"]
        assert len(current_ad_errors) == len(url_errors)
        if expected:
            assert url_errors == []
        else:
            assert len(url_errors) == 1
            assert url_errors[0]["message"]

        if non_empty:
            joined = ",".join(non_empty)
            spy.assert_called_once_with(joined)
            if not expected:
                # Requirement 7.3: message includes the evaluated URL.
                assert joined in url_errors[0]["message"]
        else:
            spy.assert_not_called()

    @staticmethod
    def _run_other_combination_dynamic(use_case_factory, objective, optimization_goal, link_urls):
        """Drive a full DYNAMIC ``execute()`` for an Otras_Combinaciones pair
        with ``asset_feed_spec.link_urls = link_urls``.

        ``is_valid_link_url`` runs the real implementation; its side effect
        also captures the ``current_ad_errors`` list of the calling
        ``execute()`` frame so the errors recorded for the ad (which
        ``execute()`` does not return) can be inspected afterwards.

        Returns ``(asset_feed, url_calls, captured_errors, leads_offsite_spy)``.
        """
        import inspect

        data = TestLeadsOffsiteOtherCombinationsIgnoreEvent._make_campaign_data(
            objective, optimization_goal, ABSENT
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=data, creative_type="DYNAMIC"
        )
        asset_feed = make_asset_feed_spec(
            images=[{"url": "https://example.com/imagen.jpg"}],
            link_urls=[dict(e) for e in link_urls],
        )
        payload = make_meta_payload(
            ad_sets=[make_ad_set(ads=[make_ad(ad_creative=make_ad_creative(asset_feed_spec=asset_feed))])]
        )

        real_is_valid_link_url = MetaAdsValidator.is_valid_link_url
        url_calls = []
        captured_errors = []

        def _capturing_is_valid_link_url(url):
            url_calls.append(url)
            frame = inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name == "execute" and "current_ad_errors" in frame.f_locals:
                    captured_errors.append(frame.f_locals["current_ad_errors"])
                    break
                frame = frame.f_back
            return real_is_valid_link_url(url)

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(f"{validator}.validate_images_precheck", return_value=None), patch(
            f"{validator}.is_valid_link_url", side_effect=_capturing_is_valid_link_url
        ), patch(f"{validator}.is_valid_length", return_value=None), patch(
            f"{validator}.validate_cta_for_goal", return_value=True
        ), patch(f"{validator}.is_unique_texts", return_value=True), patch(
            f"{validator}.is_valid_amount", return_value=None
        ), patch.object(
            FacebookGeneratePreCheckCreativeUseCase,
            "_validate_page_whatsapp_eligibility",
            return_value=True,
        ), patch.object(
            FacebookGeneratePreCheckCreativeUseCase,
            "_validate_leads_offsite_dynamic_url",
        ) as leads_offsite_spy, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            use_case.execute()
        return asset_feed, url_calls, captured_errors, leads_offsite_spy

    # Feature: meta-ads-leads-offsite-conversions, Property 6: Otras_Combinaciones DYNAMIC nunca registran url-error
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        combination=st.sampled_from(_OTHER_COMBINATIONS_BY_BRANCH["DYNAMIC"]),
        link_urls=link_urls_lists(string_only=True),
    )
    def test_other_combinations_dynamic_url_never_records_url_error(
        self, use_case_factory, combination, link_urls
    ):
        """**Validates: Requirements 7.6**

        For every DYNAMIC Otras_Combinaciones pair and every ``link_urls``
        with string ``website_url``: the existing URL block runs unchanged
        (``is_valid_link_url`` called once with ``','.join(website_urls)``),
        ``link_url_valid`` equals that result, the Leads_Offsite helper is
        not used and no ``url-error`` is recorded for the ad.
        """
        objective, optimization_goal = combination
        asset_feed, url_calls, captured_errors, leads_offsite_spy = (
            self._run_other_combination_dynamic(
                use_case_factory, objective, optimization_goal, link_urls
            )
        )

        joined = ",".join(e["website_url"] for e in link_urls)
        assert url_calls == [joined]
        assert asset_feed["link_url_valid"] is MetaAdsValidator.is_valid_link_url(joined)
        leads_offsite_spy.assert_not_called()

        assert len(captured_errors) == 1, "current_ad_errors of execute() not captured"
        assert [e for e in captured_errors[0] if e.get("slug") == "url-error"] == []

    # ------------------------------------------------------------------
    # Task 6.9: unit tests driving the full DYNAMIC ``execute()``.
    # ------------------------------------------------------------------

    @staticmethod
    def _make_leads_offsite_dynamic_asset_feed(link_urls=ABSENT):
        """Asset feed with content in every collection so the other
        ``*_valid``/``unique_*`` annotations are actually computed.
        ``link_urls=ABSENT`` omits the key entirely."""
        asset_feed = make_asset_feed_spec(
            images=[{"url": "https://example.com/imagen.jpg"}],
            titles=[{"text": "Titulo"}],
            bodies=[{"text": "Cuerpo"}],
            descriptions=[{"text": "Descripcion"}],
            call_to_action_types=[{"value": "SIGN_UP"}],
        )
        if link_urls is ABSENT:
            asset_feed.pop("link_urls")
        else:
            asset_feed["link_urls"] = [dict(e) for e in link_urls]
        return asset_feed

    @classmethod
    def _run_leads_offsite_dynamic(cls, use_case_factory, link_urls_per_ad_set):
        """Drive a full DYNAMIC ``execute()`` for Combinación_Leads_Offsite
        with one ad set (one ad each, as in DYNAMIC) per entry of
        ``link_urls_per_ad_set``.

        The real ``_validate_leads_offsite_dynamic_url`` runs; a wrapper
        captures the internal ``results`` list of the calling ``execute()``
        frame (not exposed in the response), which is later filled with the
        per-ad entries.

        Returns ``(response, status_code, results, helper_spy)``.
        """
        import inspect

        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
            pixel_id="pixel-123",
            conversion_event="LEAD",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=data, creative_type="DYNAMIC"
        )
        ad_sets = [
            make_ad_set(
                name=f"AdSet {i}",
                ads=[
                    make_ad(
                        name=f"Ad {i}",
                        ad_creative=make_ad_creative(
                            asset_feed_spec=cls._make_leads_offsite_dynamic_asset_feed(link_urls)
                        ),
                    )
                ],
            )
            for i, link_urls in enumerate(link_urls_per_ad_set)
        ]
        payload = make_meta_payload(ad_sets=ad_sets)

        real_helper = FacebookGeneratePreCheckCreativeUseCase._validate_leads_offsite_dynamic_url
        captured_results = []

        def _capturing_helper(self, asset_feed, current_ad_errors):
            frame = inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name == "execute" and "results" in frame.f_locals:
                    if not captured_results:
                        captured_results.append(frame.f_locals["results"])
                    break
                frame = frame.f_back
            return real_helper(self, asset_feed, current_ad_errors)

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(f"{validator}.validate_images_precheck", return_value=None), patch(
            f"{validator}.is_valid_length", return_value=None
        ), patch(f"{validator}.validate_cta_for_goal", return_value=True), patch(
            f"{validator}.is_unique_texts", return_value=True
        ), patch(f"{validator}.is_valid_amount", return_value=None), patch.object(
            FacebookGeneratePreCheckCreativeUseCase,
            "_validate_leads_offsite_dynamic_url",
            autospec=True,
            side_effect=_capturing_helper,
        ) as helper_spy, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()

        assert len(captured_results) == 1, "results of execute() not captured"
        return response, status_code, captured_results[0], helper_spy

    def test_leads_offsite_dynamic_absent_and_invalid_url_mark_ads_failed_with_url_error(
        self, use_case_factory
    ):
        """Requirements: 7.4, 14.8

        Two DYNAMIC ad sets (one ad each): the first without ``link_urls``,
        the second with an invalid URL. ``execute()`` completes without
        raising; each creative has ``proposal_url_valid is False``; the
        internal ``results`` holds both ads with ``status == "Failed"`` and
        exactly one ``url-error``; every other annotation equals the one of
        a baseline run with a valid URL.
        """
        invalid_url = "not-a-valid-url"
        response, status_code, results, helper_spy = self._run_leads_offsite_dynamic(
            use_case_factory, [ABSENT, [{"website_url": invalid_url}]]
        )
        baseline, _, baseline_results, _ = self._run_leads_offsite_dynamic(
            use_case_factory,
            [[{"website_url": "https://example.com/destino"}]] * 2,
        )

        assert status_code == 200
        assert helper_spy.call_count == 2

        creatives = response["data"]["creatives"]
        assert len(creatives) == 2
        assert [c["proposal_url_valid"] for c in creatives] == [False, False]
        assert creatives[0]["proposal_url"] == ""
        assert creatives[1]["proposal_url"] == invalid_url

        # Internal results: both ads Failed with exactly one url-error each.
        assert [r["ad_name"] for r in results] == ["Ad 0", "Ad 1"]
        for entry in results:
            assert entry["status"] == "Failed"
            url_errors = [e for e in entry["errors"] if e["slug"] == "url-error"]
            assert len(url_errors) == 1
            assert entry["errors"] == url_errors
        assert "ausente" in results[0]["errors"][0]["message"]
        assert invalid_url in results[1]["errors"][0]["message"]

        # Baseline sanity: valid URL -> Created, no url-error.
        assert [r["status"] for r in baseline_results] == ["Created", "Created"]
        assert [c["proposal_url_valid"] for c in baseline["data"]["creatives"]] == [True, True]

        # Other annotations unchanged vs baseline (only URL keys differ).
        url_keys = {"proposal_url", "proposal_url_valid"}
        for failed, ok in zip(creatives, baseline["data"]["creatives"]):
            assert {k: v for k, v in failed.items() if k not in url_keys} == {
                k: v for k, v in ok.items() if k not in url_keys
            }
            assert failed["unique_titles"] is True
            assert failed["daily_budget_valid"] is True
            assert failed["promoted_object_valid"] is True
            assert failed["call_to_action_types"] == [{"value": "SIGN_UP", "valid": True}]

    def test_other_combination_dynamic_absent_url_records_no_url_error(
        self, use_case_factory
    ):
        """Requirements: 14.8 (and 7.6)

        Otras_Combinaciones (OUTCOME_AWARENESS/REACH) in DYNAMIC with empty
        ``link_urls``: existing URL block runs, ``link_url_valid`` is
        ``False`` and no ``url-error`` is recorded for the ad.
        """
        asset_feed, url_calls, captured_errors, leads_offsite_spy = (
            self._run_other_combination_dynamic(
                use_case_factory,
                CampaignObjective.AWARENESS.value,
                AwarenessOptimizationGoal.REACH.value,
                [],
            )
        )

        assert url_calls == [""]
        assert asset_feed["link_url_valid"] is False
        leads_offsite_spy.assert_not_called()
        assert len(captured_errors) == 1
        assert [e for e in captured_errors[0] if e.get("slug") == "url-error"] == []


# CTAs_Leads_Offsite, as defined in the Glossary of the spec (literal on
# purpose, so the oracle does not just echo the production constant).
_LEADS_OFFSITE_CTAS_ORACLE = frozenset({
    "LEARN_MORE", "SIGN_UP", "SUBSCRIBE", "ORDER_NOW", "SHOP_NOW", "APPLY_NOW",
    "BOOK_NOW", "CONTACT_US", "GET_OFFER", "GET_QUOTE", "DOWNLOAD", "SEE_MENU",
    "SEE_DETAILS", "GET_SHOWTIMES", "REQUEST_TIME", "BUY_TICKETS", "LISTEN_NOW",
    "PLAY_GAME", "WATCH_MORE", "NO_BUTTON",
})

# Allowed members, optionally lowercased / with spaces instead of
# underscores / padded, so ``_normalize_cta`` is exercised.
_ALLOWED_DYNAMIC_CTA_VALUES = st.builds(
    lambda cta, lower, spaces, pad: (
        pad + (cta.lower() if lower else cta).replace("_", " " if spaces else "_") + pad
    ),
    st.sampled_from(sorted(_LEADS_OFFSITE_CTAS_ORACLE)),
    st.booleans(),
    st.booleans(),
    st.sampled_from(["", " ", "  "]),
)
# Known non-members (valid for other goals) plus free text.
_DISALLOWED_DYNAMIC_CTA_VALUES = st.one_of(
    st.sampled_from(["WHATSAPP_MESSAGE", "MESSAGE_PAGE", "CALL_NOW", "INSTALL_APP", "GET_DIRECTIONS"]),
    st.text(max_size=20),
)


@st.composite
def _dynamic_cta_entry(draw):
    """One ``call_to_action_types`` element: ``value`` allowed, disallowed,
    absent, ``None`` or empty/blank."""
    kind = draw(st.sampled_from(["allowed", "disallowed", "absent", "none", "empty"]))
    if kind == "absent":
        return {}
    if kind == "none":
        return {"value": None}
    if kind == "empty":
        return {"value": draw(st.sampled_from(["", " ", "   "]))}
    if kind == "allowed":
        return {"value": draw(_ALLOWED_DYNAMIC_CTA_VALUES)}
    return {"value": draw(_DISALLOWED_DYNAMIC_CTA_VALUES)}


class TestLeadsOffsiteDynamicCtas:
    """Property 7: annotation of DYNAMIC ``call_to_action_types`` in the
    PreCheck for Combinación_Leads_Offsite.

    ``execute()`` runs end to end with the real
    ``MetaAdsValidator.validate_cta_for_goal`` and the real
    ``_validate_leads_offsite_dynamic_url`` (each ad has a valid URL).

    Requirements: 6.1, 6.2
    """

    @staticmethod
    def _run(use_case_factory, ctas_per_ad_set):
        """Drive a full DYNAMIC ``execute()`` with one ad set (one ad) per
        entry of ``ctas_per_ad_set``. Returns ``(response, status_code,
        asset_feeds)`` where ``asset_feeds`` are the payload objects mutated
        in place by ``execute()``."""
        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
            pixel_id="pixel-123",
            conversion_event="LEAD",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=data, creative_type="DYNAMIC"
        )
        asset_feeds = [
            make_asset_feed_spec(
                images=[{"url": "https://example.com/imagen.jpg"}],
                titles=[{"text": "Titulo"}],
                bodies=[{"text": "Cuerpo"}],
                descriptions=[{"text": "Descripcion"}],
                link_urls=[{"website_url": "https://example.com/destino"}],
                call_to_action_types=[dict(c) for c in ctas],
            )
            for ctas in ctas_per_ad_set
        ]
        payload = make_meta_payload(
            ad_sets=[
                make_ad_set(
                    name=f"AdSet {i}",
                    ads=[make_ad(name=f"Ad {i}", ad_creative=make_ad_creative(asset_feed_spec=af))],
                )
                for i, af in enumerate(asset_feeds)
            ]
        )

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(f"{validator}.validate_images_precheck", return_value=None), patch(
            f"{validator}.is_valid_length", return_value=None
        ), patch(f"{validator}.is_unique_texts", return_value=True), patch(
            f"{validator}.is_valid_amount", return_value=None
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()
        return response, status_code, asset_feeds

    # Feature: meta-ads-leads-offsite-conversions, Property 7: Anotación de CTAs DYNAMIC en el PreCheck
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        ctas_per_ad_set=st.lists(
            st.lists(_dynamic_cta_entry(), min_size=0, max_size=5), min_size=1, max_size=3
        )
    )
    def test_dynamic_ctas_annotated_per_leads_offsite_set(
        self, use_case_factory, ctas_per_ad_set
    ):
        """**Validates: Requirements 6.1, 6.2**

        After ``execute()`` every element has
        ``valid == (_normalize_cta(value) ∈ CTAs_Leads_Offsite)`` and keeps
        its original ``value`` (or still lacks it), with no exception.
        """
        response, status_code, asset_feeds = self._run(use_case_factory, ctas_per_ad_set)

        assert status_code == 200
        creatives = response["data"]["creatives"]
        assert len(creatives) == len(ctas_per_ad_set)

        for original, asset_feed, creative in zip(ctas_per_ad_set, asset_feeds, creatives):
            annotated = asset_feed["call_to_action_types"]
            assert creative["call_to_action_types"] == annotated
            assert len(annotated) == len(original)
            for before, after in zip(original, annotated):
                # Original ``value`` untouched (absent stays absent).
                assert ("value" in after) == ("value" in before)
                assert after.get("value") == before.get("value")
                assert set(after) == set(before) | {"valid"}
                expected = (
                    MetaAdsValidator._normalize_cta(before.get("value"))
                    in _LEADS_OFFSITE_CTAS_ORACLE
                )
                assert after["valid"] is expected


@st.composite
def _standard_leads_offsite_link_data(draw):
    """A STANDARD ``link_data`` (via ``make_standard_link_data_full``) whose
    landing URL and CTA validity are drawn independently: URL valid,
    invalid or absent; CTA allowed, disallowed, with ``value`` ``None``,
    non-dict, absent or ``None``."""
    link_data = make_standard_link_data_full()
    url_kind = draw(st.sampled_from(["valid", "invalid", "absent"]))
    if url_kind == "valid":
        link_data["link"] = draw(st.sampled_from(_VALID_DYNAMIC_URLS))
    elif url_kind == "invalid":
        link_data["link"] = draw(st.sampled_from(["not-a-valid-url", "ftp//x", "a,b"]))
    else:
        link_data.pop("link", None)

    cta_kind = draw(st.sampled_from(["allowed", "disallowed", "none_value", "non_dict", "absent", "none"]))
    if cta_kind == "allowed":
        link_data["call_to_action"] = make_standard_cta(draw(_ALLOWED_DYNAMIC_CTA_VALUES))
    elif cta_kind == "disallowed":
        link_data["call_to_action"] = make_standard_cta(draw(_DISALLOWED_DYNAMIC_CTA_VALUES))
    elif cta_kind == "none_value":
        link_data["call_to_action"] = make_standard_cta(None)
    elif cta_kind == "non_dict":
        link_data["call_to_action"] = draw(st.sampled_from(["LEARN_MORE", 1, ["SIGN_UP"]]))
    elif cta_kind == "absent":
        link_data.pop("call_to_action", None)
    else:
        link_data["call_to_action"] = None
    return link_data


@st.composite
def _leads_offsite_ad_set_structures(draw):
    """``(creative_type, ad_sets_spec)``: 1–3 ad sets; STANDARD ad sets hold
    1–3 ``link_data`` dicts, DYNAMIC ad sets hold exactly 1
    ``(link_urls, call_to_action_types)`` pair with mixed validity."""
    creative_type = draw(st.sampled_from(["DYNAMIC", "STANDARD"]))
    if creative_type == "STANDARD":
        ad_sets = draw(
            st.lists(
                st.lists(_standard_leads_offsite_link_data(), min_size=1, max_size=3),
                min_size=1,
                max_size=3,
            )
        )
    else:
        ad_sets = draw(
            st.lists(
                st.tuples(
                    link_urls_lists(),
                    st.lists(_dynamic_cta_entry(), min_size=0, max_size=3),
                ).map(lambda t: [t]),
                min_size=1,
                max_size=3,
            )
        )
    return creative_type, ad_sets


class TestLeadsOffsitePreCheckSuccess:
    """Property 8: invariants of a successful Respuesta_PreCheck for
    Combinación_Leads_Offsite (valid pixel + allowed event) in both
    branches, with mixed per-ad validity.

    ``execute()`` runs end to end with the real ``MetaAdsValidator``
    collaborators except ``validate_images_precheck`` (network) and
    ``validate_promoted_object``, which is wrapped by a spy.

    Requirements: 5.3, 6.7, 8.1, 8.2, 8.3, 8.4
    """

    @staticmethod
    def _build_payload(creative_type, ad_sets_spec):
        ad_sets = []
        for i, ads_spec in enumerate(ad_sets_spec):
            ads = []
            for j, spec in enumerate(ads_spec):
                if creative_type == "STANDARD":
                    creative = make_ad_creative(
                        object_story_spec=make_object_story_spec(link_data=spec)
                    )
                else:
                    link_urls, ctas = spec
                    creative = make_ad_creative(
                        asset_feed_spec=make_asset_feed_spec(
                            images=[{"url": "https://example.com/imagen.jpg"}],
                            titles=[{"text": "Titulo"}],
                            bodies=[{"text": "Cuerpo"}],
                            descriptions=[{"text": "Descripcion"}],
                            link_urls=[dict(e) for e in link_urls],
                            call_to_action_types=[dict(c) for c in ctas],
                        )
                    )
                ads.append(make_ad(name=f"Ad {i}-{j}", ad_creative=creative))
            ad_sets.append(make_ad_set(name=f"AdSet {i}", ads=ads))
        return make_meta_payload(ad_sets=ad_sets)

    @classmethod
    def _run(cls, use_case_factory, creative_type, ad_sets_spec):
        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
            pixel_id="pixel-123",
            conversion_event="lead",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=data, creative_type=creative_type
        )
        payload = cls._build_payload(creative_type, ad_sets_spec)

        def _mark_images_valid(images):
            for image in images or []:
                image["valid"] = True
                image["error"] = None

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(
            f"{validator}.validate_images_precheck", side_effect=_mark_images_valid
        ), patch(
            f"{validator}.validate_promoted_object",
            wraps=MetaAdsValidator.validate_promoted_object,
        ) as promoted_spy, patch(
            "app.v2.use_cases.meta_ads.requests.get"
        ) as http_get, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()
        return response, status_code, promoted_spy, http_get

    # Feature: meta-ads-leads-offsite-conversions, Property 8: Invariantes de la Respuesta_PreCheck exitosa
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(structure=_leads_offsite_ad_set_structures())
    def test_successful_precheck_response_invariants(self, use_case_factory, structure):
        """**Validates: Requirements 5.3, 6.7, 8.1, 8.2, 8.3, 8.4**

        For every branch and ad set/ad structure with mixed per-ad validity:
        the response has exactly ``campaign``/``creatives``/``valid_ctas``/
        ``account_config``; one creative per ad; every
        ``promoted_object_valid is True``; ``valid_ctas`` equals
        CTAs_Leads_Offsite (20, no duplicates); ``validate_promoted_object``
        is never invoked.
        """
        creative_type, ad_sets_spec = structure
        response, status_code, promoted_spy, http_get = self._run(
            use_case_factory, creative_type, ad_sets_spec
        )

        assert status_code == 200
        data = response["data"]
        assert set(data) == {"campaign", "creatives", "valid_ctas", "account_config"}

        total_ads = sum(len(ads) for ads in ad_sets_spec)
        creatives = data["creatives"]
        assert len(creatives) == total_ads
        assert data["campaign"]["creatives_no"] == total_ads
        for creative in creatives:
            assert creative["promoted_object_valid"] is True

        valid_ctas = data["valid_ctas"]
        assert len(valid_ctas) == 20
        assert len(set(valid_ctas)) == 20
        assert set(valid_ctas) == _LEADS_OFFSITE_CTAS_ORACLE

        promoted_spy.assert_not_called()
        http_get.assert_not_called()


class TestStandardNonDictCtaGuard:
    """Requirement 15.5/15.8/15.11: a truthy non-dict ``call_to_action`` in
    a STANDARD ad must not crash ``execute()``. ``_validate_standard_cta``
    records exactly one ``cta-error`` (no annotation) and the STANDARD
    entry builders treat the value as ``{}``, so the emitted creative has
    ``call_to_action_types == []`` and
    ``call_to_action_types_valid_amount is False``.

    Per-ad errors are not exposed by ``execute()``; the internal
    ``results`` list is captured from the ``execute()`` frame by wrapping
    the real ``_validate_standard_creative``.

    Requirements: 5.3, 6.5, 8.2, 15.5, 15.8, 15.11
    """

    @staticmethod
    def _run(use_case_factory, objective, optimization_goal, call_to_action):
        import inspect

        link_data = make_standard_link_data_full(call_to_action=call_to_action)
        campaign_data = make_campaign_data_dict(
            objective=objective,
            optimization_goal=optimization_goal,
            pixel_id="pixel-1",
            conversion_event="LEAD",
            lead_gen_form_id="lead-1",
            whatsapp_number_id="whatsapp-1",
        )
        use_case, _, _ = use_case_factory(
            complete_campaign_data=campaign_data, creative_type="STANDARD"
        )
        ad = make_ad(
            name="Ad non-dict CTA",
            ad_creative=make_ad_creative(
                object_story_spec=make_object_story_spec(link_data=link_data)
            ),
        )
        meta_payload = make_meta_payload(ad_sets=[make_ad_set(ads=[ad], daily_budget=100)])

        real_validate = FacebookGeneratePreCheckCreativeUseCase._validate_standard_creative
        captured_results = []

        def _capturing_validate(self, *args, **kwargs):
            frame = inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name == "execute" and "results" in frame.f_locals:
                    if not captured_results:
                        captured_results.append(frame.f_locals["results"])
                    break
                frame = frame.f_back
            return real_validate(self, *args, **kwargs)

        def _mark_images_valid(images):
            for image in images or []:
                image["valid"] = True
                image["error"] = None

        with patch.object(
            use_case, "_validate_pixel_eligibility", return_value=True
        ), patch.object(
            use_case, "_validate_page_whatsapp_eligibility", return_value=True
        ), patch.object(
            FacebookGeneratePreCheckCreativeUseCase,
            "_validate_standard_creative",
            autospec=True,
            side_effect=_capturing_validate,
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck",
            side_effect=_mark_images_valid,
        ), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            deps.MetaAdsPayloadBuilder.return_value.build_meta_payload.return_value = (
                meta_payload
            )
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()

        results = captured_results[0] if captured_results else []
        return response, status_code, results, link_data

    @pytest.mark.parametrize(
        "call_to_action",
        ["LEARN_MORE", 1, ["SIGN_UP"]],
        ids=["str", "int", "list"],
    )
    @pytest.mark.parametrize(
        "objective, optimization_goal",
        STANDARD_SUPPORTED_COMBINATIONS,
        ids=STANDARD_SUPPORTED_COMBINATIONS_IDS,
    )
    def test_non_dict_cta_yields_single_cta_error_and_empty_cta_types(
        self, use_case_factory, objective, optimization_goal, call_to_action
    ):
        response, status_code, results, link_data = self._run(
            use_case_factory, objective, optimization_goal, call_to_action
        )

        assert status_code == 200
        ad_entries = [r for r in results if r.get("ad_name") == "Ad non-dict CTA"]
        assert len(ad_entries) == 1
        assert ad_entries[0]["status"] == "Failed"
        cta_errors = [e for e in ad_entries[0]["errors"] if e.get("slug") == "cta-error"]
        assert len(cta_errors) == 1

        # The non-dict value is left untouched (no ``valid`` annotation).
        assert link_data["call_to_action"] == call_to_action

        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["call_to_action_types"] == []
        assert creatives[0]["call_to_action_types_valid_amount"] is False


@st.composite
def _allowed_leads_event_variants(draw):
    """One of the 7 Eventos_Conversion_Leads with random per-character
    casing and optional whitespace padding on both sides."""
    base = draw(st.sampled_from(_LEADS_ALLOWED_EVENTS_FOR_TESTS))
    flags = draw(st.lists(st.booleans(), min_size=len(base), max_size=len(base)))
    mangled = "".join(c.lower() if f else c for c, f in zip(base, flags))
    whitespace = st.text(alphabet=_WHITESPACE_CHARS, max_size=4)
    return draw(whitespace) + mangled + draw(whitespace)


def _non_blank_pixel_ids():
    """Subset of ``pixel_ids()`` that passes META012 (non-blank ``str``),
    possibly padded with whitespace."""
    return pixel_ids().filter(lambda p: isinstance(p, str) and p.strip() != "")


class TestLeadsOffsitePersistence:
    """Property 9: Campaign_Setup persistence for Combinación_Leads_Offsite.

    ``execute()`` runs end to end in both branches (reusing the payload
    builder and ad set structures from ``TestLeadsOffsitePreCheckSuccess``,
    which mix valid and failed ads) with ``get_billing_event`` mocked to
    ``"IMPRESSIONS"`` and ``get_channel_id`` to ``"channel-1"``.

    Requirements: 9.1, 9.2, 9.5
    """

    @staticmethod
    def _run(use_case_factory, pixel, event, creative_type, ad_sets_spec):
        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
            pixel_id=pixel,
            conversion_event=event,
        )
        use_case, _, publish_repo = use_case_factory(
            campaign_id="campaign-1", complete_campaign_data=data, creative_type=creative_type
        )
        payload = TestLeadsOffsitePreCheckSuccess._build_payload(creative_type, ad_sets_spec)

        def _mark_images_valid(images):
            for image in images or []:
                image["valid"] = True
                image["error"] = None

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(
            f"{validator}.validate_images_precheck", side_effect=_mark_images_valid
        ), patch("app.v2.use_cases.meta_ads.requests.get"), patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()
        return response, status_code, publish_repo

    # Feature: meta-ads-leads-offsite-conversions, Property 9: Persistencia en Campaign_Setup para Combinación_Leads_Offsite
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        pixel=_non_blank_pixel_ids(),
        event=_allowed_leads_event_variants(),
        structure=_leads_offsite_ad_set_structures(),
    )
    def test_campaign_setup_persisted_once_with_pixel_event_and_billing(
        self, use_case_factory, pixel, event, structure
    ):
        """**Validates: Requirements 9.1, 9.2, 9.5**

        For every non-blank ``pixel_id``, every casing/padding variant of an
        allowed event and every failed-ads pattern, ``save_or_update`` is
        called exactly once with filter ``(campaign_id, channel_id)`` and
        data carrying ``meta_pixel_id == pixel`` (untransformed),
        ``meta_conversion_event == event.strip().upper()`` and
        ``meta_billing_event == "IMPRESSIONS"``.
        """
        creative_type, ad_sets_spec = structure
        _, status_code, publish_repo = self._run(
            use_case_factory, pixel, event, creative_type, ad_sets_spec
        )

        assert status_code == 200
        publish_repo.save_or_update.assert_called_once()
        filter_data, persisted = publish_repo.save_or_update.call_args.args
        assert filter_data == {"campaign_id": "campaign-1", "channel_id": "channel-1"}
        assert persisted["meta_pixel_id"] == pixel
        assert persisted["meta_conversion_event"] == event.strip().upper()
        assert persisted["meta_billing_event"] == "IMPRESSIONS"


class TestLeadsOffsitePreCheckHappyPath:
    """Happy-path unit examples of the PreCheck for Combinación_Leads_Offsite
    in both branches: valid ``pixel_id``, allowed (non-normalized) event and
    fully valid ads. Reuses ``TestLeadsOffsitePreCheckSuccess._build_payload``
    and the same mocked collaborators as ``TestLeadsOffsitePersistence._run``,
    additionally allowing ``lead_gen_form_id``/``whatsapp_number_id`` so the
    pre-existing optional Campaign_Setup keys can be checked.

    Requirements: 5.3, 6.7, 8.1, 8.2, 9.1, 9.2, 9.4, 14.4
    """

    _PIXEL = "pixel-123"
    _RAW_EVENT = "  submit_application "

    @staticmethod
    def _ad_sets_spec(creative_type):
        if creative_type == "STANDARD":
            return [[make_standard_link_data_full()]]
        return [[(
            [{"website_url": "https://example.com/destino"}],
            [{"value": "LEARN_MORE"}],
        )]]

    @classmethod
    def _run(cls, use_case_factory, creative_type, lead_gen_form_id=None, whatsapp_number_id=None):
        data = make_campaign_data_dict(
            objective=CampaignObjective.LEADS.value,
            optimization_goal=LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value,
            pixel_id=cls._PIXEL,
            conversion_event=cls._RAW_EVENT,
            lead_gen_form_id=lead_gen_form_id,
            whatsapp_number_id=whatsapp_number_id,
        )
        use_case, _, publish_repo = use_case_factory(
            campaign_id="campaign-1", complete_campaign_data=data, creative_type=creative_type
        )
        payload = TestLeadsOffsitePreCheckSuccess._build_payload(
            creative_type, cls._ad_sets_spec(creative_type)
        )

        def _mark_images_valid(images):
            for image in images or []:
                image["valid"] = True
                image["error"] = None

        validator = "app.v2.use_cases.meta_ads.MetaAdsValidator"
        with patch(
            f"{validator}.validate_images_precheck", side_effect=_mark_images_valid
        ), patch(
            f"{validator}.validate_promoted_object",
            wraps=MetaAdsValidator.validate_promoted_object,
        ) as promoted_spy, patch(
            "app.v2.use_cases.meta_ads.requests.get"
        ) as http_get, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            response, status_code = use_case.execute()
        return response, status_code, publish_repo, promoted_spy, http_get

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    def test_happy_path_response_and_campaign_setup(self, use_case_factory, creative_type):
        """Response carries ``valid_ctas == CTAs_Leads_Offsite`` and
        ``promoted_object_valid is True``; ``save_or_update`` is called once
        with ``meta_pixel_id`` and the normalized ``meta_conversion_event``
        plus the pre-existing keys (no optional ids provided)."""
        response, status_code, publish_repo, promoted_spy, http_get = self._run(
            use_case_factory, creative_type
        )

        assert status_code == 200
        assert response["ok"] == 1
        data = response["data"]
        assert len(data["valid_ctas"]) == 20
        assert set(data["valid_ctas"]) == _LEADS_OFFSITE_CTAS_ORACLE
        assert len(data["creatives"]) == 1
        assert data["creatives"][0]["promoted_object_valid"] is True
        promoted_spy.assert_not_called()
        http_get.assert_not_called()

        publish_repo.save_or_update.assert_called_once_with(
            {"campaign_id": "campaign-1", "channel_id": "channel-1"},
            {
                "meta_campaign_objective": "OUTCOME_LEADS",
                "meta_optimization_goal": "OFFSITE_CONVERSIONS",
                "meta_billing_event": "IMPRESSIONS",
                "meta_campaign_mode": creative_type,
                "meta_account_id": "act-1",
                "meta_page_id": "page-1",
                "meta_pixel_id": self._PIXEL,
                "meta_conversion_event": "SUBMIT_APPLICATION",
            },
        )

    @pytest.mark.parametrize("creative_type", ["DYNAMIC", "STANDARD"])
    def test_happy_path_keeps_optional_preexisting_keys(self, use_case_factory, creative_type):
        """With ``lead_gen_form_id``/``whatsapp_number_id`` provided, the
        persisted dict still carries ``meta_lead_form_id``/``meta_whatsapp_id``
        alongside the new pixel/event keys."""
        _, status_code, publish_repo, _, _ = self._run(
            use_case_factory,
            creative_type,
            lead_gen_form_id="lead-form-1",
            whatsapp_number_id="whatsapp-1",
        )

        assert status_code == 200
        publish_repo.save_or_update.assert_called_once()
        _, persisted = publish_repo.save_or_update.call_args.args
        assert persisted == {
            "meta_campaign_objective": "OUTCOME_LEADS",
            "meta_optimization_goal": "OFFSITE_CONVERSIONS",
            "meta_billing_event": "IMPRESSIONS",
            "meta_campaign_mode": creative_type,
            "meta_account_id": "act-1",
            "meta_page_id": "page-1",
            "meta_lead_form_id": "lead-form-1",
            "meta_whatsapp_id": "whatsapp-1",
            "meta_pixel_id": self._PIXEL,
            "meta_conversion_event": "SUBMIT_APPLICATION",
        }


# ---------------------------------------------------------------------------
# meta-ads-leads-offsite-conversions -- Requirement 15 (Property 10)
# ---------------------------------------------------------------------------

_CTA_TYPE_VALID_INPUTS = st.one_of(
    st.just(ABSENT), st.booleans(), st.none(), st.sampled_from(["yes", 0, 1, []])
)
"""Input ``type.valid`` values: absent, ``True``/``False`` or any other junk;
all of them must be overwritten by the real validation result."""


def _allowed_cta_values(combo):
    """Allowed CTA values for ``combo`` per the real validator, including
    case/whitespace variants that ``MetaAdsValidator._normalize_cta`` maps
    back onto an allowed value."""
    allowed = sorted(MetaAdsValidator.get_allowed_ctas_for_goal(*combo))
    exact = st.sampled_from(allowed)
    variants = st.builds(
        lambda cta, lower, pad: (" " if pad else "") + (cta.lower() if lower else cta) + (" " if pad else ""),
        exact,
        st.booleans(),
        st.booleans(),
    )
    return st.one_of(exact, variants)


def _disallowed_cta_values(combo):
    """CTA values rejected for ``combo`` by the real validator: CTAs allowed
    for some other combination but not this one, empty/blank strings, and
    arbitrary text whose normalized form is not allowed."""
    allowed = MetaAdsValidator.get_allowed_ctas_for_goal(*combo)
    other_known = sorted(
        {
            cta
            for other in FacebookGeneratePreCheckCreativeUseCase._STANDARD_SUPPORTED_COMBINATIONS
            for cta in MetaAdsValidator.get_allowed_ctas_for_goal(*other)
        }
        .union({"CALL_NOW", "WHATSAPP_MESSAGE"})
        .difference(allowed)
    )
    return st.one_of(
        st.sampled_from(other_known),
        st.sampled_from(["", "   "]),
        st.text(max_size=20).filter(
            lambda text: MetaAdsValidator._normalize_cta(text) not in allowed
        ),
    )


@st.composite
def _cta_with_dict_type(draw, combo):
    value = draw(
        st.one_of(
            st.just(ABSENT),
            st.none(),
            _allowed_cta_values(combo),
            _disallowed_cta_values(combo),
        )
    )
    cta_type = {}
    if value is not ABSENT:
        cta_type["value"] = value
    type_valid = draw(_CTA_TYPE_VALID_INPUTS)
    if type_valid is not ABSENT:
        cta_type["valid"] = type_valid
    cta = {"type": cta_type}
    root_valid = draw(_CTA_TYPE_VALID_INPUTS)
    if root_valid is not ABSENT:
        cta["valid"] = root_valid
    return cta


@st.composite
def _cta_without_dict_type(draw, combo):
    """Non-empty ``call_to_action`` dict whose ``type`` is absent or not a
    dict (``None``/str/list/int). When ``type`` is absent, another key is
    always present so the dict stays truthy (Req 15.3 covers non-empty
    dicts; an empty dict is falsy and skipped by Req 15.4)."""
    type_value = draw(
        st.one_of(
            st.just(ABSENT),
            st.none(),
            _allowed_cta_values(combo),
            _disallowed_cta_values(combo),
            st.lists(st.sampled_from(["SIGN_UP", "LEARN_MORE"]), max_size=2),
            st.integers(),
        )
    )
    cta = {}
    if type_value is not ABSENT:
        cta["type"] = type_value
    root_valid = draw(_CTA_TYPE_VALID_INPUTS)
    if root_valid is not ABSENT:
        cta["valid"] = root_valid
    if not cta:
        cta["extra"] = draw(st.sampled_from(["x", 1, True]))
    return cta


def standard_cta_shapes(combo):
    """Strategy of non-empty ``call_to_action`` dicts for the STANDARD
    branch under ``combo`` (one of ``_STANDARD_SUPPORTED_COMBINATIONS``):
    ``type`` as a dict (allowed/disallowed/``None``/absent ``value`` and
    input ``type.valid`` absent/True/False/junk) or ``type`` absent/non-dict
    (``None``/str/list/int). Reused by Property 11 (task 7.4).

    Requirements: 6.3, 15.1, 15.3
    """
    return st.one_of(_cta_with_dict_type(combo), _cta_without_dict_type(combo))


class TestStandardCtaAnnotationFix:
    """Requirement 15 (meta-ads-leads-offsite-conversions): global fix of the
    STANDARD CTA annotation. ``_validate_standard_cta`` writes the real
    ``validate_cta_for_goal`` result into ``call_to_action['type']['valid']``
    and mirrors it at the root ``call_to_action['valid']``, for every
    combination of ``_STANDARD_SUPPORTED_COMBINATIONS``.

    Oracle: the real (un-mocked) ``MetaAdsValidator.validate_cta_for_goal``
    with ``throw=False``.
    """

    # Feature: meta-ads-leads-offsite-conversions, Property 10: para toda
    # combinación de _STANDARD_SUPPORTED_COMBINATIONS y todo call_to_action
    # dict no vacío, _validate_standard_cta deja type.valid igual a
    # validate_cta_for_goal(value, objective, goal, throw=False) con value
    # intacto (type dict) o type == {'value': <original o None>,
    # 'valid': False} (type ausente/no-dict); call_to_action['valid'] ==
    # call_to_action['type']['valid']; exactamente un cta-error que menciona
    # el CTA rechazado si es False y ninguno si es True; sin excepciones.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(combo=st.sampled_from(STANDARD_SUPPORTED_COMBINATIONS), data=st.data())
    def test_property_standard_cta_annotation_fix(self, use_case_factory, combo, data):
        """**Validates: Requirements 6.3, 6.4, 15.1, 15.2, 15.3, 15.6**"""
        objective, optimization_goal = combo
        cta = data.draw(standard_cta_shapes(combo), label="call_to_action")
        original_type = cta.get("type", ABSENT)
        original_type_is_dict = isinstance(original_type, dict)
        original_value = original_type.get("value") if original_type_is_dict else None
        original_value_present = original_type_is_dict and "value" in original_type

        use_case, _, _ = use_case_factory(
            creative_type="STANDARD",
            complete_campaign_data=make_campaign_data_dict(
                objective=objective, optimization_goal=optimization_goal
            ),
        )
        link_data = make_link_data(call_to_action=cta)
        current_ad_errors = []

        use_case._validate_standard_cta(link_data, current_ad_errors)

        result_cta = link_data["call_to_action"]
        assert result_cta is cta
        assert isinstance(result_cta["type"], dict)

        if original_type_is_dict:
            expected_valid = MetaAdsValidator.validate_cta_for_goal(
                original_value, objective, optimization_goal, throw=False
            )
            assert result_cta["type"]["valid"] is expected_valid
            if original_value_present:
                assert result_cta["type"]["value"] == original_value
            rejected = original_value
        else:
            expected_valid = False
            expected_value = None if original_type is ABSENT else original_type
            assert result_cta["type"] == {"value": expected_value, "valid": False}
            rejected = expected_value

        assert result_cta["valid"] is result_cta["type"]["valid"]

        cta_errors = [e for e in current_ad_errors if e.get("slug") == "cta-error"]
        if expected_valid:
            assert current_ad_errors == []
        else:
            assert len(cta_errors) == 1
            assert len(current_ad_errors) == 1
            assert str(rejected) in cta_errors[0]["message"]

    # Feature: meta-ads-leads-offsite-conversions, Property 11: para toda
    # combinación de _STANDARD_SUPPORTED_COMBINATIONS, todo CTA permitido o
    # no permitido y todo type.valid de entrada (ausente/True/False), tras
    # execute() STANDARD call_to_action_types_valid_amount del elemento de
    # creatives es igual a validate_cta_for_goal(value, objective, goal,
    # throw=False) y a call_to_action['type']['valid'], con independencia
    # del type.valid recibido.
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        combo=st.sampled_from(STANDARD_SUPPORTED_COMBINATIONS),
        allowed=st.booleans(),
        input_valid=st.sampled_from([ABSENT, True, False]),
        data=st.data(),
    )
    def test_property_cta_types_valid_amount_reflects_real_validation(
        self, use_case_factory, combo, allowed, input_valid, data
    ):
        """**Validates: Requirements 15.7, 13.7**"""
        objective, optimization_goal = combo
        strategy = _allowed_cta_values(combo) if allowed else _disallowed_cta_values(combo)
        cta_value = data.draw(strategy, label="cta_value")
        call_to_action = make_standard_cta(cta_value, valid=input_valid)

        response, status_code, results, link_data = TestStandardNonDictCtaGuard._run(
            use_case_factory, objective, optimization_goal, call_to_action
        )

        expected_valid = MetaAdsValidator.validate_cta_for_goal(
            cta_text=cta_value, objective=objective, goal=optimization_goal, throw=False
        )
        assert expected_valid is allowed

        assert status_code == 200
        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["call_to_action_types_valid_amount"] is expected_valid
        assert link_data["call_to_action"]["type"]["valid"] is expected_valid
        assert link_data["call_to_action"]["valid"] is expected_valid

        ad_entries = [r for r in results if r.get("ad_name") == "Ad non-dict CTA"]
        assert len(ad_entries) == 1
        cta_errors = [
            e for e in ad_entries[0].get("errors") or [] if e.get("slug") == "cta-error"
        ]
        assert len(cta_errors) == (0 if expected_valid else 1)

    # ------------------------------------------------------------------
    # Unit tests (task 7.5): Requirements 14.16-14.20, 15.3
    # ------------------------------------------------------------------

    _DISALLOWED_CTA = "CALL_NOW"
    """Known CTA not allowed by any of ``_STANDARD_SUPPORTED_COMBINATIONS``."""

    @staticmethod
    def _allowed_cta(combo):
        """Deterministic allowed CTA for ``combo``."""
        return sorted(MetaAdsValidator.get_allowed_ctas_for_goal(*combo))[0]

    @staticmethod
    def _cta_errors_for_ad(results):
        ad_entries = [r for r in results if r.get("ad_name") == "Ad non-dict CTA"]
        assert len(ad_entries) == 1
        return [
            e for e in ad_entries[0].get("errors") or [] if e.get("slug") == "cta-error"
        ]

    @pytest.mark.parametrize(
        "combo", STANDARD_SUPPORTED_COMBINATIONS, ids=STANDARD_SUPPORTED_COMBINATIONS_IDS
    )
    def test_disallowed_cta_with_input_valid_true_is_rejected(self, use_case_factory, combo):
        """Req 14.16, 14.18, 14.19: a disallowed CTA with input
        ``type.valid=True`` ends up ``False`` at both levels, with exactly
        one ``cta-error`` and ``call_to_action_types_valid_amount False``."""
        objective, optimization_goal = combo
        assert self._DISALLOWED_CTA not in MetaAdsValidator.get_allowed_ctas_for_goal(*combo)
        call_to_action = make_standard_cta(self._DISALLOWED_CTA, valid=True)

        response, status_code, results, link_data = TestStandardNonDictCtaGuard._run(
            use_case_factory, objective, optimization_goal, call_to_action
        )

        assert status_code == 200
        result_cta = link_data["call_to_action"]
        assert result_cta["type"]["value"] == self._DISALLOWED_CTA
        assert result_cta["type"]["valid"] is False
        assert result_cta["valid"] is result_cta["type"]["valid"]
        cta_errors = self._cta_errors_for_ad(results)
        assert len(cta_errors) == 1
        assert self._DISALLOWED_CTA in cta_errors[0]["message"]
        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["call_to_action_types_valid_amount"] is False

    @pytest.mark.parametrize(
        "combo", STANDARD_SUPPORTED_COMBINATIONS, ids=STANDARD_SUPPORTED_COMBINATIONS_IDS
    )
    def test_allowed_cta_without_input_valid_is_accepted(self, use_case_factory, combo):
        """Req 14.17, 14.18, 14.19: an allowed CTA whose ``type`` has no
        ``valid`` key ends up ``True`` at both levels, with no ``cta-error``
        and ``call_to_action_types_valid_amount True``."""
        objective, optimization_goal = combo
        allowed_cta = self._allowed_cta(combo)
        call_to_action = make_standard_cta(allowed_cta)
        assert "valid" not in call_to_action["type"]

        response, status_code, results, link_data = TestStandardNonDictCtaGuard._run(
            use_case_factory, objective, optimization_goal, call_to_action
        )

        assert status_code == 200
        result_cta = link_data["call_to_action"]
        assert result_cta["type"]["value"] == allowed_cta
        assert result_cta["type"]["valid"] is True
        assert result_cta["valid"] is result_cta["type"]["valid"]
        assert self._cta_errors_for_ad(results) == []
        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["call_to_action_types_valid_amount"] is True

    @pytest.mark.parametrize(
        "call_to_action, expected_type",
        [
            ({"valid": True}, {"value": None, "valid": False}),
            ({"type": "LEARN_MORE"}, {"value": "LEARN_MORE", "valid": False}),
        ],
        ids=["type-absent", "type-str"],
    )
    @pytest.mark.parametrize(
        "combo", STANDARD_SUPPORTED_COMBINATIONS, ids=STANDARD_SUPPORTED_COMBINATIONS_IDS
    )
    def test_cta_without_dict_type_is_normalized(
        self, use_case_factory, combo, call_to_action, expected_type
    ):
        """Req 14.20, 15.3: a non-empty ``call_to_action`` whose ``type`` is
        absent or a string is normalized to
        ``{'value': <original or None>, 'valid': False}`` with root
        ``valid=False`` and one ``cta-error``, without raising -- both via
        direct ``_validate_standard_cta`` and through ``execute()``."""
        objective, optimization_goal = combo

        # Direct call.
        use_case, _, _ = use_case_factory(
            creative_type="STANDARD",
            complete_campaign_data=make_campaign_data_dict(
                objective=objective, optimization_goal=optimization_goal
            ),
        )
        direct_cta = dict(call_to_action)
        link_data = make_link_data(call_to_action=direct_cta)
        current_ad_errors = []
        use_case._validate_standard_cta(link_data, current_ad_errors)
        assert link_data["call_to_action"]["type"] == expected_type
        assert link_data["call_to_action"]["valid"] is False
        assert len(current_ad_errors) == 1
        assert current_ad_errors[0]["slug"] == "cta-error"

        # Full execute() harness.
        response, status_code, results, exec_link_data = TestStandardNonDictCtaGuard._run(
            use_case_factory, objective, optimization_goal, dict(call_to_action)
        )
        assert status_code == 200
        assert exec_link_data["call_to_action"]["type"] == expected_type
        assert exec_link_data["call_to_action"]["valid"] is False
        assert len(self._cta_errors_for_ad(results)) == 1
        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert creatives[0]["call_to_action_types_valid_amount"] is False


class TestOtherCombinationsPreCheckRegression:
    """Task 11.2 (meta-ads-leads-offsite-conversions): regression of the
    PreCheck for Otras_Combinaciones (every supported pair except
    ``OUTCOME_LEADS``/``OFFSITE_CONVERSIONS``).

    - STANDARD keeps ``promoted_object_valid is False`` (Req 8.6).
    - DYNAMIC keeps the existing SALES logic over
      ``MetaAdsValidator.validate_promoted_object`` (Req 8.6, 13.1).
    - The response is identical with and without ``conversion_event`` and
      ``meta_conversion_event`` is never persisted (Req 13.4).
    - The existing DYNAMIC URL block is unchanged, including the
      ``assets-budget-error`` slug for ``website_url=None`` (Req 13.1);
      ``proposal_url`` skips ``None`` values so ``execute()`` no longer
      raises ``TypeError`` (Req 16.4-16.5).

    Requirements: 8.6, 13.1, 13.4, 16.4, 16.5
    """

    _VALIDATOR = "app.v2.use_cases.meta_ads.MetaAdsValidator"
    _SALES_PAIR = (
        CampaignObjective.SALES.value,
        SalesOptimizationGoal.OFFSITE_CONVERSIONS.value,
    )
    _NON_SALES_DYNAMIC_PAIRS = [
        pair
        for pair in _OTHER_COMBINATIONS_BY_BRANCH["DYNAMIC"]
        if pair[0] != CampaignObjective.SALES.value
    ]

    @classmethod
    def _run_dynamic(
        cls,
        use_case_factory,
        objective,
        optimization_goal,
        event=ABSENT,
        promoted_object=ABSENT,
        link_urls=None,
        validate_promoted_object_kwargs=None,
    ):
        """Drive a full DYNAMIC ``execute()`` for an Otras_Combinaciones
        pair. ``validate_promoted_object`` wraps the real implementation
        unless ``validate_promoted_object_kwargs`` overrides it. The
        ``current_ad_errors`` list of the ``execute()`` frame is captured
        from the ``is_valid_amount`` call (same frame, right before the URL
        block). ``execute()`` exceptions are returned, not raised.

        Returns ``(outcome, asset_feed, ad_set, captured_errors, spy, publish_repo)``.
        """
        import inspect

        data = TestLeadsOffsiteOtherCombinationsIgnoreEvent._make_campaign_data(
            objective, optimization_goal, event
        )
        use_case, _, publish_repo = use_case_factory(
            complete_campaign_data=data, creative_type="DYNAMIC"
        )
        asset_feed = make_asset_feed_spec(
            images=[{"url": "https://example.com/imagen.jpg"}],
            link_urls=(
                [{"website_url": "https://example.com/destino"}]
                if link_urls is None
                else [dict(e) for e in link_urls]
            ),
        )
        ad_set_kwargs = {} if promoted_object is ABSENT else {"promoted_object": promoted_object}
        ad_set = make_ad_set(
            ads=[make_ad(ad_creative=make_ad_creative(asset_feed_spec=asset_feed))],
            **ad_set_kwargs,
        )
        payload = make_meta_payload(ad_sets=[ad_set])

        captured_errors = []

        def _capturing_is_valid_amount(*args, **kwargs):
            frame = inspect.currentframe().f_back
            while frame is not None:
                if frame.f_code.co_name == "execute" and "current_ad_errors" in frame.f_locals:
                    captured_errors.append(frame.f_locals["current_ad_errors"])
                    break
                frame = frame.f_back
            return None

        promoted_kwargs = validate_promoted_object_kwargs or {
            "wraps": MetaAdsValidator.validate_promoted_object
        }
        v = cls._VALIDATOR
        with patch(f"{v}.validate_images_precheck", return_value=None), patch(
            f"{v}.is_valid_link_url", return_value=True
        ), patch(f"{v}.is_valid_length", return_value=None), patch(
            f"{v}.validate_cta_for_goal", return_value=True
        ), patch(f"{v}.is_unique_texts", return_value=True), patch(
            f"{v}.is_valid_amount", side_effect=_capturing_is_valid_amount
        ), patch(
            f"{v}.validate_promoted_object", **promoted_kwargs
        ) as spy, patch_execute_dependencies() as deps:
            deps.redis_client.get.return_value = b"token"
            builder = deps.MetaAdsPayloadBuilder.return_value
            builder.build_meta_payload.return_value = payload
            builder.get_channel_id.return_value = "channel-1"
            builder.get_billing_event.return_value = "IMPRESSIONS"
            deps.FacebookGetAdAccountDetailsUseCase.return_value.execute.return_value = (
                make_ad_account_info(),
                200,
            )
            deps.FacebookMinimumBudgetUseCase.return_value.execute.return_value = (
                make_minimum_budget_response(),
                200,
            )
            try:
                outcome = use_case.execute()
            except Exception as exc:  # noqa: BLE001 - returned for assertions
                outcome = exc
        return outcome, asset_feed, ad_set, captured_errors, spy, publish_repo

    @staticmethod
    def _slugs(captured_errors):
        assert len(captured_errors) == 1, "current_ad_errors of execute() not captured"
        return [e.get("slug") for e in captured_errors[0]]

    # ------------------------------------------------------------------
    # STANDARD: promoted_object_valid stays False (Req 8.6).
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("event", [ABSENT, "LEAD", "PURCHASE"], ids=["absent", "lead", "purchase"])
    @pytest.mark.parametrize("objective, optimization_goal", _OTHER_COMBINATIONS_BY_BRANCH["STANDARD"])
    def test_standard_other_combinations_promoted_object_valid_is_false(
        self, use_case_factory, objective, optimization_goal, event
    ):
        """Requirements: 8.6, 13.1, 13.4"""
        (response, status_code), _, publish_repo = TestLeadsOffsiteOtherCombinationsIgnoreEvent._run(
            use_case_factory, "STANDARD", objective, optimization_goal, event
        )

        assert status_code == 200
        creatives = response["data"]["creatives"]
        assert len(creatives) == 1
        assert all(c["promoted_object_valid"] is False for c in creatives)
        assert response["data"]["valid_ctas"] == list(
            MetaAdsValidator.get_allowed_ctas_for_goal(objective=objective, goal=optimization_goal)
        )
        _, persisted = publish_repo.save_or_update.call_args.args
        assert "meta_conversion_event" not in persisted

    # ------------------------------------------------------------------
    # DYNAMIC: SALES logic of validate_promoted_object (Req 8.6, 13.1).
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("event", [ABSENT, "LEAD"], ids=["absent", "lead"])
    @pytest.mark.parametrize("objective, optimization_goal", _NON_SALES_DYNAMIC_PAIRS)
    def test_dynamic_non_sales_promoted_object_valid_true_without_validator(
        self, use_case_factory, objective, optimization_goal, event
    ):
        """Requirements: 8.6, 13.1"""
        outcome, asset_feed, _, captured_errors, spy, _ = self._run_dynamic(
            use_case_factory, objective, optimization_goal, event=event
        )

        response, status_code = outcome
        assert status_code == 200
        spy.assert_not_called()
        assert asset_feed["promoted_object_valid"] is True
        assert response["data"]["creatives"][0]["promoted_object_valid"] is True
        assert "promoted-object-error" not in self._slugs(captured_errors)

    @pytest.mark.parametrize("event", [ABSENT, "LEAD"], ids=["absent", "lead"])
    def test_dynamic_sales_valid_promoted_object_is_normalized_and_true(
        self, use_case_factory, event
    ):
        """Requirements: 8.6, 13.1"""
        objective, optimization_goal = self._SALES_PAIR
        outcome, asset_feed, ad_set, captured_errors, spy, _ = self._run_dynamic(
            use_case_factory, objective, optimization_goal, event=event
        )

        response, status_code = outcome
        assert status_code == 200
        spy.assert_called_once()
        assert spy.call_args.args[1:] == (objective, optimization_goal, "pixel-1")
        assert spy.call_args.kwargs == {"throw": False}
        assert ad_set["promoted_object"] == {"pixel_id": "pixel-1", "custom_event_type": "PURCHASE"}
        assert asset_feed["promoted_object_valid"] is True
        assert response["data"]["creatives"][0]["promoted_object_valid"] is True
        assert "promoted-object-error" not in self._slugs(captured_errors)

    @pytest.mark.parametrize("event", [ABSENT, "LEAD"], ids=["absent", "lead"])
    def test_dynamic_sales_invalid_custom_event_marks_false_with_error(
        self, use_case_factory, event
    ):
        """Requirements: 8.6, 13.1"""
        objective, optimization_goal = self._SALES_PAIR
        outcome, asset_feed, ad_set, captured_errors, spy, _ = self._run_dynamic(
            use_case_factory,
            objective,
            optimization_goal,
            event=event,
            promoted_object={"custom_event_type": "FOO"},
        )

        response, status_code = outcome
        assert status_code == 200
        spy.assert_called_once()
        assert asset_feed["promoted_object_valid"] is False
        assert response["data"]["creatives"][0]["promoted_object_valid"] is False
        assert self._slugs(captured_errors).count("promoted-object-error") == 1
        # Invalid promoted_object is not written back as normalized PURCHASE.
        assert ad_set["promoted_object"]["custom_event_type"] == "FOO"

    def test_dynamic_sales_validator_value_error_marks_false_with_message(self, use_case_factory):
        """Requirements: 8.6, 13.1"""
        objective, optimization_goal = self._SALES_PAIR
        outcome, asset_feed, _, captured_errors, spy, _ = self._run_dynamic(
            use_case_factory,
            objective,
            optimization_goal,
            validate_promoted_object_kwargs={"side_effect": ValueError("boom")},
        )

        response, status_code = outcome
        assert status_code == 200
        spy.assert_called_once()
        assert asset_feed["promoted_object_valid"] is False
        assert response["data"]["creatives"][0]["promoted_object_valid"] is False
        errors = [e for e in captured_errors[0] if e.get("slug") == "promoted-object-error"]
        assert [e["message"] for e in errors] == ["boom"]

    # ------------------------------------------------------------------
    # Identical response with and without conversion_event (Req 13.4).
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("event", ["LEAD", "PURCHASE", "", None], ids=["lead", "purchase", "empty", "none"])
    @pytest.mark.parametrize(
        "creative_type, objective, optimization_goal",
        [
            (branch, objective, goal)
            for branch, pairs in sorted(_OTHER_COMBINATIONS_BY_BRANCH.items())
            for objective, goal in pairs
        ],
    )
    def test_response_identical_with_and_without_conversion_event(
        self, use_case_factory, creative_type, objective, optimization_goal, event
    ):
        """Requirements: 8.6, 13.1, 13.4"""
        run = TestLeadsOffsiteOtherCombinationsIgnoreEvent._run
        result, _, publish_repo = run(
            use_case_factory, creative_type, objective, optimization_goal, event
        )
        baseline, _, base_publish_repo = run(
            use_case_factory, creative_type, objective, optimization_goal, ABSENT
        )

        assert result == baseline
        _, persisted = publish_repo.save_or_update.call_args.args
        assert "meta_conversion_event" not in persisted
        assert (
            publish_repo.save_or_update.call_args_list
            == base_publish_repo.save_or_update.call_args_list
        )

    def test_dynamic_sales_invalid_promoted_object_identical_with_and_without_event(
        self, use_case_factory
    ):
        """Requirements: 8.6, 13.4"""
        objective, optimization_goal = self._SALES_PAIR
        with_event = self._run_dynamic(
            use_case_factory, objective, optimization_goal, event="LEAD",
            promoted_object={"custom_event_type": "FOO"},
        )
        without_event = self._run_dynamic(
            use_case_factory, objective, optimization_goal, event=ABSENT,
            promoted_object={"custom_event_type": "FOO"},
        )

        assert with_event[0] == without_event[0]
        assert with_event[0][0]["data"]["creatives"][0]["promoted_object_valid"] is False
        assert self._slugs(with_event[3]) == self._slugs(without_event[3])

    # ------------------------------------------------------------------
    # Existing DYNAMIC URL block unchanged (Req 13.1).
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("objective, optimization_goal", _OTHER_COMBINATIONS_BY_BRANCH["DYNAMIC"])
    def test_dynamic_website_url_none_keeps_assets_budget_error_slug(
        self, use_case_factory, objective, optimization_goal
    ):
        """Requirements: 7.6, 13.1, 16.4, 16.5

        ``','.join`` over ``[None]`` fails inside the existing (unchanged)
        URL block, so it records the pre-existing ``assets-budget-error``
        slug, no ``url-error``, and never sets ``link_url_valid``. Since the
        follow-up (Req 16.4-16.5), ``_build_dynamic_creative_entry`` skips
        ``None`` values when joining ``proposal_url``, so ``execute()``
        returns status 200 with ``proposal_url == ''`` instead of raising
        ``TypeError``.
        """
        outcome, asset_feed, _, captured_errors, _, _ = self._run_dynamic(
            use_case_factory, objective, optimization_goal, link_urls=[{"website_url": None}]
        )

        assert not isinstance(outcome, Exception), repr(outcome)
        response, status_code = outcome
        assert status_code == 200
        slugs = self._slugs(captured_errors)
        assert slugs.count("assets-budget-error") == 1
        assert "url-error" not in slugs
        assert "link_url_valid" not in asset_feed
        proposal_url = response["data"]["creatives"][0]["proposal_url"]
        assert proposal_url == ""
        assert "None" not in proposal_url

    @pytest.mark.parametrize("objective, optimization_goal", _OTHER_COMBINATIONS_BY_BRANCH["DYNAMIC"])
    def test_dynamic_mixed_none_and_url_joins_only_non_none(
        self, use_case_factory, objective, optimization_goal
    ):
        """Requirements: 7.6, 13.1, 16.4, 16.5

        With one ``None`` entry and one string URL, ``execute()`` does not
        raise and ``proposal_url`` contains only the string URL.
        """
        outcome, _, _, captured_errors, _, _ = self._run_dynamic(
            use_case_factory,
            objective,
            optimization_goal,
            link_urls=[{"website_url": None}, {"website_url": "https://example.com/destino"}],
        )

        assert not isinstance(outcome, Exception), repr(outcome)
        response, status_code = outcome
        assert status_code == 200
        assert "url-error" not in self._slugs(captured_errors)
        assert response["data"]["creatives"][0]["proposal_url"] == "https://example.com/destino"
