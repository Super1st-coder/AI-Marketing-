"""Tests for ``MetaAdsPayloadBuilder`` ``ad_channel_id`` propagation.

Target under test: ``app.v2.use_cases.facebook_validator_service.MetaAdsPayloadBuilder.build_creative``
(STANDARD branch), which since Requirement 11 assigns
``ad_channel_id=asset_feed_spec.ad_channel_id if asset_feed_spec else None`` to
the ``ObjectStorySpec`` it constructs.

This file is deliberately separate from
``test_facebook_generate_pre_check_creative.py``: per ``design.md`` (decision 6
and the "Testing Strategy" section), Requirement 11 characterizes a distinct
collaborator (``MetaAdsPayloadBuilder``, in ``facebook_validator_service.py``),
not the STANDARD branch of ``FacebookGeneratePreCheckCreativeUseCase.execute()``
to which Requirement 1.3 acotates the main test file.

Validates: Requirements 11.1, 11.2 -- Property 7 (builder branch) per design.md.
"""

from unittest.mock import patch

import pytest
from hypothesis import given, settings, strategies as st

from app.v2.use_cases.facebook_validator_service import (
    AssetFeedSpec,
    CreativeType,
    MetaAdsPayloadBuilder,
)


@pytest.fixture(autouse=True)
def _mock_strapi_client():
    """Isolate ``MetaAdsPayloadBuilder`` from a real Strapi connection.

    ``MetaAdsPayloadBuilder.__init__`` unconditionally instantiates
    ``StrapiClient()``. Neither ``build_creative`` nor ``build_asset_feed_spec``
    call it directly for the scenarios exercised here (they only operate on the
    ``ad`` dict passed in, and ``build_asset_feed_spec`` itself is patched per
    test below), but the constructor call must still never touch a real
    Strapi instance.
    """
    with patch(
        "app.v2.use_cases.facebook_validator_service.StrapiClient"
    ) as strapi_client_mock:
        yield strapi_client_mock


def make_builder(creative_type=CreativeType.STANDARD.value):
    """Build a fresh ``MetaAdsPayloadBuilder`` with a Strapi-isolated constructor."""
    return MetaAdsPayloadBuilder(
        campaign_id="campaign-1",
        campaign_objective="OUTCOME_AWARENESS",
        optimization_goal="REACH",
        creative_type=creative_type,
    )


def make_ad(**overrides):
    """Build a minimal ``ad`` dict sufficient for ``build_creative``.

    ``build_asset_feed_spec`` is patched in every test below, so this dict
    only needs to satisfy ``build_creative``'s own direct access
    (``ad['attributes']['name']``).
    """
    attributes = {"name": "Ad 1"}
    attributes.update(overrides)
    return {"attributes": attributes}


class TestBuildCreativeStandardAdChannelIdPropagation:
    """Property 7 (builder branch): ``ad_channel_id`` propagation from
    ``MetaAdsPayloadBuilder.build_asset_feed_spec()`` into the
    ``ObjectStorySpec`` built by ``build_creative()`` for the STANDARD
    creative type.

    Validates: Requirements 11.1, 11.2.
    """

    # Feature: meta-ads-standard-precheck-validation, Property 7 (builder branch):
    # For every ad_channel_id value (None, 0, or an arbitrary positive integer)
    # assigned to a synthetic AssetFeedSpec inside
    # MetaAdsPayloadBuilder.build_creative with creative_type=STANDARD, the
    # resulting ObjectStorySpec SHALL have ad_channel_id identical to that
    # value, without raising an exception.
    @settings(max_examples=100, deadline=None)
    @given(
        ad_channel_id=st.one_of(
            st.none(),
            st.integers(min_value=0, max_value=2**31 - 1),
        )
    )
    def test_property_ad_channel_id_propagates_identically(self, ad_channel_id):
        builder = make_builder()
        synthetic_asset_feed_spec = AssetFeedSpec(ad_channel_id=ad_channel_id)

        with patch.object(
            builder, "build_asset_feed_spec", return_value=synthetic_asset_feed_spec
        ):
            creative = builder.build_creative(make_ad())

        assert creative.object_story_spec.ad_channel_id == ad_channel_id

    def test_ad_channel_id_none_propagates_as_none(self):
        """Explicit example: ``ad_channel_id=None`` on the source
        ``AssetFeedSpec`` propagates as ``None`` on ``ObjectStorySpec``."""
        builder = make_builder()
        synthetic_asset_feed_spec = AssetFeedSpec(ad_channel_id=None)

        with patch.object(
            builder, "build_asset_feed_spec", return_value=synthetic_asset_feed_spec
        ):
            creative = builder.build_creative(make_ad())

        assert creative.object_story_spec.ad_channel_id is None

    def test_ad_channel_id_zero_propagates_as_zero(self):
        """Explicit example: ``ad_channel_id=0`` propagates as ``0``, not as
        an absent/falsy default -- ``0`` is a legitimate channel id."""
        builder = make_builder()
        synthetic_asset_feed_spec = AssetFeedSpec(ad_channel_id=0)

        with patch.object(
            builder, "build_asset_feed_spec", return_value=synthetic_asset_feed_spec
        ):
            creative = builder.build_creative(make_ad())

        assert creative.object_story_spec.ad_channel_id == 0
        assert creative.object_story_spec.ad_channel_id is not None

    @pytest.mark.parametrize("ad_channel_id", [1, 42, 123456])
    def test_ad_channel_id_positive_integers_propagate_unchanged(self, ad_channel_id):
        """Explicit examples: positive integer ``ad_channel_id`` values
        propagate unchanged onto the resulting ``ObjectStorySpec``."""
        builder = make_builder()
        synthetic_asset_feed_spec = AssetFeedSpec(ad_channel_id=ad_channel_id)

        with patch.object(
            builder, "build_asset_feed_spec", return_value=synthetic_asset_feed_spec
        ):
            creative = builder.build_creative(make_ad())

        assert creative.object_story_spec.ad_channel_id == ad_channel_id

    def test_build_asset_feed_spec_returning_none_yields_ad_channel_id_none(self):
        """When ``build_asset_feed_spec()`` returns ``None`` (e.g. no
        ``ad_channels_data``/selected channel), ``ObjectStorySpec.ad_channel_id``
        SHALL be ``None``, without raising an exception (Requirement 11.2)."""
        builder = make_builder()

        with patch.object(builder, "build_asset_feed_spec", return_value=None):
            creative = builder.build_creative(make_ad())

        assert creative.object_story_spec.ad_channel_id is None

    def test_dynamic_branch_object_story_spec_never_receives_ad_channel_id(self):
        """Sanity check confirming isolation from the DYNAMIC branch: Requirement
        11 only applies to STANDARD, so a DYNAMIC ``ObjectStorySpec`` keeps its
        ``ad_channel_id`` default (``None``) regardless of the source
        ``AssetFeedSpec``'s value."""
        builder = make_builder(creative_type=CreativeType.DYNAMIC.value)
        synthetic_asset_feed_spec = AssetFeedSpec(ad_channel_id=99)

        with patch.object(
            builder, "build_asset_feed_spec", return_value=synthetic_asset_feed_spec
        ):
            creative = builder.build_creative(make_ad())

        assert creative.asset_feed_spec is synthetic_asset_feed_spec
        assert creative.object_story_spec.ad_channel_id is None
