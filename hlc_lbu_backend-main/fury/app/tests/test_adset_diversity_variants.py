"""Unit tests for the Variant_Slot shape validation and variant_key merge helpers of
services/adset_diversity.py (adset-creative-diversity, task 6.9).
Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_variants.py
"""
import json

from agents.tools.abyssale_tools import build_abyssale_payload
from services.ads_validators import (
    validate_copywriter_response,
    validate_image_prompter_response,
)
from services.adset_diversity import (
    build_variant_proposals,
    build_variant_slots,
    check_variant_items,
    make_variant_validator,
    merge_by_variant_key,
    merge_variant_creative,
)

PLAN_ID = "plan_ad_7"
# P11: one template per Ad, so both variants of ad_slot 0 share "tA"; variants are
# told apart only by variant_key.
SLOTS = build_variant_slots(PLAN_ID, ad_slot=0, n_variants=2, project_templates=["tA", "tB"])


def _copy(slot, headline="H"):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "headline": [headline],
        "primary_text": ["P"],
        "description": ["D"],
        "cta": ["LEARN_MORE"],
        "template_elements": [{"element_id": "title", "text": headline}],
    }


def _prompt(slot):
    return {
        "plan_id": PLAN_ID,
        "variant_key": slot["variant_key"],
        "template_id": slot["template_id"],
        "image_prompts": [{"element_id": "img", "image_prompt": "x", "image_request": "y"}],
    }


def _plan():
    return {"id": PLAN_ID, "concept": "c", "variants": [dict(s) for s in SLOTS]}


# --- check_variant_items ---------------------------------------------------

def test_check_variant_items_accepts_reordered_valid_items():
    items = [_copy(SLOTS[1]), _copy(SLOTS[0])]
    assert check_variant_items(items, SLOTS, PLAN_ID, kind="copy") == []


def test_check_variant_items_rejects_bad_shapes():
    good = [_copy(s) for s in SLOTS]
    assert check_variant_items([], SLOTS, PLAN_ID, kind="copy")
    assert check_variant_items(good[:1], SLOTS, PLAN_ID, kind="copy")
    assert check_variant_items([good[0], good[0]], SLOTS, PLAN_ID, kind="copy")
    no_key = [dict(good[0]), good[1]]
    del no_key[0]["variant_key"]
    assert check_variant_items(no_key, SLOTS, PLAN_ID, kind="copy")
    assert check_variant_items([{**good[0], "plan_id": "plan_ad_8"}, good[1]],
                               SLOTS, PLAN_ID, kind="copy")
    assert check_variant_items([{**good[0], "template_id": "tB"}, good[1]],
                               SLOTS, PLAN_ID, kind="copy")
    assert check_variant_items([{**good[0], "variant_key": "plan_ad_7_v9"}, good[1]],
                               SLOTS, PLAN_ID, kind="image_prompt")


# --- make_variant_validator ------------------------------------------------

def test_make_variant_validator_copy_and_image_prompt():
    copy_validator = make_variant_validator(validate_copywriter_response, SLOTS, PLAN_ID, kind="copy")
    ok = copy_validator(json.dumps([_copy(s) for s in SLOTS]))
    assert ok.is_valid and len(ok.data) == 2

    empty = copy_validator("[]")  # base validator accepts it; shape check must not
    assert not empty.is_valid and empty.error_code == "ERR_VARIANT_SHAPE"

    prompt_validator = make_variant_validator(validate_image_prompter_response, SLOTS, PLAN_ID,
                                              kind="image_prompt")
    bad = prompt_validator(json.dumps([_prompt(SLOTS[0])]))
    assert not bad.is_valid and bad.error_code == "ERR_VARIANT_SHAPE"


def test_make_variant_validator_keeps_base_failure():
    validator = make_variant_validator(validate_copywriter_response, SLOTS, PLAN_ID, kind="copy")
    result = validator("not json")
    assert not result.is_valid and result.error_code == "ERR_INVALID_JSON"


# --- merge helpers ---------------------------------------------------------

def test_merge_by_variant_key_replaces_only_regenerated():
    previous = [_copy(s, "old") for s in SLOTS]
    regenerated = [_copy(SLOTS[1], "new")]
    merged = merge_by_variant_key(previous, regenerated, SLOTS)
    assert [c["variant_key"] for c in merged] == [s["variant_key"] for s in SLOTS]
    assert merged[0]["headline"] == ["old"] and merged[1]["headline"] == ["new"]


def test_build_variant_proposals_one_per_slot():
    copies = [_copy(SLOTS[1], "b"), _copy(SLOTS[0], "a")]
    prompts = [_prompt(SLOTS[1]), _prompt(SLOTS[0])]
    proposals = build_variant_proposals(_plan(), copies, prompts, ad_id=7)
    assert [p["variant_key"] for p in proposals] == ["plan_ad_7_v1", "plan_ad_7_v2"]
    assert [p["copy"]["headline"] for p in proposals] == [["a"], ["b"]]
    assert all(p["plan_id"] == PLAN_ID and p["ad_id"] == 7 for p in proposals)
    # P11: every proposal carries the Ad_Template of the slot it was matched to.
    assert [p["template_id"] for p in proposals] == [s["template_id"] for s in SLOTS] == ["tA", "tA"]
    assert all(p["image_prompts"] for p in proposals)


def test_merge_variant_creative_feeds_abyssale_per_variant():
    copies = [_copy(SLOTS[1], "b"), _copy(SLOTS[0], "a")]
    images = [{"plan_id": PLAN_ID, "variant_key": SLOTS[1]["variant_key"], "image_prompts": []}]
    saved = [{"plan_id": PLAN_ID, "variant_key": s["variant_key"], "ad_id": f"ch{i}", "saved": True}
             for i, s in enumerate(SLOTS)]
    merged = merge_variant_creative(_plan(), copies, images, saved, ad_id=7)

    assert [m["plan"]["id"] for m in merged] == ["plan_ad_7_v1", "plan_ad_7_v2"]
    assert merged[0]["image"] == {} and merged[1]["image"] is images[0]
    assert "error" not in merged[0] and "error" not in merged[1]

    payload = build_abyssale_payload(merged, SLOTS[0]["template_id"], "4:5")["payload"]
    elements = payload["elements"]
    assert [e["metadata"]["plan_id"] for e in elements] == ["plan_ad_7_v1", "plan_ad_7_v2"]
    assert [e["template_id"] for e in elements] == ["tA", "tA"]  # P11: one template per Ad
    # Each element carries the copy of its own variant (matched by variant_key, not position).
    assert [e["metadata"]["plan_id"] for e in elements] == [s["variant_key"] for s in SLOTS]
    assert [e["ad_channel_id"] for e in elements] == ["ch0", "ch1"]


def test_merge_variant_creative_marks_missing_copy():
    merged = merge_variant_creative(_plan(), [_copy(SLOTS[0])], [], [], ad_id=7)
    assert "error" not in merged[0]
    assert "error" in merged[1] and merged[1]["variant_key"] == "plan_ad_7_v2"
    payload = build_abyssale_payload(merged, "tA", "4:5")["payload"]
    assert len(payload["elements"]) == 1
