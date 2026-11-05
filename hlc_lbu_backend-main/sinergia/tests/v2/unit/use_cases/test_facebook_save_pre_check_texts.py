"""Characterization test suite for ``FacebookSavePreCheckTextsUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookSavePreCheckTextsUseCase``
and the inherited subset of ``FacebookSavePreCheckBaseUseCase`` that it
invokes: the constructor, ``_get_ad_channel``, ``_get_campaign_setup``,
``_set_channel_id`` and ``_build_response``. ``FacebookSavePreCheckBaseUseCase``
in turn inherits from ``FacebookGeneratePreCheckCreativeUseCase`` (covered by
its own suite in the ``facebook-generate-pre-check-creative-tests`` spec) and,
transitively, from ``FacebookTestCreativeUploadUseCase``.

This module fixes the current observable behaviour, including already
existing quirks (the always-``{}`` ``complete_campaign_data`` passed to the
grandparent constructor, the mutable default ``pre_check_data: PreCheckDataDict
= {}`` in the constructor signature, the asymmetric ``.get(..., {})``/``.get(...)``
usages between ``execute()``, ``_save_creative_to_publish`` and
``_build_response``, and the transparent ``try/except Exception as e: raise e``
pass-through). Unlike its sibling ``FacebookSavePreCheckImagesUseCase``, this
class has no ``_validate_texts_dynamic``/``_validate_texts_standard`` methods
of its own: all of the DYNAMIC-branch text validation logic lives inline
inside ``execute()``, and the STANDARD branch is an explicit ``pass``. No
production code is modified or "fixed" by this suite.

Requirements: 18.2, 18.3
"""

import copy
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import pytest
from hypothesis import given, settings, strategies as st

from app.exceptions.base import DataNotFoundException, NotAccessException
from app.v2.use_cases.facebook_validator_service import CreativeType, MetaAdsValidator
from app.v2.use_cases.meta_ads import (
    FacebookSavePreCheckBaseUseCase,
    FacebookSavePreCheckTextsUseCase,
)


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it from the resulting dict" from "this key
    was provided by the caller with the value ``None``".

    Requirements: 18.2, 18.3
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


def make_pre_check_texts_data(**overrides):
    """Build a fresh ``pre_check_texts_data`` (``PreCheckDataDict``-like) dict.

    Every invocation returns a brand new dict, with brand new list objects
    for every collection field; no mutable default arguments are used, so
    callers can freely mutate the returned value (or its nested lists)
    without affecting other tests.

    Requirements: 18.2, 18.3
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


def make_text_entry(text="Sample text", **overrides):
    """Build a fresh text entry dict of the form ``{"text": ...}``.

    Pass ``text=None``/``text=""`` explicitly, or omit ``text`` via a
    ``{"text": ABSENT}``-style override handled by the caller, to
    characterize the uniqueness/length scenarios that must tolerate empty
    values without raising.

    Requirements: 18.2, 18.3
    """
    data = {"text": text}
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
    to exercise each absence level of Requirement 5.2 individually.

    Requirements: 18.2, 18.3
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
    to characterize the unknown-mode scenarios of Requirement 13.
    ``**overrides`` are merged into the top-level dict.

    Requirements: 18.2, 18.3
    """
    data = {"attributes": {"meta_campaign_mode": meta_campaign_mode}}
    data.update(overrides)
    return data


def make_asset_feed_spec(**overrides):
    """Build a fresh ``asset_feed_spec`` dict with empty collections.

    Requirements: 18.2, 18.3
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

    Empty by default; the STANDARD branch is an explicit ``pass`` (no
    method of its own is invoked), so this builder only needs to produce a
    fresh, freely-mutable dict for asserting it stays untouched.

    Requirements: 18.2, 18.3
    """
    data = {}
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict (``object_story_spec['link_data']``).

    Every field the STANDARD branch reads/writes (``name``, ``message``,
    ``description``, ``image_url``, ``link``, ``call_to_action``) defaults
    to ``None``, so a scenario can override only the field(s) it cares
    about while still asserting that the rest were left untouched by the
    Rama_STANDARD logic under test.

    Requirements: 8.1
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
    from "key present with value ``None``" (Requirements 11.3 vs 11.1, and
    14.2 vs 14.4).

    Requirements: 18.2, 18.3
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

    Requirements: 18.2, 18.3
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
    characterize the empty-``ads`` scenario of Requirement 14.1.
    ``proposal_locations`` defaults to the ``ABSENT`` sentinel: when left
    untouched, the key is omitted entirely, matching the
    ``creative.get('proposal_locations', [])`` default in ``_build_response``.

    Requirements: 18.2, 18.3
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
    """Fixture that builds a factory for ``FacebookSavePreCheckTextsUseCase``
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

    If ``pre_check_texts_data`` is omitted, a fresh
    ``make_pre_check_texts_data()`` is used so the ``AttributeError``
    characterized in Requirement 2.9, and the mutable-default scenario of
    Requirement 2.10, are not accidentally triggered here; the dedicated
    tests for those criteria construct the use case directly, without this
    fixture.

    Requirements: 1.2
    """

    def _factory(user_id="user-1", pre_check_texts_data=None):
        if pre_check_texts_data is None:
            pre_check_texts_data = make_pre_check_texts_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookSavePreCheckTextsUseCase(
                user_id, pre_check_texts_data
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
    scenarios that verify the short-circuit on a missing token
    (Requirement 6.2).

    Requirements: 1.3
    """
    with patch("app.v2.use_cases.meta_ads.redis_client") as mock_redis_client:
        yield mock_redis_client


@contextmanager
def patch_text_validators():
    """Context manager that patches
    ``app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts``,
    ``.is_valid_length`` and ``.is_valid_texts_amount`` with doubles that
    delegate to the real implementation (``unittest.mock.Mock(wraps=...)``),
    so the real logic and its side effects (in-place mutation performed by
    ``is_valid_length``, real return values) keep running exactly as in
    production, while each double also records its own invocation.

    All three doubles append to a single shared ``call_order`` list, one
    ``(method_name, args)`` tuple per invocation, in the exact order the
    calls happen. This lets a scenario assert the precise interleaved
    sequence of the 9 calls spread across ``titles``/``bodies``/
    ``descriptions`` (Requirement 10.1), which a plain ``assert_called_*``
    on three independent mocks could not distinguish from an incorrect
    order.

    Yields the shared ``call_order`` list. Used only by the Requirement
    10.1 tests; every other DYNAMIC-branch scenario (Requirements 7-9)
    exercises ``execute()`` with the fully real, unpatched validators and
    only asserts on the observable result (mutations of
    ``asset_feed``/``self.titles``/``self.bodies``/``self.descriptions``).

    Requirements: 1.4
    """
    real_is_unique_texts = MetaAdsValidator.is_unique_texts
    real_is_valid_length = MetaAdsValidator.is_valid_length
    real_is_valid_texts_amount = MetaAdsValidator.is_valid_texts_amount

    call_order = []

    def _recording_is_unique_texts(texts):
        call_order.append(("is_unique_texts", (texts,)))
        return real_is_unique_texts(texts)

    def _recording_is_valid_length(type_, texts):
        call_order.append(("is_valid_length", (type_, texts)))
        return real_is_valid_length(type_, texts)

    def _recording_is_valid_texts_amount(type_, texts):
        call_order.append(("is_valid_texts_amount", (type_, texts)))
        return real_is_valid_texts_amount(type_, texts)

    mock_is_unique_texts = Mock(wraps=_recording_is_unique_texts)
    mock_is_valid_length = Mock(wraps=_recording_is_valid_length)
    mock_is_valid_texts_amount = Mock(wraps=_recording_is_valid_texts_amount)

    with patch.object(
        MetaAdsValidator, "is_unique_texts", staticmethod(mock_is_unique_texts)
    ), patch.object(
        MetaAdsValidator, "is_valid_length", staticmethod(mock_is_valid_length)
    ), patch.object(
        MetaAdsValidator,
        "is_valid_texts_amount",
        staticmethod(mock_is_valid_texts_amount),
    ):
        yield call_order


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Local, module-scoped guard (not a global ``conftest.py`` fixture),
    ``autouse=True`` at function scope, that replaces
    ``requests.sessions.Session.request`` with a function that fails
    immediately.

    This is additional defense even though no code path reachable by
    ``FacebookSavePreCheckTextsUseCase`` performs any network request:
    ``MetaAdsValidator.is_unique_texts``, ``.is_valid_length`` and
    ``.is_valid_texts_amount`` are pure, in-memory functions. Its inclusion
    keeps this suite consistent in style with its sibling
    ``test_facebook_save_pre_check_images.py`` and protects against a
    future regression that accidentally introduced a network call in this
    file.

    Requirements: 1.5
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr(
        "requests.sessions.Session.request", _raise_on_network_access
    )


def assert_exception_type_and_message(exc_info, expected_type, expected_message):
    """Assert that the exception captured by ``pytest.raises`` (via its
    ``exc_info``) has exactly ``expected_type`` (not a subclass) and that
    ``str(exc_info.value) == expected_message``.

    Used uniformly for ``_get_ad_channel``, ``_get_campaign_setup``, the
    ``try/except`` pass-through (Requirement 15), and the malformed
    ``creative``/``ads`` structures (Requirement 14).

    Requirements: 1.6
    """
    assert type(exc_info.value) is expected_type, (
        f"expected exception type {expected_type!r}, "
        f"got {type(exc_info.value)!r}"
    )
    assert str(exc_info.value) == expected_message, (
        f"expected exception message {expected_message!r}, "
        f"got {str(exc_info.value)!r}"
    )


def assert_repository_called_once_with(mock_method, *args):
    """Thin wrapper over ``assert_called_once_with`` with an explicit
    diagnostic message, used for
    ``get_by_campaign_and_ad_channel_id``, ``get_by_campaign_id_and_channel_id``
    and ``update``.

    Requirements: 1.6
    """
    try:
        mock_method.assert_called_once_with(*args)
    except AssertionError as exc:
        raise AssertionError(
            f"expected {mock_method} to be called once with {args!r}: {exc}"
        ) from exc


def assert_no_text_validator_calls(
    mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
):
    """Assert that none of the three ``MetaAdsValidator`` text-validation
    methods used by this class (``is_unique_texts``, ``is_valid_length``,
    ``is_valid_texts_amount``) were invoked.

    Used in Requirements 3.4, 4.4, 11, 12.1/12.3 and 13.

    Requirements: 1.6
    """
    mock_is_unique_texts.assert_not_called()
    mock_is_valid_length.assert_not_called()
    mock_is_valid_texts_amount.assert_not_called()


def test_smoke_use_case_construction_and_exception_capture_need_no_flask_context(
    use_case_factory,
):
    """Smoke test for Requirement 1.6: building the use case with
    ``use_case_factory`` and capturing ``DataNotFoundException``/
    ``NotAccessException`` (both raised in the production code under test
    with an explicit ``text`` argument) works as a pure unit test, with no
    Flask application/request context and no ``tests/conftest.py``.

    If this assumption turned out to be false (for example, if
    ``flask_babel.gettext`` were reached and raised outside of an
    application context), the implementation of this task would have to
    stop and report the problem instead of adding Flask app/context
    infrastructure or a ``tests/conftest.py`` file; running this test green
    is exactly what confirms that stop condition was never reached.

    Requirements: 1.6
    """
    use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
        use_case_factory()
    )

    assert mock_ad_channel_repo_instance is use_case.ad_channel_repository
    assert mock_campaign_publish_repo_instance is use_case.campaign_publish_repository

    mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = None
    with pytest.raises(DataNotFoundException) as exc_info:
        use_case._get_ad_channel()
    assert exc_info.value.text == "Creative not found!"

    with patch_redis_client() as mock_redis_client:
        mock_redis_client.get.return_value = None
        with pytest.raises(NotAccessException) as exc_info:
            use_case._get_decoded_access_token()
    assert exc_info.value.text == (
        "No access token found in Redis. Please re-authenticate."
    )


class TestConstructorAndInheritedState:
    """Tests for the ``FacebookSavePreCheckTextsUseCase``/
    ``FacebookSavePreCheckBaseUseCase`` constructor chain and the state it
    establishes.

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
    """

    def test_own_attributes_assigned_exactly_from_complete_pre_check_data(
        self, use_case_factory
    ):
        """With complete ``pre_check_texts_data``, ``adset_id``, ``ad_id``,
        ``adchannel_id``, ``images``, ``bodies``, ``titles``,
        ``descriptions``, ``call_to_action_types`` and ``locations`` are
        assigned exactly from the provided data (by identity for the
        list-valued fields).

        Requirements: 2.1
        """
        images = [make_text_entry()]
        bodies = [make_text_entry("body-1")]
        titles = [make_text_entry("title-1")]
        descriptions = [make_text_entry("description-1")]
        call_to_action_types = ["SHOP_NOW"]
        locations = ["location-1"]
        pre_check_texts_data = make_pre_check_texts_data(
            adset_id="adset-42",
            ad_id="ad-42",
            adchannel_id="adchannel-42",
            images=images,
            bodies=bodies,
            titles=titles,
            descriptions=descriptions,
            call_to_action_types=call_to_action_types,
            locations=locations,
        )

        use_case, _, _ = use_case_factory(pre_check_texts_data=pre_check_texts_data)

        assert use_case.adset_id == "adset-42"
        assert use_case.ad_id == "ad-42"
        assert use_case.adchannel_id == "adchannel-42"
        assert use_case.images is images
        assert use_case.bodies is bodies
        assert use_case.titles is titles
        assert use_case.descriptions is descriptions
        assert use_case.call_to_action_types is call_to_action_types
        assert use_case.locations is locations

    def test_daily_budget_and_proposal_url_default_when_omitted(self, use_case_factory):
        """When ``daily_budget``/``proposal_url`` are omitted from
        ``pre_check_texts_data``, they default to ``0``/``''``.

        Requirements: 2.2, 2.3
        """
        pre_check_texts_data = make_pre_check_texts_data()
        del pre_check_texts_data["daily_budget"]
        del pre_check_texts_data["proposal_url"]

        use_case, _, _ = use_case_factory(pre_check_texts_data=pre_check_texts_data)

        assert use_case.daily_budget == 0
        assert use_case.proposal_url == ""

    @pytest.mark.parametrize(
        "field_name",
        [
            "images",
            "bodies",
            "titles",
            "descriptions",
            "call_to_action_types",
            "locations",
        ],
    )
    def test_collection_fields_default_to_fresh_empty_list_when_omitted(
        self, use_case_factory, field_name
    ):
        """When ``images``/``bodies``/``titles``/``descriptions``/
        ``call_to_action_types``/``locations`` are omitted from
        ``pre_check_texts_data``, the corresponding attribute is
        initialized to a brand new empty list: two separate instances built
        from an equivalent, independent dict each get their own list
        object, not a shared one.

        Requirements: 2.4
        """
        first_data = make_pre_check_texts_data()
        del first_data[field_name]
        second_data = make_pre_check_texts_data()
        del second_data[field_name]

        first_use_case, _, _ = use_case_factory(pre_check_texts_data=first_data)
        second_use_case, _, _ = use_case_factory(pre_check_texts_data=second_data)

        first_value = getattr(first_use_case, field_name)
        second_value = getattr(second_use_case, field_name)
        assert first_value == []
        assert second_value == []
        assert first_value is not second_value

    def test_campaign_id_and_user_id_propagated_to_great_grandparent(
        self, use_case_factory
    ):
        """``campaign_id`` is taken from
        ``pre_check_texts_data.get('campaign_id')`` and ``user_id`` is
        taken from the constructor's ``user_id`` argument; both are
        propagated correctly through ``FacebookSavePreCheckBaseUseCase``
        down to the ``self.campaign_id``/``self.user_id`` assignments made
        by the Caso_de_Uso_Bisabuelo (``FacebookTestCreativeUploadUseCase``).

        Requirements: 2.5
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-99")

        use_case, _, _ = use_case_factory(
            user_id="user-99", pre_check_texts_data=pre_check_texts_data
        )

        assert use_case.campaign_id == "campaign-99"
        assert use_case.user_id == "user-99"

    def test_complete_campaign_data_derived_attributes_are_none_without_exception(
        self, use_case_factory
    ):
        """``ad_account_id``, ``page_id``, ``objective``,
        ``optimization_goal``, ``lead_gen_form_id``, ``whatsapp_number_id``,
        ``billing_event`` and ``channel_id`` are all ``None`` after
        construction, and construction itself raises no exception,
        characterizing Datos_de_Campaña_Vacíos: ``complete_campaign_data={}``
        is always passed to the Caso_de_Uso_Bisabuelo regardless of
        ``pre_check_texts_data`` content -- including when
        ``pre_check_texts_data`` happens to carry keys with the same
        names, which are simply ignored by the parent constructor because
        it never reads them from ``pre_check_data``.

        Requirements: 2.6, 2.7
        """
        pre_check_texts_data = make_pre_check_texts_data(
            ad_account_id="should-be-ignored",
            page_id="should-be-ignored",
            objective="should-be-ignored",
        )

        use_case, _, _ = use_case_factory(pre_check_texts_data=pre_check_texts_data)

        assert use_case.ad_account_id is None
        assert use_case.page_id is None
        assert use_case.objective is None
        assert use_case.optimization_goal is None
        assert use_case.lead_gen_form_id is None
        assert use_case.whatsapp_number_id is None
        assert use_case.billing_event is None
        assert use_case.channel_id is None

    def test_repositories_instantiated_exactly_once_each(self):
        """The patched ``AdChannelRepository``/``CampaignChannelPublishRepository``
        classes are each instantiated exactly once during construction of
        ``FacebookSavePreCheckTextsUseCase`` (inherited from the
        Caso_de_Uso_Abuelo's constructor).

        Patches the two repository classes inline (not via
        ``use_case_factory``) to keep access to the mocked classes
        themselves, which is what ``assert_called_once_with`` needs to
        verify instantiation count.

        Requirements: 2.8
        """
        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            FacebookSavePreCheckTextsUseCase("user-1", make_pre_check_texts_data())

            mock_ad_channel_repository_cls.assert_called_once_with()
            mock_campaign_publish_repository_cls.assert_called_once_with()


class TestConstructorExplicitNoneAndMutableDefault:
    """Tests for the explicit-``None`` ``AttributeError`` and for the
    mutable default argument of ``FacebookSavePreCheckBaseUseCase.__init__``.

    Both tests construct the use case(s) directly, without the
    ``use_case_factory`` fixture, patching
    ``app.v2.use_cases.meta_ads.AdChannelRepository``/
    ``CampaignChannelPublishRepository`` inline instead: the fixture always
    substitutes a fresh, explicit ``make_pre_check_texts_data()`` when the
    caller omits ``pre_check_texts_data``, which would silently mask both
    scenarios below.

    Requirements: 2.9, 2.10
    """

    def test_explicit_none_pre_check_texts_data_raises_attribute_error(self):
        """Passing ``pre_check_texts_data=None`` explicitly (as opposed to
        omitting the argument) is not protected by the mutable default
        ``pre_check_data: PreCheckDataDict = {}`` in
        ``FacebookSavePreCheckBaseUseCase.__init__``: ``super().__init__``
        immediately calls ``pre_check_data.get('campaign_id')``, i.e.
        ``None.get('campaign_id')``, which raises ``AttributeError``. This
        happens before either repository is instantiated, so the patches
        below are precautionary/for consistency with the other
        constructor tests rather than strictly required to avoid a real
        ``StrapiClient``.

        Requirements: 2.9
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            with pytest.raises(AttributeError) as exc_info:
                FacebookSavePreCheckTextsUseCase("user-1", None)

        assert "NoneType" in str(exc_info.value)
        assert "get" in str(exc_info.value)

    def test_omitting_pre_check_data_twice_does_not_share_titles_between_instances(
        self,
    ):
        """Constructs two ``FacebookSavePreCheckBaseUseCase`` instances back
        to back, omitting ``pre_check_data`` in both invocations (so both
        calls bind the same shared default dict object, the literal ``{}``
        in the signature), mutates ``titles`` of the first instance, and
        checks whether the second instance reflects that mutation.

        OBSERVED BEHAVIOR (documented, not "fixed"): the default argument
        ``pre_check_data: PreCheckDataDict = {}`` is a single dict object
        shared across every call that omits the argument (the classic
        mutable-default-argument pitfall; confirmed independently below by
        inspecting ``FacebookSavePreCheckBaseUseCase.__init__.__defaults__``).
        However, the constructor never writes back into ``pre_check_data``
        itself; it only reads from it via ``pre_check_data.get('titles', [])``.
        Since the key ``'titles'`` is never present in that shared empty
        dict, ``dict.get`` falls back to the ``[]`` literal written in the
        *source code* of the ``get`` call, and that literal is evaluated
        fresh on every call (unlike the ``def ... = {}`` default itself, a
        plain list literal inside the function body is not memoized across
        calls). So ``self.titles`` ends up being a brand new, independent
        list object for each instance, and mutating the first instance's
        ``titles`` is NOT observed on the second instance. The sharing risk
        of the mutable default is real for the underlying default dict
        object, but it does not surface as cross-instance state leakage
        through ``titles`` (or the other ``pre_check_data.get(key, [])``
        derived attributes), because none of them are ever assigned back
        onto the shared default dict.

        Requirements: 2.10
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            first_use_case = FacebookSavePreCheckBaseUseCase("user-1")
            second_use_case = FacebookSavePreCheckBaseUseCase("user-2")

        first_use_case.titles.append({"text": "mutated-by-first-instance"})

        # Confirms independently that the signature's default argument is
        # indeed a single shared dict object (the mutable-default pitfall
        # is real at the signature level)...
        default_pre_check_data = (
            FacebookSavePreCheckBaseUseCase.__init__.__defaults__[0]
        )
        assert default_pre_check_data == {}

        # ...but the mutation of `titles` performed above is NOT reflected
        # on the second instance: `titles` is a fresh list per instance,
        # not the shared default dict, so no cross-instance leakage is
        # observed through this attribute.
        assert second_use_case.titles == []
        assert first_use_case.titles is not second_use_case.titles


class TestGetAdChannel:
    """Tests for ``_get_ad_channel``: the exact repository call, identity of
    the returned Ad_Channel, the ``DataNotFoundException`` raised on a
    falsy result, and the short-circuit observed within ``execute()`` when
    the Ad_Channel is missing.

    Requirements: 3.1, 3.2, 3.3, 3.4
    """

    def test_calls_repository_with_exact_positional_arguments_in_order(
        self, use_case_factory
    ):
        """``_get_ad_channel`` invokes
        ``ad_channel_repository.get_by_campaign_and_ad_channel_id`` exactly
        once with the exact positional arguments
        ``(self.campaign_id, self.adset_id, self.ad_id, self.adchannel_id)``,
        in that order.

        Requirements: 3.1
        """
        pre_check_texts_data = make_pre_check_texts_data(
            campaign_id="campaign-7",
            adset_id="adset-7",
            ad_id="ad-7",
            adchannel_id="adchannel-7",
        )
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory(
            pre_check_texts_data=pre_check_texts_data
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        use_case._get_ad_channel()

        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id,
            "campaign-7",
            "adset-7",
            "ad-7",
            "adchannel-7",
        )

    def test_returns_the_same_ad_channel_object_by_identity_when_truthy(
        self, use_case_factory
    ):
        """When the repository returns a truthy Ad_Channel,
        ``_get_ad_channel`` returns that exact same object, by identity.

        Requirements: 3.2
        """
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()
        ad_channel = make_ad_channel()
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )

        result = use_case._get_ad_channel()

        assert result is ad_channel

    @pytest.mark.parametrize(
        "falsy_ad_channel",
        [None, {}],
        ids=["none", "empty_dict"],
    )
    def test_raises_data_not_found_exception_with_exact_message_when_falsy(
        self, use_case_factory, falsy_ad_channel
    ):
        """When the repository returns a falsy value (``None`` or ``{}``),
        ``_get_ad_channel`` propagates ``DataNotFoundException`` whose
        ``.text`` is exactly ``"Creative not found!"``.

        Note: ``str(exc_info.value)`` is deliberately NOT used here.
        ``SinergiaException.__init__`` calls ``super().__init__(args)``
        (passing the ``args`` tuple itself, not the unpacked ``text``), so
        ``str(exc)`` is always the literal ``"()"`` regardless of the
        ``text`` passed in; the actual message lives on ``exc.text``.

        Requirements: 3.3
        """
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            falsy_ad_channel
        )

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_ad_channel()

        assert exc_info.value.text == "Creative not found!"

    def test_execute_short_circuits_on_missing_ad_channel_without_further_calls(
        self, use_case_factory
    ):
        """Within ``execute()``, a missing Ad_Channel (repository returns a
        falsy value) propagates ``DataNotFoundException`` without invoking
        ``_set_channel_id``,
        ``campaign_publish_repository.get_by_campaign_id_and_channel_id``,
        any of the three ``Validador_Meta`` methods used by this class
        (``is_unique_texts``, ``is_valid_length``, ``is_valid_texts_amount``),
        nor ``ad_channel_repository.update``.

        ``redis_client`` is patched with a truthy ``.get.return_value`` so
        ``_get_decoded_access_token`` succeeds first and execution actually
        reaches ``_get_ad_channel`` before failing. The three
        ``MetaAdsValidator`` text methods are patched at the class level
        purely so this test can assert none of them were called; the
        real implementation is never needed here because ``execute()``
        never reaches the validation block.

        Requirements: 3.4
        """
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory()
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_set_channel_id"
        ) as mock_set_channel_id, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == "Creative not found!"
        mock_set_channel_id.assert_not_called()
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.assert_not_called()
        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_ad_channel_repo_instance.update.assert_not_called()
        # `_set_channel_id` never ran, so `channel_id` stays at its
        # pre-call constructor state (`None`, from Datos_de_Campaña_Vacíos).
        assert use_case.channel_id is None


class TestGetCampaignSetup:
    """Tests for ``_get_campaign_setup``: the exact repository call, the
    identity of the returned Campaign_Setup, the interpolated
    ``DataNotFoundException`` message raised on a falsy result, and the
    short-circuit observed within ``execute()`` when the Campaign_Setup is
    missing (which must happen only after ``_get_ad_channel``/
    ``_set_channel_id`` have already run).

    Requirements: 4.1, 4.2, 4.3, 4.4
    """

    def test_calls_repository_with_exact_positional_arguments_in_order(
        self, use_case_factory
    ):
        """``_get_campaign_setup`` invokes
        ``campaign_publish_repository.get_by_campaign_id_and_channel_id``
        exactly once with the exact positional arguments
        ``(self.campaign_id, self.channel_id)``, in that order.

        Requirements: 4.1
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-8")
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            pre_check_texts_data=pre_check_texts_data
        )
        use_case.channel_id = "channel-8"
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_campaign_setup()

        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-8",
            "channel-8",
        )

    def test_returns_the_same_campaign_setup_object_by_identity_when_truthy(
        self, use_case_factory
    ):
        """When the repository returns a truthy Campaign_Setup,
        ``_get_campaign_setup`` returns that exact same object, by
        identity.

        Requirements: 4.2
        """
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory()
        campaign_setup = make_campaign_setup()
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        result = use_case._get_campaign_setup()

        assert result is campaign_setup

    @pytest.mark.parametrize(
        "falsy_campaign_setup",
        [None, {}],
        ids=["none", "empty_dict"],
    )
    def test_raises_data_not_found_exception_with_interpolated_message_when_falsy(
        self, use_case_factory, falsy_campaign_setup
    ):
        """When the repository returns a falsy value (``None`` or ``{}``),
        ``_get_campaign_setup`` propagates ``DataNotFoundException`` whose
        ``.text`` is exactly
        ``f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}"``,
        with both placeholders interpolated from the instance's current
        ``campaign_id``/``channel_id``.

        As with ``_get_ad_channel`` (see
        ``TestGetAdChannel.test_raises_data_not_found_exception_with_exact_message_when_falsy``),
        ``str(exc_info.value)`` is deliberately NOT used here:
        ``SinergiaException.__init__`` calls ``super().__init__(args)``
        (forwarding the ``args`` tuple itself, not the unpacked ``text``),
        so ``str(exc)`` is always the literal ``"()"`` regardless of the
        ``text`` passed in; the actual message lives on ``exc.text``.

        Requirements: 4.3
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-9")
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            pre_check_texts_data=pre_check_texts_data
        )
        use_case.channel_id = "channel-9"
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            falsy_campaign_setup
        )

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_campaign_setup()

        assert exc_info.value.text == (
            "Campaign Setup not found for campaign_id: campaign-9 "
            "and channel_id: channel-9"
        )

    def test_execute_short_circuits_on_missing_campaign_setup_after_ad_channel_and_channel_id(
        self, use_case_factory
    ):
        """Within ``execute()``, a missing Campaign_Setup (repository
        returns a falsy value) propagates ``DataNotFoundException``
        without invoking any of the three ``Validador_Meta`` methods used
        by this class (``is_unique_texts``, ``is_valid_length``,
        ``is_valid_texts_amount``) nor ``ad_channel_repository.update``.

        Crucially, this failure must happen only *after*
        ``_get_ad_channel``/``_set_channel_id`` already ran: the
        Ad_Channel repository is configured with a truthy Ad_Channel
        (``channel_ref_id=99``) so ``_get_ad_channel`` succeeds and
        ``_set_channel_id`` (left unpatched, running for real) assigns a
        non-default ``self.channel_id`` (``99``, distinct from the
        constructor's initial ``None``) before ``_get_campaign_setup`` runs
        and fails. The repository call and the exception's interpolated
        message are both asserted to embed that same non-default
        ``channel_id``, confirming ``_set_channel_id`` really executed and
        that its result is what ``_get_campaign_setup`` actually used.

        Requirements: 4.4
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-10")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel(channel_ref_id=99)
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case.execute()

        # `_set_channel_id` did run (before the failure): `self.channel_id`
        # reflects the Ad_Channel's `channel_ref_id`, not the constructor's
        # initial `None` from Datos_de_Campaña_Vacíos.
        assert use_case.channel_id == 99
        assert exc_info.value.text == (
            "Campaign Setup not found for campaign_id: campaign-10 "
            "and channel_id: 99"
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.assert_called_once()
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-10",
            99,
        )
        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_ad_channel_repo_instance.update.assert_not_called()


class TestSetChannelId:
    """Tests for ``_set_channel_id``: the nested extraction from the
    Ad_Channel's ``attributes.channel_ref.data.id``, the per-level ``0``
    default when any of those keys is absent, and the exact placement of
    ``_set_channel_id`` within ``execute()`` (after ``_get_ad_channel``,
    before ``_get_campaign_setup``).

    Requirements: 5.1, 5.2, 5.3
    """

    def test_assigns_exact_value_when_id_present_and_truthy(self, use_case_factory):
        """When ``attributes.channel_ref.data.id`` is present with a truthy
        value, ``_set_channel_id`` assigns exactly that value to
        ``self.channel_id``.

        Requirements: 5.1
        """
        use_case, _, _ = use_case_factory()
        ad_channel = make_ad_channel(channel_ref_id="channel-42")

        use_case._set_channel_id(ad_channel)

        assert use_case.channel_id == "channel-42"

    @pytest.mark.parametrize(
        "ad_channel",
        [
            {},
            {"attributes": {}},
            {"attributes": {"channel_ref": {}}},
            {"attributes": {"channel_ref": {"data": {}}}},
        ],
        ids=[
            "attributes_absent",
            "channel_ref_absent",
            "data_absent",
            "id_absent",
        ],
    )
    def test_channel_id_defaults_to_zero_without_exception_when_any_level_is_absent(
        self, use_case_factory, ad_channel
    ):
        """When any single one of ``attributes``, ``channel_ref``, ``data``
        or ``id`` is absent from the Ad_Channel (each level tested
        separately, with every level below it also absent as a
        consequence), ``_set_channel_id`` assigns ``0`` to
        ``self.channel_id`` and raises no exception.

        Each intermediate ``.get(key, {})`` absorbs the absence of that key
        with a brand new empty dict, so only the final ``.get('id', 0)``
        default is ever actually exercised, regardless of which level was
        the first to be missing.

        Requirements: 5.2
        """
        use_case, _, _ = use_case_factory()

        use_case._set_channel_id(ad_channel)

        assert use_case.channel_id == 0

    def test_execute_calls_set_channel_id_after_get_ad_channel_and_before_get_campaign_setup(
        self, use_case_factory
    ):
        """Within ``execute()``, ``_set_channel_id`` runs after
        ``_get_ad_channel`` and before ``_get_campaign_setup``, so that the
        ``channel_id`` used by ``_get_campaign_setup`` is the value just
        derived from the Ad_Channel, not the ``None`` inherited from the
        constructor (Datos_de_Campaña_Vacíos).

        The Campaign_Setup lookup is made to return a falsy value so
        ``execute()`` raises right after that lookup; this is only used to
        stop execution cleanly, the assertions below are about the
        arguments the lookup was called with and the resulting
        ``self.channel_id``, not about the resulting exception itself.

        Requirements: 5.3
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-55")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )
        ad_channel = make_ad_channel(channel_ref_id="channel-55")
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = None

        assert use_case.channel_id is None

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"
            with pytest.raises(DataNotFoundException):
                use_case.execute()

        # `_set_channel_id` already ran by the time `_get_campaign_setup`
        # was called: `channel_id` reflects the Ad_Channel's
        # `attributes.channel_ref.data.id`, and that freshly-assigned value
        # (not the constructor's initial `None`) is exactly what the
        # Campaign_Setup lookup received.
        assert use_case.channel_id == "channel-55"
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-55",
            "channel-55",
        )

    def test_execute_uses_zero_default_channel_id_for_campaign_setup_lookup_when_absent(
        self, use_case_factory
    ):
        """When the Ad_Channel omits ``attributes.channel_ref.data.id``
        entirely, ``execute()`` still calls ``_set_channel_id`` before
        ``_get_campaign_setup``, so the Campaign_Setup lookup is made with
        the freshly-assigned default ``0``, not the constructor's initial
        ``None``.

        Requirements: 5.2, 5.3
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-56")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )
        ad_channel = {"attributes": {}}
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"
            with pytest.raises(DataNotFoundException):
                use_case.execute()

        assert use_case.channel_id == 0
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-56",
            0,
        )


class TestExecuteOrchestrationAndShortCircuit:
    """Tests for the orchestration performed by ``execute()`` and the
    short-circuit behaviour observed when any of its early steps fails:
    the exact order of operations, the ``NotAccessException`` raised on a
    missing Redis token, the ``DataNotFoundException`` raised by
    ``_get_ad_channel``/``_get_campaign_setup``, and the identity-preserving
    hand-off of ``creative`` into ``_save_creative_to_publish``/
    ``_build_response`` when ``execute()`` completes without error.

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6
    """

    def test_execute_calls_operations_in_exact_order(self, use_case_factory):
        """``execute()`` performs its operations in the exact order:
        ``_get_decoded_access_token``, ``_get_ad_channel``,
        ``_set_channel_id``, creative extraction from ``ad_channel``,
        ``_get_campaign_setup``, the conditional validation block,
        ``_save_creative_to_publish``, ``_build_response``.

        ``_get_decoded_access_token``, ``_get_ad_channel``,
        ``_set_channel_id``, ``_get_campaign_setup``,
        ``_save_creative_to_publish`` and ``_build_response`` are patched on
        the instance and all attached to a single parent ``Mock`` (the
        "manager" pattern), so their relative call order can be read off
        ``manager.mock_calls`` in one shot. The extraction of ``creative``
        from ``ad_channel``, and of ``asset_feed``/``story_spec`` from
        ``creative``, are inline code in ``execute()``, not separate method
        calls, so they cannot appear in ``manager.mock_calls`` itself; they
        are exercised for real by having the patched ``_get_ad_channel``
        return a real-ish ``make_ad_channel(channel_creative=make_creative())``
        value, and their correctness is confirmed by asserting (in the test
        below covering Requirements 6.5/6.6) that the exact same ``creative``
        object flows by identity into both ``_save_creative_to_publish`` and
        ``_build_response``. ``_get_campaign_setup`` is patched to return
        ``make_campaign_setup()``, whose default ``meta_campaign_mode`` is the
        valid ``"DYNAMIC"``, so ``_set_creative_type`` converts it without
        raising. The conditional validation block is nonetheless a no-op
        because the ``asset_feed`` is genuinely ABSENT: ``make_creative()``
        builds ``ads=[make_ad()]`` and ``make_ad()`` omits ``adCreative``, so
        ``creative['ads'][0].get('adCreative', {})`` is ``{}`` and both
        ``asset_feed`` and ``story_spec`` resolve to ``None``. The DYNAMIC
        guard ``mode == CreativeType.DYNAMIC.value and asset_feed`` is falsy
        on its right operand and the STANDARD ``elif`` does not match either,
        so no text validation runs without needing to patch
        ``MetaAdsValidator`` as well.

        Requirements: 6.1
        """
        use_case, _, _ = use_case_factory()
        creative = make_creative()
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup()
        build_response_result = {"sentinel": "build-response-result"}

        manager = Mock()
        with patch.object(
            use_case, "_get_decoded_access_token"
        ) as mock_get_decoded_access_token, patch.object(
            use_case, "_get_ad_channel"
        ) as mock_get_ad_channel, patch.object(
            use_case, "_set_channel_id"
        ) as mock_set_channel_id, patch.object(
            use_case, "_get_campaign_setup"
        ) as mock_get_campaign_setup, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            manager.attach_mock(
                mock_get_decoded_access_token, "_get_decoded_access_token"
            )
            manager.attach_mock(mock_get_ad_channel, "_get_ad_channel")
            manager.attach_mock(mock_set_channel_id, "_set_channel_id")
            manager.attach_mock(mock_get_campaign_setup, "_get_campaign_setup")
            manager.attach_mock(
                mock_save_creative_to_publish, "_save_creative_to_publish"
            )
            manager.attach_mock(mock_build_response, "_build_response")

            mock_get_decoded_access_token.return_value = "decoded-token"
            mock_get_ad_channel.return_value = ad_channel
            mock_get_campaign_setup.return_value = campaign_setup
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        observed_call_order = [call_item[0] for call_item in manager.mock_calls]
        expected_call_order = [
            "_get_decoded_access_token",
            "_get_ad_channel",
            "_set_channel_id",
            "_get_campaign_setup",
            "_save_creative_to_publish",
            "_build_response",
        ]
        assert observed_call_order == expected_call_order

        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert result is build_response_result

    def test_execute_raises_not_access_exception_and_short_circuits_when_redis_token_missing(
        self, use_case_factory
    ):
        """When the Cliente_Redis returns a falsy value, ``execute()``
        propagates ``NotAccessException`` without invoking
        ``_get_ad_channel``, ``_get_campaign_setup``, any of the three
        ``Validador_Meta`` text-validation methods used by this class
        (``is_unique_texts``, ``is_valid_length``, ``is_valid_texts_amount``),
        nor ``_save_creative_to_publish``.

        ``_get_ad_channel``/``_get_campaign_setup``/``_save_creative_to_publish``
        are patched on the instance, and all three ``MetaAdsValidator``
        methods are patched at the class level, purely so this test can
        assert none of them were ever called; none of them would run for
        real before the token check fails regardless.

        Requirements: 6.2
        """
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_get_ad_channel"
        ) as mock_get_ad_channel, patch.object(
            use_case, "_get_campaign_setup"
        ) as mock_get_campaign_setup, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = None

            with pytest.raises(NotAccessException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == (
            "No access token found in Redis. Please re-authenticate."
        )
        mock_get_ad_channel.assert_not_called()
        mock_get_campaign_setup.assert_not_called()
        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.assert_not_called()

    def test_execute_short_circuits_after_ad_channel_failure_without_save_or_build(
        self, use_case_factory
    ):
        """A ``DataNotFoundException`` raised by ``_get_ad_channel`` (real
        implementation, triggered by a falsy repository result) prevents
        ``execute()`` from invoking ``_save_creative_to_publish`` or
        ``_build_response``.

        ``redis_client`` is patched with a truthy ``.get.return_value`` so
        ``_get_decoded_access_token`` succeeds first and execution actually
        reaches ``_get_ad_channel`` before failing.

        Requirements: 6.3
        """
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory()
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == "Creative not found!"
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.assert_not_called()

    def test_execute_short_circuits_after_campaign_setup_failure_without_save_or_build_but_after_extraction(
        self, use_case_factory
    ):
        """A ``DataNotFoundException`` raised by ``_get_campaign_setup``
        (real implementation, triggered by a falsy repository result)
        prevents ``execute()`` from invoking ``_save_creative_to_publish``
        or ``_build_response``, while confirming that the ``creative``/
        ``asset_feed``/``story_spec`` extraction already happened before
        the failure.

        There is no separately-mockable call to assert on directly for
        that inline extraction (it is plain code inside ``execute()``, not
        a method invocation), so this is confirmed indirectly, the same
        way Requirement 4.4 is confirmed for ``_get_campaign_setup`` alone:
        ``ad_channel_repository.get_by_campaign_and_ad_channel_id`` already
        succeeded (``_get_ad_channel`` ran for real), and ``self.channel_id``
        already reflects the Ad_Channel's ``attributes.channel_ref.data.id``
        (``_set_channel_id`` already ran) rather than the constructor's
        initial ``None`` -- both of which precede the ``creative``/
        ``asset_feed``/``story_spec`` extraction in the body of ``execute()``.
        The three ``MetaAdsValidator`` text-validation methods are
        additionally patched purely to confirm none of them was reached,
        since the validation block itself is never entered before
        ``_get_campaign_setup`` fails.

        Requirements: 6.4
        """
        pre_check_texts_data = make_pre_check_texts_data(campaign_id="campaign-61")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )
        ad_channel = make_ad_channel(
            channel_ref_id="channel-61", channel_creative=make_creative()
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == (
            "Campaign Setup not found for campaign_id: campaign-61 "
            "and channel_id: channel-61"
        )
        # Indirect confirmation that the creative/asset_feed/story_spec
        # extraction already ran before the failure: `_get_ad_channel`'s
        # repository call already succeeded, and `channel_id` already
        # reflects the Ad_Channel's nested id (assigned by `_set_channel_id`)
        # rather than the constructor's initial `None`; both precede the
        # extraction in the body of `execute()`, which itself has no
        # separately-mockable call to assert on directly.
        assert use_case.channel_id == "channel-61"
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-61",
            "channel-61",
        )
        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()

    def test_execute_saves_and_builds_response_with_same_creative_by_identity_and_returns_build_response_result_by_identity(
        self, use_case_factory
    ):
        """When ``execute()`` completes without exception, it invokes
        ``_save_creative_to_publish`` exactly once with the same
        ``creative`` object by identity, then ``_build_response`` exactly
        once with that same ``creative`` object by identity, and returns
        exactly the dict produced by ``_build_response``, by identity.

        ``creative`` is built with the default ``make_creative()``/
        ``make_ad()`` (``adCreative`` omitted entirely), so ``asset_feed``/
        ``story_spec`` are both ``None`` and the conditional validation
        block is a no-op regardless of ``meta_campaign_mode``; ``STANDARD``
        is used here for clarity, matching the no-op branch this scenario
        is meant to exercise, and ``MetaAdsValidator`` does not need to be
        patched for this scenario to reach ``_save_creative_to_publish``/
        ``_build_response`` without error.

        Requirements: 6.5, 6.6
        """
        creative = make_creative()
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")
        build_response_result = {"sentinel": "build-response-result"}

        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory()
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result


class TestDynamicBranchTitlesValidation:
    """Tests for the DYNAMIC branch's inline validation of Textos_de_Título
    (``self.titles``) within ``execute()``: the three exact
    ``MetaAdsValidator`` calls (``is_unique_texts``, ``is_valid_length``,
    ``is_valid_texts_amount``), the in-place mutation performed by
    ``is_valid_length``, and the identity-preserving overwrite of
    ``asset_feed['titles']``.

    As documented in ``design.md``, ``FacebookSavePreCheckTextsUseCase`` has
    no ``_validate_texts_dynamic`` method of its own: all of this logic
    lives inline inside ``execute()``, so this scenario exercises
    ``execute()`` end to end, with ``AdChannelRepository``/
    ``CampaignChannelPublishRepository``/``redis_client`` patched via
    ``use_case_factory``/``patch_redis_client``, and the three
    ``MetaAdsValidator`` text methods patched individually with
    ``wraps=`` the real implementation (not via the shared
    ``patch_text_validators`` helper, which is reserved for the
    call-order assertions of Requirement 10.1), so their real side
    effects (in-place mutation of ``self.titles`` entries, real return
    values) keep happening while each call's exact arguments can still be
    asserted directly on the mock.

    ``self.bodies``/``self.descriptions`` are left empty so the same
    three patched methods are also invoked for those two fields (the
    DYNAMIC branch validates all three fields unconditionally, regardless
    of whether a given field's list is empty); ``assert_any_call`` is used
    instead of ``assert_called_once_with`` throughout for this reason,
    since each of the three methods ends up invoked three times in total
    (once per field) within the same ``execute()`` call.

    Requirements: 7.1, 7.2, 7.3, 7.4
    """

    def test_calls_three_validators_with_exact_arguments_and_overwrites_titles_by_identity(
        self, use_case_factory
    ):
        """Exercise ``execute()`` end to end with ``meta_campaign_mode=
        "DYNAMIC"`` and a truthy ``asset_feed``, and verify:

        - ``MetaAdsValidator.is_unique_texts`` is invoked with
          ``[t.get('text') for t in self.titles]`` (a fresh list of
          strings, not ``self.titles`` itself), and
          ``asset_feed['unique_titles']`` is assigned exactly the
          returned boolean, using the real (wrapped, not replaced)
          implementation.
        - ``MetaAdsValidator.is_valid_length`` is invoked with the exact
          arguments ``('titles', self.titles)``; its return value
          (``None``) is discarded -- no key of ``asset_feed`` is ever
          assigned from it -- while every entry of ``self.titles`` is
          mutated in place with a ``valid_length`` key according to the
          255-character maximum used for ``"titles"``.
        - ``MetaAdsValidator.is_valid_texts_amount`` is invoked with the
          exact arguments ``('titles', self.titles)``, and
          ``asset_feed['titles_valid_amount']`` is assigned exactly the
          returned boolean.
        - ``asset_feed['titles']`` ends up overwritten exactly with
          ``self.titles``, by identity, even though ``asset_feed['titles']``
          previously held a different value (``["stale-value"]`` here),
          confirming the original content of ``asset_feed['titles']`` is
          discarded rather than merged with ``self.titles``.

        Requirements: 7.1, 7.2, 7.3, 7.4
        """
        titles = [make_text_entry("Short title"), make_text_entry("Another title")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(titles=["stale-value"])
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

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            wraps=MetaAdsValidator.is_unique_texts,
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            wraps=MetaAdsValidator.is_valid_length,
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount",
            wraps=MetaAdsValidator.is_valid_texts_amount,
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_is_unique_texts.assert_any_call(["Short title", "Another title"])
        mock_is_valid_length.assert_any_call("titles", titles)
        mock_is_valid_texts_amount.assert_any_call("titles", titles)

        # Real, unpatched-behavior results: two short, unique, non-empty
        # texts are unique (`unique_titles=True`) and within the 1..5
        # amount range (`titles_valid_amount=True`).
        assert asset_feed["unique_titles"] is True
        assert asset_feed["titles_valid_amount"] is True

        # `is_valid_length`'s discarded return value (`None`) never lands
        # on `asset_feed`; its only observable effect is the in-place
        # mutation of each `self.titles` entry.
        assert "valid_length" not in asset_feed
        assert titles[0]["valid_length"] is True
        assert titles[1]["valid_length"] is True

        # `asset_feed['titles']` is overwritten by identity with
        # `self.titles`, discarding the previous `["stale-value"]`.
        assert asset_feed["titles"] is titles
        assert asset_feed["titles"] != ["stale-value"]

    @pytest.mark.parametrize(
        "titles_count, expected_titles_valid_amount",
        [
            (0, False),
            (5, True),
            (6, False),
        ],
        ids=["zero-titles", "five-titles", "six-titles"],
    )
    def test_titles_valid_amount_real_boundary_matrix_0_5_6(
        self, use_case_factory, titles_count, expected_titles_valid_amount
    ):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.titles`` parametrized to 0, 5 and 6
        entries, each with a unique, non-empty ``text``, using the fully
        real, unpatched ``MetaAdsValidator.is_valid_texts_amount``
        implementation (valid when ``1 <= len(texts) <= 5``), and verify
        that ``asset_feed['titles_valid_amount']`` ends up ``False``,
        ``True``, ``False`` respectively.

        No ``MetaAdsValidator`` method is patched at all in this test:
        this task only needs the resulting
        ``asset_feed['titles_valid_amount']`` value, not the exact call
        arguments (already covered by task 8.1's test above), so no
        ``wraps=``-patched double is needed either.

        Requirements: 7.5, 7.6, 7.7
        """
        titles = [make_text_entry(f"Title {index}") for index in range(titles_count)]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert asset_feed["titles_valid_amount"] is expected_titles_valid_amount

    def test_two_identical_nonempty_titles_are_not_unique(self, use_case_factory):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.titles`` containing two entries whose
        ``text`` is identical (truthy, non-empty), and verify, using the
        fully real (unpatched) ``MetaAdsValidator.is_unique_texts``
        implementation, that ``asset_feed['unique_titles']`` ends up
        ``False``: ``is_unique_texts`` compares
        ``len(texts) != len(set(texts))`` after filtering falsy values, and
        two equal, truthy strings collapse into a single element in the
        ``set``, so the lengths differ.

        Requirements: 7.8
        """
        titles = [make_text_entry("Same title"), make_text_entry("Same title")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert asset_feed["unique_titles"] is False

    @pytest.mark.parametrize(
        "titles",
        [
            [],
            [
                make_text_entry(""),
                {},
                make_text_entry("Unique A"),
                make_text_entry("Unique B"),
            ],
            [make_text_entry(""), {}, make_text_entry("")],
        ],
        ids=[
            "empty-titles-list",
            "empty-and-missing-key-mixed-with-two-unique-entries",
            "only-empty-and-missing-key-entries",
        ],
    )
    def test_missing_or_empty_text_entries_are_filtered_before_uniqueness_comparison(
        self, use_case_factory, titles
    ):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.titles`` either empty, or containing
        entries whose ``text`` is ``""``/missing entirely mixed with unique
        truthy entries, or containing only ``""``/missing-``text`` entries,
        and verify, using the fully real (unpatched)
        ``MetaAdsValidator.is_unique_texts`` implementation, that:

        - No exception propagates out of ``execute()``: ``is_unique_texts``
          filters out falsy values (``texts = [t for t in texts if t]``)
          before comparing lengths, so ``""``/missing-``text`` entries
          never reach the ``set(...)`` comparison.
        - ``asset_feed['unique_titles']`` ends up ``True`` in every one of
          these three cases, because once the falsy entries are filtered
          out, no true (non-empty) duplicate remains: an empty list has no
          duplicates, two distinct non-empty titles plus two filtered-out
          entries have no duplicates, and a list containing only
          filtered-out entries reduces to an empty list, which also has no
          duplicates.

        Note: an entry whose ``text`` key is explicitly present with value
        ``None`` (as opposed to ``""`` or a missing key) is deliberately
        NOT included in this parametrization. ``is_unique_texts`` itself
        handles ``None`` exactly like ``""``/missing (it is filtered out
        by ``[t for t in texts if t]``), but the very next real call in
        ``execute()``, ``MetaAdsValidator.is_valid_length('titles', ...)``,
        does ``text.get('text', '')`` -- which only falls back to ``''``
        when the ``'text'`` key is *absent*, not when it is present with
        value ``None`` -- and then calls ``len(...)`` on the result,
        raising ``TypeError: object of type 'NoneType' has no len()``.
        Since this class has no way to exercise ``is_unique_texts`` in
        isolation from ``is_valid_length`` (both run inline, back to back,
        inside the same ``execute()`` call, per ``design.md``), a title
        entry with an explicit ``None`` ``text`` cannot be exercised
        through ``execute()`` without also hitting this unrelated,
        pre-existing ``is_valid_length`` quirk; that quirk is characterized
        separately (undisturbed, not "fixed") by
        ``test_valid_length_mutation_for_oversized_normal_and_missing_title_text``
        below using a missing ``'text'`` key rather than an explicit
        ``None``.

        Requirements: 7.9
        """
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert asset_feed["unique_titles"] is True

    def test_valid_length_mutation_for_oversized_normal_and_missing_title_text(
        self, use_case_factory
    ):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.titles`` containing three entries: one
        whose ``text`` exceeds 255 characters, one whose ``text`` has a
        length between 1 and 255 characters, and one whose ``text`` is
        missing/empty, and verify, using the fully real (unpatched)
        ``MetaAdsValidator.is_valid_length`` implementation, that each
        entry is mutated in place with the expected ``valid_length``:

        - The 300-character entry ends up with ``valid_length=False``
          (``length > max_length``, where ``max_length`` is 255 for
          ``"titles"``).
        - The normal-length entry ends up with ``valid_length=True``
          (``0 < length <= 255``).
        - The missing/empty-text entry ends up with ``valid_length=False``
          (``length == 0``, via ``text.get('text', '')`` defaulting to
          ``''`` for the omitted-``text`` case).

        Requirements: 7.10
        """
        oversized_title = make_text_entry("A" * 300)
        normal_title = make_text_entry("A" * 100)
        missing_text_title = {}
        titles = [oversized_title, normal_title, missing_text_title]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert oversized_title["valid_length"] is False
        assert normal_title["valid_length"] is True
        assert missing_text_title["valid_length"] is False


class TestDynamicBranchBodiesValidation:
    """Tests for the DYNAMIC branch's inline validation of Textos_de_Cuerpo
    (``self.bodies``) within ``execute()``: the three exact
    ``MetaAdsValidator`` calls (``is_unique_texts``, ``is_valid_length``,
    ``is_valid_texts_amount``), the in-place mutation performed by
    ``is_valid_length`` (using the 1024-character maximum for ``"bodies"``,
    distinct from the 255-character maximum used for ``titles``/
    ``descriptions``), and the identity-preserving overwrite of
    ``asset_feed['bodies']``.

    As documented in ``design.md``, ``FacebookSavePreCheckTextsUseCase`` has
    no ``_validate_texts_dynamic`` method of its own: all of this logic
    lives inline inside ``execute()``, so this scenario exercises
    ``execute()`` end to end, with ``AdChannelRepository``/
    ``CampaignChannelPublishRepository``/``redis_client`` patched via
    ``use_case_factory``/``patch_redis_client``, and the three
    ``MetaAdsValidator`` text methods patched individually with
    ``wraps=`` the real implementation (not via the shared
    ``patch_text_validators`` helper, which is reserved for the
    call-order assertions of Requirement 10.1), so their real side
    effects (in-place mutation of ``self.bodies`` entries, real return
    values) keep happening while each call's exact arguments can still be
    asserted directly on the mock.

    ``self.titles``/``self.descriptions`` are left empty so the same
    three patched methods are also invoked for those two fields (the
    DYNAMIC branch validates all three fields unconditionally, regardless
    of whether a given field's list is empty); ``assert_any_call`` is used
    instead of ``assert_called_once_with`` throughout for this reason,
    since each of the three methods ends up invoked three times in total
    (once per field) within the same ``execute()`` call.

    Requirements: 8.1, 8.2, 8.3, 8.4
    """

    def test_calls_three_validators_with_exact_arguments_and_overwrites_bodies_by_identity(
        self, use_case_factory
    ):
        """Exercise ``execute()`` end to end with ``meta_campaign_mode=
        "DYNAMIC"`` and a truthy ``asset_feed``, and verify:

        - ``MetaAdsValidator.is_unique_texts`` is invoked with
          ``[t.get('text') for t in self.bodies]`` (a fresh list of
          strings, not ``self.bodies`` itself), and
          ``asset_feed['unique_bodies']`` is assigned exactly the
          returned boolean, using the real (wrapped, not replaced)
          implementation.
        - ``MetaAdsValidator.is_valid_length`` is invoked with the exact
          arguments ``('bodies', self.bodies)``; its return value
          (``None``) is discarded -- no key of ``asset_feed`` is ever
          assigned from it -- while every entry of ``self.bodies`` is
          mutated in place with a ``valid_length`` key according to the
          1024-character maximum used for ``"bodies"`` (distinct from the
          255-character maximum used for ``titles``/``descriptions``).
        - ``MetaAdsValidator.is_valid_texts_amount`` is invoked with the
          exact arguments ``('bodies', self.bodies)``, and
          ``asset_feed['bodies_valid_amount']`` is assigned exactly the
          returned boolean.
        - ``asset_feed['bodies']`` ends up overwritten exactly with
          ``self.bodies``, by identity, even though ``asset_feed['bodies']``
          previously held a different value (``["stale-value"]`` here),
          confirming the original content of ``asset_feed['bodies']`` is
          discarded rather than merged with ``self.bodies``.

        Requirements: 8.1, 8.2, 8.3, 8.4
        """
        bodies = [make_text_entry("Short body"), make_text_entry("Another body")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=bodies, descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(bodies=["stale-value"])
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

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            wraps=MetaAdsValidator.is_unique_texts,
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            wraps=MetaAdsValidator.is_valid_length,
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount",
            wraps=MetaAdsValidator.is_valid_texts_amount,
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_is_unique_texts.assert_any_call(["Short body", "Another body"])
        mock_is_valid_length.assert_any_call("bodies", bodies)
        mock_is_valid_texts_amount.assert_any_call("bodies", bodies)

        # Real, unpatched-behavior results: two short, unique, non-empty
        # texts are unique (`unique_bodies=True`) and within the 1..5
        # amount range (`bodies_valid_amount=True`).
        assert asset_feed["unique_bodies"] is True
        assert asset_feed["bodies_valid_amount"] is True

        # `is_valid_length`'s discarded return value (`None`) never lands
        # on `asset_feed`; its only observable effect is the in-place
        # mutation of each `self.bodies` entry. Both texts here are well
        # within the 1024-character maximum used for `"bodies"`.
        assert "valid_length" not in asset_feed
        assert bodies[0]["valid_length"] is True
        assert bodies[1]["valid_length"] is True

        # `asset_feed['bodies']` is overwritten by identity with
        # `self.bodies`, discarding the previous `["stale-value"]`.
        assert asset_feed["bodies"] is bodies
        assert asset_feed["bodies"] != ["stale-value"]

    @pytest.mark.parametrize(
        "bodies_count, expected_bodies_valid_amount",
        [
            (0, False),
            (5, True),
            (6, False),
        ],
        ids=["zero-bodies", "five-bodies", "six-bodies"],
    )
    def test_bodies_valid_amount_real_boundary_matrix_0_5_6(
        self, use_case_factory, bodies_count, expected_bodies_valid_amount
    ):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.bodies`` parametrized to 0, 5 and 6
        entries, each with a unique, non-empty ``text``, using the fully
        real, unpatched ``MetaAdsValidator.is_valid_texts_amount``
        implementation (valid when ``1 <= len(texts) <= 5``), and verify
        that ``asset_feed['bodies_valid_amount']`` ends up ``False``,
        ``True``, ``False`` respectively.

        No ``MetaAdsValidator`` method is patched at all in this test:
        this task only needs the resulting
        ``asset_feed['bodies_valid_amount']`` value, not the exact call
        arguments (already covered by task 9.1's test above), so no
        ``wraps=``-patched double is needed either. Mirrors task 8.2's
        ``titles`` boundary-matrix test above, adapted to ``bodies``.

        Requirements: 8.5
        """
        bodies = [make_text_entry(f"Body {index}") for index in range(bodies_count)]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=bodies, descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert asset_feed["bodies_valid_amount"] is expected_bodies_valid_amount

    def test_300_char_text_is_invalid_for_titles_but_valid_for_bodies(
        self, use_case_factory
    ):
        """Exercise two independent ``execute()`` scenarios with the exact
        same ~300-character text, once placed in ``self.titles`` and once
        placed in ``self.bodies``, and verify, using the fully real
        (unpatched) ``MetaAdsValidator.is_valid_length`` implementation,
        that the two different per-field maximums documented in
        ``design.md`` (255 for ``"titles"``, 1024 for ``"bodies"``) produce
        opposite ``valid_length`` outcomes for the identical text:

        - Scenario 1: the 300-character text placed in ``self.titles``
          ends up mutated in place with ``valid_length=False`` (300 > 255).
        - Scenario 2: the exact same 300-character text placed in
          ``self.bodies`` ends up mutated in place with
          ``valid_length=True`` (300 <= 1024).

        Each scenario builds its own fresh ``pre_check_texts_data``/
        ``use_case``/``asset_feed``/``creative`` via ``use_case_factory``,
        so the two ``execute()`` calls are fully independent of one
        another.

        Requirements: 8.6
        """
        long_text = "A" * 300

        # Scenario 1: the 300-character text in `self.titles` -- invalid,
        # 300 exceeds the 255-character maximum for "titles".
        title_entry = make_text_entry(long_text)
        titles_pre_check_texts_data = make_pre_check_texts_data(
            titles=[title_entry], bodies=[], descriptions=[]
        )
        (
            titles_use_case,
            titles_mock_ad_channel_repo_instance,
            titles_mock_campaign_publish_repo_instance,
        ) = use_case_factory(pre_check_texts_data=titles_pre_check_texts_data)

        titles_asset_feed = make_asset_feed_spec()
        titles_ad_creative = make_ad_creative(asset_feed_spec=titles_asset_feed)
        titles_ad = make_ad(ad_creative=titles_ad_creative)
        titles_creative = make_creative(ads=[titles_ad])
        titles_ad_channel = make_ad_channel(channel_creative=titles_creative)
        titles_campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        titles_mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            titles_ad_channel
        )
        titles_mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            titles_campaign_setup
        )

        with patch_redis_client() as titles_mock_redis_client:
            titles_mock_redis_client.get.return_value = b"some-access-token"

            titles_use_case.execute()

        assert title_entry["valid_length"] is False

        # Scenario 2: the exact same 300-character text in `self.bodies`
        # -- valid, 300 is within the 1024-character maximum for "bodies".
        body_entry = make_text_entry(long_text)
        bodies_pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=[body_entry], descriptions=[]
        )
        (
            bodies_use_case,
            bodies_mock_ad_channel_repo_instance,
            bodies_mock_campaign_publish_repo_instance,
        ) = use_case_factory(pre_check_texts_data=bodies_pre_check_texts_data)

        bodies_asset_feed = make_asset_feed_spec()
        bodies_ad_creative = make_ad_creative(asset_feed_spec=bodies_asset_feed)
        bodies_ad = make_ad(ad_creative=bodies_ad_creative)
        bodies_creative = make_creative(ads=[bodies_ad])
        bodies_ad_channel = make_ad_channel(channel_creative=bodies_creative)
        bodies_campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        bodies_mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            bodies_ad_channel
        )
        bodies_mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            bodies_campaign_setup
        )

        with patch_redis_client() as bodies_mock_redis_client:
            bodies_mock_redis_client.get.return_value = b"some-access-token"

            bodies_use_case.execute()

        assert body_entry["valid_length"] is True

    def test_valid_length_mutation_for_oversized_body_text(self, use_case_factory):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.bodies`` containing a single entry
        whose ``text`` exceeds 1024 characters, and verify, using the
        fully real (unpatched) ``MetaAdsValidator.is_valid_length``
        implementation, that this entry is mutated in place with
        ``valid_length=False`` (``length > max_length``, where
        ``max_length`` is 1024 for ``"bodies"``).

        Requirements: 8.6
        """
        oversized_body = make_text_entry("A" * 1025)
        bodies = [oversized_body]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=bodies, descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert oversized_body["valid_length"] is False


class TestDynamicBranchDescriptionsValidation:
    """Tests for the DYNAMIC branch's inline validation of
    Textos_de_Descripción (``self.descriptions``) within ``execute()``: the
    three exact ``MetaAdsValidator`` calls (``is_unique_texts``,
    ``is_valid_length``, ``is_valid_texts_amount``), the in-place mutation
    performed by ``is_valid_length`` (using the 255-character maximum for
    ``"descriptions"``, the same maximum used for ``titles`` and distinct
    from the 1024-character maximum used for ``bodies``), the
    identity-preserving overwrite of ``asset_feed['descriptions']``, and
    the real 0/5/6 boundary matrix of ``is_valid_texts_amount``.

    As documented in ``design.md``, ``FacebookSavePreCheckTextsUseCase`` has
    no ``_validate_texts_dynamic`` method of its own: all of this logic
    lives inline inside ``execute()``, so this scenario exercises
    ``execute()`` end to end, with ``AdChannelRepository``/
    ``CampaignChannelPublishRepository``/``redis_client`` patched via
    ``use_case_factory``/``patch_redis_client``, and the three
    ``MetaAdsValidator`` text methods patched individually with
    ``wraps=`` the real implementation (not via the shared
    ``patch_text_validators`` helper, which is reserved for the
    call-order assertions of Requirement 10.1), so their real side
    effects (in-place mutation of ``self.descriptions`` entries, real
    return values) keep happening while each call's exact arguments can
    still be asserted directly on the mock.

    Unlike the sibling ``titles``/``bodies`` suites above (split across
    tasks 8.1/8.2 and 9.1/9.2 respectively), this task combines the
    exact-call/overwrite scenario and the 0/5/6 boundary matrix into a
    single test class, per task 10.1.

    ``self.titles``/``self.bodies`` are left empty so the same three
    patched methods are also invoked for those two fields (the DYNAMIC
    branch validates all three fields unconditionally, regardless of
    whether a given field's list is empty); ``assert_any_call`` is used
    instead of ``assert_called_once_with`` throughout for this reason,
    since each of the three methods ends up invoked three times in total
    (once per field) within the same ``execute()`` call.

    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """

    def test_calls_three_validators_with_exact_arguments_and_overwrites_descriptions_by_identity(
        self, use_case_factory
    ):
        """Exercise ``execute()`` end to end with ``meta_campaign_mode=
        "DYNAMIC"`` and a truthy ``asset_feed``, and verify:

        - ``MetaAdsValidator.is_unique_texts`` is invoked with
          ``[t.get('text') for t in self.descriptions]`` (a fresh list of
          strings, not ``self.descriptions`` itself), and
          ``asset_feed['unique_descriptions']`` is assigned exactly the
          returned boolean, using the real (wrapped, not replaced)
          implementation.
        - ``MetaAdsValidator.is_valid_length`` is invoked with the exact
          arguments ``('descriptions', self.descriptions)``; its return
          value (``None``) is discarded -- no key of ``asset_feed`` is
          ever assigned from it -- while every entry of
          ``self.descriptions`` is mutated in place with a
          ``valid_length`` key according to the 255-character maximum
          used for ``"descriptions"`` (the same maximum used for
          ``titles``, distinct from the 1024-character maximum used for
          ``bodies``).
        - ``MetaAdsValidator.is_valid_texts_amount`` is invoked with the
          exact arguments ``('descriptions', self.descriptions)``, and
          ``asset_feed['descriptions_valid_amount']`` is assigned exactly
          the returned boolean.
        - ``asset_feed['descriptions']`` ends up overwritten exactly with
          ``self.descriptions``, by identity, even though
          ``asset_feed['descriptions']`` previously held a different
          value (``["stale-value"]`` here), confirming the original
          content of ``asset_feed['descriptions']`` is discarded rather
          than merged with ``self.descriptions``.

        Requirements: 9.1, 9.2, 9.3, 9.4
        """
        descriptions = [
            make_text_entry("Short description"),
            make_text_entry("Another description"),
        ]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=[], descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(descriptions=["stale-value"])
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

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts",
            wraps=MetaAdsValidator.is_unique_texts,
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length",
            wraps=MetaAdsValidator.is_valid_length,
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount",
            wraps=MetaAdsValidator.is_valid_texts_amount,
        ) as mock_is_valid_texts_amount:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_is_unique_texts.assert_any_call(
            ["Short description", "Another description"]
        )
        mock_is_valid_length.assert_any_call("descriptions", descriptions)
        mock_is_valid_texts_amount.assert_any_call("descriptions", descriptions)

        # Real, unpatched-behavior results: two short, unique, non-empty
        # texts are unique (`unique_descriptions=True`) and within the
        # 1..5 amount range (`descriptions_valid_amount=True`).
        assert asset_feed["unique_descriptions"] is True
        assert asset_feed["descriptions_valid_amount"] is True

        # `is_valid_length`'s discarded return value (`None`) never lands
        # on `asset_feed`; its only observable effect is the in-place
        # mutation of each `self.descriptions` entry.
        assert "valid_length" not in asset_feed
        assert descriptions[0]["valid_length"] is True
        assert descriptions[1]["valid_length"] is True

        # `asset_feed['descriptions']` is overwritten by identity with
        # `self.descriptions`, discarding the previous `["stale-value"]`.
        assert asset_feed["descriptions"] is descriptions
        assert asset_feed["descriptions"] != ["stale-value"]

    @pytest.mark.parametrize(
        "descriptions_count, expected_descriptions_valid_amount",
        [
            (0, False),
            (5, True),
            (6, False),
        ],
        ids=["zero-descriptions", "five-descriptions", "six-descriptions"],
    )
    def test_descriptions_valid_amount_real_boundary_matrix_0_5_6(
        self, use_case_factory, descriptions_count, expected_descriptions_valid_amount
    ):
        """Exercise ``execute()`` end to end, in DYNAMIC mode with a truthy
        ``asset_feed``, with ``self.descriptions`` parametrized to 0, 5
        and 6 entries, each with a unique, non-empty ``text``, using the
        fully real, unpatched ``MetaAdsValidator.is_valid_texts_amount``
        implementation (valid when ``1 <= len(texts) <= 5``), and verify
        that ``asset_feed['descriptions_valid_amount']`` ends up
        ``False``, ``True``, ``False`` respectively.

        No ``MetaAdsValidator`` method is patched at all in this test:
        this task only needs the resulting
        ``asset_feed['descriptions_valid_amount']`` value, not the exact
        call arguments (already covered by the test above). Mirrors task
        8.2's/9.2's ``titles``/``bodies`` boundary-matrix tests, adapted
        to ``descriptions``.

        Requirements: 9.5
        """
        descriptions = [
            make_text_entry(f"Description {index}")
            for index in range(descriptions_count)
        ]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[], bodies=[], descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert (
            asset_feed["descriptions_valid_amount"]
            is expected_descriptions_valid_amount
        )


class TestDynamicBranchCallOrderAcrossFields:
    """Tests for the exact interleaved order of the 9 ``MetaAdsValidator``
    calls spread across ``titles``, ``bodies`` and ``descriptions`` within
    the DYNAMIC branch of ``execute()``, and for the fact that ``execute()``
    continues on to ``_save_creative_to_publish``/``_build_response``
    without interruption once all three fields have been validated.

    Unlike the per-field suites above (Requirements 7-9), which patch each
    ``MetaAdsValidator`` method individually with ``wraps=`` and use
    ``assert_any_call`` (because they cannot distinguish which of the three
    per-field invocations produced a given call), this class uses the
    shared ``patch_text_validators`` helper specifically so the exact
    9-call interleaved sequence -- not just each call's arguments in
    isolation -- can be asserted via its shared ``call_order`` list.

    Requirements: 10.1, 10.2
    """

    def test_call_order_records_exact_9_call_sequence_and_execute_continues_to_response(
        self, use_case_factory
    ):
        """Exercise ``execute()`` end to end with ``meta_campaign_mode=
        "DYNAMIC"``, a truthy ``asset_feed``, and non-empty ``titles``,
        ``bodies`` and ``descriptions``, using ``patch_text_validators``,
        and verify:

        - ``call_order`` contains exactly 9 entries, in the exact order:
          ``is_unique_texts(titles)``, ``is_valid_length('titles', ...)``,
          ``is_valid_texts_amount('titles', ...)``,
          ``is_unique_texts(bodies)``, ``is_valid_length('bodies', ...)``,
          ``is_valid_texts_amount('bodies', ...)``,
          ``is_unique_texts(descriptions)``,
          ``is_valid_length('descriptions', ...)``,
          ``is_valid_texts_amount('descriptions', ...)``.
        - ``execute()`` raises no exception and continues on to
          ``_save_creative_to_publish``/``_build_response``: the returned
          Respuesta_de_Precheck reflects the nine values assigned onto the
          already-mutated ``asset_feed`` (``unique_titles``,
          ``titles_valid_amount``, ``titles``, ``unique_bodies``,
          ``bodies_valid_amount``, ``bodies``, ``unique_descriptions``,
          ``descriptions_valid_amount``, ``descriptions``).

        ``asset_feed['titles']``/``['bodies']``/``['descriptions']`` start
        out with stale placeholder values, so the response's ``titles``/
        ``bodies``/``descriptions`` keys reflecting ``self.titles``/
        ``self.bodies``/``self.descriptions`` by identity also confirms the
        real overwrite (not merely that the stale value happened to match).

        Requirements: 10.1, 10.2
        """
        titles = [make_text_entry("Title one"), make_text_entry("Title two")]
        bodies = [make_text_entry("Body one"), make_text_entry("Body two")]
        descriptions = [
            make_text_entry("Description one"),
            make_text_entry("Description two"),
        ]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(
            titles=["stale-titles"],
            bodies=["stale-bodies"],
            descriptions=["stale-descriptions"],
        )
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

        with patch_redis_client() as mock_redis_client, patch_text_validators() as call_order:
            mock_redis_client.get.return_value = b"some-access-token"

            result = use_case.execute()

        expected_call_order = [
            ("is_unique_texts", (["Title one", "Title two"],)),
            ("is_valid_length", ("titles", titles)),
            ("is_valid_texts_amount", ("titles", titles)),
            ("is_unique_texts", (["Body one", "Body two"],)),
            ("is_valid_length", ("bodies", bodies)),
            ("is_valid_texts_amount", ("bodies", bodies)),
            ("is_unique_texts", (["Description one", "Description two"],)),
            ("is_valid_length", ("descriptions", descriptions)),
            ("is_valid_texts_amount", ("descriptions", descriptions)),
        ]
        assert len(call_order) == 9
        assert call_order == expected_call_order

        # `asset_feed` is mutated in place by the real validators, so
        # `execute()` continued past the DYNAMIC validation block without
        # interruption: `_save_creative_to_publish`/`_build_response` both
        # ran for real (no exception was raised above), and the persisted
        # `ad_channel_id` update confirms `_save_creative_to_publish` used
        # the same (mutated) `creative` object.
        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            0,
            {"channel_creative": creative},
        )

        # The nine DYNAMIC-branch assignments landed on `asset_feed`,
        # overwriting the stale placeholder values by identity with
        # `self.titles`/`self.bodies`/`self.descriptions`.
        assert asset_feed["unique_titles"] is True
        assert asset_feed["titles_valid_amount"] is True
        assert asset_feed["titles"] is titles
        assert asset_feed["unique_bodies"] is True
        assert asset_feed["bodies_valid_amount"] is True
        assert asset_feed["bodies"] is bodies
        assert asset_feed["unique_descriptions"] is True
        assert asset_feed["descriptions_valid_amount"] is True
        assert asset_feed["descriptions"] is descriptions

        # The Respuesta_de_Precheck returned by `execute()` (produced by
        # `_build_response`) reflects the already-mutated `asset_feed`.
        assert result["titles"] is titles
        assert result["bodies"] is bodies
        assert result["descriptions"] is descriptions
        assert result["unique_titles"] is True
        assert result["titles_valid_amount"] is True
        assert result["unique_bodies"] is True
        assert result["bodies_valid_amount"] is True
        assert result["unique_descriptions"] is True
        assert result["descriptions_valid_amount"] is True
        assert result["name"] == creative["name"]
        assert result["adset_id"] == creative["id"]
        assert result["ad_id"] == ad["id"]

    # Feature: facebook-save-pre-check-texts-tests, Property 1: is_valid_texts_amount
    # es verdadero si y solo si la cantidad de textos está en [1, 5]
    @settings(max_examples=100, deadline=None)
    @given(
        type_=st.sampled_from(["titles", "bodies", "descriptions"]),
        texts=st.lists(
            st.one_of(
                st.integers(),
                st.text(max_size=5),
                st.dictionaries(st.text(max_size=5), st.integers()),
            ),
            min_size=0,
            max_size=15,
        ),
    )
    def test_property_is_valid_texts_amount_true_iff_count_in_1_to_5(
        self, type_, texts
    ):
        """Optional property test (task 11.2, ``design.md`` -> Correctness
        Properties -> Property 1): for any ``type_`` in
        ``{"titles", "bodies", "descriptions"}`` and any list ``texts`` of
        arbitrary length between 0 and 15, with the content of each element
        irrelevant to the result (``is_valid_texts_amount`` only inspects
        ``len(texts)``), ``MetaAdsValidator.is_valid_texts_amount(type_,
        texts) == (1 <= len(texts) <= 5)``.

        Calls the real, unpatched ``MetaAdsValidator.is_valid_texts_amount``
        directly (not through the use case). This property test is
        optional and complements, without replacing, the concrete 0/5/6
        boundary matrices already covered by tasks 8.2, 9.2 and 10.1 for
        ``titles``, ``bodies`` and ``descriptions`` respectively.

        Validates: Requirements 7.5, 7.6, 7.7, 8.5, 9.5
        """
        assert MetaAdsValidator.is_valid_texts_amount(type_, texts) == (
            1 <= len(texts) <= 5
        )

    # Feature: facebook-save-pre-check-texts-tests, Property 2: is_unique_texts
    # es verdadero si y solo si los textos no vacíos no tienen duplicados
    @settings(max_examples=100, deadline=None)
    @given(
        texts=st.lists(
            st.one_of(st.none(), st.just(""), st.text(max_size=5)),
            min_size=0,
            max_size=15,
        )
    )
    def test_property_is_unique_texts_true_iff_no_duplicates_among_nonempty(
        self, texts
    ):
        """Optional property test (task 11.2, ``design.md`` -> Correctness
        Properties -> Property 2): for any list ``texts`` of strings
        (including ``None``/``""`` among its elements), let
        ``filtered = [t for t in texts if t]``; then
        ``MetaAdsValidator.is_unique_texts(texts) == (len(filtered) ==
        len(set(filtered)))``.

        Calls the real, unpatched ``MetaAdsValidator.is_unique_texts``
        directly (not through the use case). This property test is
        optional and complements, without replacing, the concrete
        duplicate/empty-value scenarios already covered by task 8.3 for
        ``titles``.

        Validates: Requirements 7.8, 7.9
        """
        filtered = [t for t in texts if t]
        assert MetaAdsValidator.is_unique_texts(texts) == (
            len(filtered) == len(set(filtered))
        )


class TestDynamicBranchMissingAssetFeed:
    """Tests for the DYNAMIC branch when ``asset_feed``
    (``ad_creative.get('asset_feed_spec')``) is falsy or its key is
    entirely absent from ``ad_creative``: none of the three
    ``MetaAdsValidator`` text methods are invoked, and ``execute()``'s
    validation block completes without raising, reaching the
    ``_save_creative_to_publish``/``_build_response`` call sites with the
    same ``creative`` object by identity.

    ``campaign_setup['attributes']['meta_campaign_mode']`` is set to
    ``"DYNAMIC"`` throughout, since the ``and asset_feed`` guard in
    ``execute()`` is only relevant for the DYNAMIC branch; the falsy/absent
    ``asset_feed`` alone is what short-circuits the ``if`` before any of
    the three validators would be reached, regardless of that guard's
    left-hand side.

    Three scenarios are parametrized, all producing the same observable
    result per Requirements 11.1-11.3:

    - ``asset_feed_spec=None`` explicit (key present with value ``None``).
    - ``asset_feed_spec={}`` explicit (key present with an empty dict,
      itself falsy).
    - ``asset_feed_spec`` key completely absent from ``ad_creative``
      (``make_ad_creative()`` called without the argument, so the private
      ``ABSENT`` sentinel omits the key entirely; ``ad_creative.get(
      'asset_feed_spec')`` then falls back to ``None`` with no default
      argument, same observable result as the first scenario).

    ``_save_creative_to_publish``/``_build_response`` are patched as mocks
    here (matching the style of the sibling Images suite's analogous
    Requirement-8 tests), rather than left to run for real: this class's
    focus is exclusively the DYNAMIC validation block inside ``execute()``
    (Requirement 11), not the separately-covered behaviour of
    ``_save_creative_to_publish``/``_build_response`` themselves (tasks
    18/19), whose own ``.get('asset_feed_spec', {})`` (with a default) vs
    ``ad_creative.get('asset_feed_spec')`` (no default) asymmetry means an
    explicit ``asset_feed_spec=None`` would otherwise raise ``AttributeError``
    one call deeper, inside the real ``_save_creative_to_publish``, for a
    reason unrelated to this task's Requirement 11 scope.

    Requirements: 11.1, 11.2, 11.3
    """

    @pytest.mark.parametrize(
        "asset_feed_spec_kwargs",
        [
            pytest.param({"asset_feed_spec": None}, id="asset_feed_spec-explicit-none"),
            pytest.param({"asset_feed_spec": {}}, id="asset_feed_spec-explicit-empty-dict"),
            pytest.param({}, id="asset_feed_spec-key-absent"),
        ],
    )
    def test_no_validator_calls_and_execute_continues_without_error(
        self, use_case_factory, asset_feed_spec_kwargs
    ):
        """Exercise ``execute()`` end to end with ``meta_campaign_mode=
        "DYNAMIC"`` and each of the three falsy/absent ``asset_feed``
        scenarios above, and verify:

        - None of ``MetaAdsValidator.is_unique_texts``, ``.is_valid_length``
          nor ``.is_valid_texts_amount`` is invoked.
        - ``execute()`` raises no exception.
        - ``execute()`` continues on to ``_save_creative_to_publish``/
          ``_build_response``: both are invoked exactly once with the same
          ``creative`` object by identity, and ``execute()`` returns
          exactly ``_build_response``'s result, by identity.

        ``self.titles``/``self.bodies``/``self.descriptions`` are left
        non-empty (via ``make_pre_check_texts_data`` overrides below)
        precisely so that, if the ``and asset_feed`` guard were broken and
        the validation block ran anyway, at least one of the three patched
        validators would be called and this test would fail; this makes
        the "no validator calls" assertion meaningful rather than vacuous.

        Requirements: 11.1, 11.2, 11.3
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        ad_creative = make_ad_creative(**asset_feed_spec_kwargs)
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

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            build_response_result = {"sentinel": "build-response-result"}
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result


class TestStandardBranchTextsValidationSuccess:
    """Tests for the success scenario of the Rama_STANDARD text validation
    block within ``execute()``: exactly one Título_Candidato/Cuerpo_Candidato/
    Descripción_Candidato (``Valor_Candidato == 1``) whose text passes
    ``MetaAdsValidator.is_valid_length``.

    Unlike the sibling ``FacebookSavePreCheckImagesUseCase`` (whose
    STANDARD branch delegates to its own ``_validate_images_standard``),
    ``FacebookSavePreCheckTextsUseCase``'s STANDARD branch is implemented
    inline inside ``execute()``: there is no method of its own to invoke
    directly, so every scenario below exercises ``execute()`` end to end
    (with ``_save_creative_to_publish``/``_build_response`` left
    unpatched, running for real) and asserts on the resulting
    ``Link_Data`` (``object_story_spec['link_data']``) mutation, conforme
    al Contrato_de_Anotación_STANDARD.

    Requirements: 2.2, 2.3, 2.7
    """

    @pytest.mark.parametrize(
        "field_name, link_key, valid_key, singular_type",
        [
            pytest.param("titles", "name", "title_valid", "title", id="title"),
            pytest.param("bodies", "message", "body_valid", "body", id="body"),
            pytest.param(
                "descriptions",
                "description",
                "description_valid",
                "description",
                id="description",
            ),
        ],
    )
    def test_single_valid_length_candidate_is_annotated_onto_link_data(
        self, use_case_factory, field_name, link_key, valid_key, singular_type
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and exactly one candidate (``Valor_Candidato == 1``) for the field
        under test whose text passes ``MetaAdsValidator.is_valid_length``,
        verify that ``execute()`` annotates the pre-existing ``Link_Data``
        dict, by identity, with:

        - ``link_data[valid_key] is True``.
        - ``link_data[link_key]`` equal to the single candidate's text.

        The other two text fields are left at their default (empty list,
        ``Valor_Candidato == 0``), which the same inline loop already
        annotates as ``*_valid = False`` independently of the field under
        test (Requirement 2.4, not asserted here); this does not interfere
        with the assertions on the field under test.

        Requirements: 2.2, 2.3
        """
        candidate_text = f"Valid {singular_type} text"
        pre_check_texts_data = make_pre_check_texts_data(
            **{field_name: [make_text_entry(candidate_text)]}
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
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

        assert story_spec["link_data"] is link_data
        assert link_data[valid_key] is True
        assert link_data[link_key] == candidate_text


class TestStandardBranchTextsInvalidCandidateCount:
    """Tests for the Rama_STANDARD text validation block within
    ``execute()`` when ``Valor_Candidato`` (the number of candidates for
    the field under test) is different from 1: either ``0`` (empty list)
    or greater than ``1`` (two candidates).

    Like its sibling ``TestStandardBranchTextsValidationSuccess``, this
    class exercises ``execute()`` end to end (with
    ``_save_creative_to_publish``/``_build_response`` left unpatched,
    running for real) and asserts on the resulting ``Link_Data``
    (``object_story_spec['link_data']``) mutation, conforme al
    Contrato_de_Anotación_STANDARD.

    Each scenario below only overrides the field under test
    (``titles``/``bodies``/``descriptions``); the other two text fields
    are left at their default (empty list, ``Valor_Candidato == 0``),
    which also does not invoke ``MetaAdsValidator.is_valid_length``, so
    patching it once for the whole ``execute()`` call and asserting it
    was never invoked is enough to characterize "not invoked for that
    field" without needing to inspect individual call arguments.

    Requirements: 2.4
    """

    @pytest.mark.parametrize(
        "field_name, link_key, valid_key, singular_type",
        [
            pytest.param("titles", "name", "title_valid", "title", id="title"),
            pytest.param("bodies", "message", "body_valid", "body", id="body"),
            pytest.param(
                "descriptions",
                "description",
                "description_valid",
                "description",
                id="description",
            ),
        ],
    )
    @pytest.mark.parametrize(
        "candidate_count",
        [
            pytest.param(0, id="zero-candidates"),
            pytest.param(2, id="two-candidates"),
        ],
    )
    def test_invalid_candidate_count_is_annotated_false_without_invoking_is_valid_length(
        self,
        use_case_factory,
        field_name,
        link_key,
        valid_key,
        singular_type,
        candidate_count,
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and ``Valor_Candidato`` (the candidate count for the field under
        test) equal to ``0`` or ``2``, verify that ``execute()`` annotates
        the pre-existing ``Link_Data`` dict, by identity, with:

        - ``link_data[valid_key] is False``.
        - ``MetaAdsValidator.is_valid_length`` was NOT invoked (for any
          field: the other two text fields are also at
          ``Valor_Candidato == 0`` by default, so this assertion covers
          the field under test specifically).
        - ``link_data[link_key]`` left at its default (``None``), i.e.
          NOT modified from ``make_link_data()``'s default.

        Requirements: 2.4
        """
        candidates = [
            make_text_entry(f"{singular_type} candidate {index}")
            for index in range(candidate_count)
        ]
        pre_check_texts_data = make_pre_check_texts_data(**{field_name: candidates})
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
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

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert story_spec["link_data"] is link_data
        assert link_data[valid_key] is False
        mock_is_valid_length.assert_not_called()
        assert link_data[link_key] is None


class TestStandardBranchTextsInvalidLength:
    """Tests for the Rama_STANDARD text validation block within
    ``execute()`` when ``Valor_Candidato == 1`` but the single candidate's
    text fails the real ``MetaAdsValidator.is_valid_length`` check (i.e.
    the text is longer than the per-field maximum: 255 characters for
    ``"title"``/``"description"``, 1024 characters for ``"body"``).

    Like its siblings ``TestStandardBranchTextsValidationSuccess`` and
    ``TestStandardBranchTextsInvalidCandidateCount``, this class exercises
    ``execute()`` end to end (with ``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real) and asserts on
    the resulting ``Link_Data`` (``object_story_spec['link_data']``)
    mutation, conforme al Contrato_de_Anotación_STANDARD. Unlike its
    siblings, ``MetaAdsValidator.is_valid_length`` itself is never
    patched here: the oversized candidate text is exercised against the
    real implementation to confirm the observed ``False`` outcome is
    genuinely produced by the length check, not by a test double.

    Requirements: 2.8
    """

    @pytest.mark.parametrize(
        "field_name, link_key, valid_key, singular_type, oversized_text",
        [
            pytest.param(
                "titles", "name", "title_valid", "title", "A" * 300, id="title"
            ),
            pytest.param(
                "bodies", "message", "body_valid", "body", "A" * 1025, id="body"
            ),
            pytest.param(
                "descriptions",
                "description",
                "description_valid",
                "description",
                "A" * 300,
                id="description",
            ),
        ],
    )
    def test_single_invalid_length_candidate_is_annotated_false_without_overwriting_link_data(
        self,
        use_case_factory,
        field_name,
        link_key,
        valid_key,
        singular_type,
        oversized_text,
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and exactly one candidate (``Valor_Candidato == 1``) for the field
        under test whose text exceeds the per-field maximum length
        enforced by the real ``MetaAdsValidator.is_valid_length``, verify
        that ``execute()`` annotates the pre-existing ``Link_Data`` dict,
        by identity, with:

        - ``link_data[valid_key] is False``.
        - ``link_data[link_key]`` left at its default (``None``), i.e.
          NOT overwritten with the invalid candidate's text: the inline
          ``if valid:`` guard in the production code only assigns
          ``link_data[link_key]`` when ``is_valid_length`` marks the
          candidate valid.

        The other two text fields are left at their default (empty list,
        ``Valor_Candidato == 0``), which the same inline loop already
        annotates as ``*_valid = False`` independently of the field under
        test (Requirement 2.4, not asserted here); this does not interfere
        with the assertions on the field under test.

        Requirements: 2.8
        """
        pre_check_texts_data = make_pre_check_texts_data(
            **{field_name: [make_text_entry(oversized_text)]}
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
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

        assert story_spec["link_data"] is link_data
        assert link_data[valid_key] is False
        assert link_data[link_key] is None


class TestStandardBranchTextsMissingLinkData:
    """Tests for the Rama_STANDARD text validation block within
    ``execute()`` when ``story_spec`` lacks the ``link_data`` key
    entirely, or carries it with an explicit ``None`` value.

    Like its siblings ``TestStandardBranchTextsValidationSuccess``,
    ``TestStandardBranchTextsInvalidCandidateCount`` and
    ``TestStandardBranchTextsInvalidLength``, this class exercises
    ``execute()`` end to end (with ``_save_creative_to_publish``/
    ``_build_response`` left unpatched, running for real). ``story_spec``
    itself is built directly via ``make_object_story_spec()`` (not via the
    ``link_data=...`` override used by the sibling classes above), with an
    unrelated key added when ``link_data`` is meant to be absent entirely,
    so ``story_spec`` stays truthy (an empty dict would make the
    surrounding ``elif ... and story_spec:`` guard in ``execute()`` skip
    the STANDARD branch altogether, which would make this scenario
    vacuous).

    Each scenario provides exactly one valid candidate
    (``Valor_Candidato == 1`` with a length-valid text) for each of
    title/body/description, so the inline Rama_STANDARD loop actually
    writes into ``link_data`` for all three fields, letting the assertions
    below confirm that a single, brand new ``link_data`` dict is created
    and reassigned onto ``story_spec['link_data']``, shared by every
    field's annotation, rather than a separate dict per field.

    Requirements: 2.5
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
    def test_missing_or_none_link_data_is_replaced_by_new_shared_dict(
        self, use_case_factory, build_story_spec
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        that either omits the ``link_data`` key entirely or carries it
        with an explicit ``None`` value, and exactly one valid candidate
        for each of title/body/description, verify that ``execute()``:

        - Raises no exception.
        - Creates a brand new dict and reassigns it onto
          ``story_spec['link_data']`` (it is a real dict, not ``None``
          and not absent, once ``execute()`` returns).
        - Uses that same new dict, by identity, for all three fields'
          annotations: ``title_valid``/``name``, ``body_valid``/
          ``message`` and ``description_valid``/``description`` are all
          found together on the single ``story_spec['link_data']`` object
          (there is no separate ``link_data`` per field).

        Requirements: 2.5
        """
        title_text = "Valid title text"
        body_text = "Valid body text"
        description_text = "Valid description text"
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[make_text_entry(title_text)],
            bodies=[make_text_entry(body_text)],
            descriptions=[make_text_entry(description_text)],
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        story_spec = build_story_spec()
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

        link_data = story_spec["link_data"]
        assert isinstance(link_data, dict)
        assert link_data is not None

        assert link_data["title_valid"] is True
        assert link_data["name"] == title_text
        assert link_data["body_valid"] is True
        assert link_data["message"] == body_text
        assert link_data["description_valid"] is True
        assert link_data["description"] == description_text


class TestStandardBranchFullExecuteResponse:
    """Tests for the full ``execute()`` round trip in STANDARD mode: with a
    truthy ``story_spec`` built via ``make_link_data()`` and exactly one
    valid candidate (``Valor_Candidato == 1``, length-valid) for each of
    title/body/description, verify that the dict *returned* by
    ``execute()`` (not just the mutated ``link_data``) reflects
    ``titles``/``bodies``/``descriptions`` conforme a las anotaciones
    esperadas.

    Unlike the sibling classes above (which only assert on the mutated
    ``story_spec['link_data']``), this class exercises ``execute()``
    completely unpatched (real ``MetaAdsValidator.is_valid_length``, real
    ``_save_creative_to_publish``, real ``_build_response``) and asserts on
    its return value, characterizing the STANDARD-mode branch of
    ``_build_response`` (inherited from the Caso_de_Uso_Padre), which maps
    ``link_data.get('name')``/``.get('message')``/``.get('description')``
    into single-item lists of the form
    ``[{'text': value, 'valid_length': flag}]``.

    Requirements: 8.3
    """

    def test_execute_returns_response_reflecting_texts_annotations(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        (via ``make_link_data()``) and exactly one valid candidate for
        each of title/body/description, verify that the dict returned by
        ``execute()`` has:

        - ``response["titles"] == [{'text': title_text, 'valid_length': True}]``
        - ``response["bodies"] == [{'text': body_text, 'valid_length': True}]``
        - ``response["descriptions"] == [{'text': description_text, 'valid_length': True}]``

        conforming exactly to ``_build_response``'s
        ``_as_single_item_list(link_data.get(...), link_data.get(..._valid, False))``
        mapping for the STANDARD-mode (``object_story_spec``/``link_data``)
        branch.

        Requirements: 8.3
        """
        title_text = "Valid title text"
        body_text = "Valid body text"
        description_text = "Valid description text"
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[make_text_entry(title_text)],
            bodies=[make_text_entry(body_text)],
            descriptions=[make_text_entry(description_text)],
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
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

        # Sanity check: the STANDARD-mode branch of ``_build_response`` was
        # actually exercised (``link_data`` was annotated as expected),
        # before asserting on the returned response itself.
        assert link_data["title_valid"] is True
        assert link_data["name"] == title_text
        assert link_data["body_valid"] is True
        assert link_data["message"] == body_text
        assert link_data["description_valid"] is True
        assert link_data["description"] == description_text

        assert response["titles"] == [
            {"text": title_text, "valid_length": True}
        ]
        assert response["bodies"] == [
            {"text": body_text, "valid_length": True}
        ]
        assert response["descriptions"] == [
            {"text": description_text, "valid_length": True}
        ]


class TestStandardBranchRealLengthValidationStaysNetworkFree:
    """Explicit scenario for Requirement 8.5: exercising the real,
    unpatched ``MetaAdsValidator.is_valid_length`` from the Rama_STANDARD
    of ``execute()`` never performs a real HTTP request.

    Every scenario in ``TestStandardBranchTextsValidationSuccess``,
    ``TestStandardBranchTextsMissingLinkData`` and
    ``TestStandardBranchFullExecuteResponse`` already exercises
    ``execute()`` (and therefore ``MetaAdsValidator.is_valid_length``) for
    real, without patching it, under the module-wide, ``autouse=True``
    ``deny_network`` fixture (which replaces
    ``requests.sessions.Session.request`` with a function that raises
    ``AssertionError`` on any call): those scenarios already passing is
    itself proof that ``is_valid_length`` never reaches the network.  This
    class adds one minimal, explicitly-named scenario for Requirement
    8.5's own traceability, rather than relying on that fact being merely
    incidental to scenarios written for Requirements 2.2/2.3/2.5/8.3.

    ``is_valid_length`` is a pure, in-memory string-length check (it never
    imports ``requests`` nor issues any I/O); the assertions below on
    ``link_data`` additionally confirm the real validator actually ran
    (as opposed to, say, an exception being swallowed before reaching it),
    so a passing test is not vacuous.

    Requirements: 8.5
    """

    def test_real_is_valid_length_execution_raises_no_network_error(
        self, use_case_factory
    ):
        """With ``meta_campaign_mode="STANDARD"``, a truthy ``story_spec``
        and exactly one length-valid Título_Candidato
        (``Valor_Candidato == 1``), exercise ``execute()`` end to end with
        ``MetaAdsValidator.is_valid_length`` completely unpatched.

        The ``deny_network`` fixture (autouse, module-wide) remains active
        and unmodified for this test: it is not disabled, re-patched or
        asserted on directly. If the real ``is_valid_length`` call (or
        anything else reached by this ``execute()`` invocation) attempted a
        real HTTP request, ``deny_network`` would make
        ``requests.sessions.Session.request`` raise ``AssertionError``,
        which would surface as this test failing. The test passing is
        therefore direct, explicit evidence that no real HTTP request
        occurred while the real length-validation logic ran.

        Requirements: 8.5
        """
        title_text = "Valid title text"
        pre_check_texts_data = make_pre_check_texts_data(
            titles=[make_text_entry(title_text)]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
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

            # No patch.object(MetaAdsValidator, "is_valid_length", ...) here:
            # the real implementation runs, under the still-active
            # ``deny_network`` guard.
            use_case.execute()

        # Sanity check: the real, unpatched ``is_valid_length`` actually
        # ran and produced the expected annotation, so the absence of a
        # ``deny_network`` failure above is not merely because the
        # STANDARD branch was skipped.
        assert link_data["title_valid"] is True
        assert link_data["name"] == title_text


class TestStandardSpecDoesNotRegressDynamicBranch:
    """Tests for Requirement 7.1/7.3/7.4 (no regresión): confirm that the
    STANDARD-branch implementation added by this specification did not
    change the observable behaviour of the pre-existing DYNAMIC branch of
    Caso_de_Uso_Textos, and that the STANDARD ``elif`` never runs when
    ``meta_campaign_mode == "DYNAMIC"`` (the ``if``/``elif`` are mutually
    exclusive on the same ``campaign_setup`` value, so the STANDARD block
    should be fully skipped).

    These two scenarios are additions, not replacements: no assertion of
    the pre-existing ``TestDynamicBranchTitlesValidation``,
    ``TestDynamicBranchBodiesValidation``, ``TestDynamicBranchDescriptionsValidation``
    or ``TestDynamicBranchCallOrderAcrossFields`` classes is modified.

    Requirements: 7.1, 7.3, 7.4
    """

    def test_dynamic_branch_annotations_unaffected_by_standard_branch_addition(
        self, use_case_factory
    ):
        """Regression smoke test: exercise ``execute()`` end to end with
        ``meta_campaign_mode="DYNAMIC"``, a truthy ``asset_feed`` and a
        falsy ``story_spec`` (key entirely absent from ``adCreative``, as
        already exercised by ``TestDynamicBranchMissingAssetFeed``-style
        scenarios), and verify that the DYNAMIC-branch annotations on
        ``asset_feed`` continue to work exactly as already characterized
        by the existing DYNAMIC-branch test classes: ``unique_titles``,
        ``titles_valid_amount`` computed via the real, unpatched
        ``MetaAdsValidator`` implementation, and ``asset_feed['titles']``
        overwritten by identity with ``self.titles``.

        This is a lightweight smoke test, not a duplicate of every
        existing DYNAMIC-branch assertion: its only purpose is to confirm
        that adding the STANDARD ``elif`` body did not disturb the ``if``
        branch it sits alongside.

        Requirements: 7.1, 7.4
        """
        titles = [make_text_entry("Short title"), make_text_entry("Another title")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(titles=["stale-value"])
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

        assert asset_feed["unique_titles"] is True
        assert asset_feed["titles_valid_amount"] is True
        assert asset_feed["titles"] is titles
        assert asset_feed["titles"] != ["stale-value"]

    def test_standard_logic_does_not_execute_when_mode_is_dynamic(
        self, use_case_factory
    ):
        """Build a scenario where ``story_spec``/``link_data`` IS present
        and truthy, in addition to a truthy ``asset_feed``, with
        ``meta_campaign_mode="DYNAMIC"``, and verify that ``link_data`` is
        left completely untouched (no ``title_valid``/``name``/etc.
        annotations added): the STANDARD ``elif`` never ran because the
        ``if`` (DYNAMIC) condition already matched first.

        Requirements: 7.3, 7.4
        """
        titles = [make_text_entry("Only title")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=[], descriptions=[]
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
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

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        assert link_data == link_data_snapshot
        assert "title_valid" not in link_data
        assert "body_valid" not in link_data
        assert "description_valid" not in link_data
        assert story_spec["link_data"] is link_data


class TestUnsupportedMetaCampaignModeRaisesValueError:
    """Tests for ``execute()`` when
    ``campaign_setup['attributes']['meta_campaign_mode']`` is neither
    ``"DYNAMIC"`` nor ``"STANDARD"``: the call aborts by propagating a
    ``ValueError`` and the validation block never runs.

    The abort originates in ``_set_creative_type``, which converts the raw
    mode strictly::

        self.creative_type = CreativeType(
            campaign_setup.get('attributes', {}).get('meta_campaign_mode')
        ).value

    ``CreativeType`` only admits ``"DYNAMIC"`` and ``"STANDARD"``, so every
    other value -- an empty string, ``None``, an arbitrary unrelated string,
    or the key being entirely absent from ``campaign_setup['attributes']``
    (so ``.get('meta_campaign_mode')`` falls back to ``None`` with no default
    argument) -- raises ``ValueError: <value> is not a valid CreativeType``.

    ``_set_creative_type(campaign_setup)`` runs immediately after
    ``_get_campaign_setup()`` and **before** the validation ``try`` block.
    The two branch conditions, which start with an equality check against
    ``CreativeType.DYNAMIC.value``/``CreativeType.STANDARD.value``
    respectively, are therefore never evaluated at all: their bodies do not
    fail to run because the comparisons came out false, they are never
    reached.

    Each parametrized scenario still uses a truthy ``asset_feed`` (a
    non-empty ``asset_feed_spec``) *and* a truthy ``story_spec`` (a non-empty
    ``object_story_spec``) at the same time, and that remains the reason the
    assertions below are non-vacuous: both branches' right-hand operands are
    satisfied, so if the comparisons were ever reached one branch would run,
    invoking at least one of the three patched validators and/or mutating
    ``asset_feed_spec``/``object_story_spec``. Observing neither effect is
    therefore evidence of the abort happening upstream of the comparisons,
    not of a falsy-operand no-op.

    Requirements: 13.1, 13.2
    """

    @pytest.mark.parametrize(
        "meta_campaign_mode_kwargs, expected_message",
        [
            pytest.param(
                {"meta_campaign_mode": ""},
                "'' is not a valid CreativeType",
                id="meta_campaign_mode-empty-string",
            ),
            pytest.param(
                {"meta_campaign_mode": None},
                "None is not a valid CreativeType",
                id="meta_campaign_mode-none",
            ),
            pytest.param(
                {"meta_campaign_mode": "SOME_OTHER_MODE"},
                "'SOME_OTHER_MODE' is not a valid CreativeType",
                id="meta_campaign_mode-arbitrary-value",
            ),
            pytest.param(
                None,
                "None is not a valid CreativeType",
                id="meta_campaign_mode-key-absent",
            ),
        ],
    )
    def test_execute_propagates_value_error_with_no_validator_calls_and_no_mutation_regardless_of_truthy_asset_feed_and_story_spec(
        self, use_case_factory, meta_campaign_mode_kwargs, expected_message
    ):
        """Exercise ``execute()`` with each of the four unsupported/absent
        ``meta_campaign_mode`` scenarios above, a truthy ``asset_feed`` and a
        truthy ``story_spec`` simultaneously, and verify:

        - ``execute()`` propagates a ``ValueError`` whose message is exactly
          the one carried in the parametrization table, raised by
          ``_set_creative_type`` before the validation block is entered.
        - None of ``MetaAdsValidator.is_unique_texts``, ``.is_valid_length``
          nor ``.is_valid_texts_amount`` is invoked.
        - ``asset_feed_spec``/``object_story_spec`` compare equal, key for
          key, to a snapshot taken before ``execute()`` runs: neither
          dict receives any new key nor has an existing key overwritten.
        - Neither ``_save_creative_to_publish`` nor ``_build_response`` nor
          ``ad_channel_repository.update`` is ever called: the abort happens
          upstream of the whole persistence path.
        - ``use_case.creative_type`` still holds the ``''`` left by the
          constructor, because ``CreativeType(...)`` raises before the
          assignment, so the failure leaves no intermediate state.

        ``self.titles``/``self.bodies``/``self.descriptions`` are left
        non-empty, and ``asset_feed_spec`` is seeded with a preexisting
        ``titles`` entry distinct from ``self.titles``, precisely so that,
        if the abort did not happen and a validation branch ran anyway, at
        least one patched validator would be called and/or
        ``asset_feed_spec['titles']`` would be overwritten, and this test
        would fail. ``_save_creative_to_publish``/``_build_response`` are
        patched here (matching the style of ``TestDynamicBranchMissingAssetFeed``
        and of the falsy-``story_spec`` STANDARD-branch no-op scenarios
        elsewhere in this file)
        so that reaching them can be ruled out by assertion; this class's
        focus is exclusively the absence of any effect downstream of
        ``_set_creative_type``, not the separately-covered behaviour of those
        two methods themselves (tasks 18/19).

        For the ``meta_campaign_mode-key-absent`` scenario,
        ``campaign_setup`` is built manually as ``{"attributes": {}}``
        instead of via ``make_campaign_setup`` (which always sets the key,
        even to ``None``), so that ``meta_campaign_mode`` is genuinely
        missing from ``attributes``, not merely present with value
        ``None``.

        Requirements: 13.1, 13.2
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed_spec = make_asset_feed_spec(
            titles=[make_text_entry("preexisting title")]
        )
        object_story_spec = make_object_story_spec(some_key="some_value")
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed_spec, object_story_spec=object_story_spec
        )
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)

        if meta_campaign_mode_kwargs is None:
            # Key completely absent from `attributes`, not merely `None`.
            campaign_setup = {"attributes": {}}
        else:
            campaign_setup = make_campaign_setup(**meta_campaign_mode_kwargs)

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        asset_feed_spec_snapshot = dict(asset_feed_spec)
        object_story_spec_snapshot = dict(object_story_spec)

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(ValueError) as exc_info:
                use_case.execute()

        assert str(exc_info.value) == expected_message
        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        assert asset_feed_spec == asset_feed_spec_snapshot
        assert object_story_spec == object_story_spec_snapshot
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()
        mock_ad_channel_repo_instance.update.assert_not_called()
        assert use_case.creative_type == ""


class TestMalformedCreativeAdsAdCreativeStructures:
    """Tests for the 4-level matrix of malformed ``creative``/``ads``/
    ``adCreative`` structures reaching ``execute()``'s validation block:

    ``asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')``
    ``story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')``

    - ``ads`` absent or an empty list: ``creative.get('ads', [])`` falls
      back to (or already is) ``[]``, and indexing ``[0]`` on that empty
      list raises ``IndexError`` immediately, on the very first line of
      the ``try`` block, before either extraction assignment completes and
      before any of the three ``MetaAdsValidator`` text methods or
      ``_save_creative_to_publish``/``_build_response`` are reached.
    - ``adCreative`` present with an explicit ``None`` value: ``ads[0].get(
      'adCreative', {})`` returns the actual value ``None`` (the ``{}``
      default only applies when the key is entirely absent), so calling
      ``.get('asset_feed_spec')`` on ``None`` raises ``AttributeError``,
      again on the first extraction line, before ``story_spec`` is ever
      assigned and before ``_save_creative_to_publish``/``_build_response``.
    - ``adCreative={}`` (present, empty dict): both ``.get('asset_feed_spec')``
      and ``.get('object_story_spec')`` on ``{}`` return ``None`` with no
      exception, so ``asset_feed``/``story_spec`` end up ``None``, neither
      validation branch's condition is satisfied, and ``execute()``
      continues on to ``_save_creative_to_publish``/``_build_response``.
    - ``adCreative`` key completely absent from ``ads[0]``: ``ads[0].get(
      'adCreative', {})`` now falls back to its ``{}`` default (the key is
      genuinely missing), producing the exact same ``{}`` as the previous
      scenario and therefore the exact same no-exception result.

    Every scenario below sets ``self.titles``/``self.bodies``/
    ``self.descriptions`` to non-empty content and ``meta_campaign_mode=
    "DYNAMIC"`` (irrelevant to the two exception scenarios, since the
    exception fires before ``meta_campaign_mode`` is ever consulted, but
    kept constant across the class for consistency and so the two
    no-exception scenarios would fail if a validator were spuriously
    invoked).

    Requirements: 14.1, 14.2, 14.3, 14.4
    """

    @pytest.mark.parametrize(
        "build_creative",
        [
            pytest.param(
                lambda: _make_creative_without_ads_key(),
                id="ads-key-absent",
            ),
            pytest.param(
                lambda: make_creative(ads=[]),
                id="ads-empty-list",
            ),
        ],
    )
    def test_index_error_when_ads_absent_or_empty_before_any_double_is_invoked(
        self, use_case_factory, build_creative
    ):
        """With ``ads`` absent or an empty list, verify ``execute()``
        propagates ``IndexError`` and that none of the three
        ``MetaAdsValidator`` text methods, nor ``_save_creative_to_publish``,
        nor ``_build_response``, were invoked beforehand: per the real
        code order, the ``IndexError`` fires on the very first line inside
        the ``try`` block (the ``asset_feed`` extraction), strictly before
        any of those four doubles could ever be reached.

        Requirements: 14.1
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        creative = build_creative()
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(IndexError):
                use_case.execute()

        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()

    def test_attribute_error_when_adcreative_is_explicit_none_before_save(
        self, use_case_factory
    ):
        """With ``ads`` non-empty and ``ads[0]['adCreative']=None`` explicit,
        verify ``execute()`` propagates ``AttributeError`` (raised by
        calling ``.get('asset_feed_spec')`` on ``None``), and that none of
        the three ``MetaAdsValidator`` text methods nor
        ``_save_creative_to_publish``/``_build_response`` were invoked
        beforehand: the ``AttributeError`` fires on the ``asset_feed``
        extraction line itself, before ``story_spec`` is even assigned.

        Requirements: 14.2
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        ad = make_ad(ad_creative=None)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(AttributeError):
                use_case.execute()

        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()

    @pytest.mark.parametrize(
        "build_ad",
        [
            pytest.param(lambda: make_ad(ad_creative={}), id="adcreative-empty-dict"),
            pytest.param(lambda: make_ad(), id="adcreative-key-absent"),
        ],
    )
    def test_no_exception_when_adcreative_empty_or_absent_and_execute_continues(
        self, use_case_factory, build_ad
    ):
        """With ``ads`` non-empty and ``ads[0]['adCreative']`` either an
        empty dict or the key completely absent, both produce the exact
        same observable result: ``.get('adCreative', {})`` yields ``{}``
        either way (via the explicit value in the first case, via the
        default in the second), so ``asset_feed``/``story_spec`` both end
        up ``None`` with no exception, neither validation branch's
        condition is satisfied, and ``execute()`` continues on to
        ``_save_creative_to_publish``/``_build_response``, both invoked
        exactly once with the same ``creative`` object by identity;
        ``execute()`` returns exactly ``_build_response``'s result, by
        identity.

        Requirements: 14.3, 14.4
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        ad = build_ad()
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ) as mock_is_unique_texts, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ) as mock_is_valid_length, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ) as mock_is_valid_texts_amount, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            build_response_result = {"sentinel": "build-response-result"}
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        assert_no_text_validator_calls(
            mock_is_unique_texts, mock_is_valid_length, mock_is_valid_texts_amount
        )
        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result


def _make_creative_without_ads_key():
    """Build a fresh ``creative`` dict with the ``ads`` key entirely
    absent, distinct from ``make_creative(ads=[])`` (key present, empty
    list). Both feed the same ``creative.get('ads', [])[0]`` code path
    to the same ``IndexError``, but only this helper exercises the
    "key absent" half of Requirement 14.1's "absent or empty" wording.

    Requirements: 18.2, 18.3
    """
    creative = make_creative()
    del creative["ads"]
    return creative


class TestTryExceptPassThrough:
    """Tests for the ``try/except Exception as e: raise e`` block inside
    ``execute()``'s validation section:

    .. code-block:: python

        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            ...
        except Exception as e:
            raise e

    ``raise e`` re-raises the exact same exception object that was just
    caught, with no transformation applied to either its type or its
    ``str()`` message: no prefix, no suffix, no wrapping in a different
    exception class, no ``from``-chaining that would alter what
    ``type(e)``/``str(e)`` report. This is observationally equivalent to
    the ``try/except`` block not existing at all: if the ``try/except
    Exception as e: raise e`` were deleted entirely, the original
    exception raised on the extraction line would propagate out of
    ``execute()`` uncaught, with its original type and message
    untouched — which is exactly what happens *with* the block present,
    since ``except Exception as e: raise e`` performs no transformation
    before re-raising. The only way a ``try/except`` like this could
    change observable behaviour is by wrapping (e.g. ``raise
    RuntimeError(str(e))``) or by altering the exception in some other
    way; this test proves neither occurs by comparing the exception
    observed from ``execute()`` against the exception Python itself
    raises for the exact same underlying operation
    (``None.get('asset_feed_spec')``), performed independently, outside
    of ``execute()`` and outside of any ``try/except`` whatsoever.

    Requirements: 15.1, 15.2
    """

    def test_attribute_error_type_and_message_are_unchanged_end_to_end(
        self, use_case_factory
    ):
        """Reuse the ``AttributeError`` scenario from task 16.1
        (``TestMalformedCreativeAdsAdCreativeStructures.
        test_attribute_error_when_adcreative_is_explicit_none_before_save``,
        Requirement 14.2): ``ads[0]['adCreative']`` is explicit ``None``,
        so the first line inside the ``try`` block
        (``creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')``)
        calls ``.get('asset_feed_spec')`` on ``None`` and raises
        ``AttributeError`` *inside* the ``try`` block, which
        ``except Exception as e: raise e`` catches and immediately
        re-raises out of ``execute()``.

        Independently of ``execute()``, and outside of any
        ``try/except`` of our own, this test performs the exact same
        underlying operation (``None.get('asset_feed_spec')``) directly,
        to capture the ``AttributeError`` that Python itself raises for
        that operation with zero interception.

        Asserting that ``type(...)`` and ``str(...)`` are identical for
        both exceptions demonstrates that the ``try/except Exception as
        e: raise e`` block changed nothing observable: the exception
        that escapes ``execute()`` has the exact same type and the exact
        same message as the exception Python raises natively for
        ``None.get(...)``, with no prefix/suffix/wrapping added by the
        ``except`` clause. This is the same outcome that would be
        observed if the ``try/except`` block were removed entirely
        (Requirement 15.2), since an uncaught exception also propagates
        with its original type and message unchanged; ``raise e`` with
        no transformation reproduces that exact outcome explicitly.

        Requirements: 15.1, 15.2
        """
        titles = [make_text_entry("Title one")]
        bodies = [make_text_entry("Body one")]
        descriptions = [make_text_entry("Description one")]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        ad = make_ad(ad_creative=None)
        creative = make_creative(ads=[ad])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_unique_texts"
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_length"
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_texts_amount"
        ), patch.object(
            use_case, "_save_creative_to_publish"
        ), patch.object(
            use_case, "_build_response"
        ):
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(AttributeError) as exc_info_from_execute:
                use_case.execute()

        # Independently reproduce the exact same underlying operation
        # (``None.get('asset_feed_spec')``, mirroring what
        # ``ads[0].get('adCreative', {}).get('asset_feed_spec')`` reduces
        # to when ``adCreative`` is explicit ``None``) outside of
        # ``execute()`` and outside of any ``try/except`` of our own, to
        # capture what Python itself raises for that operation with no
        # interception at all.
        with pytest.raises(AttributeError) as exc_info_from_direct_operation:
            None.get('asset_feed_spec')

        assert type(exc_info_from_execute.value) is AttributeError
        assert type(exc_info_from_execute.value) is type(
            exc_info_from_direct_operation.value
        )
        assert str(exc_info_from_execute.value) == str(
            exc_info_from_direct_operation.value
        )


class TestSaveCreativeToPublish:
    """Tests for ``_save_creative_to_publish`` (inherited from the
    Caso_de_Uso_Abuelo, ``FacebookGeneratePreCheckCreativeUseCase``):

    .. code-block:: python

        def _save_creative_to_publish(self, creative):
            ad_channel_id = creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)
            data = {
                'channel_creative': creative
            }
            self.ad_channel_repository.update(ad_channel_id, data)

    Every scenario below invokes ``_save_creative_to_publish`` directly on
    a use case built via ``use_case_factory``, without going through
    ``execute()``, since that is the only way to isolate this method's own
    ``creative.get('ads')`` (no default) from the different
    ``creative.get('ads', [])`` (``[]`` default) used by ``execute()``'s
    own validation block.

    Requirements: 16.1, 16.2, 16.3, 16.4
    """

    def test_exact_call_with_truthy_ad_channel_id_and_creative_identity(
        self, use_case_factory
    ):
        """With ``asset_feed_spec['ad_channel_id']`` present and truthy,
        verify ``ad_channel_repository.update`` is invoked exactly once
        with the exact positional arguments
        ``(ad_channel_id, {'channel_creative': creative})``, where
        ``ad_channel_id`` is the exact truthy value read from
        ``asset_feed_spec['ad_channel_id']``, and ``creative`` inside the
        recorded call is the same object, by identity, as the one passed
        in to ``_save_creative_to_publish``.

        Requirements: 16.1, 16.2
        """
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        asset_feed_spec = make_asset_feed_spec(ad_channel_id="channel-99")
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])

        use_case._save_creative_to_publish(creative)

        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            "channel-99",
            {"channel_creative": creative},
        )
        call_args = mock_ad_channel_repo_instance.update.call_args
        assert call_args.args[0] == "channel-99"
        assert call_args.args[1]["channel_creative"] is creative

    @pytest.mark.parametrize(
        "build_ad",
        [
            pytest.param(
                lambda: make_ad(
                    ad_creative=make_ad_creative(asset_feed_spec=ABSENT)
                ),
                id="asset-feed-spec-absent",
            ),
            pytest.param(
                lambda: make_ad(ad_creative=make_ad_creative()),
                id="adcreative-empty-no-asset-feed-spec",
            ),
            pytest.param(
                lambda: make_ad(ad_creative=ABSENT),
                id="adcreative-key-absent",
            ),
            pytest.param(
                lambda: make_ad(
                    ad_creative=make_ad_creative(
                        asset_feed_spec=make_asset_feed_spec()
                    )
                ),
                id="ad-channel-id-absent-in-asset-feed-spec",
            ),
        ],
    )
    def test_ad_channel_id_defaults_to_zero_per_missing_level(
        self, use_case_factory, build_ad
    ):
        """Parametrizes the absence of ``adCreative``, ``asset_feed_spec``
        or ``ad_channel_id`` separately (with ``creative['ads']``
        non-empty in every case), verifying that
        ``ad_channel_repository.update`` is invoked with the default ``0``
        as its first argument in each case: every intermediate ``.get(key,
        {})`` along ``creative.get('ads')[0].get('adCreative',
        {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)`` absorbs a
        missing key or an empty dict with its own ``{}``/``0`` default, so
        none of these four levels of absence raises, unlike the
        ``creative.get('ads')`` call itself (no default), covered
        separately below.

        Note ``make_asset_feed_spec()`` always sets ``ad_channel_id=0``
        itself; the last parametrized case (``ad_channel_id`` present but
        already ``0``) still exercises the same observable ``0`` result as
        the other three "absent" cases, so it is kept here as the
        "closest to complete, still falls back to 0" reference point of
        the matrix rather than as a fifth truly-absent scenario.

        Requirements: 16.3
        """
        ad = build_ad()
        creative = make_creative(ads=[ad])
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        use_case._save_creative_to_publish(creative)

        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            0,
            {"channel_creative": creative},
        )

    def test_isolated_call_with_ads_key_absent_raises_type_error(
        self, use_case_factory
    ):
        """Invokes ``_save_creative_to_publish`` directly and in isolation
        (not through ``execute()``) with a ``creative`` whose ``ads`` key
        is entirely absent: ``creative.get('ads')`` (no second argument,
        unlike ``execute()``'s own ``creative.get('ads', [])``) returns
        ``None``, and ``None[0]`` raises ``TypeError`` (not
        ``IndexError``, which is what an empty list would raise).

        This exact ``creative`` (``ads`` key absent) is NOT reachable via
        this path from ``execute()``: ``execute()``'s own validation block
        extracts ``asset_feed``/``story_spec`` first, using
        ``creative.get('ads', [])[0]...`` -- with the ``ads`` key absent,
        ``creative.get('ads', [])`` falls back to ``[]``, and indexing
        ``[0]`` on that empty list already raises ``IndexError`` (see
        ``TestMalformedCreativeAdsAdCreativeStructures.
        test_index_error_when_ads_absent_or_empty_before_any_double_is_invoked``,
        Requirement 14.1) long before ``execute()`` would ever reach its
        own call to ``_save_creative_to_publish(creative)`` further down.
        So the ``TypeError`` characterized here is only observable when
        ``_save_creative_to_publish`` is invoked directly and in
        isolation, as done in this test, never as a consequence of a real
        ``execute()`` call with this same malformed ``creative``.

        Requirements: 16.4
        """
        use_case, _, _ = use_case_factory()

        creative = _make_creative_without_ads_key()

        with pytest.raises(TypeError):
            use_case._save_creative_to_publish(creative)


_BUILD_RESPONSE_DEFAULTS_BRANCHES = [
    pytest.param(CreativeType.DYNAMIC.value, 0, id="dynamic-max-amount-0"),
    pytest.param(CreativeType.STANDARD.value, 1, id="standard-max-amount-1"),
]
"""Parametrización de las dos ramas de extracción de ``_build_response`` para
los escenarios de valores por defecto.

``_build_response`` despacha con ``self.creative_type == CreativeType.STANDARD.value``
(``app/v2/use_cases/meta_ads.py:2533``), atributo que ``_set_creative_type``
asigna dentro de ``execute()`` a partir de
``campaign_setup['attributes']['meta_campaign_mode']``. Los escenarios que
invocan ``_build_response`` de forma directa y aislada deben fijarlo ellos
mismos: el ``''`` que deja el constructor no es ``"STANDARD"``, así que sin
fijación explícita se tomaría siempre la rama DYNAMIC, y el estado ``''`` es
inalcanzable en producción porque ``_set_creative_type`` aborta con
``ValueError`` ante cualquier modo distinto de ``"DYNAMIC"``/``"STANDARD"``.

Para las tres formas de ``adCreative`` de estos escenarios (``asset_feed_spec``
vacío, ``adCreative`` explícitamente ``None`` y clave ``adCreative`` ausente) las
dos ramas coinciden en 25 de las 30 claves de la respuesta; la única diferencia
son los cinco ``*_max_amount``, que la rama STANDARD fija por literal a ``1``
(cardinalidad exacta 1 de un ad set STANDARD) y la DYNAMIC resuelve con
``asset_feed_spec.get('*_max_amount', 0)``. De ahí el segundo parámetro.
"""


class TestBuildResponse:
    """Tests for ``_build_response`` (inherited from the Caso_de_Uso_Abuelo,
    ``FacebookGeneratePreCheckCreativeUseCase``):

    .. code-block:: python

        def _build_response(self, creative):
            ads_to_publish = creative.get('ads')[0]

            ad_creative = ads_to_publish.get('adCreative') or {}
            object_story_spec = ad_creative.get('object_story_spec')
            asset_feed_spec = ad_creative.get('asset_feed_spec')

            if self.creative_type == CreativeType.STANDARD.value:
                object_story_spec = object_story_spec or {}
                link_data = object_story_spec.get('link_data') or {}
                call_to_action = link_data.get('call_to_action') or {}

                def _as_single_item_list(value, valid_flag):
                    return [{'text': value, 'valid_length': valid_flag}] if value else []

                image_url = link_data.get('image_url')
                images = [{
                    'url': image_url,
                    'valid': link_data.get('image_valid', False),
                    'error': link_data.get('image_error'),
                }] if image_url else []

                creative_to_publish = {
                    'name': creative.get('name'),
                    'adset_id': creative.get('id'),
                    'ad_id': ads_to_publish.get('id'),
                    'adchannel_id': object_story_spec.get('ad_channel_id', 0),
                    'daily_budget': creative.get('daily_budget'),
                    'images': images,
                    'bodies': _as_single_item_list(link_data.get('message'), link_data.get('body_valid', False)),
                    ...
                    'images_max_amount': 1,
                    'titles_max_amount': 1,
                    'bodies_max_amount': 1,
                    'descriptions_max_amount': 1,
                    'call_to_action_types_max_amount': 1,
                    ...
                    'proposal_url': link_data.get('link') or '',
                    'proposal_url_valid': link_data.get('link_url_valid', False),
                    'proposal_locations': creative.get('proposal_locations', []),
                    'locations': object_story_spec.get('locations', []),
                    'locations_valid': object_story_spec.get('locations_valid', False),
                }
            else:
                creative_to_publish = {
                    'name': creative.get('name'),
                    'adset_id': creative.get('id'),
                    'ad_id': ads_to_publish.get('id'),
                    'adchannel_id': ad_creative.get('asset_feed_spec', {}).get('ad_channel_id', 0),
                    'daily_budget': creative.get('daily_budget'),
                    'images': [...],
                    'bodies': ad_creative.get('asset_feed_spec', {}).get('bodies', []),
                    ...
                    'images_max_amount': ad_creative.get('asset_feed_spec', {}).get('images_max_amount', 0),
                    ...
                    'proposal_url': ','.join([u.get('website_url', '') for u in ad_creative.get('asset_feed_spec', {}).get('link_urls', [])]),
                    'proposal_url_valid': ad_creative.get('asset_feed_spec', {}).get('link_url_valid', False),
                    'proposal_locations': creative.get('proposal_locations', []),
                    'locations': ad_creative.get('asset_feed_spec', {}).get('locations', []),
                    'locations_valid': ad_creative.get('asset_feed_spec', {}).get('locations_valid', False),
                }

            return creative_to_publish

    Summary of the two branches. The dispatch is on the *declared* campaign
    mode: ``self.creative_type``, which ``_set_creative_type`` assigns inside
    ``execute()`` from ``campaign_setup['attributes']['meta_campaign_mode']``.
    (Commit ``be390b56`` replaced the earlier shape-based heuristic
    ``object_story_spec or not asset_feed_spec`` with this check; that
    expression no longer exists in the code.) Under STANDARD every field is
    read from ``object_story_spec``/``link_data`` and the five
    ``*_max_amount`` values are the literal ``1``; under DYNAMIC every field
    is an ``asset_feed_spec.get(key, default)`` lookup and the five
    ``*_max_amount`` values default to ``0``.

    Most scenarios below invoke ``_build_response`` directly on a use case
    built via ``use_case_factory``, without going through ``execute()``,
    to isolate this method's own key set/defaults/join logic. Those
    scenarios assign ``use_case.creative_type`` themselves, since
    ``_set_creative_type`` never runs for them and the ``''`` left by the
    constructor is not ``"STANDARD"`` (a state unreachable in production,
    because ``_set_creative_type`` raises ``ValueError`` for any mode outside
    ``{"DYNAMIC", "STANDARD"}``). The last scenario (Requirement 17.6)
    exercises a full ``execute()`` DYNAMIC round trip instead, since that is
    the only way to observe the response reflecting the in-place mutations
    performed earlier, inline, on the very same ``asset_feed_spec`` dict.

    Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6
    """

    EXPECTED_RESPONSE_KEYS = {
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

    def test_exact_key_set_and_explicit_values_reflected(self, use_case_factory):
        """With a complete ``creative`` whose ``asset_feed_spec`` supplies
        an explicit value for every field listed in Requirement 17.1
        (``images`` kept as ``[]`` here; its own url/valid/error mapping is
        exercised separately below), verify:

        - ``set(result.keys())`` equals exactly ``EXPECTED_RESPONSE_KEYS``,
          no more and no fewer keys (Requirement 17.1).
        - Every explicit value supplied is reflected exactly, unmodified,
          in the corresponding response key (Requirement 17.2).

        Requirements: 17.1, 17.2
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        bodies = [make_text_entry("body-1")]
        titles = [make_text_entry("title-1")]
        descriptions = [make_text_entry("description-1")]
        call_to_action_types = ["SHOP_NOW"]
        locations = ["location-1"]
        asset_feed_spec = make_asset_feed_spec(
            ad_channel_id="channel-1",
            images=[],
            bodies=bodies,
            titles=titles,
            descriptions=descriptions,
            call_to_action_types=call_to_action_types,
            images_valid_amount=True,
            titles_valid_amount=True,
            bodies_valid_amount=True,
            descriptions_valid_amount=True,
            call_to_action_types_valid_amount=True,
            images_max_amount=5,
            titles_max_amount=5,
            bodies_max_amount=5,
            descriptions_max_amount=5,
            call_to_action_types_max_amount=5,
            unique_titles=True,
            unique_bodies=True,
            unique_descriptions=True,
            daily_budget_valid=True,
            min_daily_budget=100,
            link_urls=[{"website_url": "http://a.com"}],
            link_url_valid=True,
            locations=locations,
            locations_valid=True,
        )
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        ad = make_ad(ad_creative=ad_creative, ad_id="ad-42")
        creative = make_creative(
            name="My Creative",
            ads=[ad],
            id="adset-42",
            daily_budget=500,
            proposal_locations=["prop-loc-1"],
        )

        result = use_case._build_response(creative)

        assert set(result.keys()) == self.EXPECTED_RESPONSE_KEYS

        assert result["name"] == "My Creative"
        assert result["adset_id"] == "adset-42"
        assert result["ad_id"] == "ad-42"
        assert result["adchannel_id"] == "channel-1"
        assert result["daily_budget"] == 500
        assert result["images"] == []
        assert result["bodies"] is bodies
        assert result["titles"] is titles
        assert result["descriptions"] is descriptions
        assert result["call_to_action_types"] is call_to_action_types
        assert result["images_valid_amount"] is True
        assert result["titles_valid_amount"] is True
        assert result["bodies_valid_amount"] is True
        assert result["descriptions_valid_amount"] is True
        assert result["call_to_action_types_valid_amount"] is True
        assert result["images_max_amount"] == 5
        assert result["titles_max_amount"] == 5
        assert result["bodies_max_amount"] == 5
        assert result["descriptions_max_amount"] == 5
        assert result["call_to_action_types_max_amount"] == 5
        assert result["unique_titles"] is True
        assert result["unique_bodies"] is True
        assert result["unique_descriptions"] is True
        assert result["daily_budget_valid"] is True
        assert result["min_daily_budget"] == 100
        assert result["proposal_url"] == "http://a.com"
        assert result["proposal_url_valid"] is True
        assert result["proposal_locations"] == ["prop-loc-1"]
        assert result["locations"] is locations
        assert result["locations_valid"] is True

    def test_images_mapped_to_url_valid_error_subdicts(self, use_case_factory):
        """Complements Requirement 17.2 for the one field whose reflection
        is not a plain passthrough: each entry of
        ``asset_feed_spec['images']`` is mapped to a fresh
        ``{'url', 'valid', 'error'}`` sub-dict, dropping any other key the
        source entry might carry (``extra_key`` below).

        Requirements: 17.1, 17.2
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        asset_feed_spec = make_asset_feed_spec(
            images=[
                {
                    "url": "http://img1.png",
                    "valid": True,
                    "error": None,
                    "extra_key": "ignored",
                },
                {"url": "http://img2.png", "valid": False, "error": "too big"},
            ]
        )
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])

        result = use_case._build_response(creative)

        assert result["images"] == [
            {"url": "http://img1.png", "valid": True, "error": None},
            {"url": "http://img2.png", "valid": False, "error": "too big"},
        ]
        assert "extra_key" not in result["images"][0]

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_defaults_for_all_omitted_fields(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """With an entirely empty ``asset_feed_spec`` (every field from
        Requirement 17.1 omitted) and no ``object_story_spec``, verify the
        exact defaults: ``False`` for the five ``*_valid_amount`` fields,
        ``[]`` for ``images``/``bodies``/``titles``/``descriptions``/
        ``call_to_action_types``/``locations``, ``False`` for
        ``unique_titles``/``unique_bodies``/``unique_descriptions``/
        ``daily_budget_valid``/``proposal_url_valid``/``locations_valid``,
        and ``0`` for ``min_daily_budget``.

        Note on the five ``*_max_amount`` values: they are the only response
        fields whose default depends on the extraction branch, so they are
        parametrized. ``_build_response`` dispatches on the *declared*
        campaign mode -- ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``), assigned inside ``execute()``
        by ``_set_creative_type`` from
        ``campaign_setup['attributes']['meta_campaign_mode']`` -- and each
        branch carries its own default: the DYNAMIC extraction resolves every
        value with ``asset_feed_spec.get('*_max_amount', 0)``, which yields
        ``0`` against an empty ``asset_feed_spec``, while the STANDARD
        extraction hardcodes the literal ``1`` (the exact-cardinality-1 rule
        for STANDARD ad sets). A direct, isolated call never runs
        ``_set_creative_type``, so the mode is fixed here by the
        parametrization and both branches are asserted.

        Worth keeping in view: this Caso_de_Uso never populates
        ``object_story_spec`` itself, so the STANDARD parametrization of this
        scenario (together with its two sibling default scenarios) is the
        only coverage of ``_build_response``'s STANDARD branch in this file.
        This mirrors the equivalent assertion in
        ``test_facebook_save_pre_check_images.py``'s
        ``test_response_uses_exact_defaults_for_every_omitted_field``.

        Requirements: 17.3
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        ad_creative = make_ad_creative(asset_feed_spec={})
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])

        result = use_case._build_response(creative)

        assert result["images"] == []
        assert result["bodies"] == []
        assert result["titles"] == []
        assert result["descriptions"] == []
        assert result["call_to_action_types"] == []

        assert result["images_valid_amount"] is False
        assert result["titles_valid_amount"] is False
        assert result["bodies_valid_amount"] is False
        assert result["descriptions_valid_amount"] is False
        assert result["call_to_action_types_valid_amount"] is False

        assert result["images_max_amount"] == expected_max_amount
        assert result["titles_max_amount"] == expected_max_amount
        assert result["bodies_max_amount"] == expected_max_amount
        assert result["descriptions_max_amount"] == expected_max_amount
        assert result["call_to_action_types_max_amount"] == expected_max_amount

        assert result["unique_titles"] is False
        assert result["unique_bodies"] is False
        assert result["unique_descriptions"] is False
        assert result["daily_budget_valid"] is False
        assert result["proposal_url_valid"] is False
        assert result["locations_valid"] is False

        assert result["min_daily_budget"] == 0
        assert result["locations"] == []

        # `proposal_url` falls back to `''.join([])` (an empty `link_urls`
        # default) rather than to a documented `*_valid_amount`-style
        # default; asserted here purely for completeness of the empty
        # `asset_feed_spec` scenario, not as its own separate requirement.
        assert result["proposal_url"] == ""

    def test_proposal_url_is_comma_join_of_link_urls_website_url_in_order(
        self, use_case_factory
    ):
        """With ``asset_feed_spec['link_urls']`` containing two entries,
        verify ``result['proposal_url']`` is exactly
        ``','.join(...)`` of their ``website_url`` values, in the same
        order they appear in ``link_urls``.

        Requirements: 17.4
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        asset_feed_spec = make_asset_feed_spec(
            link_urls=[
                {"website_url": "http://a.com"},
                {"website_url": "http://b.com"},
            ]
        )
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])

        result = use_case._build_response(creative)

        assert result["proposal_url"] == "http://a.com,http://b.com"

    def test_proposal_locations_defaults_to_empty_list_when_creative_omits_key(
        self, use_case_factory
    ):
        """With ``creative`` omitting the ``proposal_locations`` key
        entirely (the ``make_creative`` default, via the ``ABSENT``
        sentinel), verify ``result['proposal_locations'] == []``.

        Requirements: 17.5
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        asset_feed_spec = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        ad = make_ad(ad_creative=ad_creative)
        creative = make_creative(ads=[ad])

        assert "proposal_locations" not in creative

        result = use_case._build_response(creative)

        assert result["proposal_locations"] == []

    def test_full_execute_dynamic_scenario_response_reflects_mutated_asset_feed(
        self, use_case_factory
    ):
        """Exercise a full ``execute()`` round trip with
        ``meta_campaign_mode="DYNAMIC"``, a truthy ``asset_feed`` that
        starts out with stale ``titles``/``bodies``/``descriptions``
        placeholders, and non-empty, unique ``self.titles``/
        ``self.bodies``/``self.descriptions``. The real (unpatched)
        ``MetaAdsValidator`` methods mutate ``asset_feed`` inline during
        the DYNAMIC branch, before ``_build_response`` is ever called.

        Verify the returned Respuesta_de_Precheck reflects exactly those
        already-mutated values -- not the stale placeholders -- proving
        ``_build_response`` reads ``asset_feed_spec`` (via ``ad_creative``,
        via ``creative``) after the mutation, rather than a prior copy
        taken before ``execute()``'s validation block ran.

        This is a lighter, response-focused complement to
        ``TestDynamicBranchCallOrderAcrossFields.
        test_call_order_records_exact_9_call_sequence_and_execute_continues_to_response``
        (task 11.1), which already covers the same response-reflects-
        mutation fact as a secondary assertion alongside its primary
        9-call-order focus; this test exists so Requirement 17.6 has its
        own explicit, clearly-attributed assertion within
        ``TestBuildResponse``.

        Requirements: 17.6
        """
        titles = [make_text_entry("Unique title A"), make_text_entry("Unique title B")]
        bodies = [make_text_entry("Unique body A"), make_text_entry("Unique body B")]
        descriptions = [
            make_text_entry("Unique description A"),
            make_text_entry("Unique description B"),
        ]
        pre_check_texts_data = make_pre_check_texts_data(
            titles=titles, bodies=bodies, descriptions=descriptions
        )
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_texts_data=pre_check_texts_data)
        )

        asset_feed = make_asset_feed_spec(
            titles=["stale-titles"],
            bodies=["stale-bodies"],
            descriptions=["stale-descriptions"],
        )
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

            result = use_case.execute()

        assert result["titles"] is titles
        assert result["bodies"] is bodies
        assert result["descriptions"] is descriptions
        assert result["unique_titles"] is True
        assert result["unique_bodies"] is True
        assert result["unique_descriptions"] is True
        assert result["titles_valid_amount"] is True
        assert result["bodies_valid_amount"] is True
        assert result["descriptions_valid_amount"] is True

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_isolated_call_with_explicit_none_ad_creative_returns_default_response(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """Invokes ``_build_response`` directly and in isolation (not
        through ``execute()``) on an instance built via
        ``use_case_factory``, with ``creative['ads'][0]['adCreative']``
        set to ``None`` explicitly (via ``make_ad(ad_creative=None)``).

        Prior to the sibling specification
        ``meta-ads-standard-save-precheck-images`` (Requirement 5), this
        scenario propagated ``AttributeError`` because
        ``ad_creative = ads_to_publish.get('adCreative')`` (no default)
        kept ``ad_creative`` as ``None``, and the very next line called
        ``.get(...)`` on it directly. That specification's Requirement 5.1
        deliberately changed this: ``_build_response`` now normalizes
        ``ad_creative = ads_to_publish.get('adCreative') or {}`` before
        deriving ``object_story_spec``/``asset_feed_spec`` from it, so an
        explicit ``None`` ``adCreative`` normalizes to ``{}`` and no
        ``.get(...)`` is ever called on ``None``. That normalization is
        still what keeps the ``AttributeError`` away, and it is the primary
        intent of this scenario.

        Which extraction branch runs is a separate matter, decided by the
        *declared* campaign mode:
        ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``), assigned inside
        ``execute()`` by ``_set_creative_type``. A direct, isolated call
        never runs it, so the mode is fixed here by the parametrization and
        both branches are asserted. With ``ad_creative`` normalized to
        ``{}``, neither ``object_story_spec`` nor ``asset_feed_spec`` is
        available, so each branch falls back to its own defaults throughout
        and no exception is raised either way; the two agree on 25 of the 30
        response keys for this shape and differ only in the five
        ``*_max_amount`` values, hence their parametrized expectation. This
        mirrors the equivalent test in
        ``test_facebook_save_pre_check_images.py``
        (``test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none``).

        Requirements: 17.7
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        ad = make_ad(ad_creative=None)
        creative = make_creative(ads=[ad])

        result = use_case._build_response(creative)

        assert result["images"] == []
        assert result["bodies"] == []
        assert result["titles"] == []
        assert result["descriptions"] == []
        assert result["call_to_action_types"] == []
        assert result["images_valid_amount"] is False
        assert result["titles_valid_amount"] is False
        assert result["bodies_valid_amount"] is False
        assert result["descriptions_valid_amount"] is False
        assert result["call_to_action_types_valid_amount"] is False
        assert result["images_max_amount"] == expected_max_amount
        assert result["titles_max_amount"] == expected_max_amount
        assert result["bodies_max_amount"] == expected_max_amount
        assert result["descriptions_max_amount"] == expected_max_amount
        assert result["call_to_action_types_max_amount"] == expected_max_amount
        assert result["unique_titles"] is False
        assert result["unique_bodies"] is False
        assert result["unique_descriptions"] is False
        assert result["daily_budget_valid"] is False
        assert result["proposal_url_valid"] is False
        assert result["locations_valid"] is False
        assert result["min_daily_budget"] == 0
        assert result["locations"] == []
        assert result["proposal_url"] == ""

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_isolated_call_with_ad_creative_key_absent_returns_default_response(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """Invokes ``_build_response`` directly and in isolation (not
        through ``execute()``) on an instance built via
        ``use_case_factory``, with the ``adCreative`` key entirely absent
        from ``ads_to_publish`` (the ``make_ad()`` default, via the
        ``ABSENT`` sentinel, with no ``ad_creative`` argument passed).

        A completely absent ``adCreative`` key and an explicit
        ``adCreative=None`` both make ``ads_to_publish.get('adCreative')``
        evaluate to ``None``, which the ``ad_creative = ads_to_publish.get(
        'adCreative') or {}`` normalization (added by the sibling
        specification ``meta-ads-standard-save-precheck-images``,
        Requirement 5.1) treats identically: both normalize to ``{}``, so no
        ``.get(...)`` is ever called on ``None`` and no exception is raised.
        That observable equivalence -- a missing key behaves exactly like a
        key present with ``None`` -- is what this scenario asserts, returning
        the same all-defaults response as
        ``test_isolated_call_with_explicit_none_ad_creative_returns_default_response``
        above.

        The equivalence is now asserted under both extraction branches.
        Which one runs is decided by the *declared* campaign mode --
        ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``), assigned inside
        ``execute()`` by ``_set_creative_type`` -- and a direct, isolated
        call never runs it, so the mode is fixed here by the parametrization.
        With ``ad_creative`` normalized to ``{}`` neither
        ``object_story_spec`` nor ``asset_feed_spec`` is available, so each
        branch falls back to its own defaults throughout: the two agree on 25
        of the 30 response keys for this shape and differ only in the five
        ``*_max_amount`` values, hence their parametrized expectation. This
        mirrors the equivalent test in
        ``test_facebook_save_pre_check_images.py``
        (``test_direct_isolated_call_returns_default_response_when_ad_creative_key_absent``).

        Requirements: 17.8
        """
        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        ad = make_ad()
        assert "adCreative" not in ad
        creative = make_creative(ads=[ad])

        result = use_case._build_response(creative)

        assert result["images"] == []
        assert result["bodies"] == []
        assert result["titles"] == []
        assert result["descriptions"] == []
        assert result["call_to_action_types"] == []
        assert result["images_valid_amount"] is False
        assert result["titles_valid_amount"] is False
        assert result["bodies_valid_amount"] is False
        assert result["descriptions_valid_amount"] is False
        assert result["call_to_action_types_valid_amount"] is False
        assert result["images_max_amount"] == expected_max_amount
        assert result["titles_max_amount"] == expected_max_amount
        assert result["bodies_max_amount"] == expected_max_amount
        assert result["descriptions_max_amount"] == expected_max_amount
        assert result["call_to_action_types_max_amount"] == expected_max_amount
        assert result["unique_titles"] is False
        assert result["unique_bodies"] is False
        assert result["unique_descriptions"] is False
        assert result["daily_budget_valid"] is False
        assert result["proposal_url_valid"] is False
        assert result["locations_valid"] is False
        assert result["min_daily_budget"] == 0
        assert result["locations"] == []
        assert result["proposal_url"] == ""


LEADS_OFFSITE = ("OUTCOME_LEADS", "OFFSITE_CONVERSIONS")
LEADS_LEAD_GENERATION = ("OUTCOME_LEADS", "LEAD_GENERATION")
SALES_OFFSITE = ("OUTCOME_SALES", "OFFSITE_CONVERSIONS")


class TestLeadsOffsiteSaveTexts:
    """Coverage of ``FacebookSavePreCheckTextsUseCase`` for
    Combinación_Leads_Offsite (``OUTCOME_LEADS`` + ``OFFSITE_CONVERSIONS``).

    ``execute()`` runs end to end with the real ``MetaAdsValidator``; only
    ``redis_client`` and the two repositories are substituted. Each
    ``ad_channel_repository.update`` call is snapshotted with ``deepcopy``
    at call time so the persisted payload can be compared field by field
    between combinations.

    Requirements: 10.5, 10.6, 10.7, 10.8, 14.9
    """

    @staticmethod
    def _make_inputs():
        return make_pre_check_texts_data(
            titles=[make_text_entry("Título uno"), make_text_entry("Título dos")],
            bodies=[make_text_entry("Cuerpo del anuncio")],
            descriptions=[make_text_entry("Descripción breve")],
        )

    @staticmethod
    def _make_creative(mode, promoted_object_valid=True):
        if mode == "DYNAMIC":
            ad_creative = make_ad_creative(
                asset_feed_spec=make_asset_feed_spec(
                    ad_channel_id="channel-7",
                    titles=[make_text_entry("Viejo título")],
                    promoted_object={"page_id": "page-1"},
                    promoted_object_valid=promoted_object_valid,
                )
            )
        else:
            ad_creative = make_ad_creative(
                object_story_spec=make_object_story_spec(
                    ad_channel_id="channel-7",
                    link_data=make_link_data(link="https://example.com"),
                )
            )
        return make_creative(ads=[make_ad(ad_creative=ad_creative)])

    def _run(self, use_case_factory, mode, combination, promoted_object_valid=True):
        """Execute the use case and return
        ``(persisted_snapshots, response, save_spy)``."""
        attributes = {}
        if combination is not None:
            attributes = {
                "meta_campaign_objective": combination[0],
                "meta_optimization_goal": combination[1],
            }
        campaign_setup = make_campaign_setup(meta_campaign_mode=mode)
        campaign_setup["attributes"].update(attributes)
        creative = self._make_creative(mode, promoted_object_valid)
        ad_channel = make_ad_channel(channel_creative=creative)

        use_case, mock_ad_channel_repo, mock_publish_repo = use_case_factory(
            pre_check_texts_data=self._make_inputs()
        )
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = ad_channel
        mock_publish_repo.get_by_campaign_id_and_channel_id.return_value = campaign_setup

        snapshots = []
        mock_ad_channel_repo.update.side_effect = lambda ad_channel_id, data: (
            snapshots.append((ad_channel_id, copy.deepcopy(data)))
        )

        with patch_redis_client() as mock_redis_client, patch.object(
            use_case,
            "_save_creative_to_publish",
            wraps=use_case._save_creative_to_publish,
        ) as save_spy:
            mock_redis_client.get.return_value = b"some-access-token"
            response = use_case.execute()

        save_spy.assert_called_once()
        assert save_spy.call_args.args[0] is creative
        return snapshots, response, creative

    def test_dynamic_happy_path_leads_offsite(self, use_case_factory):
        """Req 10.6, 14.9: DYNAMIC completes without exception, persists
        once through ``AdChannelRepository.update`` with the annotated
        ``asset_feed_spec``."""
        snapshots, response, creative = self._run(
            use_case_factory, "DYNAMIC", LEADS_OFFSITE
        )

        assert len(snapshots) == 1
        ad_channel_id, data = snapshots[0]
        assert ad_channel_id == "channel-7"
        asset_feed = data["channel_creative"]["ads"][0]["adCreative"]["asset_feed_spec"]
        assert [t["text"] for t in asset_feed["titles"]] == ["Título uno", "Título dos"]
        assert [b["text"] for b in asset_feed["bodies"]] == ["Cuerpo del anuncio"]
        assert [d["text"] for d in asset_feed["descriptions"]] == ["Descripción breve"]
        assert asset_feed["unique_titles"] is True
        assert asset_feed["titles_valid_amount"] is True
        assert asset_feed["bodies_valid_amount"] is True
        assert asset_feed["descriptions_valid_amount"] is True
        assert all(t["valid_length"] is True for t in asset_feed["titles"])
        assert [t["text"] for t in response["titles"]] == ["Título uno", "Título dos"]

    def test_standard_happy_path_leads_offsite(self, use_case_factory):
        """Req 10.6, 14.9: STANDARD completes without exception, persists
        once with the single-candidate texts written into ``link_data``."""
        snapshots, response, _ = self._run(use_case_factory, "STANDARD", LEADS_OFFSITE)

        assert len(snapshots) == 1
        ad_channel_id, data = snapshots[0]
        assert ad_channel_id == "channel-7"
        link_data = data["channel_creative"]["ads"][0]["adCreative"][
            "object_story_spec"
        ]["link_data"]
        # Two title candidates -> invalid, name untouched.
        assert link_data["title_valid"] is False
        assert link_data["name"] is None
        assert link_data["body_valid"] is True
        assert link_data["message"] == "Cuerpo del anuncio"
        assert link_data["description_valid"] is True
        assert link_data["description"] == "Descripción breve"
        assert link_data["link"] == "https://example.com"
        assert response["bodies"] == [
            {"text": "Cuerpo del anuncio", "valid_length": True}
        ]

    @pytest.mark.parametrize("mode", ["DYNAMIC", "STANDARD"])
    def test_identical_to_lead_generation_field_by_field(self, use_case_factory, mode):
        """Req 10.5: persistence and response for Combinación_Leads_Offsite
        match ``OUTCOME_LEADS`` + ``LEAD_GENERATION`` field by field."""
        offsite_snapshots, offsite_response, _ = self._run(
            use_case_factory, mode, LEADS_OFFSITE
        )
        leadgen_snapshots, leadgen_response, _ = self._run(
            use_case_factory, mode, LEADS_LEAD_GENERATION
        )

        assert len(offsite_snapshots) == len(leadgen_snapshots) == 1
        offsite_id, offsite_data = offsite_snapshots[0]
        leadgen_id, leadgen_data = leadgen_snapshots[0]
        assert offsite_id == leadgen_id

        offsite_ad = offsite_data["channel_creative"]["ads"][0]["adCreative"]
        leadgen_ad = leadgen_data["channel_creative"]["ads"][0]["adCreative"]
        spec_key = "asset_feed_spec" if mode == "DYNAMIC" else "object_story_spec"
        offsite_spec = offsite_ad[spec_key]
        leadgen_spec = leadgen_ad[spec_key]
        assert offsite_spec.keys() == leadgen_spec.keys()
        for key in offsite_spec:
            assert offsite_spec[key] == leadgen_spec[key], key

        assert offsite_data == leadgen_data
        assert offsite_response.keys() == leadgen_response.keys()
        for key in offsite_response:
            assert offsite_response[key] == leadgen_response[key], key

    @pytest.mark.parametrize("promoted_object_valid", [True, False])
    def test_dynamic_preserves_persisted_promoted_object_valid(
        self, use_case_factory, promoted_object_valid
    ):
        """Req 10.7: the ``promoted_object_valid`` written by Caso_PreCheck
        is persisted unchanged, along with ``promoted_object``."""
        snapshots, _, _ = self._run(
            use_case_factory, "DYNAMIC", LEADS_OFFSITE, promoted_object_valid
        )

        asset_feed = snapshots[0][1]["channel_creative"]["ads"][0]["adCreative"][
            "asset_feed_spec"
        ]
        assert asset_feed["promoted_object_valid"] is promoted_object_valid
        assert asset_feed["promoted_object"] == {"page_id": "page-1"}

    @pytest.mark.parametrize("mode", ["DYNAMIC", "STANDARD"])
    @pytest.mark.parametrize(
        "combination",
        [
            pytest.param(LEADS_LEAD_GENERATION, id="leads-lead-generation"),
            pytest.param(SALES_OFFSITE, id="sales-offsite-conversions"),
        ],
    )
    def test_other_combinations_unchanged(self, use_case_factory, mode, combination):
        """Req 10.8: ``LEAD_GENERATION`` and ``SALES/OFFSITE_CONVERSIONS``
        produce the same persistence and response as a Campaign_Setup with
        no objective/goal at all (the use case is combination-agnostic)."""
        snapshots, response, _ = self._run(use_case_factory, mode, combination)
        baseline_snapshots, baseline_response, _ = self._run(
            use_case_factory, mode, None
        )

        assert len(snapshots) == 1
        assert snapshots == baseline_snapshots
        assert response == baseline_response
