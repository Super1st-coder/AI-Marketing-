"""Tests for the OUTCOME_LEADS + OFFSITE_CONVERSIONS support in the validator service.

Covers Requirement 1 of the ``meta-ads-leads-offsite-conversions`` spec.
"""

from typing import Optional

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.v2.use_cases.facebook_validator_service import (
    LEADS_ALLOWED_CONVERSION_EVENTS,
    LEADS_GOAL_ALLOWED_CTAS,
    SALES_ALLOWED_CUSTOM_EVENTS,
    LeadsOptimizationGoal,
    MetaAdsValidator,
)

OBJECTIVE = "OUTCOME_LEADS"
GOAL = "OFFSITE_CONVERSIONS"

# Independent oracle: the exact CTAs_Leads_Offsite set from the Glossary.
EXPECTED_LEADS_OFFSITE_CTAS = frozenset({
    "LEARN_MORE", "SIGN_UP", "SUBSCRIBE", "ORDER_NOW", "SHOP_NOW", "APPLY_NOW",
    "BOOK_NOW", "CONTACT_US", "GET_OFFER", "GET_QUOTE", "DOWNLOAD", "SEE_MENU",
    "SEE_DETAILS", "GET_SHOWTIMES", "REQUEST_TIME", "BUY_TICKETS", "LISTEN_NOW",
    "PLAY_GAME", "WATCH_MORE", "NO_BUTTON",
})


def _reference_normalize(value: Optional[str]) -> str:
    """Reference normalization as defined by Requirement 1.5."""
    if not value:
        return ""
    return value.strip().upper().replace(" ", "_")


@st.composite
def cta_variants(draw, cta: str) -> str:
    """Variant of ``cta``: per-char case flips, ``_`` -> `` `` swaps and space padding."""
    chars = []
    for ch in cta:
        if ch == "_" and draw(st.booleans()):
            chars.append(" ")
        elif draw(st.booleans()):
            chars.append(ch.lower())
        else:
            chars.append(ch.upper())
    left = draw(st.text(alphabet=" ", max_size=3))
    right = draw(st.text(alphabet=" ", max_size=3))
    return f"{left}{''.join(chars)}{right}"


allowed_cta_variants = st.sampled_from(sorted(EXPECTED_LEADS_OFFSITE_CTAS)).flatmap(cta_variants)
blank_ctas = st.one_of(st.none(), st.just(""), st.text(alphabet=" \t\n", min_size=1, max_size=5))
any_cta = st.one_of(
    allowed_cta_variants,
    blank_ctas,
    st.sampled_from(["WHATSAPP_MESSAGE", "CALL_NOW", "MESSAGE_PAGE"]).flatmap(cta_variants),
    st.text(),
)


class TestLeadsOffsiteCtaValidation:
    """Property 1 and examples for ``validate_cta_for_goal`` with Leads_Offsite."""

    # Feature: meta-ads-leads-offsite-conversions, Property 1: Validación de CTA para Combinación_Leads_Offsite
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(cta=any_cta)
    def test_property_cta_validation_matches_reference_model(self, cta):
        """**Validates: Requirements 1.5, 1.6, 1.7**"""
        normalized = _reference_normalize(cta)
        expected = normalized in EXPECTED_LEADS_OFFSITE_CTAS

        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is expected

        if expected:
            assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=True) is True
            return

        with pytest.raises(ValueError) as exc_info:
            MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=True)
        if not normalized:
            assert str(exc_info.value) == "CTA is required but was empty"
        else:
            assert str(exc_info.value) == (
                f"CTA '{normalized}' not allowed for objective '{OBJECTIVE}' and goal '{GOAL}'"
            )

    @pytest.mark.parametrize("cta", ["learn more", " SEE_MENU ", "Sign_Up", "no button"])
    def test_variants_of_allowed_ctas_are_accepted(self, cta):
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is True

    @pytest.mark.parametrize("cta", ["WHATSAPP_MESSAGE", "CALL_NOW"])
    def test_disallowed_ctas_are_rejected(self, cta):
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is False
        with pytest.raises(ValueError, match=rf"^CTA '{cta}' not allowed for objective 'OUTCOME_LEADS' and goal 'OFFSITE_CONVERSIONS'$"):
            MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=True)

    @pytest.mark.parametrize("cta", [None, "", "   "])
    def test_blank_ctas_are_rejected_as_empty(self, cta):
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is False
        with pytest.raises(ValueError, match=r"^CTA is required but was empty$"):
            MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=True)


class TestLeadsOffsiteConstants:
    """Unit tests for the validator constants touched by Requirement 1."""

    def test_leads_enum_has_exactly_four_members_with_identical_values(self):
        """**Validates: Requirements 1.1**"""
        assert {m.name: m.value for m in LeadsOptimizationGoal} == {
            "LEAD_GENERATION": "LEAD_GENERATION",
            "QUALITY_LEAD": "QUALITY_LEAD",
            "CONVERSATIONS": "CONVERSATIONS",
            "OFFSITE_CONVERSIONS": "OFFSITE_CONVERSIONS",
        }

    def test_leads_conversion_events_are_exactly_seven(self):
        """**Validates: Requirements 1.2**"""
        assert isinstance(LEADS_ALLOWED_CONVERSION_EVENTS, set)
        assert LEADS_ALLOWED_CONVERSION_EVENTS == {
            "COMPLETE_REGISTRATION", "LEAD", "CONTACT", "SUBMIT_APPLICATION",
            "SCHEDULE", "SUBSCRIBE", "START_TRIAL",
        }

    def test_sales_custom_events_unchanged(self):
        """**Validates: Requirements 1.2, 1.9**"""
        assert SALES_ALLOWED_CUSTOM_EVENTS == {
            "PURCHASE", "INITIATE_CHECKOUT", "ADD_TO_CART", "ADD_TO_WISHLIST",
            "VIEW_CONTENT", "SUBSCRIBE", "START_TRIAL",
        }

    def test_leads_offsite_ctas_are_exactly_twenty(self):
        """**Validates: Requirements 1.3**"""
        ctas = LEADS_GOAL_ALLOWED_CTAS[LeadsOptimizationGoal.OFFSITE_CONVERSIONS.value]
        assert len(ctas) == 20
        assert set(ctas) == EXPECTED_LEADS_OFFSITE_CTAS

    def test_previous_leads_cta_entries_untouched(self):
        """**Validates: Requirements 1.3, 1.9**"""
        assert set(LEADS_GOAL_ALLOWED_CTAS) == {
            "LEAD_GENERATION", "QUALITY_LEAD", "CONVERSATIONS", "OFFSITE_CONVERSIONS",
        }
        assert LEADS_GOAL_ALLOWED_CTAS["LEAD_GENERATION"] == {
            "SIGN_UP", "APPLY_NOW", "DOWNLOAD", "GET_QUOTE", "LEARN_MORE", "SUBSCRIBE",
        }
        assert LEADS_GOAL_ALLOWED_CTAS["QUALITY_LEAD"] == {
            "SIGN_UP", "APPLY_NOW", "BOOK_NOW", "DOWNLOAD", "GET_QUOTE", "LEARN_MORE",
        }
        assert LEADS_GOAL_ALLOWED_CTAS["CONVERSATIONS"] == {"WHATSAPP_MESSAGE"}

    def test_leads_offsite_ctas_are_subset_of_valid_cta_values(self):
        """**Validates: Requirements 1.8**"""
        assert {"SEE_MENU", "SEE_DETAILS"} <= MetaAdsValidator.VALID_CTA_VALUES
        assert EXPECTED_LEADS_OFFSITE_CTAS <= MetaAdsValidator.VALID_CTA_VALUES

    @pytest.mark.parametrize("throw", [True, False])
    def test_offsite_conversions_is_valid_goal_for_leads(self, throw):
        """**Validates: Requirements 1.4**"""
        assert MetaAdsValidator.validate_optimization_goal_for_objective(GOAL, OBJECTIVE, throw=throw) is True

    def test_offsite_conversions_still_invalid_for_awareness(self):
        """**Validates: Requirements 1.9**"""
        assert MetaAdsValidator.validate_optimization_goal_for_objective(
            "OFFSITE_CONVERSIONS", "OUTCOME_AWARENESS", throw=False
        ) is False

    @pytest.mark.parametrize("cta", sorted(EXPECTED_LEADS_OFFSITE_CTAS))
    def test_each_leads_offsite_cta_is_valid(self, cta):
        """**Validates: Requirements 14.7**"""
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is True
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=True) is True

    @pytest.mark.parametrize("cta", ["CALL_NOW", "WHATSAPP_MESSAGE"])
    def test_non_leads_offsite_ctas_are_invalid(self, cta):
        """**Validates: Requirements 14.7**"""
        assert MetaAdsValidator.validate_cta_for_goal(cta, OBJECTIVE, GOAL, throw=False) is False
