"""Characterization test suite for ``FacebookSavePreCheckImagesUseCase``.

Target under test: ``app.v2.use_cases.meta_ads.FacebookSavePreCheckImagesUseCase``
and the inherited subset of ``FacebookSavePreCheckBaseUseCase`` that it
invokes: the constructor, ``_get_ad_channel``, ``_get_campaign_setup``,
``_set_channel_id`` and ``_build_response``.

This module fixes the current observable behaviour, including already
existing quirks (the always-``{}`` ``complete_campaign_data`` passed to the
grandparent constructor, the mutable default ``pre_check_data: PreCheckDataDict
= {}`` in the constructor signature, the asymmetric ``.get(..., {})``/``.get(...)``
usages between ``execute()``, ``_save_creative_to_publish`` and
``_build_response``, and the transparent ``try/except Exception as e: raise e``
pass-through). No production code is modified or "fixed" by this suite.

Requirements: 15.2, 15.3
"""

from contextlib import contextmanager
from io import BytesIO
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
from hypothesis import given, settings, strategies as st
from PIL import Image

from app.exceptions.base import DataNotFoundException, NotAccessException
from app.v2.use_cases.facebook_validator_service import CreativeType, MetaAdsValidator
from app.v2.use_cases.meta_ads import (
    FacebookSavePreCheckBaseUseCase,
    FacebookSavePreCheckImagesUseCase,
)


def _build_valid_test_image_bytes():
    """Build the raw PNG bytes of a minimal, real in-memory image that
    satisfies ``MetaAdsValidator.validate_images_precheck``'s real size/
    aspect-ratio checks (a 400x400 square is within
    ``IMG_MIN_SIZE``/``IMG_MAX_SIZE`` and within the allowed aspect-ratio
    range), so a simulated successful HTTP fetch can be parsed by
    ``PIL.Image.open`` without raising, letting ``validate_images_precheck``
    reach its ``valid = True`` default rather than falling into its
    ``except Exception`` (invalid image format) branch.

    Requirements: 14.6
    """
    buffer = BytesIO()
    Image.new("RGB", (400, 400), color="red").save(buffer, format="PNG")
    return buffer.getvalue()


_VALID_TEST_IMAGE_BYTES = _build_valid_test_image_bytes()


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it from the resulting dict" from "this key
    was provided by the caller with the value ``None``".

    Requirements: 15.2, 15.3
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


def make_pre_check_images_data(**overrides):
    """Build a fresh ``pre_check_images_data`` (``PreCheckDataDict``-like) dict.

    Every invocation returns a brand new dict, with brand new list objects
    for every collection field; no mutable default arguments are used, so
    callers can freely mutate the returned value (or its nested lists)
    without affecting other tests.

    Requirements: 15.2, 15.3
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


def make_image_entry(url="https://example.test/img.jpg", **overrides):
    """Build a fresh image entry dict of the form ``{"url": ...}``.

    Pass ``url=None`` explicitly, or omit ``url`` via ``overrides`` handling
    on the caller side, to characterize entries that must not trigger a
    real HTTP request in ``validate_images_precheck``.

    Requirements: 15.2, 15.3
    """
    data = {"url": url}
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

    Requirements: 15.2, 15.3
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
    to characterize the unknown-mode scenarios of Requirement 10.
    ``**overrides`` are merged into the top-level dict.

    Requirements: 15.2, 15.3
    """
    data = {"attributes": {"meta_campaign_mode": meta_campaign_mode}}
    data.update(overrides)
    return data


def make_asset_feed_spec(**overrides):
    """Build a fresh ``asset_feed_spec`` dict with empty collections.

    Requirements: 15.2, 15.3
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

    Empty by default; the STANDARD branch is a no-op, so this builder only
    needs to produce a fresh, freely-mutable dict for asserting it stays
    untouched.

    Requirements: 15.2, 15.3
    """
    data = {}
    data.update(overrides)
    return data


def make_link_data(**overrides):
    """Build a fresh ``link_data`` dict.

    Adapted from the identically-named builder in
    ``test_facebook_generate_pre_check_creative.py``: ``name``, ``message``,
    ``description``, ``image_url``, ``link`` and ``call_to_action`` all
    default to ``None``, composable directly with
    ``make_object_story_spec(link_data=make_link_data(...))``.

    Requirements: 7.1
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
    from "key present with value ``None``" (Requirements 8.3 vs 8.1, and
    11.2 vs 11.4).

    Requirements: 15.2, 15.3
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

    Requirements: 15.2, 15.3
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
    characterize the empty-``ads`` scenario of Requirement 11.1.
    ``proposal_locations`` defaults to the ``ABSENT`` sentinel: when left
    untouched, the key is omitted entirely, matching the
    ``creative.get('proposal_locations', [])`` default in ``_build_response``.

    Requirements: 15.2, 15.3
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
    """Fixture that builds a factory for ``FacebookSavePreCheckImagesUseCase``
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

    If ``pre_check_images_data`` is omitted, a fresh
    ``make_pre_check_images_data()`` is used so the ``AttributeError``
    characterized in Requirement 2.9, and the mutable-default scenario of
    Requirement 2.10, are not accidentally triggered here; the dedicated
    tests for those criteria construct the use case directly, without this
    fixture.

    Requirements: 1.2
    """

    def _factory(user_id="user-1", pre_check_images_data=None):
        if pre_check_images_data is None:
            pre_check_images_data = make_pre_check_images_data()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookSavePreCheckImagesUseCase(
                user_id, pre_check_images_data
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
def patch_image_fetch(side_effect=None):
    """Context manager that patches
    ``app.v2.use_cases.facebook_validator_service.requests.get`` (not
    ``MetaAdsValidator`` itself), yielding the resulting ``MagicMock``.

    By default (``side_effect=None``), the patched ``requests.get`` returns
    a ``MagicMock`` whose ``.raise_for_status()`` does not raise and whose
    ``.headers``/``.content`` simulate a minimal, valid-enough image
    response, so scenarios that are not focused on
    ``validate_images_precheck``'s own success path do not fail by
    accident.

    Pass ``side_effect=requests.exceptions.RequestException(...)`` (or a
    subclass, e.g. ``requests.exceptions.ConnectionError``) to simulate a
    network failure for Requirement 7.9, exercising
    ``validate_images_precheck``'s real ``except requests.exceptions.RequestException``
    branch without opening a real socket.

    Requirements: 1.4, 1.5
    """
    with patch(
        "app.v2.use_cases.facebook_validator_service.requests.get"
    ) as mock_requests_get:
        if side_effect is not None:
            mock_requests_get.side_effect = side_effect
        else:
            fake_response = MagicMock()
            fake_response.raise_for_status.return_value = None
            fake_response.headers = {}
            fake_response.content = b""
            mock_requests_get.return_value = fake_response
        yield mock_requests_get


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Local, module-scoped guard (not a global ``conftest.py`` fixture),
    ``autouse=True`` at function scope, that replaces
    ``requests.sessions.Session.request`` with a function that fails
    immediately.

    This is additional defense for any scenario where ``patch_image_fetch``
    is not active but an image entry unexpectedly carries a truthy ``url``.
    It coexists with ``patch_image_fetch``: when the latter is active,
    ``requests.get`` is already substituted before execution would ever
    reach ``Session.request``, so this guard does not interfere with
    scenarios that intentionally exercise ``validate_images_precheck``.

    Requirements: 1.4, 1.5
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
    ``try/except`` pass-through (Requirement 12), and the malformed
    ``creative``/``ads`` structures (Requirement 11).

    Requirements: 15.4
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

    Requirements: 15.4
    """
    try:
        mock_method.assert_called_once_with(*args)
    except AssertionError as exc:
        raise AssertionError(
            f"expected {mock_method} to be called once with {args!r}: {exc}"
        ) from exc


def assert_no_validator_calls(mock_is_valid_images_amount, mock_validate_images_precheck):
    """Assert that neither ``MetaAdsValidator.is_valid_images_amount`` nor
    ``MetaAdsValidator.validate_images_precheck`` were invoked.

    Used in Requirements 8, 9.4 and 10.

    Requirements: 15.4
    """
    mock_is_valid_images_amount.assert_not_called()
    mock_validate_images_precheck.assert_not_called()


def test_builders_placeholder_smoke():
    """Smoke test confirming the builders above produce fresh, independent
    structures with no mutable state shared across invocations.

    Requirements: 15.2, 15.3
    """
    first_data = make_pre_check_images_data()
    second_data = make_pre_check_images_data()
    assert first_data is not second_data
    assert first_data["images"] is not second_data["images"]

    first_data["images"].append(make_image_entry())
    assert second_data["images"] == []

    first_creative = make_creative()
    second_creative = make_creative()
    assert first_creative["ads"] is not second_creative["ads"]
    assert first_creative["ads"][0] is not second_creative["ads"][0]


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
    """Tests for the ``FacebookSavePreCheckImagesUseCase``/
    ``FacebookSavePreCheckBaseUseCase`` constructor chain and the state it
    establishes.

    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8
    """

    def test_own_attributes_assigned_exactly_from_complete_pre_check_data(
        self, use_case_factory
    ):
        """With complete ``pre_check_images_data``, ``adset_id``, ``ad_id``,
        ``adchannel_id``, ``images``, ``bodies``, ``titles``,
        ``descriptions``, ``call_to_action_types`` and ``locations`` are
        assigned exactly from the provided data (by identity for the
        list-valued fields).

        Requirements: 2.1
        """
        images = [make_image_entry()]
        bodies = ["body-1"]
        titles = ["title-1"]
        descriptions = ["description-1"]
        call_to_action_types = ["SHOP_NOW"]
        locations = ["location-1"]
        pre_check_images_data = make_pre_check_images_data(
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

        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)

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
        ``pre_check_images_data``, they default to ``0``/``''``.

        Requirements: 2.2, 2.3
        """
        pre_check_images_data = make_pre_check_images_data()
        del pre_check_images_data["daily_budget"]
        del pre_check_images_data["proposal_url"]

        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)

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
        ``pre_check_images_data``, the corresponding attribute is
        initialized to a brand new empty list: two separate instances built
        from an equivalent, independent dict each get their own list
        object, not a shared one.

        Requirements: 2.4
        """
        first_data = make_pre_check_images_data()
        del first_data[field_name]
        second_data = make_pre_check_images_data()
        del second_data[field_name]

        first_use_case, _, _ = use_case_factory(pre_check_images_data=first_data)
        second_use_case, _, _ = use_case_factory(pre_check_images_data=second_data)

        first_value = getattr(first_use_case, field_name)
        second_value = getattr(second_use_case, field_name)
        assert first_value == []
        assert second_value == []
        assert first_value is not second_value

    def test_campaign_id_and_user_id_propagated_to_great_grandparent(
        self, use_case_factory
    ):
        """``campaign_id`` is taken from
        ``pre_check_images_data.get('campaign_id')`` and ``user_id`` is
        taken from the constructor's ``user_id`` argument; both are
        propagated correctly through ``FacebookSavePreCheckBaseUseCase``
        down to the ``self.campaign_id``/``self.user_id`` assignments made
        by the Caso_de_Uso_Bisabuelo (``FacebookTestCreativeUploadUseCase``).

        Requirements: 2.5
        """
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-99")

        use_case, _, _ = use_case_factory(
            user_id="user-99", pre_check_images_data=pre_check_images_data
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
        ``pre_check_images_data`` content -- including when
        ``pre_check_images_data`` happens to carry keys with the same
        names, which are simply ignored by the parent constructor because
        it never reads them from ``pre_check_data``.

        Requirements: 2.6, 2.7
        """
        pre_check_images_data = make_pre_check_images_data(
            ad_account_id="should-be-ignored",
            page_id="should-be-ignored",
            objective="should-be-ignored",
        )

        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)

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
        ``FacebookSavePreCheckImagesUseCase`` (inherited from the
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
            FacebookSavePreCheckImagesUseCase("user-1", make_pre_check_images_data())

            mock_ad_channel_repository_cls.assert_called_once_with()
            mock_campaign_publish_repository_cls.assert_called_once_with()

    def test_explicit_none_pre_check_images_data_propagates_attribute_error(self):
        """Constructing ``FacebookSavePreCheckImagesUseCase`` directly (not
        via ``use_case_factory``, so the repositories are patched inline
        here) with ``pre_check_images_data=None`` passed *explicitly*
        propagates an ``AttributeError`` when the constructor chain
        eventually invokes ``None.get('campaign_id')``.

        This characterizes that the mutable default
        ``pre_check_data: PreCheckDataDict = {}`` in
        ``FacebookSavePreCheckBaseUseCase.__init__`` only protects the case
        where the caller *omits* the argument entirely; it offers no
        protection when the caller passes ``None`` explicitly, since a
        default value is never substituted for an explicitly-passed
        argument regardless of its value.

        Requirements: 2.9
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            with pytest.raises(AttributeError) as exc_info:
                FacebookSavePreCheckImagesUseCase("user-1", None)

        assert str(exc_info.value) == "'NoneType' object has no attribute 'get'"

    def test_mutable_default_pre_check_data_is_not_observably_shared_between_instances(
        self,
    ):
        """Constructing two ``FacebookSavePreCheckBaseUseCase`` instances
        back-to-back, without providing ``pre_check_data`` in either
        invocation (so both rely on the mutable default
        ``pre_check_data: PreCheckDataDict = {}`` in the signature),
        mutating ``images`` on the first instance does not make the second
        instance reflect that mutation.

        Documented result (verified empirically, not assumed): even though
        the default argument object ``{}`` bound to the ``pre_check_data``
        parameter *is* the very same dict across both calls (the classic
        mutable-default-argument hazard), ``self.images`` is assigned via
        ``pre_check_data.get('images', [])`` -- and because the shared
        default dict never actually contains an ``'images'`` key, ``.get``
        falls back to its *own* second positional argument ``[]``, which
        Python evaluates as a brand new list literal at each call site
        execution (unlike a default *parameter* value, a default argument
        to ``.get()`` is a fresh expression evaluated on every call, not a
        function-definition-time singleton). So the two instances'
        ``self.images`` lists are independent objects here: mutating the
        first instance's ``images`` is NOT observed on the second instance.
        This is current behaviour, characterized as-is; no correction is
        proposed for the underlying mutable-default-argument hazard, which
        would still be observable for a hypothetical field read directly
        off ``pre_check_data`` without going through ``.get(key, [])``.

        Requirements: 2.10
        """
        with patch("app.v2.use_cases.meta_ads.AdChannelRepository"), patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ):
            first_use_case = FacebookSavePreCheckBaseUseCase("user-1")
            second_use_case = FacebookSavePreCheckBaseUseCase("user-2")

            first_use_case.images.append("mutated-by-first-instance")

            # Observed result: the second instance's `images` list does NOT
            # reflect the first instance's mutation. `self.images` is
            # produced by `pre_check_data.get('images', [])`; the shared
            # mutable-default `{}` never gains an `'images'` key, so `.get`
            # always falls back to a brand new `[]` literal evaluated at
            # each call, rather than returning a value stored inside the
            # shared default dict itself.
            assert second_use_case.images == []
            assert first_use_case.images is not second_use_case.images


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
        pre_check_images_data = make_pre_check_images_data(
            campaign_id="campaign-7",
            adset_id="adset-7",
            ad_id="ad-7",
            adchannel_id="adchannel-7",
        )
        use_case, mock_ad_channel_repo_instance, _ = use_case_factory(
            pre_check_images_data=pre_check_images_data
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
        ``text`` passed in; the actual message lives on ``exc.text``. This
        was verified empirically before writing this assertion.

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
        nor ``ad_channel_repository.update``.

        ``redis_client`` is patched with a truthy ``.get.return_value`` so
        ``_get_decoded_access_token`` succeeds first and execution actually
        reaches ``_get_ad_channel`` before failing.

        Requirements: 3.4
        """
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory()
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"
            with patch.object(use_case, "_set_channel_id") as mock_set_channel_id:
                with pytest.raises(DataNotFoundException) as exc_info:
                    use_case.execute()

        assert exc_info.value.text == "Creative not found!"
        mock_set_channel_id.assert_not_called()
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.assert_not_called()
        mock_ad_channel_repo_instance.update.assert_not_called()
        # `_set_channel_id` never ran, so `channel_id` stays at its
        # pre-call constructor state (`None`, from Datos_de_Campaña_Vacíos).
        assert use_case.channel_id is None


class TestGetCampaignSetup:
    """Tests for ``_get_campaign_setup``: the exact repository call, identity
    of the returned Campaign_Setup, the ``DataNotFoundException`` raised
    with an interpolated message on a falsy result, and the short-circuit
    observed within ``execute()`` when the Campaign_Setup is missing.

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
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-7")
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            pre_check_images_data=pre_check_images_data
        )
        use_case.channel_id = "channel-7"
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_campaign_setup()

        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-7",
            "channel-7",
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
        use_case.channel_id = 1
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
    def test_raises_data_not_found_exception_with_exact_interpolated_message_when_falsy(
        self, use_case_factory, falsy_campaign_setup
    ):
        """When the repository returns a falsy value (``None`` or ``{}``),
        ``_get_campaign_setup`` propagates ``DataNotFoundException`` whose
        ``.text`` is exactly
        ``f"Campaign Setup not found for campaign_id: {self.campaign_id} and channel_id: {self.channel_id}"``.

        Note: ``str(exc_info.value)`` is deliberately NOT used here, for
        the same reason documented in ``TestGetAdChannel``:
        ``SinergiaException.__init__`` calls ``super().__init__(args)``
        (passing the ``args`` tuple itself, not the unpacked ``text``), so
        ``str(exc)`` is always the literal ``"()"`` regardless of the
        ``text`` passed in; the actual message lives on ``exc.text``.

        Requirements: 4.3
        """
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-13")
        use_case, _, mock_campaign_publish_repo_instance = use_case_factory(
            pre_check_images_data=pre_check_images_data
        )
        use_case.channel_id = "channel-13"
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            falsy_campaign_setup
        )

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_campaign_setup()

        assert exc_info.value.text == (
            "Campaign Setup not found for campaign_id: campaign-13 "
            "and channel_id: channel-13"
        )

    def test_execute_short_circuits_on_missing_campaign_setup_after_ad_channel_and_set_channel_id_ran(
        self, use_case_factory
    ):
        """Within ``execute()``, a missing Campaign_Setup (repository
        returns a falsy value) propagates ``DataNotFoundException`` without
        invoking either of the ``MetaAdsValidator`` validators nor
        ``ad_channel_repository.update``, but only after ``_get_ad_channel``
        and ``_set_channel_id`` already ran: ``ad_channel_repository``'s
        lookup is truthy so ``_get_ad_channel`` succeeds normally, and
        ``_set_channel_id`` runs on that result, setting ``channel_id``
        from the Ad_Channel's ``attributes.channel_ref.data.id`` before
        ``_get_campaign_setup`` is ever called.

        ``redis_client`` is patched with a truthy ``.get.return_value`` so
        ``_get_decoded_access_token`` succeeds first and execution actually
        reaches ``_get_ad_channel``/``_set_channel_id``/``_get_campaign_setup``
        before failing.

        Requirements: 4.4
        """
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-21")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
        )
        ad_channel = make_ad_channel(channel_ref_id="channel-21")
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = None

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"
        ) as mock_is_valid_images_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == (
            "Campaign Setup not found for campaign_id: campaign-21 "
            "and channel_id: channel-21"
        )
        # `_get_ad_channel` and `_set_channel_id` already ran: `channel_id`
        # reflects the Ad_Channel's `attributes.channel_ref.data.id`, and
        # that is the exact value used for the (now-failed) lookup.
        assert use_case.channel_id == "channel-21"
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            "campaign-21",
            "channel-21",
        )
        assert_no_validator_calls(mock_is_valid_images_amount, mock_validate_images_precheck)
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
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-55")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
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
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-56")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
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


class TestExecuteOrchestration:
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
        from ``ad_channel`` is inline code in ``execute()``, not a separate
        method call, so it cannot appear in ``manager.mock_calls`` itself;
        it is exercised for real by having the patched ``_get_ad_channel``
        return a real-ish ``make_ad_channel(channel_creative=make_creative())``
        value, and its correctness is confirmed by asserting (in the test
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
        so no validation runs without needing to patch ``MetaAdsValidator``
        (or the ``_validate_images_*`` methods) as well.

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
        ``_get_ad_channel``, ``_get_campaign_setup``, any image validation
        (``MetaAdsValidator.is_valid_images_amount``/
        ``validate_images_precheck``), nor ``_save_creative_to_publish``.

        ``_get_ad_channel``/``_get_campaign_setup``/``_save_creative_to_publish``
        are patched on the instance, and both ``MetaAdsValidator`` methods
        are patched at the class level, purely so this test can assert none
        of them were ever called; none of them would run for real before
        the token check fails regardless.

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
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"
        ) as mock_is_valid_images_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
            mock_redis_client.get.return_value = None

            with pytest.raises(NotAccessException) as exc_info:
                use_case.execute()

        assert exc_info.value.text == (
            "No access token found in Redis. Please re-authenticate."
        )
        mock_get_ad_channel.assert_not_called()
        mock_get_campaign_setup.assert_not_called()
        assert_no_validator_calls(mock_is_valid_images_amount, mock_validate_images_precheck)
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
        ``MetaAdsValidator`` is additionally patched purely to confirm
        neither validator was reached, since the validation block itself
        is never entered before ``_get_campaign_setup`` fails.

        Requirements: 6.4
        """
        pre_check_images_data = make_pre_check_images_data(campaign_id="campaign-61")
        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
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
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"
        ) as mock_is_valid_images_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
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
        assert_no_validator_calls(mock_is_valid_images_amount, mock_validate_images_precheck)
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

        The Campaign_Setup uses ``meta_campaign_mode="STANDARD"`` with a
        falsy (absent) ``story_spec``, so the conditional validation block
        is a no-op and ``MetaAdsValidator`` does not need to be patched for
        this scenario to reach ``_save_creative_to_publish``/
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


class TestValidateImagesDynamic:
    """Tests for the DYNAMIC branch's image validation: the invocation of
    ``_validate_images_dynamic`` from ``execute()``, the exact call to
    ``MetaAdsValidator.validate_images_precheck``, the overwrite of
    ``asset_feed['images']``, and the exact call to/assignment from
    ``MetaAdsValidator.is_valid_images_amount``.

    Requirements: 7.1, 7.2, 7.3, 7.4
    """

    def test_execute_invokes_validate_images_dynamic_with_asset_feed_by_identity_when_dynamic_and_truthy(
        self, use_case_factory
    ):
        """When ``campaign_setup['attributes']['meta_campaign_mode']`` is
        ``"DYNAMIC"`` and ``asset_feed`` (``ad_creative['asset_feed_spec']``)
        is a truthy dict, ``execute()`` invokes ``_validate_images_dynamic``
        with that exact same ``asset_feed`` object, by identity.

        ``_validate_images_dynamic`` itself is patched on the instance so
        this test stays focused purely on the invocation and its argument;
        ``_save_creative_to_publish``/``_build_response`` are also patched
        so ``execute()`` can complete without needing a fully-shaped
        ``creative`` beyond what the extraction/validation block reads.

        Requirements: 7.1
        """
        asset_feed = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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
            use_case, "_validate_images_dynamic"
        ) as mock_validate_images_dynamic, patch.object(
            use_case, "_save_creative_to_publish"
        ), patch.object(use_case, "_build_response"):
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_validate_images_dynamic.assert_called_once_with(asset_feed)
        assert mock_validate_images_dynamic.call_args.args[0] is asset_feed

    def test_execute_does_not_invoke_validate_images_standard_when_dynamic_even_with_truthy_story_spec(
        self, use_case_factory
    ):
        """When ``campaign_setup['attributes']['meta_campaign_mode']`` is
        ``"DYNAMIC"``, ``_validate_images_standard`` is never invoked --
        even when ``story_spec`` (``ad_creative['object_story_spec']``) is
        also truthy alongside a truthy ``asset_feed`` -- confirming that
        the DYNAMIC/STANDARD dispatch in ``execute()`` is driven purely by
        ``meta_campaign_mode`` and not merely by the absence of
        ``story_spec``.

        ``_validate_images_dynamic`` is patched on the instance so
        ``execute()`` doesn't need a fully-shaped ``asset_feed``;
        ``_validate_images_standard`` is likewise patched via
        ``patch.object`` purely to assert it is never called;
        ``_save_creative_to_publish``/``_build_response`` are also patched
        so ``execute()`` can complete without needing to reach
        ``_build_response``'s real dispatch logic.

        Requirements: 7.9
        """
        asset_feed = make_asset_feed_spec()
        story_spec = make_object_story_spec(headline="Some headline")
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed, object_story_spec=story_spec
        )
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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
            use_case, "_validate_images_dynamic"
        ), patch.object(
            use_case, "_validate_images_standard"
        ) as mock_validate_images_standard, patch.object(
            use_case, "_save_creative_to_publish"
        ), patch.object(use_case, "_build_response"):
            mock_redis_client.get.return_value = b"some-access-token"

            use_case.execute()

        mock_validate_images_standard.assert_not_called()

    def test_validate_images_dynamic_calls_validate_images_precheck_with_self_images_by_identity_without_real_http(
        self, use_case_factory
    ):
        """``_validate_images_dynamic`` invokes
        ``MetaAdsValidator.validate_images_precheck`` exactly once with
        ``self.images`` as its only argument, compared by list identity
        (not content equality).

        ``MetaAdsValidator.validate_images_precheck`` is patched directly as
        a mock for this narrower invocation check, which is what makes the
        identity comparison against ``self.images`` possible without
        depending on ``validate_images_precheck``'s real body; this also
        guarantees no real HTTP request can happen here, independently of
        the ``deny_network`` guard that is already active for the whole
        suite. ``_validate_images_dynamic`` is invoked directly on the use
        case (not through ``execute()``), matching the direct-method-
        invocation convention already used for other methods in this
        suite (e.g. ``_get_ad_channel`` in ``TestGetAdChannel``).

        Requirements: 7.2
        """
        images = [make_image_entry()]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        asset_feed = make_asset_feed_spec()

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
            use_case._validate_images_dynamic(asset_feed)

        mock_validate_images_precheck.assert_called_once_with(images)
        assert mock_validate_images_precheck.call_args.args[0] is images

    def test_validate_images_dynamic_overwrites_asset_feed_images_with_self_images_by_identity_even_when_previously_different(
        self, use_case_factory
    ):
        """After ``MetaAdsValidator.validate_images_precheck`` returns (its
        real behaviour never raises), ``asset_feed['images']`` is
        overwritten exactly with ``self.images``, by identity, even when
        ``asset_feed['images']`` previously held a different value (here, a
        list with unrelated entries), characterizing that the original
        content of ``asset_feed['images']`` is discarded rather than merged
        with ``self.images``.

        Both ``MetaAdsValidator`` methods are patched as mocks so this test
        stays focused purely on the overwrite itself, without depending on
        the validators' real bodies or requiring any network isolation
        beyond the patches already in place.

        Requirements: 7.3
        """
        images = [make_image_entry(url=None)]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        previous_images = [{"url": "https://old.example.test/previous.jpg"}]
        asset_feed = make_asset_feed_spec(images=previous_images)

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ), patch("app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"):
            use_case._validate_images_dynamic(asset_feed)

        assert asset_feed["images"] is images
        assert asset_feed["images"] is not previous_images

    def test_validate_images_dynamic_calls_is_valid_images_amount_with_self_images_and_assigns_exact_returned_boolean(
        self, use_case_factory
    ):
        """``_validate_images_dynamic`` invokes
        ``MetaAdsValidator.is_valid_images_amount`` exactly once with
        ``self.images`` as its only argument (compared by identity), and
        ``asset_feed['images_valid_amount']`` is assigned exactly the
        boolean value that call returned.

        ``MetaAdsValidator.is_valid_images_amount`` is patched with an
        explicit boolean return value so the assignment can be checked
        precisely; ``MetaAdsValidator.validate_images_precheck`` is also
        patched as a mock to keep this test isolated from its real body and
        to guarantee no real HTTP request can happen here.

        Requirements: 7.4
        """
        images = [make_image_entry()]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        asset_feed = make_asset_feed_spec()

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ), patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"
        ) as mock_is_valid_images_amount:
            mock_is_valid_images_amount.return_value = True

            use_case._validate_images_dynamic(asset_feed)

        mock_is_valid_images_amount.assert_called_once_with(images)
        assert mock_is_valid_images_amount.call_args.args[0] is images
        assert asset_feed["images_valid_amount"] is True

    @pytest.mark.parametrize(
        "images_count, expected_images_valid_amount",
        [
            (0, False),
            (10, True),
            (11, False),
        ],
    )
    def test_validate_images_dynamic_real_is_valid_images_amount_boundary_matrix(
        self, use_case_factory, images_count, expected_images_valid_amount
    ):
        """Exercise the real, unpatched
        ``MetaAdsValidator.is_valid_images_amount`` boundary at 0/10/11
        entries: ``self.images`` with exactly 0, 10 and 11 minimal entries
        yields ``asset_feed['images_valid_amount']`` equal to ``False``,
        ``True`` and ``False`` respectively.

        Per the spec's explicit rule,
        ``MetaAdsValidator.is_valid_images_amount`` is never patched here;
        only its real implementation runs. ``MetaAdsValidator.validate_images_precheck``
        is also left unpatched (it is exercised for real too), but each
        minimal image entry (``{}``) has no ``url`` key, so
        ``image.get('url')`` is falsy and its ``for`` loop's
        ``if not img_url: continue`` skips straight past the HTTP-fetching
        branch for every entry, without issuing any real HTTP request; the
        module-wide ``deny_network`` guard remains in place as additional
        defense.

        Requirements: 7.5, 7.6, 7.7
        """
        images = [{} for _ in range(images_count)]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        asset_feed = make_asset_feed_spec()

        use_case._validate_images_dynamic(asset_feed)

        assert asset_feed["images_valid_amount"] is expected_images_valid_amount

    # Feature: facebook-save-pre-check-images-tests, Property 1: is_valid_images_amount
    # es verdadero si y solo si la cantidad de imágenes está en [1, 10]
    @settings(max_examples=100, deadline=None)
    @given(
        images=st.lists(
            st.one_of(st.integers(), st.dictionaries(st.text(max_size=5), st.integers())),
            min_size=0,
            max_size=20,
        )
    )
    def test_property_is_valid_images_amount_iff_length_in_1_to_10(self, images):
        """Optional property test (task 8.4, ``design.md`` -> Correctness
        Properties -> Property 1): for any list ``images`` of arbitrary
        length between 0 and 20, with content irrelevant to the result,
        ``MetaAdsValidator.is_valid_images_amount(images) == (1 <= len(images) <= 10)``.

        Calls the real, unpatched ``MetaAdsValidator.is_valid_images_amount``
        directly (not through the use case), matching Requirement 7's
        real-implementation rule already followed by the boundary matrix
        test above, which this property test complements but does not
        replace (this task is optional per ``design.md``/``requirements.md``).

        Validates: Requirements 7.5, 7.6, 7.7
        """
        assert MetaAdsValidator.is_valid_images_amount(images) == (
            1 <= len(images) <= 10
        )

    def test_validate_images_dynamic_real_validate_images_precheck_skips_entries_without_truthy_url_without_http_request(
        self, use_case_factory
    ):
        """With entries of ``self.images`` that lack a truthy ``url``
        (one entirely missing the ``'url'`` key, one with ``url=""``, one
        with ``url=None``), the real, unpatched
        ``MetaAdsValidator.validate_images_precheck`` does not issue any
        HTTP request for those entries and its ``for`` loop's
        ``if not img_url: continue`` skips them without adding ``valid``/
        ``error`` keys to any of them.

        Neither ``MetaAdsValidator.validate_images_precheck`` nor
        ``requests.get``/``patch_image_fetch`` are patched here: the point
        of this test is to exercise the real body of
        ``validate_images_precheck`` and confirm it never reaches its
        ``requests.get`` call for these entries. The module-wide
        ``deny_network`` guard (which replaces
        ``requests.sessions.Session.request`` with a function that raises
        ``AssertionError``) stays active and would fail this test loudly if
        that assumption were ever violated.

        Requirements: 7.8
        """
        entry_missing_url_key = {"caption": "no url key at all"}
        entry_with_empty_url = make_image_entry(url="")
        entry_with_none_url = make_image_entry(url=None)
        images = [entry_missing_url_key, entry_with_empty_url, entry_with_none_url]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        asset_feed = make_asset_feed_spec()

        use_case._validate_images_dynamic(asset_feed)

        for entry in images:
            assert "valid" not in entry
            assert "error" not in entry
        assert asset_feed["images"] is images

    def test_validate_images_dynamic_real_validate_images_precheck_mutates_entry_in_place_on_simulated_network_failure_without_raising(
        self, use_case_factory
    ):
        """With an entry of ``self.images`` that has a truthy ``url``, and
        ``patch_image_fetch`` activated with a ``side_effect`` of
        ``requests.exceptions.RequestException`` on
        ``app.v2.use_cases.facebook_validator_service.requests.get``, the
        real, unpatched ``MetaAdsValidator.validate_images_precheck``
        mutates that entry in place with ``valid=False``/
        ``error="Could not fetch image"``, without
        ``_validate_images_dynamic`` (nor, transitively, ``execute()``)
        propagating any exception -- characterizing that
        ``validate_images_precheck`` never lets an exception escape by
        itself; it always catches it and records the failure on the entry
        instead.

        Requirements: 7.9
        """
        image_entry = make_image_entry()
        images = [image_entry]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        asset_feed = make_asset_feed_spec()

        with patch_image_fetch(
            side_effect=requests.exceptions.RequestException("simulated network failure")
        ):
            use_case._validate_images_dynamic(asset_feed)

        assert image_entry["valid"] is False
        assert image_entry["error"] == "Could not fetch image"
        assert asset_feed["images"] is images

    def test_execute_continues_to_save_and_build_response_with_mutated_asset_feed_after_simulated_network_failure(
        self, use_case_factory
    ):
        """After a successful ``_validate_images_dynamic`` run whose only
        image entry fails the simulated network fetch, ``execute()``
        continues, without interruption, into
        ``_save_creative_to_publish``/``_build_response``, and the
        resulting Respuesta_de_Precheck is built from the already-mutated
        ``asset_feed``: its ``images`` entry reflects
        ``valid=False``/``error="Could not fetch image"``.

        This is a full, unpatched ``execute()`` run in DYNAMIC mode:
        neither ``_validate_images_dynamic``, ``_save_creative_to_publish``
        nor ``_build_response`` are patched, only the repository/Redis/
        network collaborators are (via ``use_case_factory``,
        ``patch_redis_client`` and ``patch_image_fetch``), so
        ``ad_channel_repository.update`` (invoked by the real
        ``_save_creative_to_publish``) safely lands on a mock instance
        without touching Strapi.

        Requirements: 7.10
        """
        image_entry = make_image_entry()
        images = [image_entry]
        pre_check_images_data = make_pre_check_images_data(images=images)
        asset_feed = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_image_fetch(
            side_effect=requests.exceptions.RequestException("simulated network failure")
        ):
            mock_redis_client.get.return_value = b"some-access-token"

            result = use_case.execute()

        assert image_entry["valid"] is False
        assert image_entry["error"] == "Could not fetch image"
        assert asset_feed["images"] is images
        assert result["images"] == [
            {"url": image_entry["url"], "valid": False, "error": "Could not fetch image"}
        ]
        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            0,
            {"channel_creative": creative},
        )


class TestDynamicBranchMissingAssetFeed:
    """Tests for Requirement 8: a DYNAMIC-mode creative whose ``asset_feed``
    (``ad_creative['asset_feed_spec']``) is ``None``, an empty dict, or a
    key entirely absent from ``adCreative`` never triggers
    ``_validate_images_dynamic`` nor either ``MetaAdsValidator`` method, and
    ``execute()`` still continues on to ``_save_creative_to_publish``/
    ``_build_response`` without raising.

    All three scenarios collapse to the same outcome because of how
    ``execute()`` reads ``asset_feed`` and checks it: the production code
    evaluates ``creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')``
    -- with **no** second/default argument to that last ``.get`` call --
    and then only enters the DYNAMIC branch ``if ... and asset_feed``.
    ``None`` and ``{}`` are both falsy directly (Requirements 8.1, 8.2);
    and when the ``asset_feed_spec`` key is missing from ``adCreative``
    altogether, ``.get('asset_feed_spec')`` without a default falls back to
    ``None`` (not ``{}``), which is falsy too (Requirement 8.3) -- so all
    three scenarios are observationally identical from ``execute()``'s
    point of view.

    Requirements: 8.1, 8.2, 8.3
    """

    @pytest.mark.parametrize(
        "scenario_id, make_ad_creative_kwargs",
        [
            ("asset_feed_spec_explicit_none", {"asset_feed_spec": None}),
            ("asset_feed_spec_empty_dict", {"asset_feed_spec": {}}),
            ("asset_feed_spec_key_absent", {}),
        ],
    )
    def test_execute_skips_dynamic_validation_and_continues_without_error(
        self, use_case_factory, scenario_id, make_ad_creative_kwargs
    ):
        """With ``meta_campaign_mode="DYNAMIC"`` and ``asset_feed`` falsy
        (``None`` explicit, ``{}`` explicit, or the ``asset_feed_spec`` key
        entirely absent from ``adCreative``, per ``make_ad_creative_kwargs``),
        ``execute()`` never invokes ``_validate_images_dynamic``, never
        invokes either ``MetaAdsValidator.is_valid_images_amount`` or
        ``MetaAdsValidator.validate_images_precheck``, and still continues
        on, without raising, into ``_save_creative_to_publish`` and
        ``_build_response`` -- both with the same ``creative`` object by
        identity -- returning exactly ``_build_response``'s result.

        ``_validate_images_dynamic`` is patched on the instance (to assert
        it is never called at all, regardless of how it might internally
        invoke the validators), and both ``MetaAdsValidator`` methods are
        additionally patched at the class level (to assert, independently,
        that neither validator itself is ever reached) -- combining the two
        assertion styles already used elsewhere in this suite (e.g.
        ``TestExecuteOrchestration``'s short-circuit tests) rather than
        picking only one. ``_save_creative_to_publish``/``_build_response``
        are patched as mocks purely so this test can assert, by identity,
        that ``execute()`` reaches them with the same ``creative`` object
        without needing a fully persistence-shaped ``creative``/``asset_feed_spec``.

        Requirements: 8.1, 8.2, 8.3
        """
        ad_creative = make_ad_creative(**make_ad_creative_kwargs)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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
            use_case, "_validate_images_dynamic"
        ) as mock_validate_images_dynamic, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.is_valid_images_amount"
        ) as mock_is_valid_images_amount, patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            build_response_result = {"sentinel": f"build-response-{scenario_id}"}
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        mock_validate_images_dynamic.assert_not_called()
        assert_no_validator_calls(mock_is_valid_images_amount, mock_validate_images_precheck)
        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result


class TestValidateImagesStandard:
    """Tests for the real ``_validate_images_standard`` implementation
    (Requirement 2, 3 and 4 of ``meta-ads-standard-save-precheck-images``):
    given exactly one Imagen_Candidata (``self.images``), it validates it
    via ``MetaAdsValidator.validate_images_precheck`` and annotates the
    result onto ``story_spec['link_data']`` (``image_url``/``image_valid``/
    ``image_error``).

    This class fully replaces the previous characterization of the old
    no-op ``pass`` body (see git history for that version); it is extended,
    scenario by scenario, by later tasks of the same spec.
    """

    def test_validate_images_standard_annotates_link_data_when_exactly_one_valid_image_candidate(
        self, use_case_factory
    ):
        """With exactly one Imagen_Candidata (``self.images``) whose image
        is simulated as valid (via ``patch_image_fetch``/
        ``_build_valid_test_image_bytes``, so
        ``MetaAdsValidator.validate_images_precheck`` runs for real without
        any real HTTP request), ``_validate_images_standard`` annotates
        ``story_spec['link_data']['image_url']`` with the candidate's
        ``url``, ``['image_valid']`` as ``True`` and ``['image_error']`` as
        ``None``.

        Validates: Requirements 7.2
        """
        image_url = "https://example.test/valid-standard-image.jpg"
        images = [make_image_entry(url=image_url)]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)

        with patch_image_fetch() as mock_requests_get:
            mock_requests_get.return_value.headers = {}
            mock_requests_get.return_value.content = _VALID_TEST_IMAGE_BYTES

            use_case._validate_images_standard(story_spec)

        assert link_data["image_url"] == image_url
        assert link_data["image_valid"] is True
        assert link_data["image_error"] is None

    def test_validate_images_standard_annotates_link_data_when_exactly_one_invalid_image_candidate(
        self, use_case_factory
    ):
        """With exactly one Imagen_Candidata (``self.images``) whose fetch
        is simulated to fail (via ``patch_image_fetch`` with a
        ``side_effect`` of ``requests.exceptions.RequestException``, so
        ``MetaAdsValidator.validate_images_precheck`` runs for real and
        reaches its own ``except requests.exceptions.RequestException``
        branch without any real HTTP request), ``_validate_images_standard``
        still assigns ``story_spec['link_data']['image_url']`` with the
        candidate's ``url``, but annotates ``['image_valid']`` as ``False``
        and ``['image_error']`` with the exact message
        ``"Could not fetch image"`` that ``validate_images_precheck``
        anotates for that branch (same message already characterized for
        the DYNAMIC branch in
        ``TestValidateImagesDynamic.test_validate_images_dynamic_real_validate_images_precheck_mutates_entry_in_place_on_simulated_network_failure_without_raising``).

        Validates: Requirements 7.3
        """
        image_url = "https://example.test/invalid-standard-image.jpg"
        images = [make_image_entry(url=image_url)]
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)

        with patch_image_fetch(
            side_effect=requests.exceptions.RequestException("simulated network failure")
        ):
            use_case._validate_images_standard(story_spec)

        assert link_data["image_url"] == image_url
        assert link_data["image_valid"] is False
        assert link_data["image_error"] == "Could not fetch image"

    @pytest.mark.parametrize(
        "scenario_id, images",
        [
            ("zero_image_candidates", []),
            (
                "two_or_more_image_candidates",
                [make_image_entry(), make_image_entry()],
            ),
        ],
    )
    def test_validate_images_standard_does_not_invoke_validator_and_leaves_preexisting_image_url_unmodified_when_image_candidate_count_is_not_exactly_one(
        self, use_case_factory, scenario_id, images
    ):
        """With zero Imágenes_Candidatas or with two or more Imágenes_Candidatas
        (``self.images``), ``_validate_images_standard`` annotates
        ``story_spec['link_data']['image_valid']`` as ``False``, never
        invokes ``MetaAdsValidator.validate_images_precheck`` (patched
        directly so its non-invocation can be asserted), and leaves a
        preexisting ``story_spec['link_data']['image_url']`` unmodified.

        Validates: Requirements 7.4
        """
        pre_check_images_data = make_pre_check_images_data(images=images)
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        preexisting_image_url = "https://example.test/preexisting-image.jpg"
        link_data = make_link_data(image_url=preexisting_image_url)
        story_spec = make_object_story_spec(link_data=link_data)

        with patch(
            "app.v2.use_cases.meta_ads.MetaAdsValidator.validate_images_precheck"
        ) as mock_validate_images_precheck:
            use_case._validate_images_standard(story_spec)

        assert link_data["image_valid"] is False
        mock_validate_images_precheck.assert_not_called()
        assert link_data["image_url"] == preexisting_image_url

    def test_validate_images_standard_creates_fresh_link_data_when_key_absent_from_story_spec(
        self, use_case_factory
    ):
        """With ``story_spec`` entirely lacking the ``link_data`` key (so
        ``story_spec.get('link_data')`` is ``None``) and zero Imágenes_Candidatas
        (``self.images = []``, same 0-candidate scenario already
        characterized in task 5.3), ``_validate_images_standard`` raises no
        exception and, after the call, ``story_spec['link_data']`` is a
        brand new dict (created by the production code itself, not
        preexisting) with ``image_valid`` annotated as ``False``, exactly
        like the 0-candidate scenario: the early return for
        ``len(self.images) != 1`` never reaches the
        ``link_data['image_error'] = ...`` assignment, so ``image_error``
        is simply never set on this freshly created dict.

        Validates: Requirements 7.5
        """
        pre_check_images_data = make_pre_check_images_data(images=[])
        use_case, _, _ = use_case_factory(pre_check_images_data=pre_check_images_data)
        story_spec = make_object_story_spec()

        assert "link_data" not in story_spec

        use_case._validate_images_standard(story_spec)

        link_data = story_spec["link_data"]
        assert isinstance(link_data, dict)
        assert link_data["image_valid"] is False
        assert "image_error" not in link_data


class TestUnsupportedMetaCampaignModeRaisesValueError:
    """Tests for Requirement 10: when
    ``campaign_setup['attributes']['meta_campaign_mode']`` is anything other
    than the exact strings ``"DYNAMIC"``/``"STANDARD"`` -- including an
    empty string, ``None``, an arbitrary unrelated value, or the
    ``meta_campaign_mode`` key being entirely absent from ``attributes`` --
    ``execute()`` aborts by propagating a ``ValueError`` and nothing else
    happens: neither ``_validate_images_dynamic`` nor
    ``_validate_images_standard`` is invoked, neither
    ``ad_channel_repository.update`` nor ``_build_response`` is reached, and
    neither ``asset_feed_spec`` nor ``object_story_spec`` is mutated.

    The abort originates in ``_set_creative_type``, which converts the raw
    mode strictly::

        self.creative_type = CreativeType(
            campaign_setup.get('attributes', {}).get('meta_campaign_mode')
        ).value

    ``CreativeType`` only admits ``"DYNAMIC"`` and ``"STANDARD"``, so every
    other value -- including ``None``, which is what
    ``.get('meta_campaign_mode')`` yields when the key is absent -- raises
    ``ValueError: <value> is not a valid CreativeType``.

    ``_set_creative_type(campaign_setup)`` runs immediately after
    ``_get_campaign_setup()`` and **before** the validation ``try`` block, so
    the abort happens before the ``mode == CreativeType.DYNAMIC.value`` /
    ``mode == CreativeType.STANDARD.value`` comparisons are ever evaluated.
    Note that the left operand of both comparisons is the raw ``mode``, i.e.
    ``campaign_setup.get('attributes', {}).get('meta_campaign_mode')``, and
    not ``self.creative_type``. The two branches are therefore not
    skipped because their conditions turned out false; they are never
    reached at all.

    That is precisely why keeping ``asset_feed`` and ``story_spec`` truthy at
    the same time still matters here: both branches' right-hand operands are
    satisfied, so if the comparisons were ever reached one of them would run
    and mutate. The "neither validator ran, nothing was mutated" assertions
    below therefore remain non-vacuous -- they observe the early abort, not a
    falsy-operand no-op.

    Requirements: 10.1, 10.2
    """

    @pytest.mark.parametrize(
        "scenario_id, campaign_setup_kwargs, expected_message",
        [
            (
                "meta_campaign_mode_empty_string",
                {"meta_campaign_mode": ""},
                "'' is not a valid CreativeType",
            ),
            (
                "meta_campaign_mode_none",
                {"meta_campaign_mode": None},
                "None is not a valid CreativeType",
            ),
            (
                "meta_campaign_mode_unrelated_value",
                {"meta_campaign_mode": "SOME_OTHER_MODE"},
                "'SOME_OTHER_MODE' is not a valid CreativeType",
            ),
            (
                "meta_campaign_mode_key_absent",
                {"attributes": {}},
                "None is not a valid CreativeType",
            ),
        ],
        ids=[
            "meta_campaign_mode-empty-string",
            "meta_campaign_mode-none",
            "meta_campaign_mode-arbitrary-value",
            "meta_campaign_mode-key-absent",
        ],
    )
    def test_execute_propagates_value_error_before_invoking_either_branch_or_mutating(
        self, use_case_factory, scenario_id, campaign_setup_kwargs, expected_message
    ):
        """With ``asset_feed``/``story_spec`` both truthy, for every
        ``meta_campaign_mode`` value in ``["", None, "SOME_OTHER_MODE"]`` as
        well as ``meta_campaign_mode`` being entirely absent (achieved here
        by overriding ``attributes`` to ``{}`` on ``make_campaign_setup``,
        which replaces the whole top-level ``attributes`` dict rather than
        merging into it, since ``make_campaign_setup``'s ``**overrides``
        are applied at the top level), ``execute()`` propagates the
        ``ValueError`` raised by ``_set_creative_type`` with the exact
        message carried in the parametrization table, and no observable
        effect of the validation block or of the persistence path is left
        behind: neither ``_validate_images_dynamic`` nor
        ``_validate_images_standard`` is invoked, ``asset_feed``/
        ``story_spec`` keep exactly the same keys/values they had before
        ``execute()`` ran, ``_save_creative_to_publish``, ``_build_response``
        and ``ad_channel_repository.update`` are never called, and
        ``use_case.creative_type`` still holds the ``''`` left by the
        constructor -- ``CreativeType(...)`` raises before the assignment, so
        the failure leaves no intermediate state.

        ``_validate_images_dynamic``/``_validate_images_standard`` are
        patched on the instance (matching the convention used for the
        analogous falsy-``asset_feed``/falsy-``story_spec`` scenarios in
        ``TestDynamicBranchMissingAssetFeed``/``TestValidateImagesStandard``),
        purely to assert neither is ever called; ``_save_creative_to_publish``/
        ``_build_response`` are patched as mocks so this test can assert they
        are never reached without needing a fully persistence-shaped
        ``creative``.

        Requirements: 10.1, 10.2
        """
        asset_feed = make_asset_feed_spec(
            images=[make_image_entry()], ad_channel_id=5
        )
        story_spec = make_object_story_spec(headline="Some headline")
        ad_creative = make_ad_creative(
            asset_feed_spec=asset_feed, object_story_spec=story_spec
        )
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(**campaign_setup_kwargs)

        asset_feed_before = dict(asset_feed)
        story_spec_before = dict(story_spec)

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
            use_case, "_validate_images_dynamic"
        ) as mock_validate_images_dynamic, patch.object(
            use_case, "_validate_images_standard"
        ) as mock_validate_images_standard, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"

            with pytest.raises(ValueError) as exc_info:
                use_case.execute()

        assert str(exc_info.value) == expected_message
        mock_validate_images_dynamic.assert_not_called()
        mock_validate_images_standard.assert_not_called()
        assert asset_feed == asset_feed_before
        assert story_spec == story_spec_before
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()
        mock_ad_channel_repo_instance.update.assert_not_called()
        assert use_case.creative_type == ""


class TestMalformedCreativeStructures:
    """Tests for Requirement 11: the exact behaviour of ``execute()``'s
    validation block (the ``try`` block that extracts ``asset_feed``/
    ``story_spec``) when faced with malformed ``creative``/``ads``/
    ``adCreative`` structures -- an absent or empty ``ads`` list
    (``IndexError``), an ``adCreative`` present with an explicit ``None``
    value (``AttributeError``), and an ``adCreative`` present as ``{}`` or
    entirely absent (no exception, both collapsing to the same outcome).

    Per the production code in ``execute()``::

        ad_channel = self._get_ad_channel()
        self._set_channel_id(ad_channel)
        creative = ad_channel.get('attributes', {}).get('channel_creative', {})

        campaign_setup = self._get_campaign_setup()

        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            ...
        except Exception as e:
            raise e

        self._save_creative_to_publish(creative)
        creative_to_publish = self._build_response(creative)

    ``_get_campaign_setup()`` (and, transitively, ``_get_ad_channel()``/
    ``_set_channel_id()``) already ran, in that order, *before* the ``try``
    block is even entered -- so any doubles they use are already invoked by
    the time ``creative.get('ads', [])[0]`` is evaluated, regardless of
    which of the four scenarios below is exercised. This is verified
    directly below rather than assumed, per the task's explicit
    instruction to confirm the order against the real code.

    Requirements: 11.1, 11.2, 11.3, 11.4
    """

    @pytest.mark.parametrize(
        "scenario_id",
        ["ads_key_absent", "ads_empty_list"],
    )
    def test_execute_raises_index_error_when_ads_absent_or_empty_after_campaign_setup_already_invoked(
        self, use_case_factory, scenario_id
    ):
        """When ``creative`` has no ``ads`` key at all, or ``creative['ads']``
        is an empty list, ``execute()`` propagates ``IndexError`` while
        evaluating ``creative.get('ads', [])[0]``.

        By the time this happens, ``_get_ad_channel``'s repository call,
        ``_set_channel_id`` (``self.channel_id`` already reflects the
        Ad_Channel's nested id, not the constructor's initial ``None``),
        and ``_get_campaign_setup``'s repository call have *already*
        executed for real -- confirmed here directly via the two
        repository mocks and ``use_case.channel_id`` -- because in the
        actual source order of ``execute()``, ``_get_campaign_setup()`` is
        called before the ``try`` block that performs the
        ``creative.get('ads', [])[0]`` extraction, even though that
        extraction itself precedes ``_save_creative_to_publish``.
        ``_save_creative_to_publish``/``_build_response`` are patched as
        mocks and asserted never called, since the ``IndexError`` must
        prevent ``execute()`` from ever reaching them.

        Requirements: 11.1
        """
        if scenario_id == "ads_key_absent":
            creative = make_creative()
            del creative["ads"]
        else:
            creative = make_creative(ads=[])

        ad_channel = make_ad_channel(
            channel_ref_id="channel-11-1", channel_creative=creative
        )
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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

            with pytest.raises(IndexError) as exc_info:
                use_case.execute()

        assert_exception_type_and_message(
            exc_info, IndexError, "list index out of range"
        )
        # Confirms the doubles already invoked, in real source order,
        # before the `IndexError` is raised: `_get_ad_channel`'s
        # repository call, `_set_channel_id` (via `channel_id`), and
        # `_get_campaign_setup`'s repository call -- all of which precede
        # the `try` block in the body of `execute()`.
        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id,
            use_case.campaign_id,
            use_case.adset_id,
            use_case.ad_id,
            use_case.adchannel_id,
        )
        assert use_case.channel_id == "channel-11-1"
        assert_repository_called_once_with(
            mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id,
            use_case.campaign_id,
            "channel-11-1",
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()

    def test_execute_raises_attribute_error_when_ad_creative_is_explicit_none_before_save(
        self, use_case_factory
    ):
        """When ``creative['ads'][0]['adCreative']`` is present with an
        explicit ``None`` value, ``execute()`` propagates ``AttributeError``
        while invoking ``.get('asset_feed_spec')`` on ``None`` -- because
        ``.get('adCreative', {})``'s default is only substituted when the
        key is *absent*, never when it is present with value ``None`` --
        and this happens before ``_save_creative_to_publish`` is ever
        invoked.

        ``_save_creative_to_publish`` is patched as a mock and asserted
        never called, confirming the exception preempts persistence.

        Requirements: 11.2
        """
        creative = make_creative(ads=[make_ad(ad_creative=None)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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

            with pytest.raises(AttributeError) as exc_info:
                use_case.execute()

        assert_exception_type_and_message(
            exc_info, AttributeError, "'NoneType' object has no attribute 'get'"
        )
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()

    @pytest.mark.parametrize(
        "scenario_id, ad_creative_kwargs",
        [
            ("ad_creative_empty_dict", {}),
        ],
    )
    def test_execute_raises_no_exception_when_ad_creative_is_empty_dict_and_continues(
        self, use_case_factory, scenario_id, ad_creative_kwargs
    ):
        """When ``creative['ads'][0]['adCreative']`` is present with value
        ``{}`` (empty dict), ``execute()`` raises no exception at this
        point: both ``asset_feed`` and ``story_spec`` end up ``None`` (via
        ``{}.get('asset_feed_spec')``/``{}.get('object_story_spec')``,
        neither with a second default argument in the production code), no
        validation branch runs, and ``execute()`` continues on to
        ``_save_creative_to_publish``/``_build_response``.

        ``_validate_images_dynamic``/``_validate_images_standard`` are
        patched on the instance purely to assert neither is ever invoked
        (matching the convention already used in
        ``TestDynamicBranchMissingAssetFeed``/``TestValidateImagesStandard``
        for the analogous falsy-``asset_feed``/``story_spec`` scenarios);
        ``_save_creative_to_publish``/``_build_response`` are patched as
        mocks so this test can assert, by identity, that ``execute()``
        reaches them with the same ``creative`` object.

        Requirements: 11.3
        """
        ad_creative = make_ad_creative(**ad_creative_kwargs)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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
            use_case, "_validate_images_dynamic"
        ) as mock_validate_images_dynamic, patch.object(
            use_case, "_validate_images_standard"
        ) as mock_validate_images_standard, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            build_response_result = {"sentinel": f"build-response-{scenario_id}"}
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        mock_validate_images_dynamic.assert_not_called()
        mock_validate_images_standard.assert_not_called()
        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result

    def test_execute_raises_no_exception_when_ad_creative_key_absent_same_outcome_as_empty_dict(
        self, use_case_factory
    ):
        """When the ``adCreative`` key is entirely absent from
        ``creative['ads'][0]`` (as opposed to being present with value
        ``None`` or ``{}``), ``execute()`` raises no exception: because the
        key is absent, ``.get('adCreative', {})``'s default *does* apply
        here (unlike the explicit-``None`` scenario of Requirement 11.2),
        producing the same empty dict as Requirement 11.3, so
        ``asset_feed``/``story_spec`` both end up ``None``, no validation
        branch runs, and ``execute()`` continues on to
        ``_save_creative_to_publish``/``_build_response`` -- the same
        observable outcome as the ``adCreative={}`` scenario above.

        Requirements: 11.4
        """
        ad_without_creative = make_ad()  # `ad_creative` defaults to ABSENT.
        assert "adCreative" not in ad_without_creative
        creative = make_creative(ads=[ad_without_creative])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

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
            use_case, "_validate_images_dynamic"
        ) as mock_validate_images_dynamic, patch.object(
            use_case, "_validate_images_standard"
        ) as mock_validate_images_standard, patch.object(
            use_case, "_save_creative_to_publish"
        ) as mock_save_creative_to_publish, patch.object(
            use_case, "_build_response"
        ) as mock_build_response:
            mock_redis_client.get.return_value = b"some-access-token"
            build_response_result = {"sentinel": "build-response-ad_creative_key_absent"}
            mock_build_response.return_value = build_response_result

            result = use_case.execute()

        mock_validate_images_dynamic.assert_not_called()
        mock_validate_images_standard.assert_not_called()
        mock_save_creative_to_publish.assert_called_once_with(creative)
        mock_build_response.assert_called_once_with(creative)
        assert mock_save_creative_to_publish.call_args.args[0] is creative
        assert mock_build_response.call_args.args[0] is creative
        assert result is build_response_result


class TestTryExceptPassThrough:
    """Tests for Requirement 12: the ``try/except Exception as e: raise e``
    block inside ``execute()`` is a fully transparent pass-through -- it
    neither changes the exception's type nor its message.

    Per the production code in ``execute()``::

        try:
            asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')
            story_spec = creative.get('ads', [])[0].get('adCreative', {}).get('object_story_spec')
            ...
        except Exception as e:
            raise e

    ``raise e`` re-raises the *same* exception object that was caught,
    without constructing a new exception instance and without attaching a
    prefix/suffix to its message. This is observably identical to what
    would happen if the ``try/except`` block were removed entirely and the
    code inside it executed directly inside ``execute()``: the exception
    that originates from evaluating ``None.get('asset_feed_spec')`` would
    propagate out of ``execute()`` with the exact same type
    (``AttributeError``) and the exact same message
    (``"'NoneType' object has no attribute 'get'"``). A wrapping pattern --
    e.g. ``except Exception as e: raise RuntimeError(f"validation failed: {e}")``
    or ``except Exception as e: raise SomeCustomException(str(e)) from e`` --
    would instead change the observed type to the wrapper's type and/or
    prepend/append text to the message, which is exactly what this test
    demonstrates does *not* happen here.

    Requirements: 12.1, 12.2
    """

    def test_execute_propagates_attribute_error_with_identical_type_and_message(
        self, use_case_factory
    ):
        """Reuses the ``adCreative=None`` scenario from Requirement 11.2
        (task 13.1's ``test_execute_raises_attribute_error_when_ad_creative_is_explicit_none_before_save``)
        to verify, end-to-end from ``execute()``, that the ``AttributeError``
        observed by the caller has exactly the same type and exactly the
        same ``str(exception)`` message as the exception that originates
        inside the ``try`` block from evaluating
        ``None.get('asset_feed_spec')`` -- confirmed here both by comparing
        against a reference exception triggered directly in this test (via
        ``None.get('asset_feed_spec')`` in an isolated ``try/except``) and
        by asserting the exact standard message, since a wrapping pattern
        would typically change the type and/or add context to the message.

        This is equivalent to the behaviour that would be observed if the
        ``try/except Exception as e: raise e`` block did not exist at all
        and ``asset_feed = creative.get('ads', [])[0].get('adCreative', {}).get('asset_feed_spec')``
        executed directly in the body of ``execute()``: with no wrapping
        exception class and no added prefix/suffix, ``raise e`` reproduces
        the original exception exactly, unlike a wrapping pattern such as
        ``raise NuevaExcepcion(str(e))`` (Requirement 12.2), which *would*
        alter the observed type.

        Requirements: 12.1, 12.2
        """
        # Build the reference exception directly, outside of `execute()`,
        # by triggering the exact same expression
        # (`adCreative.get('asset_feed_spec')` with `adCreative is None`)
        # that the `try` block evaluates internally.
        try:
            None.get('asset_feed_spec')
        except Exception as reference_exc:
            reference_type = type(reference_exc)
            reference_message = str(reference_exc)
        else:  # pragma: no cover - defensive; `None.get` always raises.
            pytest.fail("expected None.get('asset_feed_spec') to raise")

        creative = make_creative(ads=[make_ad(ad_creative=None)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

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

            with pytest.raises(AttributeError) as exc_info:
                use_case.execute()

        # Same assertion helper used for the Requirement 11 scenarios: the
        # type observed from `execute()` is exactly `AttributeError` (not a
        # wrapper/custom exception type), and the message is exactly the
        # standard `NoneType` message, with no prefix/suffix.
        assert_exception_type_and_message(
            exc_info, AttributeError, "'NoneType' object has no attribute 'get'"
        )
        # Direct type/message equality against the reference exception
        # triggered independently in this test, proving the exception that
        # crosses the `try/except Exception as e: raise e` boundary inside
        # `execute()` is identical -- by type and by message -- to the one
        # that originates from the equivalent expression evaluated on its
        # own, with no wrapping and no additional context.
        assert type(exc_info.value) is reference_type
        assert str(exc_info.value) == reference_message
        mock_save_creative_to_publish.assert_not_called()
        mock_build_response.assert_not_called()


class TestSaveCreativeToPublish:
    """Tests for ``_save_creative_to_publish`` (inherited from the
    Caso_de_Uso_Abuelo, ``FacebookGeneratePreCheckCreativeUseCase``): the
    exact repository call, the per-level ``0`` default of the nested
    ``ad_channel_id`` extraction, and the ``TypeError`` exposed only when
    the method is invoked directly and in isolation with a ``creative``
    that has no ``ads`` key.

    Per the production code::

        def _save_creative_to_publish(self, creative):
            ad_channel_id = creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)
            data = {
                'channel_creative': creative
            }
            self.ad_channel_repository.update(ad_channel_id, data)

    Note the asymmetry confirmed directly against the source above:
    ``creative.get('ads')`` here has **no** second (default) argument,
    unlike the ``creative.get('ads', [])`` used inside ``execute()``'s
    validation block. When the key is absent, ``.get('ads')`` returns
    ``None``, and ``None[0]`` raises ``TypeError`` (not ``IndexError``,
    which is what ``[][0]`` would raise) -- confirmed with the Python
    runtime itself (``None[0]`` raises
    ``TypeError: 'NoneType' object is not subscriptable``), not merely
    assumed from reading the source.

    Requirements: 13.1, 13.2, 13.3, 13.4
    """

    def test_calls_update_with_exact_arguments_and_truthy_ad_channel_id(
        self, use_case_factory
    ):
        """``_save_creative_to_publish`` invokes
        ``ad_channel_repository.update`` exactly once with the exact
        arguments ``(ad_channel_id, {'channel_creative': creative})``,
        where ``creative`` is the same object by identity and
        ``ad_channel_id`` is extracted from
        ``creative.get('ads')[0].get('adCreative', {}).get('asset_feed_spec', {}).get('ad_channel_id', 0)``.
        When ``asset_feed_spec['ad_channel_id']`` is present with a truthy
        value, that exact value is used as the first positional argument.

        Requirements: 13.1, 13.2
        """
        asset_feed_spec = make_asset_feed_spec(ad_channel_id="channel-13-1")
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])

        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        use_case._save_creative_to_publish(creative)

        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            "channel-13-1",
            {"channel_creative": creative},
        )
        call_args = mock_ad_channel_repo_instance.update.call_args
        assert call_args.args[0] == "channel-13-1"
        assert call_args.args[1]["channel_creative"] is creative

    @pytest.mark.parametrize(
        "scenario_id, build_creative",
        [
            (
                "ad_creative_absent",
                lambda: make_creative(ads=[make_ad()]),
            ),
            (
                "asset_feed_spec_absent",
                lambda: make_creative(
                    ads=[make_ad(ad_creative=make_ad_creative())]
                ),
            ),
            (
                "ad_channel_id_absent",
                lambda: make_creative(
                    ads=[
                        make_ad(
                            ad_creative=make_ad_creative(
                                asset_feed_spec={
                                    k: v
                                    for k, v in make_asset_feed_spec().items()
                                    if k != "ad_channel_id"
                                }
                            )
                        )
                    ]
                ),
            ),
        ],
        ids=[
            "adCreative_absent",
            "asset_feed_spec_absent",
            "ad_channel_id_absent",
        ],
    )
    def test_defaults_ad_channel_id_to_zero_for_each_absent_level(
        self, use_case_factory, scenario_id, build_creative
    ):
        """When ``adCreative``, ``asset_feed_spec`` or ``ad_channel_id`` is
        absent (each level tested separately, with ``creative['ads']``
        always non-empty), ``ad_channel_repository.update`` is invoked with
        the default ``0`` as the first positional argument.

        Requirements: 13.3
        """
        creative = build_creative()
        assert creative["ads"], "scenario must keep a non-empty `ads` list"

        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        use_case._save_creative_to_publish(creative)

        assert_repository_called_once_with(
            mock_ad_channel_repo_instance.update,
            0,
            {"channel_creative": creative},
        )

    def test_direct_isolated_call_raises_type_error_when_ads_key_absent(
        self, use_case_factory
    ):
        """Invoking ``_save_creative_to_publish`` directly and in isolation
        (not through ``execute()``) with a ``creative`` whose ``ads`` key
        is absent propagates ``TypeError``, because
        ``creative.get('ads')`` (no default here) returns ``None``, and
        ``None[0]`` is not subscriptable.

        This path is never reachable from ``execute()``: for the exact
        same ``creative`` (missing ``ads``), ``execute()``'s validation
        block already evaluates ``creative.get('ads', [])[0]`` -- which
        *does* have a ``[]`` default -- and that expression raises
        ``IndexError`` first (Requirement 11.1), well before
        ``_save_creative_to_publish`` would ever be called. The
        ``TypeError`` characterized here is only observable by calling
        ``_save_creative_to_publish`` directly on the use case instance,
        bypassing ``execute()`` entirely, as done below.

        Requirements: 13.4
        """
        creative = make_creative()
        del creative["ads"]

        use_case, mock_ad_channel_repo_instance, _ = use_case_factory()

        with pytest.raises(TypeError) as exc_info:
            use_case._save_creative_to_publish(creative)

        assert_exception_type_and_message(
            exc_info, TypeError, "'NoneType' object is not subscriptable"
        )
        mock_ad_channel_repo_instance.update.assert_not_called()


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
    """Tests for ``_build_response`` (inherited from the Caso_de_Uso_Padre,
    ``FacebookSavePreCheckBaseUseCase``): the exact set of keys in the
    Respuesta_de_Precheck, the exact reflection of explicit
    ``asset_feed_spec`` values, the exact per-field defaults for omitted
    fields, the comma-join of ``link_urls`` into ``proposal_url``, the
    ``[]`` default for a missing ``proposal_locations``, and the reflection
    of ``valid``/``error`` values already mutated by
    ``_validate_images_dynamic`` in a full DYNAMIC ``execute()`` scenario.

    Per the production code::

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
                    'titles': _as_single_item_list(link_data.get('name'), link_data.get('title_valid', False)),
                    'descriptions': _as_single_item_list(link_data.get('description'), link_data.get('description_valid', False)),
                    'call_to_action_types': [call_to_action.get('type', {})] if call_to_action else [],
                    'images_valid_amount': link_data.get('image_valid', False),
                    'titles_valid_amount': link_data.get('title_valid', False),
                    'bodies_valid_amount': link_data.get('body_valid', False),
                    'descriptions_valid_amount': link_data.get('description_valid', False),
                    'call_to_action_types_valid_amount': call_to_action.get('type', {}).get('valid', False) if call_to_action else False,
                    'images_max_amount': 1,
                    'titles_max_amount': 1,
                    'bodies_max_amount': 1,
                    'descriptions_max_amount': 1,
                    'call_to_action_types_max_amount': 1,
                    'unique_titles': link_data.get('title_valid', False),
                    'unique_bodies': link_data.get('body_valid', False),
                    'unique_descriptions': link_data.get('description_valid', False),
                    'daily_budget_valid': object_story_spec.get('daily_budget_valid', False),
                    'min_daily_budget': object_story_spec.get('min_daily_budget', 0),
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
                    'images': [{'url': i.get('url'), 'valid': i.get('valid'), 'error': i.get('error')} for i in ad_creative.get('asset_feed_spec', {}).get('images', [])],
                    'bodies': ad_creative.get('asset_feed_spec', {}).get('bodies', []),
                    'titles': ad_creative.get('asset_feed_spec', {}).get('titles', []),
                    'descriptions': ad_creative.get('asset_feed_spec', {}).get('descriptions', []),
                    'call_to_action_types': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types', []),
                    'images_valid_amount': ad_creative.get('asset_feed_spec', {}).get('images_valid_amount', False),
                    'titles_valid_amount': ad_creative.get('asset_feed_spec', {}).get('titles_valid_amount', False),
                    'bodies_valid_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_valid_amount', False),
                    'descriptions_valid_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_valid_amount', False),
                    'call_to_action_types_valid_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_valid_amount', False),
                    'images_max_amount': ad_creative.get('asset_feed_spec', {}).get('images_max_amount', 0),
                    'titles_max_amount': ad_creative.get('asset_feed_spec', {}).get('titles_max_amount', 0),
                    'bodies_max_amount': ad_creative.get('asset_feed_spec', {}).get('bodies_max_amount', 0),
                    'descriptions_max_amount': ad_creative.get('asset_feed_spec', {}).get('descriptions_max_amount', 0),
                    'call_to_action_types_max_amount': ad_creative.get('asset_feed_spec', {}).get('call_to_action_types_max_amount', 0),
                    'unique_titles': ad_creative.get('asset_feed_spec', {}).get('unique_titles', False),
                    'unique_bodies': ad_creative.get('asset_feed_spec', {}).get('unique_bodies', False),
                    'unique_descriptions': ad_creative.get('asset_feed_spec', {}).get('unique_descriptions', False),
                    'daily_budget_valid': ad_creative.get('asset_feed_spec', {}).get('daily_budget_valid', False),
                    'min_daily_budget': ad_creative.get('asset_feed_spec', {}).get('min_daily_budget', 0),
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
    read from ``object_story_spec``/``link_data``, the three text collections
    are single-item lists built by ``_as_single_item_list``, and the five
    ``*_max_amount`` values are the literal ``1``. Under DYNAMIC every field
    is an ``asset_feed_spec.get(key, default)`` lookup and the five
    ``*_max_amount`` values default to ``0``. Scenarios that invoke
    ``_build_response`` directly, without ``execute()``, therefore assign
    ``use_case.creative_type`` themselves -- the ``''`` left by the
    constructor is not ``"STANDARD"`` and is unreachable in production,
    because ``_set_creative_type`` raises ``ValueError`` for any mode outside
    ``{"DYNAMIC", "STANDARD"}``.

    Note that in the DYNAMIC branch ``proposal_url_valid`` is read from
    ``asset_feed_spec['link_url_valid']`` (singular ``link_url``), not
    ``link_urls_valid``/``proposal_url_valid`` -- confirmed directly against
    the source above, matched exactly by the fixtures below.

    Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
    """

    EXPECTED_RESPONSE_KEYS = frozenset(
        {
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

    def test_response_contains_exactly_the_keys_from_requirement_14_1(
        self, use_case_factory
    ):
        """``_build_response`` returns a dict whose key set is exactly the
        one listed in Requirement 14.1 -- no additional keys, none missing
        -- regardless of whether ``asset_feed_spec`` provides every field or
        relies on defaults.

        Requirements: 14.1
        """
        asset_feed_spec = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])

        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        response = use_case._build_response(creative)

        assert set(response.keys()) == self.EXPECTED_RESPONSE_KEYS

    def test_response_reflects_exact_explicit_asset_feed_spec_values_including_images_projection(
        self, use_case_factory
    ):
        """When ``asset_feed_spec`` (and the surrounding ``creative``)
        provide explicit values for every field listed in Requirement
        14.1, the Respuesta_de_Precheck reflects exactly those values,
        including the projection of ``images`` to
        ``[{'url', 'valid', 'error'}]`` per entry (dropping any other key
        an image entry might carry, and reading ``valid``/``error`` off
        each entry via ``.get`` -- so entries without those keys yield
        ``None`` for them in the projection).

        Requirements: 14.2
        """
        images = [
            {"url": "https://example.test/one.jpg", "valid": True, "error": None, "extra": "dropped"},
            {"url": "https://example.test/two.jpg", "valid": False, "error": "Could not fetch image"},
        ]
        asset_feed_spec = make_asset_feed_spec(
            images=images,
            bodies=["body-1", "body-2"],
            titles=["title-1"],
            descriptions=["description-1"],
            call_to_action_types=["SHOP_NOW"],
            ad_channel_id="channel-14-2",
            images_valid_amount=True,
            titles_valid_amount=True,
            bodies_valid_amount=True,
            descriptions_valid_amount=True,
            call_to_action_types_valid_amount=True,
            images_max_amount=10,
            titles_max_amount=5,
            bodies_max_amount=5,
            descriptions_max_amount=5,
            call_to_action_types_max_amount=5,
            unique_titles=True,
            unique_bodies=True,
            unique_descriptions=True,
            daily_budget_valid=True,
            min_daily_budget=500,
            link_urls=[{"website_url": "https://a.example.test"}, {"website_url": "https://b.example.test"}],
            link_url_valid=True,
            locations=["location-1", "location-2"],
            locations_valid=True,
        )
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(
            name="Creative 14.2",
            ads=[make_ad(ad_creative=ad_creative, ad_id="ad-14-2")],
            daily_budget=999,
            proposal_locations=["proposal-location-1"],
        )

        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        response = use_case._build_response(creative)

        assert response["name"] == "Creative 14.2"
        assert response["adset_id"] == creative["id"]
        assert response["ad_id"] == "ad-14-2"
        assert response["adchannel_id"] == "channel-14-2"
        assert response["daily_budget"] == 999
        assert response["images"] == [
            {"url": "https://example.test/one.jpg", "valid": True, "error": None},
            {"url": "https://example.test/two.jpg", "valid": False, "error": "Could not fetch image"},
        ]
        assert response["bodies"] == ["body-1", "body-2"]
        assert response["titles"] == ["title-1"]
        assert response["descriptions"] == ["description-1"]
        assert response["call_to_action_types"] == ["SHOP_NOW"]
        assert response["images_valid_amount"] is True
        assert response["titles_valid_amount"] is True
        assert response["bodies_valid_amount"] is True
        assert response["descriptions_valid_amount"] is True
        assert response["call_to_action_types_valid_amount"] is True
        assert response["images_max_amount"] == 10
        assert response["titles_max_amount"] == 5
        assert response["bodies_max_amount"] == 5
        assert response["descriptions_max_amount"] == 5
        assert response["call_to_action_types_max_amount"] == 5
        assert response["unique_titles"] is True
        assert response["unique_bodies"] is True
        assert response["unique_descriptions"] is True
        assert response["daily_budget_valid"] is True
        assert response["min_daily_budget"] == 500
        assert response["proposal_url"] == "https://a.example.test,https://b.example.test"
        assert response["proposal_url_valid"] is True
        assert response["proposal_locations"] == ["proposal-location-1"]
        assert response["locations"] == ["location-1", "location-2"]
        assert response["locations_valid"] is True

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_response_uses_exact_defaults_for_every_omitted_field(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """When ``asset_feed_spec`` omits every field listed in
        Requirement 14.1 except the five collection fields with their own
        empty-list default (``images``, ``bodies``, ``titles``,
        ``descriptions``, ``call_to_action_types``), the
        Respuesta_de_Precheck uses exactly: ``False`` for each of the five
        ``*_valid_amount`` indicators, ``False`` for ``unique_titles``/
        ``unique_bodies``/``unique_descriptions``/``daily_budget_valid``/
        ``proposal_url_valid``/``locations_valid``, ``0`` for
        ``min_daily_budget``, and an empty list for ``locations``.

        The five ``*_max_amount`` values are the only ones that depend on
        the branch, so they are parametrized. ``_build_response``
        dispatches on the declared campaign mode --
        ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``) -- and each branch has its
        own default: ``0`` under DYNAMIC, where every ``*_max_amount``
        comes from an ``asset_feed_spec.get('*_max_amount', 0)`` lookup
        that finds nothing in an empty ``asset_feed_spec``, and ``1`` under
        STANDARD, where the extraction hardcodes the literal ``1`` (the
        exact-cardinality-1 rule for STANDARD ad sets). Because this
        scenario invokes ``_build_response`` directly, without
        ``execute()``, ``_set_creative_type`` never runs and the mode must
        be fixed by the test itself; the parametrization does exactly that
        and asserts both branches.

        An entirely empty ``asset_feed_spec`` (``{}``) is used directly
        here, rather than ``make_asset_feed_spec()``'s own defaults, so
        every ``.get(key, default)`` in ``_build_response`` is forced to
        fall back to its own production default rather than to a value the
        test builder happens to pre-populate.

        Requirements: 14.3
        """
        ad_creative = make_ad_creative(asset_feed_spec={})
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])

        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        response = use_case._build_response(creative)

        assert response["images_valid_amount"] is False
        assert response["titles_valid_amount"] is False
        assert response["bodies_valid_amount"] is False
        assert response["descriptions_valid_amount"] is False
        assert response["call_to_action_types_valid_amount"] is False
        assert response["images_max_amount"] == expected_max_amount
        assert response["titles_max_amount"] == expected_max_amount
        assert response["bodies_max_amount"] == expected_max_amount
        assert response["descriptions_max_amount"] == expected_max_amount
        assert response["call_to_action_types_max_amount"] == expected_max_amount
        assert response["unique_titles"] is False
        assert response["unique_bodies"] is False
        assert response["unique_descriptions"] is False
        assert response["daily_budget_valid"] is False
        assert response["proposal_url_valid"] is False
        assert response["locations_valid"] is False
        assert response["min_daily_budget"] == 0
        assert response["locations"] == []
        assert response["images"] == []
        assert response["bodies"] == []
        assert response["titles"] == []
        assert response["descriptions"] == []
        assert response["call_to_action_types"] == []
        assert response["proposal_url"] == ""

    def test_proposal_url_is_comma_joined_website_urls_in_the_same_order(
        self, use_case_factory
    ):
        """When ``asset_feed_spec['link_urls']`` contains multiple entries
        with a ``website_url``, ``proposal_url`` in the Respuesta_de_Precheck
        is exactly ``','.join(...)`` of those values, in the same order as
        ``link_urls``.

        Requirements: 14.4
        """
        link_urls = [
            {"website_url": "https://first.example.test"},
            {"website_url": "https://second.example.test"},
            {"website_url": "https://third.example.test"},
        ]
        asset_feed_spec = make_asset_feed_spec(link_urls=link_urls)
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])

        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        response = use_case._build_response(creative)

        assert response["proposal_url"] == (
            "https://first.example.test,https://second.example.test,https://third.example.test"
        )

    def test_proposal_locations_is_empty_list_when_creative_omits_the_key(
        self, use_case_factory
    ):
        """When ``creative`` omits the ``proposal_locations`` key entirely,
        ``proposal_locations`` in the Respuesta_de_Precheck is an empty
        list.

        ``make_creative()`` already defaults ``proposal_locations`` to the
        ``ABSENT`` sentinel (omitting the key), matching this scenario
        directly; the assertion below also confirms the key really is
        absent from the built ``creative``, so the empty-list result can
        only come from ``_build_response``'s own default, not from the
        builder pre-populating it.

        Requirements: 14.5
        """
        asset_feed_spec = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        assert "proposal_locations" not in creative

        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.DYNAMIC.value

        response = use_case._build_response(creative)

        assert response["proposal_locations"] == []

    def test_execute_dynamic_branch_response_reflects_images_mutated_by_validate_images_dynamic(
        self, use_case_factory
    ):
        """In a full, unpatched DYNAMIC ``execute()`` run, the
        Respuesta_de_Precheck's ``images`` projection reflects the exact
        ``valid``/``error`` values that ``_validate_images_dynamic``
        already mutated onto ``self.images`` (via the real
        ``MetaAdsValidator.validate_images_precheck``) -- one entry
        succeeds (simulated network success through ``patch_image_fetch``'s
        default success response) and one entry fails (simulated network
        failure) -- demonstrating that ``_build_response`` reads
        ``asset_feed_spec`` *after* the DYNAMIC validation mutation, not a
        pre-validation copy.

        Neither ``_validate_images_dynamic``, ``_save_creative_to_publish``
        nor ``_build_response`` are patched here: only the repository/
        Redis/network collaborators are, via ``use_case_factory``,
        ``patch_redis_client`` and two separate ``patch_image_fetch``
        activations (one per image entry, since ``requests.get`` itself is
        the substitution point, not a per-URL selector).

        Requirements: 14.6
        """
        succeeding_entry = make_image_entry(url="https://example.test/succeeds.jpg")
        failing_entry = make_image_entry(url="https://example.test/fails.jpg")
        images = [succeeding_entry, failing_entry]
        pre_check_images_data = make_pre_check_images_data(images=images)
        asset_feed_spec = make_asset_feed_spec()
        ad_creative = make_ad_creative(asset_feed_spec=asset_feed_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="DYNAMIC")

        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        def _fake_requests_get(url, *args, **kwargs):
            if url == succeeding_entry["url"]:
                fake_response = MagicMock()
                fake_response.raise_for_status.return_value = None
                fake_response.headers = {}
                fake_response.content = _VALID_TEST_IMAGE_BYTES
                return fake_response
            raise requests.exceptions.RequestException("simulated network failure")

        with patch_redis_client() as mock_redis_client, patch(
            "app.v2.use_cases.facebook_validator_service.requests.get",
            side_effect=_fake_requests_get,
        ):
            mock_redis_client.get.return_value = b"some-access-token"

            result = use_case.execute()

        assert succeeding_entry["valid"] is True
        assert succeeding_entry.get("error") is None
        assert failing_entry["valid"] is False
        assert failing_entry["error"] == "Could not fetch image"
        assert result["images"] == [
            {"url": succeeding_entry["url"], "valid": True, "error": None},
            {"url": failing_entry["url"], "valid": False, "error": "Could not fetch image"},
        ]
        assert asset_feed_spec["images"] is images

    def test_execute_standard_branch_response_contains_expected_keys_and_reflects_validated_image(
        self, use_case_factory
    ):
        """In a full, unpatched STANDARD ``execute()`` run (with
        ``_validate_images_standard`` NOT patched), the resulting
        Respuesta_de_Precheck contains exactly the key set from the
        Glossary of ``requirements.md`` (``EXPECTED_RESPONSE_KEYS``), and
        its ``images`` field reflects the single Imagen_Candidata's real
        validation outcome: one entry with ``valid=True``/``error=None``,
        exactly the shape produced by ``_build_response``'s STANDARD
        extraction branch.

        Neither ``_validate_images_standard``, ``_save_creative_to_publish``
        nor ``_build_response`` are patched here: only the repository/
        Redis/network collaborators are, via ``use_case_factory``,
        ``patch_redis_client`` and ``patch_image_fetch`` (simulating a
        successful fetch of a real, valid in-memory image).

        Validates: Requirements 7.6
        """
        image_url = "https://example.test/standard-execute-image.jpg"
        images = [make_image_entry(url=image_url)]
        pre_check_images_data = make_pre_check_images_data(images=images)
        link_data = make_link_data()
        story_spec = make_object_story_spec(link_data=link_data)
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        creative = make_creative(ads=[make_ad(ad_creative=ad_creative)])
        ad_channel = make_ad_channel(channel_creative=creative)
        campaign_setup = make_campaign_setup(meta_campaign_mode="STANDARD")

        use_case, mock_ad_channel_repo_instance, mock_campaign_publish_repo_instance = (
            use_case_factory(pre_check_images_data=pre_check_images_data)
        )
        mock_ad_channel_repo_instance.get_by_campaign_and_ad_channel_id.return_value = (
            ad_channel
        )
        mock_campaign_publish_repo_instance.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with patch_redis_client() as mock_redis_client, patch_image_fetch() as mock_requests_get:
            mock_redis_client.get.return_value = b"some-access-token"
            mock_requests_get.return_value.headers = {}
            mock_requests_get.return_value.content = _VALID_TEST_IMAGE_BYTES

            result = use_case.execute()

        assert set(result.keys()) == self.EXPECTED_RESPONSE_KEYS
        assert result["images"] == [{"url": image_url, "valid": True, "error": None}]

    def test_direct_isolated_call_reflects_pre_annotated_standard_link_data_per_mapping_table(
        self, use_case_factory
    ):
        """Invoking ``_build_response`` directly and in isolation (not
        through ``execute()``) with a fully-populated ``object_story_spec``/
        ``link_data`` -- including annotations already present from a prior
        ``FacebookGeneratePreCheckCreativeUseCase.execute()`` run
        (``title_valid``, ``body_valid``, ``daily_budget_valid``,
        ``call_to_action``) -- the Respuesta_de_Precheck reflects exactly
        those values, per the "``CreativeToPublish`` para STANDARD" mapping
        table of ``design.md``.

        In particular:

        - ``titles``/``bodies``/``descriptions`` are each a single-item
          list built from ``link_data['name']``/``['message']``/
          ``['description']`` paired with their own ``*_valid`` flag --
          note that ``bodies`` still contains an entry even though
          ``body_valid`` is ``False``, because ``_as_single_item_list``
          only checks the *value*'s truthiness, not the valid flag.
        - ``call_to_action_types`` is a single-item list of the raw
          ``call_to_action['type']`` dict, and
          ``call_to_action_types_valid_amount`` is read from
          ``call_to_action['type']['valid']``.
        - ``daily_budget_valid``/``min_daily_budget`` come from
          ``object_story_spec``, not from ``link_data``.
        - ``proposal_url``/``proposal_url_valid`` come from
          ``link_data['link']``/``['link_url_valid']``.
        - ``locations``/``locations_valid`` come from
          ``object_story_spec``.
        - ``images`` reflects ``link_data['image_url']``/``['image_valid']``/
          ``['image_error']``.
        - ``adchannel_id`` reflects the explicit, truthy
          ``object_story_spec['ad_channel_id']``.

        The whole mapping table above depends on the STANDARD extraction
        branch, which ``_build_response`` selects from the declared campaign
        mode (``if self.creative_type == CreativeType.STANDARD.value:``,
        ``app/v2/use_cases/meta_ads.py:2533``). A direct, isolated call never
        runs ``_set_creative_type``, so this scenario fixes
        ``creative_type = CreativeType.STANDARD.value`` itself, mirroring
        what ``execute()`` would have assigned from
        ``campaign_setup['attributes']['meta_campaign_mode']``. It is not
        parametrized over DYNAMIC: its ``creative`` carries an
        ``object_story_spec`` and deliberately carries no
        ``asset_feed_spec``, so under DYNAMIC the entire table would
        collapse to the defaults and duplicate the defaults scenarios.

        Requirements: 7.7
        """
        link_data = make_link_data(
            name="Headline from a prior GeneratePreCheckCreative run",
            title_valid=True,
            message="Body from a prior GeneratePreCheckCreative run",
            body_valid=False,
            description="Description from a prior GeneratePreCheckCreative run",
            description_valid=True,
            image_url="https://example.test/standard-build-response-image.jpg",
            image_valid=True,
            image_error=None,
            link="https://example.test/proposal",
            link_url_valid=True,
            call_to_action={"type": {"value": "SIGN_UP", "valid": True}},
        )
        story_spec = make_object_story_spec(
            link_data=link_data,
            daily_budget_valid=True,
            min_daily_budget=750,
            ad_channel_id="channel-7-7",
            locations=["location-7-7-a", "location-7-7-b"],
            locations_valid=True,
        )
        ad_creative = make_ad_creative(object_story_spec=story_spec)
        creative = make_creative(
            name="Creative 7.7",
            ads=[make_ad(ad_creative=ad_creative, ad_id="ad-7-7")],
            daily_budget=321,
            proposal_locations=["proposal-location-7-7"],
        )

        use_case, _, _ = use_case_factory()
        use_case.creative_type = CreativeType.STANDARD.value

        response = use_case._build_response(creative)

        assert response["name"] == "Creative 7.7"
        assert response["adset_id"] == creative["id"]
        assert response["ad_id"] == "ad-7-7"
        assert response["adchannel_id"] == "channel-7-7"
        assert response["daily_budget"] == 321
        assert response["images"] == [
            {
                "url": link_data["image_url"],
                "valid": True,
                "error": None,
            }
        ]
        assert response["titles"] == [
            {"text": link_data["name"], "valid_length": True}
        ]
        assert response["bodies"] == [
            {"text": link_data["message"], "valid_length": False}
        ]
        assert response["descriptions"] == [
            {"text": link_data["description"], "valid_length": True}
        ]
        assert response["call_to_action_types"] == [{"value": "SIGN_UP", "valid": True}]
        assert response["images_valid_amount"] is True
        assert response["titles_valid_amount"] is True
        assert response["bodies_valid_amount"] is False
        assert response["descriptions_valid_amount"] is True
        assert response["call_to_action_types_valid_amount"] is True
        assert response["images_max_amount"] == 1
        assert response["titles_max_amount"] == 1
        assert response["bodies_max_amount"] == 1
        assert response["descriptions_max_amount"] == 1
        assert response["call_to_action_types_max_amount"] == 1
        assert response["unique_titles"] is True
        assert response["unique_bodies"] is False
        assert response["unique_descriptions"] is True
        assert response["daily_budget_valid"] is True
        assert response["min_daily_budget"] == 750
        assert response["proposal_url"] == link_data["link"]
        assert response["proposal_url_valid"] is True
        assert response["proposal_locations"] == ["proposal-location-7-7"]
        assert response["locations"] == ["location-7-7-a", "location-7-7-b"]
        assert response["locations_valid"] is True

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_direct_isolated_call_returns_default_response_when_ad_creative_is_explicit_none(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """Invoking ``_build_response`` directly and in isolation (not
        through ``execute()``) with ``creative['ads'][0]['adCreative']``
        present but set to an explicit ``None`` no longer raises
        ``AttributeError``: this behavior changed as part of
        ``meta-ads-standard-save-precheck-images`` (Requirement 5.1/5.4),
        which normalizes ``ad_creative = ads_to_publish.get('adCreative') or {}``
        before deriving ``object_story_spec``/``asset_feed_spec`` from it.

        That normalization is what keeps the ``AttributeError`` away, and it
        is the primary intent of this scenario: with ``ad_creative``
        normalized to ``{}``, both ``object_story_spec`` and
        ``asset_feed_spec`` come out ``None`` and neither branch ever calls
        ``.get(...)`` on ``None``.

        Which branch runs is a separate matter, decided by the declared
        campaign mode: ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``). A direct, isolated call
        never runs ``_set_creative_type``, so the mode is fixed here by the
        parametrization and both branches are asserted. Under STANDARD,
        ``object_story_spec = object_story_spec or {}`` and
        ``link_data = object_story_spec.get('link_data') or {}`` both
        normalize to ``{}``, so every field falls back to its own STANDARD
        default; under DYNAMIC, every field is an
        ``ad_creative.get('asset_feed_spec', {}).get(key, default)`` lookup
        against a missing ``asset_feed_spec``, so every field falls back to
        its own DYNAMIC default. The two branches agree on 25 of the 30
        response keys for this shape; the five ``*_max_amount`` values are
        the only ones that differ, hence their parametrized expectation.

        This is a deliberate behavior change from the code prior to this
        specification (which propagated
        ``AttributeError: 'NoneType' object has no attribute 'get'`` for
        this exact shape), explicitly authorized by Requirement 1.5
        ("salvo los ajustes estrictamente necesarios para acomodar la
        extensión de `_build_response` descrita en el Requirement 5") and
        justified by the design's Error Handling section
        (Requirement 5.1/5.4/7.8). It does not violate Requirement 6
        (non-regression), because Requirement 6 protects only ads whose
        ``asset_feed_spec`` is truthy (real DYNAMIC ads); an ``adCreative``
        that is explicitly ``None`` never has a truthy ``asset_feed_spec``,
        so it never falls under that protection.

        Requirements: 7.8
        """
        creative = make_creative(ads=[make_ad(ad_creative=None)])

        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        response = use_case._build_response(creative)

        assert set(response.keys()) == self.EXPECTED_RESPONSE_KEYS
        assert response["name"] == creative.get("name")
        assert response["adset_id"] == creative.get("id")
        assert response["ad_id"] == creative["ads"][0].get("id")
        assert response["daily_budget"] == creative.get("daily_budget")
        assert response["proposal_locations"] == []
        assert response["adchannel_id"] == 0
        assert response["images"] == []
        assert response["bodies"] == []
        assert response["titles"] == []
        assert response["descriptions"] == []
        assert response["call_to_action_types"] == []
        assert response["images_valid_amount"] is False
        assert response["titles_valid_amount"] is False
        assert response["bodies_valid_amount"] is False
        assert response["descriptions_valid_amount"] is False
        assert response["call_to_action_types_valid_amount"] is False
        assert response["images_max_amount"] == expected_max_amount
        assert response["titles_max_amount"] == expected_max_amount
        assert response["bodies_max_amount"] == expected_max_amount
        assert response["descriptions_max_amount"] == expected_max_amount
        assert response["call_to_action_types_max_amount"] == expected_max_amount
        assert response["unique_titles"] is False
        assert response["unique_bodies"] is False
        assert response["unique_descriptions"] is False
        assert response["daily_budget_valid"] is False
        assert response["min_daily_budget"] == 0
        assert response["proposal_url"] == ""
        assert response["proposal_url_valid"] is False
        assert response["locations"] == []
        assert response["locations_valid"] is False

    @pytest.mark.parametrize(
        "creative_type, expected_max_amount", _BUILD_RESPONSE_DEFAULTS_BRANCHES
    )
    def test_direct_isolated_call_returns_default_response_when_ad_creative_key_absent(
        self, use_case_factory, creative_type, expected_max_amount
    ):
        """Invoking ``_build_response`` directly and in isolation (not
        through ``execute()``) with the ``adCreative`` key entirely absent
        from ``ads_to_publish`` produces exactly the same no-exception,
        all-defaults outcome as the explicit-``None`` scenario above,
        because ``ads_to_publish.get('adCreative') or {}`` also normalizes
        to ``{}`` when the key is missing.

        The observable equivalence under test is precisely that: a missing
        ``adCreative`` key behaves exactly like a key present with ``None``.
        The normalization is what keeps the ``AttributeError`` away in both
        shapes, and that equivalence is now asserted under both extraction
        branches.

        Which branch runs is decided by the declared campaign mode --
        ``if self.creative_type == CreativeType.STANDARD.value:``
        (``app/v2/use_cases/meta_ads.py:2533``) -- and a direct, isolated
        call never runs ``_set_creative_type``, so the mode is fixed here by
        the parametrization. With ``ad_creative`` normalized to ``{}``,
        neither ``object_story_spec`` nor ``asset_feed_spec`` is ever
        available, so each branch falls back to its own defaults
        throughout: the two agree on 25 of the 30 response keys for this
        shape and differ only in the five ``*_max_amount`` values, hence
        their parametrized expectation.

        This is a deliberate behavior change from the code prior to this
        specification (which propagated
        ``AttributeError: 'NoneType' object has no attribute 'get'`` for
        this exact shape), explicitly authorized by Requirement 1.5 and
        justified by the design's Error Handling section
        (Requirement 5.1/5.4/7.8). It does not violate Requirement 6
        (non-regression), because Requirement 6 protects only ads whose
        ``asset_feed_spec`` is truthy (real DYNAMIC ads); an ``adCreative``
        whose key is entirely absent never has a truthy ``asset_feed_spec``,
        so it never falls under that protection.

        Requirements: 7.8
        """
        creative = make_creative(ads=[make_ad()])
        assert "adCreative" not in creative["ads"][0]

        use_case, _, _ = use_case_factory()
        use_case.creative_type = creative_type

        response = use_case._build_response(creative)

        assert set(response.keys()) == self.EXPECTED_RESPONSE_KEYS
        assert response["name"] == creative.get("name")
        assert response["adset_id"] == creative.get("id")
        assert response["ad_id"] == creative["ads"][0].get("id")
        assert response["daily_budget"] == creative.get("daily_budget")
        assert response["proposal_locations"] == []
        assert response["adchannel_id"] == 0
        assert response["images"] == []
        assert response["bodies"] == []
        assert response["titles"] == []
        assert response["descriptions"] == []
        assert response["call_to_action_types"] == []
        assert response["images_valid_amount"] is False
        assert response["titles_valid_amount"] is False
        assert response["bodies_valid_amount"] is False
        assert response["descriptions_valid_amount"] is False
        assert response["call_to_action_types_valid_amount"] is False
        assert response["images_max_amount"] == expected_max_amount
        assert response["titles_max_amount"] == expected_max_amount
        assert response["bodies_max_amount"] == expected_max_amount
        assert response["descriptions_max_amount"] == expected_max_amount
        assert response["call_to_action_types_max_amount"] == expected_max_amount
        assert response["unique_titles"] is False
        assert response["unique_bodies"] is False
        assert response["unique_descriptions"] is False
        assert response["daily_budget_valid"] is False
        assert response["min_daily_budget"] == 0
        assert response["proposal_url"] == ""
        assert response["proposal_url_valid"] is False
        assert response["locations"] == []
        assert response["locations_valid"] is False


_LEADS_OFFSITE_URL_OK = "https://example.test/ok.jpg"
_LEADS_OFFSITE_URL_FAIL = "https://example.test/fail.jpg"

_COMBINATION_LEADS_OFFSITE = ("OUTCOME_LEADS", "OFFSITE_CONVERSIONS")
_COMBINATION_LEAD_GENERATION = ("OUTCOME_LEADS", "LEAD_GENERATION")
_COMBINATION_SALES_OFFSITE = ("OUTCOME_SALES", "OFFSITE_CONVERSIONS")


class TestLeadsOffsiteSaveImages:
    """Coverage of ``FacebookSavePreCheckImagesUseCase.execute()`` for the
    Combinación_Leads_Offsite (``OUTCOME_LEADS`` + ``OFFSITE_CONVERSIONS``)
    in both Rama_DYNAMIC and Rama_STANDARD, plus the field-by-field
    differential against ``OUTCOME_LEADS`` + ``LEAD_GENERATION`` and the
    non-regression cases for Otras_Combinaciones.

    Every scenario is a full, unpatched ``execute()`` run: only the
    repositories (``use_case_factory``), Redis (``patch_redis_client``) and
    the image HTTP fetch (``patch_image_fetch``) are doubled.
    ``_save_creative_to_publish`` is wrapped by a spy that delegates to the
    real implementation, so persistence reaches the mocked
    ``AdChannelRepository.update``.

    Requirements: 10.5, 10.6, 10.7, 10.8, 14.9
    """

    @staticmethod
    def _fake_fetch(url, timeout=None):
        """Simulated ``requests.get``: ``_LEADS_OFFSITE_URL_OK`` returns a
        valid 400x400 PNG; any other URL fails with ``RequestException``."""
        if url == _LEADS_OFFSITE_URL_OK:
            response = MagicMock()
            response.raise_for_status.return_value = None
            response.headers = {}
            response.content = _VALID_TEST_IMAGE_BYTES
            return response
        raise requests.exceptions.RequestException("simulated network failure")

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
        return make_creative(ads=[make_ad(ad_creative=ad_creative)])

    @staticmethod
    def _build_images(mode):
        if mode == "DYNAMIC":
            return [
                make_image_entry(url=_LEADS_OFFSITE_URL_OK),
                make_image_entry(url=_LEADS_OFFSITE_URL_FAIL),
            ]
        return [make_image_entry(url=_LEADS_OFFSITE_URL_OK)]

    def _run(self, use_case_factory, mode, combination, promoted_object_valid=True):
        """Run a full ``execute()`` and return
        ``(result, creative, update_mock, save_spy)``."""
        objective, goal = combination
        creative = self._build_creative(mode, promoted_object_valid)
        pre_check_images_data = make_pre_check_images_data(
            images=self._build_images(mode)
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
            pre_check_images_data=pre_check_images_data
        )
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel(channel_creative=creative)
        )
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )
        with patch_redis_client() as mock_redis_client, patch_image_fetch(
            side_effect=self._fake_fetch
        ), patch.object(
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
        assert asset_feed["images"] == [
            {"url": _LEADS_OFFSITE_URL_OK, "valid": True, "error": None},
            {"url": _LEADS_OFFSITE_URL_FAIL, "valid": False, "error": "Could not fetch image"},
        ]
        assert asset_feed["images_valid_amount"] is True
        save_spy.assert_called_once_with(creative)
        assert_repository_called_once_with(
            update_mock, 7, {"channel_creative": creative}
        )
        assert result["adchannel_id"] == 7
        assert result["images"] == asset_feed["images"]
        assert result["images_valid_amount"] is True

    @staticmethod
    def _assert_standard_outcome(result, creative, update_mock, save_spy):
        ad = creative["ads"][0]
        link_data = ad["adCreative"]["object_story_spec"]["link_data"]
        assert link_data["image_url"] == _LEADS_OFFSITE_URL_OK
        assert link_data["image_valid"] is True
        assert link_data["image_error"] is None
        save_spy.assert_called_once_with(creative)
        assert_repository_called_once_with(
            update_mock, 8, {"channel_creative": {**creative, "ads": [ad]}}
        )
        assert result["adchannel_id"] == 8
        assert result["images"] == [
            {"url": _LEADS_OFFSITE_URL_OK, "valid": True, "error": None}
        ]
        assert result["images_valid_amount"] is True
        assert result["images_max_amount"] == 1

    # ------------------------------------------------------------------
    # Happy paths for Combinación_Leads_Offsite (Req 10.6, 14.9)
    # ------------------------------------------------------------------

    def test_dynamic_happy_path_leads_offsite(self, use_case_factory):
        """DYNAMIC + Combinación_Leads_Offsite finishes without exception,
        annotates the images and persists through ``AdChannelRepository``
        via exactly one ``_save_creative_to_publish`` call.

        Requirements: 10.6, 14.9
        """
        outcome = self._run(use_case_factory, "DYNAMIC", _COMBINATION_LEADS_OFFSITE)
        self._assert_dynamic_outcome(*outcome)

    def test_standard_happy_path_leads_offsite(self, use_case_factory):
        """STANDARD + Combinación_Leads_Offsite finishes without exception,
        annotates ``link_data`` and persists through ``AdChannelRepository``
        via exactly one ``_save_creative_to_publish`` call.

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
