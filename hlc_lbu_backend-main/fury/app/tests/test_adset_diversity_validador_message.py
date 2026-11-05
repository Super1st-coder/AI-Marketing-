"""Tests of the message to the Validador_Adset (adset-creative-diversity, P13, D21):
``build_validador_message`` / ``build_validador_views`` of services/adset_diversity.py.

- Property 14 (task 26.3): content of the message.
- Unit tests of Req 12.21 (task 26.4).

Run with:
    PYTHONPATH=. pytest tests/test_adset_diversity_validador_message.py
    PYTHONPATH=. python tests/test_adset_diversity_validador_message.py
"""
import copy
import json

from hypothesis import given, settings
from hypothesis import strategies as st

from services.adset_diversity import (
    FULL_ADSET_CONTEXT_HEADER,
    VALIDADOR_VIEW_COPY_FIELDS,
    VALIDADOR_VIEW_PROMPT_FIELDS,
    _plan_payload,
    build_validador_message,
    build_validador_view,
    build_validador_views,
    build_variant_proposals,
    build_variant_slots,
)

# ---------------------------------------------------------------------------
# Shared constants and helpers (Property 14 and unit tests)
# ---------------------------------------------------------------------------

CHECK_A = "(a) every variant respects the creative plan"
CHECK_B = "(b) no variant invades any of the Forbidden_Territories"
CHECK_C = "(c) `subset_to_regenerate` contains ONLY the variant_key of the variants that fail"
WARNINGS_HEADER = "Deterministic diversity warnings (this iteration, informative only):"

VIEW_KEYS = {"variant_key", "angle", "copy", "image_prompts"}
# Keys that never travel to the Validador_Adset (D21).
FORBIDDEN_MESSAGE_KEYS = ("image_request", "product_image_sources", "product_image_urls",
                          "base_image_url")
FORBIDDEN_VIEW_KEYS = ("plan", "ad_id", "plan_id", "template_id")


def json_line(message: str, prefix: str):
    """JSON value of the single line of ``message`` starting with ``prefix``."""
    lines = [line for line in message.split("\n") if line.startswith(prefix)]
    assert len(lines) == 1, (prefix, lines)
    return json.loads(lines[0][len(prefix):])


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

# Free text without ':', '/', '"', '_' nor newlines: it can never form a marker URL
# (`https://...`), a quoted JSON key (`"variants"`) or a forbidden key name.
_ALPHABET = list("abcdefghijklmnopqrstuvwxyz ABCXYZ0123456789áéíóúñüÁÑ¿?!.,-")
texts = st.text(alphabet=st.sampled_from(_ALPHABET), max_size=20)
non_empty_texts = st.text(alphabet=st.sampled_from(_ALPHABET), min_size=1, max_size=20)
json_values = st.one_of(texts, st.lists(texts, max_size=5), st.integers(-5, 5), st.none())
EXTRA_COPY_KEYS = ("notes", "reasoning", "angle", "image_request", "product_id",
                   "base_image_url")
EXTRA_PROMPT_KEYS = ("notes", "style", "plan_id", "template_id")


@st.composite
def creative_plans(draw):
    """Creative_Plan with Variant_Slots (with ``angle``), ``_territory`` and
    ``_project_templates``, the shape ``_build_or_load_creative_plan`` produces."""
    ad_id = draw(st.integers(min_value=1, max_value=10_000), label="ad_id")
    plan_id = f"plan_ad_{ad_id}"
    ad_slot = draw(st.integers(min_value=0, max_value=5), label="ad_slot")
    templates = draw(st.lists(st.sampled_from(["t1", "t2", "t3", "t4"]), min_size=1,
                              max_size=4, unique=True), label="templates")
    n_variants = draw(st.integers(min_value=1, max_value=8), label="n_variants")
    plan = {
        "id": plan_id,
        "concept": draw(non_empty_texts, label="concept"),
        "emocion": draw(st.one_of(st.none(), texts)),
        "intencion": draw(st.one_of(st.none(), texts)),
        "visual_dominante": draw(st.one_of(st.none(), texts)),
        "contexto_uso": draw(st.one_of(st.none(), texts)),
        "psicologia": draw(st.one_of(st.none(), texts)),
        "tone": draw(st.one_of(st.none(), texts)),
        "color_palette": draw(st.one_of(st.none(), texts)),
        "target_insight": draw(texts),
        "_territory": {"anchor_primary": {"text": draw(texts)},
                       "territorio_prohibido": draw(st.lists(texts, max_size=3))},
        "_project_templates": templates,
        "variants": build_variant_slots(plan_id, ad_slot, n_variants, templates),
    }
    return ad_id, plan


def _marker(counter: list[int], kind: str) -> str:
    """Unique ``https://`` marker URL (never present in the plan, copies or context)."""
    counter[0] += 1
    return f"https://marker-{counter[0]}.invalid/{kind}.png"


@st.composite
def copy_for(draw, plan_id: str, slot: dict) -> dict:
    """Copywriter item: identity + an arbitrary subset of the Validador_View copy fields
    + arbitrary extra keys."""
    item = {"plan_id": plan_id, "variant_key": slot["variant_key"],
            "template_id": slot["template_id"]}
    for field in draw(st.lists(st.sampled_from(VALIDADOR_VIEW_COPY_FIELDS), unique=True)):
        if field == "template_elements":
            item[field] = draw(st.dictionaries(non_empty_texts, texts, max_size=3))
        else:
            item[field] = draw(st.one_of(texts, st.lists(texts, min_size=1, max_size=5)))
    for key in draw(st.lists(st.sampled_from(EXTRA_COPY_KEYS), unique=True)):
        item[key] = draw(json_values)
    return item


@st.composite
def prompt_item_for(draw, plan_id: str, slot: dict, counter: list[int],
                    markers: list[str]) -> dict:
    """Image_Prompter item whose elements carry ``image_request`` (with
    ``technical_specs.product_image_sources``), ``product_image_urls`` and
    ``base_image_url`` with marker URLs, plus an arbitrary subset of
    ``element_id`` / ``image_prompt`` and extra keys."""
    elements = []
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        source, product, base = (_marker(counter, k) for k in ("source", "product", "base"))
        markers.extend([source, product, base])
        element = {
            "image_request": {"technical_specs": {"product_image_sources": [source]},
                              "mode": draw(texts)},
            "product_image_urls": [product],
            "base_image_url": base,
        }
        for field in draw(st.lists(st.sampled_from(VALIDADOR_VIEW_PROMPT_FIELDS),
                                   unique=True)):
            element[field] = draw(texts)
        for key in draw(st.lists(st.sampled_from(EXTRA_PROMPT_KEYS), unique=True)):
            element[key] = draw(json_values)
        elements.append(element)
    return {"plan_id": plan_id, "variant_key": slot["variant_key"],
            "template_id": slot["template_id"], "image_prompts": elements}


adset_contexts = st.dictionaries(
    st.sampled_from(["adset_name", "brand", "audience", "country", "objective"]),
    texts, max_size=5,
).map(lambda d: {"ok": True, "adset": d})


# ---------------------------------------------------------------------------
# Property 14: Contenido del mensaje al Validador
# ---------------------------------------------------------------------------


# Feature: adset-creative-diversity, Property 14: Contenido del mensaje al Validador
@settings(max_examples=100, deadline=None)
@given(
    data=st.data(),
    ad_and_plan=creative_plans(),
    forbidden=st.lists(non_empty_texts, max_size=4),
    warnings=st.lists(non_empty_texts, max_size=3),
    adset_context=adset_contexts,
)
def test_validador_message_content(data, ad_and_plan, forbidden, warnings, adset_context):
    """**Validates: Requirements 2.5, 7.3, 7.14**"""
    ad_id, plan = ad_and_plan
    plan_id = plan["id"]
    slots = plan["variants"]
    keys = [s["variant_key"] for s in slots]
    counter, markers = [0], []

    # Copies / prompts for arbitrary subsets of the variants (missing ones still yield
    # a proposal with an empty copy / image_prompts).
    copy_keys = data.draw(st.lists(st.sampled_from(keys), unique=True), label="copy_keys")
    prompt_keys = data.draw(st.lists(st.sampled_from(keys), unique=True), label="prompt_keys")
    copies = [data.draw(copy_for(plan_id, s), label="copy") for s in slots
              if s["variant_key"] in copy_keys]
    prompts = [data.draw(prompt_item_for(plan_id, s, counter, markers), label="prompts")
               for s in slots if s["variant_key"] in prompt_keys]
    proposals = build_variant_proposals(plan, copies, prompts, ad_id)
    proposals_before = copy.deepcopy(proposals)
    plan_before = copy.deepcopy(plan)
    ctx_json = dumps(adset_context)

    message = build_validador_message(plan, proposals, forbidden, ctx_json, warnings)

    # Mandatory content: plan id, Forbidden_Territories, warnings (or "- none"),
    # checks (a)–(c) and the FULL ADSET CONTEXT block (Req 7.3, 2.5).
    assert f"id={dumps(plan_id)}" in message
    assert json_line(message, "variant_keys: ") == keys
    assert json_line(message, "Forbidden_Territories: ") == forbidden
    for text in forbidden:
        assert dumps(text) in message
    for check in (CHECK_A, CHECK_B, CHECK_C):
        assert check in message, check
    block = message.split(WARNINGS_HEADER + "\n", 1)[1].split("\nPlan: ", 1)[0]
    assert block.split("\n") == ([f"- {w}" for w in warnings] if warnings else ["- none"])
    assert message.endswith(f"{FULL_ADSET_CONTEXT_HEADER}\n{ctx_json}\n")

    # The plan exactly once, without variants / _project_templates.
    payload = _plan_payload(plan)
    assert "variants" not in payload and "_project_templates" not in payload
    assert message.count(dumps(payload)) == 1
    assert json_line(message, "Plan: ") == payload
    # As JSON keys (generated text has no ':', so `"variants":` can only be a key).
    assert '"variants":' not in message
    assert '"_project_templates":' not in message
    assert "Proposals:" not in message

    # Variants: == build_validador_views(...), one view per slot in order, exact keys.
    views = json_line(message, "Variants: ")
    assert views == build_validador_views(plan, proposals)
    assert [v["variant_key"] for v in views] == keys
    copy_map = {c["variant_key"]: c for c in copies}
    prompt_map = {p["variant_key"]: p for p in prompts}
    for slot, view in zip(slots, views):
        assert set(view) == VIEW_KEYS
        assert not any(k in view for k in FORBIDDEN_VIEW_KEYS)
        assert view["angle"] == slot["angle"]
        source_copy = copy_map.get(slot["variant_key"], {})
        assert view["copy"] == {f: source_copy[f] for f in VALIDADOR_VIEW_COPY_FIELDS
                                if f in source_copy}
        source_prompts = prompt_map.get(slot["variant_key"], {}).get("image_prompts", [])
        assert view["image_prompts"] == [
            {f: el[f] for f in VALIDADOR_VIEW_PROMPT_FIELDS if f in el}
            for el in source_prompts
        ]

    # Neither the forbidden keys nor any marker URL reach the message.
    for key in FORBIDDEN_MESSAGE_KEYS:
        assert key not in message, key
    for url in markers:
        assert url not in message, url
    assert "https://marker-" not in message

    # Inputs are not mutated: proposals keep their full image_request (Req 7.14).
    assert proposals == proposals_before
    assert plan == plan_before
    for proposal in proposals:
        for element in proposal["image_prompts"]:
            assert "product_image_sources" in element["image_request"]["technical_specs"]


# ---------------------------------------------------------------------------
# Unit tests (Req 12.21) — task 26.4
# ---------------------------------------------------------------------------

SOURCE_URL = "https://cdn.example.invalid/source.png"
PRODUCT_URL = "https://cdn.example.invalid/product.png"
BASE_URL = "https://cdn.example.invalid/base.png"
AD_ID = 4242


def _fixture():
    """Plan with 3 Variant_Slots plus full copies / image prompts with URLs and extras."""
    plan_id = f"plan_ad_{AD_ID}"
    templates = ["tpl_a", "tpl_b"]
    plan = {
        "id": plan_id,
        "concept": "Mañanas tranquilas",
        "tone": "cálido",
        "color_palette": "tierra",
        "_territory": {"anchor_primary": {"text": "calma"},
                       "territorio_prohibido": ["lujo ostentoso"]},
        "_project_templates": templates,
        "variants": build_variant_slots(plan_id, 0, 3, templates),
    }
    copies, prompts = [], []
    for k, slot in enumerate(plan["variants"], start=1):
        copies.append({
            "plan_id": plan_id, "variant_key": slot["variant_key"],
            "template_id": slot["template_id"],
            "headline": f"Titular {k}", "primary_text": f"Texto {k}",
            "description": f"Desc {k}", "cta": "Comprar",
            "template_elements": {"title": f"T{k}"},
            "notes": "internal", "reasoning": "why",
        })
        prompts.append({
            "plan_id": plan_id, "variant_key": slot["variant_key"],
            "template_id": slot["template_id"],
            "image_prompts": [{
                "element_id": f"img_{k}", "image_prompt": f"Taza humeante {k}",
                "image_request": {"technical_specs": {"product_image_sources": [SOURCE_URL]}},
                "product_image_urls": [PRODUCT_URL],
                "base_image_url": BASE_URL,
                "style": "photo",
            }],
        })
    proposals = build_variant_proposals(plan, copies, prompts, AD_ID)
    return plan, proposals


FORBIDDEN = ["lujo ostentoso", "ruido urbano"]
ADSET_CONTEXT_JSON = dumps({"ok": True, "adset": {"adset_name": "Otoño", "brand": "Acme"}})


def _message(warnings=None):
    plan, proposals = _fixture()
    return plan, proposals, build_validador_message(
        plan, proposals, FORBIDDEN, ADSET_CONTEXT_JSON, warnings or [])


def test_message_omits_forbidden_keys_and_urls():
    _, _, message = _message()
    for key in FORBIDDEN_MESSAGE_KEYS:
        assert key not in message, key
    for url in (SOURCE_URL, PRODUCT_URL, BASE_URL):
        assert url not in message, url
    assert "Proposals:" not in message


def test_views_have_exact_keys_and_no_plan_identity():
    plan, _, message = _message()
    views = json_line(message, "Variants: ")
    assert [v["variant_key"] for v in views] == [s["variant_key"] for s in plan["variants"]]
    for slot, view in zip(plan["variants"], views):
        assert set(view) == VIEW_KEYS
        for key in FORBIDDEN_VIEW_KEYS:
            assert key not in view, key
        assert view["angle"] == slot["angle"]
        assert set(view["copy"]) == set(VALIDADOR_VIEW_COPY_FIELDS)
        assert "notes" not in view["copy"] and "reasoning" not in view["copy"]
        assert view["image_prompts"] == [{
            "element_id": view["image_prompts"][0]["element_id"],
            "image_prompt": view["image_prompts"][0]["image_prompt"],
        }]
        assert set(view["image_prompts"][0]) == set(VALIDADOR_VIEW_PROMPT_FIELDS)


def test_plan_appears_once_without_variants_or_project_templates():
    plan, _, message = _message()
    payload = json_line(message, "Plan: ")
    assert payload == _plan_payload(plan)
    assert "variants" not in payload and "_project_templates" not in payload
    assert payload["concept"] == plan["concept"]
    assert message.count(dumps(_plan_payload(plan))) == 1
    assert message.count("Plan: ") == 1
    assert '"variants":' not in message
    assert '"_project_templates":' not in message
    # The full plan (with slots) is never dumped.
    assert dumps(plan) not in message
    assert dumps(plan["variants"]) not in message


def test_full_adset_context_and_forbidden_territories_present():
    plan, _, message = _message()
    assert f"{FULL_ADSET_CONTEXT_HEADER}\n{ADSET_CONTEXT_JSON}\n" in message
    assert message.endswith(f"{FULL_ADSET_CONTEXT_HEADER}\n{ADSET_CONTEXT_JSON}\n")
    assert json_line(message, "Forbidden_Territories: ") == FORBIDDEN
    assert f"id={dumps(plan['id'])}" in message
    for check in (CHECK_A, CHECK_B, CHECK_C):
        assert check in message, check


def test_warnings_listed_instead_of_errors():
    warnings = ["HEADLINE_SIMILAR v1~v2", "CTA_REPEATED v2~v3"]
    _, _, message = _message(warnings)
    assert "Deterministic diversity errors" not in message
    block = message.split(WARNINGS_HEADER + "\n", 1)[1].split("\nPlan: ", 1)[0]
    assert block.split("\n") == [f"- {w}" for w in warnings]
    assert "- none" not in message


def test_no_warnings_renders_none():
    _, _, message = _message([])
    block = message.split(WARNINGS_HEADER + "\n", 1)[1].split("\nPlan: ", 1)[0]
    assert block == "- none"
    assert "Deterministic diversity errors" not in message


def test_message_does_not_mutate_inputs():
    plan, proposals = _fixture()
    plan_before, proposals_before = copy.deepcopy(plan), copy.deepcopy(proposals)
    build_validador_message(plan, proposals, FORBIDDEN, ADSET_CONTEXT_JSON, ["w"])
    assert plan == plan_before
    assert proposals == proposals_before


# --- build_validador_view edge cases -----------------------------------------

SLOT = {"variant_key": "plan_ad_1_v1", "template_id": "tpl_a",
        "angle": {"hook": "question", "headline_structure": "short", "copy_length": "short"}}


def test_view_missing_proposal_gives_empty_copy_and_prompts():
    for proposal in (None, {}, "not a dict"):
        view = build_validador_view(SLOT, proposal)
        assert view == {"variant_key": SLOT["variant_key"], "angle": SLOT["angle"],
                        "copy": {}, "image_prompts": []}


def test_view_non_dict_copy_gives_empty_copy():
    for bad_copy in (None, "texto", ["headline"], 3):
        view = build_validador_view(SLOT, {"copy": bad_copy, "image_prompts": []})
        assert view["copy"] == {}


def test_view_non_list_image_prompts_gives_empty_list():
    for bad in (None, "prompt", {"element_id": "x"}, 7):
        view = build_validador_view(SLOT, {"copy": {}, "image_prompts": bad})
        assert view["image_prompts"] == []


def test_view_skips_non_dict_elements_and_keeps_only_view_fields():
    proposal = {
        "copy": {"headline": "H", "cta": "Ir", "notes": "x", "plan_id": "p"},
        "image_prompts": [
            "string", None, 5, ["list"],
            {"element_id": "e1", "image_prompt": "p1", "base_image_url": BASE_URL},
            {"image_prompt": "p2"},
            {},
        ],
    }
    view = build_validador_view(SLOT, proposal)
    assert view["copy"] == {"headline": "H", "cta": "Ir"}
    assert view["image_prompts"] == [{"element_id": "e1", "image_prompt": "p1"},
                                     {"image_prompt": "p2"}, {}]


def test_view_does_not_mutate_inputs():
    slot = copy.deepcopy(SLOT)
    proposal = {
        "ad_id": 1, "plan_id": "plan_ad_1", "variant_key": slot["variant_key"],
        "template_id": "tpl_a", "plan": {"id": "plan_ad_1"},
        "copy": {"headline": "H", "notes": "n"},
        "image_prompts": [{"element_id": "e1", "image_prompt": "p",
                           "image_request": {"technical_specs":
                                             {"product_image_sources": [SOURCE_URL]}}}],
    }
    slot_before, proposal_before = copy.deepcopy(slot), copy.deepcopy(proposal)
    view = build_validador_view(slot, proposal)
    assert slot == slot_before
    assert proposal == proposal_before
    assert view["copy"] is not proposal["copy"]
    assert view["image_prompts"] is not proposal["image_prompts"]
    assert view["image_prompts"][0] is not proposal["image_prompts"][0]
    for key in FORBIDDEN_VIEW_KEYS:
        assert key not in view


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-v"]))
