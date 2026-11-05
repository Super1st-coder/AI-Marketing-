"""Test suite for ``FacebookExportAssetsPostLaunchCampaignUseCase``.

Target under test:
``app.v2.use_cases.meta_ads.FacebookExportAssetsPostLaunchCampaignUseCase``,
its sanitized constructor, the private helpers that implement the five
pre-validations (payload, token/account, campaign, ad-channel,
campaign-setup), the two read-only surplus collectors over the
Ad_Channel_de_Exportación (``media_formats`` and ``channel_attributes``),
the in-memory ZIP packaging step and the Resultado_de_Exportación contract.

This module is the single new file authorized by Requirement 1.2 of
``sinergia/.kiro/specs/meta-ads-export-assets-post-launch-campaign/``. It is
a pure unit suite: no Flask application or request context, no
``conftest.py``, zero real network traffic, zero Redis connections and zero
Strapi requests in every single case (Requirement 12.2).

The builders below reproduce the **production shape** of the Strapi payloads
confirmed by the maintainer (see the *Data Models* section of ``design.md``).
``make_media_format`` in particular always carries the seven auxiliary keys
(``uid``, ``unit``, ``width``, ``height``, ``errors``, ``visual_id``,
``preview_url``) that the Caso_de_Uso must ignore, so that every main-flow
case implicitly exercises Requirement 7.10: if the implementation ever
downloaded ``preview_url``, the download double would record one extra
invocation and the count assertions would fail.

The builders also carry the **four Nombres_de_Origen** from which the name of
the Paquete_ZIP is derived (Requirement 10.4): ``make_campaign`` supplies
``attributes.name`` and ``make_ad_channel`` supplies the three populated name
relations ``attributes.ad_ref2.data.attributes.name``,
``attributes.ad_ref2.data.attributes.ad_set_ref2.data.attributes.name`` and
``attributes.channel_ref.data.attributes.name``, following the populated
response shape documented in ``design.md``. Their defaults are already
whitelist-clean, hold no digit at all — so no identifier of the
Payload_de_Exportación can accidentally be a substring of the resulting name —
and are distinct from one another, so a swapped component breaks the exact
filename comparison of Requirement 12.25.

Requirements: 7.10, 10.4, 12.1, 12.3
"""

import os
import re
import zipfile
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.exceptions.base import (
    DataNotFoundException,
    IncorrectValidationException,
    NotAccessException,
    ParametersNotFoundException,
)
from app.v2.repository.ad_channel import AdChannelRepository
from app.v2.use_cases.facebook_validator_service import CreativeType
from app.v2.use_cases.meta_ads import FacebookExportAssetsPostLaunchCampaignUseCase


class _AbsentSentinel:
    """Private sentinel type used by the payload builders below.

    Its sole purpose is to let a builder distinguish "this key was not
    provided by the caller, omit it from the resulting dict" from "this key
    was provided by the caller with the value ``None``". That distinction is
    formally required by Requirements 7.7, 7.8, 8.5, 8.6, 8.7, 8.10, 8.11
    and 9.4, where absence and ``None`` are different scenarios with
    different expected outcomes.

    Requirements: 12.3
    """

    def __repr__(self):
        return "ABSENT"


ABSENT = _AbsentSentinel()


# Real production ``visual_url`` values of the three formats of the
# ``ad-channel`` record supplied by the maintainer (see *Data Models* in
# ``design.md``). They all live in the ``production-banners`` S3 bucket and
# all end in ``.jpeg``, which is what makes ``.jpeg`` — and not ``.jpg`` —
# the extension derived by default (Requirement 9.3).
_VISUAL_URL_FACEBOOK_POST = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "12271afc-a8c8-4a0f-a5c9-6999ec76cee9.jpeg"
)
_VISUAL_URL_INSTAGRAM_PORTRAIT = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "c46eaade-94b4-468f-9e1f-62d493f0def3.jpeg"
)
_VISUAL_URL_INSTAGRAM_STORY = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "bb5ea12f-67a6-4024-a4aa-24ace40dcb88.jpeg"
)
_PREVIEW_URL = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/templates/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "c87c1252-4d41-45b9-84b8-2b5f8d92f56b.png"
)


# The four default Nombres_de_Origen of the builders, in the order in which
# Requirement 10.4 interpolates them: campaign, ad set, ad, channel.
#
# Three properties are deliberate and load-bearing:
#
# * every character already belongs to the whitelist ``[A-Za-z0-9._-]`` of
#   Requirement 10.12, so the sanitisation is the identity on them and the
#   main-flow filename is stable and readable;
# * they hold **no digit at all**, so the string representation of none of the
#   five identifiers of the Payload_de_Exportación (``101``, ``7``, ``202``,
#   ``303``, ``404``) can be a substring of the resulting name by accident,
#   which is what makes the exclusion half of Requirement 12.25 meaningful;
# * they are distinct from one another and none is a prefix or suffix of
#   another, so swapping any two components breaks the exact comparison.
_DEFAULT_CAMPAIGN_NAME = "Black_Friday"
_DEFAULT_AD_SET_NAME = "AdSet_Prospecting"
_DEFAULT_AD_NAME = "Ad_Retargeting"
_DEFAULT_CHANNEL_NAME = "facebook"


def make_export_payload(**overrides):
    """Build a fresh Payload_de_Exportación with the five required keys.

    Every invocation returns a brand new dict, so callers can freely mutate
    the returned value without affecting other cases (Requirement 12.3).

    Any override whose value is the ``ABSENT`` sentinel removes that key
    from the result entirely, which is how the key-absent half of the
    ``clave x tipo de invalidez`` matrix of Requirements 2.3 and 12.9 is
    built; pass ``None`` or ``''`` explicitly for the other two halves.

    Requirements: 2.3, 12.3, 12.9
    """
    data = {
        "campaign_id": 101,
        "brand_id": 7,
        "adset_id": 202,
        "ad_id": 303,
        "adchannel_id": 404,
    }
    data.update(overrides)
    for key in [key for key, value in data.items() if value is ABSENT]:
        del data[key]
    return data


def make_account(parent_account_id=ABSENT, account_id=1):
    """Build a fresh ``account`` dict as returned by
    ``AccountRepository.get_by_email``.

    ``parent_account_id`` defaults to the ``ABSENT`` sentinel: when left
    untouched, the ``parent_account`` key is omitted from ``attributes``
    entirely, so ``_get_parent_account`` falls back to the account's own
    ``id`` (Requirement 3.8). Pass an explicit identifier to exercise the
    nested ``attributes.parent_account.data.id`` path instead
    (Requirement 3.7).

    Requirements: 3.7, 3.8, 12.3
    """
    attributes = {}
    if parent_account_id is not ABSENT:
        attributes["parent_account"] = {"data": {"id": parent_account_id}}
    return {"id": account_id, "attributes": attributes}


def make_campaign(name=_DEFAULT_CAMPAIGN_NAME, **overrides):
    """Build a fresh ``campaign`` record as returned by
    ``CampaignRepository.get_by_id_brand_and_account``.

    It carries ``id`` and an ``attributes`` node holding **exactly one** key,
    ``name``: Requirement 4.6 allows the Caso_de_Uso to read that single
    attribute — the Nombre_de_Origen of the campaign feeding the first
    component of the filename of Requirement 10.4 — and forbids it from
    reading any other, so a record with nothing else in ``attributes`` must be
    enough to both resolve the campaign and name the Paquete_ZIP.

    Three degradations are reachable through the parameters:

    * ``name=ABSENT`` omits the ``name`` key while keeping ``attributes``,
      the "source name absent" half of Requirement 10.13;
    * ``name=None``, ``name=123`` or ``name='   '`` keep the key with a value
      that is unusable — ``None``, not a ``str`` instance, or blank after the
      sanitisation of Requirement 10.12 — the other halves of the same
      criterion;
    * ``make_campaign(attributes=ABSENT)`` omits the ``attributes`` key
      altogether, since ``**overrides`` are merged at the **top level**, which
      is the degenerate record that must still resolve (Requirement 4.6).

    Requirements: 4.6, 10.4, 10.13, 12.3
    """
    attributes = {}
    if name is not ABSENT:
        attributes["name"] = name
    data = {"id": 101, "attributes": attributes}
    data.update(overrides)
    for key in [key for key, value in data.items() if value is ABSENT]:
        del data[key]
    return data


def make_media_format(format_id="facebook-post", visual_url=None, pinned=False, **overrides):
    """Build a fresh element of ``media_formats`` with the **production
    shape** confirmed by the maintainer (see *Data Models* in ``design.md``).

    ``visual_url=None`` means "use the realistic default", a
    ``production-banners`` URL ending in ``.jpeg``; the derived extension is
    therefore ``.jpeg`` and the expected main-flow entry name is
    ``images/facebook-post.jpeg`` (Requirement 9.3 takes the extension as it
    appears in the URL, without normalizing ``.jpeg`` to ``.jpg``).

    Any of ``format_id``, ``visual_url`` and ``pinned`` set to the ``ABSENT``
    sentinel removes the corresponding key (``id``, ``visual_url``,
    ``pinned``) from the result, covering the absence scenarios of
    Requirements 7.7, 7.8 and 9.4. To exercise a key **present with value
    ``None``**, mutate the returned dict, which is always freshly built and
    freely mutable.

    The seven auxiliary keys are **always present**, exactly as in
    production, and the Caso_de_Uso must ignore all of them
    (Requirement 7.10): ``preview_url`` in particular is a perfectly valid
    image URL whose binary must never be downloaded nor packaged.

    Requirements: 7.10, 9.3, 12.3
    """
    if visual_url is None:
        visual_url = _VISUAL_URL_FACEBOOK_POST
    media_format = {
        # The three keys the Caso_de_Uso reads (Requirement 7.10).
        "id": format_id,
        "visual_url": visual_url,
        "pinned": pinned,
        # The seven real auxiliary keys, which the Caso_de_Uso must IGNORE.
        "uid": "45124a95-21da-11f1-b0d8-0293afdb0cd1",
        "unit": "px",
        "width": 1200,
        "height": 1200,
        "errors": [],
        "visual_id": "12271afc-a8c8-4a0f-a5c9-6999ec76cee9",
        "preview_url": _PREVIEW_URL,
    }
    media_format.update(overrides)
    for key in [key for key, value in media_format.items() if value is ABSENT]:
        del media_format[key]
    return media_format


def make_text_payload(payload_id=1, text="Texto excedente"):
    """Build a fresh element of a ``payloads`` list, of the form
    ``{'id': ..., 'payload': ...}``.

    ``id == 0`` is the published base asset and ``id != 0`` are the
    Textos_Excedentes (Requirement 8.2), hence the default of ``1``.

    ``payload_id=ABSENT`` omits the ``id`` key and ``text=ABSENT`` omits the
    ``payload`` key, covering the absence scenarios of Requirements 8.10 and
    8.11; pass ``None`` or ``''`` explicitly for the present-but-unusable
    ones.

    Requirements: 8.2, 8.10, 8.11, 12.3
    """
    data = {}
    if payload_id is not ABSENT:
        data["id"] = payload_id
    if text is not ABSENT:
        data["payload"] = text
    return data


def make_channel_attribute(name="primary_text", payloads=None, **overrides):
    """Build a fresh element of ``channel_attributes``, of the form
    ``{'name': ..., 'payloads': [...]}``.

    ``payloads=None`` means "use a fresh default list" holding the published
    base asset (``id == 0``) plus one Texto_Excedente (``id == 1``); pass
    ``payloads=[]`` explicitly for the empty-list scenario. The list is
    rebuilt on every invocation, so no state is shared between cases
    (Requirement 12.3).

    ``name`` is compared case-sensitively and without whitespace
    normalization by the Caso_de_Uso (Requirement 8.1), so passing
    ``'Primary_Text'`` or ``' primary_text '`` yields an attribute that must
    be skipped without logging an error (Requirement 8.8). ``name=ABSENT``
    or ``payloads=ABSENT`` omits the corresponding key
    (Requirements 8.6, 8.7).

    Requirements: 8.1, 8.6, 8.7, 8.8, 12.3
    """
    if payloads is None:
        payloads = [
            make_text_payload(payload_id=0, text="Cuerpo publicado en Meta"),
            make_text_payload(payload_id=1, text="Cuerpo alternativo A"),
        ]
    data = {"name": name, "payloads": payloads}
    data.update(overrides)
    for key in [key for key, value in data.items() if value is ABSENT]:
        del data[key]
    return data


def degrade_nested_key(node, path, value=ABSENT):
    """Degrade one intermediate key of a nested read path, in place.

    ``path`` is the sequence of keys leading to the key to degrade, starting at
    ``node`` itself. ``value=ABSENT`` **deletes** that key; any other value
    **replaces** it, which is how the "absent or not a ``dict`` instance"
    matrix of Requirement 5.10 is built over the three read paths of
    Requirement 5.9 without hand-writing one fixture per level.

    The node is mutated and also returned, so it composes with the builders::

        ad_channel = degrade_nested_key(
            make_ad_channel(), ('attributes', 'ad_ref2', 'data'), 'not-a-dict'
        )

    Requirements: 5.9, 5.10, 12.3
    """
    current = node
    for key in path[:-1]:
        current = current[key]
    if value is ABSENT:
        del current[path[-1]]
    else:
        current[path[-1]] = value
    return node


def make_ad_channel(
    channel_ref_id=1,
    media_formats=None,
    channel_attributes=None,
    ad_name=_DEFAULT_AD_NAME,
    ad_set_name=_DEFAULT_AD_SET_NAME,
    channel_name=_DEFAULT_CHANNEL_NAME,
    degraded_paths=None,
    **overrides
):
    """Build a fresh Ad_Channel_de_Exportación as returned by
    ``AdChannelRepository.get_by_campaign_and_ad_channel_id`` **with
    ``populate_names=True``**, that is with the three name relations populated
    exactly as the JSON shape documented in ``design.md``::

        attributes.ad_ref2.data.attributes.name                              -> ad
        attributes.ad_ref2.data.attributes.ad_set_ref2.data.attributes.name   -> ad set
        attributes.channel_ref.data.attributes.name                          -> channel

    Those three, plus the ``name`` of ``make_campaign``, are the four
    Nombres_de_Origen of Requirement 5.9 from which the filename of
    Requirement 10.4 is derived.

    ``channel_ref.data`` keeps carrying ``id`` next to its new ``attributes``
    node, because the Channel_ID of Requirement 5.3 is still read from that
    very path and the population of ``name`` must not displace it.

    ``ad_name``, ``ad_set_name`` and ``channel_name`` each accept ``ABSENT`` to
    omit their ``name`` key while keeping the surrounding structure intact, or
    any unusable value (``None``, a non-``str``, a blank string) for the other
    halves of Requirement 10.13. ``degraded_paths`` accepts an iterable of
    ``(path, value)`` pairs handed to ``degrade_nested_key``, so any
    intermediate key of the three paths can be made absent or turned into a
    non-``dict`` value for Requirement 5.10.

    Both ``media_formats`` and ``channel_attributes`` are flat JSON fields of
    the ``ad-channels`` content type, so Strapi always returns them inside
    ``attributes`` without any ``populate`` (see OQ-4, RESOLVED).

    ``media_formats=None`` means "use a fresh default list" reproducing the
    three production formats: ``facebook-post`` (not pinned),
    ``instagram-portrait`` (``pinned=True``, the published asset) and
    ``instagram-story`` (not pinned), each with its own real ``visual_url``
    so that a content swap between ZIP entries makes assertions fail.
    ``channel_attributes=None`` means "use a fresh default list" with the
    four Categorías_de_Texto (``primary_text``, ``headline``,
    ``description``, ``cta``), each holding one base asset and one surplus.

    ``ABSENT`` on either argument omits that key from ``attributes``
    (Requirements 7.7, 8.5); ``**overrides`` are merged at the **top level**
    (not into ``attributes``), so ``make_ad_channel(attributes=ABSENT)``
    omits ``attributes`` altogether and ``make_ad_channel(attributes={...})``
    replaces it wholesale, which is how the four absence levels of the
    ``attributes.channel_ref.data.id`` path of Requirement 5.5 are built.
    ``channel_ref_id=ABSENT`` omits the innermost ``id`` key.

    Every value is rebuilt on each invocation, so the returned structure is
    freely mutable — mutate it to exercise a key **present with value
    ``None``** (for example ``ad_channel['attributes']['media_formats'] =
    None``).

    Requirements: 5.3, 5.5, 5.9, 5.10, 7.7, 8.5, 12.3
    """
    if media_formats is None:
        media_formats = [
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
                pinned=False,
            ),
            make_media_format(
                format_id="instagram-portrait",
                visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
                pinned=True,
            ),
            make_media_format(
                format_id="instagram-story",
                visual_url=_VISUAL_URL_INSTAGRAM_STORY,
                pinned=False,
            ),
        ]
    if channel_attributes is None:
        channel_attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=0, text="Cuerpo publicado en Meta"),
                    make_text_payload(payload_id=1, text="Cuerpo alternativo A"),
                ],
            ),
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
            make_channel_attribute(
                name="description",
                payloads=[
                    make_text_payload(payload_id=0, text="Descripcion publicada"),
                    make_text_payload(payload_id=1, text="Descripcion alterna"),
                ],
            ),
            make_channel_attribute(
                name="cta",
                payloads=[
                    make_text_payload(payload_id=0, text="Comprar ahora"),
                    make_text_payload(payload_id=1, text="Mas informacion"),
                ],
            ),
        ]
    # The populated ``ad_set_ref2`` relation, nested inside ``ad_ref2``.
    ad_set_attributes = {}
    if ad_set_name is not ABSENT:
        ad_set_attributes["name"] = ad_set_name
    # The populated ``ad_ref2`` relation, carrying its own ``name`` and the
    # nested ``ad_set_ref2``.
    ad_attributes = {
        "ad_set_ref2": {"data": {"attributes": ad_set_attributes}},
    }
    if ad_name is not ABSENT:
        ad_attributes["name"] = ad_name
    # The populated ``channel_ref`` relation: ``id`` for Requirement 5.3 and
    # ``attributes.name`` for the fourth filename component.
    channel_ref_data = {}
    if channel_ref_id is not ABSENT:
        channel_ref_data["id"] = channel_ref_id
    channel_attributes_node = {}
    if channel_name is not ABSENT:
        channel_attributes_node["name"] = channel_name
    channel_ref_data["attributes"] = channel_attributes_node
    attributes = {
        "media_formats": media_formats,
        "channel_attributes": channel_attributes,
        "ad_ref2": {"data": {"attributes": ad_attributes}},
        "channel_ref": {"data": channel_ref_data},
    }
    for key in [key for key, value in attributes.items() if value is ABSENT]:
        del attributes[key]
    data = {"id": 77, "attributes": attributes}
    data.update(overrides)
    for key in [key for key, value in data.items() if value is ABSENT]:
        del data[key]
    for path, value in (degraded_paths or []):
        degrade_nested_key(data, path, value)
    return data


def make_campaign_setup(meta_published=True, meta_campaign_mode="STANDARD", **overrides):
    """Build a fresh Campaign_Setup as returned by
    ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``.

    Defaults describe the happy path: published (``meta_published`` is
    literally ``True``, compared by identity in Requirement 6.4, so ``1``,
    ``'True'`` and ``'true'`` are rejected) and in ``STANDARD`` mode
    (compared case-sensitively and without whitespace normalization in
    Requirement 6.5, so ``'standard'`` and ``' STANDARD '`` are rejected).

    ``meta_published=ABSENT`` or ``meta_campaign_mode=ABSENT`` omits the
    corresponding key from ``attributes``. ``**overrides`` are merged at the
    **top level**, so ``make_campaign_setup(attributes=ABSENT)`` omits
    ``attributes`` altogether, the scenario where both reads yield ``None``
    without raising (Requirement 6.3).

    Requirements: 6.3, 6.4, 6.5, 12.3
    """
    attributes = {
        "meta_published": meta_published,
        "meta_campaign_mode": meta_campaign_mode,
    }
    for key in [key for key, value in attributes.items() if value is ABSENT]:
        del attributes[key]
    data = {"id": 55, "attributes": attributes}
    data.update(overrides)
    for key in [key for key, value in data.items() if value is ABSENT]:
        del data[key]
    return data


# ---------------------------------------------------------------------------
# Shared fixtures and helpers (Requirements 12.2, 12.3)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    """Local guard (not a global ``conftest.py`` fixture), ``autouse=True`` at
    function scope, that replaces ``requests.sessions.Session.request`` with a
    function that fails immediately.

    This is the additional line of defense demanded by Requirement 12.2: it
    guarantees zero real network traffic even in the scenarios where
    ``patch_image_download`` is **not** active but a Formato_de_Medio
    unexpectedly carries a usable ``visual_url``. It coexists with
    ``patch_image_download``: when the latter is active,
    ``app.v2.use_cases.meta_ads.requests.get`` is already substituted long
    before execution could ever reach ``Session.request``, so this guard never
    interferes with the download scenarios.

    It replicates literally the mechanism already present in the sibling suite
    ``sinergia/tests/v2/unit/use_cases/test_facebook_save_pre_check_images.py``.

    Requirements: 12.2
    """

    def _raise_on_network_access(*args, **kwargs):
        raise AssertionError(
            "Network access is forbidden in this unit test suite; "
            "patch the relevant collaborator instead of hitting the network."
        )

    monkeypatch.setattr("requests.sessions.Session.request", _raise_on_network_access)


@contextmanager
def patch_redis_client():
    """Context manager that patches ``app.v2.use_cases.meta_ads.redis_client``
    and yields the resulting ``MagicMock``, so a scenario can configure
    ``.get.return_value``/``.get.side_effect`` directly, for example::

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

    This is patch point #5 of the six external dependencies of
    Requirement 12.2. Redis is resolved during ``execute()`` (not in
    ``__init__``), hence a context manager wrapped around the invocation
    rather than a construction-time fixture.

    Used by the tests of ``_get_decoded_access_token`` and by every
    ``execute()`` scenario, including the missing-token short circuit of
    Requirement 3.2.

    Requirements: 12.2
    """
    with patch("app.v2.use_cases.meta_ads.redis_client") as mock_redis_client:
        yield mock_redis_client


def expected_image_binary(visual_url):
    """Return the deterministic, **URL-specific** binary that
    ``patch_image_download`` serves for ``visual_url``.

    Deriving the payload from the URL itself is what makes Requirement 12.6
    verifiable: every ``visual_url`` of a fixture yields a different byte
    string, so a content swap between two ``images/...`` entries of the
    Paquete_ZIP necessarily breaks the byte-for-byte assertions.

    Requirements: 12.6
    """
    return "BINARY:{}".format(visual_url).encode("utf-8")


@contextmanager
def patch_image_download(responses=None):
    """Context manager that patches ``app.v2.use_cases.meta_ads.requests.get``
    (patch point #6 of Requirement 12.2) with a double that **dispatches by
    URL** through ``side_effect``, and yields the resulting ``MagicMock``.

    ``responses`` is an optional mapping of URL to the outcome desired for
    that URL. Four forms are accepted:

    * an ``Exception`` instance or class (for example
      ``requests.exceptions.Timeout`` or ``requests.exceptions.Timeout()``):
      the double **raises** it, exercising the "download raised" branch of
      Requirements 7.4 and 7.6, and cause (c) of an Asset_No_Incluido;
    * an ``int``: the double returns a response whose ``status_code`` is that
      value and whose ``content`` is empty, exercising the
      ``status_code != 200`` branch of Requirements 7.5 and 7.6, and cause (b)
      of an Asset_No_Incluido;
    * a ``bytes`` value: the double returns a ``200`` response carrying
      exactly those bytes;
    * a ``dict``: its ``status_code`` and ``content`` keys are used verbatim,
      defaulting to ``200`` and to the URL-derived binary respectively.

    Every URL not listed in ``responses`` resolves successfully with status
    ``200`` and the URL-specific binary of ``expected_image_binary``, so a
    happy-path scenario needs no configuration at all.

    Note what this does **not** do: it never inspects which URLs the
    Caso_de_Uso *should* have requested. That is precisely how Requirement
    7.10 is exercised implicitly — since ``make_media_format`` always carries
    a perfectly downloadable ``preview_url``, an implementation that read it
    would register one extra invocation here and break the call-count
    assertions of Requirements 12.8 and 12.16.

    Requirements: 12.2, 12.6
    """
    if responses is None:
        responses = {}

    def _dispatch(url, *args, **kwargs):
        outcome = responses.get(url)

        if isinstance(outcome, type) and issubclass(outcome, BaseException):
            raise outcome()
        if isinstance(outcome, BaseException):
            raise outcome

        response = MagicMock()
        if isinstance(outcome, int) and not isinstance(outcome, bool):
            response.status_code = outcome
            response.content = b""
        elif isinstance(outcome, bytes):
            response.status_code = 200
            response.content = outcome
        elif isinstance(outcome, dict):
            response.status_code = outcome.get("status_code", 200)
            response.content = outcome.get("content", expected_image_binary(url))
        else:
            response.status_code = 200
            response.content = expected_image_binary(url)
        return response

    with patch("app.v2.use_cases.meta_ads.requests.get") as mock_requests_get:
        mock_requests_get.side_effect = _dispatch
        yield mock_requests_get


def read_zip(content):
    """Open ``content`` as an in-memory ZIP archive and return the pair
    ``(namelist, {entry_name: bytes})``.

    ``namelist`` preserves the archive's own entry order (the order in which
    the Caso_de_Uso wrote them, relevant to Requirement 9.16); sort it in the
    assertion when the criterion asks for the alphabetically ordered list.

    This single helper already covers reading ``manifest.txt``: the manifest
    tests fetch ``contents['manifest.txt'].decode('utf-8')`` and compare it by
    exact string equality, so no manifest-specific reader is needed.

    Requirements: 12.4, 12.5, 12.6
    """
    with zipfile.ZipFile(BytesIO(content)) as zip_file:
        namelist = zip_file.namelist()
        contents = {name: zip_file.read(name) for name in namelist}
    return namelist, contents


def image_entries(namelist):
    """Return the subset of ``namelist`` holding the image entries, that is
    the names starting with ``'images/'``.

    Pure readability sugar for the entry-count assertions of Requirements
    12.7, 12.8 and 12.18.

    Requirements: 12.7, 12.8, 12.18
    """
    return [name for name in namelist if name.startswith("images/")]


def manifest_lines(contents):
    """Return the UTF-8 decoded lines of the ``manifest.txt`` entry when it is
    present in ``contents``, and ``None`` when it is absent.

    Returning ``None`` rather than an empty list on absence is deliberate: it
    makes the present/absent distinction of Requirement 9.11 explicit in the
    assertion, since a present-but-empty manifest and an absent manifest carry
    opposite meanings (incomplete versus complete package).

    Requirements: 9.9, 9.10, 9.11
    """
    if "manifest.txt" not in contents:
        return None
    return contents["manifest.txt"].decode("utf-8").split("\n")


def assert_exception_type(exc_info, expected_type):
    """Assert that the exception captured by ``pytest.raises`` has **exactly**
    ``expected_type`` (not a subclass of it).

    The message text is deliberately never asserted: Requirement 12.9
    explicitly forbids comparing it, because the four exceptions of this flow
    carry translated, human-facing text that must be free to change without
    breaking the suite. The one place where messages *are* compared is the
    indistinguishability check of Requirement 4.5, which compares two messages
    against **each other**, never against a literal.

    Requirements: 12.9
    """
    assert type(exc_info.value) is expected_type, (
        "expected exception type {!r}, got {!r} instead".format(
            expected_type, type(exc_info.value)
        )
    )


# ---------------------------------------------------------------------------
# Builder independence (Requirement 12.3)
# ---------------------------------------------------------------------------


def _container_ids(value):
    """Collect the ``id()`` of every ``dict`` and ``list`` reachable from
    ``value``, including ``value`` itself.

    Used by ``TestBuildersIndependence`` to prove structural independence: if
    two consecutive invocations of a builder share no single mutable container,
    then no case can possibly leak state into another through them.
    """
    found = set()
    if isinstance(value, dict):
        found.add(id(value))
        for item in value.values():
            found |= _container_ids(item)
    elif isinstance(value, list):
        found.add(id(value))
        for item in value:
            found |= _container_ids(item)
    return found


_ALL_BUILDERS = [
    ("make_export_payload", make_export_payload),
    ("make_account", make_account),
    ("make_campaign", make_campaign),
    ("make_media_format", make_media_format),
    ("make_channel_attribute", make_channel_attribute),
    ("make_text_payload", make_text_payload),
    ("make_ad_channel", make_ad_channel),
    ("make_campaign_setup", make_campaign_setup),
]


class TestBuildersIndependence:
    """Smoke tests for the eight builders of this module: two invocations of
    the same builder must produce entirely distinct objects, and mutating one
    must never be observable through the other.

    This is the guarantee Requirement 12.3 asks for — no test case shares
    mutable state with another, so the outcome of a case is independent of the
    suite's execution order. It is checked here once, up front, rather than
    trusted implicitly by the ~200 assertions that follow.

    Requirements: 12.3
    """

    @pytest.mark.parametrize(
        "builder", [builder for _, builder in _ALL_BUILDERS],
        ids=[name for name, _ in _ALL_BUILDERS],
    )
    def test_two_invocations_return_equal_but_not_identical_objects(self, builder):
        """Same value, different object."""
        first = builder()
        second = builder()

        assert first == second
        assert first is not second

    @pytest.mark.parametrize(
        "builder", [builder for _, builder in _ALL_BUILDERS],
        ids=[name for name, _ in _ALL_BUILDERS],
    )
    def test_two_invocations_share_no_mutable_container(self, builder):
        """Requirement 12.3: no ``dict`` and no ``list`` is shared between two
        invocations, at any nesting depth. This is what rules out mutable
        default arguments and makes the outcome of every case independent of
        the execution order of the suite.
        """
        first = builder()
        second = builder()

        assert _container_ids(first).isdisjoint(_container_ids(second))

    @pytest.mark.parametrize(
        "builder", [builder for _, builder in _ALL_BUILDERS],
        ids=[name for name, _ in _ALL_BUILDERS],
    )
    def test_mutating_top_level_of_one_does_not_affect_the_other(self, builder):
        """Adding and removing top-level keys in one result leaves the other
        untouched.
        """
        first = builder()
        second = builder()
        pristine = builder()

        first["injected_by_test"] = "mutated"
        for key in list(first.keys()):
            if key != "injected_by_test":
                del first[key]

        assert "injected_by_test" not in second
        assert second == pristine

    def test_mutating_nested_media_formats_does_not_affect_the_other(self):
        """The nested ``media_formats`` list of one Ad_Channel_de_Exportación is
        not the one of another, and neither are the dicts inside it.
        """
        first = make_ad_channel()
        second = make_ad_channel()

        first["attributes"]["media_formats"].append(make_media_format(format_id="extra"))
        first["attributes"]["media_formats"][0]["pinned"] = True
        first["attributes"]["media_formats"][0]["visual_url"] = "https://mutated.test/x.jpg"

        assert len(second["attributes"]["media_formats"]) == 3
        assert second["attributes"]["media_formats"][0]["pinned"] is False
        assert (
            second["attributes"]["media_formats"][0]["visual_url"]
            == _VISUAL_URL_FACEBOOK_POST
        )

    def test_mutating_nested_channel_attributes_does_not_affect_the_other(self):
        """Same guarantee for ``channel_attributes`` and for the ``payloads``
        lists nested two levels down.
        """
        first = make_ad_channel()
        second = make_ad_channel()

        first["attributes"]["channel_attributes"][0]["payloads"].append(
            make_text_payload(payload_id=99, text="Inyectado por la prueba")
        )
        first["attributes"]["channel_attributes"][0]["payloads"][1]["payload"] = "mutado"
        first["attributes"]["channel_attributes"].pop()

        assert len(second["attributes"]["channel_attributes"]) == 4
        assert len(second["attributes"]["channel_attributes"][0]["payloads"]) == 2
        assert (
            second["attributes"]["channel_attributes"][0]["payloads"][1]["payload"]
            == "Cuerpo alternativo A"
        )

    def test_mutating_default_payloads_of_channel_attribute_does_not_affect_the_other(self):
        """``make_channel_attribute`` rebuilds its default ``payloads`` list on
        every invocation, so it is not a shared mutable default.
        """
        first = make_channel_attribute()
        second = make_channel_attribute()

        first["payloads"].clear()

        assert len(second["payloads"]) == 2
        assert second["payloads"][1]["payload"] == "Cuerpo alternativo A"

    def test_mutating_media_format_errors_list_does_not_affect_the_other(self):
        """The auxiliary ``errors`` list of ``make_media_format`` is fresh too,
        even though the Caso_de_Uso must never read it (Requirement 7.10).
        """
        first = make_media_format()
        second = make_media_format()

        first["errors"].append("boom")

        assert second["errors"] == []


class TestSharedHelpers:
    """Self-tests for the shared helpers above.

    A helper that silently misbehaves would weaken every assertion built on
    top of it, so the four non-trivial ones are characterized here: the
    network guard actually fires, the download double dispatches per URL,
    ``read_zip`` round-trips, and ``manifest_lines`` distinguishes an absent
    manifest from a present one.

    Requirements: 12.2, 12.3
    """

    def test_deny_network_blocks_real_session_requests(self):
        """Requirement 12.2, the zero-real-traffic half: the autouse guard is
        active without any explicit opt-in, so a case that reached the network
        would fail instead of leaving the process.
        """
        with pytest.raises(AssertionError):
            requests.Session().request("GET", "https://example.test")

    def test_patch_image_download_serves_a_distinct_binary_per_url(self):
        """Requirement 12.6 hinges on this: two URLs, two different payloads."""
        with patch_image_download() as mock_requests_get:
            first = mock_requests_get(_VISUAL_URL_FACEBOOK_POST, timeout=10)
            second = mock_requests_get(_VISUAL_URL_INSTAGRAM_STORY, timeout=10)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.content != second.content
        assert first.content == expected_image_binary(_VISUAL_URL_FACEBOOK_POST)
        assert second.content == expected_image_binary(_VISUAL_URL_INSTAGRAM_STORY)

    def test_patch_image_download_honours_a_configured_status_code(self):
        """An ``int`` outcome yields that status code, cause (b) of an
        Asset_No_Incluido.
        """
        responses = {_VISUAL_URL_INSTAGRAM_STORY: 404}

        with patch_image_download(responses) as mock_requests_get:
            failing = mock_requests_get(_VISUAL_URL_INSTAGRAM_STORY, timeout=10)
            succeeding = mock_requests_get(_VISUAL_URL_FACEBOOK_POST, timeout=10)

        assert failing.status_code == 404
        assert succeeding.status_code == 200

    @pytest.mark.parametrize(
        "outcome",
        [requests.exceptions.Timeout, requests.exceptions.Timeout("timed out")],
        ids=["exception_class", "exception_instance"],
    )
    def test_patch_image_download_raises_a_configured_exception(self, outcome):
        """Both an exception class and an instance are accepted, cause (c) of an
        Asset_No_Incluido.
        """
        responses = {_VISUAL_URL_INSTAGRAM_STORY: outcome}

        with patch_image_download(responses) as mock_requests_get:
            with pytest.raises(requests.exceptions.Timeout):
                mock_requests_get(_VISUAL_URL_INSTAGRAM_STORY, timeout=10)

            unaffected = mock_requests_get(_VISUAL_URL_FACEBOOK_POST, timeout=10)

        assert unaffected.status_code == 200

    def test_patch_redis_client_yields_a_configurable_double(self):
        """The Redis double is configurable and records its invocations."""
        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"some-access-token"

            assert mock_redis_client.get("facebook_access_token:user-1") == (
                b"some-access-token"
            )

        mock_redis_client.get.assert_called_once_with("facebook_access_token:user-1")

    def test_read_zip_returns_namelist_and_contents(self):
        """``read_zip`` round-trips a ZIP built the same way the Caso_de_Uso
        builds it.
        """
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("images/facebook-post.jpeg", b"first-binary")
            zip_file.writestr("primary_texts.txt", "Cuerpo\nOtro".encode("utf-8"))

        namelist, contents = read_zip(buffer.getvalue())

        assert namelist == ["images/facebook-post.jpeg", "primary_texts.txt"]
        assert contents["images/facebook-post.jpeg"] == b"first-binary"
        assert contents["primary_texts.txt"].decode("utf-8") == "Cuerpo\nOtro"

    def test_read_zip_handles_an_archive_without_entries(self):
        """The Requirement 9.13 outcome is a valid ZIP with an empty namelist."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED):
            pass

        namelist, contents = read_zip(buffer.getvalue())

        assert namelist == []
        assert contents == {}

    def test_image_entries_filters_only_the_images_prefix(self):
        namelist = [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
            "primary_texts.txt",
            "manifest.txt",
        ]

        assert image_entries(namelist) == [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ]

    def test_manifest_lines_returns_none_when_the_entry_is_absent(self):
        """Absence means "complete package" and must be distinguishable from an
        empty manifest (Requirement 9.11).
        """
        assert manifest_lines({"primary_texts.txt": b"Cuerpo"}) is None

    def test_manifest_lines_splits_the_present_entry(self):
        contents = {"manifest.txt": "facebook-post\ninstagram-story".encode("utf-8")}

        assert manifest_lines(contents) == ["facebook-post", "instagram-story"]

    def test_assert_exception_type_accepts_the_exact_type_and_rejects_others(self):
        """The helper checks the exact type and never the message text."""
        with pytest.raises(DataNotFoundException) as exc_info:
            raise DataNotFoundException(text="cualquier texto")

        assert_exception_type(exc_info, DataNotFoundException)

        with pytest.raises(AssertionError):
            assert_exception_type(exc_info, IncorrectValidationException)


# ---------------------------------------------------------------------------
# Use case factory (Requirement 12.2)
# ---------------------------------------------------------------------------


_EXPECTED_INSTANCE_ATTRIBUTES = {
    "user_id",
    "account_repository",
    "campaign_channel_publish_repository",
    "ad_channel_repository",
    "campaign_repository",
}


@pytest.fixture
def use_case_factory():
    """Fixture that builds a factory for
    ``FacebookExportAssetsPostLaunchCampaignUseCase`` instances whose four
    repositories are test doubles.

    Each call to the returned factory patches the four repository classes **in
    the namespace from which the Caso_de_Uso resolves them**, that is
    ``app.v2.use_cases.meta_ads.AccountRepository``,
    ``app.v2.use_cases.meta_ads.CampaignRepository``,
    ``app.v2.use_cases.meta_ads.AdChannelRepository`` and
    ``app.v2.use_cases.meta_ads.CampaignChannelPublishRepository``, **before**
    constructing the use case — the four instances are created inside
    ``__init__``, so patching afterwards would come too late — and then
    returns::

        (use_case,
         mock_account_repo,
         mock_campaign_repo,
         mock_ad_channel_repo,
         mock_campaign_publish_repo)

    Those are patch points #1 to #4 of the six external dependencies of
    Requirement 12.2; Redis (#5) and the image download (#6) are resolved
    during ``execute()`` and are therefore supplied by the
    ``patch_redis_client`` / ``patch_image_download`` context managers instead.

    The patches are released as soon as the factory returns, which is
    deliberate and harmless: the use case already holds a reference to each
    mock instance in the corresponding attribute, so the doubles stay in place
    for the whole test while the module-level names are restored.

    Calling the factory multiple times (within the same test or across tests)
    always produces a brand new use case and brand new mock instances; nothing
    is shared between invocations.

    Requirements: 11.2, 12.2
    """

    def _factory(user_id="user-1"):
        with patch(
            "app.v2.use_cases.meta_ads.AccountRepository"
        ) as mock_account_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignRepository"
        ) as mock_campaign_repository_cls, patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case = FacebookExportAssetsPostLaunchCampaignUseCase(user_id)
            mock_account_repo = mock_account_repository_cls.return_value
            mock_campaign_repo = mock_campaign_repository_cls.return_value
            mock_ad_channel_repo = mock_ad_channel_repository_cls.return_value
            mock_campaign_publish_repo = mock_campaign_publish_repository_cls.return_value

        return (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        )

    return _factory


class TestConstructorSanitation:
    """Characterization of the sanitized ``__init__`` (Requirement 11).

    Before this specification, ``__init__`` contained the line
    ``self.brand_repository = BrandRepository()``, which raised ``NameError``
    at instantiation time because ``BrandRepository`` is not imported in
    ``sinergia/app/v2/use_cases/meta_ads.py``. The endpoint was therefore
    unusable before any export logic could run.

    These tests pin the post-fix contract: the class instantiates cleanly,
    ``brand_repository`` stays **undefined** (not ``None``), exactly five
    instance attributes exist, and construction is completely inert — zero
    Strapi queries, zero Redis accesses and zero HTTP requests.

    Requirements: 11.1, 11.2, 11.3, 11.6
    """

    def test_instantiation_does_not_raise(self, use_case_factory):
        """Requirement 11.1: ``__init__`` completes without ``NameError`` or any
        other exception.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert isinstance(use_case, FacebookExportAssetsPostLaunchCampaignUseCase)

    def test_instantiation_with_the_real_repositories_does_not_raise(self):
        """Requirement 11.1 again, this time with the four **real** repository
        classes, since the ``NameError`` lived in the constructor body itself.

        This is the strongest form of the criterion: no patching of the
        repository classes at all, only the ``deny_network`` autouse guard,
        which doubles as the proof of Requirement 11.3 — the four repository
        constructors merely build a ``StrapiClient`` and fix its
        ``content_type``, so no traffic is emitted and the guard never fires.
        """
        use_case = FacebookExportAssetsPostLaunchCampaignUseCase("user-1")

        assert use_case.user_id == "user-1"
        assert hasattr(use_case, "brand_repository") is False

    def test_brand_repository_attribute_is_undefined(self, use_case_factory):
        """Requirement 11.1: the attribute is **removed**, not set to ``None``.

        ``hasattr`` covers both the instance and the class, so a leftover class
        level ``brand_repository = None`` would also fail here.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert hasattr(use_case, "brand_repository") is False
        assert "brand_repository" not in vars(use_case)

    def test_vars_holds_exactly_the_five_expected_attributes(self, use_case_factory):
        """Requirement 11.2: exactly five instance attributes, no more."""
        use_case, _, _, _, _ = use_case_factory()

        assert set(vars(use_case)) == _EXPECTED_INSTANCE_ATTRIBUTES

    def test_the_four_repository_attributes_hold_the_test_doubles(self, use_case_factory):
        """Requirement 11.2: each of the four repositories is instantiated once
        and stored in its own attribute, and the factory hands back exactly
        those four instances.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()

        assert use_case.account_repository is mock_account_repo
        assert use_case.campaign_repository is mock_campaign_repo
        assert use_case.ad_channel_repository is mock_ad_channel_repo
        assert use_case.campaign_channel_publish_repository is mock_campaign_publish_repo

    def test_construction_invokes_nothing_on_the_four_repositories(self, use_case_factory):
        """Requirement 11.3: zero Strapi queries during construction.

        No method is called on any of the four doubles, so ``mock_calls`` is
        empty for all of them — a constructor that eagerly fetched the account,
        the campaign or the campaign setup would record something here.
        """
        (
            _,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()

        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []

    def test_construction_touches_neither_redis_nor_the_network(self, use_case_factory):
        """Requirements 11.3 and 12.2: zero Redis accesses and zero HTTP
        requests, with the Redis client and the download function replaced in
        the namespace from which the Caso_de_Uso resolves them.

        Both doubles are active **while** the use case is being built, so an
        ``__init__`` that resolved the Meta access token or downloaded anything
        would be caught here rather than in a later ``execute()`` scenario.
        """
        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                use_case, _, _, _, _ = use_case_factory()

        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0
        assert set(vars(use_case)) == _EXPECTED_INSTANCE_ATTRIBUTES

    @pytest.mark.parametrize(
        "user_id", [None, ""], ids=["none", "empty_string"]
    )
    def test_falsy_user_id_is_stored_verbatim_without_validation(
        self, use_case_factory, user_id
    ):
        """Requirement 11.6: ``__init__`` does not validate ``user_id``.

        A ``None`` or empty ``user_id`` is stored as received and surfaces later
        as ``NotAccessException`` from ``_get_decoded_access_token()``
        (Requirement 3.2), never as a construction-time failure.
        """
        use_case, _, _, _, _ = use_case_factory(user_id=user_id)

        assert use_case.user_id is user_id
        assert set(vars(use_case)) == _EXPECTED_INSTANCE_ATTRIBUTES
        assert hasattr(use_case, "brand_repository") is False


# ---------------------------------------------------------------------------
# Payload validation (Requirements 2.2, 2.3)
# ---------------------------------------------------------------------------


_REQUIRED_PAYLOAD_KEYS = ("campaign_id", "brand_id", "ad_id", "adset_id", "adchannel_id")

_INVALID_VALUES = [
    (ABSENT, "absent"),
    (None, "none"),
    ("", "empty_string"),
]

# The full ``clave x tipo de invalidez`` matrix of Requirement 2.3: five keys
# times three ways of being invalid, built as explicit pairs so the parametrize
# ids name both halves of every case.
_INVALID_KEY_MATRIX = [
    pytest.param(key, value, id="{}__{}".format(key, value_id))
    for key in _REQUIRED_PAYLOAD_KEYS
    for value, value_id in _INVALID_VALUES
]


class TestPayloadValidation:
    """Characterization of ``_validate_payload``, invoked **directly**
    (Requirements 2.2, 2.3).

    ``_validate_payload`` is the first operation of ``execute()`` and the only
    gate that runs before any network access, so it is pinned here in
    isolation: every case builds the use case through ``use_case_factory`` and
    calls the method itself, without going through ``execute()``. The
    orchestration-level consequences (that it runs *first*, that the five values
    travel on unconverted) belong to the ``execute()`` suites.

    Two families of cases:

    * the rejecting matrix — ``payload`` not a ``dict``, and each of the five
      required keys absent (via the ``ABSENT`` sentinel), present with ``None``,
      or present with ``''`` — all raising ``ParametersNotFoundException`` after
      a ``logger.error`` that names the offending keys, and all leaving the four
      repository doubles and the download double untouched;
    * the accepting cases — a valid payload, including one carrying extra keys,
      which must be ignored rather than rejected (Requirement 2.2).

    Requirements: 2.2, 2.3
    """

    def test_required_keys_are_exactly_the_five_of_the_contract(self):
        """Requirement 2.2: the Caso_de_Uso reads exactly those five keys.

        Pinned against a literal tuple declared in this module rather than
        against the class attribute itself, so a change of the contract has to
        be made deliberately in both places.
        """
        assert (
            FacebookExportAssetsPostLaunchCampaignUseCase._REQUIRED_PAYLOAD_KEYS
            == _REQUIRED_PAYLOAD_KEYS
        )

    @pytest.mark.parametrize("key,invalid_value", _INVALID_KEY_MATRIX)
    def test_invalid_key_raises_parameters_not_found(
        self, use_case_factory, key, invalid_value
    ):
        """Requirement 2.3, rejecting half of the matrix: for each of the five
        keys, absence, ``None`` and ``''`` all raise
        ``ParametersNotFoundException``.

        Only the exception **type** is asserted, never the message text.
        """
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(**{key: invalid_value})

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case._validate_payload(payload)

        assert_exception_type(exc_info, ParametersNotFoundException)

    @pytest.mark.parametrize("key,invalid_value", _INVALID_KEY_MATRIX)
    def test_invalid_key_is_named_in_the_logged_error(
        self, use_case_factory, key, invalid_value
    ):
        """Requirement 2.3: ``logger.error`` names the absent or invalid key."""
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(**{key: invalid_value})

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(ParametersNotFoundException):
                use_case._validate_payload(payload)

        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        assert key in logged

    def test_every_invalid_key_is_named_when_several_are_invalid(self, use_case_factory):
        """Requirement 2.3: the log names **each** offending key, not just the
        first one found, so a caller can fix them all in one round trip.

        The three invalidity types are mixed in a single payload on purpose.
        """
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(campaign_id=ABSENT, ad_id=None, adchannel_id="")

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(ParametersNotFoundException) as exc_info:
                use_case._validate_payload(payload)

        assert_exception_type(exc_info, ParametersNotFoundException)
        logged = mock_logger.error.call_args[0][0]
        for key in ["campaign_id", "ad_id", "adchannel_id"]:
            assert key in logged

    def test_all_five_keys_missing_raises_and_names_all_of_them(self, use_case_factory):
        """Requirement 2.3, the extreme case: an empty ``dict`` is a ``dict``,
        yet all five keys are absent.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(ParametersNotFoundException) as exc_info:
                use_case._validate_payload({})

        assert_exception_type(exc_info, ParametersNotFoundException)
        logged = mock_logger.error.call_args[0][0]
        for key in _REQUIRED_PAYLOAD_KEYS:
            assert key in logged

    @pytest.mark.parametrize(
        "payload",
        [
            None,
            [],
            ["campaign_id"],
            (),
            "campaign_id=101",
            0,
            101,
            1.5,
            True,
            {"campaign_id", "brand_id", "ad_id", "adset_id", "adchannel_id"},
        ],
        ids=[
            "none",
            "empty_list",
            "list_of_keys",
            "empty_tuple",
            "string",
            "zero",
            "int",
            "float",
            "bool",
            "set_of_key_names",
        ],
    )
    def test_non_dict_payload_raises_parameters_not_found(
        self, use_case_factory, payload
    ):
        """Requirement 2.3: a ``payload`` that is not a ``dict`` is rejected
        before any key is looked at.

        The ``set`` case matters: it holds the five key names and supports the
        ``in`` operator, so an implementation checking membership without first
        checking the type would wrongly accept it.
        """
        use_case, _, _, _, _ = use_case_factory()

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case._validate_payload(payload)

        assert_exception_type(exc_info, ParametersNotFoundException)

    def test_non_dict_payload_logs_an_error(self, use_case_factory):
        """Requirement 2.3: the non-``dict`` branch logs too, exactly once."""
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(ParametersNotFoundException):
                use_case._validate_payload(None)

        assert mock_logger.error.call_count == 1

    def test_rejection_touches_no_repository_no_redis_and_no_download(
        self, use_case_factory
    ):
        """Requirement 2.3: rejection happens with zero Strapi queries, zero
        Redis accesses and zero binary downloads.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()

        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                with pytest.raises(ParametersNotFoundException):
                    use_case._validate_payload(make_export_payload(brand_id=None))

        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []
        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0

    def test_valid_payload_returns_none_without_raising(self, use_case_factory):
        """Requirement 2.3, accepting half: the five keys present and usable, so
        the method returns ``None`` and raises nothing.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._validate_payload(make_export_payload()) is None

    def test_valid_payload_logs_no_error(self, use_case_factory):
        """The happy path is silent: no ``logger.error`` at all."""
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            use_case._validate_payload(make_export_payload())

        assert mock_logger.error.call_count == 0

    def test_extra_keys_are_ignored_and_do_not_raise(self, use_case_factory):
        """Requirement 2.2: any key beyond the five is ignored without altering
        the flow — not rejected, and not required to be usable either.

        The extra keys deliberately carry the very values that would be invalid
        on a required key (``None`` and ``''``), plus a name shadowing a
        neighbouring concept (``user_id``, which Requirement 2.6 says must come
        from the constructor).
        """
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(
            user_id="someone-else@example.test",
            unexpected_none=None,
            unexpected_empty="",
            unexpected_nested={"deep": ["value"]},
        )

        assert use_case._validate_payload(payload) is None

    def test_extra_keys_do_not_prevent_detecting_an_invalid_required_key(
        self, use_case_factory
    ):
        """Requirement 2.2 combined with 2.3: extra keys are ignored, they do not
        compensate for a missing required one.
        """
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(
            campaign_id=ABSENT, campaignId=101, campaign="101"
        )

        with pytest.raises(ParametersNotFoundException) as exc_info:
            use_case._validate_payload(payload)

        assert_exception_type(exc_info, ParametersNotFoundException)

    @pytest.mark.parametrize(
        "value",
        [0, False, 0.0, " ", "0", [], {}],
        ids=["zero", "false", "zero_float", "whitespace", "string_zero", "empty_list", "empty_dict"],
    )
    def test_falsy_but_neither_none_nor_empty_string_is_accepted(
        self, use_case_factory, value
    ):
        """Requirement 2.3 draws the line at ``None`` and ``''`` only.

        Every other falsy value — ``0``, ``False``, an empty collection, a
        whitespace-only string — is left alone: the Caso_de_Uso must not widen
        the rejection to plain truthiness, and must not normalize or convert the
        value either.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._validate_payload(make_export_payload(adset_id=value)) is None

    def test_payload_is_not_mutated_by_validation(self, use_case_factory):
        """Validation is read-only: no key is added, removed or normalized, which
        is what lets ``execute()`` read the five values afterwards exactly as
        they arrived.
        """
        use_case, _, _, _, _ = use_case_factory()
        payload = make_export_payload(extra_key="untouched")
        snapshot = dict(payload)

        use_case._validate_payload(payload)

        assert payload == snapshot

# ---------------------------------------------------------------------------
# Campaign resolution (Requirements 4.1 - 4.6)
# ---------------------------------------------------------------------------


class _RecordingDict(dict):
    """A ``dict`` that records every key read attempted on it.

    Used to prove Requirement 4.6 by construction: the Caso_de_Uso may check
    that the campaign record is a non-empty ``dict`` (which goes through
    ``isinstance`` and ``__len__``/``__bool__``, never through a key read) but
    must not read a single one of its attributes. Any ``campaign['x']``,
    ``campaign.get('x')`` or ``'x' in campaign`` performed by the
    implementation lands in ``reads`` and fails the assertion.

    Requirements: 4.6
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reads = []

    def __getitem__(self, key):
        self.reads.append(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.reads.append(key)
        return super().get(key, default)

    def __contains__(self, key):
        self.reads.append(key)
        return super().__contains__(key)


# The three failure conditions of Requirement 4.2, as returned by the
# repository double: ``None``, a value that is not a ``dict`` instance, and a
# ``dict`` with zero keys.
_UNRESOLVED_CAMPAIGN_VALUES = [
    pytest.param(None, id="none"),
    pytest.param([], id="empty_list"),
    pytest.param([{"id": 101}], id="list_of_records"),
    pytest.param({"id": 101}.items(), id="dict_items_view"),
    pytest.param("", id="empty_string"),
    pytest.param("101", id="string"),
    pytest.param(0, id="zero"),
    pytest.param(101, id="int"),
    pytest.param(False, id="false"),
    pytest.param({"id", "attributes"}, id="set_of_key_names"),
    pytest.param({}, id="empty_dict"),
]

# The three canonical conditions whose ``DataNotFoundException`` must be
# indistinguishable from one another (Requirement 4.5): a ``campaign_id``
# matching no campaign, a campaign whose brand differs, and a campaign whose
# account differs. From the Caso_de_Uso's viewpoint the repository answers all
# three the same way, which is exactly the point (see OQ-6, CONFIRMED); the
# three returned values below are the three shapes of "not resolved".
_INDISTINGUISHABLE_CONDITIONS = [
    ("unknown_campaign_id", None),
    ("brand_mismatch", []),
    ("account_mismatch", {}),
]


class TestCampaignResolution:
    """Characterization of ``_get_campaign``, invoked **directly**
    (Requirements 4.1 - 4.6).

    Four families of cases:

    * the single repository invocation, with the three arguments travelling
      positionally and **verbatim** from the Payload_de_Exportación and the
      Cuenta_Padre, with no ``int()``, ``str()`` or ``strip()`` on the way
      (Requirements 4.1, 4.3);
    * the three unresolved outcomes — ``None``, a non-``dict`` and an empty
      ``dict`` — each raising ``DataNotFoundException`` after a
      ``logger.error`` that names the three values used, and all three
      carrying a message indistinguishable from the others
      (Requirements 4.2, 4.5);
    * propagation of a repository failure without substitution, preserving the
      original exception instance, its type, its message and its traceback,
      and without retrying the query (Requirement 4.4);
    * a degenerate campaign record ``{'id': 1}``, which resolves successfully
      precisely because no attribute of it is ever read (Requirement 4.6).

    Note on Requirement 4.5: the message check compares the three messages
    against **each other**, never against a literal, so the human-facing text
    stays free to change as long as it stays uniform across the three
    conditions.

    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
    """

    # -- Requirement 4.1 / 4.3: the single, verbatim repository invocation ---

    def test_repository_is_invoked_once_with_the_three_positional_arguments(
        self, use_case_factory
    ):
        """Requirement 4.1: exactly one call to
        ``get_by_id_brand_and_account(campaign_id, brand_id, parent_account)``.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        payload = make_export_payload()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()

        use_case._get_campaign(payload["campaign_id"], payload["brand_id"], 42)

        mock_campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            payload["campaign_id"], payload["brand_id"], 42
        )

    @pytest.mark.parametrize(
        "campaign_id,brand_id,parent_account",
        [
            pytest.param(101, 7, 42, id="ints"),
            pytest.param("101", "7", "42", id="strings"),
            pytest.param(" 101 ", " 7 ", " 42 ", id="strings_with_whitespace"),
            pytest.param("0101", "007", "0042", id="strings_with_leading_zeros"),
            pytest.param(0, 0, 0, id="zeros"),
            pytest.param(101, "7", 42, id="mixed"),
        ],
    )
    def test_the_three_arguments_travel_without_type_conversion(
        self, use_case_factory, campaign_id, brand_id, parent_account
    ):
        """Requirements 2.5 and 4.1: the values reach the repository exactly as
        they arrived — no ``int()``, no ``str()``, no ``strip()``, no dropping
        of leading zeros.

        ``assert_called_once_with`` alone would not catch a ``str``/``int``
        conversion for the numeric cases (``'101' == 101`` is ``False``, but
        ``0 == False`` is ``True``), so the recorded arguments are also checked
        for their exact type and, when applicable, for object identity.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()

        use_case._get_campaign(campaign_id, brand_id, parent_account)

        mock_campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            campaign_id, brand_id, parent_account
        )
        recorded_args, recorded_kwargs = (
            mock_campaign_repo.get_by_id_brand_and_account.call_args
        )
        assert recorded_kwargs == {}
        assert [type(value) for value in recorded_args] == [
            type(campaign_id),
            type(brand_id),
            type(parent_account),
        ]

    def test_the_three_arguments_are_the_very_objects_received(self, use_case_factory):
        """Requirement 4.1 in its strongest form: identity, not equality.

        Three unique sentinel objects are passed in and the very same three
        objects must be handed to the repository, in that order, positionally.
        A defensive copy, a normalization or a reordering all break this.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()
        campaign_id = object()
        brand_id = object()
        parent_account = object()

        use_case._get_campaign(campaign_id, brand_id, parent_account)

        recorded_args, recorded_kwargs = (
            mock_campaign_repo.get_by_id_brand_and_account.call_args
        )
        assert recorded_kwargs == {}
        assert len(recorded_args) == 3
        assert recorded_args[0] is campaign_id
        assert recorded_args[1] is brand_id
        assert recorded_args[2] is parent_account

    def test_resolution_uses_the_constructor_repository_only(self, use_case_factory):
        """Requirement 4.3: the query goes through ``self.campaign_repository``
        and no other repository is touched, so a single Strapi read to
        ``campaigns`` happens per invocation.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()

        use_case._get_campaign(101, 7, 42)

        assert mock_campaign_repo.get_by_id_brand_and_account.call_count == 1
        assert len(mock_campaign_repo.mock_calls) == 1
        assert mock_account_repo.mock_calls == []
        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []

    def test_resolution_touches_neither_redis_nor_the_network(self, use_case_factory):
        """The campaign check is a single Strapi read: zero Redis accesses and
        zero binary downloads.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()

        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                use_case._get_campaign(101, 7, 42)

        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 4.2: the three unresolved outcomes ---------------------

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_CAMPAIGN_VALUES)
    def test_unresolved_campaign_raises_data_not_found(
        self, use_case_factory, returned_value
    ):
        """Requirement 4.2: ``None``, any non-``dict`` value and an empty
        ``dict`` all mean "not resolved".

        The ``set`` and ``dict_items`` cases matter for the same reason as in
        the payload suite: they are iterable and support ``in``, so an
        implementation checking truthiness or membership without first checking
        ``isinstance(..., dict)`` would wrongly accept them.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = returned_value

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_campaign(101, 7, 42)

        assert_exception_type(exc_info, DataNotFoundException)

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_CAMPAIGN_VALUES)
    def test_unresolved_campaign_logs_the_three_values_used(
        self, use_case_factory, returned_value
    ):
        """Requirement 4.2: ``logger.error`` names the ``campaign_id``, the
        ``brand_id`` and the Cuenta_Padre used, so the operator can reproduce
        the query even though the caller gets an opaque message.

        The three values are deliberately unlikely digit strings, so finding
        them in the logged line cannot be a coincidence.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = returned_value

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(DataNotFoundException):
                use_case._get_campaign(918273, 645342, 110099)

        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        for value in ["918273", "645342", "110099"]:
            assert value in logged

    def test_unresolved_campaign_does_not_retry_the_query(self, use_case_factory):
        """Requirement 4.1: still exactly one invocation on the failing path —
        no retry loop, no second lookup without the brand or account filter.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = None

        with pytest.raises(DataNotFoundException):
            use_case._get_campaign(101, 7, 42)

        mock_campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            101, 7, 42
        )

    def test_unresolved_campaign_stops_before_any_other_repository(
        self, use_case_factory
    ):
        """Requirement 4.2: the Ad_Channel_de_Exportación and the
        Campaign_Setup are not resolved, and nothing is downloaded.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = {}

        with patch_image_download() as mock_requests_get:
            with pytest.raises(DataNotFoundException):
                use_case._get_campaign(101, 7, 42)

        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []
        assert mock_account_repo.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 4.5: the three messages are indistinguishable ----------

    def test_the_three_failure_conditions_raise_an_identical_exception(
        self, use_case_factory
    ):
        """Requirement 4.5: unknown campaign, brand mismatch and account
        mismatch are indistinguishable to the caller.

        The three raised exceptions are compared **against each other** — same
        exact type, same ``str()``, same ``text`` and same ``code`` — and never
        against a hard-coded literal, so the wording remains free to change as
        long as it stays uniform. A leak such as "campaign belongs to another
        brand" would break the equality.
        """
        raised = {}
        for condition, returned_value in _INDISTINGUISHABLE_CONDITIONS:
            use_case, _, mock_campaign_repo, _, _ = use_case_factory()
            mock_campaign_repo.get_by_id_brand_and_account.return_value = returned_value

            with pytest.raises(DataNotFoundException) as exc_info:
                use_case._get_campaign(101, 7, 42)

            assert_exception_type(exc_info, DataNotFoundException)
            raised[condition] = exc_info.value

        messages = {str(exception) for exception in raised.values()}
        texts = {exception.text for exception in raised.values()}
        codes = {exception.code for exception in raised.values()}
        types = {type(exception) for exception in raised.values()}

        assert len(messages) == 1, (
            "the three failure conditions must be indistinguishable, got "
            "{!r}".format({name: str(exc) for name, exc in raised.items()})
        )
        assert len(texts) == 1
        assert len(codes) == 1
        assert len(types) == 1

    def test_the_indistinguishable_message_leaks_none_of_the_query_values(
        self, use_case_factory
    ):
        """Requirement 4.5, complementary angle: the opaque message must not
        become distinguishable through the values it interpolates either.

        The ``campaign_id``, ``brand_id`` and Cuenta_Padre belong in the server
        log (checked above), not in the text handed back to the caller.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = None

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_campaign(918273, 645342, 110099)

        message = str(exc_info.value)
        for value in ["918273", "645342", "110099"]:
            assert value not in message

    # -- Requirement 4.4: propagation without substitution ------------------

    @pytest.mark.parametrize(
        "injected",
        [
            requests.exceptions.HTTPError("500 Server Error"),
            requests.exceptions.ConnectionError("connection reset by peer"),
            requests.exceptions.Timeout("read timed out"),
            ValueError("unexpected payload shape"),
            KeyError("data"),
            RuntimeError("boom"),
        ],
        ids=[
            "http_error",
            "connection_error",
            "timeout",
            "value_error",
            "key_error",
            "runtime_error",
        ],
    )
    def test_repository_exception_is_propagated_unchanged(
        self, use_case_factory, injected
    ):
        """Requirement 4.4: an exception raised by the repository reaches the
        caller as-is.

        ``pytest.raises`` is given the injected exception's own class, so a
        substitution by ``DataNotFoundException`` fails the test outright; and
        the captured value is asserted to be the **same instance**, which is
        what a bare ``raise`` guarantees and what ``raise e`` — or worse,
        ``raise DataNotFoundException(...)`` — would not.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.side_effect = injected

        with pytest.raises(type(injected)) as exc_info:
            use_case._get_campaign(101, 7, 42)

        assert exc_info.value is injected
        assert type(exc_info.value) is type(injected)
        assert str(exc_info.value) == str(injected)
        assert exc_info.value.__traceback__ is not None

    def test_repository_exception_is_not_converted_to_data_not_found(
        self, use_case_factory
    ):
        """Requirement 4.4, stated the other way round: a transport failure is
        **not** reported as "campaign not found".

        The distinction matters operationally — a 500 from Strapi and a
        campaign that does not belong to the account call for entirely
        different responses.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        injected = requests.exceptions.HTTPError("500 Server Error")
        mock_campaign_repo.get_by_id_brand_and_account.side_effect = injected

        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            use_case._get_campaign(101, 7, 42)

        assert not isinstance(exc_info.value, DataNotFoundException)
        assert exc_info.value is injected

    def test_repository_exception_is_logged_and_the_query_is_not_repeated(
        self, use_case_factory
    ):
        """Requirement 4.4: the failure is logged with ``logger.error`` and the
        query is issued exactly once — no retry after the exception.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.side_effect = (
            requests.exceptions.HTTPError("500 Server Error")
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(requests.exceptions.HTTPError):
                use_case._get_campaign(101, 7, 42)

        assert mock_logger.error.call_count == 1
        mock_campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            101, 7, 42
        )

    def test_repository_exception_stops_before_the_ad_channel_resolution(
        self, use_case_factory
    ):
        """Requirement 4.4: propagation ends the flow, so the
        Ad_Channel_de_Exportación is never resolved and nothing is downloaded.
        """
        (
            use_case,
            _,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.side_effect = RuntimeError("boom")

        with patch_image_download() as mock_requests_get:
            with pytest.raises(RuntimeError):
                use_case._get_campaign(101, 7, 42)

        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 4.6: existence check only, no attribute read -----------

    def test_degenerate_campaign_record_resolves(self, use_case_factory):
        """Requirement 4.6: ``{'id': 1}`` is enough.

        A record with a single key and no ``attributes`` at all resolves
        successfully, which is only possible if the Caso_de_Uso treats the
        return value as a mere existence-and-ownership check.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        degenerate = {"id": 1}
        mock_campaign_repo.get_by_id_brand_and_account.return_value = degenerate

        resolved = use_case._get_campaign(101, 7, 42)

        assert resolved is degenerate

    def test_degenerate_campaign_record_resolves_without_reading_any_key(
        self, use_case_factory
    ):
        """Requirement 4.6: not one key of the record is read.

        The recording ``dict`` reports every ``[]``, ``.get()`` and ``in``
        performed on it. The expected report is the empty list: checking
        ``isinstance`` and emptiness needs no key access.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        degenerate = _RecordingDict({"id": 1})
        mock_campaign_repo.get_by_id_brand_and_account.return_value = degenerate

        resolved = use_case._get_campaign(101, 7, 42)

        assert resolved is degenerate
        assert degenerate.reads == []

    def test_a_record_whose_only_key_is_not_id_also_resolves(self, use_case_factory):
        """Requirement 4.6: "a ``dict`` with at least one key" is the whole
        criterion — the name of that key is irrelevant, so not even ``id`` is
        looked for.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        unusual = _RecordingDict({"unexpected_key": None})
        mock_campaign_repo.get_by_id_brand_and_account.return_value = unusual

        resolved = use_case._get_campaign(101, 7, 42)

        assert resolved is unusual
        assert unusual.reads == []

    def test_resolution_logs_no_error_on_the_happy_path(self, use_case_factory):
        """The successful path is silent: no ``logger.error`` at all."""
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        mock_campaign_repo.get_by_id_brand_and_account.return_value = make_campaign()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            use_case._get_campaign(101, 7, 42)

        assert mock_logger.error.call_count == 0

    def test_the_resolved_record_is_returned_unmodified(self, use_case_factory):
        """Requirement 4.6: the record is neither mutated nor copied.

        The builder-made campaign is compared against a pristine snapshot, and
        identity is asserted too, so a normalization step would be caught.
        """
        use_case, _, mock_campaign_repo, _, _ = use_case_factory()
        campaign = make_campaign()
        snapshot = dict(campaign)
        mock_campaign_repo.get_by_id_brand_and_account.return_value = campaign

        resolved = use_case._get_campaign(101, 7, 42)

        assert resolved is campaign
        assert campaign == snapshot

# ---------------------------------------------------------------------------
# Ad channel resolution and Channel_ID reading (Requirements 5.1 - 5.5)
# ---------------------------------------------------------------------------


# The unresolved outcomes of Requirement 5.2: ``None`` and "any value evaluated
# as false", of which the empty ``dict`` is the example the criterion names.
# Unlike the campaign of Requirement 4.2, here the criterion is truthiness, so
# a non-empty non-``dict`` value (a list of records, a string) is *not* a
# failure and is covered by the accepting cases below instead.
_UNRESOLVED_AD_CHANNEL_VALUES = [
    pytest.param(None, id="none"),
    pytest.param({}, id="empty_dict"),
    pytest.param([], id="empty_list"),
    pytest.param("", id="empty_string"),
    pytest.param(0, id="zero"),
    pytest.param(False, id="false"),
    pytest.param(0.0, id="zero_float"),
    pytest.param(set(), id="empty_set"),
]


# Values that are not ``dict`` instances, used to fill each intermediate level
# of the ``attributes.channel_ref.data`` path (Requirement 5.5). ``True`` and
# ``1`` are here on purpose: an implementation reading the path with a chain of
# ``or {}`` fallbacks instead of an ``isinstance`` check would try ``.get`` on
# them and raise ``AttributeError``.
_NON_DICT_NODE_VALUES = [
    pytest.param(None, id="none"),
    pytest.param([], id="empty_list"),
    pytest.param([{"id": 9}], id="list_of_records"),
    pytest.param("", id="empty_string"),
    pytest.param("9", id="string"),
    pytest.param(0, id="zero"),
    pytest.param(9, id="int"),
    pytest.param(False, id="false"),
    pytest.param(True, id="true"),
    pytest.param(1.5, id="float"),
    pytest.param({"id"}, id="set_of_key_names"),
    pytest.param((), id="empty_tuple"),
]

_NESTED_LEVELS = ["attributes", "channel_ref", "data"]


def _ad_channel_without_attributes():
    """Level 1 of the Requirement 5.5 matrix: no ``attributes`` key at all."""
    return make_ad_channel(attributes=ABSENT)


def _ad_channel_without_channel_ref():
    """Level 2: ``attributes`` present, ``channel_ref`` absent."""
    ad_channel = make_ad_channel()
    del ad_channel["attributes"]["channel_ref"]
    return ad_channel


def _ad_channel_without_data():
    """Level 3: ``channel_ref`` present, ``data`` absent."""
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["channel_ref"] = {}
    return ad_channel


def _ad_channel_without_id():
    """Level 4: the whole path present, the innermost ``id`` absent."""
    return make_ad_channel(channel_ref_id=ABSENT)


_ABSENT_LEVEL_BUILDERS = [
    pytest.param(_ad_channel_without_attributes, id="attributes_absent"),
    pytest.param(_ad_channel_without_channel_ref, id="channel_ref_absent"),
    pytest.param(_ad_channel_without_data, id="data_absent"),
    pytest.param(_ad_channel_without_id, id="id_absent"),
]


def _ad_channel_with_non_dict_level(level, value):
    """Return an Ad_Channel_de_Exportación whose ``level`` node holds ``value``,
    a value that is not a ``dict`` instance.
    """
    ad_channel = make_ad_channel()
    if level == "attributes":
        ad_channel["attributes"] = value
    elif level == "channel_ref":
        ad_channel["attributes"]["channel_ref"] = value
    elif level == "data":
        ad_channel["attributes"]["channel_ref"]["data"] = value
    else:  # pragma: no cover - guards against a typo in the parametrization
        raise AssertionError("unknown nesting level {!r}".format(level))
    return ad_channel


class TestAdChannelResolution:
    """Characterization of ``_get_ad_channel``, invoked **directly**
    (Requirements 5.1, 5.2, 5.4).

    Three families of cases:

    * the single repository invocation, with the **four** identifiers
      travelling positionally and verbatim — ``campaign_id``, ``adset_id``,
      ``ad_id``, ``adchannel_id``, in that order, which is *not* the order in
      which they are declared in the payload builder and is therefore the
      easiest thing to get wrong here (Requirement 5.1);
    * every falsy returned value raising ``DataNotFoundException`` after a
      ``logger.error`` naming the four identifiers consulted, with no retry
      and without touching the Campaign_Setup repository, which is the
      Requirement 5.6 short-circuit seen from this method (Requirement 5.2);
    * a truthy returned value handed back untouched, by identity, so the
      Channel_ID can be read from that very record (Requirement 5.3).

    Requirements: 5.1, 5.2, 5.4
    """

    # -- Requirement 5.1: the single, verbatim, four-argument invocation ----

    def test_repository_is_invoked_once_with_the_four_positional_arguments(
        self, use_case_factory
    ):
        """Requirement 5.1: exactly one call to
        ``get_by_campaign_and_ad_channel_id(campaign_id, adset_id, ad_id,
        adchannel_id)``.

        The four values come from the Payload_de_Exportación and are
        deliberately all different, so a swapped ``adset_id``/``ad_id`` pair —
        the most likely mistake, since the payload declares ``ad_id`` first in
        Requirement 2.2 while this call takes ``adset_id`` first — fails the
        assertion.

        Requirement 5.7 adds the name-population flag to that very call, as a
        **keyword** argument: the four identifiers keep travelling
        positionally, so the flag cannot be mistaken for a fifth identifier.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        payload = make_export_payload()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        use_case._get_ad_channel(
            payload["campaign_id"],
            payload["adset_id"],
            payload["ad_id"],
            payload["adchannel_id"],
        )

        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.assert_called_once_with(
            101, 202, 303, 404, populate_names=True
        )
        recorded_args, recorded_kwargs = (
            mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_args
        )
        assert len(recorded_args) == 4
        assert recorded_kwargs == {"populate_names": True}

    @pytest.mark.parametrize(
        "campaign_id,adset_id,ad_id,adchannel_id",
        [
            pytest.param(101, 202, 303, 404, id="ints"),
            pytest.param("101", "202", "303", "404", id="strings"),
            pytest.param(" 101 ", " 202 ", " 303 ", " 404 ", id="strings_with_whitespace"),
            pytest.param("0101", "0202", "0303", "0404", id="strings_with_leading_zeros"),
            pytest.param(0, 0, 0, 0, id="zeros"),
            pytest.param(101, "202", 303, "404", id="mixed"),
        ],
    )
    def test_the_four_arguments_travel_without_type_conversion(
        self, use_case_factory, campaign_id, adset_id, ad_id, adchannel_id
    ):
        """Requirement 5.1: the four identifiers are passed on without being
        transformed or normalised — no ``int()``, no ``str()``, no ``strip()``,
        no dropping of leading zeros.

        As in the campaign suite, ``assert_called_once_with`` alone would let a
        ``0``/``False`` confusion through, so the recorded arguments are checked
        for their exact type too.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        use_case._get_ad_channel(campaign_id, adset_id, ad_id, adchannel_id)

        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.assert_called_once_with(
            campaign_id, adset_id, ad_id, adchannel_id, populate_names=True
        )
        recorded_args, recorded_kwargs = (
            mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_args
        )
        # Requirement 5.7: the flag is the only keyword argument, and the four
        # identifiers remain the only positional ones.
        assert recorded_kwargs == {"populate_names": True}
        assert len(recorded_args) == 4
        assert [type(value) for value in recorded_args] == [
            type(campaign_id),
            type(adset_id),
            type(ad_id),
            type(adchannel_id),
        ]

    def test_the_four_arguments_are_the_very_objects_received(self, use_case_factory):
        """Requirement 5.1 in its strongest form: identity and order, not
        equality.

        Four unique sentinel objects go in and the very same four objects must
        reach the repository, in that order, positionally. A defensive copy, a
        normalization or a reordering all break this.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )
        campaign_id = object()
        adset_id = object()
        ad_id = object()
        adchannel_id = object()

        use_case._get_ad_channel(campaign_id, adset_id, ad_id, adchannel_id)

        recorded_args, recorded_kwargs = (
            mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_args
        )
        assert recorded_kwargs == {"populate_names": True}
        assert len(recorded_args) == 4
        assert recorded_args[0] is campaign_id
        assert recorded_args[1] is adset_id
        assert recorded_args[2] is ad_id
        assert recorded_args[3] is adchannel_id

    def test_resolution_uses_the_constructor_repository_only(self, use_case_factory):
        """Requirement 5.4: the query goes through ``self.ad_channel_repository``
        and no other repository is touched.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        use_case._get_ad_channel(101, 202, 303, 404)

        assert mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 1
        assert len(mock_ad_channel_repo.mock_calls) == 1
        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []

    def test_resolution_instantiates_no_new_ad_channel_repository(
        self, use_case_factory
    ):
        """Requirement 5.4: zero instantiations of ``AdChannelRepository``
        during the resolution itself.

        The class is patched again **after** the use case has been built, so
        the double records only what happens inside ``_get_ad_channel``: the
        expected count is zero, since the instance created by ``__init__`` is
        the one being reused.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls:
            use_case._get_ad_channel(101, 202, 303, 404)

        assert mock_ad_channel_repository_cls.call_count == 0
        assert mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 1

    def test_resolution_touches_neither_redis_nor_the_network(self, use_case_factory):
        """The creative lookup is a single Strapi read: zero Redis accesses and
        zero binary downloads.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                use_case._get_ad_channel(101, 202, 303, 404)

        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 5.2: every falsy value means "creative not found" ------

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_AD_CHANNEL_VALUES)
    def test_falsy_ad_channel_raises_data_not_found(
        self, use_case_factory, returned_value
    ):
        """Requirement 5.2: ``None`` and every other falsy value — the empty
        ``dict`` named by the criterion included — raise
        ``DataNotFoundException``.

        Only the exception type is asserted, never the message text.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            returned_value
        )

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_ad_channel(101, 202, 303, 404)

        assert_exception_type(exc_info, DataNotFoundException)

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_AD_CHANNEL_VALUES)
    def test_falsy_ad_channel_logs_the_four_identifiers_consulted(
        self, use_case_factory, returned_value
    ):
        """Requirement 5.2: ``logger.error`` reports the combination of the four
        identifiers, so the operator can reproduce the query.

        The four values are unlikely digit strings, so finding them in the
        logged line cannot be a coincidence.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            returned_value
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(DataNotFoundException):
                use_case._get_ad_channel(918273, 645342, 110099, 553311)

        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        for value in ["918273", "645342", "110099", "553311"]:
            assert value in logged

    def test_falsy_ad_channel_does_not_retry_the_query(self, use_case_factory):
        """Requirement 5.1: still exactly one invocation on the failing path —
        no retry loop and no second lookup with fewer filters.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = None

        with pytest.raises(DataNotFoundException):
            use_case._get_ad_channel(101, 202, 303, 404)

        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.assert_called_once_with(
            101, 202, 303, 404, populate_names=True
        )

    def test_falsy_ad_channel_stops_before_the_campaign_setup(self, use_case_factory):
        """Requirement 5.6: the failure ends the flow, so the Campaign_Setup is
        never resolved and nothing is downloaded.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = {}

        with patch_image_download() as mock_requests_get:
            with pytest.raises(DataNotFoundException):
                use_case._get_ad_channel(101, 202, 303, 404)

        assert mock_campaign_publish_repo.mock_calls == []
        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 5.2, accepting half -----------------------------------

    def test_truthy_ad_channel_is_returned_by_identity(self, use_case_factory):
        """Requirement 5.3 depends on this: the record reaches the caller as the
        very same object, unmodified, so the Channel_ID is read from it.
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        ad_channel = make_ad_channel()
        pristine = make_ad_channel()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = ad_channel

        resolved = use_case._get_ad_channel(101, 202, 303, 404)

        assert resolved is ad_channel
        assert ad_channel == pristine

    @pytest.mark.parametrize(
        "returned_value",
        [
            pytest.param({"id": 77}, id="degenerate_record"),
            pytest.param({"attributes": {}}, id="record_without_id"),
            pytest.param([{"id": 77}], id="non_empty_list"),
            pytest.param("77", id="non_empty_string"),
            pytest.param(77, id="non_zero_int"),
            pytest.param(True, id="true"),
        ],
    )
    def test_any_truthy_value_resolves(self, use_case_factory, returned_value):
        """Requirement 5.2 draws the line at truthiness only: a record without
        ``attributes``, and even a value that is not a ``dict``, resolves.

        This is deliberately laxer than the campaign check of Requirement 4.1
        (a ``dict`` with at least one key) and the Campaign_Setup check of
        Requirement 6.2 (falsy **or** non-``dict``). Pinning it here keeps the
        three from being unified by accident, and the degenerate shapes stay
        harmless because ``_resolve_channel_id`` defaults to ``0`` for all of
        them (Requirement 5.5).
        """
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            returned_value
        )

        assert use_case._get_ad_channel(101, 202, 303, 404) is returned_value

    def test_resolution_logs_no_error_on_the_happy_path(self, use_case_factory):
        """The successful path is silent: no ``logger.error`` at all."""
        use_case, _, _, mock_ad_channel_repo, _ = use_case_factory()
        mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel()
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            use_case._get_ad_channel(101, 202, 303, 404)

        assert mock_logger.error.call_count == 0


class TestChannelIdResolution:
    """Characterization of ``_resolve_channel_id``, invoked **directly**
    (Requirements 5.3, 5.4, 5.5).

    The method replicates the read pattern of
    ``FacebookSavePreCheckBaseUseCase._set_channel_id``:
    ``attributes.channel_ref.data.id`` with ``0`` as the default at every
    level. Two families of cases:

    * the complete path, whose value is returned as read and without
      conversion (Requirement 5.3);
    * the degraded shapes — the four absence levels (``attributes``,
      ``channel_ref``, ``data``, ``id``) and every intermediate level holding
      a value that is not a ``dict`` — all resolving to ``0`` **without
      raising**, so the failure surfaces later, when the Campaign_Setup is
      resolved with ``channel_id == 0`` (Requirement 5.5).

    The "no exception" half is the point of Requirement 5.5: an
    ``AttributeError`` or a ``TypeError`` escaping from here would reach the
    caller as a 500 instead of the intended ``DataNotFoundException`` of
    Requirement 6.2.

    Requirements: 5.3, 5.4, 5.5
    """

    # -- Requirement 5.3: the complete path -------------------------------

    def test_complete_path_yields_the_nested_id(self, use_case_factory):
        """Requirement 5.3: ``attributes.channel_ref.data.id`` is read."""
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._resolve_channel_id(make_ad_channel(channel_ref_id=1)) == 1

    @pytest.mark.parametrize(
        "channel_ref_id",
        [
            pytest.param(1, id="one"),
            pytest.param(55, id="fifty_five"),
            pytest.param(918273, id="large_int"),
            pytest.param(0, id="zero"),
        ],
    )
    def test_the_nested_id_is_returned_verbatim(self, use_case_factory, channel_ref_id):
        """Requirement 5.3: the value is returned as stored, with its exact type
        and no conversion.

        ``0`` is included on purpose: a stored ``0`` and the default ``0`` of
        Requirement 5.5 are indistinguishable by design, and both lead to the
        Campaign_Setup query being issued all the same (Requirement 6.1).
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(channel_ref_id=channel_ref_id)

        resolved = use_case._resolve_channel_id(ad_channel)

        assert resolved == channel_ref_id
        assert type(resolved) is type(channel_ref_id)

    def test_the_read_does_not_mutate_the_ad_channel(self, use_case_factory):
        """The read is read-only: no key is created by a ``setdefault``-style
        traversal, at any depth.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(channel_ref_id=55)
        pristine = make_ad_channel(channel_ref_id=55)

        use_case._resolve_channel_id(ad_channel)

        assert ad_channel == pristine

    def test_the_read_touches_no_repository_no_redis_and_no_network(
        self, use_case_factory
    ):
        """The Channel_ID comes from the record already in memory: zero Strapi
        queries, zero Redis accesses and zero downloads.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()

        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                assert use_case._resolve_channel_id(make_ad_channel(channel_ref_id=7)) == 7

        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_ad_channel_repo.mock_calls == []
        assert mock_campaign_publish_repo.mock_calls == []
        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0

    def test_the_read_instantiates_no_repository(self, use_case_factory):
        """Requirement 5.4: no repository is constructed while reading the
        Channel_ID either.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls:
            use_case._resolve_channel_id(make_ad_channel(channel_ref_id=7))

        assert mock_ad_channel_repository_cls.call_count == 0
        assert mock_campaign_publish_repository_cls.call_count == 0

    # -- Requirement 5.5: the four absence levels -------------------------

    @pytest.mark.parametrize("build_ad_channel", _ABSENT_LEVEL_BUILDERS)
    def test_absent_level_resolves_to_zero(self, use_case_factory, build_ad_channel):
        """Requirement 5.5, absence matrix: ``attributes``, ``channel_ref``,
        ``data`` or ``id`` missing all yield ``0``.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._resolve_channel_id(build_ad_channel()) == 0

    @pytest.mark.parametrize("build_ad_channel", _ABSENT_LEVEL_BUILDERS)
    def test_absent_level_raises_nothing_and_logs_no_error(
        self, use_case_factory, build_ad_channel
    ):
        """Requirement 5.5: the degraded read is silent and does not raise.

        The criterion is explicit that the failure must surface later, in the
        Campaign_Setup resolution, so this step neither raises nor reports an
        error of its own.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            assert use_case._resolve_channel_id(build_ad_channel()) == 0

        assert mock_logger.error.call_count == 0

    @pytest.mark.parametrize("level", _NESTED_LEVELS)
    @pytest.mark.parametrize("value", _NON_DICT_NODE_VALUES)
    def test_non_dict_intermediate_level_resolves_to_zero(
        self, use_case_factory, level, value
    ):
        """Requirement 5.5, non-``dict`` matrix: each of the three intermediate
        levels holding a value that is not a ``dict`` yields ``0``.

        The value being *present* is what makes this different from the absence
        matrix: a ``.get(key, {})`` chain returns the stored ``None`` rather
        than the ``{}`` default, so the very next ``.get`` raises unless the
        implementation checks ``isinstance(..., dict)`` at every step.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = _ad_channel_with_non_dict_level(level, value)

        assert use_case._resolve_channel_id(ad_channel) == 0

    @pytest.mark.parametrize("value", _NON_DICT_NODE_VALUES)
    def test_non_dict_ad_channel_itself_resolves_to_zero(self, use_case_factory, value):
        """Requirement 5.5 applied to the outermost node: the laxer acceptance
        of Requirement 5.2 lets a non-``dict`` record through, and the read
        must still answer ``0`` instead of raising.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._resolve_channel_id(value) == 0

    @pytest.mark.parametrize(
        "ad_channel",
        [
            pytest.param({}, id="empty_dict"),
            pytest.param({"id": 77}, id="record_without_attributes"),
            pytest.param({"attributes": {}}, id="empty_attributes"),
            pytest.param({"attributes": {"channel_ref": {}}}, id="empty_channel_ref"),
            pytest.param(
                {"attributes": {"channel_ref": {"data": {}}}}, id="empty_data"
            ),
            pytest.param(
                {"attributes": {"channel_ref": {"data": {"other": 9}}}},
                id="data_without_id",
            ),
        ],
    )
    def test_degenerate_shapes_resolve_to_zero(self, use_case_factory, ad_channel):
        """Requirement 5.5: the whole ladder of progressively emptier records
        resolves to ``0``, none of them raising.
        """
        use_case, _, _, _, _ = use_case_factory()

        assert use_case._resolve_channel_id(ad_channel) == 0

    def test_a_sibling_key_named_id_at_the_wrong_depth_is_not_read(
        self, use_case_factory
    ):
        """Requirement 5.3: the ``id`` read is the one at
        ``attributes.channel_ref.data``, not the record's own ``id`` nor any
        homonym at another depth.

        The record here carries an ``id`` at the top level, inside
        ``attributes`` and inside ``channel_ref``, none of which is the right
        one, so an implementation reading the wrong depth returns ``77``,
        ``88`` or ``99`` instead of ``0``.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = {
            "id": 77,
            "attributes": {"id": 88, "channel_ref": {"id": 99, "data": {}}},
        }

        assert use_case._resolve_channel_id(ad_channel) == 0

    def test_the_nested_id_wins_over_the_homonyms_at_other_depths(
        self, use_case_factory
    ):
        """Requirement 5.3, stated the other way round: with all four present,
        the innermost one is the Channel_ID.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = {
            "id": 77,
            "attributes": {"id": 88, "channel_ref": {"id": 99, "data": {"id": 55}}},
        }

        assert use_case._resolve_channel_id(ad_channel) == 55

# The rejection matrix of Requirement 6.2, as returned by the
# ``CampaignChannelPublishRepository`` double: every falsy value (the four
# named by the criterion included) **and** every value that is not a ``dict``
# instance, even when truthy.
_UNRESOLVED_CAMPAIGN_SETUP_VALUES = [
    pytest.param(None, id="none"),
    pytest.param({}, id="empty_dict"),
    pytest.param([], id="empty_list"),
    pytest.param(0, id="zero"),
    pytest.param("", id="empty_string"),
    pytest.param(False, id="false"),
    pytest.param([{"id": 55}], id="list_of_records"),
    pytest.param("55", id="string"),
    pytest.param(55, id="int"),
    pytest.param({"id", "attributes"}, id="set_of_key_names"),
    pytest.param({"id": 55}.items(), id="dict_items_view"),
]

# The rejection matrix of Requirement 6.4. ``meta_published`` is compared by
# identity against ``True``, so the truthy look-alikes ``1``, ``'True'`` and
# ``'true'`` are rejected exactly like the absent key, ``None`` and ``False``.
_REJECTED_META_PUBLISHED_VALUES = [
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param(False, id="false"),
    pytest.param(1, id="int_one"),
    pytest.param("True", id="string_True"),
    pytest.param("true", id="string_true"),
    pytest.param(0, id="int_zero"),
    pytest.param("", id="empty_string"),
    pytest.param("published", id="arbitrary_string"),
]

# The rejection matrix of Requirement 6.5. The comparison is case sensitive
# and performs no whitespace normalization, so ``'standard'`` and
# ``' STANDARD '`` are rejected; the enum **member** is rejected too, since
# ``CreativeType`` does not derive from ``str`` and only its ``.value`` is
# equal to ``'STANDARD'``.
_REJECTED_META_CAMPAIGN_MODE_VALUES = [
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param("", id="empty_string"),
    pytest.param("standard", id="lowercase"),
    pytest.param(" STANDARD ", id="surrounding_whitespace"),
    pytest.param("STANDARD\n", id="trailing_newline"),
    pytest.param("Standard", id="capitalized"),
    pytest.param(CreativeType.DYNAMIC.value, id="dynamic"),
    pytest.param(CreativeType.STANDARD, id="enum_member_instead_of_its_value"),
]

# The precedence matrix of Requirement 6.6: a Campaign_Setup that is *both*
# unpublished and in a non-STANDARD mode must raise exactly one exception, the
# publication one, and must not report the mode.
_BOTH_INVALID_COMBINATIONS = [
    pytest.param(False, CreativeType.DYNAMIC.value, id="false_and_dynamic"),
    pytest.param(None, CreativeType.DYNAMIC.value, id="none_and_dynamic"),
    pytest.param(ABSENT, CreativeType.DYNAMIC.value, id="absent_and_dynamic"),
    pytest.param(1, CreativeType.DYNAMIC.value, id="int_one_and_dynamic"),
    pytest.param("True", CreativeType.DYNAMIC.value, id="string_True_and_dynamic"),
    pytest.param(False, "", id="false_and_empty_mode"),
]


class TestCampaignSetupValidation:
    """Characterization of ``_get_validated_campaign_setup``, invoked
    **directly** (Requirements 6.1 - 6.7, 6.9).

    Four families of cases:

    * the single repository invocation, with ``campaign_id`` and the
      Channel_ID travelling positionally and verbatim, **including** the
      variant where the Channel_ID holds the default ``0`` of Requirements 5.3
      and 5.5 — the query is issued all the same, so the failure surfaces here
      as the ``DataNotFoundException`` of Requirement 6.2 instead of being
      silently skipped (Requirement 6.1);
    * the rejection of the resolved record: every falsy value and every
      non-``dict`` value, even truthy, reported with a ``logger.error`` naming
      the two identifiers consulted (Requirement 6.2);
    * the two value validations, publication first and mode second, each with
      its own rejection matrix: identity against ``True`` for the former
      (Requirement 6.4) and case-sensitive, whitespace-preserving equality
      against ``CreativeType.STANDARD.value`` for the latter
      (Requirement 6.5), plus the degraded read where ``attributes`` is absent
      and both values come back as ``None`` without raising
      ``AttributeError`` (Requirement 6.3);
    * the normative precedence between the two — an unpublished, ``DYNAMIC``
      setup raises exactly one exception, the publication one, and the mode
      check is not evaluated (Requirement 6.6) — and the happy path, which
      returns the record untouched without a single ``logger.error``
      (Requirement 6.9).

    Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.9
    """

    # -- Requirement 6.1: the single, verbatim, two-argument invocation -----

    def test_repository_is_invoked_once_with_the_two_positional_arguments(
        self, use_case_factory
    ):
        """Requirement 6.1: exactly one call to
        ``get_by_campaign_id_and_channel_id(campaign_id, channel_id)``, in that
        order.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_validated_campaign_setup(101, 55)

        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.assert_called_once_with(
            101, 55
        )

    def test_the_query_is_issued_as_well_when_channel_id_is_zero(
        self, use_case_factory
    ):
        """Requirement 6.1, the variant that is easiest to get wrong: a
        Channel_ID of ``0`` — the default assigned by Requirements 5.3 and 5.5
        when the nested path is degraded — must **not** short circuit the
        query.

        An implementation guarding the call with ``if channel_id:`` would skip
        Strapi entirely and raise its own error, so the recorded arguments are
        checked for their exact type too: a ``0`` silently turned into
        ``False`` or into ``None`` fails here.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_validated_campaign_setup(101, 0)

        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.assert_called_once_with(
            101, 0
        )
        recorded_args, recorded_kwargs = (
            mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_args
        )
        assert recorded_kwargs == {}
        assert recorded_args[1] == 0
        assert type(recorded_args[1]) is int

    def test_the_query_is_issued_with_channel_id_zero_even_when_the_record_is_missing(
        self, use_case_factory
    ):
        """Requirement 6.1 combined with 6.2: with ``channel_id == 0`` the
        query is still emitted and the missing record becomes
        ``DataNotFoundException``, which is the intended way for a degraded
        ``attributes.channel_ref.data.id`` to fail.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = None

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_validated_campaign_setup(101, 0)

        assert_exception_type(exc_info, DataNotFoundException)
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.assert_called_once_with(
            101, 0
        )

    @pytest.mark.parametrize(
        "campaign_id,channel_id",
        [
            pytest.param(101, 55, id="ints"),
            pytest.param("101", 55, id="string_campaign_id"),
            pytest.param(" 101 ", 55, id="campaign_id_with_whitespace"),
            pytest.param("0101", 55, id="campaign_id_with_leading_zeros"),
            pytest.param(0, 0, id="zeros"),
            pytest.param(101, "55", id="string_channel_id"),
        ],
    )
    def test_the_two_arguments_travel_without_type_conversion(
        self, use_case_factory, campaign_id, channel_id
    ):
        """Requirement 6.1: both values are passed on as received — no
        ``int()``, no ``str()``, no ``strip()``.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_validated_campaign_setup(campaign_id, channel_id)

        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.assert_called_once_with(
            campaign_id, channel_id
        )
        recorded_args, recorded_kwargs = (
            mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_args
        )
        assert recorded_kwargs == {}
        assert [type(value) for value in recorded_args] == [
            type(campaign_id),
            type(channel_id),
        ]

    # -- Requirement 6.7: the constructor's repository, and only it ---------

    def test_validation_uses_the_constructor_repository_only(self, use_case_factory):
        """Requirement 6.7: the query goes through
        ``self.campaign_channel_publish_repository`` and no other repository is
        touched.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_validated_campaign_setup(101, 55)

        assert mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_count == 1
        assert len(mock_campaign_publish_repo.mock_calls) == 1
        assert mock_account_repo.mock_calls == []
        assert mock_campaign_repo.mock_calls == []
        assert mock_ad_channel_repo.mock_calls == []

    def test_validation_instantiates_no_repository(self, use_case_factory):
        """Requirement 6.7: zero instantiations of
        ``CampaignChannelPublishRepository`` — or of any other repository —
        during the validation itself.

        The classes are patched **after** the use case has been built, so the
        doubles record only what happens inside the method under test.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        with patch(
            "app.v2.use_cases.meta_ads.CampaignChannelPublishRepository"
        ) as mock_campaign_publish_repository_cls, patch(
            "app.v2.use_cases.meta_ads.AdChannelRepository"
        ) as mock_ad_channel_repository_cls, patch(
            "app.v2.use_cases.meta_ads.CampaignRepository"
        ) as mock_campaign_repository_cls, patch(
            "app.v2.use_cases.meta_ads.AccountRepository"
        ) as mock_account_repository_cls:
            use_case._get_validated_campaign_setup(101, 55)

        assert mock_campaign_publish_repository_cls.call_count == 0
        assert mock_ad_channel_repository_cls.call_count == 0
        assert mock_campaign_repository_cls.call_count == 0
        assert mock_account_repository_cls.call_count == 0
        assert mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_count == 1

    def test_validation_touches_neither_redis_nor_the_network(self, use_case_factory):
        """The Campaign_Setup validation is a single Strapi read: zero Redis
        accesses and zero binary downloads (Requirements 6.2, 6.4, 6.5 all
        forbid downloading anything).
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        with patch_redis_client() as mock_redis_client:
            with patch_image_download() as mock_requests_get:
                use_case._get_validated_campaign_setup(101, 55)

        assert mock_redis_client.mock_calls == []
        assert mock_requests_get.call_count == 0

    # -- Requirement 6.2: falsy and non-dict records ------------------------

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_CAMPAIGN_SETUP_VALUES)
    def test_unresolved_campaign_setup_raises_data_not_found(
        self, use_case_factory, returned_value
    ):
        """Requirement 6.2: ``None``, every falsy value named by the criterion
        (``{}``, ``[]``, ``0``, the empty string) and every value that is not a
        ``dict`` instance — even a truthy one — raise
        ``DataNotFoundException``.

        Only the exception type is asserted, never the message text.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            returned_value
        )

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_validated_campaign_setup(101, 55)

        assert_exception_type(exc_info, DataNotFoundException)

    @pytest.mark.parametrize("returned_value", _UNRESOLVED_CAMPAIGN_SETUP_VALUES)
    def test_unresolved_campaign_setup_logs_both_identifiers(
        self, use_case_factory, returned_value
    ):
        """Requirement 6.2: a single ``logger.error`` naming the ``campaign_id``
        and the Channel_ID consulted.

        The two values are deliberately unlikely digit strings, so finding them
        in the logged line cannot be a coincidence.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            returned_value
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(DataNotFoundException):
                use_case._get_validated_campaign_setup(918273, 110099)

        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        for value in ["918273", "110099"]:
            assert value in logged

    def test_unresolved_campaign_setup_does_not_retry_the_query(
        self, use_case_factory
    ):
        """Requirement 6.2: the failed lookup is not repeated."""
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = None

        with pytest.raises(DataNotFoundException):
            use_case._get_validated_campaign_setup(101, 55)

        assert mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_count == 1

    def test_unresolved_campaign_setup_downloads_nothing(self, use_case_factory):
        """Requirement 6.2: no binary is downloaded when the record is missing,
        so the short circuit happens before the surplus collection.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = {}

        with patch_image_download() as mock_requests_get:
            with pytest.raises(DataNotFoundException):
                use_case._get_validated_campaign_setup(101, 55)

        assert mock_requests_get.call_count == 0

    # -- Requirement 6.3: the degraded read of ``attributes`` ---------------

    def test_absent_attributes_yields_none_in_both_reads_without_raising(
        self, use_case_factory
    ):
        """Requirement 6.3: a record without the ``attributes`` key must make
        both reads yield ``None`` **without raising**, so the failure is the
        ``IncorrectValidationException`` of Requirement 6.4 and not an
        ``AttributeError`` or a ``TypeError`` escaping as a 500.

        ``assert_exception_type`` compares the type exactly, so any other
        exception type fails the case.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(attributes=ABSENT)
        )

        with pytest.raises(IncorrectValidationException) as exc_info:
            use_case._get_validated_campaign_setup(101, 55)

        assert_exception_type(exc_info, IncorrectValidationException)

    def test_empty_attributes_behaves_like_absent_attributes(self, use_case_factory):
        """Requirement 6.3: ``attributes`` present but empty is the same
        degraded read — both values are ``None`` — and reaches the very same
        publication rejection.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = {
            "id": 55,
            "attributes": {},
        }

        with pytest.raises(IncorrectValidationException) as exc_info:
            use_case._get_validated_campaign_setup(101, 55)

        assert_exception_type(exc_info, IncorrectValidationException)

    def test_the_reads_do_not_mutate_the_campaign_setup(self, use_case_factory):
        """Requirement 6.3: the two reads are read-only — no key is created by
        a ``setdefault``-style traversal, not even on the degraded record.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        campaign_setup = make_campaign_setup(attributes=ABSENT)
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        with pytest.raises(IncorrectValidationException):
            use_case._get_validated_campaign_setup(101, 55)

        assert campaign_setup == make_campaign_setup(attributes=ABSENT)

    # -- Requirement 6.4: publication compared by identity against True -----

    @pytest.mark.parametrize("meta_published", _REJECTED_META_PUBLISHED_VALUES)
    def test_rejected_meta_published_raises_incorrect_validation(
        self, use_case_factory, meta_published
    ):
        """Requirement 6.4: anything that is not identically the boolean
        ``True`` — absent key, ``None``, ``False``, and the truthy look-alikes
        ``1``, ``'True'`` and ``'true'`` — raises
        ``IncorrectValidationException``.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(meta_published=meta_published)
        )

        with pytest.raises(IncorrectValidationException) as exc_info:
            use_case._get_validated_campaign_setup(101, 55)

        assert_exception_type(exc_info, IncorrectValidationException)

    @pytest.mark.parametrize("meta_published", _REJECTED_META_PUBLISHED_VALUES)
    def test_rejected_meta_published_logs_the_campaign_id(
        self, use_case_factory, meta_published
    ):
        """Requirement 6.4: a single ``logger.error`` naming the
        ``campaign_id``.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(meta_published=meta_published)
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(IncorrectValidationException):
                use_case._get_validated_campaign_setup(918273, 55)

        assert mock_logger.error.call_count == 1
        assert "918273" in mock_logger.error.call_args[0][0]

    @pytest.mark.parametrize("meta_published", _REJECTED_META_PUBLISHED_VALUES)
    def test_rejected_meta_published_downloads_nothing_and_writes_nothing(
        self, use_case_factory, meta_published
    ):
        """Requirement 6.4: no binary is downloaded and no Strapi record is
        updated — the repository double records only the single read.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(meta_published=meta_published)
        )

        with patch_image_download() as mock_requests_get:
            with pytest.raises(IncorrectValidationException):
                use_case._get_validated_campaign_setup(101, 55)

        assert mock_requests_get.call_count == 0
        assert len(mock_campaign_publish_repo.mock_calls) == 1

    def test_meta_published_true_is_accepted(self, use_case_factory):
        """Requirement 6.4, stated the other way round: the literal ``True`` is
        the one accepted value.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(meta_published=True)
        )

        assert use_case._get_validated_campaign_setup(101, 55) is not None

    # -- Requirement 6.5: mode compared case-sensitively, verbatim ----------

    @pytest.mark.parametrize(
        "meta_campaign_mode", _REJECTED_META_CAMPAIGN_MODE_VALUES
    )
    def test_rejected_meta_campaign_mode_raises_incorrect_validation(
        self, use_case_factory, meta_campaign_mode
    ):
        """Requirement 6.5: ``None``, the empty string, ``'standard'``,
        ``' STANDARD '`` and ``CreativeType.DYNAMIC.value`` are all rejected
        with ``IncorrectValidationException``.

        The setup is published in every case, so the only possible cause of the
        exception is the mode.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_published=True, meta_campaign_mode=meta_campaign_mode
            )
        )

        with pytest.raises(IncorrectValidationException) as exc_info:
            use_case._get_validated_campaign_setup(101, 55)

        assert_exception_type(exc_info, IncorrectValidationException)

    @pytest.mark.parametrize(
        "meta_campaign_mode",
        [
            pytest.param("standard", id="lowercase"),
            pytest.param(" STANDARD ", id="surrounding_whitespace"),
            pytest.param(CreativeType.DYNAMIC.value, id="dynamic"),
        ],
    )
    def test_rejected_meta_campaign_mode_logs_the_mode_value(
        self, use_case_factory, meta_campaign_mode
    ):
        """Requirement 6.5: a single ``logger.error`` carrying the mode value
        that was read, which is what tells this rejection apart from the
        publication one.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_published=True, meta_campaign_mode=meta_campaign_mode
            )
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(IncorrectValidationException):
                use_case._get_validated_campaign_setup(101, 55)

        assert mock_logger.error.call_count == 1
        assert meta_campaign_mode in mock_logger.error.call_args[0][0]

    @pytest.mark.parametrize(
        "meta_campaign_mode", _REJECTED_META_CAMPAIGN_MODE_VALUES
    )
    def test_rejected_meta_campaign_mode_downloads_nothing_and_writes_nothing(
        self, use_case_factory, meta_campaign_mode
    ):
        """Requirement 6.5: no binary is downloaded and no Strapi record is
        updated.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_published=True, meta_campaign_mode=meta_campaign_mode
            )
        )

        with patch_image_download() as mock_requests_get:
            with pytest.raises(IncorrectValidationException):
                use_case._get_validated_campaign_setup(101, 55)

        assert mock_requests_get.call_count == 0
        assert len(mock_campaign_publish_repo.mock_calls) == 1

    def test_the_exact_standard_value_is_accepted(self, use_case_factory):
        """Requirement 6.5, stated the other way round: exactly
        ``CreativeType.STANDARD.value`` passes.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(meta_campaign_mode=CreativeType.STANDARD.value)
        )

        assert use_case._get_validated_campaign_setup(101, 55) is not None

    # -- Requirement 6.6: publication is checked before the mode ------------

    @pytest.mark.parametrize(
        "meta_published,meta_campaign_mode", _BOTH_INVALID_COMBINATIONS
    )
    def test_both_invalid_raises_exactly_one_exception_about_publication(
        self, use_case_factory, meta_published, meta_campaign_mode
    ):
        """Requirement 6.6: with both values invalid, exactly **one**
        ``IncorrectValidationException`` is raised and it is the publication
        one — the mode check is not evaluated.

        The two rejections are told apart the only way the criteria allow
        without pinning message text: the publication error must name the
        ``campaign_id`` (Requirement 6.4) and the mode error must carry the
        mode value that was read (Requirement 6.5). So a single
        ``logger.error`` naming the campaign and **not** carrying the mode
        value proves which branch fired.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_published=meta_published,
                meta_campaign_mode=meta_campaign_mode,
            )
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._get_validated_campaign_setup(918273, 55)

        assert_exception_type(exc_info, IncorrectValidationException)
        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        assert "918273" in logged
        if meta_campaign_mode:
            assert meta_campaign_mode not in logged

    def test_precedence_does_not_depend_on_the_mode_being_invalid(
        self, use_case_factory
    ):
        """Requirement 6.6 from the complementary angle: an unpublished setup
        whose mode **is** ``STANDARD`` raises the same single publication
        exception, so the outcome is driven by the publication value alone.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup(
                meta_published=False,
                meta_campaign_mode=CreativeType.STANDARD.value,
            )
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(IncorrectValidationException) as exc_info:
                use_case._get_validated_campaign_setup(918273, 55)

        assert_exception_type(exc_info, IncorrectValidationException)
        assert mock_logger.error.call_count == 1
        assert "918273" in mock_logger.error.call_args[0][0]

    # -- Requirement 6.9: the happy path ------------------------------------

    def test_happy_path_returns_the_resolved_record_by_identity(
        self, use_case_factory
    ):
        """Requirement 6.9: the very record returned by the repository is
        handed back, not a copy nor a reshaped version of it.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        campaign_setup = make_campaign_setup()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        assert use_case._get_validated_campaign_setup(101, 55) is campaign_setup

    def test_happy_path_logs_no_error(self, use_case_factory):
        """Requirement 6.9: a published ``STANDARD`` setup emits zero
        ``logger.error`` calls.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            use_case._get_validated_campaign_setup(101, 55)

        assert mock_logger.error.call_count == 0

    def test_happy_path_does_not_query_the_campaign_setup_twice(
        self, use_case_factory
    ):
        """Requirement 6.9: the Campaign_Setup is not consulted again after
        passing both validations.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup()
        )

        use_case._get_validated_campaign_setup(101, 55)

        assert mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_count == 1

    def test_happy_path_returns_the_record_unmodified(self, use_case_factory):
        """Requirement 6.3: the validated record comes back exactly as stored,
        with no key added, removed nor rewritten.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        campaign_setup = make_campaign_setup()
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        returned = use_case._get_validated_campaign_setup(101, 55)

        assert returned == make_campaign_setup()

    def test_happy_path_ignores_additional_attributes(self, use_case_factory):
        """Requirement 6.3: only ``meta_published`` and ``meta_campaign_mode``
        are read; any other attribute of the record is irrelevant to the
        outcome and travels back untouched.
        """
        use_case, _, _, _, mock_campaign_publish_repo = use_case_factory()
        campaign_setup = make_campaign_setup()
        campaign_setup["attributes"]["meta_campaign_id"] = "23851234567890123"
        campaign_setup["attributes"]["unexpected_key"] = {"nested": [1, 2, 3]}
        mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            campaign_setup
        )

        returned = use_case._get_validated_campaign_setup(101, 55)

        assert returned is campaign_setup
        assert returned["attributes"]["unexpected_key"] == {"nested": [1, 2, 3]}


# ---------------------------------------------------------------------------
# Token, account and Cuenta_Padre resolution (Requirements 3.2, 3.4, 3.5,
# 3.7, 3.8)
# ---------------------------------------------------------------------------


# Redis values that ``_get_decoded_access_token`` must reject, all of them
# falsy: an absent key and an expired key both surface as ``None`` from
# ``redis_client.get``, and an emptied key as empty ``bytes`` (or, defensively,
# an empty ``str``). The three conditions of Requirement 3.2 — "no existe, ha
# expirado o contiene un valor vacío" — collapse into this single matrix.
_REJECTED_REDIS_TOKENS = [
    pytest.param(None, id="absent_or_expired_key"),
    pytest.param(b"", id="empty_bytes"),
    pytest.param("", id="empty_str"),
]


class TestParentAccountResolution:
    """Characterization of the **three pre-existing** methods
    ``_get_decoded_access_token``, ``_get_account`` and
    ``_get_parent_account``, invoked **directly** (Requirement 3.5).

    Unlike the rest of this suite, these tests do not pin new behaviour: they
    pin the behaviour that was already there before the export logic was
    added. Requirement 3.5 forbids changing it — for the same inputs the three
    methods must keep returning the same values and raising the same exception
    types — so this class is a regression net around code this specification
    deliberately leaves untouched.

    Four families of cases:

    * ``_get_decoded_access_token``: the Redis key is read exactly once and its
      name is literally ``facebook_access_token:{user_id}``; every falsy value
      raises ``NotAccessException`` before Strapi is touched (Requirement 3.2);
      a present value comes back UTF-8 decoded;
    * ``_get_account``: a single ``get_by_email(self.user_id)`` call, with
      every falsy result reported through ``logger.error`` naming the
      ``user_id`` and raised as ``DataNotFoundException`` (Requirement 3.4),
      and a truthy result returned by identity;
    * ``_get_parent_account`` with a populated ``attributes.parent_account.data``
      node, which yields that node's ``id`` (Requirement 3.7);
    * ``_get_parent_account`` without that node — absent, empty or with a falsy
      ``data`` — which falls back to the account's own ``id``
      (Requirement 3.8).

    Requirements: 3.2, 3.4, 3.5, 3.7, 3.8
    """

    # -- Requirement 3.2: the token read and its rejection matrix -----------

    def test_redis_is_read_once_with_the_user_scoped_key(self, use_case_factory):
        """Requirement 3.5: the key format is part of the preserved contract —
        exactly one ``get`` of ``facebook_access_token:{user_id}``.
        """
        use_case, _, _, _, _ = use_case_factory(user_id="user-42")

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"EAAG-some-token"

            use_case._get_decoded_access_token()

        mock_redis_client.get.assert_called_once_with("facebook_access_token:user-42")

    def test_present_token_is_returned_utf8_decoded(self, use_case_factory):
        """Requirement 3.5: the stored ``bytes`` come back as a ``str``, decoded
        as UTF-8, with no other transformation.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = b"EAAG-some-token"

            token = use_case._get_decoded_access_token()

        assert token == "EAAG-some-token"
        assert isinstance(token, str)

    @pytest.mark.parametrize("stored_value", _REJECTED_REDIS_TOKENS)
    def test_falsy_token_raises_not_access_exception(
        self, use_case_factory, stored_value
    ):
        """Requirement 3.2: absent, expired and empty all raise
        ``NotAccessException``, and nothing else.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = stored_value

            with pytest.raises(NotAccessException) as exc_info:
                use_case._get_decoded_access_token()

        assert_exception_type(exc_info, NotAccessException)

    @pytest.mark.parametrize("stored_value", _REJECTED_REDIS_TOKENS)
    def test_falsy_token_does_not_touch_strapi(self, use_case_factory, stored_value):
        """Requirement 3.2: the short circuit happens before any Strapi query,
        so the four repository doubles record zero invocations.
        """
        (
            use_case,
            mock_account_repo,
            mock_campaign_repo,
            mock_ad_channel_repo,
            mock_campaign_publish_repo,
        ) = use_case_factory()

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = stored_value

            with pytest.raises(NotAccessException):
                use_case._get_decoded_access_token()

        assert mock_account_repo.get_by_email.call_count == 0
        assert mock_campaign_repo.get_by_id_brand_and_account.call_count == 0
        assert mock_ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 0
        assert mock_campaign_publish_repo.get_by_campaign_id_and_channel_id.call_count == 0

    def test_empty_user_id_still_reads_the_bare_prefixed_key(self, use_case_factory):
        """Requirement 11.6 seen from here: an empty ``user_id`` is not
        validated at construction time; it surfaces as a lookup of the bare
        ``facebook_access_token:`` key, which does not exist, hence
        ``NotAccessException`` (Requirement 3.2).
        """
        use_case, _, _, _, _ = use_case_factory(user_id="")

        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = None

            with pytest.raises(NotAccessException) as exc_info:
                use_case._get_decoded_access_token()

        assert_exception_type(exc_info, NotAccessException)
        mock_redis_client.get.assert_called_once_with("facebook_access_token:")

    # -- Requirement 3.4: the account lookup -------------------------------

    def test_account_repository_is_invoked_once_with_the_user_id(
        self, use_case_factory
    ):
        """Requirement 3.5: exactly one ``get_by_email(self.user_id)``, with the
        ``user_id`` taken from the constructor and never from a payload
        (Requirement 2.6).
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory(user_id="user-42")
        mock_account_repo.get_by_email.return_value = make_account()

        use_case._get_account()

        mock_account_repo.get_by_email.assert_called_once_with("user-42")

    def test_resolved_account_is_returned_by_identity(self, use_case_factory):
        """Requirement 3.5: the very dict returned by the repository is handed
        back, not a copy nor a reshaped version of it.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        account = make_account()
        mock_account_repo.get_by_email.return_value = account

        assert use_case._get_account() is account

    @pytest.mark.parametrize(
        "repository_result",
        [
            pytest.param(None, id="none"),
            pytest.param({}, id="empty_dict"),
            pytest.param([], id="empty_list"),
            pytest.param("", id="empty_str"),
            pytest.param(0, id="zero"),
            pytest.param(False, id="false"),
        ],
    )
    def test_missing_account_raises_data_not_found_exception(
        self, use_case_factory, repository_result
    ):
        """Requirement 3.4: every falsy result of ``get_by_email`` raises
        ``DataNotFoundException``.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = repository_result

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_account()

        assert_exception_type(exc_info, DataNotFoundException)

    def test_missing_account_is_logged_with_the_user_id(self, use_case_factory):
        """Requirement 3.4: the failure is reported through ``logger.error``
        naming the ``user_id`` that could not be resolved.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory(user_id="user-42")
        mock_account_repo.get_by_email.return_value = None

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            with pytest.raises(DataNotFoundException):
                use_case._get_account()

        assert mock_logger.error.call_count == 1
        assert "user-42" in mock_logger.error.call_args[0][0]

    def test_resolved_account_logs_no_error(self, use_case_factory):
        """Requirement 3.5: the happy path emits zero ``logger.error`` calls."""
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = make_account()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            use_case._get_account()

        assert mock_logger.error.call_count == 0

    # -- Requirement 3.7: the account has a parent -------------------------

    def test_parent_account_node_present_yields_the_parent_id(
        self, use_case_factory
    ):
        """Requirement 3.7: with ``attributes.parent_account.data.id`` populated,
        that identifier is the Cuenta_Padre, not the account's own ``id``.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = make_account(
            parent_account_id=99, account_id=1
        )

        parent_account = use_case._get_parent_account()

        assert parent_account == 99

    def test_parent_account_resolution_reads_the_account_once(
        self, use_case_factory
    ):
        """Requirement 3.5: resolving the Cuenta_Padre issues a single account
        lookup, not one per nested read.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory(user_id="user-42")
        mock_account_repo.get_by_email.return_value = make_account(
            parent_account_id=99
        )

        use_case._get_parent_account()

        mock_account_repo.get_by_email.assert_called_once_with("user-42")

    def test_missing_account_propagates_from_parent_account_resolution(
        self, use_case_factory
    ):
        """Requirement 3.4: ``_get_parent_account`` delegates to ``_get_account``,
        so an unresolvable account surfaces as the same
        ``DataNotFoundException`` here.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = None

        with pytest.raises(DataNotFoundException) as exc_info:
            use_case._get_parent_account()

        assert_exception_type(exc_info, DataNotFoundException)

    # -- Requirement 3.8: the account has no parent ------------------------

    def test_absent_parent_account_node_yields_the_own_id(self, use_case_factory):
        """Requirement 3.8: with the ``parent_account`` key omitted from
        ``attributes``, the account's own ``id`` is the Cuenta_Padre.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = make_account(account_id=7)

        assert use_case._get_parent_account() == 7

    @pytest.mark.parametrize(
        "attributes",
        [
            pytest.param({}, id="empty_attributes"),
            pytest.param({"parent_account": {}}, id="parent_account_without_data"),
            pytest.param({"parent_account": {"data": None}}, id="data_is_none"),
            pytest.param({"parent_account": {"data": {}}}, id="data_is_empty_dict"),
        ],
    )
    def test_degraded_parent_account_paths_fall_back_to_the_own_id(
        self, use_case_factory, attributes
    ):
        """Requirement 3.8: every degraded shape of the nested node — absent,
        present but without ``data``, or with a falsy ``data`` — falls back to
        the account's own ``id`` without raising.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = {"id": 7, "attributes": attributes}

        assert use_case._get_parent_account() == 7

    def test_parent_account_id_is_returned_verbatim_without_conversion(
        self, use_case_factory
    ):
        """Requirement 3.5: the identifier travels as stored; a string
        ``parent_account`` id is not coerced into an ``int``.
        """
        use_case, mock_account_repo, _, _, _ = use_case_factory()
        mock_account_repo.get_by_email.return_value = make_account(
            parent_account_id="99", account_id=1
        )

        parent_account = use_case._get_parent_account()

        assert parent_account == "99"
        assert isinstance(parent_account, str)


# ---------------------------------------------------------------------------
# Naming helpers: extension derivation and entry name disambiguation
# (Requirements 9.3, 9.5)
# ---------------------------------------------------------------------------


# The four ``visual_url`` values of the extension-derivation table of
# ``design.md``, in the order in which the table lists them, plus the shape the
# algorithm actually sees in production. The first three URLs exercise an
# extension that *is* present in the last path segment (with and without a
# query string); the fourth exercises the ``.jpg`` default of Requirement 9.3.
_DESIGN_TABLE_URLS = [
    pytest.param("https://cdn.example/a/img.jpg", ".jpg", id="jpg"),
    pytest.param("https://cdn.example/a/img.png", ".png", id="png"),
    pytest.param("https://cdn.example/a/img.png?v=2&t=1", ".png", id="png_with_query"),
    pytest.param("https://cdn.example/a/img", ".jpg", id="no_extension_defaults"),
]

# The three real ``visual_url`` values of the maintainer-supplied ``ad-channel``
# record. They all end in ``.jpeg``, which Requirement 9.3 takes verbatim: the
# design explicitly does **not** normalise ``.jpeg`` into ``.jpg``.
_PRODUCTION_URLS = [
    pytest.param(_VISUAL_URL_FACEBOOK_POST, id="facebook_post"),
    pytest.param(_VISUAL_URL_INSTAGRAM_PORTRAIT, id="instagram_portrait"),
    pytest.param(_VISUAL_URL_INSTAGRAM_STORY, id="instagram_story"),
]


class TestExtensionDerivation:
    """Characterization of the ``_derive_image_extension`` ``staticmethod``,
    invoked **directly on the class** (Requirement 9.3).

    Being a ``staticmethod``, it needs no instance and no repository doubles:
    every case here calls
    ``FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(url)``.

    Four families of cases:

    * the four URLs of the extension-derivation table of ``design.md``,
      including the ``.jpg`` default for a last path segment with no extension;
    * the three real production URLs, which end in ``.jpeg`` and must derive
      ``.jpeg`` rather than the ``.jpg`` default;
    * the fragment variants, which must be discarded exactly like the query
      string because neither reaches the ``.path`` component;
    * the capitalisation variants, preserved as they appear in the URL because
      Requirement 9.3 asks for no normalisation.

    Requirements: 9.3
    """

    @pytest.mark.parametrize("visual_url,expected_extension", _DESIGN_TABLE_URLS)
    def test_design_table_urls_derive_their_documented_extension(
        self, visual_url, expected_extension
    ):
        """Requirement 9.3: the four rows of the ``design.md`` table, asserted
        one by one.
        """
        derived = FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(
            visual_url
        )

        assert derived == expected_extension

    @pytest.mark.parametrize("visual_url", _PRODUCTION_URLS)
    def test_production_urls_derive_the_jpeg_extension_verbatim(self, visual_url):
        """Requirement 9.3: the extension is taken as it figures in the URL, so
        the production ``.jpeg`` is **not** rewritten into ``.jpg``.
        """
        derived = FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(
            visual_url
        )

        assert derived == ".jpeg"

    @pytest.mark.parametrize(
        "visual_url,expected_extension",
        [
            pytest.param("https://cdn.example/a/img.png#seccion", ".png", id="fragment"),
            pytest.param(
                "https://cdn.example/a/img.png?v=2#seccion", ".png", id="query_and_fragment"
            ),
            pytest.param(
                "https://cdn.example/a/img#.png", ".jpg", id="extension_only_in_fragment"
            ),
        ],
    )
    def test_fragment_never_takes_part_in_the_derivation(
        self, visual_url, expected_extension
    ):
        """Requirement 9.3: the fragment is discarded just like the query
        string.

        The third case is the discriminating one: an extension that lives
        **only** inside the fragment must not be picked up, so the result is the
        ``.jpg`` default and not ``.png``.
        """
        derived = FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(
            visual_url
        )

        assert derived == expected_extension

    @pytest.mark.parametrize(
        "visual_url,expected_extension",
        [
            pytest.param("https://cdn.example/a/img.PNG", ".PNG", id="upper_png"),
            pytest.param("https://cdn.example/a/img.JPEG", ".JPEG", id="upper_jpeg"),
            pytest.param("https://cdn.example/a/img.Jpg", ".Jpg", id="mixed_case_jpg"),
        ],
    )
    def test_capitalisation_of_the_extension_is_preserved(
        self, visual_url, expected_extension
    ):
        """Requirement 9.3: no case normalisation — ``.PNG`` stays ``.PNG``."""
        derived = FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(
            visual_url
        )

        assert derived == expected_extension

    @pytest.mark.parametrize(
        "visual_url",
        [
            pytest.param("https://cdn.example/a/img", id="segment_without_dot"),
            pytest.param("https://cdn.example/a/.gitignore", id="segment_starting_with_dot"),
            pytest.param("https://cdn.example/a/", id="empty_last_segment"),
        ],
    )
    def test_segment_without_extension_falls_back_to_the_default(self, visual_url):
        """Requirement 9.3: the fallback is the class constant, and it applies to
        every shape of "the segment carries no extension".

        The dot-leading name is the case that motivates ``os.path.splitext`` over
        a manual ``rsplit('.', 1)``: ``.gitignore`` is a name, not an extension.
        """
        derived = FacebookExportAssetsPostLaunchCampaignUseCase._derive_image_extension(
            visual_url
        )

        assert derived == ".jpg"
        assert (
            derived
            == FacebookExportAssetsPostLaunchCampaignUseCase._DEFAULT_IMAGE_EXTENSION
        )


class TestNameDisambiguation:
    """Characterization of the ``_disambiguate_entry_name`` ``staticmethod``,
    invoked **directly on the class** (Requirement 9.5).

    The contract has one subtlety worth pinning on its own: the ``_{n}`` suffix
    goes **immediately before the extension**, so ``img.jpg`` becomes
    ``img_1.jpg`` and never ``img.jpg_1``. The successive-collision cases below
    reproduce the accumulation loop of ``_collect_surplus_images`` — call the
    helper, then ``add`` its result to ``used_names`` — which is the only way
    the second and third collisions can be reached.

    Requirements: 9.5
    """

    def test_name_free_of_collision_is_returned_unchanged(self):
        """Requirement 9.5: with no collision the argument travels back
        untouched, which is the normal outcome with the production data.
        """
        entry_name = "images/facebook-post.jpeg"

        assert (
            FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                entry_name, set()
            )
            is entry_name
        )

    def test_single_collision_inserts_the_suffix_before_the_extension(self):
        """Requirement 9.5: one collision yields ``_1`` before the extension."""
        used_names = {"images/img.jpg"}

        disambiguated = (
            FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                "images/img.jpg", used_names
            )
        )

        assert disambiguated == "images/img_1.jpg"
        assert disambiguated != "images/img.jpg_1"

    def test_three_successive_collisions_number_from_one_upwards(self):
        """Requirement 9.5: driving the helper the way ``_collect_surplus_images``
        does — accumulating every result into ``used_names`` — four elements
        sharing the same ``id`` and extension produce ``img.jpg``,
        ``img_1.jpg``, ``img_2.jpg`` and ``img_3.jpg``.

        This covers the 1, 2 and 3 successive collision cases in a single
        sequence, and pins that the counter starts at ``1`` and grows by ``1``.
        """
        used_names = set()
        produced = []

        for _ in range(4):
            disambiguated = (
                FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                    "images/img.jpg", used_names
                )
            )
            produced.append(disambiguated)
            used_names.add(disambiguated)

        assert produced == [
            "images/img.jpg",
            "images/img_1.jpg",
            "images/img_2.jpg",
            "images/img_3.jpg",
        ]
        assert len(used_names) == 4

    def test_suffix_is_never_appended_after_the_extension(self):
        """Requirement 9.5: the forbidden shape ``img.jpg_1`` must not appear at
        any point of the sequence, whatever the extension.

        Asserted structurally — every produced name still ends in the original
        extension — so the test fails for ``img.jpeg_1``, ``img.jpeg_2`` and any
        other "suffix at the end" variant.
        """
        used_names = set()

        for _ in range(3):
            disambiguated = (
                FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                    "images/instagram-story.jpeg", used_names
                )
            )
            used_names.add(disambiguated)

        assert sorted(used_names) == [
            "images/instagram-story.jpeg",
            "images/instagram-story_1.jpeg",
            "images/instagram-story_2.jpeg",
        ]
        for name in used_names:
            assert name.endswith(".jpeg")

    def test_name_without_extension_gets_the_suffix_at_the_end(self):
        """Requirement 9.5: with no extension to insert the suffix before, the
        ``_1`` lands at the end of the name, which is the same rule applied to
        an empty extension.
        """
        used_names = {"images/img"}

        assert (
            FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                "images/img", used_names
            )
            == "images/img_1"
        )

    def test_used_names_is_not_mutated_by_the_helper(self):
        """Requirement 9.5: bookkeeping belongs to the caller — the helper only
        computes a free name, and ``_collect_surplus_images`` is the one that
        ``add``s it.
        """
        used_names = {"images/img.jpg"}

        FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
            "images/img.jpg", used_names
        )

        assert used_names == {"images/img.jpg"}

    def test_collision_is_checked_against_the_exact_name_only(self):
        """Requirement 9.5: a ``used_names`` holding only the *suffixed* variant
        is no collision for the base name, so the base name is returned as is.
        """
        used_names = {"images/img_1.jpg", "images/img.png"}

        assert (
            FacebookExportAssetsPostLaunchCampaignUseCase._disambiguate_entry_name(
                "images/img.jpg", used_names
            )
            == "images/img.jpg"
        )


# ---------------------------------------------------------------------------
# Surplus image collection (Requirements 7.1-7.11, 9.2, 9.4, 9.5, 9.16)
# ---------------------------------------------------------------------------


def entry_names(images):
    """Return the ``entry_name`` of every descriptor of the **first** element of
    the tuple returned by ``_collect_surplus_images``, in the order in which the
    collector produced them (the order of appearance within ``media_formats``,
    Requirement 9.16).
    """
    return [descriptor["entry_name"] for descriptor in images]


def entry_contents(images):
    """Return the ``content`` of every descriptor, in the same order."""
    return [descriptor["content"] for descriptor in images]


def identifier_of_entry(entry_name):
    """Derive back the ``{id}`` part of an ``images/{id}{extension}`` entry name.

    This is the inverse of the naming rule of Requirement 9.2, and it is what
    lets the complementarity test compare the identifiers carried by the
    **first** element of the tuple against those listed in the **second** one.
    """
    assert entry_name.startswith("images/"), entry_name
    stem = entry_name[len("images/"):]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return stem


def requested_urls(mock_requests_get):
    """Return the first positional argument of every recorded download, that is
    the URL each ``requests.get`` was issued against.
    """
    return [recorded_call[0][0] for recorded_call in mock_requests_get.call_args_list]


def make_ad_channel_with_formats(media_formats):
    """Build an Ad_Channel_de_Exportación whose ``media_formats`` is exactly
    ``media_formats``.

    ``channel_attributes`` is forced to the empty list because
    ``_collect_surplus_images`` never reads it, and leaving the default four
    Categorías_de_Texto in place would only add noise to these fixtures.
    """
    return make_ad_channel(media_formats=media_formats, channel_attributes=[])


# Three non-pinned formats with distinct identifiers and distinct real
# ``visual_url`` values, used by the partial-failure scenarios: exactly one of
# the three fails, so the assertions can pin *which* identifier is reported.
_THREE_SURPLUS_IDS = ["alpha", "beta", "gamma"]
_THREE_SURPLUS_URLS = [
    _VISUAL_URL_FACEBOOK_POST,
    _VISUAL_URL_INSTAGRAM_PORTRAIT,
    _VISUAL_URL_INSTAGRAM_STORY,
]


def make_three_surplus_formats():
    """Build a fresh ``media_formats`` list of three non-pinned formats."""
    return [
        make_media_format(format_id=format_id, visual_url=visual_url, pinned=False)
        for format_id, visual_url in zip(_THREE_SURPLUS_IDS, _THREE_SURPLUS_URLS)
    ]


# The values of ``pinned`` that are **not** identically ``True`` and therefore
# still make the element a surplus candidate (Requirement 7.1). ``ABSENT``
# removes the key altogether.
_NON_PINNED_VALUES = [
    pytest.param(False, id="false"),
    pytest.param("True", id="string_true"),
    pytest.param("true", id="string_true_lowercase"),
    pytest.param(1, id="int_one"),
    pytest.param(None, id="none"),
    pytest.param(ABSENT, id="absent"),
]

# Every shape of "``visual_url`` is not usable" of Requirement 7.1: not a
# ``str``, or a ``str`` with no character left after stripping. All of them are
# causes of an Asset_No_Incluido (cause (a)), so they produce no entry but they
# **do** produce an identifier.
_UNUSABLE_VISUAL_URLS = [
    pytest.param("", id="empty_string"),
    pytest.param("   ", id="spaces_only"),
    pytest.param("\t\n ", id="tabs_and_newline_only"),
    pytest.param(None, id="present_but_none"),
    pytest.param(12345, id="int"),
    pytest.param(["https://cdn.example/a/img.jpg"], id="list"),
    pytest.param({"url": "https://cdn.example/a/img.jpg"}, id="dict"),
    pytest.param(ABSENT, id="absent"),
]

# Every shape of "``media_formats`` is unusable" of Requirement 7.7. Both
# elements of the returned tuple must be the empty list for all of them.
_UNUSABLE_MEDIA_FORMATS = [
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param({}, id="empty_dict"),
    pytest.param({"0": {"id": "facebook-post"}}, id="dict_keyed_by_index"),
    pytest.param("facebook-post", id="string"),
    pytest.param(3, id="int"),
    pytest.param((), id="empty_tuple"),
]


class TestSurplusImageCollection:
    """Characterization of ``_collect_surplus_images``, invoked **directly** on
    the instance while ``execute()`` does not exist yet.

    Every case unpacks the returned value **positionally** into the two names
    the design fixes for it::

        images, not_included_ids = use_case._collect_surplus_images(ad_channel)

    and asserts **both** elements, never just one. That is deliberate: the
    single hardest thing to get right in this method (Requirements 7.11, 9.4) is
    that each surplus candidate lands in exactly one of the two lists, with an
    identifier derived from one single expression. Asserting only the images
    would let a divergence between the ``{id}`` of an ``images/...`` entry and
    the identifier reported for a failure pass unnoticed.

    Requirements: 7.1, 7.2, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 9.2, 9.4,
    9.5, 9.16
    """

    # -- Requirements 7.1, 7.2, 7.3, 9.2: the nominal walk -----------------

    def test_two_downloadable_surpluses_are_collected_and_nothing_is_reported(
        self, use_case_factory
    ):
        """Requirements 7.1, 9.2: of the three production formats, the two that
        are not pinned become ``images/{id}.jpeg`` entries carrying their own
        binary, and the Asset_No_Incluido list stays empty.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel()

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert entry_names(images) == [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST),
            expected_image_binary(_VISUAL_URL_INSTAGRAM_STORY),
        ]
        assert not_included_ids == []
        assert mock_requests_get.call_count == 2

    def test_every_descriptor_holds_exactly_entry_name_and_content(
        self, use_case_factory
    ):
        """Requirement 9.2: the descriptor shape consumed by the packaging step
        is exactly ``{'entry_name': str, 'content': bytes}``.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_image_download():
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel()
            )

        assert not_included_ids == []
        for descriptor in images:
            assert set(descriptor.keys()) == {"entry_name", "content"}
            assert isinstance(descriptor["entry_name"], str)
            assert isinstance(descriptor["content"], bytes)

    def test_each_surplus_is_downloaded_once_with_the_ten_second_timeout(
        self, use_case_factory
    ):
        """Requirement 7.2: one single GET per Imagen_Excedente, with the class
        timeout and no retry.

        Requirement 7.10 rides along here: the requested URLs are **exactly**
        the two surplus ``visual_url`` values, so the perfectly downloadable
        ``preview_url`` that every production element carries is never fetched.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel()
            )

        assert len(images) == 2
        assert not_included_ids == []
        assert requested_urls(mock_requests_get) == [
            _VISUAL_URL_FACEBOOK_POST,
            _VISUAL_URL_INSTAGRAM_STORY,
        ]
        assert _PREVIEW_URL not in requested_urls(mock_requests_get)
        for recorded_call in mock_requests_get.call_args_list:
            recorded_args, recorded_kwargs = recorded_call
            assert len(recorded_args) == 1
            assert recorded_kwargs == {"timeout": 10}

    def test_two_equivalent_invocations_produce_the_same_order(self, use_case_factory):
        """Requirement 9.16: the collector is deterministic — same fixture, same
        entry names in the same order, and the same (empty) report.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_image_download():
            first_images, first_ids = use_case._collect_surplus_images(
                make_ad_channel()
            )
            second_images, second_ids = use_case._collect_surplus_images(
                make_ad_channel()
            )

        assert entry_names(first_images) == entry_names(second_images)
        assert entry_contents(first_images) == entry_contents(second_images)
        assert first_ids == second_ids == []

    def test_final_log_reports_the_downloaded_and_the_skipped_counts(
        self, use_case_factory
    ):
        """Requirement 7.9: one closing ``logger.info`` carrying both counts, the
        second of which is the size of the Asset_No_Incluido list — not merely
        the number of failed downloads.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = make_three_surplus_formats()
        media_formats[1]["visual_url"] = ""

        with patch_image_download():
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(
                    make_ad_channel_with_formats(media_formats)
                )

        assert len(images) == 2
        assert not_included_ids == ["beta"]
        assert mock_logger.info.call_count == 1
        logged = mock_logger.info.call_args[0][0]
        assert str(len(images)) in logged
        assert str(len(not_included_ids)) in logged

    # -- Requirement 7.1: pinned elements are neither exported nor reported --

    def test_pinned_element_yields_neither_entry_nor_identifier(self, use_case_factory):
        """Requirement 7.1: the pinned format is the asset already published in
        Meta. It is not a surplus, so it produces no ``images/...`` entry, and
        it is not an Asset_No_Incluido either, so it produces no identifier.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            make_media_format(
                format_id="instagram-portrait",
                visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
                pinned=True,
            )
        ]

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert images == []
        assert not_included_ids == []
        mock_requests_get.assert_not_called()

    def test_pinned_identifier_appears_in_neither_tuple_element(self, use_case_factory):
        """Requirement 7.1 on the production fixture: ``instagram-portrait`` is
        the pinned one, so its identifier is absent from both lists.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_image_download():
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel()
            )

        collected_ids = [identifier_of_entry(name) for name in entry_names(images)]
        assert "instagram-portrait" not in collected_ids
        assert "instagram-portrait" not in not_included_ids

    def test_pinned_element_with_unusable_url_is_still_not_reported(
        self, use_case_factory
    ):
        """Requirements 7.1, 7.11: the ``pinned`` check runs **before** the
        identifier is derived, so a pinned element whose ``visual_url`` is
        unusable cannot leak into the Asset_No_Incluido list through cause (a).
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            make_media_format(format_id="instagram-portrait", pinned=True)
        ]
        media_formats[0]["visual_url"] = ""

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert images == []
        assert not_included_ids == []
        mock_requests_get.assert_not_called()

    @pytest.mark.parametrize("pinned", _NON_PINNED_VALUES)
    def test_non_identical_true_pinned_values_are_surplus_candidates(
        self, use_case_factory, pinned
    ):
        """Requirement 7.1: ``pinned`` is compared with ``is True``, not by
        truthiness, so ``'True'``, ``1``, ``None`` and an absent key all leave
        the element in the surplus set.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
                pinned=pinned,
            )
        ]

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert entry_names(images) == ["images/facebook-post.jpeg"]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST)
        ]
        assert not_included_ids == []
        assert mock_requests_get.call_count == 1

    # -- Requirements 7.1, 7.11: cause (a), an unusable ``visual_url`` ------

    @pytest.mark.parametrize("visual_url", _UNUSABLE_VISUAL_URLS)
    def test_unusable_visual_url_produces_no_entry_but_one_identifier(
        self, use_case_factory, visual_url
    ):
        """Requirements 7.1, 7.11: a non-``str`` or blank ``visual_url`` is cause
        (a) of an Asset_No_Incluido — no ``images/...`` entry, one identifier
        reported, and no download attempted at all.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_format = make_media_format(format_id="facebook-post")
        if visual_url is ABSENT:
            del media_format["visual_url"]
        else:
            media_format["visual_url"] = visual_url

        with patch_image_download() as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats([media_format])
            )

        assert images == []
        assert not_included_ids == ["facebook-post"]
        mock_requests_get.assert_not_called()

    # -- Requirements 7.4, 7.5, 7.6: causes (b) and (c), failed downloads ---

    def test_one_of_three_downloads_with_a_non_200_status_is_reported(
        self, use_case_factory
    ):
        """Requirements 7.4, 7.6, 7.11: the format whose download answers 404 is
        skipped from the package and reported, the walk continues, the other two
        binaries arrive, and nothing is raised.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())

        with patch_image_download(
            {_VISUAL_URL_INSTAGRAM_PORTRAIT: 404}
        ) as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert mock_requests_get.call_count == 3
        assert entry_names(images) == ["images/alpha.jpeg", "images/gamma.jpeg"]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST),
            expected_image_binary(_VISUAL_URL_INSTAGRAM_STORY),
        ]
        assert not_included_ids == ["beta"]

    def test_non_200_status_and_url_are_logged_as_an_error(self, use_case_factory):
        """Requirement 7.4: the failure is logged with both the ``visual_url``
        and the status code.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())

        with patch_image_download({_VISUAL_URL_INSTAGRAM_PORTRAIT: 503}):
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert len(images) == 2
        assert not_included_ids == ["beta"]
        assert mock_logger.error.call_count == 1
        logged = mock_logger.error.call_args[0][0]
        assert _VISUAL_URL_INSTAGRAM_PORTRAIT in logged
        assert "503" in logged

    def test_one_of_three_downloads_raising_a_timeout_is_reported(
        self, use_case_factory
    ):
        """Requirements 7.5, 7.6, 7.11: a download that raises is handled exactly
        like a non-200 one — the exception never escapes the collector, the two
        remaining binaries are collected and the failing identifier is reported.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())

        with patch_image_download(
            {_VISUAL_URL_INSTAGRAM_PORTRAIT: requests.exceptions.Timeout}
        ) as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert mock_requests_get.call_count == 3
        assert entry_names(images) == ["images/alpha.jpeg", "images/gamma.jpeg"]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST),
            expected_image_binary(_VISUAL_URL_INSTAGRAM_STORY),
        ]
        assert not_included_ids == ["beta"]

    def test_raised_download_is_logged_with_its_url_and_does_not_propagate(
        self, use_case_factory
    ):
        """Requirement 7.5: the ``visual_url`` is logged, and the walk resumes at
        the next element rather than unwinding.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())

        with patch_image_download(
            {_VISUAL_URL_FACEBOOK_POST: requests.exceptions.Timeout()}
        ):
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert entry_names(images) == ["images/beta.jpeg", "images/gamma.jpeg"]
        assert not_included_ids == ["alpha"]
        assert mock_logger.error.call_count == 1
        assert _VISUAL_URL_FACEBOOK_POST in mock_logger.error.call_args[0][0]

    # -- Requirement 7.7: an unusable ``media_formats`` --------------------

    @pytest.mark.parametrize("media_formats", _UNUSABLE_MEDIA_FORMATS)
    def test_unusable_media_formats_yields_two_empty_lists(
        self, use_case_factory, media_formats
    ):
        """Requirement 7.7: absent, ``None`` or not a ``list`` — **both**
        elements of the tuple are the empty list, so no ``manifest.txt`` can be
        written downstream, and the condition is logged as a warning.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(channel_attributes=[])
        if media_formats is ABSENT:
            del ad_channel["attributes"]["media_formats"]
        else:
            ad_channel["attributes"]["media_formats"] = media_formats

        with patch_image_download() as mock_requests_get:
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(ad_channel)

        assert images == []
        assert not_included_ids == []
        assert mock_logger.warning.call_count == 1
        mock_requests_get.assert_not_called()

    def test_empty_media_formats_list_yields_two_empty_lists_without_warning(
        self, use_case_factory
    ):
        """Requirement 7.7 boundary: an empty ``list`` **is** a ``list``, so it
        is the nominal "nothing to export" case, not the degraded one.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch_image_download() as mock_requests_get:
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(
                    make_ad_channel_with_formats([])
                )

        assert images == []
        assert not_included_ids == []
        assert mock_logger.warning.call_count == 0
        mock_requests_get.assert_not_called()

    # -- Requirement 7.8: non-dict elements are skipped silently ------------

    @pytest.mark.parametrize(
        "element",
        [
            pytest.param("facebook-post", id="string"),
            pytest.param(None, id="none"),
            pytest.param(7, id="int"),
            pytest.param([{"id": "facebook-post"}], id="list"),
        ],
    )
    def test_non_dict_element_is_skipped_and_never_reported(
        self, use_case_factory, element
    ):
        """Requirements 7.8, 7.11: a non-``dict`` element is not a surplus
        candidate, so it is skipped without an error **and** without an entry in
        the Asset_No_Incluido list. Only the sibling ``dict`` is exported.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            element,
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
                pinned=False,
            ),
        ]

        with patch_image_download():
            with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
                images, not_included_ids = use_case._collect_surplus_images(
                    make_ad_channel_with_formats(media_formats)
                )

        assert entry_names(images) == ["images/facebook-post.jpeg"]
        assert not_included_ids == []
        assert mock_logger.error.call_count == 0

    # -- Requirements 9.4, 7.11: the identifier of an element without ``id`` -

    @pytest.mark.parametrize(
        "id_state",
        [pytest.param(ABSENT, id="id_absent"), pytest.param(None, id="id_is_none")],
    )
    def test_missing_id_is_reported_by_its_global_index(self, use_case_factory, id_state):
        """Requirements 9.4, 7.11: the fallback identifier is the zero-based index
        within the **complete** ``media_formats``, pinned and non-``dict``
        elements included.

        The fixture is built so that the two indices differ: the element sits at
        global index 2, but it is the **first** surplus candidate of the list.
        Reporting ``'0'`` here — the position among the surplus items — would be
        the natural bug, and this case is what rules it out.
        """
        use_case, _, _, _, _ = use_case_factory()
        candidate = make_media_format(format_id="facebook-post", pinned=False)
        if id_state is ABSENT:
            del candidate["id"]
        else:
            candidate["id"] = None
        candidate["visual_url"] = ""
        media_formats = [
            make_media_format(
                format_id="instagram-portrait",
                visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
                pinned=True,
            ),
            "not-a-dict",
            candidate,
        ]

        with patch_image_download():
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert images == []
        assert not_included_ids == ["2"]

    @pytest.mark.parametrize(
        "id_state",
        [pytest.param(ABSENT, id="id_absent"), pytest.param(None, id="id_is_none")],
    )
    def test_missing_id_names_the_entry_with_the_same_global_index(
        self, use_case_factory, id_state
    ):
        """Requirements 9.2, 9.4, 7.11: the very same expression feeds the entry
        name, so a successful download of that same element at global index 2
        produces ``images/2.jpeg``.

        Together with the previous case this pins the invariant that matters:
        the ``{id}`` of an ``images/...`` entry and the identifier reported for
        a failure cannot diverge, because they are computed once, before
        branching by cause.
        """
        use_case, _, _, _, _ = use_case_factory()
        candidate = make_media_format(
            format_id="facebook-post", visual_url=_VISUAL_URL_FACEBOOK_POST, pinned=False
        )
        if id_state is ABSENT:
            del candidate["id"]
        else:
            candidate["id"] = None
        media_formats = [
            make_media_format(
                format_id="instagram-portrait",
                visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
                pinned=True,
            ),
            "not-a-dict",
            candidate,
        ]

        with patch_image_download():
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert entry_names(images) == ["images/2.jpeg"]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST)
        ]
        assert not_included_ids == []

    # -- Requirement 7.11: the order of the reported identifiers -----------

    def test_identifiers_of_mixed_causes_follow_the_media_formats_order(
        self, use_case_factory
    ):
        """Requirement 7.11: the Asset_No_Incluido list is ordered by appearance
        within ``media_formats``, **not** grouped by cause.

        The fixture interleaves the three causes on purpose — a download that
        raises at index 0, an unusable ``visual_url`` at index 2 and a non-200
        status at index 3 — so an implementation that accumulated one list per
        cause and concatenated them afterwards would produce
        ``['gamma', 'alpha', 'delta']`` and fail here.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            make_media_format(
                format_id="alpha", visual_url=_VISUAL_URL_FACEBOOK_POST, pinned=False
            ),
            make_media_format(
                format_id="beta",
                visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
                pinned=False,
            ),
            make_media_format(
                format_id="gamma", visual_url=_VISUAL_URL_INSTAGRAM_STORY, pinned=False
            ),
            make_media_format(
                format_id="delta", visual_url="https://cdn.example/a/delta.jpeg",
                pinned=False,
            ),
        ]
        media_formats[2]["visual_url"] = "   "

        with patch_image_download(
            {
                _VISUAL_URL_FACEBOOK_POST: requests.exceptions.Timeout,
                "https://cdn.example/a/delta.jpeg": 500,
            }
        ) as mock_requests_get:
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert not_included_ids == ["alpha", "gamma", "delta"]
        assert entry_names(images) == ["images/beta.jpeg"]
        # ``gamma`` never reaches the network: its URL is unusable.
        assert requested_urls(mock_requests_get) == [
            _VISUAL_URL_FACEBOOK_POST,
            _VISUAL_URL_INSTAGRAM_PORTRAIT,
            "https://cdn.example/a/delta.jpeg",
        ]

    # -- Requirement 9.5: colliding entry names ----------------------------

    def test_two_surpluses_sharing_id_and_extension_are_disambiguated(
        self, use_case_factory
    ):
        """Requirement 9.5: two successful downloads whose computed entry name is
        identical yield ``images/{id}.jpeg`` and ``images/{id}_1.jpeg``, each
        carrying the binary of **its own** ``visual_url``.

        The URL-specific binaries of ``patch_image_download`` are what make this
        meaningful: a swap between the two entries would break the content
        assertion even though the names would still be right.
        """
        use_case, _, _, _, _ = use_case_factory()
        media_formats = [
            make_media_format(
                format_id="duplicated",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
                pinned=False,
            ),
            make_media_format(
                format_id="duplicated",
                visual_url=_VISUAL_URL_INSTAGRAM_STORY,
                pinned=False,
            ),
        ]

        with patch_image_download():
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        assert entry_names(images) == [
            "images/duplicated.jpeg",
            "images/duplicated_1.jpeg",
        ]
        assert entry_contents(images) == [
            expected_image_binary(_VISUAL_URL_FACEBOOK_POST),
            expected_image_binary(_VISUAL_URL_INSTAGRAM_STORY),
        ]
        assert not_included_ids == []

    # -- Property 12 at method level: exact complementarity ----------------

    def test_both_tuple_elements_are_disjoint_and_cover_every_candidate(
        self, use_case_factory
    ):
        """Property 12 of ``design.md`` (Requirements 7.11, 9.4) checked by
        example at the method level, before ``execute()`` and before the ZIP
        exists.

        On a fixture mixing successes and the three failure causes, every surplus
        candidate appears **exactly once**: the identifiers derived from the
        ``entry_name`` values of the first tuple element and those listed in the
        second one are disjoint, and their union is exactly the set of candidates
        — the ``dict`` elements whose ``pinned`` is not identically ``True``,
        identified by their ``id`` or, when it is missing, by their global index.
        """
        use_case, _, _, _, _ = use_case_factory()
        without_id = make_media_format(
            format_id=ABSENT,
            visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
            pinned=False,
        )
        media_formats = [
            # index 0: candidate, downloads successfully.
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
                pinned=False,
            ),
            # index 1: pinned, not a candidate.
            make_media_format(
                format_id="instagram-portrait",
                visual_url="https://cdn.example/a/pinned.jpeg",
                pinned=True,
            ),
            # index 2: candidate, download answers 500 (cause b).
            make_media_format(
                format_id="instagram-story",
                visual_url=_VISUAL_URL_INSTAGRAM_STORY,
                pinned=False,
            ),
            # index 3: not a dict, not a candidate.
            "not-a-dict",
            # index 4: candidate, unusable ``visual_url`` (cause a).
            make_media_format(format_id="extra-square", visual_url="", pinned=False),
            # index 5: candidate without ``id``, downloads successfully.
            without_id,
        ]
        expected_candidates = {
            "facebook-post",
            "instagram-story",
            "extra-square",
            "5",
        }

        with patch_image_download({_VISUAL_URL_INSTAGRAM_STORY: 500}):
            images, not_included_ids = use_case._collect_surplus_images(
                make_ad_channel_with_formats(media_formats)
            )

        collected_ids = {identifier_of_entry(name) for name in entry_names(images)}
        reported_ids = set(not_included_ids)

        assert collected_ids == {"facebook-post", "5"}
        assert reported_ids == {"instagram-story", "extra-square"}
        assert collected_ids.isdisjoint(reported_ids)
        assert collected_ids | reported_ids == expected_candidates
        assert len(images) + len(not_included_ids) == len(expected_candidates)


# ---------------------------------------------------------------------------
# Task 8.2 - Surplus text collection (Requirements 8.1 - 8.11)
# ---------------------------------------------------------------------------


def make_ad_channel_with_attributes(channel_attributes):
    """Build an Ad_Channel_de_Exportación whose ``channel_attributes`` is
    exactly ``channel_attributes``.

    ``media_formats`` is forced to the empty list because
    ``_collect_surplus_texts`` never reads it, and leaving the default three
    production formats in place would only add noise to these fixtures (and,
    were the method to touch them, would trip the ``deny_network`` guard).
    """
    return make_ad_channel(media_formats=[], channel_attributes=channel_attributes)


def empty_texts():
    """Return the mapping the method must produce when no Texto_Excedente
    survives: the four Categorías_de_Texto present as keys, each an empty list.

    Requirement 8.6 mandates the four keys always exist (the implementation
    deliberately avoids a ``defaultdict``), so "no surplus" is an empty list per
    category, never a missing key. A function — not a module-level constant —
    so that every caller compares against a brand new object.
    """
    return {"primary_text": [], "headline": [], "description": [], "cta": []}


# The four recognised Categorías_de_Texto of Requirement 8.1, in the order the
# implementation initialises them.
_TEXT_CATEGORIES = ["primary_text", "headline", "description", "cta"]

# Names that must be skipped without logging an error (Requirements 8.8, 8.11).
# The three capitalization/whitespace variants called out by Requirement 8.1
# lead the list: the comparison is exact, case-sensitive and does **not**
# normalize whitespace.
_UNRECOGNISED_NAMES = [
    pytest.param("Primary_Text", id="capitalized"),
    pytest.param("PRIMARY_TEXT", id="uppercase"),
    pytest.param(" primary_text ", id="surrounded_by_spaces"),
    pytest.param("primary_text ", id="trailing_space"),
    pytest.param(" primary_text", id="leading_space"),
    pytest.param("primary_text\n", id="trailing_newline"),
    pytest.param("Headline", id="capitalized_headline"),
    pytest.param("CTA", id="uppercase_cta"),
    pytest.param("primarytext", id="no_underscore"),
    pytest.param("primary_texts", id="plural"),
    pytest.param("title", id="unknown_word"),
    pytest.param("", id="empty_string"),
]

# Every shape of "``channel_attributes`` is unusable" of Requirement 8.6: all
# four categories stay empty and a single ``logger.warning`` is emitted.
#
# ``None`` is deliberately **not** in this list: ``channel_attributes=None`` is
# the builder's own "use the default list" marker, so the present-but-``None``
# case is built by mutating the record after the fact, in a dedicated test
# below. Same reasoning for ``_UNUSABLE_PAYLOADS``.
_UNUSABLE_CHANNEL_ATTRIBUTES = [
    pytest.param(ABSENT, id="absent"),
    pytest.param({}, id="empty_dict"),
    pytest.param({"primary_text": ["a"]}, id="dict_keyed_by_category"),
    pytest.param("primary_text", id="string"),
    pytest.param(4, id="int"),
    pytest.param((), id="empty_tuple"),
]

# Every shape of "``payloads`` is unusable" of Requirement 8.7: the category is
# treated as empty and the walk continues with the next attribute.
_UNUSABLE_PAYLOADS = [
    pytest.param(ABSENT, id="absent"),
    pytest.param({}, id="empty_dict"),
    pytest.param({"0": {"id": 1, "payload": "x"}}, id="dict_keyed_by_index"),
    pytest.param("Cuerpo alternativo A", id="string"),
    pytest.param(7, id="int"),
    pytest.param((), id="empty_tuple"),
]

# Elements of ``payloads`` that are not ``dict`` (Requirement 8.5): skipped
# with no error and no warning.
_NON_DICT_PAYLOAD_ITEMS = [
    pytest.param("Cuerpo alternativo A", id="string"),
    pytest.param(None, id="none"),
    pytest.param(5, id="int"),
    pytest.param([], id="empty_list"),
    pytest.param(["Cuerpo alternativo A"], id="list"),
    pytest.param((1, "Cuerpo alternativo A"), id="tuple"),
]

# Values of ``payload`` that make the element unusable (Requirement 8.4):
# absent, ``None``, not a ``str``, or blank once stripped.
_UNUSABLE_PAYLOAD_VALUES = [
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param("", id="empty_string"),
    pytest.param("   ", id="spaces_only"),
    pytest.param("\t\n ", id="tabs_and_newline_only"),
    pytest.param("\u00a0", id="non_breaking_space_only"),
    pytest.param(42, id="int"),
    pytest.param(["Cuerpo alternativo A"], id="list"),
    pytest.param({"text": "Cuerpo alternativo A"}, id="dict"),
]


class TestSurplusTextCollection:
    """Characterization of ``_collect_surplus_texts``, invoked **directly** on
    the instance while ``execute()`` does not exist yet.

    The method is pure with respect to the outside world: it reads
    ``ad_channel['attributes']['channel_attributes']`` and nothing else, issues
    no HTTP request, no Redis command and no Strapi query. The ``deny_network``
    autouse fixture therefore guards every case here for free, and no download
    double is installed.

    Two invariants are asserted over and over because they are what
    ``_build_zip_package`` relies on:

    * the returned mapping always holds **exactly** the four
      Categorías_de_Texto as keys, even when nothing survives the filters, so a
      caller can iterate it deterministically (Requirement 8.6);
    * the value of ``payload`` is accumulated **untrimmed**, even though
      ``strip()`` is what decided it was usable in the first place
      (Requirements 8.3, 8.4). That asymmetry is deliberate and is asserted
      explicitly.

    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10, 8.11
    """

    # -- Requirements 8.1, 8.2, 8.3: the nominal walk ----------------------

    def test_one_surplus_per_category_is_collected(self, use_case_factory):
        """Requirements 8.1, 8.2, 8.3: on the default fixture — the four
        Categorías_de_Texto, each holding the published base asset (``id == 0``)
        plus one surplus (``id == 1``) — every category yields exactly its own
        surplus, and the base asset is nowhere to be found.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(media_formats=[])

        texts = use_case._collect_surplus_texts(ad_channel)

        assert texts == {
            "primary_text": ["Cuerpo alternativo A"],
            "headline": ["Titulo alterno"],
            "description": ["Descripcion alterna"],
            "cta": ["Mas informacion"],
        }

    def test_the_four_categories_are_always_present_as_keys(self, use_case_factory):
        """Requirement 8.6: the mapping is initialised with the four categories,
        so its key set never depends on which attributes happened to appear.
        """
        use_case, _, _, _, _ = use_case_factory()
        only_cta = [
            make_channel_attribute(
                name="cta",
                payloads=[make_text_payload(payload_id=9, text="Reservar")],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(only_cta)
        )

        assert sorted(texts.keys()) == sorted(_TEXT_CATEGORIES)
        assert texts == {
            "primary_text": [],
            "headline": [],
            "description": [],
            "cta": ["Reservar"],
        }

    @pytest.mark.parametrize("category", _TEXT_CATEGORIES)
    def test_each_recognised_category_is_processed_in_isolation(
        self, use_case_factory, category
    ):
        """Requirement 8.1: each of the four names is recognised on its own, and
        recognising one never contaminates the other three.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name=category,
                payloads=[make_text_payload(payload_id=3, text="Texto excedente")],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        expected = empty_texts()
        expected[category] = ["Texto excedente"]
        assert texts == expected

    def test_empty_payloads_list_yields_an_empty_category(self, use_case_factory):
        """A present but empty ``payloads`` list is not a degraded structure: the
        category is simply empty, with no warning.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [make_channel_attribute(name="primary_text", payloads=[])]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

    def test_empty_channel_attributes_list_yields_the_four_empty_categories(
        self, use_case_factory
    ):
        """A present but empty ``channel_attributes`` list is a valid absence of
        surplus, distinct from the degraded shapes of Requirement 8.6: no
        warning is emitted.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes([])
            )

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

    # -- Requirement 8.2: the id == 0 / id == '0' exclusion ----------------

    def test_base_asset_ids_are_excluded_and_surplus_ids_are_kept(
        self, use_case_factory
    ):
        """Requirement 8.2: within one ``payloads`` list, the integer ``0`` and
        the string ``'0'`` are the published base asset and are dropped, while
        every other identifier is a Texto_Excedente and is kept in order.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=0, text="Base entera"),
                    make_text_payload(payload_id="0", text="Base cadena"),
                    make_text_payload(payload_id=1, text="Excedente uno"),
                    make_text_payload(payload_id="2", text="Excedente dos"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["Excedente uno", "Excedente dos"]

    @pytest.mark.parametrize(
        "excluded_id",
        [
            pytest.param(0, id="int_zero"),
            pytest.param("0", id="string_zero"),
        ],
    )
    def test_zero_id_is_excluded_without_any_log(self, use_case_factory, excluded_id):
        """Requirement 8.2: the base asset is dropped **silently** — it is the
        expected content of a published creative, not an anomaly.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[make_text_payload(payload_id=excluded_id, text="Base")],
            )
        ]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 0
        assert mock_logger.error.call_count == 0

    @pytest.mark.parametrize(
        "kept_id",
        [
            pytest.param(1, id="int_one"),
            pytest.param(-1, id="negative_int"),
            pytest.param(42, id="large_int"),
            pytest.param("1", id="string_one"),
            pytest.param("00", id="double_zero_string"),
            pytest.param("abc", id="non_numeric_string"),
        ],
    )
    def test_non_zero_ids_are_kept(self, use_case_factory, kept_id):
        """Requirement 8.2: anything that is neither ``0`` nor ``'0'`` — and is
        not ``None`` — is a Texto_Excedente, whatever its type.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="headline",
                payloads=[make_text_payload(payload_id=kept_id, text="Titulo alterno")],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["headline"] == ["Titulo alterno"]

    # -- Requirements 8.8, 8.11: names that are skipped --------------------

    @pytest.mark.parametrize("unrecognised_name", _UNRECOGNISED_NAMES)
    def test_unrecognised_name_is_skipped_without_error(
        self, use_case_factory, unrecognised_name
    ):
        """Requirements 8.1, 8.8: the comparison against the four categories is
        exact, case-sensitive and performs no whitespace normalization, so
        ``'Primary_Text'``, ``'PRIMARY_TEXT'`` and ``' primary_text '`` all
        describe an attribute that is dropped — with no ``logger.error``, since
        an unknown name is not an anomaly of this export.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name=unrecognised_name,
                payloads=[make_text_payload(payload_id=1, text="Cuerpo alternativo A")],
            )
        ]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.error.call_count == 0
        assert mock_logger.warning.call_count == 0

    def test_unrecognised_names_do_not_shadow_the_recognised_one(
        self, use_case_factory
    ):
        """Requirement 8.8: a capitalization variant sitting next to the exact
        name neither replaces it nor merges into it.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="Primary_Text",
                payloads=[make_text_payload(payload_id=1, text="Variante ignorada")],
            ),
            make_channel_attribute(
                name="primary_text",
                payloads=[make_text_payload(payload_id=1, text="Variante exportada")],
            ),
            make_channel_attribute(
                name=" primary_text ",
                payloads=[make_text_payload(payload_id=2, text="Otra ignorada")],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["Variante exportada"]

    @pytest.mark.parametrize(
        "attribute",
        [
            pytest.param("primary_text", id="attribute_is_a_string"),
            pytest.param(None, id="attribute_is_none"),
            pytest.param(9, id="attribute_is_an_int"),
            pytest.param(["primary_text"], id="attribute_is_a_list"),
            pytest.param(
                make_channel_attribute(name=ABSENT), id="name_key_is_absent"
            ),
            pytest.param(make_channel_attribute(name=None), id="name_is_none"),
            pytest.param(make_channel_attribute(name=1), id="name_is_an_int"),
            pytest.param(
                make_channel_attribute(name=["primary_text"]), id="name_is_a_list"
            ),
            pytest.param(
                make_channel_attribute(name={"value": "primary_text"}),
                id="name_is_a_dict",
            ),
        ],
    )
    def test_malformed_attribute_is_skipped_without_error(
        self, use_case_factory, attribute
    ):
        """Requirement 8.11: a non-``dict`` attribute, a missing ``name``, a
        ``None`` ``name`` and a non-``str`` ``name`` are all skipped with no
        error, and the walk continues.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes([attribute])
            )

        assert texts == empty_texts()
        assert mock_logger.error.call_count == 0

    def test_malformed_attribute_does_not_stop_the_walk(self, use_case_factory):
        """Requirement 8.11: the surviving attributes after a malformed one are
        still processed.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            "not-a-dict",
            make_channel_attribute(name=None, payloads=[]),
            make_channel_attribute(
                name="cta",
                payloads=[make_text_payload(payload_id=1, text="Comprar")],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["cta"] == ["Comprar"]

    # -- Requirements 8.3, 8.9: duplicates, order and concatenation --------

    def test_duplicated_texts_are_kept_as_independent_entries(
        self, use_case_factory
    ):
        """Requirement 8.3: repeated texts are **not** de-duplicated — three
        identical surpluses produce three entries.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="description",
                payloads=[
                    make_text_payload(payload_id=1, text="Misma descripcion"),
                    make_text_payload(payload_id=2, text="Misma descripcion"),
                    make_text_payload(payload_id=3, text="Misma descripcion"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["description"] == [
            "Misma descripcion",
            "Misma descripcion",
            "Misma descripcion",
        ]

    def test_order_of_appearance_within_payloads_is_preserved(
        self, use_case_factory
    ):
        """Requirement 8.3: the order is the order of appearance inside
        ``payloads``, not the order of the identifiers.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=9, text="Primero"),
                    make_text_payload(payload_id=0, text="Base descartada"),
                    make_text_payload(payload_id=3, text="Segundo"),
                    make_text_payload(payload_id=7, text="Tercero"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["Primero", "Segundo", "Tercero"]

    def test_two_attributes_of_the_same_category_are_concatenated_in_order(
        self, use_case_factory
    ):
        """Requirement 8.9: two attributes declaring the same category merge
        into one list, following the order of the attributes and, within each,
        the order of its ``payloads``.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=1, text="A1"),
                    make_text_payload(payload_id=2, text="A2"),
                ],
            ),
            make_channel_attribute(
                name="headline",
                payloads=[make_text_payload(payload_id=1, text="H1")],
            ),
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=3, text="B1"),
                    make_text_payload(payload_id=4, text="B2"),
                ],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["A1", "A2", "B1", "B2"]
        assert texts["headline"] == ["H1"]

    def test_three_attributes_of_the_same_category_are_concatenated_in_order(
        self, use_case_factory
    ):
        """Requirement 8.9: the concatenation is not limited to two attributes,
        and an interleaved empty one does not disturb the order.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="cta",
                payloads=[make_text_payload(payload_id=1, text="Comprar")],
            ),
            make_channel_attribute(name="cta", payloads=[]),
            make_channel_attribute(
                name="cta",
                payloads=[
                    make_text_payload(payload_id=2, text="Reservar"),
                    make_text_payload(payload_id=3, text="Registrarse"),
                ],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["cta"] == ["Comprar", "Reservar", "Registrarse"]

    # -- Requirements 8.3, 8.4: the untrimmed value ------------------------

    @pytest.mark.parametrize(
        "raw_text",
        [
            pytest.param("  Cuerpo con espacios  ", id="surrounded_by_spaces"),
            pytest.param("\tCuerpo tabulado", id="leading_tab"),
            pytest.param("Cuerpo con salto\n", id="trailing_newline"),
            pytest.param("\n  Cuerpo mixto \t", id="mixed_whitespace"),
        ],
    )
    def test_payload_value_is_kept_untrimmed(self, use_case_factory, raw_text):
        """Requirements 8.3, 8.4: the asymmetry is deliberate — ``strip()``
        decides whether the element is usable, but the value stored is the
        original one, byte for byte, so the exported ``.txt`` reproduces exactly
        what the creative team wrote.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[make_text_payload(payload_id=1, text=raw_text)],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == [raw_text]

    def test_inner_whitespace_and_unicode_are_preserved(self, use_case_factory):
        """Requirement 8.3: no normalization of any kind — inner runs of spaces,
        accents and emoji survive untouched.
        """
        use_case, _, _, _, _ = use_case_factory()
        raw_text = "  Envío   gratis ✨ para ti  "
        attributes = [
            make_channel_attribute(
                name="description",
                payloads=[make_text_payload(payload_id=1, text=raw_text)],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["description"] == [raw_text]

    # -- Requirement 8.6: channel_attributes absent / None / non-list ------

    @pytest.mark.parametrize("channel_attributes", _UNUSABLE_CHANNEL_ATTRIBUTES)
    def test_unusable_channel_attributes_yields_four_empty_categories(
        self, use_case_factory, channel_attributes
    ):
        """Requirement 8.6: absent, ``None`` or any non-``list`` value is logged
        with a single ``logger.warning``, the four categories are treated as
        empty, and the packaging continues — no exception is raised.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel_with_attributes(channel_attributes)

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(ad_channel)

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 0

    def test_none_channel_attributes_yields_four_empty_categories(
        self, use_case_factory
    ):
        """Requirement 8.6, present-but-``None`` half: the key exists and holds
        ``None``, which is a different scenario from the key being absent and is
        therefore built by mutating the record — ``channel_attributes=None`` is
        the builder's "use the default list" marker, not a value.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(media_formats=[])
        ad_channel["attributes"]["channel_attributes"] = None

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(ad_channel)

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 0

    def test_absent_attributes_node_yields_four_empty_categories(
        self, use_case_factory
    ):
        """Requirement 8.6: the whole ``attributes`` node missing is read
        through the same defensive path, with no exception.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(make_ad_channel(attributes=ABSENT))

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 0

    # -- Requirement 8.7: payloads absent / None / non-list ----------------

    @pytest.mark.parametrize("payloads", _UNUSABLE_PAYLOADS)
    def test_unusable_payloads_yields_an_empty_category(
        self, use_case_factory, payloads
    ):
        """Requirement 8.7: an absent, ``None`` or non-``list`` ``payloads``
        makes **that** category empty; nothing else changes and no exception is
        raised.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [make_channel_attribute(name="primary_text", payloads=payloads)]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts == empty_texts()

    def test_none_payloads_yields_an_empty_category(self, use_case_factory):
        """Requirement 8.7, present-but-``None`` half: the ``payloads`` key
        exists and holds ``None``. Built by mutation for the same reason as the
        ``channel_attributes`` case above.
        """
        use_case, _, _, _, _ = use_case_factory()
        attribute = make_channel_attribute(name="primary_text")
        attribute["payloads"] = None
        attributes = [
            attribute,
            make_channel_attribute(
                name="headline",
                payloads=[make_text_payload(payload_id=1, text="Titulo alterno")],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == []
        assert texts["headline"] == ["Titulo alterno"]

    @pytest.mark.parametrize("payloads", _UNUSABLE_PAYLOADS)
    def test_unusable_payloads_does_not_stop_the_walk(
        self, use_case_factory, payloads
    ):
        """Requirement 8.7: the next attribute is still processed after one with
        an unusable ``payloads``.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(name="primary_text", payloads=payloads),
            make_channel_attribute(
                name="headline",
                payloads=[make_text_payload(payload_id=1, text="Titulo alterno")],
            ),
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == []
        assert texts["headline"] == ["Titulo alterno"]

    # -- Requirement 8.5: non-dict elements of payloads --------------------

    @pytest.mark.parametrize("item", _NON_DICT_PAYLOAD_ITEMS)
    def test_non_dict_payload_item_is_skipped(self, use_case_factory, item):
        """Requirement 8.5: an element of ``payloads`` that is not a ``dict`` is
        skipped, with no error and no warning.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [make_channel_attribute(name="primary_text", payloads=[item])]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.error.call_count == 0
        assert mock_logger.warning.call_count == 0

    def test_non_dict_payload_item_does_not_stop_the_walk(self, use_case_factory):
        """Requirement 8.5: the usable elements around a non-``dict`` one are
        still collected, in their original order.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=1, text="Antes"),
                    "not-a-dict",
                    None,
                    make_text_payload(payload_id=2, text="Despues"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["Antes", "Despues"]

    # -- Requirement 8.10: id absent / None --------------------------------

    @pytest.mark.parametrize(
        "payload_id",
        [
            pytest.param(ABSENT, id="absent"),
            pytest.param(None, id="none"),
        ],
    )
    def test_missing_id_is_skipped_with_a_warning(self, use_case_factory, payload_id):
        """Requirement 8.10: an element whose ``id`` is absent or ``None`` is
        dropped and the condition is reported with ``logger.warning`` — unlike
        the ``id == 0`` exclusion, which is silent.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=payload_id, text="Sin identificador")
                ],
            )
        ]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.warning.call_count == 1
        assert mock_logger.error.call_count == 0

    def test_missing_id_does_not_stop_the_walk(self, use_case_factory):
        """Requirement 8.10: the walk continues with the next element of
        ``payloads`` after one without a usable ``id``.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    make_text_payload(payload_id=ABSENT, text="Sin clave id"),
                    make_text_payload(payload_id=None, text="Id nulo"),
                    make_text_payload(payload_id=5, text="Con identificador"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["primary_text"] == ["Con identificador"]

    # -- Requirement 8.4: payload absent / None / non-str / blank ----------

    @pytest.mark.parametrize("text", _UNUSABLE_PAYLOAD_VALUES)
    def test_unusable_payload_value_is_skipped(self, use_case_factory, text):
        """Requirement 8.4: a ``payload`` that is absent, ``None``, not a
        ``str`` or blank once stripped produces no entry.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="primary_text",
                payloads=[make_text_payload(payload_id=1, text=text)],
            )
        ]

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            texts = use_case._collect_surplus_texts(
                make_ad_channel_with_attributes(attributes)
            )

        assert texts == empty_texts()
        assert mock_logger.error.call_count == 0

    def test_unusable_payload_value_does_not_stop_the_walk(self, use_case_factory):
        """Requirement 8.4: usable elements around an unusable ``payload`` are
        still collected, in order.
        """
        use_case, _, _, _, _ = use_case_factory()
        attributes = [
            make_channel_attribute(
                name="cta",
                payloads=[
                    make_text_payload(payload_id=1, text="   "),
                    make_text_payload(payload_id=2, text="Comprar ya"),
                    make_text_payload(payload_id=3, text=ABSENT),
                    make_text_payload(payload_id=4, text="Reservar hoy"),
                ],
            )
        ]

        texts = use_case._collect_surplus_texts(
            make_ad_channel_with_attributes(attributes)
        )

        assert texts["cta"] == ["Comprar ya", "Reservar hoy"]

    # -- Cross-cutting: nothing leaves the method ---------------------------

    def test_the_input_ad_channel_is_not_mutated(self, use_case_factory):
        """The method is read-only with respect to its argument: this
        specification is read-only towards Strapi, and mutating the record in
        place would be an easy way to leak state between the image and the text
        collection steps of ``execute()``.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(media_formats=[])
        expected = make_ad_channel(media_formats=[])

        use_case._collect_surplus_texts(ad_channel)

        assert ad_channel == expected

    def test_two_invocations_on_the_same_ad_channel_are_independent(
        self, use_case_factory
    ):
        """Consecutive invocations do not accumulate: the second result equals
        the first one instead of holding twice as many texts. Guards against a
        mapping shared at class level rather than rebuilt per call.
        """
        use_case, _, _, _, _ = use_case_factory()
        ad_channel = make_ad_channel(media_formats=[])

        first = use_case._collect_surplus_texts(ad_channel)
        second = use_case._collect_surplus_texts(ad_channel)

        assert first == second
        assert first is not second
        assert first["primary_text"] == ["Cuerpo alternativo A"]


# ---------------------------------------------------------------------------
# Task 9.2 - ZIP package structure (Requirements 9.1, 9.6-9.16, 10.2)
# ---------------------------------------------------------------------------


def make_image_descriptor(entry_name, content=None):
    """Build a fresh Imagen_Excedente descriptor of the shape
    ``_collect_surplus_images`` produces and ``_build_zip_package`` consumes,
    that is ``{'entry_name': str, 'content': bytes}``.

    The default ``content`` is derived from ``entry_name``, so every descriptor
    of a fixture carries a **distinct** binary: were the packer to swap two
    payloads between entries, the content assertions below would fail instead
    of passing by coincidence.
    """
    if content is None:
        content = "binary-of-{}".format(entry_name).encode("utf-8")
    return {"entry_name": entry_name, "content": content}


def two_image_descriptors():
    """Build a fresh list of two image descriptors named after the production
    shape confirmed by the maintainer (``images/{format-id}.jpeg``).
    """
    return [
        make_image_descriptor("images/facebook-post.jpeg"),
        make_image_descriptor("images/instagram-story.jpeg"),
    ]


def full_texts():
    """Build a fresh Textos_Excedentes mapping with **all four**
    Categorías_de_Texto non empty, the first of them holding two texts so the
    ``'\\n'`` separator of Requirement 9.7 is actually exercised.
    """
    return {
        "primary_text": ["Cuerpo alternativo A", "Cuerpo alternativo B"],
        "headline": ["Titular alternativo"],
        "description": ["Descripción alternativa"],
        "cta": ["Comprar ya"],
    }


# The Categoría_de_Texto → filename mapping of Requirement 9.6, restated here
# independently of the implementation constant so that a change to
# ``_TEXT_CATEGORY_FILENAMES`` is caught by these tests instead of being
# mirrored by them.
_CATEGORY_FILENAMES = {
    "primary_text": "primary_texts.txt",
    "headline": "headlines.txt",
    "description": "descriptions.txt",
    "cta": "ctas.txt",
}

# The four ``.txt`` names of Requirement 9.6, sorted alphabetically for the
# exact list comparisons.
_ALL_TXT_NAMES = sorted(_CATEGORY_FILENAMES.values())


def zip_infolist(content):
    """Return the ``ZipInfo`` entries of ``content``.

    ``read_zip`` deliberately returns only names and bytes, which is what most
    assertions need; the compression assertion of Requirement 9.1 is the one
    case that has to reach the archive metadata.
    """
    with zipfile.ZipFile(BytesIO(content)) as zip_file:
        return zip_file.infolist()


class TestZipStructure:
    """Characterization of ``_build_zip_package``, invoked **directly** on the
    instance while ``execute()`` does not exist yet, with the resulting bytes
    read back through ``read_zip``.

    The method is pure: it takes the three already-collected sets and returns
    bytes, with no Strapi query, no Redis command, no HTTP request and no
    temporary file. The ``deny_network`` autouse fixture guards every case here
    for free.

    Two structural invariants are asserted repeatedly because the whole
    predictability promise of Requirement 9 rests on them:

    * image entries live **exclusively** under ``images/`` and text entries
      **exclusively** at the root, with 0 text entries under the prefix
      (Requirement 9.15);
    * ``manifest.txt`` is derived **exclusively** from ``not_included_ids``, so
      its presence signals an incomplete package and its absence a complete one
      (Requirements 9.9, 9.11, 9.12).

    Requirements: 9.1, 9.6, 9.7, 9.8, 9.9, 9.10, 9.11, 9.12, 9.13, 9.14, 9.15,
    9.16, 10.2
    """

    # -- Requirements 9.6, 9.15, 9.16: the nominal structure ---------------

    def test_two_images_and_the_four_txt_files(self, use_case_factory):
        """Requirements 9.6, 9.15: two ``images/...`` entries plus the four
        root ``.txt`` files, and nothing else.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(two_image_descriptors(), full_texts(), [])

        namelist, _ = read_zip(content)
        assert sorted(namelist) == sorted(
            ["images/facebook-post.jpeg", "images/instagram-story.jpeg"] + _ALL_TXT_NAMES
        )

    def test_images_are_written_in_the_order_received(self, use_case_factory):
        """Requirement 9.16: the image entries keep the order of the descriptor
        list, which is the order of appearance within ``media_formats``.
        """
        use_case, _, _, _, _ = use_case_factory()
        images = [
            make_image_descriptor("images/c.jpeg"),
            make_image_descriptor("images/a.jpeg"),
            make_image_descriptor("images/b.jpeg"),
        ]

        content = use_case._build_zip_package(images, empty_texts(), [])

        namelist, _ = read_zip(content)
        assert namelist == ["images/c.jpeg", "images/a.jpeg", "images/b.jpeg"]

    def test_image_binaries_are_stored_unchanged(self, use_case_factory):
        """Each entry carries its **own** binary, byte for byte: the packer
        neither transforms nor swaps the payloads it received.
        """
        use_case, _, _, _, _ = use_case_factory()
        images = two_image_descriptors()

        content = use_case._build_zip_package(images, full_texts(), [])

        _, contents = read_zip(content)
        for descriptor in images:
            assert contents[descriptor["entry_name"]] == descriptor["content"]

    # -- Requirement 9.1: in memory, ZIP_DEFLATED --------------------------

    def test_every_entry_is_deflated(self, use_case_factory):
        """Requirement 9.1: ``compress_type == zipfile.ZIP_DEFLATED`` on every
        single entry of ``infolist()``, images and texts alike.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )

        infolist = zip_infolist(content)
        assert len(infolist) == 7
        for info in infolist:
            assert info.compress_type == zipfile.ZIP_DEFLATED, (
                "entry {!r} was not stored with ZIP_DEFLATED".format(info.filename)
            )

    def test_the_result_is_bytes(self, use_case_factory):
        """Requirement 10.2: the return value is ``bytes``, the whole buffer
        read after closing the archive, and never empty.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(two_image_descriptors(), full_texts(), [])

        assert isinstance(content, bytes)
        assert len(content) > 0

    # -- Requirement 9.7: the writing convention of the .txt files ---------

    @pytest.mark.parametrize("category", _TEXT_CATEGORIES)
    def test_txt_content_is_the_texts_joined_by_newline(
        self, use_case_factory, category
    ):
        """Requirement 9.7: the decoded content of each ``.txt`` equals, by
        **exact** string comparison, its texts joined by ``'\\n'``.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = full_texts()

        content = use_case._build_zip_package([], texts, [])

        _, contents = read_zip(content)
        filename = _CATEGORY_FILENAMES[category]
        assert contents[filename].decode("utf-8") == "\n".join(texts[category])

    @pytest.mark.parametrize("category", _TEXT_CATEGORIES)
    def test_txt_content_has_no_leading_or_trailing_newline(
        self, use_case_factory, category
    ):
        """Requirement 9.7: ``'\\n'`` is a separator **between** elements, so
        there is no leading and no trailing newline.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = full_texts()

        content = use_case._build_zip_package([], texts, [])

        _, contents = read_zip(content)
        decoded = contents[_CATEGORY_FILENAMES[category]].decode("utf-8")
        assert not decoded.startswith("\n")
        assert not decoded.endswith("\n")
        assert decoded.count("\n") == len(texts[category]) - 1

    def test_multiple_texts_of_a_category_keep_their_order(self, use_case_factory):
        """Requirement 9.7: the order established by Requirements 8.3 and 8.9
        is preserved line by line.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = empty_texts()
        texts["primary_text"] = ["Primero", "Segundo", "Tercero"]

        content = use_case._build_zip_package([], texts, [])

        _, contents = read_zip(content)
        assert contents["primary_texts.txt"].decode("utf-8").split("\n") == [
            "Primero",
            "Segundo",
            "Tercero",
        ]

    def test_txt_content_is_encoded_in_utf8(self, use_case_factory):
        """Requirement 9.7: non-ASCII text survives the round trip, which is
        only true if the encoding is UTF-8 on the way in.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = empty_texts()
        texts["description"] = ["Descripción con ñ, acentos y emoji 🚀"]

        content = use_case._build_zip_package([], texts, [])

        _, contents = read_zip(content)
        assert (
            contents["descriptions.txt"].decode("utf-8")
            == "Descripción con ñ, acentos y emoji 🚀"
        )

    # -- Requirement 9.8: an empty category has no file --------------------

    @pytest.mark.parametrize("empty_category", _TEXT_CATEGORIES)
    def test_empty_category_has_no_file(self, use_case_factory, empty_category):
        """Requirement 9.8: the ``.txt`` of an empty Categoría_de_Texto is
        omitted, while the other three are still written.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = full_texts()
        texts[empty_category] = []

        content = use_case._build_zip_package([], texts, [])

        namelist, _ = read_zip(content)
        omitted = _CATEGORY_FILENAMES[empty_category]
        assert omitted not in namelist
        assert sorted(namelist) == sorted(
            name for name in _ALL_TXT_NAMES if name != omitted
        )

    def test_all_categories_empty_produce_no_txt_at_all(self, use_case_factory):
        """Requirement 9.8, taken to its limit: four empty categories produce
        zero ``.txt`` entries, leaving only the image entries.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            two_image_descriptors(), empty_texts(), []
        )

        namelist, _ = read_zip(content)
        assert namelist == ["images/facebook-post.jpeg", "images/instagram-story.jpeg"]

    # -- Requirement 9.15: images under images/, texts at the root ---------

    def test_no_txt_name_contains_a_slash(self, use_case_factory):
        """Requirement 9.15: the text entries live at the **root**, so none of
        their names contains the ``'/'`` character.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )

        namelist, _ = read_zip(content)
        text_names = [name for name in namelist if name.endswith(".txt")]
        assert sorted(text_names) == sorted(_ALL_TXT_NAMES + ["manifest.txt"])
        for name in text_names:
            assert "/" not in name

    def test_no_image_entry_lives_outside_the_prefix(self, use_case_factory):
        """Requirement 9.15: every image entry lives under ``images/`` and no
        text entry does — 0 text entries under the prefix.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )

        namelist, _ = read_zip(content)
        assert len(image_entries(namelist)) == 2
        assert [name for name in image_entries(namelist) if name.endswith(".txt")] == []
        non_image = [name for name in namelist if not name.startswith("images/")]
        assert sorted(non_image) == sorted(_ALL_TXT_NAMES + ["manifest.txt"])

    def test_no_explicit_directory_entry_is_created(self, use_case_factory):
        """The ``images/`` prefix is part of the entry names, not a directory
        entry of its own: nothing in ``namelist()`` ends with ``'/'``.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(two_image_descriptors(), full_texts(), [])

        namelist, _ = read_zip(content)
        assert [name for name in namelist if name.endswith("/")] == []

    # -- Requirement 9.13: the three sets empty ----------------------------

    def test_three_empty_sets_produce_a_valid_empty_zip(self, use_case_factory):
        """Requirement 9.13: with the THREE sets empty the result is still non
        empty ``bytes`` that open as a valid ZIP whose ``namelist()`` is the
        empty list.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package([], empty_texts(), [])

        assert isinstance(content, bytes)
        assert len(content) > 0
        namelist, contents = read_zip(content)
        assert namelist == []
        assert contents == {}

    def test_three_empty_sets_do_not_raise(self, use_case_factory):
        """Requirement 9.13: the empty package is a normal outcome, not an
        error — and it is reported through ``logger.info``, never
        ``logger.error``.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            content = use_case._build_zip_package([], empty_texts(), [])

        assert zipfile.is_zipfile(BytesIO(content))
        assert mock_logger.info.call_count == 1
        assert mock_logger.error.call_count == 0

    # -- Determinism -------------------------------------------------------

    def test_two_equivalent_invocations_are_deterministic(self, use_case_factory):
        """Two invocations with equivalent (freshly built, equal) arguments
        produce the same entry names in the same order, which is what makes the
        disambiguation of Requirement 9.5 and the exact list comparisons of
        Requirement 12 meaningful.
        """
        use_case, _, _, _, _ = use_case_factory()

        first = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )
        second = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )

        first_namelist, first_contents = read_zip(first)
        second_namelist, second_contents = read_zip(second)
        assert first_namelist == second_namelist
        assert first_contents == second_contents

    def test_the_input_collections_are_not_mutated(self, use_case_factory):
        """The packer is read-only towards its three arguments: mutating them
        would be an easy way to make a second invocation diverge from the
        first.
        """
        use_case, _, _, _, _ = use_case_factory()
        images = two_image_descriptors()
        texts = full_texts()
        not_included_ids = ["instagram-portrait"]

        use_case._build_zip_package(images, texts, not_included_ids)

        assert images == two_image_descriptors()
        assert texts == full_texts()
        assert not_included_ids == ["instagram-portrait"]

    # -- Requirements 9.9, 9.10: the manifest entry ------------------------

    def test_non_empty_not_included_ids_writes_the_manifest_at_the_root(
        self, use_case_factory
    ):
        """Requirements 9.9, 9.15: a non empty set of Assets_No_Incluidos adds
        ``manifest.txt`` **at the root** — its name holds no ``'/'``.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            two_image_descriptors(), full_texts(), ["instagram-portrait"]
        )

        namelist, _ = read_zip(content)
        assert "manifest.txt" in namelist
        assert "/" not in "manifest.txt"
        assert "images/manifest.txt" not in namelist

    def test_manifest_content_is_the_identifiers_joined_by_newline(
        self, use_case_factory
    ):
        """Requirement 9.10: the decoded content equals, by **exact** string
        comparison, the identifiers joined by ``'\\n'``, in the order of
        appearance within ``media_formats``.
        """
        use_case, _, _, _, _ = use_case_factory()
        not_included_ids = ["facebook-post", "instagram-portrait", "3"]

        content = use_case._build_zip_package([], empty_texts(), not_included_ids)

        _, contents = read_zip(content)
        assert contents["manifest.txt"].decode("utf-8") == "\n".join(not_included_ids)
        assert manifest_lines(contents) == not_included_ids

    def test_manifest_content_has_no_leading_or_trailing_newline(
        self, use_case_factory
    ):
        """Requirement 9.10: same convention as the category ``.txt`` files —
        ``'\\n'`` between elements, none after the last identifier.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            [], empty_texts(), ["facebook-post", "instagram-portrait"]
        )

        _, contents = read_zip(content)
        decoded = contents["manifest.txt"].decode("utf-8")
        assert not decoded.startswith("\n")
        assert not decoded.endswith("\n")
        assert decoded == "facebook-post\ninstagram-portrait"

    def test_a_single_not_included_id_produces_a_single_line(self, use_case_factory):
        """Requirement 9.10: one identifier means one line and zero ``'\\n'``
        characters.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package([], empty_texts(), ["instagram-story"])

        _, contents = read_zip(content)
        decoded = contents["manifest.txt"].decode("utf-8")
        assert decoded == "instagram-story"
        assert "\n" not in decoded

    # -- Requirement 9.11: no manifest when the set is empty ---------------

    def test_empty_not_included_ids_omits_the_manifest(self, use_case_factory):
        """Requirement 9.11: an empty set omits the entry entirely — its
        absence is what signals a **complete** package.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(two_image_descriptors(), full_texts(), [])

        namelist, contents = read_zip(content)
        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None

    def test_no_path_writes_an_empty_manifest(self, use_case_factory):
        """Requirement 9.11: writing and omitting are the two branches of the
        same falsy check, so a present-but-empty ``manifest.txt`` is
        unreachable.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package([], empty_texts(), [])

        namelist, _ = read_zip(content)
        assert namelist == []

    # -- Requirement 9.14: the manifest as the only entry ------------------

    def test_only_the_manifest_when_images_and_texts_are_empty(
        self, use_case_factory
    ):
        """Requirement 9.14: no images and no texts but a non empty set of
        Assets_No_Incluidos yields a package of exactly one entry.
        """
        use_case, _, _, _, _ = use_case_factory()

        content = use_case._build_zip_package(
            [], empty_texts(), ["facebook-post", "instagram-story"]
        )

        namelist, contents = read_zip(content)
        assert namelist == ["manifest.txt"]
        assert contents["manifest.txt"].decode("utf-8") == (
            "facebook-post\ninstagram-story"
        )

    def test_manifest_only_package_is_reported_and_does_not_raise(
        self, use_case_factory
    ):
        """Requirement 9.14: the manifest-only outcome is logged through
        ``logger.info`` and is not an error either.
        """
        use_case, _, _, _, _ = use_case_factory()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            content = use_case._build_zip_package([], empty_texts(), ["facebook-post"])

        assert zipfile.is_zipfile(BytesIO(content))
        assert mock_logger.info.call_count == 1
        assert mock_logger.error.call_count == 0

    # -- Requirement 9.12: manifest.txt is not a Categoría_de_Texto --------

    @pytest.mark.parametrize(
        "invented_key",
        [
            pytest.param("manifest", id="manifest"),
            pytest.param("manifest.txt", id="manifest_txt"),
        ],
    )
    def test_an_invented_manifest_key_in_texts_produces_no_entry(
        self, use_case_factory, invented_key
    ):
        """Requirement 9.12: the mapping of Requirement 9.6 produces 0 entries
        named ``manifest.txt``. A ``texts`` dict carrying an invented
        ``'manifest'`` / ``'manifest.txt'`` key is ignored, because only the
        four recognised Categorías_de_Texto are looked up.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = empty_texts()
        texts[invented_key] = ["instagram-portrait"]

        content = use_case._build_zip_package([], texts, [])

        namelist, _ = read_zip(content)
        assert namelist == []
        assert invented_key not in namelist
        assert "manifest.txt" not in namelist

    def test_the_manifest_is_derived_only_from_not_included_ids(
        self, use_case_factory
    ):
        """Requirement 9.12: when both an invented ``'manifest.txt'`` key and a
        real set of Assets_No_Incluidos are present, the single written entry
        holds the identifiers, never the text of the invented category.
        """
        use_case, _, _, _, _ = use_case_factory()
        texts = empty_texts()
        texts["manifest.txt"] = ["NO DEBE APARECER"]

        content = use_case._build_zip_package([], texts, ["instagram-portrait"])

        namelist, contents = read_zip(content)
        assert namelist == ["manifest.txt"]
        assert contents["manifest.txt"].decode("utf-8") == "instagram-portrait"


# ---------------------------------------------------------------------------
# End-to-end wiring of ``execute()`` (Requirements 12.2, 12.3)
# ---------------------------------------------------------------------------


class _DefaultSentinel:
    """Private sentinel meaning "the scenario builder supplies its default".

    It cannot be replaced by ``None``, because ``None`` is a **meaningful**
    configured value in several ``execute()`` scenarios: a repository double
    returning ``None`` is how a missing campaign, a missing creative or a
    missing campaign setup are simulated (Requirements 4.2, 5.2, 6.2), and a
    Redis double returning ``None`` is how the missing access token of
    Requirement 3.2 is simulated. Hence a sentinel distinct both from ``None``
    and from ``ABSENT``, whose meaning is "omit this key" rather than "use the
    default".

    Requirements: 12.3
    """

    def __repr__(self):
        return "DEFAULT"


DEFAULT = _DefaultSentinel()


# The simulated access token. It is deliberately a long, unmistakable string:
# Requirement 3.6 forbids it from reaching the Resultado_de_Exportación or the
# content of any ZIP entry, and ``TestTokenNotLeaked`` searches for exactly
# this value inside them.
SIMULATED_ACCESS_TOKEN = "simulated-facebook-access-token-value"


class ExportScenario:
    """A fully wired ``execute()`` scenario: the four repository doubles are
    already configured, and ``run()`` invokes ``execute()`` with Redis and the
    image download patched.

    Building and running are two separate steps on purpose. The failure
    scenarios of Requirements 12.9 and 12.10 need to assert **on the doubles**
    after the invocation raised, which is only possible if the caller owns the
    scenario object before the call::

        scenario = export_scenario(campaign=None)
        with pytest.raises(DataNotFoundException):
            scenario.run()
        assert scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 0

    The two context managers are exited before ``run()`` returns, which is
    harmless: ``MagicMock`` instances keep their recorded calls after
    ``patch`` restores the original names, so ``redis_client`` and
    ``requests_get`` remain assertable for the rest of the test.

    Requirements: 12.2, 12.3
    """

    def __init__(
        self,
        use_case,
        account_repo,
        campaign_repo,
        ad_channel_repo,
        campaign_publish_repo,
        payload,
        responses,
        access_token,
    ):
        self.use_case = use_case
        self.account_repo = account_repo
        self.campaign_repo = campaign_repo
        self.ad_channel_repo = ad_channel_repo
        self.campaign_publish_repo = campaign_publish_repo
        self.payload = payload
        self.responses = responses
        self.access_token = access_token
        self.redis_client = None
        self.requests_get = None
        self.result = None

    def run(self):
        """Invoke ``execute()`` once and return its Resultado_de_Exportación.

        Patch point #5 (Redis) is configured to hand back the access token as
        the ``bytes`` value ``_get_decoded_access_token`` expects, or ``None``
        when the scenario asked for a missing token. Patch point #6 (the image
        download) dispatches by URL through ``patch_image_download``.
        """
        with patch_redis_client() as mock_redis_client:
            mock_redis_client.get.return_value = (
                None if self.access_token is None
                else self.access_token.encode("utf-8")
            )
            with patch_image_download(self.responses) as mock_requests_get:
                self.redis_client = mock_redis_client
                self.requests_get = mock_requests_get
                self.result = self.use_case.execute(self.payload)

        return self.result

    def run_zip(self):
        """Invoke ``execute()`` and return the pair
        ``(namelist, {entry_name: bytes})`` of the resulting Paquete_ZIP.

        The vast majority of the end-to-end cases assert over the archive
        rather than over the envelope, so this saves a ``read_zip`` round trip
        in every one of them.
        """
        result = self.run()
        return read_zip(result["content"])


@pytest.fixture
def export_scenario(use_case_factory):
    """Fixture that builds a ready-to-run :class:`ExportScenario`.

    Every argument left untouched falls back to the happy-path default built by
    the corresponding builder, so a main-flow case is a bare
    ``export_scenario()``. Pass an explicit value to alter exactly one link of
    the chain, including ``None`` to simulate a repository (or Redis) that
    resolves nothing:

    * ``payload`` — the Payload_de_Exportación, default ``make_export_payload()``
    * ``account`` — return value of ``AccountRepository.get_by_email``
    * ``campaign`` — return value of ``get_by_id_brand_and_account``
    * ``ad_channel`` — return value of ``get_by_campaign_and_ad_channel_id``
    * ``campaign_setup`` — return value of ``get_by_campaign_id_and_channel_id``
    * ``responses`` — the per-URL outcome mapping of ``patch_image_download``
    * ``access_token`` — the simulated token, or ``None`` for a missing one
    * ``user_id`` — the constructor argument of the Caso_de_Uso

    Requirements: 12.2, 12.3
    """

    def _build(
        payload=DEFAULT,
        account=DEFAULT,
        campaign=DEFAULT,
        ad_channel=DEFAULT,
        campaign_setup=DEFAULT,
        responses=None,
        access_token=DEFAULT,
        user_id="user-1",
    ):
        (
            use_case,
            account_repo,
            campaign_repo,
            ad_channel_repo,
            campaign_publish_repo,
        ) = use_case_factory(user_id=user_id)

        account_repo.get_by_email.return_value = (
            make_account() if account is DEFAULT else account
        )
        campaign_repo.get_by_id_brand_and_account.return_value = (
            make_campaign() if campaign is DEFAULT else campaign
        )
        ad_channel_repo.get_by_campaign_and_ad_channel_id.return_value = (
            make_ad_channel() if ad_channel is DEFAULT else ad_channel
        )
        campaign_publish_repo.get_by_campaign_id_and_channel_id.return_value = (
            make_campaign_setup() if campaign_setup is DEFAULT else campaign_setup
        )

        return ExportScenario(
            use_case=use_case,
            account_repo=account_repo,
            campaign_repo=campaign_repo,
            ad_channel_repo=ad_channel_repo,
            campaign_publish_repo=campaign_publish_repo,
            payload=make_export_payload() if payload is DEFAULT else payload,
            responses=responses,
            access_token=(
                SIMULATED_ACCESS_TOKEN if access_token is DEFAULT else access_token
            ),
        )

    return _build


# The two Imágenes_Excedentes of the default Ad_Channel_de_Exportación:
# ``facebook-post`` and ``instagram-story``. ``instagram-portrait`` is the
# published asset (``pinned=True``) and is therefore not among them.
_MAIN_FLOW_SURPLUS_URLS = {
    "facebook-post": _VISUAL_URL_FACEBOOK_POST,
    "instagram-story": _VISUAL_URL_INSTAGRAM_STORY,
}

# The six entry names the main-flow fixture must produce, alphabetically
# sorted: two ``images/{id}.jpeg`` (the extension comes from the production
# ``visual_url`` values, Requirement 9.3) plus the four category files at the
# root. Written out literally rather than derived, so a change in the naming
# rules shows up here as a diff.
_MAIN_FLOW_EXPECTED_NAMES = [
    "ctas.txt",
    "descriptions.txt",
    "headlines.txt",
    "images/facebook-post.jpeg",
    "images/instagram-story.jpeg",
    "primary_texts.txt",
]

# The single Texto_Excedente (``id == 1``) of each of the four categories of
# the default fixture. The base assets (``id == 0``, "Cuerpo publicado en
# Meta", "Titulo publicado", "Descripcion publicada", "Comprar ahora") are
# published in Meta and must not appear.
_MAIN_FLOW_EXPECTED_TEXTS = {
    "primary_texts.txt": "Cuerpo alternativo A",
    "headlines.txt": "Titulo alterno",
    "descriptions.txt": "Descripcion alterna",
    "ctas.txt": "Mas informacion",
}


class TestMainFlow:
    """The main flow, end to end through ``execute()``.

    The fixture is the default Ad_Channel_de_Exportación: exactly two
    Imágenes_Excedentes that download **successfully** (``facebook-post`` and
    ``instagram-story``; ``instagram-portrait`` is the pinned published asset)
    and exactly one Texto_Excedente in each of the four Categorías_de_Texto.

    Since the set of Assets_No_Incluidos is empty for this fixture, the
    **exact** six-name comparison also proves ``manifest.txt`` is absent
    (Requirement 9.11) — no "six plus one" variant is needed.

    Requirements: 9.11, 12.4, 12.5, 12.6
    """

    def test_zip_namelist_matches_expected_six_entries(self, export_scenario):
        """Requirement 12.4: the alphabetically sorted entry names equal, by
        exact list comparison, the six expected names.

        Being an exact comparison it is simultaneously an inclusion check (the
        two images and the four category files are there) and an exclusion one:
        nothing else is, neither an entry for the pinned asset, nor one for a
        base text, nor ``manifest.txt``.
        """
        scenario = export_scenario()

        namelist, contents = scenario.run_zip()

        assert sorted(namelist) == _MAIN_FLOW_EXPECTED_NAMES
        # Requirement 9.11, made explicit: the absence of the manifest is what
        # signals a complete package.
        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None

    def test_txt_contents_match_expected_joined_texts(self, export_scenario):
        """Requirement 12.5: each of the four ``.txt`` files, decoded as UTF-8,
        equals by exact string comparison the expected Textos_Excedentes of its
        category, in the order of appearance of the fixture.

        One surplus per category means one line per file, so no leading and no
        trailing ``'\\n'`` at all.
        """
        scenario = export_scenario()

        _, contents = scenario.run_zip()

        for filename, expected_text in _MAIN_FLOW_EXPECTED_TEXTS.items():
            decoded = contents[filename].decode("utf-8")
            assert decoded == expected_text
            assert not decoded.startswith("\n")
            assert not decoded.endswith("\n")

    def test_txt_contents_exclude_the_published_base_texts(self, export_scenario):
        """Requirement 12.5, the exclusion half: the text of the ``id == 0``
        element of each category is the one published in Meta, so it appears in
        no entry of the Paquete_ZIP.
        """
        scenario = export_scenario()

        _, contents = scenario.run_zip()

        published_texts = [
            "Cuerpo publicado en Meta",
            "Titulo publicado",
            "Descripcion publicada",
            "Comprar ahora",
        ]
        for entry_content in contents.values():
            decoded = entry_content.decode("utf-8", errors="ignore")
            for published_text in published_texts:
                assert published_text not in decoded

    def test_image_bytes_match_downloaded_binaries(self, export_scenario):
        """Requirement 12.6: the binary of every ``images/...`` entry equals,
        **byte for byte**, the one the download double returned for its own
        ``visual_url``.

        The double serves a different payload per URL, so a content swap
        between the two entries breaks this assertion.
        """
        scenario = export_scenario()

        namelist, contents = scenario.run_zip()

        assert sorted(image_entries(namelist)) == [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ]
        for format_id, visual_url in _MAIN_FLOW_SURPLUS_URLS.items():
            entry_name = "images/{}.jpeg".format(format_id)
            assert contents[entry_name] == expected_image_binary(visual_url)

    def test_the_two_image_entries_hold_different_binaries(self, export_scenario):
        """Requirement 12.6, the premise of the previous case: the two entries
        do not share their content, otherwise a swap would be undetectable.
        """
        scenario = export_scenario()

        _, contents = scenario.run_zip()

        assert (
            contents["images/facebook-post.jpeg"]
            != contents["images/instagram-story.jpeg"]
        )

    def test_the_pinned_asset_binary_is_not_packaged(self, export_scenario):
        """Requirement 12.4: the published (``pinned=True``) asset produces no
        entry, and its binary is in none of them either.
        """
        scenario = export_scenario()

        namelist, contents = scenario.run_zip()

        assert "images/instagram-portrait.jpeg" not in namelist
        pinned_binary = expected_image_binary(_VISUAL_URL_INSTAGRAM_PORTRAIT)
        assert pinned_binary not in contents.values()

    def test_execute_returns_a_valid_zip_without_raising(self, export_scenario):
        """The envelope of the main flow: ``content`` holds non empty ``bytes``
        that are a readable ZIP archive.

        The detailed contract of the three keys belongs to
        ``TestExportResultContract``; what is pinned here is only that the main
        flow completes and yields a package that can actually be opened.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0
        assert zipfile.is_zipfile(BytesIO(result["content"]))


# ---------------------------------------------------------------------------
# Resultado_de_Exportación contract, collaborator invocations, empty package
# and token confinement (Requirements 3.6, 9.13, 10.1-10.4, 12.11, 12.15,
# 12.16, 12.17)
# ---------------------------------------------------------------------------


# The exact key set of the Resultado_de_Exportación (Requirement 10.1). It is a
# ``set`` and not a list because the criterion demands an exact **set**
# comparison: three keys, no more and no fewer, order irrelevant.
_EXPORT_RESULT_KEYS = {"content", "content_type", "filename"}


def expected_filename(
    campaign_name=_DEFAULT_CAMPAIGN_NAME,
    ad_set_name=_DEFAULT_AD_SET_NAME,
    ad_name=_DEFAULT_AD_NAME,
    channel_name=_DEFAULT_CHANNEL_NAME,
):
    """Build the expected ``filename`` out of the four **Nombres_Saneados**.

    Requirement 10.4 fixes the shape
    ``assets_{campaign_name}_{ad_set_name}_{ad_name}_{channel_name}.zip``,
    interpolating the four sanitised Nombres_de_Origen in that order — never an
    identifier of the Payload_de_Exportación, which is why this helper does not
    take the payload at all any more.

    Every argument left untouched falls back to the default source name of the
    builders, so a main-flow expectation is a bare ``expected_filename()``;
    pass ``''`` for a position whose Nombre_de_Origen is missing, which keeps
    its place in the template as two consecutive ``_`` (Requirement 10.13).
    The all-empty collapse to ``assets.zip`` of Requirement 10.14 is asserted
    against that literal instead, since it is not an interpolation of this
    template.

    Requirements: 10.4, 10.13
    """
    return "assets_{}_{}_{}_{}.zip".format(
        campaign_name, ad_set_name, ad_name, channel_name
    )


class TestExportResultContract:
    """The Resultado_de_Exportación envelope returned by ``execute()``.

    Requirement 10.1 replicates the **structural** pattern of
    ``GetBinaryObject.execute``, not its literal code (see OQ-2, CONFIRMED):
    what is verifiable is the three-key set ``content`` / ``content_type`` /
    ``filename``, whatever the value of each one.

    Requirements: 10.1, 10.2, 10.3, 10.4, 12.15
    """

    def test_result_keys_equal_the_expected_three_key_set(self, export_scenario):
        """Requirement 12.15: the key set equals, by exact comparison, the set
        of the three keys ``content``, ``content_type`` and ``filename``.

        Being an exact set comparison it also forbids extras: no ``ok``, no
        ``data``, no ``status``, and above all nothing carrying the campaign,
        the creative or the access token (Requirement 3.6).
        """
        scenario = export_scenario()

        result = scenario.run()

        assert isinstance(result, dict)
        assert set(result.keys()) == _EXPORT_RESULT_KEYS
        assert len(result) == 3

    def test_content_type_is_the_zip_mime_type(self, export_scenario):
        """Requirement 10.3: ``content_type`` is exactly the ``application/zip``
        string, compared by exact string equality.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert result["content_type"] == "application/zip"

    def test_filename_interpolates_the_four_source_names(self, export_scenario):
        """Requirements 10.4, 12.15: ``filename`` equals
        ``assets_{campaign_name}_{ad_set_name}_{ad_name}_{channel_name}.zip``
        built with the four Nombres_de_Origen of the fixture.

        Both the derived form and the literal are asserted: the first pins the
        template, the second pins the four names the builders actually supply,
        so a swap between two components fails here.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert result["filename"] == expected_filename()
        assert result["filename"] == (
            "assets_Black_Friday_AdSet_Prospecting_Ad_Retargeting_facebook.zip"
        )

    def test_filename_ignores_the_payload_identifiers_entirely(
        self, export_scenario
    ):
        """Requirements 10.4, 10.13, 12.15: the name is derived **only** from
        the four Nombres_de_Origen, so no identifier of the
        Payload_de_Exportación takes part in it.

        Five unmistakable identifiers go into the payload and the resulting
        filename is byte-identical to the main-flow one: the derivation cannot
        depend on any of them, and none of the five leaks into the value the
        resource declares in its ``Content-Disposition`` header.
        """
        payload = make_export_payload(
            campaign_id="CAMPAIGNVALUE",
            brand_id="BRANDVALUE",
            adset_id="ADSETVALUE",
            ad_id="ADVALUE",
            adchannel_id="ADCHANNELVALUE",
        )
        scenario = export_scenario(payload=payload)

        result = scenario.run()

        assert result["filename"] == expected_filename()
        for identifier in payload.values():
            assert str(identifier) not in result["filename"]

    def test_content_is_non_empty_bytes_that_open_as_a_zip(self, export_scenario):
        """Requirement 10.2: ``content`` holds the ``bytes`` of the whole
        Paquete_ZIP, readable as a ZIP archive.

        ``bytes`` and not ``BytesIO``, and not ``str`` either: the resource
        wraps this value in a ``BytesIO`` itself before handing it to
        ``send_file``.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0
        assert zipfile.is_zipfile(BytesIO(result["content"]))

    def test_the_three_keys_hold_the_expected_value_types(self, export_scenario):
        """Requirement 10.1: the envelope is fully typed — ``bytes`` for the
        package and ``str`` for the two metadata values.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert isinstance(result["content"], bytes)
        assert isinstance(result["content_type"], str)
        assert isinstance(result["filename"], str)


class TestRepositoryInvocations:
    """Exactly one invocation of each collaborator, with the arguments derived
    from the fixture, for the main flow of Requirement 12.4.

    The download double is the sixth collaborator: one invocation per
    Imagen_Excedente and not a single one more, which is also what makes
    Requirement 7.10 observable — the fixture always carries a perfectly
    downloadable ``preview_url``, so an implementation that read it would
    register a third call here.

    Requirements: 12.16
    """

    def test_account_repository_is_invoked_once_with_the_user_id(
        self, export_scenario
    ):
        """The account is resolved by the ``user_id`` of the constructor, never
        by a value taken from the payload.
        """
        scenario = export_scenario(user_id="user-42")

        scenario.run()

        scenario.account_repo.get_by_email.assert_called_once_with("user-42")

    def test_campaign_repository_is_invoked_once_with_id_brand_and_parent(
        self, export_scenario
    ):
        """Requirements 4.1, 12.16: a single
        ``get_by_id_brand_and_account(campaign_id, brand_id, parent_account)``,
        with the resolved Cuenta_Padre as third argument.

        The account fixture carries a ``parent_account`` identifier distinct
        both from its own ``id`` and from every payload identifier, so the value
        being passed can only come from the nested
        ``attributes.parent_account.data.id`` path (Requirement 3.7).
        """
        payload = make_export_payload()
        scenario = export_scenario(
            payload=payload,
            account=make_account(parent_account_id=42, account_id=1),
        )

        scenario.run()

        scenario.campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            payload["campaign_id"], payload["brand_id"], 42
        )

    def test_campaign_repository_falls_back_to_the_own_account_id(
        self, export_scenario
    ):
        """Requirement 3.8: with no ``parent_account`` node, the account's own
        ``id`` is the third argument of the campaign query.
        """
        payload = make_export_payload()
        scenario = export_scenario(account=make_account(account_id=13), payload=payload)

        scenario.run()

        scenario.campaign_repo.get_by_id_brand_and_account.assert_called_once_with(
            payload["campaign_id"], payload["brand_id"], 13
        )

    def test_ad_channel_repository_is_invoked_once_with_the_four_identifiers(
        self, export_scenario
    ):
        """Requirements 5.1, 5.7: a single
        ``get_by_campaign_and_ad_channel_id(campaign_id, adset_id, ad_id,
        adchannel_id, populate_names=True)``, with the four identifiers in that
        positional order, without transforming the values, and the
        name-population flag as the only keyword argument.
        """
        payload = make_export_payload()
        scenario = export_scenario(payload=payload)

        scenario.run()

        (
            scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id
            .assert_called_once_with(
                payload["campaign_id"],
                payload["adset_id"],
                payload["ad_id"],
                payload["adchannel_id"],
                populate_names=True,
            )
        )
        recorded_args, recorded_kwargs = (
            scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id.call_args
        )
        assert len(recorded_args) == 4
        assert recorded_kwargs == {"populate_names": True}

    def test_campaign_publish_repository_is_invoked_once_with_the_resolved_channel(
        self, export_scenario
    ):
        """Requirement 6.1: a single
        ``get_by_campaign_id_and_channel_id(campaign_id, channel_id)``, with the
        Channel_ID read from ``attributes.channel_ref.data.id``.

        The fixture uses a ``channel_ref`` identifier different from the default
        so the assertion pins the resolved value rather than a coincidence.
        """
        payload = make_export_payload()
        scenario = export_scenario(
            payload=payload, ad_channel=make_ad_channel(channel_ref_id=9)
        )

        scenario.run()

        (
            scenario.campaign_publish_repo.get_by_campaign_id_and_channel_id
            .assert_called_once_with(payload["campaign_id"], 9)
        )

    def test_each_repository_records_exactly_one_call_in_total(
        self, export_scenario
    ):
        """Requirement 12.16: one invocation of each of the four repositories,
        counting **every** method of the double, not just the expected one.

        ``mock_calls`` (unlike ``call_count`` on a single method) also catches an
        implementation that issued a second, different query on the same
        repository.
        """
        scenario = export_scenario()

        scenario.run()

        for repository in (
            scenario.account_repo,
            scenario.campaign_repo,
            scenario.ad_channel_repo,
            scenario.campaign_publish_repo,
        ):
            assert len(repository.mock_calls) == 1, repository.mock_calls

    def test_one_download_per_surplus_image(self, export_scenario):
        """Requirement 12.16: exactly one download invocation per
        Imagen_Excedente — two for the default fixture, whose third format is
        the pinned published asset.
        """
        scenario = export_scenario()

        scenario.run()

        assert scenario.requests_get.call_count == 2
        assert sorted(requested_urls(scenario.requests_get)) == sorted(
            _MAIN_FLOW_SURPLUS_URLS.values()
        )

    def test_the_pinned_and_auxiliary_urls_are_never_requested(
        self, export_scenario
    ):
        """Requirements 7.1, 7.10: neither the ``visual_url`` of the pinned
        asset nor the ``preview_url`` of any element is downloaded.
        """
        scenario = export_scenario()

        scenario.run()

        urls = requested_urls(scenario.requests_get)
        assert _VISUAL_URL_INSTAGRAM_PORTRAIT not in urls
        assert _PREVIEW_URL not in urls

    def test_every_download_uses_the_single_attempt_timeout(self, export_scenario):
        """Requirement 7.2: one attempt per image, with the timeout of the Caso
        de Uso, so no download can hang the export.
        """
        scenario = export_scenario()

        scenario.run()

        for recorded_call in scenario.requests_get.call_args_list:
            assert recorded_call[1]["timeout"] == (
                FacebookExportAssetsPostLaunchCampaignUseCase._IMAGE_DOWNLOAD_TIMEOUT
            )


# Two pinned formats and nothing else: zero surplus candidates, hence zero
# Imágenes_Excedentes **and** zero Assets_No_Incluidos (a pinned element is the
# published asset, never a not-included one).
def _only_pinned_media_formats():
    return [
        make_media_format(
            format_id="facebook-post",
            visual_url=_VISUAL_URL_FACEBOOK_POST,
            pinned=True,
        ),
        make_media_format(
            format_id="instagram-story",
            visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            pinned=True,
        ),
    ]


# Four Categorías_de_Texto holding only the published base asset (``id == 0``),
# so no Texto_Excedente survives the filter of Requirement 8.2.
def _only_base_channel_attributes():
    return [
        make_channel_attribute(
            name=name,
            payloads=[make_text_payload(payload_id=0, text=text)],
        )
        for name, text in (
            ("primary_text", "Cuerpo publicado en Meta"),
            ("headline", "Titulo publicado"),
            ("description", "Descripcion publicada"),
            ("cta", "Comprar ahora"),
        )
    ]


# The two ways of having **zero** surplus candidates required by Requirement
# 12.11. Both leave the THREE sets empty, which is what keeps
# ``namelist() == []`` correct per Requirement 9.13; a fixture whose candidates
# merely failed to download would yield ``['manifest.txt']`` instead
# (Requirement 9.14), a different outcome covered elsewhere.
_EMPTY_PACKAGE_AD_CHANNELS = [
    pytest.param(
        lambda: make_ad_channel(
            media_formats=_only_pinned_media_formats(),
            channel_attributes=_only_base_channel_attributes(),
        ),
        id="all_formats_pinned_and_only_base_texts",
    ),
    pytest.param(
        lambda: make_ad_channel(media_formats=ABSENT, channel_attributes=ABSENT),
        id="no_media_formats_and_no_channel_attributes",
    ),
    pytest.param(
        lambda: make_ad_channel(media_formats=[], channel_attributes=[]),
        id="both_lists_empty",
    ),
]


class TestEmptyPackage:
    """The empty Paquete_ZIP: a valid archive with **no entries at all**.

    The fixtures deliberately have **zero surplus candidates** and zero
    Textos_Excedentes, so the three sets (Imágenes_Excedentes,
    Textos_Excedentes and Assets_No_Incluidos) are empty and Requirement 9.13
    applies: a valid ZIP whose ``namelist()`` is the empty list, never a JSON
    response and never an error.

    Requirements: 9.13, 10.2, 12.11
    """

    @pytest.mark.parametrize("build_ad_channel", _EMPTY_PACKAGE_AD_CHANNELS)
    def test_execute_returns_a_zip_with_no_entries(
        self, export_scenario, build_ad_channel
    ):
        """Requirement 12.11: ``execute()`` does not raise, ``content`` is a non
        empty ``bytes`` sequence that opens as a valid ZIP, and its entry name
        list equals the empty list.
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        result = scenario.run()

        assert set(result.keys()) == _EXPORT_RESULT_KEYS
        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0
        assert zipfile.is_zipfile(BytesIO(result["content"]))

        namelist, contents = read_zip(result["content"])
        assert namelist == []
        assert contents == {}

    @pytest.mark.parametrize("build_ad_channel", _EMPTY_PACKAGE_AD_CHANNELS)
    def test_the_empty_package_carries_no_manifest(
        self, export_scenario, build_ad_channel
    ):
        """Requirement 9.11 as the complement of 9.13: with zero
        Assets_No_Incluidos the manifest is **absent**, which is precisely what
        signals a complete (if empty) package rather than an incomplete one.
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        namelist, contents = scenario.run_zip()

        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None

    @pytest.mark.parametrize("build_ad_channel", _EMPTY_PACKAGE_AD_CHANNELS)
    def test_the_empty_package_triggers_no_download(
        self, export_scenario, build_ad_channel
    ):
        """The premise of the previous cases: with zero surplus candidates there
        is nothing to download, so no candidate could have silently failed and
        produced a manifest instead.
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        scenario.run()

        assert scenario.requests_get.call_count == 0

    def test_the_envelope_of_an_empty_package_is_the_regular_one(
        self, export_scenario
    ):
        """Requirements 10.3, 10.4: an empty package is not a special case for
        the envelope — same ``content_type`` and same ``filename`` as a full
        one, so the resource still answers with a ZIP download.

        The four Nombres_de_Origen are those of the builders, untouched by the
        emptiness of the archive: the name of the package describes the
        hierarchy it belongs to, not its contents.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel(media_formats=[], channel_attributes=[]),
        )

        result = scenario.run()

        assert result["content_type"] == "application/zip"
        assert result["filename"] == expected_filename()


class TestTokenNotLeaked:
    """Confinement of the Meta access token (Requirement 3.6).

    The token is resolved by ``_get_decoded_access_token`` as an authentication
    gate and its value is discarded right away: it must appear neither in the
    Resultado_de_Exportación nor in the content of **any** entry of the
    Paquete_ZIP.

    Requirements: 3.6, 12.17
    """

    def test_the_token_is_absent_from_the_export_result(self, export_scenario):
        """Requirement 12.17: the simulated token value is in none of the three
        values of the envelope, neither in the metadata strings nor in the
        package bytes.
        """
        scenario = export_scenario()

        result = scenario.run()

        # Premise: the token really was handed over by the Redis double, so the
        # assertions below are not vacuously true.
        assert scenario.redis_client.get.call_count == 1

        assert SIMULATED_ACCESS_TOKEN not in result["filename"]
        assert SIMULATED_ACCESS_TOKEN not in result["content_type"]
        assert SIMULATED_ACCESS_TOKEN.encode("utf-8") not in result["content"]

    def test_the_token_is_absent_from_every_zip_entry(self, export_scenario):
        """Requirement 12.17: no entry of the Paquete_ZIP contains the token,
        neither an ``images/...`` binary nor a category ``.txt``.
        """
        scenario = export_scenario()

        namelist, contents = scenario.run_zip()

        # Premise: there is something to search through.
        assert len(namelist) == 6
        for entry_name, entry_content in contents.items():
            assert SIMULATED_ACCESS_TOKEN.encode("utf-8") not in entry_content, entry_name
            decoded = entry_content.decode("utf-8", errors="ignore")
            assert SIMULATED_ACCESS_TOKEN not in decoded, entry_name

    def test_the_token_is_absent_from_the_manifest_entry(self, export_scenario):
        """Requirements 3.6, 9.10: the incomplete-package outcome adds one more
        entry written by the Caso_de_Uso itself, and the token is not in it
        either.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel_with_formats(make_three_surplus_formats()),
            responses={_VISUAL_URL_INSTAGRAM_PORTRAIT: 404},
        )

        namelist, contents = scenario.run_zip()

        # Premise: this fixture really produced a manifest.
        assert "manifest.txt" in namelist
        assert manifest_lines(contents) == ["beta"]
        assert SIMULATED_ACCESS_TOKEN.encode("utf-8") not in contents["manifest.txt"]

    def test_the_token_is_absent_from_the_zip_container_bytes(self, export_scenario):
        """Requirement 3.6 down to the container level: the token is not in the
        raw archive bytes either, which also covers the entry **names** and the
        ZIP metadata, not just the entry contents.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert SIMULATED_ACCESS_TOKEN.encode("utf-8") not in result["content"]
        assert b"facebook_access_token" not in result["content"]


# ---------------------------------------------------------------------------
# Pre-validation failures and short circuits, end to end through ``execute()``
# (Requirements 12.9, 12.10)
# ---------------------------------------------------------------------------


# The eight failure scenarios of the pre-validation chain, one per link, in the
# order in which ``execute()`` evaluates them (Requirement 6.8). Each entry is a
# callable returning the ``export_scenario`` keyword arguments that break
# exactly that link, plus the exception type ``execute()`` must raise.
#
# Each builder is a callable rather than a literal dict so that every
# parametrized case gets a **freshly built** fixture, per Requirement 12.3.
_PRE_VALIDATION_FAILURES = [
    pytest.param(
        lambda: {"payload": make_export_payload(campaign_id=ABSENT)},
        ParametersNotFoundException,
        id="incomplete_payload",
    ),
    pytest.param(
        lambda: {"access_token": None},
        NotAccessException,
        id="missing_access_token",
    ),
    pytest.param(
        lambda: {"account": None},
        DataNotFoundException,
        id="account_not_found",
    ),
    pytest.param(
        lambda: {"campaign": None},
        DataNotFoundException,
        id="campaign_not_found",
    ),
    pytest.param(
        lambda: {"ad_channel": None},
        DataNotFoundException,
        id="ad_channel_not_found",
    ),
    pytest.param(
        lambda: {"campaign_setup": None},
        DataNotFoundException,
        id="campaign_setup_not_found",
    ),
    pytest.param(
        lambda: {"campaign_setup": make_campaign_setup(meta_published=False)},
        IncorrectValidationException,
        id="meta_published_not_true",
    ),
    pytest.param(
        lambda: {
            "campaign_setup": make_campaign_setup(
                meta_campaign_mode=CreativeType.DYNAMIC.value
            )
        },
        IncorrectValidationException,
        id="meta_campaign_mode_dynamic",
    ),
]


class TestPreValidationFailures:
    """The eight failure scenarios of the pre-validation chain, exercised
    through ``execute()``.

    Only the exception **type** is asserted, via ``assert_exception_type`` and
    never against the message text: Requirement 12.9 forbids comparing it,
    because the four exceptions of this flow carry human-facing wording that
    must stay free to change.

    The second assertion of every scenario is the one that makes the abort
    semantics observable: zero invocations of the download double. A
    pre-validation that raised *after* starting to fetch binaries would satisfy
    the type assertion and still be wrong.

    Requirements: 12.9
    """

    @pytest.mark.parametrize(
        "build_kwargs, expected_exception", _PRE_VALIDATION_FAILURES
    )
    def test_execute_raises_the_expected_exception_type(
        self, export_scenario, build_kwargs, expected_exception
    ):
        """Requirement 12.9: each broken link makes ``execute()`` raise exactly
        its own exception type, checked by identity of the type and not by
        ``isinstance``, so a broader ancestor would not pass either.
        """
        scenario = export_scenario(**build_kwargs())

        with pytest.raises(expected_exception) as exc_info:
            scenario.run()

        assert_exception_type(exc_info, expected_exception)

    @pytest.mark.parametrize(
        "build_kwargs, expected_exception", _PRE_VALIDATION_FAILURES
    )
    def test_no_binary_is_downloaded_when_a_pre_validation_fails(
        self, export_scenario, build_kwargs, expected_exception
    ):
        """Requirement 12.9: the download double records exactly zero
        invocations in all eight scenarios.

        The default Ad_Channel_de_Exportación of the fixture carries two
        perfectly downloadable Imágenes_Excedentes, so a flow that reached the
        collection step would register two calls here. Note the double stays
        assertable after ``run()`` unwound: ``MagicMock`` keeps its recorded
        calls once ``patch`` has restored the original name.
        """
        scenario = export_scenario(**build_kwargs())

        with pytest.raises(expected_exception):
            scenario.run()

        assert scenario.requests_get.call_count == 0
        assert scenario.requests_get.mock_calls == []

    @pytest.mark.parametrize(
        "build_kwargs, expected_exception", _PRE_VALIDATION_FAILURES
    )
    def test_no_export_result_is_produced_when_a_pre_validation_fails(
        self, export_scenario, build_kwargs, expected_exception
    ):
        """Requirement 12.9, the complement of the type assertion: the failure
        propagates instead of degrading into a Resultado_de_Exportación, so no
        empty ZIP is ever handed back for a rejected request.
        """
        scenario = export_scenario(**build_kwargs())

        with pytest.raises(expected_exception):
            scenario.run()

        assert scenario.result is None


class TestPreValidationShortCircuits:
    """The three short circuits of Requirement 12.10: a failing link stops the
    chain, so the collaborators of the **later** links are never queried.

    This is what distinguishes a genuinely sequential chain from one that
    resolves everything up front and validates afterwards. Both would raise the
    same exception type; only the first leaves the downstream doubles
    untouched.

    Every case also pins the *premise* — that the failing link itself was
    actually reached and queried — so a regression that skipped the whole chain
    could not pass by accident.

    Requirements: 12.10
    """

    def test_a_failing_campaign_stops_before_the_ad_channel_query(
        self, export_scenario
    ):
        """Requirements 4.2, 12.10: when the campaign does not resolve,
        ``AdChannelRepository.get_by_campaign_and_ad_channel_id`` records zero
        invocations.
        """
        scenario = export_scenario(campaign=None)

        with pytest.raises(DataNotFoundException) as exc_info:
            scenario.run()

        assert_exception_type(exc_info, DataNotFoundException)
        # Premise: the campaign link was reached and queried exactly once.
        assert scenario.campaign_repo.get_by_id_brand_and_account.call_count == 1
        # The short circuit itself.
        assert (
            scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 0
        )
        assert scenario.ad_channel_repo.mock_calls == []
        # And nothing downstream of it either.
        assert scenario.campaign_publish_repo.mock_calls == []
        assert scenario.requests_get.call_count == 0

    def test_a_failing_ad_channel_stops_before_the_campaign_setup_query(
        self, export_scenario
    ):
        """Requirements 5.2, 12.10: when the Ad_Channel_de_Exportación does not
        resolve, ``CampaignChannelPublishRepository.get_by_campaign_id_and_channel_id``
        records zero invocations.
        """
        scenario = export_scenario(ad_channel=None)

        with pytest.raises(DataNotFoundException) as exc_info:
            scenario.run()

        assert_exception_type(exc_info, DataNotFoundException)
        # Premise: the ad-channel link was reached and queried exactly once.
        assert (
            scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id.call_count == 1
        )
        # The short circuit itself.
        assert (
            scenario.campaign_publish_repo
            .get_by_campaign_id_and_channel_id.call_count == 0
        )
        assert scenario.campaign_publish_repo.mock_calls == []
        assert scenario.requests_get.call_count == 0

    def test_a_missing_token_stops_before_the_account_and_campaign_queries(
        self, export_scenario
    ):
        """Requirements 3.2, 12.10: when the token is absent from Redis, the
        ``AccountRepository`` and ``CampaignRepository`` doubles record zero
        invocations.

        ``mock_calls`` on the repository object, rather than ``call_count`` on a
        single method, so a call to *any* method of either double would be
        caught.
        """
        scenario = export_scenario(access_token=None)

        with pytest.raises(NotAccessException) as exc_info:
            scenario.run()

        assert_exception_type(exc_info, NotAccessException)
        # Premise: the token gate was reached, so Redis really was consulted.
        assert scenario.redis_client.get.call_count == 1
        # The short circuit itself.
        assert scenario.account_repo.mock_calls == []
        assert scenario.account_repo.get_by_email.call_count == 0
        assert scenario.campaign_repo.mock_calls == []
        assert scenario.campaign_repo.get_by_id_brand_and_account.call_count == 0
        # And nothing downstream of them either.
        assert scenario.ad_channel_repo.mock_calls == []
        assert scenario.campaign_publish_repo.mock_calls == []
        assert scenario.requests_get.call_count == 0

    def test_an_incomplete_payload_stops_before_every_collaborator(
        self, export_scenario
    ):
        """Requirements 2.4, 12.10 as the first link of the chain: an invalid
        Payload_de_Exportación is rejected before Redis, before the four
        repositories and before any download.
        """
        scenario = export_scenario(payload=make_export_payload(adchannel_id=ABSENT))

        with pytest.raises(ParametersNotFoundException) as exc_info:
            scenario.run()

        assert_exception_type(exc_info, ParametersNotFoundException)
        assert scenario.redis_client.mock_calls == []
        assert scenario.account_repo.mock_calls == []
        assert scenario.campaign_repo.mock_calls == []
        assert scenario.ad_channel_repo.mock_calls == []
        assert scenario.campaign_publish_repo.mock_calls == []
        assert scenario.requests_get.call_count == 0


# ---------------------------------------------------------------------------
# Degraded input structures, end to end through execute()
# (Requirements 9.9, 9.11, 12.12)
# ---------------------------------------------------------------------------
#
# One factory per degraded fixture. They are callables, not module level
# values, so every parametrized case builds its own fresh structure and no
# case can leak a mutation into another (Requirement 12.3).
#
# ``make_ad_channel(media_formats=None)`` means "use the default list", never
# "the key is present with value ``None``": the present-but-``None`` shape is
# built by mutating the freshly returned record, which is exactly what the
# builder's docstring invites callers to do. The same applies to
# ``channel_attributes`` and to the ``payloads`` of a Atributo_de_Canal.


def _degraded_media_formats_absent():
    """Requirement 7.7: the ``media_formats`` key is missing from
    ``attributes`` altogether.
    """
    return make_ad_channel(media_formats=ABSENT)


def _degraded_media_formats_none():
    """Requirement 7.7: ``media_formats`` is present with the value ``None``,
    which the ``ABSENT`` sentinel deliberately cannot express.
    """
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["media_formats"] = None
    return ad_channel


def _degraded_media_formats_non_list_dict():
    """Requirement 7.7: ``media_formats`` is a ``dict`` wrapping what looks
    like a perfectly usable list of formats.

    The two formats inside are unreachable: a non-``list`` value is treated as
    an empty set of Imágenes_Excedentes **and** as an empty set of
    Assets_No_Incluidos, so they are neither downloaded nor reported.
    """
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["media_formats"] = {
        "formats": [
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
            ),
            make_media_format(
                format_id="instagram-story",
                visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            ),
        ]
    }
    return ad_channel


def _degraded_media_formats_non_list_str():
    """Requirement 7.7: ``media_formats`` is a ``str``.

    A ``str`` is iterable, so an implementation that iterated without checking
    the type would walk its characters instead of failing the type check.
    """
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["media_formats"] = "facebook-post,instagram-story"
    return ad_channel


def _degraded_media_format_element_non_dict():
    """Requirement 7.8: three of the five elements of ``media_formats`` are not
    ``dict`` instances, interleaved with two usable formats.

    The two usable ones are exported; the three others are skipped without
    logging an error and, not being surplus candidates, are **not**
    Assets_No_Incluidos either.
    """
    return make_ad_channel(
        media_formats=[
            "not-a-dict",
            make_media_format(
                format_id="facebook-post",
                visual_url=_VISUAL_URL_FACEBOOK_POST,
            ),
            None,
            7,
            make_media_format(
                format_id="instagram-story",
                visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            ),
        ]
    )


def _degraded_every_media_format_element_non_dict():
    """Requirement 7.8 taken to its limit: no element of ``media_formats`` is a
    ``dict``, so the list yields zero images and zero Assets_No_Incluidos.
    """
    return make_ad_channel(media_formats=["not-a-dict", None, 7, ["nested"]])


def _degraded_payload_element_non_dict():
    """Requirement 8.5: three of the four elements of the ``payloads`` list of
    the ``primary_text`` attribute are not ``dict`` instances.

    The surviving Texto_Excedente still produces ``primary_texts.txt``, and the
    ``headline`` attribute is intact so that the case also pins that the
    degradation of one category does not spill over into another.
    """
    return make_ad_channel(
        channel_attributes=[
            make_channel_attribute(
                name="primary_text",
                payloads=[
                    "not-a-dict",
                    None,
                    7,
                    make_text_payload(payload_id=1, text="Cuerpo alternativo A"),
                ],
            ),
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
        ]
    )


def _degraded_every_payload_element_non_dict():
    """Requirement 8.5 taken to its limit: no element of the ``payloads`` list
    of ``primary_text`` is a ``dict``, so that category ends up empty and its
    ``.txt`` file is omitted (Requirement 9.8).
    """
    return make_ad_channel(
        channel_attributes=[
            make_channel_attribute(
                name="primary_text",
                payloads=["not-a-dict", None, 7, ["nested"]],
            ),
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
        ]
    )


def _degraded_channel_attributes_absent():
    """Requirement 8.6: the ``channel_attributes`` key is missing from
    ``attributes`` altogether, so the four Categorías_de_Texto are empty.
    """
    return make_ad_channel(channel_attributes=ABSENT)


def _degraded_channel_attributes_none():
    """Requirement 8.6: ``channel_attributes`` is present with the value
    ``None``.
    """
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["channel_attributes"] = None
    return ad_channel


def _degraded_channel_attributes_non_list_dict():
    """Requirement 8.6: ``channel_attributes`` is a ``dict`` keyed by category
    name instead of a list of attributes.

    Its contents are unreachable: a non-``list`` value means every category is
    empty, so not a single ``.txt`` file is written.
    """
    ad_channel = make_ad_channel()
    ad_channel["attributes"]["channel_attributes"] = {
        "primary_text": ["Cuerpo alternativo A"],
        "headline": ["Titulo alterno"],
    }
    return ad_channel


def _degraded_payloads_absent():
    """Requirement 8.7: the ``payloads`` key of the ``primary_text`` attribute
    is missing, so that category is empty while ``headline`` is unaffected.
    """
    return make_ad_channel(
        channel_attributes=[
            make_channel_attribute(name="primary_text", payloads=ABSENT),
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
        ]
    )


def _degraded_payloads_none():
    """Requirement 8.7: the ``payloads`` key of the ``primary_text`` attribute
    is present with the value ``None``.

    Built by mutation, since ``make_channel_attribute(payloads=None)`` means
    "use the default list", not "the key holds ``None``".
    """
    primary_text = make_channel_attribute(name="primary_text")
    primary_text["payloads"] = None
    return make_ad_channel(
        channel_attributes=[
            primary_text,
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
        ]
    )


def _degraded_payloads_non_list():
    """Requirement 8.7: the ``payloads`` key of the ``primary_text`` attribute
    holds a ``dict`` instead of a list.
    """
    primary_text = make_channel_attribute(name="primary_text")
    primary_text["payloads"] = {
        "0": "Cuerpo publicado en Meta",
        "1": "Cuerpo alternativo A",
    }
    return make_ad_channel(
        channel_attributes=[
            primary_text,
            make_channel_attribute(
                name="headline",
                payloads=[
                    make_text_payload(payload_id=0, text="Titulo publicado"),
                    make_text_payload(payload_id=1, text="Titulo alterno"),
                ],
            ),
        ]
    )


# The five degraded fixtures of Requirements 7.7, 7.8, 8.5, 8.6 and 8.7, each
# paired with the alphabetically sorted list of entry names its Paquete_ZIP
# must hold.
#
# Every expected list is written out **literally**, never derived from the
# fixture nor assembled from shared constants: deriving it would let the same
# misreading of the input produce both the actual and the expected value, and
# the case would pass while the package was wrong.
#
# None of the fifteen lists contains ``manifest.txt``, and that is a
# substantive claim rather than an oversight (Requirements 9.9, 9.11):
#
# * a non-``list`` (or absent) ``media_formats`` produces no manifest because
#   Requirement 7.7 orders **both** sets — Imágenes_Excedentes and
#   Assets_No_Incluidos — to be treated as empty, even when the unusable value
#   visibly wraps formats that would otherwise have been candidates;
# * an element of ``media_formats`` that is not a ``dict`` produces no manifest
#   entry for that element because it is not a surplus candidate at all, so
#   there is nothing the user was expecting and nothing to report;
# * the three ``channel_attributes``/``payloads`` degradations only ever empty
#   text categories, and the manifest is derived exclusively from
#   Assets_No_Incluidos (Requirement 9.12), so no text degradation can add it.
_DEGRADED_CASES = [
    # Requirement 7.7 — media_formats absent, None or non-list. Zero images,
    # the four category files, and NO manifest.
    pytest.param(
        _degraded_media_formats_absent,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "primary_texts.txt",
        ],
        id="media_formats-absent",
    ),
    pytest.param(
        _degraded_media_formats_none,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "primary_texts.txt",
        ],
        id="media_formats-none",
    ),
    pytest.param(
        _degraded_media_formats_non_list_dict,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "primary_texts.txt",
        ],
        id="media_formats-non-list-dict",
    ),
    pytest.param(
        _degraded_media_formats_non_list_str,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "primary_texts.txt",
        ],
        id="media_formats-non-list-str",
    ),
    # Requirement 7.8 — a non-dict element of media_formats. The two usable
    # formats are exported and NO manifest is written.
    pytest.param(
        _degraded_media_format_element_non_dict,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
            "primary_texts.txt",
        ],
        id="media_formats-element-non-dict",
    ),
    pytest.param(
        _degraded_every_media_format_element_non_dict,
        [
            "ctas.txt",
            "descriptions.txt",
            "headlines.txt",
            "primary_texts.txt",
        ],
        id="media_formats-every-element-non-dict",
    ),
    # Requirement 8.5 — a non-dict element of payloads. The two default
    # Imágenes_Excedentes are exported; primary_texts.txt survives with its
    # single usable text, and disappears when no element is usable.
    pytest.param(
        _degraded_payload_element_non_dict,
        [
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
            "primary_texts.txt",
        ],
        id="payloads-element-non-dict",
    ),
    pytest.param(
        _degraded_every_payload_element_non_dict,
        [
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="payloads-every-element-non-dict",
    ),
    # Requirement 8.6 — channel_attributes absent, None or non-list. The two
    # images, zero text files, NO manifest.
    pytest.param(
        _degraded_channel_attributes_absent,
        [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="channel_attributes-absent",
    ),
    pytest.param(
        _degraded_channel_attributes_none,
        [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="channel_attributes-none",
    ),
    pytest.param(
        _degraded_channel_attributes_non_list_dict,
        [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="channel_attributes-non-list-dict",
    ),
    # Requirement 8.7 — payloads absent, None or non-list on one attribute.
    # That single category is empty; headline is untouched.
    pytest.param(
        _degraded_payloads_absent,
        [
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="payloads-absent",
    ),
    pytest.param(
        _degraded_payloads_none,
        [
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="payloads-none",
    ),
    pytest.param(
        _degraded_payloads_non_list,
        [
            "headlines.txt",
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ],
        id="payloads-non-list",
    ),
]


class TestDegradedStructures:
    """``execute()`` over the five degraded input structures of Requirements
    7.7, 7.8, 8.5, 8.6 and 8.7.

    The contract under test is a total one: a malformed Ad_Channel_de_
    Exportación degrades the **contents** of the Paquete_ZIP and never the
    outcome of the call. Every case must return a Resultado_de_Exportación
    without raising, and the entry names of its archive must equal the list
    declared for that fixture — including whether ``manifest.txt`` is part of
    it, which Requirements 9.9 and 9.11 decide fixture by fixture.

    Requirements: 9.9, 9.11, 12.12
    """

    @pytest.mark.parametrize("build_ad_channel, expected_namelist", _DEGRADED_CASES)
    def test_execute_returns_an_export_result_without_raising(
        self, export_scenario, build_ad_channel, expected_namelist
    ):
        """Requirement 12.12, first half: the degraded fixture yields a
        Resultado_de_Exportación with exactly the three contract keys, and no
        exception escapes ``execute()``.

        The call is made outside any ``pytest.raises``, so any exception raised
        by the degraded structure surfaces as an error of this very test.
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        result = scenario.run()

        assert set(result.keys()) == {"content", "content_type", "filename"}
        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0
        assert result["content_type"] == "application/zip"
        # The degradation affects ``media_formats`` and ``channel_attributes``,
        # never the four Nombres_de_Origen, so the name stays the main-flow one.
        assert result["filename"] == expected_filename()

    @pytest.mark.parametrize("build_ad_channel, expected_namelist", _DEGRADED_CASES)
    def test_zip_namelist_equals_the_declared_expectation(
        self, export_scenario, build_ad_channel, expected_namelist
    ):
        """Requirement 12.12, second half: the alphabetically sorted entry names
        equal, by exact list comparison, the list declared for this fixture.

        Being exact, the comparison is at once an inclusion check (what the
        degraded structure could still contribute is there) and an exclusion one
        (what it could not is absent, ``manifest.txt`` included).
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        namelist, _ = scenario.run_zip()

        assert sorted(namelist) == expected_namelist

    @pytest.mark.parametrize("build_ad_channel, expected_namelist", _DEGRADED_CASES)
    def test_manifest_presence_matches_the_declared_expectation(
        self, export_scenario, build_ad_channel, expected_namelist
    ):
        """Requirements 9.9, 9.11: the presence of ``manifest.txt`` is decided
        by the declared expectation of the fixture, never by the shape of the
        degraded input.

        Stated as an equality between two booleans rather than as a bare
        ``not in``, so the day a degraded fixture is added whose expectation
        *does* include the manifest, this case keeps checking the right thing.
        """
        scenario = export_scenario(ad_channel=build_ad_channel())

        namelist, contents = scenario.run_zip()

        expects_manifest = "manifest.txt" in expected_namelist
        assert ("manifest.txt" in namelist) is expects_manifest
        if expects_manifest:
            assert manifest_lines(contents) is not None
        else:
            # An absent manifest signals a complete package; a present but
            # empty one would signal the opposite, hence the explicit ``None``.
            assert manifest_lines(contents) is None

    def test_non_list_media_formats_reports_no_not_included_asset(
        self, export_scenario
    ):
        """Requirements 7.7, 9.11, the trickiest of the five: ``media_formats``
        is a ``dict`` **wrapping two otherwise usable formats**, and the package
        still comes out without ``manifest.txt``.

        Requirement 7.7 orders both sets to be treated as empty, so those two
        formats are not surplus candidates: nothing is downloaded and nothing is
        reported as missing. Reporting them would wrongly tell the user that two
        assets they were expecting failed to arrive.
        """
        scenario = export_scenario(ad_channel=_degraded_media_formats_non_list_dict())

        namelist, contents = scenario.run_zip()

        assert image_entries(namelist) == []
        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None
        # Nothing was even attempted: zero downloads, so neither of the two
        # unreachable formats was treated as a candidate.
        assert scenario.requests_get.call_count == 0

    def test_non_dict_media_format_element_is_not_reported_as_not_included(
        self, export_scenario
    ):
        """Requirements 7.8, 9.11: the three non-``dict`` elements interleaved
        among the usable formats produce neither an ``images/...`` entry nor a
        line in ``manifest.txt``, because they are not surplus candidates.

        The download double records exactly two invocations, one per usable
        format, which pins that the skipping happened *before* any attempt.
        """
        scenario = export_scenario(ad_channel=_degraded_media_format_element_non_dict())

        namelist, contents = scenario.run_zip()

        assert sorted(image_entries(namelist)) == [
            "images/facebook-post.jpeg",
            "images/instagram-story.jpeg",
        ]
        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None
        assert scenario.requests_get.call_count == 2

    def test_surviving_texts_of_a_degraded_payloads_list_are_intact(
        self, export_scenario
    ):
        """Requirements 8.5, 8.7: degrading a ``payloads`` list empties or
        thins that one category without altering the value of the
        Textos_Excedentes that survive it.

        Otherwise a case could pass its namelist comparison while writing the
        wrong text, or the text of the wrong category, into the surviving file.
        """
        scenario = export_scenario(ad_channel=_degraded_payload_element_non_dict())

        _, contents = scenario.run_zip()

        assert contents["primary_texts.txt"].decode("utf-8") == "Cuerpo alternativo A"
        assert contents["headlines.txt"].decode("utf-8") == "Titulo alterno"


# ---------------------------------------------------------------------------
# Surplus filtering and partial download failures, end to end through
# ``execute()`` (Requirements 9.9, 9.10, 12.7, 12.8)
# ---------------------------------------------------------------------------


# A fourth production-shaped ``visual_url``, reserved for the **pinned**
# element of the filtering fixture. It has to be distinct from the three of
# ``_THREE_SURPLUS_URLS`` so that ``expected_image_binary`` yields a binary
# only that element could have contributed: if it ever showed up inside a ZIP
# entry, the assertion would name it.
_VISUAL_URL_PINNED_FORMAT = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "3f0d9a17-5c62-4f8e-9a1b-7d4e2c6b8a90.jpeg"
)

# The identifier of the pinned (published) format of the filtering fixture.
_FILTERING_PINNED_ID = "delta"

# The Categorías_de_Texto of the filtering fixture, declared as an ordered
# list of ``(name, [(payload_id, text), ...])`` pairs.
#
# Two deliberate traits:
#
# * ``primary_text`` holds **three** Textos_Excedentes with non-consecutive
#   identifiers (1, 2, 7), so "the file holds exactly the ``id != 0`` ones"
#   is a statement about a real list and not about a single element;
# * in ``headline`` the base asset (``id == 0``) sits in the **middle** of the
#   list, so a naive "skip the first element" implementation would keep the
#   published text and drop a surplus, and this fixture would catch it.
_FILTERING_TEXT_PAYLOADS = [
    (
        "primary_text",
        [
            (0, "Cuerpo publicado en Meta"),
            (1, "Cuerpo alternativo A"),
            (2, "Cuerpo alternativo B"),
            (7, "Cuerpo alternativo C"),
        ],
    ),
    (
        "headline",
        [
            (1, "Titulo alterno"),
            (0, "Titulo publicado"),
            (4, "Titulo alterno B"),
        ],
    ),
    (
        "description",
        [
            (0, "Descripcion publicada"),
            (2, "Descripcion alterna"),
        ],
    ),
    (
        "cta",
        [
            (0, "Comprar ahora"),
            (3, "Mas informacion"),
        ],
    ),
]

# The expected content of each of the four ``.txt`` entries, written out
# literally rather than derived from ``_FILTERING_TEXT_PAYLOADS``: the point of
# the criterion is that the file holds **exactly** the ``id != 0`` texts joined
# by ``'\n'``, and deriving the expectation from the same source that builds the
# fixture would make a filtering bug invisible.
_FILTERING_EXPECTED_TEXTS = {
    "primary_texts.txt": (
        "Cuerpo alternativo A\nCuerpo alternativo B\nCuerpo alternativo C"
    ),
    "headlines.txt": "Titulo alterno\nTitulo alterno B",
    "descriptions.txt": "Descripcion alterna",
    "ctas.txt": "Mas informacion",
}

# The text of the ``id == 0`` element of each category: the asset already
# published in Meta, which must appear in no entry of the Paquete_ZIP.
_FILTERING_BASE_TEXTS = {
    "primary_texts.txt": "Cuerpo publicado en Meta",
    "headlines.txt": "Titulo publicado",
    "descriptions.txt": "Descripcion publicada",
    "ctas.txt": "Comprar ahora",
}

# The seven entry names the filtering fixture must produce, alphabetically
# sorted: three ``images/{id}.jpeg`` for the three non-pinned formats plus the
# four category files at the root. ``images/delta.jpeg`` is deliberately not
# among them, and neither is ``manifest.txt``.
_FILTERING_EXPECTED_NAMES = [
    "ctas.txt",
    "descriptions.txt",
    "headlines.txt",
    "images/alpha.jpeg",
    "images/beta.jpeg",
    "images/gamma.jpeg",
    "primary_texts.txt",
]


def make_filtering_media_formats():
    """Build a fresh ``media_formats`` list of four elements: the three
    non-pinned formats of ``_THREE_SURPLUS_IDS`` plus one ``pinned=True``
    element, the published asset, **interleaved** at index 1.

    The pinned element sits between two surpluses on purpose, so the filtering
    cannot be mistaken for "take the tail of the list" nor for "drop the last
    element".

    Every one of the four carries its own ``visual_url``, so
    ``expected_image_binary`` yields four distinct binaries and a content mix-up
    between entries breaks the assertions.
    """
    return [
        make_media_format(
            format_id=_THREE_SURPLUS_IDS[0],
            visual_url=_THREE_SURPLUS_URLS[0],
            pinned=False,
        ),
        make_media_format(
            format_id=_FILTERING_PINNED_ID,
            visual_url=_VISUAL_URL_PINNED_FORMAT,
            pinned=True,
        ),
        make_media_format(
            format_id=_THREE_SURPLUS_IDS[1],
            visual_url=_THREE_SURPLUS_URLS[1],
            pinned=False,
        ),
        make_media_format(
            format_id=_THREE_SURPLUS_IDS[2],
            visual_url=_THREE_SURPLUS_URLS[2],
            pinned=False,
        ),
    ]


def make_filtering_channel_attributes():
    """Build a fresh ``channel_attributes`` list for the four
    Categorías_de_Texto of ``_FILTERING_TEXT_PAYLOADS``.
    """
    return [
        make_channel_attribute(
            name=name,
            payloads=[
                make_text_payload(payload_id=payload_id, text=text)
                for payload_id, text in items
            ],
        )
        for name, items in _FILTERING_TEXT_PAYLOADS
    ]


def make_filtering_ad_channel():
    """Build a fresh Ad_Channel_de_Exportación for ``TestSurplusFiltering``.

    **Every download of every non-pinned element succeeds** in this fixture
    (the download double is left unconfigured, so it answers ``200`` with the
    URL-specific binary for any URL). That is a requirement of the criterion,
    not an accident: the set of Assets_No_Incluidos has to be empty for the
    count equality between ``images/...`` entries and non-pinned surpluses to
    hold. A single failed download would leave one surplus out of the package
    and the equality would no longer be true.
    """
    return make_ad_channel(
        media_formats=make_filtering_media_formats(),
        channel_attributes=make_filtering_channel_attributes(),
    )


def non_pinned_count(ad_channel):
    """Count the elements of ``media_formats`` that are surplus candidates,
    that is the ``dict`` elements whose ``pinned`` is not identically ``True``
    (Requirement 7.1).

    Counted from the fixture itself rather than hardcoded, because the
    criterion states the equality against "the number of non-pinned surpluses
    **of the fixture**".
    """
    return len(
        [
            media_format
            for media_format in ad_channel["attributes"]["media_formats"]
            if isinstance(media_format, dict) and media_format.get("pinned") is not True
        ]
    )


class TestSurplusFiltering:
    """The two filtering rules of the export, end to end through ``execute()``.

    The fixture is ``make_filtering_ad_channel()``: four Formatos_de_Medio, one
    of them ``pinned=True``, and four Categorías_de_Texto each holding its
    published base asset (``id == 0``) plus one or more Textos_Excedentes
    (``id != 0``).

    All downloads of the three non-pinned elements **succeed**, so the set of
    Assets_No_Incluidos is empty, ``manifest.txt`` is absent (Requirement 9.11)
    and the count of ``images/...`` entries can be compared against the count of
    non-pinned surpluses of the fixture. With one failed download that equality
    would not hold, which is exactly the scenario of
    ``TestPartialDownloadFailures``.

    Requirements: 9.9, 9.10, 12.7
    """

    def test_pinned_format_produces_no_image_entry(self, export_scenario):
        """Requirement 12.7, first half: the ``pinned=True`` element yields no
        ``images/...`` entry at all.

        Asserted three ways so the case cannot pass by accident: its expected
        name is absent, no entry name mentions its identifier, and its binary is
        in none of the entries either.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        namelist, contents = scenario.run_zip()

        assert "images/{}.jpeg".format(_FILTERING_PINNED_ID) not in namelist
        assert [name for name in namelist if _FILTERING_PINNED_ID in name] == []
        pinned_binary = expected_image_binary(_VISUAL_URL_PINNED_FORMAT)
        assert pinned_binary not in contents.values()

    def test_pinned_format_is_never_downloaded(self, export_scenario):
        """Requirement 12.7: the pinned element is filtered out **before** any
        download attempt, not after one whose result is then discarded.

        The URLs actually requested are the three of the non-pinned elements, in
        the order of appearance within ``media_formats``, and neither the pinned
        ``visual_url`` nor the ``preview_url`` shared by the four elements
        (Requirement 7.10) is among them.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        scenario.run()

        assert requested_urls(scenario.requests_get) == list(_THREE_SURPLUS_URLS)
        assert _VISUAL_URL_PINNED_FORMAT not in requested_urls(scenario.requests_get)
        assert _PREVIEW_URL not in requested_urls(scenario.requests_get)
        assert scenario.requests_get.call_count == 3

    def test_image_entry_count_equals_the_non_pinned_surplus_count(
        self, export_scenario
    ):
        """Requirement 12.7, second half: the total number of ``images/...``
        entries equals the number of non-pinned surpluses of the fixture.

        The right-hand side is counted from the fixture, so the equality keeps
        its meaning if the fixture ever grows another format.
        """
        ad_channel = make_filtering_ad_channel()
        scenario = export_scenario(ad_channel=ad_channel)

        namelist, _ = scenario.run_zip()

        assert non_pinned_count(ad_channel) == 3
        assert len(image_entries(namelist)) == non_pinned_count(ad_channel)
        assert sorted(image_entries(namelist)) == [
            "images/alpha.jpeg",
            "images/beta.jpeg",
            "images/gamma.jpeg",
        ]

    def test_the_count_equality_rests_on_an_empty_not_included_set(
        self, export_scenario
    ):
        """Requirements 9.9, 9.11: the premise of the previous case, made
        explicit.

        Every non-pinned download of this fixture succeeds, so the set of
        Assets_No_Incluidos is empty and ``manifest.txt`` is absent. Were it
        present, one surplus would be missing from the package and the count
        equality would be false — hence this assertion guards the fixture
        itself, not only the implementation.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        namelist, contents = scenario.run_zip()

        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None

    def test_each_image_entry_holds_its_own_binary(self, export_scenario):
        """The three surviving entries carry, byte for byte, the binary the
        download double served for their **own** ``visual_url``.

        Without this the count equality could hold while the contents were
        swapped between entries.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        _, contents = scenario.run_zip()

        for format_id, visual_url in zip(_THREE_SURPLUS_IDS, _THREE_SURPLUS_URLS):
            entry_name = "images/{}.jpeg".format(format_id)
            assert contents[entry_name] == expected_image_binary(visual_url)

    @pytest.mark.parametrize(
        "filename, expected_content",
        sorted(_FILTERING_EXPECTED_TEXTS.items()),
    )
    def test_category_file_holds_exactly_the_non_zero_id_texts(
        self, export_scenario, filename, expected_content
    ):
        """Requirement 12.7, the text half: the ``.txt`` of each category holds
        exactly the Textos_Excedentes with ``id != 0``, joined by ``'\\n'`` in
        the order of appearance, with no leading and no trailing newline.

        ``headlines.txt`` is the discriminating one: its base asset sits in the
        middle of the ``payloads`` list, so the expected content proves the
        filtering is by ``id`` and not by position.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        _, contents = scenario.run_zip()

        decoded = contents[filename].decode("utf-8")
        assert decoded == expected_content
        assert not decoded.startswith("\n")
        assert not decoded.endswith("\n")

    @pytest.mark.parametrize(
        "filename, base_text",
        sorted(_FILTERING_BASE_TEXTS.items()),
    )
    def test_base_text_is_absent_from_its_own_category_file(
        self, export_scenario, filename, base_text
    ):
        """Requirement 12.7: the text of the ``id == 0`` element is the one
        already published in Meta, so it is not contained in the ``.txt`` of its
        category.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        _, contents = scenario.run_zip()

        assert base_text not in contents[filename].decode("utf-8")

    def test_no_base_text_appears_in_any_entry_of_the_package(self, export_scenario):
        """Requirement 12.7, widened: none of the four published texts leaks
        into any other entry of the Paquete_ZIP either, not even into a
        different category's file.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        _, contents = scenario.run_zip()

        for entry_content in contents.values():
            decoded = entry_content.decode("utf-8", errors="ignore")
            for base_text in _FILTERING_BASE_TEXTS.values():
                assert base_text not in decoded

    def test_zip_namelist_matches_the_seven_expected_entries(self, export_scenario):
        """The two filtering rules stated as one exact comparison: the
        alphabetically sorted entry names equal the seven expected names.

        Being exact, it is simultaneously an inclusion check (three images and
        four category files) and an exclusion one (no entry for the pinned
        format, no ``manifest.txt``).
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        namelist, _ = scenario.run_zip()

        assert sorted(namelist) == _FILTERING_EXPECTED_NAMES

    def test_execute_returns_an_export_result_without_raising(self, export_scenario):
        """The filtering never changes the outcome of the call: the envelope is
        the usual Resultado_de_Exportación and no exception escapes.
        """
        scenario = export_scenario(ad_channel=make_filtering_ad_channel())

        result = scenario.run()

        assert set(result.keys()) == {"content", "content_type", "filename"}
        assert result["content_type"] == "application/zip"
        assert zipfile.is_zipfile(BytesIO(result["content"]))


# The two failing outcomes the criterion demands, plus the two equivalent
# spellings ``patch_image_download`` accepts for each of them: an ``int`` means
# "answer with that status code", and an exception class or instance means
# "raise it". ``requests.exceptions.Timeout`` is the timeout exception of the
# very HTTP library the Caso_de_Uso already uses.
_PARTIAL_FAILURE_OUTCOMES = [
    pytest.param(404, id="status_404"),
    pytest.param(500, id="status_500"),
    pytest.param(requests.exceptions.Timeout, id="timeout_class"),
    pytest.param(requests.exceptions.Timeout("read timed out"), id="timeout_instance"),
]

# The index of the failing format within the three-element fixture. Every
# position is exercised: first, middle and last.
_PARTIAL_FAILURE_INDICES = [
    pytest.param(0, id="first_fails"),
    pytest.param(1, id="middle_fails"),
    pytest.param(2, id="last_fails"),
]


def build_partial_failure_scenario(export_scenario, failing_index, outcome):
    """Build a scenario of three Imágenes_Excedentes where exactly one of them
    fails to download.

    ``channel_attributes`` is forced to the empty list by
    ``make_ad_channel_with_formats``, so the resulting Paquete_ZIP holds only
    ``images/...`` entries plus ``manifest.txt`` and the entry-count assertions
    read without noise.
    """
    ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())
    responses = {_THREE_SURPLUS_URLS[failing_index]: outcome}
    return export_scenario(ad_channel=ad_channel, responses=responses)


def surviving_image_entries(failing_index):
    """The two ``images/...`` entry names expected once the format at
    ``failing_index`` has been left out, alphabetically sorted.
    """
    return sorted(
        "images/{}.jpeg".format(format_id)
        for index, format_id in enumerate(_THREE_SURPLUS_IDS)
        if index != failing_index
    )


class TestPartialDownloadFailures:
    """One failed download out of three, end to end through ``execute()``.

    The fixture is always the same: three non-pinned Imágenes_Excedentes with
    distinct identifiers and distinct ``visual_url`` values. Exactly one of them
    fails, either with a status code other than ``200`` or by raising
    ``requests.exceptions.Timeout``, and the two remaining ones download
    successfully.

    What the criterion pins is that a partial failure **degrades the package,
    never the call**: three download attempts, two ``images/...`` entries, a
    ``manifest.txt`` at the root naming the single format that did not make it,
    and a Resultado_de_Exportación returned without raising.

    Requirements: 9.9, 9.10, 12.8
    """

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_download_is_attempted_once_per_surplus(
        self, export_scenario, failing_index, outcome
    ):
        """Requirement 12.8: the download double records exactly three
        invocations, one per Imagen_Excedente.

        Three and not two proves the failing format **was** attempted, and three
        and not four proves neither a retry (Requirement 7.2 allows a single
        attempt) nor a stray ``preview_url`` download (Requirement 7.10)
        happened.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        scenario.run()

        assert scenario.requests_get.call_count == 3
        assert requested_urls(scenario.requests_get) == list(_THREE_SURPLUS_URLS)

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_exactly_two_image_entries_survive(
        self, export_scenario, failing_index, outcome
    ):
        """Requirement 12.8: the Paquete_ZIP holds exactly two ``images/...``
        entries, the ones of the two formats that did download.

        Compared by exact list equality, so it also states which two: the
        failing identifier is not among them.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        namelist, _ = scenario.run_zip()

        assert len(image_entries(namelist)) == 2
        assert sorted(image_entries(namelist)) == surviving_image_entries(failing_index)

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_surviving_entries_hold_their_own_binaries(
        self, export_scenario, failing_index, outcome
    ):
        """The two survivors carry, byte for byte, the binary served for their
        own ``visual_url``, and the failing format contributes no content at
        all.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        _, contents = scenario.run_zip()

        for index, format_id in enumerate(_THREE_SURPLUS_IDS):
            if index == failing_index:
                continue
            entry_name = "images/{}.jpeg".format(format_id)
            assert contents[entry_name] == expected_image_binary(
                _THREE_SURPLUS_URLS[index]
            )
        failed_binary = expected_image_binary(_THREE_SURPLUS_URLS[failing_index])
        assert failed_binary not in contents.values()

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_manifest_is_present_at_the_zip_root(
        self, export_scenario, failing_index, outcome
    ):
        """Requirements 9.9, 12.8: ``manifest.txt`` is present, and it sits at
        the **root** of the archive.

        The entry name is exactly ``manifest.txt``: no ``images/`` prefix, no
        directory of any kind, which is what the second assertion rules out.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        namelist, contents = scenario.run_zip()

        assert "manifest.txt" in namelist
        assert [name for name in namelist if name.endswith("/manifest.txt")] == []
        assert manifest_lines(contents) is not None

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_manifest_equals_the_single_failed_identifier(
        self, export_scenario, failing_index, outcome
    ):
        """Requirements 9.10, 12.8: the UTF-8 decoded content of
        ``manifest.txt`` equals, **by exact string comparison**, the identifier
        of the single failed format.

        Exact equality and not containment: one failure means one identifier and
        nothing else, with no leading and no trailing ``'\\n'``, and with the two
        successful identifiers absent from it.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        _, contents = scenario.run_zip()

        failed_id = _THREE_SURPLUS_IDS[failing_index]
        decoded = contents["manifest.txt"].decode("utf-8")
        assert decoded == failed_id
        assert manifest_lines(contents) == [failed_id]
        for index, format_id in enumerate(_THREE_SURPLUS_IDS):
            if index != failing_index:
                assert format_id not in decoded

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_execute_returns_an_export_result_without_raising(
        self, export_scenario, failing_index, outcome
    ):
        """Requirement 12.8: ``execute()`` returns the Resultado_de_Exportación
        without raising, whichever way the download failed.

        The call is made outside any ``pytest.raises``, so a status code turned
        into an exception, or a ``Timeout`` escaping the collector, would surface
        as an error of this very test.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        result = scenario.run()

        assert set(result.keys()) == {"content", "content_type", "filename"}
        assert isinstance(result["content"], bytes)
        assert len(result["content"]) > 0
        assert result["content_type"] == "application/zip"
        # A failed download degrades the contents of the package, never its
        # name: the four Nombres_de_Origen are untouched.
        assert result["filename"] == expected_filename()
        assert zipfile.is_zipfile(BytesIO(result["content"]))

    @pytest.mark.parametrize("outcome", _PARTIAL_FAILURE_OUTCOMES)
    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_namelist_equals_two_images_plus_the_manifest(
        self, export_scenario, failing_index, outcome
    ):
        """The whole archive of the partial-failure scenario, as one exact
        comparison: the two surviving images plus ``manifest.txt``, and nothing
        else.

        The fixture carries no Textos_Excedentes, so any other name showing up
        here would be an entry the packaging invented.
        """
        scenario = build_partial_failure_scenario(
            export_scenario, failing_index, outcome
        )

        namelist, _ = scenario.run_zip()

        assert sorted(namelist) == surviving_image_entries(failing_index) + [
            "manifest.txt"
        ]


# --------------------------------------------------------------------------- #
# Fixtures of the five manifest scenarios (Requirements 12.18 - 12.22).
#
# They all go through ``make_ad_channel_with_formats``, which forces
# ``channel_attributes`` to the empty list, so every fixture of this section has
# **zero** Textos_Excedentes and the resulting ``namelist()`` holds only
# ``images/...`` entries plus, when applicable, ``manifest.txt``. That is what
# lets ``test_manifest_only_package`` compare the whole archive against the
# single-element list ``['manifest.txt']`` (Requirement 9.14).
# --------------------------------------------------------------------------- #

# The non-200 status code used by the single-failure scenario. Any value other
# than 200 satisfies Requirement 7.5; 403 is picked so it differs from the codes
# already exercised by ``TestPartialDownloadFailures`` (404 and 500).
_MANIFEST_FAILING_STATUS = 403

# The identifiers of the two-causes fixture. They are deliberately named after
# the **cause** each one exercises, so a wrong order in ``manifest.txt`` reads as
# a wrong sequence of causes rather than as two interchangeable strings.
_TWO_CAUSES_RAISING_ID = "raising-download"
_TWO_CAUSES_UNUSABLE_ID = "unusable-visual-url"
_TWO_CAUSES_SUCCESSFUL_ID = "successful-download"


def make_two_causes_formats(raising_first):
    """Build a ``media_formats`` list combining the two reportable causes that
    are **not** a non-200 status code (Requirement 7.11).

    Three non-pinned elements, with the successful one sitting **between** the
    two failing ones so their relative order in ``manifest.txt`` cannot be an
    artifact of adjacency:

    * one element whose download raises (cause (c)), its ``visual_url`` being
      the one the scenario maps to ``requests.exceptions.Timeout``;
    * one element with an unusable ``visual_url`` (cause (a)), a whitespace-only
      string, which is therefore never requested at all;
    * one element that downloads successfully, contributing the only
      ``images/...`` entry of the package.

    ``raising_first`` swaps the position of the two failing elements, which is
    what turns the exact string comparison of
    ``test_two_causes_are_reported_in_media_formats_order`` into a real ordering
    assertion: the same two identifiers must come out in the opposite order.
    """
    raising = make_media_format(
        format_id=_TWO_CAUSES_RAISING_ID,
        visual_url=_VISUAL_URL_FACEBOOK_POST,
        pinned=False,
    )
    unusable = make_media_format(
        format_id=_TWO_CAUSES_UNUSABLE_ID,
        visual_url="   ",
        pinned=False,
    )
    successful = make_media_format(
        format_id=_TWO_CAUSES_SUCCESSFUL_ID,
        visual_url=_VISUAL_URL_INSTAGRAM_STORY,
        pinned=False,
    )
    first, last = (raising, unusable) if raising_first else (unusable, raising)
    return [first, successful, last]


# The identifiers of the manifest-only fixture: two non-pinned elements whose
# downloads both fail, plus the published pinned asset, which is neither
# downloaded nor reported (Requirement 7.11).
_MANIFEST_ONLY_FAILING_IDS = ["alpha", "gamma"]
_MANIFEST_ONLY_PINNED_ID = "instagram-portrait"


def make_manifest_only_formats():
    """Build the ``media_formats`` list of the manifest-only package
    (Requirement 9.14): two non-pinned elements whose downloads fail, one with a
    non-200 status and one raising, plus one ``pinned=True`` element.

    The pinned element carries its own distinct ``visual_url``, so the response
    mapping of the scenario cannot make it fail by accident: it is left out
    because it is the published asset, not because its download did not work.
    """
    return [
        make_media_format(
            format_id=_MANIFEST_ONLY_FAILING_IDS[0],
            visual_url=_VISUAL_URL_FACEBOOK_POST,
            pinned=False,
        ),
        make_media_format(
            format_id=_MANIFEST_ONLY_PINNED_ID,
            visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
            pinned=True,
        ),
        make_media_format(
            format_id=_MANIFEST_ONLY_FAILING_IDS[1],
            visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            pinned=False,
        ),
    ]


_MANIFEST_ONLY_RESPONSES = {
    _VISUAL_URL_FACEBOOK_POST: _MANIFEST_FAILING_STATUS,
    _VISUAL_URL_INSTAGRAM_STORY: requests.exceptions.Timeout,
}


# The zero-based index, **within the complete ``media_formats``**, of the
# element without a usable ``id`` in the fixture below. It is deliberately
# different from that element's position among the surplus candidates, which is
# ``0``: it is the first candidate, but the third element of the list.
_GLOBAL_INDEX_OF_MISSING_ID = 2
_GLOBAL_INDEX_PINNED_ID = "pinned-format"
_GLOBAL_INDEX_TRAILING_ID = "trailing-format"


def make_missing_id_formats(id_value):
    """Build a ``media_formats`` list whose element without a usable ``id`` is
    preceded by a ``pinned`` element and by a non-``dict`` one
    (Requirements 7.11, 9.4).

    The resulting positions are::

        index 0 -> pinned=True element      (not a surplus candidate)
        index 1 -> a plain string           (not a surplus candidate)
        index 2 -> id absent or None, download fails  -> reported as '2'
        index 3 -> a normal surplus, download succeeds -> images/... entry

    Two elements that are not surplus candidates sit ahead of it on purpose: the
    reported identifier must be the index within the **complete** list, so
    counting only the candidates (which would yield ``'0'``) or only the
    ``dict`` elements (which would yield ``'1'``) both produce a wrong answer
    that this fixture can tell apart.

    ``id_value`` is either the ``ABSENT`` sentinel, which removes the ``id`` key
    altogether, or ``None``, which keeps the key with the value ``None``. Both
    are the same case for Requirement 9.4.
    """
    return [
        make_media_format(
            format_id=_GLOBAL_INDEX_PINNED_ID,
            visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
            pinned=True,
        ),
        "not-a-dict-element",
        make_media_format(
            format_id=id_value,
            visual_url=_VISUAL_URL_FACEBOOK_POST,
            pinned=False,
        ),
        make_media_format(
            format_id=_GLOBAL_INDEX_TRAILING_ID,
            visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            pinned=False,
        ),
    ]


class TestManifest:
    """The ``manifest.txt`` entry of the Paquete_ZIP, end to end through
    ``execute()``.

    The manifest is the only channel through which a partially complete export
    is visible to whoever downloads the package: its **presence** signals an
    incomplete package and its **absence** a complete one (Requirements 9.9,
    9.11). Its payload is nothing but identifiers, one per line, in the order of
    appearance within ``media_formats`` (Requirements 7.11, 9.10).

    Every case reads the entry through the ``manifest_lines`` helper, which
    returns ``None`` when the entry is absent instead of an empty list, so the
    present/absent distinction is explicit in the assertion rather than implied
    by a length comparison.

    Requirements: 7.11, 9.9, 9.10, 9.11, 9.14, 12.18, 12.19, 12.20, 12.21, 12.22
    """

    @pytest.mark.parametrize("failing_index", _PARTIAL_FAILURE_INDICES)
    def test_single_failed_download_is_reported(self, export_scenario, failing_index):
        """Requirement 12.18: three surplus candidates, a status code other than
        200 on exactly one of them.

        ``manifest.txt`` is present at the **root** of the archive and its UTF-8
        content equals, by exact string comparison, the identifier of that one
        format: a single line, with no leading and no trailing ``'\\n'``, and
        with the two successful identifiers nowhere inside it.
        """
        ad_channel = make_ad_channel_with_formats(make_three_surplus_formats())
        responses = {_THREE_SURPLUS_URLS[failing_index]: _MANIFEST_FAILING_STATUS}
        scenario = export_scenario(ad_channel=ad_channel, responses=responses)

        namelist, contents = scenario.run_zip()

        assert "manifest.txt" in namelist
        assert [name for name in namelist if name.endswith("/manifest.txt")] == []

        failed_id = _THREE_SURPLUS_IDS[failing_index]
        decoded = contents["manifest.txt"].decode("utf-8")
        assert decoded == failed_id
        assert not decoded.startswith("\n")
        assert not decoded.endswith("\n")
        assert manifest_lines(contents) == [failed_id]
        for index, format_id in enumerate(_THREE_SURPLUS_IDS):
            if index != failing_index:
                assert format_id not in decoded

    @pytest.mark.parametrize(
        "raising_first, expected_ids",
        [
            pytest.param(
                True,
                [_TWO_CAUSES_RAISING_ID, _TWO_CAUSES_UNUSABLE_ID],
                id="raising_before_unusable",
            ),
            pytest.param(
                False,
                [_TWO_CAUSES_UNUSABLE_ID, _TWO_CAUSES_RAISING_ID],
                id="unusable_before_raising",
            ),
        ],
    )
    def test_two_causes_are_reported_in_media_formats_order(
        self, export_scenario, raising_first, expected_ids
    ):
        """Requirement 12.19: a fixture combining an element whose download
        raises with a non-pinned element whose ``visual_url`` is unusable.

        The content of ``manifest.txt`` equals, by exact string comparison, the
        **two** identifiers joined by ``'\\n'`` in their order of appearance
        within ``media_formats``. Both orderings are exercised, so the
        assertion cannot be satisfied by a fixed order (alphabetical, or "status
        failures first") that happens to match one of them.

        Note the asymmetry between the two causes at the HTTP level: the
        unusable ``visual_url`` is rejected before any request, so the download
        double records two invocations and not three.
        """
        ad_channel = make_ad_channel_with_formats(
            make_two_causes_formats(raising_first=raising_first)
        )
        responses = {_VISUAL_URL_FACEBOOK_POST: requests.exceptions.Timeout}
        scenario = export_scenario(ad_channel=ad_channel, responses=responses)

        namelist, contents = scenario.run_zip()

        assert contents["manifest.txt"].decode("utf-8") == "\n".join(expected_ids)
        assert manifest_lines(contents) == expected_ids

        # The surviving surplus is the only image of the package, and the
        # unusable ``visual_url`` never reached the network.
        assert image_entries(namelist) == [
            "images/{}.jpeg".format(_TWO_CAUSES_SUCCESSFUL_ID)
        ]
        expected_urls = (
            [_VISUAL_URL_FACEBOOK_POST, _VISUAL_URL_INSTAGRAM_STORY]
            if raising_first
            else [_VISUAL_URL_INSTAGRAM_STORY, _VISUAL_URL_FACEBOOK_POST]
        )
        assert requested_urls(scenario.requests_get) == expected_urls
        assert "   " not in requested_urls(scenario.requests_get)

    def test_manifest_absent_when_all_downloads_succeed(self, export_scenario):
        """Requirement 12.20: with status 200 for every Imagen_Excedente, the
        name ``manifest.txt`` is **not** in ``namelist()``.

        This is the complete-package half of Requirement 9.11: an absent
        manifest, not a present but empty one. ``manifest_lines`` returning
        ``None`` is what distinguishes the two.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel_with_formats(make_three_surplus_formats())
        )

        namelist, contents = scenario.run_zip()

        assert "manifest.txt" not in namelist
        assert manifest_lines(contents) is None
        assert sorted(namelist) == [
            "images/alpha.jpeg",
            "images/beta.jpeg",
            "images/gamma.jpeg",
        ]

    def test_manifest_only_package(self, export_scenario):
        """Requirements 9.14, 12.21: two non-pinned elements whose downloads
        fail, one ``pinned=True`` element and zero Textos_Excedentes.

        The archive is not empty and it is not an error either: it holds exactly
        one entry, ``manifest.txt``, listing the two candidates that did not make
        it. The pinned identifier is absent from it, because the published asset
        is not something the user is missing, and ``execute()`` returns its usual
        Resultado_de_Exportación without raising.
        """
        ad_channel = make_ad_channel_with_formats(make_manifest_only_formats())
        scenario = export_scenario(
            ad_channel=ad_channel, responses=_MANIFEST_ONLY_RESPONSES
        )

        result = scenario.run()
        namelist, contents = read_zip(result["content"])

        assert namelist == ["manifest.txt"]
        assert manifest_lines(contents) == _MANIFEST_ONLY_FAILING_IDS

        decoded = contents["manifest.txt"].decode("utf-8")
        assert _MANIFEST_ONLY_PINNED_ID not in decoded

        assert set(result.keys()) == {"content", "content_type", "filename"}
        assert result["content_type"] == "application/zip"
        assert zipfile.is_zipfile(BytesIO(result["content"]))

    def test_manifest_only_package_never_downloads_the_pinned_asset(
        self, export_scenario
    ):
        """Requirement 9.14, the premise of the previous case: the pinned element
        is left out by the filter, not by a failed download.

        Its ``visual_url`` is absent from the requested URLs, and the two
        requests issued are those of the two non-pinned candidates.
        """
        ad_channel = make_ad_channel_with_formats(make_manifest_only_formats())
        scenario = export_scenario(
            ad_channel=ad_channel, responses=_MANIFEST_ONLY_RESPONSES
        )

        scenario.run()

        assert requested_urls(scenario.requests_get) == [
            _VISUAL_URL_FACEBOOK_POST,
            _VISUAL_URL_INSTAGRAM_STORY,
        ]
        assert _VISUAL_URL_INSTAGRAM_PORTRAIT not in requested_urls(
            scenario.requests_get
        )

    @pytest.mark.parametrize(
        "id_value",
        [pytest.param(ABSENT, id="id_key_absent"), pytest.param(None, id="id_is_none")],
    )
    def test_missing_id_is_reported_by_global_index(self, export_scenario, id_value):
        """Requirement 12.22: an Asset_No_Incluido whose element lacks the ``id``
        key, or holds ``None`` in it, is reported by the string representation of
        its **zero-based index within the complete** ``media_formats``.

        The fixture puts a ``pinned`` element and a non-``dict`` element ahead of
        it, so its global index (``2``) differs both from its position among the
        surplus candidates (``0``) and from its position among the ``dict``
        elements (``1``). The last two assertions rule out those two wrong
        answers explicitly.
        """
        ad_channel = make_ad_channel_with_formats(make_missing_id_formats(id_value))
        responses = {_VISUAL_URL_FACEBOOK_POST: _MANIFEST_FAILING_STATUS}
        scenario = export_scenario(ad_channel=ad_channel, responses=responses)

        namelist, contents = scenario.run_zip()

        expected_id = str(_GLOBAL_INDEX_OF_MISSING_ID)
        assert manifest_lines(contents) == [expected_id]
        assert contents["manifest.txt"].decode("utf-8") == expected_id
        assert manifest_lines(contents) != ["0"]
        assert manifest_lines(contents) != ["1"]

        # The trailing surplus downloaded fine, so the package is partial and
        # not empty: one image entry plus the manifest.
        assert sorted(namelist) == [
            "images/{}.jpeg".format(_GLOBAL_INDEX_TRAILING_ID),
            "manifest.txt",
        ]


# --------------------------------------------------------------------------- #
# Fixtures of the exclusive-key-reading scenario (Requirement 7.10).
#
# ``make_media_format`` always carries the seven auxiliary keys, so the default
# fixture already exercises Requirement 7.10 implicitly. What it cannot do is
# make a leak *visible*: its ``visual_id`` default,
# ``'12271afc-a8c8-4a0f-a5c9-6999ec76cee9'``, is literally a substring of the
# ``facebook-post`` ``visual_url``, and the download double derives the binary
# it serves from that URL. Searching for that value inside the ZIP entries
# would therefore find it even in a perfectly correct implementation.
#
# Hence the sentinel values below: unmistakable strings that appear nowhere in
# any ``visual_url``, in no text of the fixture and in no derived entry name, so
# finding one inside an entry can only mean the Caso_de_Uso read a key it must
# ignore.
# --------------------------------------------------------------------------- #

# The seven auxiliary keys of a ``media_formats`` element that the Caso_de_Uso
# must ignore. Only ``id``, ``visual_url`` and ``pinned`` are read.
_AUXILIARY_KEY_NAMES = (
    "uid",
    "unit",
    "width",
    "height",
    "errors",
    "visual_id",
    "preview_url",
)

# Sentinel values for six of the seven auxiliary keys. ``preview_url`` is
# deliberately left out of this mapping: it keeps its real production value
# ``_PREVIEW_URL``, because the sharpest form of Requirement 7.10 is that a
# perfectly downloadable image URL is *not* downloaded, and swapping it for a
# sentinel would weaken exactly that.
_AUXILIARY_SENTINEL_VALUES = {
    "uid": "AUXILIARY-UID-MUST-NOT-BE-EXPORTED",
    "unit": "AUXILIARY-UNIT-MUST-NOT-BE-EXPORTED",
    "width": "AUXILIARY-WIDTH-MUST-NOT-BE-EXPORTED",
    "height": "AUXILIARY-HEIGHT-MUST-NOT-BE-EXPORTED",
    "errors": ["AUXILIARY-ERRORS-MUST-NOT-BE-EXPORTED"],
    "visual_id": "AUXILIARY-VISUAL-ID-MUST-NOT-BE-EXPORTED",
}


def _auxiliary_sentinel_overrides():
    """Return a **fresh** copy of the six sentinel overrides, with a fresh
    ``errors`` list.

    Same reason the eight builders never share state (Requirement 12.3): the
    mapping above is a module-level literal, and handing its list out to three
    elements of the same fixture would have them share one object.
    """
    overrides = dict(_AUXILIARY_SENTINEL_VALUES)
    overrides["errors"] = list(_AUXILIARY_SENTINEL_VALUES["errors"])
    return overrides

# The flattened sentinel strings to search for inside the ZIP entries. The
# ``errors`` value is a list, so what travels into the archive if it were
# exported is its single element.
_AUXILIARY_SENTINEL_STRINGS = [
    _AUXILIARY_SENTINEL_VALUES["uid"],
    _AUXILIARY_SENTINEL_VALUES["unit"],
    _AUXILIARY_SENTINEL_VALUES["width"],
    _AUXILIARY_SENTINEL_VALUES["height"],
    _AUXILIARY_SENTINEL_VALUES["errors"][0],
    _AUXILIARY_SENTINEL_VALUES["visual_id"],
    _PREVIEW_URL,
]

# The two non-pinned formats of the fixture below, plus the pinned one. Their
# identifiers carry no resemblance to any auxiliary value, so the expected entry
# names cannot be satisfied by accident.
_EXCLUSIVE_KEYS_SURPLUS_IDS = ["read-only-alpha", "read-only-beta"]
_EXCLUSIVE_KEYS_PINNED_ID = "read-only-pinned"

_EXCLUSIVE_KEYS_SURPLUS_URLS = {
    _EXCLUSIVE_KEYS_SURPLUS_IDS[0]: _VISUAL_URL_FACEBOOK_POST,
    _EXCLUSIVE_KEYS_SURPLUS_IDS[1]: _VISUAL_URL_INSTAGRAM_STORY,
}

# Two ``images/...`` entries plus the four Categorías_de_Texto of the default
# ``channel_attributes``: the fixture keeps the texts so the auxiliary search
# runs over a package with entries of both kinds.
_EXCLUSIVE_KEYS_EXPECTED_NAMES = [
    "ctas.txt",
    "descriptions.txt",
    "headlines.txt",
    "images/read-only-alpha.jpeg",
    "images/read-only-beta.jpeg",
    "primary_texts.txt",
]


def make_auxiliary_rich_formats():
    """Build a ``media_formats`` list whose three elements carry the seven
    auxiliary keys with **unmistakable sentinel values** (Requirement 7.10).

    Two non-pinned elements with distinct real ``visual_url`` values, so both
    download successfully and the resulting package holds two ``images/...``
    entries, plus one ``pinned=True`` element, which is the published asset.

    ``preview_url`` keeps its real value on all three: it is a valid, perfectly
    downloadable ``.png`` that the download double would serve without
    complaint, which is what makes "zero invocations against it" a real
    assertion rather than a tautology.
    """
    surplus = [
        make_media_format(
            format_id=format_id,
            visual_url=visual_url,
            pinned=False,
            **_auxiliary_sentinel_overrides()
        )
        for format_id, visual_url in _EXCLUSIVE_KEYS_SURPLUS_URLS.items()
    ]
    pinned = make_media_format(
        format_id=_EXCLUSIVE_KEYS_PINNED_ID,
        visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
        pinned=True,
        **_auxiliary_sentinel_overrides()
    )
    return [surplus[0], pinned, surplus[1]]


def make_auxiliary_rich_ad_channel():
    """Build an Ad_Channel_de_Exportación with the auxiliary-rich
    ``media_formats`` above and the default four Categorías_de_Texto.
    """
    return make_ad_channel(media_formats=make_auxiliary_rich_formats())


class TestExclusiveKeyReading:
    """Only ``id``, ``visual_url`` and ``pinned`` are read from a
    ``media_formats`` element, end to end through ``execute()``
    (Requirement 7.10).

    Production elements carry seven further keys — ``uid``, ``unit``, ``width``,
    ``height``, ``errors``, ``visual_id`` and ``preview_url`` — and the
    Caso_de_Uso must ignore every one of them. ``preview_url`` is the dangerous
    one: it is a valid image URL, so an implementation that walked the element
    looking for "some URL to download" would happily fetch it and ship a
    preview thumbnail as if it were a surplus asset.

    Two independent observations pin the requirement down: the download double
    is never invoked against ``preview_url``, and neither the seven key names
    nor their values show up in the content of any entry of the Paquete_ZIP.

    Requirements: 7.10
    """

    def test_only_the_surplus_visual_urls_are_requested(self, export_scenario):
        """Requirement 7.10: the requested URLs are exactly the ``visual_url``
        of the two non-pinned elements, in their order of appearance.

        One request per Imagen_Excedente and not one more: three elements each
        carrying a ``visual_url`` and a ``preview_url`` add up to six candidate
        URLs, and only two of them are fetched.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        scenario.run()

        assert requested_urls(scenario.requests_get) == [
            _VISUAL_URL_FACEBOOK_POST,
            _VISUAL_URL_INSTAGRAM_STORY,
        ]
        assert scenario.requests_get.call_count == 2

    def test_the_preview_url_is_never_downloaded(self, export_scenario):
        """Requirement 7.10: zero invocations of the download double against
        ``preview_url``, even though all three elements carry it.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        scenario.run()

        assert requested_urls(scenario.requests_get).count(_PREVIEW_URL) == 0
        assert _PREVIEW_URL not in requested_urls(scenario.requests_get)

    def test_the_preview_binary_is_not_packaged(self, export_scenario):
        """Requirement 7.10, the packaging half: the binary the double would
        have served for ``preview_url`` is in no entry of the Paquete_ZIP.

        Asserted separately from the call count because an implementation could
        conceivably obtain that binary by another route; what matters to whoever
        opens the archive is that it is not in it.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        namelist, contents = scenario.run_zip()

        preview_binary = expected_image_binary(_PREVIEW_URL)
        assert preview_binary not in contents.values()
        for entry_name, entry_content in contents.items():
            assert preview_binary not in entry_content, entry_name
        assert "images/{}.png".format(_EXCLUSIVE_KEYS_SURPLUS_IDS[0]) not in namelist

    def test_the_seven_key_names_are_absent_from_every_entry(self, export_scenario):
        """Requirement 7.10: none of the seven auxiliary **key names** appears
        in the content of any entry of the Paquete_ZIP.

        This is what rules out a serialised dump of the element — a JSON blob, a
        ``repr()``, a metadata sidecar — as the content of an entry: any of them
        would carry the key names themselves.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        _, contents = scenario.run_zip()

        for entry_name, entry_content in contents.items():
            decoded = entry_content.decode("utf-8", errors="ignore")
            for key_name in _AUXILIARY_KEY_NAMES:
                assert key_name not in decoded, (entry_name, key_name)
                assert key_name.encode("utf-8") not in entry_content, (
                    entry_name,
                    key_name,
                )

    def test_the_seven_values_are_absent_from_every_entry(self, export_scenario):
        """Requirement 7.10: none of the seven auxiliary **values** appears in
        the content of any entry of the Paquete_ZIP either.

        The six sentinels plus the real ``preview_url``. The sentinels are
        strings that exist nowhere else in the fixture, so a hit can only come
        from the Caso_de_Uso having read a key it must ignore.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        _, contents = scenario.run_zip()

        for entry_name, entry_content in contents.items():
            decoded = entry_content.decode("utf-8", errors="ignore")
            for sentinel in _AUXILIARY_SENTINEL_STRINGS:
                assert sentinel not in decoded, (entry_name, sentinel)
                assert sentinel.encode("utf-8") not in entry_content, (
                    entry_name,
                    sentinel,
                )

    def test_the_package_is_built_from_the_three_read_keys_only(self, export_scenario):
        """Requirement 7.10, stated positively: the archive is exactly what
        ``id``, ``visual_url`` and ``pinned`` dictate.

        The names come from ``id`` plus the extension derived from
        ``visual_url``, the pinned element contributes nothing, and each entry
        holds the binary served for its own ``visual_url`` — with seven
        auxiliary keys sitting right next to them making no difference at all.
        """
        scenario = export_scenario(ad_channel=make_auxiliary_rich_ad_channel())

        namelist, contents = scenario.run_zip()

        assert sorted(namelist) == _EXCLUSIVE_KEYS_EXPECTED_NAMES
        assert "images/{}.jpeg".format(_EXCLUSIVE_KEYS_PINNED_ID) not in namelist
        for format_id, visual_url in _EXCLUSIVE_KEYS_SURPLUS_URLS.items():
            entry_name = "images/{}.jpeg".format(format_id)
            assert contents[entry_name] == expected_image_binary(visual_url)


# --------------------------------------------------------------------------- #
# Fixtures of the complementarity scenario (Property 12 of ``design.md``,
# Requirements 7.11, 9.9, 9.10, 9.11).
#
# One single fixture mixes every shape an element of ``media_formats`` can take:
# two successful downloads, the three causes of an Asset_No_Incluido, one pinned
# element and one non-``dict`` element. The last two are **not** surplus
# candidates, so they belong to neither side of the partition, which is what
# makes the union assertion meaningful rather than trivially true.
# --------------------------------------------------------------------------- #

# Two extra real-shaped ``visual_url`` values: the three module-level constants
# are not enough for a fixture with four distinct URLs, and reusing one would
# make the per-URL response mapping ambiguous.
_COMPLEMENTARITY_URL_RAISING = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "7d3c2f41-5a6b-4c8d-9e0f-1a2b3c4d5e6f.jpeg"
)
_COMPLEMENTARITY_URL_SECOND_SUCCESS = (
    "https://production-banners.s3-eu-west-1.amazonaws.com/"
    "c7f8a281-b153-43cd-a45a-a669890ceaf9/"
    "3f9e8d7c-6b5a-4938-8271-0a1b2c3d4e5f.jpeg"
)

# The HTTP status code of the one status failure of the fixture. It is searched
# for as a string inside ``manifest.txt``, where the NFR Security of
# Requirement 9.10 forbids it.
_COMPLEMENTARITY_FAILING_STATUS = 451

_COMPLEMENTARITY_PINNED_ID = "published-asset"
_COMPLEMENTARITY_SUCCESS_IDS = ["survivor-one", "survivor-two"]

# The zero-based index, within the **complete** ``media_formats``, of the
# element without an ``id``. It is reported by that index (Requirement 9.4), so
# it is the identifier the manifest side of the partition must carry.
_COMPLEMENTARITY_MISSING_ID_INDEX = 5

_COMPLEMENTARITY_FAILED_IDS = [
    "lost-to-status",
    "lost-to-exception",
    str(_COMPLEMENTARITY_MISSING_ID_INDEX),
]

# The complete set of surplus candidates of the fixture: every element that is a
# ``dict`` and whose ``pinned`` is not identically ``True``. Declared literally
# rather than derived from the fixture, so the partition is compared against an
# independent statement of what the fixture holds.
_COMPLEMENTARITY_CANDIDATE_IDS = {
    "survivor-one",
    "lost-to-status",
    "lost-to-exception",
    "5",
    "survivor-two",
}


def make_complementarity_formats():
    """Build the mixed ``media_formats`` list of the complementarity scenario.

    The positions, and what each element must contribute::

        index 0 -> pinned=True                       -> neither side
        index 1 -> 'survivor-one', download 200      -> images/survivor-one.jpeg
        index 2 -> a plain string, not a dict        -> neither side
        index 3 -> 'lost-to-status', status 451      -> manifest.txt
        index 4 -> 'lost-to-exception', raises       -> manifest.txt
        index 5 -> id absent, visual_url unusable    -> manifest.txt, as '5'
        index 6 -> 'survivor-two', download 200      -> images/survivor-two.jpeg

    The successes are deliberately placed at both ends, with the three failures
    in between, so neither side of the partition can be produced by a rule as
    coarse as "the first N elements".
    """
    return [
        make_media_format(
            format_id=_COMPLEMENTARITY_PINNED_ID,
            visual_url=_VISUAL_URL_INSTAGRAM_PORTRAIT,
            pinned=True,
        ),
        make_media_format(
            format_id=_COMPLEMENTARITY_SUCCESS_IDS[0],
            visual_url=_VISUAL_URL_FACEBOOK_POST,
            pinned=False,
        ),
        "not-a-dict-element",
        make_media_format(
            format_id=_COMPLEMENTARITY_FAILED_IDS[0],
            visual_url=_VISUAL_URL_INSTAGRAM_STORY,
            pinned=False,
        ),
        make_media_format(
            format_id=_COMPLEMENTARITY_FAILED_IDS[1],
            visual_url=_COMPLEMENTARITY_URL_RAISING,
            pinned=False,
        ),
        make_media_format(
            format_id=ABSENT,
            visual_url="   ",
            pinned=False,
        ),
        make_media_format(
            format_id=_COMPLEMENTARITY_SUCCESS_IDS[1],
            visual_url=_COMPLEMENTARITY_URL_SECOND_SUCCESS,
            pinned=False,
        ),
    ]


_COMPLEMENTARITY_RESPONSES = {
    _VISUAL_URL_INSTAGRAM_STORY: _COMPLEMENTARITY_FAILING_STATUS,
    _COMPLEMENTARITY_URL_RAISING: requests.exceptions.Timeout,
}

# Everything the NFR Security of Requirement 9.10 forbids inside
# ``manifest.txt``: the full ``visual_url`` of every element of the fixture, any
# fragment of the S3 bucket (its name, its region, its host and the two UUID
# levels of a key), the HTTP status code of the failure and the simulated access
# token. The manifest carries identifiers and nothing else.
_MANIFEST_FORBIDDEN_FRAGMENTS = [
    _VISUAL_URL_FACEBOOK_POST,
    _VISUAL_URL_INSTAGRAM_PORTRAIT,
    _VISUAL_URL_INSTAGRAM_STORY,
    _COMPLEMENTARITY_URL_RAISING,
    _COMPLEMENTARITY_URL_SECOND_SUCCESS,
    _PREVIEW_URL,
    "production-banners",
    "s3-eu-west-1",
    "amazonaws.com",
    "c7f8a281-b153-43cd-a45a-a669890ceaf9",
    "12271afc-a8c8-4a0f-a5c9-6999ec76cee9",
    "bb5ea12f-67a6-4024-a4aa-24ace40dcb88",
    "7d3c2f41-5a6b-4c8d-9e0f-1a2b3c4d5e6f",
    str(_COMPLEMENTARITY_FAILING_STATUS),
    SIMULATED_ACCESS_TOKEN,
]


class TestManifestComplementarity:
    """Property 12 of ``design.md``, verified by example: ``manifest.txt`` and
    the ``images/...`` entries partition the surplus candidates exactly.

    Let **M** be the set of identifiers listed in ``manifest.txt`` (empty when
    the entry is absent) and **I** the set derived from the names of the entries
    starting with ``images/``. For any ``media_formats`` and any assignment of
    success or failure to each download, **M** and **I** are disjoint and their
    union is exactly the set of surplus candidates — the elements that are
    ``dict`` instances whose ``pinned`` is not identically ``True``.

    That invariant is what makes the package honest: every asset the user could
    expect either arrived, as a binary, or is named as missing, and no asset can
    be both or neither.

    The class also covers the NFR Security of Requirement 9.10: the manifest
    reports identifiers, so a source URL, a bucket fragment, an HTTP status code
    or the access token has zero occurrences in it.

    Requirements: 7.10, 7.11, 9.9, 9.10, 9.11
    """

    def _run(self, export_scenario):
        """Run the mixed fixture and return
        ``(namelist, contents, manifest_ids, image_ids)``.

        ``manifest_ids`` is **M** and ``image_ids`` is **I**, both as sets, so
        each case below reads as the set statement it is asserting.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel_with_formats(make_complementarity_formats()),
            responses=_COMPLEMENTARITY_RESPONSES,
        )

        namelist, contents = scenario.run_zip()

        lines = manifest_lines(contents)
        manifest_ids = set() if lines is None else set(lines)
        image_ids = {identifier_of_entry(name) for name in image_entries(namelist)}
        return namelist, contents, manifest_ids, image_ids

    def test_the_two_identifier_sets_are_disjoint(self, export_scenario):
        """Property 12, first half: **M** and **I** share no identifier.

        No candidate can be reported as missing and shipped as a binary at the
        same time, which is exactly what a second derivation of the identifier
        (one per branch) would eventually break.
        """
        _, _, manifest_ids, image_ids = self._run(export_scenario)

        assert manifest_ids & image_ids == set()
        assert manifest_ids.isdisjoint(image_ids)
        assert manifest_ids == set(_COMPLEMENTARITY_FAILED_IDS)
        assert image_ids == set(_COMPLEMENTARITY_SUCCESS_IDS)

    def test_their_union_equals_the_surplus_candidates(self, export_scenario):
        """Property 12, second half: **M** ∪ **I** equals the whole set of
        surplus candidates of the fixture.

        Nothing is lost silently: the five candidates are accounted for, the
        pinned element and the non-``dict`` element belong to neither side, and
        the count matches the sum, so no identifier is duplicated across the two.
        """
        _, _, manifest_ids, image_ids = self._run(export_scenario)

        assert manifest_ids | image_ids == _COMPLEMENTARITY_CANDIDATE_IDS
        assert len(manifest_ids) + len(image_ids) == len(
            _COMPLEMENTARITY_CANDIDATE_IDS
        )
        assert _COMPLEMENTARITY_PINNED_ID not in manifest_ids | image_ids

    def test_every_candidate_appears_exactly_once_in_the_package(self, export_scenario):
        """Property 12 read entry by entry: each candidate shows up once, as an
        ``images/...`` entry or as a line of ``manifest.txt``.

        The manifest lines are compared as a **list** here, not as a set, so the
        order of appearance within ``media_formats`` of Requirement 7.11 is
        pinned as well: the status failure, the raising one and then the one
        reported by its global index.
        """
        namelist, contents, _, _ = self._run(export_scenario)

        assert manifest_lines(contents) == _COMPLEMENTARITY_FAILED_IDS
        assert sorted(namelist) == [
            "images/{}.jpeg".format(_COMPLEMENTARITY_SUCCESS_IDS[0]),
            "images/{}.jpeg".format(_COMPLEMENTARITY_SUCCESS_IDS[1]),
            "manifest.txt",
        ]
        packaged_ids = [identifier_of_entry(name) for name in image_entries(namelist)]
        reported_ids = manifest_lines(contents)
        for candidate_id in _COMPLEMENTARITY_CANDIDATE_IDS:
            occurrences = packaged_ids.count(candidate_id) + reported_ids.count(
                candidate_id
            )
            assert occurrences == 1, candidate_id

    def test_the_surviving_binaries_are_the_expected_ones(self, export_scenario):
        """The premise of the partition: the two entries on the **I** side hold
        the binary of their own ``visual_url``.

        Without this, "the identifier is in **I**" would say nothing about the
        asset actually having arrived.
        """
        _, contents, _, _ = self._run(export_scenario)

        assert contents[
            "images/{}.jpeg".format(_COMPLEMENTARITY_SUCCESS_IDS[0])
        ] == expected_image_binary(_VISUAL_URL_FACEBOOK_POST)
        assert contents[
            "images/{}.jpeg".format(_COMPLEMENTARITY_SUCCESS_IDS[1])
        ] == expected_image_binary(_COMPLEMENTARITY_URL_SECOND_SUCCESS)

    def test_the_manifest_leaks_no_url_bucket_status_nor_token(self, export_scenario):
        """NFR Security of Requirement 9.10: zero occurrences inside
        ``manifest.txt`` of a source ``visual_url``, of any fragment of the S3
        bucket (name, region, host, key UUIDs), of the HTTP status code of the
        failure and of the simulated access token.

        The manifest is handed to whoever downloads the package, so it must name
        the missing assets without disclosing where they were meant to come from
        or why precisely the fetch failed.
        """
        _, contents, _, _ = self._run(export_scenario)

        decoded = contents["manifest.txt"].decode("utf-8")
        for fragment in _MANIFEST_FORBIDDEN_FRAGMENTS:
            assert decoded.count(fragment) == 0, fragment
            assert contents["manifest.txt"].count(fragment.encode("utf-8")) == 0, (
                fragment
            )

    def test_the_manifest_holds_identifiers_and_nothing_else(self, export_scenario):
        """NFR Security of Requirement 9.10, stated positively: every line of
        ``manifest.txt`` is one of the expected identifiers, and the entry
        carries no URL-shaped or path-shaped text at all.

        A whitelist rather than a blacklist: it also catches a leak of something
        this suite did not think to forbid.
        """
        _, contents, _, _ = self._run(export_scenario)

        decoded = contents["manifest.txt"].decode("utf-8")
        assert manifest_lines(contents) == _COMPLEMENTARITY_FAILED_IDS
        for forbidden_character in ("http", "://", "/", ".jpeg", ".png", " "):
            assert forbidden_character not in decoded, forbidden_character


# ---------------------------------------------------------------------------
# Entry naming at the Paquete_ZIP level (Requirements 9.3, 9.5, 12.13, 12.14)
# ---------------------------------------------------------------------------


# The four rows of the extension-derivation table of ``design.md``, this time
# carried by four Imágenes_Excedentes of a real Ad_Channel_de_Exportación:
# identifier, ``visual_url`` and the entry name the Paquete_ZIP must end up
# holding. These fixtures are the only ones of the suite that override the
# ``.jpeg`` production default of ``make_media_format``, because Requirement
# 12.13 asks precisely for extensions other than that one.
_NAMING_CASES = [
    ("plain-jpg", "https://cdn.example/a/img.jpg", "images/plain-jpg.jpg"),
    ("plain-png", "https://cdn.example/a/img.png", "images/plain-png.png"),
    (
        "png-with-query",
        "https://cdn.example/a/img.png?v=2&t=1",
        "images/png-with-query.png",
    ),
    ("no-extension", "https://cdn.example/a/img", "images/no-extension.jpg"),
]

_NAMING_EXPECTED_NAMES = sorted(entry_name for _, _, entry_name in _NAMING_CASES)


def make_naming_formats():
    """Build a fresh ``media_formats`` list of the four naming cases.

    All four are non-pinned and all four download successfully, so the set of
    Assets_No_Incluidos is empty and the package holds exactly four entries.
    """
    return [
        make_media_format(format_id=format_id, visual_url=visual_url, pinned=False)
        for format_id, visual_url, _ in _NAMING_CASES
    ]


class TestZipEntryNamingEndToEnd:
    """Requirement 12.13 at the level of the Paquete_ZIP: the extension rule of
    Requirement 9.3 decides the **effective entry name**, not just the return
    value of a helper.

    ``TestExtensionDerivation`` already pins ``_derive_image_extension`` in
    isolation; this class exercises ``execute()`` end to end, so it also proves
    the derived extension is the one that reaches ``zipfile`` — a correct helper
    whose result the packaging step dropped or recomputed would pass there and
    fail here. Hence the deliberately different class name: both live in the
    same module.

    Requirements: 9.3, 12.13
    """

    def _run(self, export_scenario):
        scenario = export_scenario(
            ad_channel=make_ad_channel_with_formats(make_naming_formats())
        )
        namelist, contents = scenario.run_zip()
        return scenario, namelist, contents

    def test_namelist_holds_exactly_the_four_expected_entry_names(
        self, export_scenario
    ):
        """Requirement 12.13: the four entry names are
        ``images/{id}.jpg``, ``images/{id}.png``, ``images/{id}.png`` and
        ``images/{id}.jpg`` for their respective identifiers.

        An exact comparison, so it also proves nothing else got packaged: no
        text entry (``channel_attributes`` is empty) and no ``manifest.txt``,
        since every download succeeded (Requirement 9.11).
        """
        _, namelist, contents = self._run(export_scenario)

        assert sorted(namelist) == _NAMING_EXPECTED_NAMES
        assert manifest_lines(contents) is None

    @pytest.mark.parametrize(
        "format_id,visual_url,expected_entry_name",
        [
            pytest.param(format_id, visual_url, expected_entry_name, id=format_id)
            for format_id, visual_url, expected_entry_name in _NAMING_CASES
        ],
    )
    def test_each_visual_url_yields_its_documented_entry_name(
        self, export_scenario, format_id, visual_url, expected_entry_name
    ):
        """Requirement 12.13, row by row: each ``visual_url`` shape produces its
        own entry name, and that entry carries the binary the download double
        served for **that** URL.

        The fourth row is the discriminating one: a last path segment with no
        dot at all falls back to the ``.jpg`` default of Requirement 9.3, and
        the query string of the third row never leaks into the name.
        """
        _, namelist, contents = self._run(export_scenario)

        assert expected_entry_name in namelist
        assert contents[expected_entry_name] == expected_image_binary(visual_url)

    def test_the_query_string_reaches_neither_the_name_nor_the_package(
        self, export_scenario
    ):
        """Requirement 9.3: the query string is discarded before deriving the
        extension, so no entry name carries ``?``, ``&`` or ``=``.
        """
        _, namelist, _ = self._run(export_scenario)

        for entry_name in namelist:
            for forbidden_character in ("?", "&", "="):
                assert forbidden_character not in entry_name, entry_name

    def test_the_four_images_are_downloaded_once_each(self, export_scenario):
        """The premise of the four assertions above: exactly four downloads,
        one per Imagen_Excedente and none for ``preview_url``
        (Requirement 7.10).
        """
        scenario, _, _ = self._run(export_scenario)

        assert scenario.requests_get.call_count == len(_NAMING_CASES)
        assert sorted(requested_urls(scenario.requests_get)) == sorted(
            visual_url for _, visual_url, _ in _NAMING_CASES
        )


# The two colliding Imágenes_Excedentes of Requirement 12.14: same ``id`` and
# same derived extension, different ``visual_url`` — which is what makes the
# per-entry binary assertion able to tell the two apart.
_COLLIDING_ID = "duplicado"
_COLLIDING_URL_FIRST = "https://cdn.example/dup/primera.jpg"
_COLLIDING_URL_SECOND = "https://cdn.example/dup/segunda.jpg"

_COLLIDING_EXPECTED_NAMES = [
    "images/{}.jpg".format(_COLLIDING_ID),
    "images/{}_1.jpg".format(_COLLIDING_ID),
]


def make_colliding_formats():
    """Build a fresh ``media_formats`` list of two non-pinned formats sharing
    the same ``id`` and the same derived extension.

    With the production data confirmed by the maintainer the identifiers of a
    same list are unique, so this shape is defensive: it exists to pin what
    Requirement 9.5 must do should it ever occur.
    """
    return [
        make_media_format(
            format_id=_COLLIDING_ID, visual_url=_COLLIDING_URL_FIRST, pinned=False
        ),
        make_media_format(
            format_id=_COLLIDING_ID, visual_url=_COLLIDING_URL_SECOND, pinned=False
        ),
    ]


class TestZipEntryDisambiguationEndToEnd:
    """Requirement 12.14 at the level of the Paquete_ZIP: two colliding names
    become two distinct entries, and neither asset is lost.

    ``TestNameDisambiguation`` pins ``_disambiguate_entry_name`` in isolation;
    this class exercises ``execute()``, so it additionally proves the collision
    is resolved **before** writing to the archive. Without it, an implementation
    that computed the suffix but wrote the original name would silently ship a
    single entry, or a duplicated one, and the second binary would vanish.

    Requirements: 9.5, 12.14
    """

    def _run(self, export_scenario):
        scenario = export_scenario(
            ad_channel=make_ad_channel_with_formats(make_colliding_formats())
        )
        namelist, contents = scenario.run_zip()
        return scenario, namelist, contents

    def test_sorted_namelist_equals_the_base_name_and_its_suffixed_variant(
        self, export_scenario
    ):
        """Requirement 12.14: the alphabetically sorted entry names equal, by
        exact list comparison,
        ``['images/{id}.jpg', 'images/{id}_1.jpg']``.

        The suffix sits immediately before the extension, never after it, so
        ``images/{id}.jpg_1`` is not an accepted outcome.
        """
        _, namelist, contents = self._run(export_scenario)

        assert sorted(namelist) == _COLLIDING_EXPECTED_NAMES
        assert len(namelist) == 2
        assert manifest_lines(contents) is None

    def test_each_entry_holds_the_binary_of_its_own_visual_url(
        self, export_scenario
    ):
        """Requirement 12.14, second half: the base name carries the binary of
        the first element of ``media_formats`` and the suffixed one that of the
        second, each matching its **own** ``visual_url``.

        The order of appearance of Requirement 9.16 is what makes the mapping
        deterministic: the first element takes the base name and the second the
        ``_1`` suffix.
        """
        _, _, contents = self._run(export_scenario)

        assert contents[_COLLIDING_EXPECTED_NAMES[0]] == expected_image_binary(
            _COLLIDING_URL_FIRST
        )
        assert contents[_COLLIDING_EXPECTED_NAMES[1]] == expected_image_binary(
            _COLLIDING_URL_SECOND
        )

    def test_the_two_entries_do_not_share_their_content(self, export_scenario):
        """The premise of the previous case: the two binaries differ, so a swap
        or an overwrite of one entry by the other could not go unnoticed.
        """
        _, _, contents = self._run(export_scenario)

        assert (
            contents[_COLLIDING_EXPECTED_NAMES[0]]
            != contents[_COLLIDING_EXPECTED_NAMES[1]]
        )

    def test_both_collisions_are_downloaded_and_none_is_reported_missing(
        self, export_scenario
    ):
        """Both elements are Imágenes_Excedentes with a successful download, so
        there are exactly two downloads and the set of Assets_No_Incluidos is
        empty: the shared identifier is packaged twice, not reported once
        (Requirement 9.11).
        """
        scenario, namelist, contents = self._run(export_scenario)

        assert scenario.requests_get.call_count == 2
        assert requested_urls(scenario.requests_get) == [
            _COLLIDING_URL_FIRST,
            _COLLIDING_URL_SECOND,
        ]
        assert "manifest.txt" not in contents
        assert image_entries(namelist) == namelist


# ---------------------------------------------------------------------------
# The real ``AdChannelRepository`` query parameters
# (Requirements 5.7, 5.8, 12.29)
# ---------------------------------------------------------------------------

# Four deliberately distinctive identifiers, all different from each other and
# from the ones the payload builder declares, so a swapped pair inside the
# repository — the four filters do **not** follow the order of the signature —
# breaks the exact comparison instead of passing by coincidence.
_REPO_CAMPAIGN_ID = 9101
_REPO_ADSET_ID = 9202
_REPO_AD_ID = 9303
_REPO_ADCHANNEL_ID = 9404


def expected_legacy_params(
    campaign_id=_REPO_CAMPAIGN_ID,
    adset_id=_REPO_ADSET_ID,
    ad_id=_REPO_AD_ID,
    adchannel_id=_REPO_ADCHANNEL_ID,
):
    """Return a fresh dict holding the **five** query parameters that
    ``AdChannelRepository.get_by_campaign_and_ad_channel_id`` sent before the
    ZIP filename correction.

    The five keys are spelled out **literally** here, never imported from
    ``AdChannelRepository`` nor derived from its source: that is what makes the
    comparison a non-regression proof for the two pre-existing consumers of the
    method (``FacebookSavePreCheckBaseUseCase._get_ad_channel`` and
    ``FacebookPublishCampaignUseCase._get_ad_channel``). Reading the expected
    value out of the implementation would make the assertion tautological.

    A fresh dict per invocation, as every builder of this module
    (Requirement 12.3).

    Requirements: 5.7, 12.3
    """
    return {
        "filters[id][$eq]": adchannel_id,
        "filters[ad_ref2][id][$eq]": ad_id,
        "filters[ad_ref2][ad_set_ref2][id][$eq]": adset_id,
        "filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]": (
            campaign_id
        ),
        "populate[channel_ref][fields][0]": "id",
    }


def expected_populated_params(
    campaign_id=_REPO_CAMPAIGN_ID,
    adset_id=_REPO_ADSET_ID,
    ad_id=_REPO_AD_ID,
    adchannel_id=_REPO_ADCHANNEL_ID,
):
    """Return a fresh dict holding the **eight** query parameters expected when
    the optional population parameter of Requirement 5.7 is activated: the five
    legacy ones unchanged plus the three ``name`` populations of Requirement 5.8.

    Spelled out literally too, in the same **object notation** the method
    already used for ``populate[channel_ref][fields][0]``: the list notation
    (``params['populate'] = [...]``) would produce two incompatible shapes for
    the same key once Strapi deserializes the query string.

    Requirements: 5.8, 12.3
    """
    return {
        "filters[id][$eq]": adchannel_id,
        "filters[ad_ref2][id][$eq]": ad_id,
        "filters[ad_ref2][ad_set_ref2][id][$eq]": adset_id,
        "filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]": (
            campaign_id
        ),
        "populate[channel_ref][fields][0]": "id",
        "populate[ad_ref2][fields][0]": "name",
        "populate[ad_ref2][populate][ad_set_ref2][fields][0]": "name",
        "populate[channel_ref][fields][1]": "name",
    }


@contextmanager
def patch_strapi_get(return_value=None):
    """Context manager that replaces the ``get`` method **inherited from**
    ``StrapiClient`` with a test double and yields it.

    The double is installed on the transport method itself, so the repository
    under test is the **real** ``AdChannelRepository``: the query parameters it
    builds are recorded verbatim and no request ever leaves the process. The
    ``deny_network`` autouse fixture guards the same boundary from below
    (Requirement 12.2).

    Requirements: 12.2, 12.29
    """
    with patch.object(
        AdChannelRepository, "get", return_value=return_value
    ) as mock_get:
        yield mock_get


def recorded_params(mock_get):
    """Return the pair ``(content_type, params)`` of the single recorded
    invocation of the doubled ``get``.

    Both travel positionally in ``self.get(self.content_type, params)``, so a
    silent move of either one to a keyword argument surfaces here as a
    ``KeyError``/``IndexError`` rather than as a passing assertion.
    """
    recorded_args, recorded_kwargs = mock_get.call_args
    assert recorded_kwargs == {}
    return recorded_args[0], recorded_args[1]


class TestAdChannelRepositoryPopulateParams:
    """Characterization of the **real**
    ``AdChannelRepository.get_by_campaign_and_ad_channel_id``, with the ``get``
    method inherited from ``StrapiClient`` replaced by a test double and zero
    real requests (Requirement 12.29).

    Unlike every other class of this suite, the collaborator doubled here is
    not the repository but its transport: the object under test is the genuine
    repository, instantiated for real. Its constructor only builds a
    ``StrapiClient`` and fixes ``content_type``, so it emits no traffic
    (Requirement 12.2).

    Three families of cases:

    * with the optional parameter of Requirement 5.7 at its default, the
      ``params`` dict equals **by exact comparison** the five-key dict that
      predates this correction, which is the non-regression proof for the two
      consumers already calling the method;
    * with the parameter activated, the dict carries in addition the three
      ``name`` populations of Requirement 5.8 while preserving the four filters
      and the ``populate[channel_ref][fields][0]`` key on which Requirement 5.3
      depends;
    * the return handling of the method is untouched in both modes.

    Requirements: 5.7, 5.8, 12.1, 12.2, 12.29
    """

    # -- Zero traffic, and the content type the query is issued against ----

    def test_instantiating_the_real_repository_issues_no_request(self):
        """Requirements 12.2 and 12.29: the real repository is constructible
        inside this suite with no patch whatsoever beyond the ``deny_network``
        guard, because its constructor only builds a ``StrapiClient`` and fixes
        the content type.

        Any request attempted here would trip the autouse guard.
        """
        repository = AdChannelRepository()

        assert repository.content_type == "ad-channels"

    def test_the_query_is_issued_against_the_ad_channels_content_type(self):
        """Requirement 12.29: the first positional argument of the doubled
        ``get`` is the ``'ad-channels'`` content type, in both modes of the
        optional parameter.
        """
        for populate_names in (False, True):
            with patch_strapi_get() as mock_get:
                AdChannelRepository().get_by_campaign_and_ad_channel_id(
                    _REPO_CAMPAIGN_ID,
                    _REPO_ADSET_ID,
                    _REPO_AD_ID,
                    _REPO_ADCHANNEL_ID,
                    populate_names=populate_names,
                )

            content_type, _ = recorded_params(mock_get)
            assert mock_get.call_count == 1
            assert content_type == "ad-channels"

    # -- The default: the five-key dict, unchanged (Requirement 5.7) --------

    def test_default_parameter_sends_the_legacy_five_key_params(self):
        """Requirements 5.7 and 12.29, the non-regression half: invoked with
        the four identifiers only, the ``params`` dict received by the double is
        equal **by exact comparison** to the five-key dict declared literally in
        this module.

        Exact equality, not containment: it also pins that none of the three
        ``name`` population keys leaks into the default query, which is what
        keeps the two pre-existing consumers of the method behaving identically.
        """
        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
            )

        _, params = recorded_params(mock_get)
        assert mock_get.call_count == 1
        assert params == expected_legacy_params()
        assert len(params) == 5

    def test_parameter_explicitly_deactivated_sends_the_legacy_five_key_params(
        self,
    ):
        """Requirement 12.29: passing the optional parameter explicitly
        deactivated is indistinguishable from omitting it, so the default value
        is genuinely inert and not merely unreached.
        """
        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
                populate_names=False,
            )

        _, params = recorded_params(mock_get)
        assert params == expected_legacy_params()
        assert len(params) == 5

    # -- Activated: the three ``name`` populations (Requirement 5.8) --------

    def test_activated_parameter_sends_the_eight_key_params(self):
        """Requirements 5.8 and 12.29: with the parameter activated the
        ``params`` dict equals **by exact comparison** the eight-key dict, that
        is the five legacy keys plus the ``name`` population of ``ad_ref2``, of
        ``ad_set_ref2`` nested inside ``ad_ref2``, and of ``channel_ref``.

        Exact equality also pins the absence of any extra population the
        Caso_de_Uso does not read.
        """
        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
                populate_names=True,
            )

        _, params = recorded_params(mock_get)
        assert mock_get.call_count == 1
        assert params == expected_populated_params()
        assert len(params) == 8

    def test_activated_parameter_preserves_the_filters_and_the_id_population(
        self,
    ):
        """Requirement 12.29, read the other way round: the activated query is a
        strict superset of the default one.

        The four filters keep their values and
        ``populate[channel_ref][fields][0]`` keeps the value ``'id'``, on which
        the Channel_ID resolution of Requirement 5.3 depends: the ``name`` of
        ``channel_ref`` is added at index ``1`` of the same ``fields``, it does
        not displace the ``id``.
        """
        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
                populate_names=True,
            )

        _, params = recorded_params(mock_get)
        legacy = expected_legacy_params()
        assert {key: params[key] for key in legacy} == legacy
        assert params["populate[channel_ref][fields][0]"] == "id"
        assert params["populate[channel_ref][fields][1]"] == "name"
        assert set(params) - set(legacy) == {
            "populate[ad_ref2][fields][0]",
            "populate[ad_ref2][populate][ad_set_ref2][fields][0]",
            "populate[channel_ref][fields][1]",
        }

    # -- The four identifiers travel verbatim ------------------------------

    @pytest.mark.parametrize(
        "campaign_id,adset_id,ad_id,adchannel_id",
        [
            pytest.param(9101, 9202, 9303, 9404, id="ints"),
            pytest.param("9101", "9202", "9303", "9404", id="strings"),
            pytest.param(
                " 9101 ", " 9202 ", " 9303 ", " 9404 ", id="strings_with_whitespace"
            ),
            pytest.param(
                "09101", "09202", "09303", "09404", id="strings_with_leading_zeros"
            ),
            pytest.param(0, 0, 0, 0, id="zeros"),
            pytest.param(9101, "9202", 9303, "9404", id="mixed"),
        ],
    )
    @pytest.mark.parametrize("populate_names", [False, True])
    def test_the_four_identifiers_travel_without_type_conversion(
        self, populate_names, campaign_id, adset_id, ad_id, adchannel_id
    ):
        """Requirement 12.29: each identifier lands on its own filter verbatim —
        no ``int()``, no ``str()``, no ``strip()``, no dropping of leading
        zeros — and it does so in both modes of the optional parameter.

        The values are distinctive on purpose: the signature takes
        ``adset_id`` before ``ad_id`` while the dict declares the ``ad_ref2``
        filter before the ``ad_set_ref2`` one, which is the easiest thing to get
        wrong here. Equality alone would let a ``0``/``False`` confusion
        through, so the exact type of each recorded value is checked too.
        """
        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                campaign_id,
                adset_id,
                ad_id,
                adchannel_id,
                populate_names=populate_names,
            )

        _, params = recorded_params(mock_get)
        expected = (
            expected_populated_params(campaign_id, adset_id, ad_id, adchannel_id)
            if populate_names
            else expected_legacy_params(campaign_id, adset_id, ad_id, adchannel_id)
        )
        assert params == expected
        assert type(params["filters[id][$eq]"]) is type(adchannel_id)
        assert type(params["filters[ad_ref2][id][$eq]"]) is type(ad_id)
        assert type(params["filters[ad_ref2][ad_set_ref2][id][$eq]"]) is type(adset_id)
        assert type(
            params[
                "filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]"
            ]
        ) is type(campaign_id)

    def test_the_four_identifiers_are_the_very_objects_received(self):
        """Requirement 12.29 in its strongest form: identity, not equality.

        Four unique sentinel objects go in and the very same four objects reach
        the query parameters, each on its own filter. A defensive copy or a
        normalization breaks this.
        """
        campaign_id = object()
        adset_id = object()
        ad_id = object()
        adchannel_id = object()

        with patch_strapi_get() as mock_get:
            AdChannelRepository().get_by_campaign_and_ad_channel_id(
                campaign_id, adset_id, ad_id, adchannel_id, populate_names=True
            )

        _, params = recorded_params(mock_get)
        assert params["filters[id][$eq]"] is adchannel_id
        assert params["filters[ad_ref2][id][$eq]"] is ad_id
        assert params["filters[ad_ref2][ad_set_ref2][id][$eq]"] is adset_id
        assert (
            params[
                "filters[ad_ref2][ad_set_ref2][funnel_flow_ref][campaign_ref][id][$eq]"
            ]
            is campaign_id
        )

    # -- The return handling is unaffected ---------------------------------

    @pytest.mark.parametrize("populate_names", [False, True])
    def test_a_populated_data_list_yields_its_first_record(self, populate_names):
        """Requirement 12.29: the return handling of the method is untouched by
        the correction — a response of the shape ``{'data': [record]}`` yields
        that very record, by identity.
        """
        record = make_ad_channel()

        with patch_strapi_get({"data": [record]}):
            result = AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
                populate_names=populate_names,
            )

        assert result is record

    @pytest.mark.parametrize(
        "response",
        [
            pytest.param({"data": []}, id="empty_data_list"),
            pytest.param({}, id="empty_response"),
            pytest.param(None, id="no_response"),
        ],
    )
    @pytest.mark.parametrize("populate_names", [False, True])
    def test_an_unusable_response_yields_none(self, populate_names, response):
        """Requirement 12.29: the three unusable responses keep yielding
        ``None`` in both modes, so the ``DataNotFoundException`` that
        Requirement 5.2 raises upstream is still reached the same way.
        """
        with patch_strapi_get(response):
            result = AdChannelRepository().get_by_campaign_and_ad_channel_id(
                _REPO_CAMPAIGN_ID,
                _REPO_ADSET_ID,
                _REPO_AD_ID,
                _REPO_ADCHANNEL_ID,
                populate_names=populate_names,
            )

        assert result is None


# ---------------------------------------------------------------------------
# Name of the Paquete_ZIP: interpolation of the four Nombres_de_Origen,
# sanitisation, missing components and wiring of the name population
# (Requirements 4.6, 5.1, 5.7, 5.9, 5.10, 10.4, 10.12-10.15, 12.25-12.28)
# ---------------------------------------------------------------------------


# The exact whitelist of Requirement 10.12, used as the structural guarantee of
# Property 13(b): the value travels in the ``Content-Disposition`` header, so a
# single character outside this set is a security defect and not a cosmetic one.
_FILENAME_WHITELIST = re.compile(r'^[A-Za-z0-9._-]+$')

# The main-flow filename, spelled out once. Kept as a literal next to the
# derived ``expected_filename()`` so that a change in either the template or the
# default source names shows up here as a diff.
_EXPECTED_MAIN_FLOW_FILENAME = (
    "assets_Black_Friday_AdSet_Prospecting_Ad_Retargeting_facebook.zip"
)


def assert_filename_is_safe(filename):
    """Assert the four structural guarantees every ``filename`` must satisfy.

    No character outside ``[A-Za-z0-9._-]`` (which already rules out spaces,
    the path separators ``/`` and ``\\``, control characters, quotes and every
    non-ASCII character) and a ``.zip`` suffix. They are asserted one by one
    rather than through the regex alone so a failure names the offending
    property.

    Requirements: 10.12, 10.4
    """
    assert filename.endswith(".zip")
    assert " " not in filename
    assert "/" not in filename
    assert "\\" not in filename
    assert all(character >= " " and character != "\x7f" for character in filename)
    assert filename == filename.encode("ascii", "ignore").decode("ascii")
    assert _FILENAME_WHITELIST.match(filename)


# The four outcomes of the filename table of algorithm 6 of ``design.md``,
# expressed as (four source names, expected filename). They are the by-example
# coverage of Property 13: from all four names present down to all four
# missing, including the two intermediate shapes where the empty components
# keep their position as consecutive ``_``.
_FILENAME_OUTCOMES = [
    pytest.param(
        (_DEFAULT_CAMPAIGN_NAME, _DEFAULT_AD_SET_NAME, _DEFAULT_AD_NAME,
         _DEFAULT_CHANNEL_NAME),
        _EXPECTED_MAIN_FLOW_FILENAME,
        id="four_names_present",
    ),
    pytest.param(
        (_DEFAULT_CAMPAIGN_NAME, ABSENT, _DEFAULT_AD_NAME, _DEFAULT_CHANNEL_NAME),
        "assets_Black_Friday__Ad_Retargeting_facebook.zip",
        id="ad_set_name_missing",
    ),
    pytest.param(
        (ABSENT, ABSENT, ABSENT, _DEFAULT_CHANNEL_NAME),
        "assets____facebook.zip",
        id="only_the_channel_name_survives",
    ),
    pytest.param(
        (ABSENT, ABSENT, ABSENT, ABSENT),
        "assets.zip",
        id="four_names_missing",
    ),
]


class TestExportFilename:
    """The name of the Paquete_ZIP, derived from the four Nombres_de_Origen and
    from nothing else, end to end through ``execute()``.

    Two families of cases: the main flow, whose four source names are distinct
    and already whitelist-clean, and the four outcomes of the filename table of
    algorithm 6 of ``design.md``, which are the by-example coverage of
    Property 13.

    Requirements: 10.4, 10.12, 10.13, 10.14, 12.25
    """

    def test_filename_equals_the_four_names_interpolated_in_order(
        self, export_scenario
    ):
        """Requirements 10.4, 12.25: with the four Nombres_de_Origen distinct
        and already conforming to ``[A-Za-z0-9._-]``, ``filename`` equals — by
        **exact string comparison** —
        ``assets_{campaign_name}_{ad_set_name}_{ad_name}_{channel_name}.zip``.

        The four defaults are pairwise distinct and none is a prefix or a suffix
        of another, so swapping any two of them changes the value and fails
        here.
        """
        scenario = export_scenario()

        result = scenario.run()

        assert result["filename"] == _EXPECTED_MAIN_FLOW_FILENAME
        assert result["filename"] == expected_filename()

    def test_no_payload_identifier_is_contained_in_the_filename(
        self, export_scenario
    ):
        """Requirements 10.13, 12.25, the exclusion half: the string
        representation of **none** of the five identifiers of the
        Payload_de_Exportación is contained in ``filename``.

        Checked by containment and not by equality, because the danger is a
        substring: an identifier smuggled in the middle of the name would leak
        just as much as one used as a whole component.
        """
        payload = make_export_payload()
        scenario = export_scenario(payload=payload)

        result = scenario.run()

        assert len(payload) == 5
        for identifier in payload.values():
            assert str(identifier) not in result["filename"]

    def test_the_four_names_are_swappable_only_at_the_cost_of_the_assertion(
        self, export_scenario
    ):
        """Requirement 12.25, the premise of the exact comparison: a fixture
        whose ad-set and ad names are exchanged produces a **different**
        filename, so the order of the four components is genuinely pinned.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel(
                ad_name=_DEFAULT_AD_SET_NAME, ad_set_name=_DEFAULT_AD_NAME
            )
        )

        result = scenario.run()

        assert result["filename"] != _EXPECTED_MAIN_FLOW_FILENAME
        assert result["filename"] == expected_filename(
            ad_set_name=_DEFAULT_AD_NAME, ad_name=_DEFAULT_AD_SET_NAME
        )

    @pytest.mark.parametrize("source_names, expected", _FILENAME_OUTCOMES)
    def test_the_four_documented_outcomes_are_safe_filenames(
        self, export_scenario, source_names, expected
    ):
        """Property 13 by example, over the four outcomes of the filename table
        of ``design.md`` (Requirements 10.4, 10.13, 10.14, 12.25).

        Each outcome is checked twice: by exact string equality against the
        value the table declares, and against the structural guarantees — no
        character outside ``[A-Za-z0-9._-]`` and a ``.zip`` suffix — that make
        the value safe to put in a ``Content-Disposition`` header.
        """
        campaign_name, ad_set_name, ad_name, channel_name = source_names
        payload = make_export_payload()
        scenario = export_scenario(
            payload=payload,
            campaign=make_campaign(name=campaign_name),
            ad_channel=make_ad_channel(
                ad_set_name=ad_set_name, ad_name=ad_name, channel_name=channel_name
            ),
        )

        result = scenario.run()

        assert result["filename"] == expected
        assert_filename_is_safe(result["filename"])
        for identifier in payload.values():
            assert str(identifier) not in result["filename"]

    def test_the_all_empty_collapse_happens_only_when_the_four_are_empty(
        self, export_scenario
    ):
        """Requirement 10.14 read as an equivalence, the (d) half of
        Property 13: ``assets.zip`` if **and only if** the four
        Nombres_Saneados are the empty string.

        One surviving name is enough to keep the template, empty components
        included, so the collapse can never hide a name that was actually
        there.
        """
        scenario = export_scenario(
            campaign=make_campaign(name=ABSENT),
            ad_channel=make_ad_channel(
                ad_set_name=ABSENT, ad_name=ABSENT, channel_name="x"
            ),
        )

        result = scenario.run()

        assert result["filename"] == "assets____x.zip"
        assert result["filename"] != "assets.zip"


# The nine rows of the sanitisation table of algorithm 6 of ``design.md``, which
# Requirement 12.26 demands: spaces, diacritics, a path separator, a control
# character and a newline, two or more forbidden characters in a row, forbidden
# characters at both ends, a name longer than the 60 character cap, a name
# written entirely in a non-Latin script, and a value that is not a ``str``.
#
# Each row declares the Nombre_de_Origen and the Nombre_Saneado it must produce.
_SANITIZATION_ROWS = [
    pytest.param("Black Friday 2025", "Black_Friday_2025", id="spaces"),
    pytest.param("Campaña Otoño", "Campana_Otono", id="diacritics_and_enye"),
    pytest.param(r"promo/2025\ruta", "promo_2025_ruta", id="path_separators"),
    pytest.param("promo\n\x00inyectada", "promo_inyectada", id="control_and_newline"),
    pytest.param("a  ##  b", "a_b", id="two_or_more_forbidden_in_a_row"),
    pytest.param("__promo__", "promo", id="forbidden_at_both_ends"),
    pytest.param("A" * 80, "A" * 60, id="longer_than_sixty"),
    pytest.param("Кампания", "", id="non_latin_script"),
    pytest.param(123, "", id="not_a_str"),
]


class TestFilenameSanitization:
    """The six sanitisation steps of Requirement 10.12, exercised **end to end
    through ``execute()``** rather than against the helper alone.

    The row under test is injected as the Nombre_de_Origen of the campaign and
    the other three components keep their clean defaults, so the expected value
    is the whole filename and not just a fragment of it: the assertion covers
    the sanitisation *and* its interpolation into the template.

    Requirements: 10.12, 10.13, 12.26
    """

    @pytest.mark.parametrize("raw_name, sanitized", _SANITIZATION_ROWS)
    def test_the_row_produces_its_documented_filename(
        self, export_scenario, raw_name, sanitized
    ):
        """Requirement 12.26: ``filename`` equals, by exact string comparison,
        the value declared by the row of the sanitisation table.

        The two rows whose Nombre_Saneado is the empty string (the non-Latin
        script of Requirement 10.13 and the non-``str`` value) are asserted the
        same way: their component simply comes out empty, marked by two
        consecutive ``_``.
        """
        scenario = export_scenario(campaign=make_campaign(name=raw_name))

        result = scenario.run()

        assert result["filename"] == expected_filename(campaign_name=sanitized)

    @pytest.mark.parametrize("raw_name, sanitized", _SANITIZATION_ROWS)
    def test_the_row_produces_a_structurally_safe_filename(
        self, export_scenario, raw_name, sanitized
    ):
        """Requirement 12.26, the four structural checks: no spaces, no ``/``
        and no ``\\``, no control characters and pure ASCII.

        This is the guarantee the NFR rests on — the value ends up in a
        ``Content-Disposition`` header, where a newline would allow header
        injection and a ``/`` would let the client write outside its download
        directory.
        """
        scenario = export_scenario(campaign=make_campaign(name=raw_name))

        result = scenario.run()

        assert_filename_is_safe(result["filename"])

    def test_the_cap_of_sixty_characters_is_applied_per_component(
        self, export_scenario
    ):
        """Requirement 10.12 step (f), stated as a length: the truncation caps
        the **component**, not the whole filename, so a long name shortens its
        own position and leaves the other three intact.
        """
        scenario = export_scenario(campaign=make_campaign(name="B" * 200))

        result = scenario.run()

        assert result["filename"] == expected_filename(campaign_name="B" * 60)
        assert result["filename"].count("B") == 60

    def test_truncation_never_leaves_a_trailing_separator_exposed(
        self, export_scenario
    ):
        """Requirement 10.12 step (f), second half: the characters ``_`` and
        ``.`` the truncation may leave at the end are trimmed again, so the
        component never ends in a bare separator.

        The raw name is 59 usable characters followed by a space and more text,
        so the naive cut would end exactly on the ``_`` that replaced the space.
        """
        raw_name = "C" * 59 + " cola"
        scenario = export_scenario(campaign=make_campaign(name=raw_name))

        result = scenario.run()

        assert result["filename"] == expected_filename(campaign_name="C" * 59)
        assert_filename_is_safe(result["filename"])

    def test_each_component_is_sanitized_independently(self, export_scenario):
        """Requirement 10.12: the four Nombres_de_Origen are sanitised one by
        one, so a dirty name in one position never alters another position.
        """
        scenario = export_scenario(
            campaign=make_campaign(name="Campaña Otoño"),
            ad_channel=make_ad_channel(
                ad_set_name="Prospecting / EU",
                ad_name="Retargeting  ##  01",
                channel_name="__facebook__",
            ),
        )

        result = scenario.run()

        assert result["filename"] == expected_filename(
            campaign_name="Campana_Otono",
            ad_set_name="Prospecting_EU",
            ad_name="Retargeting_01",
            channel_name="facebook",
        )
        assert_filename_is_safe(result["filename"])


# The four positions of the filename, each with the payload identifier that
# Requirement 10.13 forbids using as its fallback, and the keyword through
# which its Nombre_de_Origen is injected into the builders.
_MISSING_COMPONENT_POSITIONS = [
    pytest.param("campaign_name", "campaign_id", id="campaign_name"),
    pytest.param("ad_set_name", "adset_id", id="ad_set_name"),
    pytest.param("ad_name", "ad_id", id="ad_name"),
    pytest.param("channel_name", "adchannel_id", id="channel_name"),
]

# The four ways a Nombre_de_Origen can be unusable, as enumerated by
# Requirement 10.13: the key absent, the value ``None``, a value that is not a
# ``str`` instance, and a value that is left empty by the sanitisation of
# Requirement 10.12.
_UNUSABLE_SOURCE_NAMES = [
    pytest.param(ABSENT, id="key_absent"),
    pytest.param(None, id="none"),
    pytest.param(4242, id="not_a_str"),
    pytest.param("   ", id="blank_after_sanitisation"),
]

# The four labels the single ``logger.warning`` of Requirement 10.15 must name,
# in the order of the components.
_FILENAME_COMPONENT_LABELS = ("campaign_name", "ad_set_name", "ad_name",
                              "channel_name")


def build_missing_component_scenario(export_scenario, position, raw_name,
                                     payload=None):
    """Build an ``execute()`` scenario whose Nombre_de_Origen at ``position``
    holds ``raw_name`` and whose other three keep their clean defaults.

    Requirements: 10.13, 12.27
    """
    campaign_kwargs = {}
    ad_channel_kwargs = {}
    if position == "campaign_name":
        campaign_kwargs["name"] = raw_name
    else:
        ad_channel_kwargs[position] = raw_name
    return export_scenario(
        payload=make_export_payload() if payload is None else payload,
        campaign=make_campaign(**campaign_kwargs),
        ad_channel=make_ad_channel(**ad_channel_kwargs),
    )


class TestFilenameMissingComponents:
    """A missing Nombre_de_Origen yields the **empty component**, never the
    identifier of the Payload_de_Exportación that occupies the same position in
    the hierarchy (Requirement 10.13).

    Four positions × four ways of being unusable, plus the degenerate case of
    all four missing, which collapses to ``assets.zip`` (Requirement 10.14),
    plus the single ``logger.warning`` naming the empty components
    (Requirement 10.15).

    Requirements: 10.13, 10.14, 10.15, 12.27
    """

    @pytest.mark.parametrize("raw_name", _UNUSABLE_SOURCE_NAMES)
    @pytest.mark.parametrize("position, identifier_key",
                             _MISSING_COMPONENT_POSITIONS)
    def test_the_component_of_that_position_comes_out_empty(
        self, export_scenario, position, identifier_key, raw_name
    ):
        """Requirement 12.27: the component of the missing name is the empty
        string, in its own position, and ``execute()`` returns the
        Resultado_de_Exportación without raising.

        The call sits outside any ``pytest.raises``, so an unusable source name
        turned into an exception surfaces as an error of this very case.
        """
        scenario = build_missing_component_scenario(
            export_scenario, position, raw_name
        )

        result = scenario.run()

        assert set(result.keys()) == _EXPORT_RESULT_KEYS
        assert result["filename"] == expected_filename(**{position: ""})
        assert_filename_is_safe(result["filename"])

    @pytest.mark.parametrize("raw_name", _UNUSABLE_SOURCE_NAMES)
    @pytest.mark.parametrize("position, identifier_key",
                             _MISSING_COMPONENT_POSITIONS)
    def test_the_identifier_of_that_position_is_not_used_as_a_fallback(
        self, export_scenario, position, identifier_key, raw_name
    ):
        """Requirements 10.13, 12.27: the identifier of the
        Payload_de_Exportación associated with the missing position is **not**
        contained in ``filename``, and neither is any of the other four.

        This is the whole point of the empty component: the client sees that a
        name is missing, and no internal Strapi identifier leaves the server
        through the name of the downloaded file.
        """
        payload = make_export_payload()
        scenario = build_missing_component_scenario(
            export_scenario, position, raw_name, payload=payload
        )

        result = scenario.run()

        assert str(payload[identifier_key]) not in result["filename"]
        for identifier in payload.values():
            assert str(identifier) not in result["filename"]

    @pytest.mark.parametrize("raw_name", _UNUSABLE_SOURCE_NAMES)
    def test_the_four_names_missing_collapse_to_the_bare_fallback(
        self, export_scenario, raw_name
    ):
        """Requirements 10.14, 12.27: with the four Nombres_de_Origen unusable,
        ``filename`` equals — by exact string comparison — ``assets.zip``, with
        no separator and no empty component.

        Asserted for each of the four ways of being unusable, so the collapse
        does not depend on *how* the names went missing.
        """
        scenario = export_scenario(
            campaign=make_campaign(name=raw_name),
            ad_channel=make_ad_channel(
                ad_set_name=raw_name, ad_name=raw_name, channel_name=raw_name
            ),
        )

        result = scenario.run()

        assert result["filename"] == "assets.zip"
        assert_filename_is_safe(result["filename"])

    @pytest.mark.parametrize("position, identifier_key",
                             _MISSING_COMPONENT_POSITIONS)
    def test_a_single_warning_names_the_empty_component(
        self, export_scenario, position, identifier_key
    ):
        """Requirement 10.15: exactly **one** ``logger.warning`` per invocation
        of ``execute()``, naming which of the four components came out empty —
        not one warning per empty component, and never an exception.
        """
        scenario = build_missing_component_scenario(
            export_scenario, position, ABSENT
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            scenario.run()

        assert mock_logger.warning.call_count == 1
        logged = mock_logger.warning.call_args[0][0]
        assert position in logged
        for other_label in _FILENAME_COMPONENT_LABELS:
            if other_label != position:
                assert other_label not in logged

    def test_a_single_warning_names_the_four_empty_components(
        self, export_scenario
    ):
        """Requirement 10.15 with the four components empty: still a **single**
        warning, naming all four labels at once.
        """
        scenario = export_scenario(
            campaign=make_campaign(name=ABSENT),
            ad_channel=make_ad_channel(
                ad_set_name=ABSENT, ad_name=ABSENT, channel_name=ABSENT
            ),
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            scenario.run()

        assert mock_logger.warning.call_count == 1
        logged = mock_logger.warning.call_args[0][0]
        for label in _FILENAME_COMPONENT_LABELS:
            assert label in logged

    def test_the_main_flow_emits_no_warning_at_all(self, export_scenario):
        """Requirement 10.15 read the other way round: with the four
        Nombres_de_Origen present, there is nothing to warn about, so the count
        stays at zero.

        This is what makes the single-warning assertions above meaningful: the
        one recorded call can only come from the empty component.
        """
        scenario = export_scenario()

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            scenario.run()

        assert mock_logger.warning.call_count == 0

    def test_a_missing_name_does_not_alter_the_package_contents(
        self, export_scenario
    ):
        """Requirement 10.13: an unusable Nombre_de_Origen degrades the **name**
        of the Paquete_ZIP and nothing else — the six entries of the main flow
        are still there.
        """
        scenario = export_scenario(campaign=make_campaign(name=ABSENT))

        namelist, _ = scenario.run_zip()

        assert sorted(namelist) == _MAIN_FLOW_EXPECTED_NAMES


class TestCampaignNameExclusiveRead:
    """Requirement 4.6 at the ``execute()`` level: ``attributes.name`` is the
    **only** thing ever read from the campaign record.

    ``TestCampaignResolution`` proves the complementary half — ``_get_campaign``
    itself reads **zero** keys, since resolving the campaign is a mere
    existence-and-ownership check — and the read audited here happens later, in
    the derivation of the filename, which is why both expectations coexist
    without contradicting each other.

    Requirements: 4.6, 10.4
    """

    def test_only_attributes_and_then_name_are_read_from_the_campaign(
        self, export_scenario
    ):
        """Requirement 4.6: over a whole ``execute()``, the campaign record
        reports exactly one key read, ``attributes``, and its nested node
        reports exactly one, ``name``.

        Both levels are recording ``dict`` instances, so any extra
        ``campaign['x']``, ``campaign.get('x')`` or ``'x' in campaign`` — at
        either level — lands in ``reads`` and fails the assertion.
        """
        attributes = _RecordingDict({"name": _DEFAULT_CAMPAIGN_NAME})
        campaign = _RecordingDict({"id": 101, "attributes": attributes})
        scenario = export_scenario(campaign=campaign)

        result = scenario.run()

        assert campaign.reads == ["attributes"]
        assert attributes.reads == ["name"]
        assert result["filename"] == expected_filename()

    def test_the_unread_attributes_of_the_campaign_reach_no_entry(
        self, export_scenario
    ):
        """Requirement 4.6: the attributes the Caso_de_Uso must not read do not
        reach the Resultado_de_Exportación nor any entry of the Paquete_ZIP
        either — the record is a check and a name, never a data source.
        """
        unread_marker = "UNREADCAMPAIGNATTRIBUTE"
        campaign = make_campaign()
        campaign["attributes"]["budget"] = unread_marker
        campaign["attributes"]["objective"] = unread_marker
        scenario = export_scenario(campaign=campaign)

        result = scenario.run()

        assert unread_marker not in result["filename"]
        _, contents = read_zip(result["content"])
        for entry_content in contents.values():
            assert unread_marker not in entry_content.decode("utf-8", errors="ignore")


# The intermediate keys of the three read paths of Requirement 5.9, each with
# the filename components its degradation must empty. Degrading a key shared by
# two paths (everything from ``ad_ref2`` down to its ``attributes``) empties
# both components at once, which is exactly what Requirement 5.10 prescribes.
_NAME_PATH_DEGRADATIONS = [
    pytest.param(
        ("attributes", "ad_ref2"), ("ad_set_name", "ad_name"), id="ad_ref2",
    ),
    pytest.param(
        ("attributes", "ad_ref2", "data"), ("ad_set_name", "ad_name"),
        id="ad_ref2-data",
    ),
    pytest.param(
        ("attributes", "ad_ref2", "data", "attributes"),
        ("ad_set_name", "ad_name"),
        id="ad_ref2-data-attributes",
    ),
    pytest.param(
        ("attributes", "ad_ref2", "data", "attributes", "ad_set_ref2"),
        ("ad_set_name",),
        id="ad_set_ref2",
    ),
    pytest.param(
        ("attributes", "ad_ref2", "data", "attributes", "ad_set_ref2", "data"),
        ("ad_set_name",),
        id="ad_set_ref2-data",
    ),
    pytest.param(
        ("attributes", "ad_ref2", "data", "attributes", "ad_set_ref2", "data",
         "attributes"),
        ("ad_set_name",),
        id="ad_set_ref2-data-attributes",
    ),
    pytest.param(
        ("attributes", "channel_ref"), ("channel_name",), id="channel_ref",
    ),
    pytest.param(
        ("attributes", "channel_ref", "data"), ("channel_name",),
        id="channel_ref-data",
    ),
    pytest.param(
        ("attributes", "channel_ref", "data", "attributes"), ("channel_name",),
        id="channel_ref-data-attributes",
    ),
]

# The two ways an intermediate key of Requirement 5.10 can be degraded: absent,
# or present with a value that is not a ``dict`` instance. ``True`` and ``0``
# are here because a walk written with ``or {}`` fallbacks instead of an
# ``isinstance`` check would call ``.get`` on them and raise ``AttributeError``.
_DEGRADED_NODE_VALUES = [
    pytest.param(ABSENT, id="absent"),
    pytest.param(None, id="none"),
    pytest.param("not-a-dict", id="string"),
    pytest.param(0, id="zero"),
    pytest.param(True, id="true"),
    pytest.param([], id="empty_list"),
]


class TestNamePopulationWiring:
    """The wiring that brings the three name relations into the single
    ``ad-channels`` query, and its behaviour when the populated shape is not the
    one expected.

    Two halves, both required by Requirement 12.28: the invocation carrying the
    four positional identifiers of Requirement 5.1 plus the activated
    name-population flag of Requirement 5.7, and the degradation of every
    intermediate key of the three read paths of Requirement 5.9, which must
    yield the empty component of Requirement 10.13 without raising
    (Requirement 5.10).

    Requirements: 5.1, 5.7, 5.9, 5.10, 10.13, 12.28
    """

    def test_the_single_query_carries_the_four_identifiers_and_the_flag(
        self, export_scenario
    ):
        """Requirement 12.28(a): exactly **one** invocation of
        ``get_by_campaign_and_ad_channel_id``, whose four first positional
        arguments are those of Requirement 5.1 and in which the optional
        parameter of Requirement 5.7 is activated.

        The flag travels as a keyword argument and the identifiers positionally,
        so ``recorded_args`` still holds exactly four values: the population of
        the names adds no fifth identifier and reorders nothing.
        """
        payload = make_export_payload()
        scenario = export_scenario(payload=payload)

        scenario.run()

        query = scenario.ad_channel_repo.get_by_campaign_and_ad_channel_id
        assert query.call_count == 1
        recorded_args, recorded_kwargs = query.call_args
        assert len(recorded_args) == 4
        assert recorded_args[0] is payload["campaign_id"]
        assert recorded_args[1] is payload["adset_id"]
        assert recorded_args[2] is payload["ad_id"]
        assert recorded_args[3] is payload["adchannel_id"]
        assert recorded_kwargs == {"populate_names": True}

    def test_the_population_adds_no_second_query(self, export_scenario):
        """Requirement 5.7: the three names come from the query that already
        resolved the creative, so the number of invocations recorded by the
        ``AdChannelRepository`` double — counting every method — stays at one.
        """
        scenario = export_scenario()

        scenario.run()

        assert len(scenario.ad_channel_repo.mock_calls) == 1

    @pytest.mark.parametrize("value", _DEGRADED_NODE_VALUES)
    @pytest.mark.parametrize("path, emptied_components",
                             _NAME_PATH_DEGRADATIONS)
    def test_a_degraded_intermediate_key_empties_only_its_components(
        self, export_scenario, path, emptied_components, value
    ):
        """Requirements 5.10, 12.28(b): an intermediate key of one of the three
        read paths that is absent, or whose value is not a ``dict`` instance,
        yields the empty component of Requirement 10.13 for the names that
        depend on it and leaves the others untouched.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel(degraded_paths=[(path, value)])
        )

        result = scenario.run()

        expected = expected_filename(
            **{component: "" for component in emptied_components}
        )
        assert result["filename"] == expected
        assert_filename_is_safe(result["filename"])

    @pytest.mark.parametrize("value", _DEGRADED_NODE_VALUES)
    @pytest.mark.parametrize("path, emptied_components",
                             _NAME_PATH_DEGRADATIONS)
    def test_a_degraded_intermediate_key_raises_nothing(
        self, export_scenario, path, emptied_components, value
    ):
        """Requirements 5.10, 12.28(b): ``execute()`` returns the
        Resultado_de_Exportación without raising and without an error log, so a
        malformed populated relation degrades the name and never the outcome of
        the export.

        The invocation sits outside any ``pytest.raises``: an ``AttributeError``
        or a ``TypeError`` escaping the defensive walk surfaces as an error of
        this very case.
        """
        scenario = export_scenario(
            ad_channel=make_ad_channel(degraded_paths=[(path, value)])
        )

        with patch("app.v2.use_cases.meta_ads.logger") as mock_logger:
            result = scenario.run()

        assert set(result.keys()) == _EXPORT_RESULT_KEYS
        assert isinstance(result["content"], bytes)
        assert mock_logger.error.call_count == 0

    @pytest.mark.parametrize("path, emptied_components",
                             _NAME_PATH_DEGRADATIONS)
    def test_a_degraded_intermediate_key_leaks_no_identifier(
        self, export_scenario, path, emptied_components
    ):
        """Requirements 10.13, 12.28(b): the components emptied by the
        degradation are **not** replaced by the identifiers of the
        Payload_de_Exportación that occupy those positions.
        """
        payload = make_export_payload()
        scenario = export_scenario(
            payload=payload,
            ad_channel=make_ad_channel(degraded_paths=[(path, ABSENT)]),
        )

        result = scenario.run()

        for identifier in payload.values():
            assert str(identifier) not in result["filename"]

    def test_the_channel_id_still_travels_next_to_the_populated_name(
        self, export_scenario
    ):
        """Requirement 5.3 alongside Requirement 5.9: the population of
        ``channel_ref.attributes.name`` does not displace the ``id`` the
        Channel_ID is read from — both live in ``channel_ref.data``.
        """
        payload = make_export_payload()
        scenario = export_scenario(
            payload=payload,
            ad_channel=make_ad_channel(channel_ref_id=9, channel_name="instagram"),
        )

        result = scenario.run()

        (
            scenario.campaign_publish_repo.get_by_campaign_id_and_channel_id
            .assert_called_once_with(payload["campaign_id"], 9)
        )
        assert result["filename"] == expected_filename(channel_name="instagram")

    def test_the_populated_record_is_read_without_being_modified(
        self, export_scenario
    ):
        """Requirement 5.9: the three reads leave the Ad_Channel_de_Exportación
        exactly as it arrived, so nothing downstream can depend on a mutation
        performed while naming the package.
        """
        ad_channel = make_ad_channel()
        snapshot = make_ad_channel()
        scenario = export_scenario(ad_channel=ad_channel)

        scenario.run()

        assert ad_channel == snapshot

    def test_an_absent_attributes_node_empties_the_three_populated_names(
        self, export_scenario
    ):
        """Requirement 5.10 applied to the outermost intermediate key of the
        three paths: with no ``attributes`` node at all, the three names of the
        creative come out empty and only the campaign name survives.
        """
        scenario = export_scenario(ad_channel=make_ad_channel(attributes=ABSENT))

        result = scenario.run()

        assert result["filename"] == expected_filename(
            ad_set_name="", ad_name="", channel_name=""
        )
        assert_filename_is_safe(result["filename"])


# ---------------------------------------------------------------------------
# Self-audit of the suite (Requirements 12.1, 12.23, 12.24)
# ---------------------------------------------------------------------------

# The single authorized location of this suite, relative to the ``sinergia/``
# working directory, and the exact target of the validation command.
_AUTHORIZED_SUITE_RELATIVE_PATH = os.path.join(
    'tests', 'v2', 'unit', 'use_cases',
    'test_facebook_export_assets_post_launch_campaign.py',
)

# The complete validation command, reproduced verbatim, whose target must be
# this very module.
_VALIDATION_COMMAND = (
    './venv/bin/python -m pytest -q -ra '
    'tests/v2/unit/use_cases/test_facebook_export_assets_post_launch_campaign.py'
)

# Every acceptance criterion of Requirement 12, from the first to the last. The
# range grew from 24 to 29 with the correction of the name of the Paquete_ZIP
# (OQ-9), which added the criteria 12.25 to 12.29.
_REQUIREMENT_12_CRITERIA = tuple(range(1, 30))

# Every construct through which pytest can report a case as skipped or as an
# expected failure. The suite must declare none of them.
#
# The needles are assembled from fragments on purpose: spelled out literally
# they would appear in this very module, which is the text the audit reads, and
# the case would fail against its own constants.
_SKIP_AND_XFAIL_CONSTRUCTS = (
    'mark.' + 'skip',       # covers the decorator and the ``marks=`` form
    'mark.' + 'xfail',      # idem, conditional variants included
    'pytest' + '.skip(',    # imperative skip from inside a case
    'pytest' + '.xfail(',   # imperative expected failure
    'pytest' + '.importorskip(',
)


def read_suite_source():
    """Return the source text of this very module, read from disk."""
    with open(os.path.abspath(__file__), encoding='utf-8') as handle:
        return handle.read()


def criteria_covered_by_test_cases(source):
    """Map every criterion of Requirement 12 to the test cases that name it.

    A criterion counts as covered only when its reference sits **inside the
    body of a test function**, never when it appears only in the module
    docstring or in a class docstring: the obligation of Requirement 12.23 is
    one test *case* per criterion, not one mention per criterion.
    """
    covered = {}
    current_class = None
    current_case = None
    for line in source.split('\n'):
        if line and not line[0].isspace():
            # Any statement at column zero closes the class and the method
            # currently open, so module level text is never attributed to the
            # last case of the preceding class.
            current_class = None
            current_case = None
        class_match = re.match(r'^class (\w+)', line)
        if class_match:
            current_class = class_match.group(1)
            current_case = None
        method_match = re.match(r'^    def (\w+)', line)
        if method_match:
            name = method_match.group(1)
            current_case = name if name.startswith('test_') else None
        if current_case is None or 'Requirement' not in line:
            continue
        for number in re.findall(r'12\.(\d+)', line):
            covered.setdefault(int(number), set()).add(
                '{}::{}'.format(current_class, current_case)
            )
    return covered


class TestSuiteSelfAudit:
    """The three structural criteria of Requirement 12 that no functional case
    can assert: the location of the suite (12.1), the coverage of every
    criterion by at least one case and the absence of skipped or expected
    failures (12.23), and the target of the validation command (12.24).

    These read the source of this very module rather than the behaviour of the
    Caso_de_Uso, which is precisely why they live apart from every other class
    of the suite.

    Requirements: 12.1, 12.23, 12.24
    """

    def test_the_suite_resides_at_the_single_authorized_path(self):
        """Requirement 12.1: the suite is the file
        ``sinergia/tests/v2/unit/use_cases/test_facebook_export_assets_post_launch_campaign.py``.

        Asserted against the real path of the loaded module, so moving or
        renaming the file breaks the case instead of silently relocating the
        only test artifact the specification authorizes.
        """
        suite_path = os.path.abspath(__file__)

        assert suite_path.endswith(_AUTHORIZED_SUITE_RELATIVE_PATH)
        assert os.path.isfile(suite_path)
        assert os.path.basename(os.path.dirname(suite_path)) == 'use_cases'

    def test_the_validation_command_targets_this_very_module(self):
        """Requirement 12.24: the target of the validation command is this
        module, expressed relative to the ``sinergia/`` working directory.
        """
        target = _VALIDATION_COMMAND.split()[-1]

        assert target == _AUTHORIZED_SUITE_RELATIVE_PATH.replace(os.sep, '/')
        assert os.path.abspath(__file__).endswith(target.replace('/', os.sep))
        assert '-q' in _VALIDATION_COMMAND.split()
        assert '-ra' in _VALIDATION_COMMAND.split()

    def test_every_criterion_of_requirement_12_is_covered_by_a_test_case(self):
        """Requirement 12.23, the coverage half: each of the twenty-nine
        criteria of Requirement 12 is named by at least one test case of this
        suite, this self-audit included.

        The five criteria added by the correction of the name of the
        Paquete_ZIP — 12.25 to 12.29 — are audited exactly like the twenty-four
        that preceded them, so the correction cannot close with a criterion left
        without a case.
        """
        covered = criteria_covered_by_test_cases(read_suite_source())

        uncovered = [
            number for number in _REQUIREMENT_12_CRITERIA if not covered.get(number)
        ]
        assert uncovered == []
        assert len(_REQUIREMENT_12_CRITERIA) == 29

    def test_the_suite_declares_no_skip_and_no_expected_failure(self):
        """Requirement 12.23, the zero-skip half: the suite declares no
        construct able to report a case as skipped or as an expected failure,
        so the count of both stays at zero for Requirement 12.24.
        """
        source = read_suite_source()

        declared = [
            construct
            for construct in _SKIP_AND_XFAIL_CONSTRUCTS
            if construct in source
        ]
        assert declared == []
