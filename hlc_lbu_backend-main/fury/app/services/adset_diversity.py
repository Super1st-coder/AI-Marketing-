"""Pure helpers for the Adset creative-diversity path (``USE_ADSET_CREATIVE_DIVERSITY``).

In the Diversity_Path creative diversity is guaranteed at the level of the **Ads of an
Adset** instead of the variants of a single Ad:

* every Adset_Ad gets an Ad_Slot (its 0-based position in the Adset_Ads sorted by ``id``);
* ``services.territory_assignment.assign_territories`` assigns one territory per Ad_Slot
  once per job, and :func:`bind_territories` pins each territory to its Ad's ``id``;
* each Ad then gets a single Creative_Plan (``plan_ad_{ad_id}``) whose Variant_Slots
  (``{plan_id}_v{k}``) carry the Abyssale template of every variant.

This module has no network, LLM or Redis access: the same input always produces the
same output. The orchestration lives in ``services.job_runner_service`` and the
deterministic verification in ``services.diversity_checker``.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Optional, Sequence, TypedDict

from core.logging import get_logger
from core.validation import ValidationResult
from schemas.territory_schemas import AdDescription
from services.territory_assignment import (
    build_estratega_adset_input,
    territory_to_plan,
    unwrap_adset,
)

logger = get_logger(__name__)

VARIANT_KEY_FMT = "{plan_id}_v{k}"
PLAN_ID_FMT = "plan_ad_{ad_id}"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class VariantAngle(TypedDict):
    hook: str  # opening rhetorical device (question, bold_claim, ...)
    headline_structure: str  # headline focus (buyer_first, outcome_first, ...)
    copy_length: str  # short | medium | long


class VariantSlot(TypedDict):
    variant_key: str  # f"{plan_id}_v{k}", k = 1..n_variants
    template_id: str  # Ad_Template of the Ad_Slot, same for every k (P11, D15)
    angle: VariantAngle  # assign_variant_angles(plan_id, n)[k - 1] (P14, D22)


class CreativePlan(TypedDict):
    id: str  # f"plan_ad_{ad_id}"
    concept: str
    emocion: Optional[str]
    intencion: Optional[str]
    visual_dominante: Optional[str]
    contexto_uso: Optional[str]
    psicologia: Optional[str]
    tone: Optional[str]  # derivados.hook
    color_palette: Optional[str]  # palette_family
    target_insight: str  # anchor_primary.text
    _territory: dict[str, Any]  # anchor_primary, palette_family, derivados, territorio_prohibido
    _project_templates: list[str]  # D14: kept to resume rules 6.6/6.7 from checkpoint
    variants: list[VariantSlot]


class DiversityReport(TypedDict):
    ad_id: int
    plan_id: str
    deterministic_pass: bool
    deterministic_errors: list[str]
    deterministic_warnings: list[str]
    overall_pass: bool  # deterministic_pass and Validador verdict
    iterations: int  # 0 if the Ad failed before the loop; 1..3 otherwise
    subset_to_regenerate: list[str]
    ad_failed: bool  # D5
    error: Optional[str]  # D5 (no signed URLs nor secrets)


@dataclass(frozen=True)
class AdSlotPlan:
    slot_ad_ids: list[int]  # ad_id per Ad_Slot (index = slot); includes the extra slot
    target_ad_ids: list[int]  # Ads to process (Scenario_1: all; Scenario_2: [id_ad])
    extra_slot: bool  # True if id_ad was not among the Adset_Ads (Req 3.6)


# ---------------------------------------------------------------------------
# Ad_Slot resolution
# ---------------------------------------------------------------------------

def _is_valid_ad_id(value: Any) -> bool:
    # bool is a subclass of int: exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def extract_adset_ads(adset_context: dict[str, Any], task_id: str) -> list[int]:
    """ids of ``unwrap_adset(ctx)["ads"]`` that are int > 0 (bool excluded), without
    duplicates, sorted ascending. Logs a ``[{task_id}]`` warning for every discarded
    entry (Req 3.1, 3.2, D11)."""
    adset = unwrap_adset(adset_context)
    ads = adset.get("ads") if isinstance(adset, dict) else None
    if ads is None:
        return []
    if not isinstance(ads, list):
        logger.warning(f"[{task_id}] adset ads is not a list ({type(ads).__name__}); ignoring")
        return []

    seen: set[int] = set()
    for index, entry in enumerate(ads):
        ad_id = entry.get("id") if isinstance(entry, dict) else None
        if not _is_valid_ad_id(ad_id):
            logger.warning(
                f"[{task_id}] discarding adset ad entry #{index}: invalid id {ad_id!r}"
            )
            continue
        if ad_id in seen:
            logger.warning(f"[{task_id}] discarding adset ad entry #{index}: duplicate id {ad_id}")
            continue
        seen.add(ad_id)
    return sorted(seen)


def resolve_ad_slots(adset_ad_ids: list[int], id_ad: Optional[int], task_id: str) -> AdSlotPlan:
    """Scenario_1 if ``id_ad`` is None/0; Scenario_2 if ``id_ad > 0``. When ``id_ad`` is
    not among the Adset_Ads it gets an extra slot at the end, with a warning (Req 3.5–3.7)."""
    slot_ad_ids = list(adset_ad_ids)
    if not id_ad or id_ad <= 0:
        return AdSlotPlan(slot_ad_ids=slot_ad_ids, target_ad_ids=list(slot_ad_ids), extra_slot=False)

    extra_slot = id_ad not in slot_ad_ids
    if extra_slot:
        logger.warning(
            f"[{task_id}] id_ad={id_ad} not found in adset ads; "
            f"assigning extra Ad_Slot {len(slot_ad_ids)}"
        )
        slot_ad_ids.append(id_ad)
    return AdSlotPlan(slot_ad_ids=slot_ad_ids, target_ad_ids=[id_ad], extra_slot=extra_slot)


def bind_territories(territories: list[AdDescription], slot_ad_ids: list[int]) -> list[AdDescription]:
    """Deep copy of every AdDescription with ``ad_id = slot_ad_ids[slot]`` (Req 3.2, 3.13).

    Raises ``ValueError`` if the number of territories differs from the number of slots.
    """
    if len(territories) != len(slot_ad_ids):
        raise ValueError(
            f"bind_territories: {len(territories)} territories for {len(slot_ad_ids)} Ad_Slots"
        )
    return [
        territory.model_copy(deep=True, update={"ad_id": ad_id})
        for territory, ad_id in zip(territories, slot_ad_ids)
    ]


# ---------------------------------------------------------------------------
# Project_Templates, Variant_Slots and Creative_Plan
# ---------------------------------------------------------------------------

def resolve_project_templates(template_context: Any) -> list[str]:
    """``str(t.get("id") or t.get("template_id"))`` for every entry of ``templates``, in
    the returned order, keeping only the first occurrence of each identifier (compared
    as ``str``). ``[]`` if ``ok`` is False or the shape is not valid (Req 4.5, 4.7).

    A missing or empty ``id`` falls back to ``template_id``. Entries that are not dicts
    or have neither value (missing, ``None`` or ``""``) are skipped.
    """
    if not isinstance(template_context, dict) or template_context.get("ok") is False:
        return []
    templates = template_context.get("templates")
    if not isinstance(templates, list):
        return []

    resolved: list[str] = []
    seen: set[str] = set()
    for entry in templates:
        if not isinstance(entry, dict):
            continue
        template_id = entry.get("id") or entry.get("template_id")
        if template_id is None or template_id == "":
            continue
        key = str(template_id)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(key)
    return resolved


def template_seed(seed: str) -> int:
    """Stable seed of the Template_Order (P12, D18):
    ``int.from_bytes(sha256(f"adset-templates:{seed}").digest()[:8], "big")``.

    Never ``hash()``: it is salted per process, so it would change between workers and
    restarts.
    """
    digest = hashlib.sha256(f"adset-templates:{seed}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def template_order(project_templates: Sequence[str], seed: str) -> list[str]:
    """Template_Order of a job (Decision P12, D18): a new list with the same identifiers
    as ``project_templates``, shuffled with a local ``random.Random(template_seed(seed))``.

    The global ``random`` module is neither used nor altered and the input is not
    mutated. The same ``(project_templates, seed)`` always yields the same order. ``[]``
    for an empty list; a one-element list is returned as is (Req 4.10, 4.11).
    """
    order = list(project_templates)
    if len(order) > 1:
        random.Random(template_seed(seed)).shuffle(order)
    return order


# The three functions below keep their signatures (D15): they receive an ordered list
# and, in the Diversity_Path, the caller always passes the job's Template_Order.

def ad_template_for_slot(ad_slot: int, project_templates: Sequence[str]) -> str:
    """Ad_Template of an Ad_Slot: ``project_templates[ad_slot % len(project_templates)]``
    (Decisions P11, P12, D15).

    In the Diversity_Path ``project_templates`` is the job's Template_Order
    (:func:`template_order`), not the order returned by ``get_template_context``. It
    depends only on the Ad_Slot and the list, so within a job it is the same in
    Scenario_1 and Scenario_2 (extra slot included) and on every retry. Ad_Slots get
    different templates while their number does not exceed ``len(project_templates)``;
    beyond that the templates repeat in rotation (Req 4.5, 4.6).

    Raises ``ValueError`` if ``project_templates`` is empty or ``ad_slot < 0``.
    """
    if not project_templates:
        raise ValueError("ad_template_for_slot: project_templates is empty")
    if ad_slot < 0:
        raise ValueError(f"ad_template_for_slot: ad_slot must be >= 0, got {ad_slot}")
    return project_templates[ad_slot % len(project_templates)]


def slot_ad_templates(n_slots: int, project_templates: Sequence[str]) -> list[str]:
    """Ad_Slot → Ad_Template map of the whole Adset:
    ``[ad_template_for_slot(s, project_templates) for s in range(n_slots)]`` (P11, P12, D16).

    In the Diversity_Path ``project_templates`` is the job's Template_Order. Used to evaluate rule 6.12 (``check_ad_templates``) while each Ad is processed on its
    own. ``n_slots <= 0`` yields ``[]``; raises ``ValueError`` if ``project_templates`` is
    empty and ``n_slots > 0``.
    """
    return [ad_template_for_slot(slot, project_templates) for slot in range(n_slots)]


# ---------------------------------------------------------------------------
# Variant_Angle (Decision P14, D22)
# ---------------------------------------------------------------------------
# ``VariantAngle`` is defined with the data models above (it types ``VariantSlot.angle``).

ANGLE_KEYS: tuple[str, ...] = ("hook", "headline_structure", "copy_length")

# Angle_Vocabulary (P14, D22): fixed order, 6 entries. Every ``hook`` and every
# ``headline_structure`` is distinct and ``copy_length`` cycles short → medium → long,
# so two distinct entries always differ in hook and structure (Req 14.9).
ANGLE_VOCABULARY: tuple[VariantAngle, ...] = (
    VariantAngle(hook="question", headline_structure="buyer_first", copy_length="short"),
    VariantAngle(hook="bold_claim", headline_structure="outcome_first", copy_length="medium"),
    VariantAngle(hook="mini_story", headline_structure="detail_first", copy_length="long"),
    VariantAngle(hook="sensory_scene", headline_structure="product_first", copy_length="short"),
    VariantAngle(hook="practical_tip", headline_structure="contrast", copy_length="medium"),
    VariantAngle(hook="direct_address", headline_structure="moment_first", copy_length="long"),
)


def angle_offset(plan_id: str) -> int:
    """Angle offset of a Creative_Plan (P14, D22, Req 14.2):
    ``int(sha256(plan_id.encode("utf-8")).hexdigest(), 16) % len(ANGLE_VOCABULARY)``.

    Stable across processes; never ``hash()`` (salted per process).
    """
    digest = hashlib.sha256(plan_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % len(ANGLE_VOCABULARY)


def assign_variant_angles(plan_id: str, n_variants: int) -> list[VariantAngle]:
    """Variant_Angles of the ``n_variants`` Variant_Slots of a plan (P14, D22):
    ``[dict(ANGLE_VOCABULARY[(o + k - 1) % len]) for k in 1..n_variants]`` with
    ``o = angle_offset(plan_id)``.

    Returns new copies (mutating them does not alter the constant). Pure: it neither
    uses nor alters ``random`` and does not depend on ``task_id`` nor on the
    Template_Order. Angles are pairwise distinct while ``n_variants <=
    len(ANGLE_VOCABULARY)``. Raises ``ValueError`` if ``n_variants < 1`` (Req 14.2, 14.3).
    """
    if n_variants < 1:
        raise ValueError(f"assign_variant_angles: n_variants must be >= 1, got {n_variants}")
    offset = angle_offset(plan_id)
    size = len(ANGLE_VOCABULARY)
    return [
        VariantAngle(**ANGLE_VOCABULARY[(offset + k - 1) % size])
        for k in range(1, n_variants + 1)
    ]


def is_valid_variant_angle(value: Any) -> bool:
    """``True`` only if ``value`` is a dict equal (``==``) to an element of
    ``ANGLE_VOCABULARY`` (P14, D22, Req 14.5, 14.9)."""
    return isinstance(value, dict) and any(value == angle for angle in ANGLE_VOCABULARY)


def ensure_variant_angles(plan: CreativePlan) -> tuple[CreativePlan, bool]:
    """Reuse or recompute the Variant_Angles of a cached plan (P14, D22, Req 14.4, 14.5).

    If every Variant_Slot has a valid ``angle`` → ``(plan, False)``, without copying
    (repeated but valid angles are reused as is). Otherwise → ``(copy, True)`` where the
    copy has the ``angle`` of ALL slots set to
    ``assign_variant_angles(plan["id"], len(variants))[k - 1]``. ``variant_key``,
    ``template_id`` and every other key are kept; the input is not mutated.
    """
    variants = plan.get("variants") or []
    if all(isinstance(slot, dict) and is_valid_variant_angle(slot.get("angle"))
           for slot in variants):
        return plan, False

    angles = assign_variant_angles(plan["id"], len(variants))
    fixed = dict(plan)
    fixed["variants"] = [{**slot, "angle": angle} for slot, angle in zip(variants, angles)]
    return fixed, True  # type: ignore[return-value]


def build_variant_slots(plan_id: str, ad_slot: int, n_variants: int,
                        project_templates: list[str]) -> list[VariantSlot]:
    """k = 1..n_variants → ``{"variant_key": f"{plan_id}_v{k}", "template_id":
    ad_template_for_slot(ad_slot, project_templates), "angle":
    assign_variant_angles(plan_id, n_variants)[k - 1]}``.

    One template per Ad (Decisions P11, P12, D15): every Variant_Slot of the Ad shares
    the Ad_Template of its Ad_Slot; variants differ in copy, image and Variant_Angle
    (P14, D22), not in template.
    In the Diversity_Path ``project_templates`` is the job's Template_Order.

    Raises ``ValueError`` if ``project_templates`` is empty or ``n_variants < 1``
    (Req 4.5, 4.6, 4.9). There is no upper bound on ``n_variants`` (P7).
    """
    if not project_templates:
        raise ValueError("build_variant_slots: project_templates is empty")
    if n_variants < 1:
        raise ValueError(f"build_variant_slots: n_variants must be >= 1, got {n_variants}")

    ad_template = ad_template_for_slot(ad_slot, project_templates)
    angles = assign_variant_angles(plan_id, n_variants)
    return [
        VariantSlot(
            variant_key=VARIANT_KEY_FMT.format(plan_id=plan_id, k=k),
            template_id=ad_template,
            angle=angles[k - 1],
        )
        for k in range(1, n_variants + 1)
    ]


def build_creative_plan(territory: AdDescription, ad_id: int, ad_slot: int,
                        variant_slots: list[VariantSlot]) -> CreativePlan:
    """``territory_to_plan(territory, ad_slot)`` with ``id = plan_ad_{ad_id}``, without
    ``template_id`` / ``template_selection_reason``, plus ``variants`` (Req 4.1, 4.3).

    ``_project_templates`` (D14) is not set here: the orchestrator adds it once the
    Project_Templates are resolved.
    """
    plan = territory_to_plan(territory, ad_slot)
    plan.pop("template_id", None)
    plan.pop("template_selection_reason", None)
    plan["id"] = PLAN_ID_FMT.format(ad_id=ad_id)
    plan["variants"] = [VariantSlot(**slot) for slot in variant_slots]
    return plan  # type: ignore[return-value]


def first_text(value: Any) -> str:
    """First element if ``value`` is a list (when it is a str), ``value`` if it is a str;
    ``""`` otherwise. No normalisation."""
    if isinstance(value, list):
        value = value[0] if value else ""
    return value if isinstance(value, str) else ""


# ---------------------------------------------------------------------------
# Response shape per Variant_Slot and merge by variant_key
# ---------------------------------------------------------------------------

VARIANT_SHAPE_ERROR_CODE = "ERR_VARIANT_SHAPE"


def check_variant_items(items: Any, slots: list[VariantSlot], plan_id: str,
                        *, kind: Literal["copy", "image_prompt"]) -> list[str]:
    """Shape errors of a Copywriter (``kind="copy"``) or Image_Prompter
    (``kind="image_prompt"``) response against the Variant_Slots of a Creative_Plan.

    Valid only if ``items`` is a non-empty list with exactly one dict per slot, each one
    with ``plan_id == plan_id``, a ``variant_key`` of a slot (not repeated) and the
    ``template_id`` of that same slot. Order is irrelevant. Returns ``[]`` if valid
    (Req 5.2, 5.3, 5.8).
    """
    label = "Copy" if kind == "copy" else "Image prompt"
    if not isinstance(items, list):
        return [f"{label} response must be a list, got {type(items).__name__}"]
    if not items:
        return [f"{label} response is an empty list; expected {len(slots)} item(s)"]

    errors: list[str] = []
    if len(items) != len(slots):
        errors.append(f"{label} response has {len(items)} item(s); expected {len(slots)} "
                      f"(one per Variant_Slot)")

    slot_templates = {slot["variant_key"]: slot["template_id"] for slot in slots}
    seen: set[str] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"{label} {index} is not a dictionary")
            continue
        if item.get("plan_id") != plan_id:
            errors.append(f"{label} {index} has plan_id {item.get('plan_id')!r}; "
                          f"expected {plan_id!r}")
        variant_key = item.get("variant_key")
        if not variant_key:
            errors.append(f"{label} {index} is missing variant_key")
            continue
        if variant_key not in slot_templates:
            errors.append(f"{label} {index} has unknown variant_key {variant_key!r}")
            continue
        if variant_key in seen:
            errors.append(f"{label} {index} repeats variant_key {variant_key!r}")
            continue
        seen.add(variant_key)
        expected_template = slot_templates[variant_key]
        if item.get("template_id") != expected_template:
            errors.append(f"{label} {index} ({variant_key}) has template_id "
                          f"{item.get('template_id')!r}; expected {expected_template!r}")

    missing = [slot["variant_key"] for slot in slots if slot["variant_key"] not in seen]
    if missing:
        errors.append(f"{label} response is missing variant_key(s): {', '.join(missing)}")
    return errors


# Fields the base validators require as lists; models sometimes answer a single value.
_LIST_FIELDS: dict[str, tuple[str, ...]] = {
    "copy": ("headline", "primary_text", "description", "cta"),
    "image_prompt": (),
}
_LIST_OF_DICT_FIELDS: dict[str, tuple[str, ...]] = {
    "copy": ("template_elements",),
    "image_prompt": ("image_prompts",),
}


def _strip_fences(text: str) -> str:
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    return re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)


def normalize_variant_fields(response: Any, *, kind: Literal["copy", "image_prompt"]
                             ) -> tuple[Any, list[str]]:
    """Wraps scalar values of list fields before the base validator: a non-empty ``str``
    in ``headline`` / ``primary_text`` / ``description`` / ``cta`` becomes ``[str]`` and a
    ``dict`` in ``template_elements`` / ``image_prompts`` becomes ``[dict]``.

    In production (job 259a13a7) the Copywriter answered every list field as a plain
    string and the whole job failed on ``ERR_COPY_INVALID_TYPE_*``. Values are never
    invented: empty strings, ``None`` and other types are left for the base validator.
    Returns ``(response, messages)``; the response is re-serialized only when something
    changed, so unparseable answers reach the base validator untouched.
    """
    if not isinstance(response, str) or not response.strip():
        return response, []
    try:
        parsed = json.loads(_strip_fences(response))
    except (json.JSONDecodeError, ValueError):
        return response, []
    items = [parsed] if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return response, []
    messages: list[str] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        for name in _LIST_FIELDS[kind]:
            value = item.get(name)
            if isinstance(value, str) and value.strip():
                item[name] = [value]
                messages.append(f"item {index}: {name} str -> [str]")
        for name in _LIST_OF_DICT_FIELDS[kind]:
            value = item.get(name)
            if isinstance(value, dict):
                item[name] = [value]
                messages.append(f"item {index}: {name} dict -> [dict]")
    if not messages:
        return response, []
    return json.dumps(items, ensure_ascii=False), messages


def repair_variant_items(items: Any, slots: list[VariantSlot], plan_id: str
                         ) -> tuple[Any, list[str]]:
    """Deterministic repair of the ``plan_id`` / ``variant_key`` identity of a Copywriter or
    Image_Prompter response, applied before :func:`check_variant_items`.

    The agents' system instructions (Langfuse) describe the Legacy_Path schema, which has
    ``plan_id`` but no ``variant_key``. In production the models either omit
    ``variant_key`` or write it into ``plan_id`` (``plan_id = "plan_ad_827_v1"``). Each
    item without a valid ``variant_key`` is resolved in this order:

    1. its ``plan_id`` is the ``variant_key`` of a free slot → that slot;
    2. otherwise the first free slot (in slot order) whose ``template_id`` equals the
       item's ``template_id``.

    Items that already carry a slot's ``variant_key`` claim it first. A resolved item gets
    ``variant_key`` and ``plan_id = plan_id``; a known item without ``plan_id`` gets
    ``plan_id``. An item is never assigned without a matching ``plan_id`` or
    ``template_id``, so content is never attached to a slot of another template.
    Returns ``(new_items, repair_messages)``; the input is not mutated and non-list
    input is returned unchanged.
    """
    if not isinstance(items, list):
        return items, []
    slot_keys = [slot["variant_key"] for slot in slots]
    slot_templates = {slot["variant_key"]: slot["template_id"] for slot in slots}
    repaired = [dict(item) if isinstance(item, dict) else item for item in items]
    taken = {item.get("variant_key") for item in repaired
             if isinstance(item, dict) and item.get("variant_key") in slot_templates}
    messages: list[str] = []
    for index, item in enumerate(repaired):
        if not isinstance(item, dict):
            continue
        key = item.get("variant_key")
        if key in slot_templates:
            if not item.get("plan_id"):
                item["plan_id"] = plan_id
                messages.append(f"item {index}: plan_id set to {plan_id!r}")
            continue
        if key:
            continue  # unknown variant_key: check_variant_items rejects it
        if item.get("plan_id") in slot_templates and item["plan_id"] not in taken:
            candidate, reason = item["plan_id"], "taken from plan_id"
        else:
            template = item.get("template_id")
            candidate = next((k for k in slot_keys
                              if k not in taken and slot_templates[k] == template), None)
            reason = f"matched by template_id {template!r}"
        if candidate is None:
            continue
        taken.add(candidate)
        item["variant_key"] = candidate
        item["plan_id"] = plan_id
        messages.append(f"item {index}: variant_key {candidate!r} {reason}")
    return repaired, messages


def make_variant_validator(base: Callable[[str], ValidationResult], slots: list[VariantSlot],
                           plan_id: str, *, kind: Literal["copy", "image_prompt"],
                           image_elements: Sequence[str] | None = None,
                           ) -> Callable[[str], ValidationResult]:
    """Composite validator for ``run_agent``: ``base(response)`` and, if valid,
    :func:`check_variant_items` on ``result.data``. Returns
    ``ValidationResult(is_valid=False, errors=..., error_code="ERR_VARIANT_SHAPE")`` when
    the shape fails; otherwise the base result unchanged.

    With ``kind="image_prompt"`` and non-``None`` ``image_elements`` (P15, Req 15.6,
    15.7), the errors of :func:`check_image_elements` are appended to those of
    :func:`check_variant_items` (only when ``data`` is a list). ``element_id`` values are
    never invented, renamed nor removed. ``image_elements`` with ``kind="copy"`` raises
    ``ValueError``; ``None`` keeps the previous behaviour."""
    if image_elements is not None and kind != "image_prompt":
        raise ValueError("image_elements is only supported with kind='image_prompt'")
    slots_copy = [VariantSlot(**slot) for slot in slots]
    elements_copy = (None if image_elements is None
                     else _expected_element_ids(image_elements))

    def validator(response: str) -> ValidationResult:
        response, coerced = normalize_variant_fields(response, kind=kind)
        if coerced:
            logger.warning(f"{kind} response normalized for {plan_id!r}: {'; '.join(coerced)}")
        result = base(response)
        if not result.is_valid:
            return result
        data, repairs = repair_variant_items(result.data, slots_copy, plan_id)
        if repairs:
            logger.warning(f"{kind} response repaired against the Variant_Slots of "
                           f"{plan_id!r}: {'; '.join(repairs)}")
            result.data = data
            result.warnings = list(result.warnings) + repairs
        shape_errors = check_variant_items(result.data, slots_copy, plan_id, kind=kind)
        if elements_copy is not None and isinstance(result.data, list):
            shape_errors = shape_errors + check_image_elements(result.data, elements_copy)
        if shape_errors:
            return ValidationResult(
                is_valid=False,
                errors=shape_errors,
                warnings=list(result.warnings),
                data=None,
                error_code=VARIANT_SHAPE_ERROR_CODE,
            )
        return result

    return validator


def _index_by_variant_key(items: list[dict]) -> dict[str, dict]:
    """``variant_key → item`` for dict items with a ``variant_key`` (first one wins)."""
    indexed: dict[str, dict] = {}
    for item in items or []:
        if isinstance(item, dict):
            key = item.get("variant_key")
            if key and key not in indexed:
                indexed[key] = item
    return indexed


def merge_by_variant_key(previous: list[dict], regenerated: list[dict],
                         slots: list[VariantSlot]) -> list[dict]:
    """Replaces in ``previous`` the items whose ``variant_key`` is in ``regenerated``;
    returns one item per slot, in slot order (Req 7.4). Slots present in neither list
    are omitted."""
    previous_map = _index_by_variant_key(previous)
    regenerated_map = _index_by_variant_key(regenerated)
    merged: list[dict] = []
    for slot in slots:
        key = slot["variant_key"]
        item = regenerated_map.get(key, previous_map.get(key))
        if item is not None:
            merged.append(item)
    return merged


def build_variant_proposals(plan: CreativePlan, copies: list[dict], prompts: list[dict],
                            ad_id: int) -> list[dict]:
    """One proposal per Variant_Slot: ``{ad_id, plan_id, variant_key, template_id, plan,
    copy, image_prompts}``, matched by ``variant_key`` (Req 5.9)."""
    copy_map = _index_by_variant_key(copies)
    prompt_map = _index_by_variant_key(prompts)
    plan_id = plan.get("id", "")
    proposals: list[dict] = []
    for slot in plan.get("variants", []):
        key = slot["variant_key"]
        proposals.append({
            "ad_id": ad_id,
            "plan_id": plan_id,
            "variant_key": key,
            "template_id": slot["template_id"],
            "plan": plan,
            "copy": copy_map.get(key, {}),
            "image_prompts": prompt_map.get(key, {}).get("image_prompts", []),
        })
    return proposals


def merge_variant_creative(plan: CreativePlan, copies: list[dict], images: list[dict],
                           saved_ads: list[dict], ad_id: int) -> list[dict]:
    """One item per Variant_Slot for ``build_abyssale_payload``: ``plan = {**plan, "id":
    variant_key}`` (→ ``metadata.plan_id = variant_key``), with copy, image and
    ``ad_channel`` matched by ``variant_key``. The item carries an ``error`` key (and is
    therefore skipped by ``build_abyssale_payload``) if its copy is missing (Req 5.9, 8.2).
    """
    copy_map = _index_by_variant_key(copies)
    image_map = _index_by_variant_key(images)
    channel_map = _index_by_variant_key(saved_ads)
    merged: list[dict] = []
    for slot in plan.get("variants", []):
        key = slot["variant_key"]
        item: dict[str, Any] = {
            "ad_id": ad_id,
            "variant_key": key,
            "plan": {**plan, "id": key},
            "copy": copy_map.get(key, {}),
            # {} (not None) so build_abyssale_payload can read a missing image safely.
            "image": image_map.get(key, {}),
            "ad_channel": channel_map.get(key, {}),
        }
        if key not in copy_map:
            item["error"] = f"missing copy for variant_key={key}"
        merged.append(item)
    return merged


# ---------------------------------------------------------------------------
# Image_Elements (P15, Req 15.2, 15.4, 15.13; D23, D25)
# ---------------------------------------------------------------------------
#
# Pure helpers: no network, no Redis and no ``settings``. The caller passes the
# Decorative_Image_Patterns (``settings.ADSET_DECORATIVE_IMAGE_PATTERNS``, read with
# ``getattr(..., DEFAULT_DECORATIVE_IMAGE_PATTERNS)`` in the Diversity_Path block).
# Only Element_Ids, dimensions, ``template_id`` and URLs without query string leave
# these helpers (Req 15.13): no signature parameters ever reach the Image_Prompter.

DEFAULT_DECORATIVE_IMAGE_PATTERNS: tuple[str, ...] = (
    "degradado", "gradient", "overlay", "mask", "shape")  # same value as the setting
IMAGE_ELEMENT_FORMAT = "instagram-portrait"
IMAGE_ELEMENT_TYPE = "image"


class ImageElementSpec(TypedDict, total=False):
    element_id: str  # always present
    width: int  # layout[IMAGE_ELEMENT_FORMAT].width, only if int > 0
    height: int  # idem


@dataclass(frozen=True)
class ImageElements:
    """Image_Elements resolved for an Ad_Template (P15, Req 15.2, 15.4; D23, D25).

    In memory only (never persisted in Redis/Checkpoints, Req 15.1).
    """

    template_id: str
    element_ids: tuple[str, ...]  # order of ``elements``, no duplicates (D23)
    specs: tuple[ImageElementSpec, ...]  # one per element_id, same order
    preview_url: Optional[str]  # without query string (D25, Req 15.13)


def element_id_of(element: Any) -> str:
    """Element_Id of a template element (P15, D23).

    ``str(element["name"] or element["id"])`` when that value is truthy, ``""``
    otherwise or when ``element`` is not a dict. Literally the criterion of
    ``job_runner_service._build_save_ads_payloads``, so the id given to the
    Image_Prompter is the one Sinergia (``media_images_banner``) and Abyssale
    (``layers``) use.
    """
    if not isinstance(element, dict):
        return ""
    value = element.get("name") or element.get("id")
    return str(value) if value else ""


def is_template_definition(template: Any) -> bool:
    """True if ``template`` is a dict whose ``elements`` key is a list (Req 15.3; D24)."""
    return isinstance(template, dict) and isinstance(template.get("elements"), list)


def _normalized_patterns(patterns: Any) -> list[str]:
    """Non-empty ``strip().casefold()`` patterns; non-``str`` entries are ignored (D23)."""
    if isinstance(patterns, (str, bytes)) or not isinstance(patterns, Sequence):
        # A bare string is not a list of patterns; treat it as no patterns.
        return []
    normalized: list[str] = []
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        p = pattern.strip().casefold()
        if p:
            normalized.append(p)
    return normalized


def _image_elements_iter(template: Any):
    """Yield ``(element_id, element)`` for dict elements with ``type == "image"`` and a
    non-empty Element_Id, in order (Req 15.2 (a)–(c))."""
    if not is_template_definition(template):
        return
    for element in template["elements"]:
        if not isinstance(element, dict):
            continue
        if element.get("type") != IMAGE_ELEMENT_TYPE:
            continue
        element_id = element_id_of(element)
        if element_id:
            yield element_id, element


def template_image_elements(template: Mapping[str, Any],
                            patterns: Sequence[str]) -> list[str]:
    """Image_Elements of a Template_Definition (P15, Req 15.2 (a)–(e); D23).

    (a) walks ``elements`` in order ignoring non-dict entries; (b) keeps only
    ``type == "image"`` (exact equality, so ``"Image"``/``None``/``"logo"`` are out);
    (c) skips empty Element_Ids (:func:`element_id_of`); (d) drops an element when a
    non-empty ``pattern.strip().casefold()`` is a substring of
    ``element_id.casefold()`` (non-``str`` and blank patterns are ignored); (e) keeps
    the first occurrence of each Element_Id. Returns ``[]`` when ``template`` does
    not satisfy :func:`is_template_definition`. Returns a new list and never mutates
    ``template`` nor ``patterns``. No network nor ``settings``.

    For template ``1bb5c1ad`` it returns ``["image_0"]``.
    """
    normalized = _normalized_patterns(patterns)
    result: list[str] = []
    seen: set[str] = set()
    for element_id, _element in _image_elements_iter(template):
        if element_id in seen:
            continue
        folded = element_id.casefold()
        if any(p in folded for p in normalized):
            continue
        seen.add(element_id)
        result.append(element_id)
    return result


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def image_element_specs(template: Mapping[str, Any],
                        element_ids: Sequence[str]) -> list[ImageElementSpec]:
    """One :class:`ImageElementSpec` per ``element_id`` (same order) (P15, Req 15.4; D25).

    ``width``/``height`` come from ``layout[IMAGE_ELEMENT_FORMAT]`` of the first
    element with that Element_Id and ``type == "image"``, and are included only if
    both are ``int`` > 0 (``bool`` excluded). Never mutates its arguments.
    """
    first_by_id: dict[str, dict] = {}
    for element_id, element in _image_elements_iter(template):
        first_by_id.setdefault(element_id, element)
    specs: list[ImageElementSpec] = []
    for element_id in element_ids:
        spec: ImageElementSpec = {"element_id": element_id}
        element = first_by_id.get(element_id)
        layout = element.get("layout") if element is not None else None
        fmt = layout.get(IMAGE_ELEMENT_FORMAT) if isinstance(layout, dict) else None
        if isinstance(fmt, dict):
            width, height = fmt.get("width"), fmt.get("height")
            if _positive_int(width) and _positive_int(height):
                spec["width"] = width
                spec["height"] = height
        specs.append(spec)
    return specs


def _clean_url(value: Any) -> Optional[str]:
    """URL without query string (Req 15.13), or ``None`` if not a non-empty str."""
    if not isinstance(value, str):
        return None
    url = value.partition("?")[0]
    return url if url.strip() else None


def template_preview_url(template: Mapping[str, Any]) -> Optional[str]:
    """Preview URL of a Template_Definition without query string (P15, Req 15.4, 15.13; D25).

    ``template["preview_url"]`` or, if missing/empty, the ``preview_url`` of the
    ``formats`` entry with ``id == IMAGE_ELEMENT_FORMAT`` (the ``_MOCK_TEMPLATES``
    shape); always ``url.partition("?")[0]``; ``None`` when there is none.
    """
    if not isinstance(template, dict):
        return None
    url = _clean_url(template.get("preview_url"))
    if url:
        return url
    formats = template.get("formats")
    if isinstance(formats, list):
        for fmt in formats:
            if isinstance(fmt, dict) and fmt.get("id") == IMAGE_ELEMENT_FORMAT:
                url = _clean_url(fmt.get("preview_url"))
                if url:
                    return url
    return None


def build_image_elements(template_id: str, template: Mapping[str, Any],
                         patterns: Sequence[str]) -> ImageElements:
    """:func:`template_image_elements` + :func:`image_element_specs` +
    :func:`template_preview_url` (P15, Req 15.2, 15.4; D23, D25)."""
    element_ids = template_image_elements(template, patterns)
    return ImageElements(
        template_id=str(template_id),
        element_ids=tuple(element_ids),
        specs=tuple(image_element_specs(template, element_ids)),
        preview_url=template_preview_url(template),
    )


# Received values come from the LLM and go back to it in the retry message (D25): they
# are shown with a truncated ``repr`` (non-``str`` values only by their type) and capped.
_MAX_SHOWN_CHARS = 64
_MAX_SHOWN_IDS = 20


@dataclass(frozen=True)
class _NonDict:
    """A non-dict ``image_prompts`` element: shown only by its type, even a ``str``."""

    value: Any


def _shown(value: Any) -> str:
    """``repr(value)`` truncated to 64 chars for a ``str``; ``<type>`` otherwise (D25)."""
    if isinstance(value, _NonDict):
        return f"<{type(value.value).__name__}>"
    if isinstance(value, str):
        text = repr(value)
        return text if len(text) <= _MAX_SHOWN_CHARS else text[:_MAX_SHOWN_CHARS - 3] + "..."
    return f"<{type(value).__name__}>"


def _shown_list(values: Sequence[Any]) -> str:
    """``[a, b, ...]`` with at most 20 entries shown with :func:`_shown`."""
    shown = [_shown(v) for v in values[:_MAX_SHOWN_IDS]]
    if len(values) > _MAX_SHOWN_IDS:
        shown.append(f"... (+{len(values) - _MAX_SHOWN_IDS} more)")
    return "[" + ", ".join(shown) + "]"


def _expected_element_ids(image_elements: Any) -> list[str]:
    if isinstance(image_elements, ImageElements):
        return list(image_elements.element_ids)
    if isinstance(image_elements, (str, bytes)) or not isinstance(image_elements, Sequence):
        return []
    return list(image_elements)


def check_image_elements(items: Any, image_elements: Sequence[str] | ImageElements
                         ) -> list[str]:
    """Image_Elements_Checker (P15, Req 15.5, 15.13; D25).

    One error per variant dict of ``items`` whose ``image_prompts`` is missing or not a
    list, has a non-dict element, misses an Image_Element, has an ``element_id`` that
    is not an Image_Element or that is repeated, or has an element whose
    ``element_type`` is missing or not ``"image"``. ``element_id`` values are compared
    by exact ``str`` equality (no ``strip`` nor ``casefold``). With empty Image_Elements
    only ``image_prompts == []`` is valid. ``[]`` iff every variant has exactly one
    element per Image_Element (any order), all with ``element_type == "image"``.
    Non-dict variants are left to :func:`check_variant_items`; a non-list ``items``
    returns ``[]``. Never mutates its arguments.

    Error format: ``Image prompt {variant_key!r}: element_ids {received} do not match
    Image_Elements {expected} (<reasons>)``; received values are shown with
    :func:`_shown` (at most 20), so nothing but Element_Ids and type names leaks.
    """
    if not isinstance(items, list):
        return []
    expected = _expected_element_ids(image_elements)
    expected_set = set(expected)
    errors: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        prompts = item.get("image_prompts")
        reasons: list[str] = []
        received: list[Any] = []
        if "image_prompts" not in item:
            reasons.append("image_prompts is missing")
        elif not isinstance(prompts, list):
            reasons.append("image_prompts is not a list")
        else:
            counts: dict[str, int] = {}
            non_dict = bad_type = False
            unexpected: list[Any] = []
            for element in prompts:
                if not isinstance(element, dict):
                    non_dict = True
                    received.append(_NonDict(element))
                    continue
                element_id = element.get("element_id")
                received.append(element_id)
                if element.get("element_type") != IMAGE_ELEMENT_TYPE:
                    bad_type = True
                if isinstance(element_id, str) and element_id in expected_set:
                    counts[element_id] = counts.get(element_id, 0) + 1
                else:
                    unexpected.append(element_id)
                    if isinstance(element_id, str):
                        counts[element_id] = counts.get(element_id, 0) + 1
            missing = [e for e in expected if e not in counts]
            repeated = [e for e, n in counts.items() if n > 1]
            if non_dict:
                reasons.append("element is not a dict")
            if missing:
                reasons.append(f"missing {_shown_list(missing)}")
            if unexpected:
                reasons.append(f"unexpected {_shown_list(unexpected)}")
            if repeated:
                reasons.append(f"repeated {_shown_list(repeated)}")
            if bad_type:
                reasons.append('element_type != "image"')
        if reasons:
            errors.append(
                f"Image prompt {_shown(item.get('variant_key'))}: element_ids "
                f"{_shown_list(received)} do not match Image_Elements "
                f"{_shown_list(expected)} ({'; '.join(reasons)})"
            )
    return errors


def filter_image_prompts(items: Any, element_ids: Sequence[str] | ImageElements
                         ) -> tuple[list[dict], list[tuple[str, str]]]:
    """Defence in depth before the Image_Generator (P15, Req 15.10, 15.13; D27).

    Returns deep copies of every variant dict of ``items`` with ``image_prompts``
    restricted to the dict elements whose ``element_id`` (exact ``str`` equality) is in
    ``element_ids`` — a variant left without elements keeps ``image_prompts: []`` and the
    caller skips it — plus the ``(variant_key, element_id)`` of every dropped element in
    order (non-``str`` values shown as ``<type>``, for the warnings). Non-dict variants
    are skipped; a non-list ``items`` gives ``([], [])``. Never mutates its arguments.
    """
    if not isinstance(items, list):
        return [], []
    allowed = set(_expected_element_ids(element_ids))
    kept_items: list[dict] = []
    dropped: list[tuple[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        variant_key = item.get("variant_key")
        key_label = variant_key if isinstance(variant_key, str) else _shown(variant_key)
        prompts = item.get("image_prompts")
        kept: list[dict] = []
        for element in prompts if isinstance(prompts, list) else []:
            if not isinstance(element, dict):
                dropped.append((key_label, _shown(_NonDict(element))))
                continue
            element_id = element.get("element_id")
            if isinstance(element_id, str) and element_id in allowed:
                kept.append(deepcopy(element))
            else:
                dropped.append((key_label, element_id if isinstance(element_id, str)
                                else _shown(element_id)))
        new_item = {k: deepcopy(v) for k, v in item.items() if k != "image_prompts"}
        new_item["image_prompts"] = kept
        kept_items.append(new_item)
    return kept_items, dropped


# ---------------------------------------------------------------------------
# Agent messages (deterministic text; always carry FULL ADSET CONTEXT — Req 2.5)
# ---------------------------------------------------------------------------
#
# ``adset_context`` / ``adset_context_json`` are expected to be already processed with
# ``job_runner_service._strip_signed_urls`` (done once at step 1 of ``_run_phase1``),
# exactly like the Legacy_Path. These builders never re-fetch nor re-strip the context.

FULL_ADSET_CONTEXT_HEADER = "FULL ADSET CONTEXT (use this — do NOT call get_adset_context):"


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _full_adset_context_block(adset_context_json: str) -> str:
    """Same block (header + JSON + newline) the Legacy_Path appends to every agent input."""
    return f"{FULL_ADSET_CONTEXT_HEADER}\n{adset_context_json or '{}'}\n"


def _slots_payload(slots: list[VariantSlot], *, with_angle: bool = False) -> list[dict[str, Any]]:
    """``{variant_key, template_id}`` per slot; with ``with_angle=True`` also its
    ``angle`` (only the Copywriter receives it, Req 14.6, D22)."""
    payload: list[dict[str, Any]] = []
    for s in slots:
        item: dict[str, Any] = {"variant_key": s["variant_key"], "template_id": s["template_id"]}
        if with_angle:
            item["angle"] = s.get("angle")
        payload.append(item)
    return payload


# Copywriter-only instruction block for the Variant_Angles (P14, D22, Req 14.6).
VARIANT_ANGLES_BLOCK = (
    "VARIANT ANGLES — each Variant_Slot below carries an `angle` (hook, headline_structure,\n"
    "copy_length). It tells HOW to tell this plan's message, never WHAT: write the copy of\n"
    "each variant following the angle of ITS Variant_Slot:\n"
    "- hook: the rhetorical device that delivers the primary_text opening (the hook TYPE\n"
    "  still comes from the plan's psicologia).\n"
    "- headline_structure: what the headline leads with (the headline STRUCTURE still\n"
    "  comes from the plan's intencion).\n"
    "- copy_length: short = headline ≤ 18 and primary_text ≤ 60 chars; medium = headline\n"
    "  19–23 and primary_text 61–80; long = headline 24–27 and primary_text 81–100.\n"
    "Apply the angle strictly to the FIRST option of `headline` and `primary_text`; let it\n"
    "guide the other options without breaking the multi-option rules.\n"
    "The angle refines WITHIN the Creative_Plan: if any part of it is incompatible with the\n"
    "plan, its DERIVED CONTRACT, the brand tone or do_donts, the plan wins — keep the plan\n"
    "and apply the remaining parts of the angle. Never leave the plan and never touch any\n"
    "Forbidden_Territory. Do NOT copy `angle` into your output.\n"
)


def _plan_payload(plan: CreativePlan) -> dict[str, Any]:
    """The Creative_Plan without its Variant_Slots / Project_Templates: those travel only
    in the ``Variant_Slots:`` line, so the model cannot read each variant as its own plan."""
    return {k: v for k, v in plan.items() if k not in ("variants", "_project_templates")}


def _identity_contract(plan_id: str, slots: list[VariantSlot], what: str) -> str:
    """Explicit output identity that overrides the Legacy_Path schema of the agent's
    system instruction (``plan_id`` but no ``variant_key``)."""
    first = slots[0] if slots else {"variant_key": "", "template_id": ""}
    example = {"plan_id": plan_id, "variant_key": first["variant_key"],
               "template_id": first["template_id"]}
    return (
        f"OUTPUT IDENTITY — this overrides the output schema of your instructions:\n"
        f"- Every {what} object MUST contain the keys plan_id, variant_key and "
        f"template_id, plus the fields your instructions describe.\n"
        f"- plan_id is {_dumps(plan_id)} for ALL objects. NEVER put a variant_key in "
        f"plan_id.\n"
        f"- variant_key and template_id are copied verbatim from one Variant_Slot; each "
        f"variant_key appears exactly once.\n"
        f"- Identity of the first object: {_dumps(example)}\n"
        f"- Your final answer MUST be the JSON array itself: never empty, no prose.\n"
    )


def build_estratega_message(adset_context: dict, adset_context_json: str,
                            ad_territory: AdDescription) -> str:
    """``build_estratega_adset_input(adset_context, [ad_territory])`` (Req 4.2) plus the
    ``FULL ADSET CONTEXT`` block (Req 2.5)."""
    return (
        build_estratega_adset_input(adset_context, [ad_territory])
        + _full_adset_context_block(adset_context_json)
    )


def build_copy_message(plan: CreativePlan, slots: list[VariantSlot],
                       forbidden: list[str], adset_context_json: str, *,
                       id_adset: int, ad_id: int, project_id: str) -> str:
    """Copywriter input for one Creative_Plan: exactly one copy per Variant_Slot, copying
    ``plan_id`` / ``variant_key`` / ``template_id`` from the slot, varying ``headline`` and
    ``primary_text`` across variants and never mentioning the Forbidden_Territories
    (Req 5.1, 2.5). ``slots`` may be a subset of ``plan["variants"]`` (regeneration)."""
    plan_id = plan.get("id", "")
    return (
        f"Generate copy for ONE creative plan with {len(slots)} variant(s).\n"
        f"Return ONLY a JSON array with exactly {len(slots)} copy object(s): one per "
        f"Variant_Slot below, no more, no less.\n"
        f"Each copy MUST set plan_id={_dumps(plan_id)} and copy `variant_key` and "
        f"`template_id` verbatim from its Variant_Slot (never repeat a variant_key).\n"
        f"All variants share the same creative plan: keep its concept, anchor and axes, "
        f"but vary `headline` and `primary_text` between variants.\n"
        f"Do NOT mention, allude to or build on any Forbidden_Territory.\n"
        + VARIANT_ANGLES_BLOCK
        + _identity_contract(plan_id, slots, "copy")
        + f"Plan: {_dumps(_plan_payload(plan))}\n"
        f"Variant_Slots: {_dumps(_slots_payload(slots, with_angle=True))}\n"
        f"Forbidden_Territories: {_dumps(list(forbidden))}\n"
        f"id_adset={id_adset} ad_id={ad_id} project_id={project_id}\n"
        + _full_adset_context_block(adset_context_json)
    )


_IMAGE_ELEMENTS_HEADER = (
    'IMAGE ELEMENTS — the "Image_Elements:" line below is the ONLY source of element ids:\n'
)
_IMAGE_ELEMENTS_RULES = (
    "- Every object's `image_prompts` contains EXACTLY one entry per element listed in\n"
    "  Image_Elements (any order), no more, no less.\n"
    '- Copy each `element_id` verbatim from Image_Elements and set `element_type` to "image".\n'
    "- NEVER use as element_id an id from the copies' `template_elements`: those are text\n"
    "  layers (e.g. hook, tagline) and must not receive images.\n"
)
_IMAGE_ELEMENTS_EMPTY_RULE = (
    '- Image_Elements is empty: set "image_prompts": [] in EVERY object.\n'
)
_IMAGE_ELEMENTS_LAYOUT_RULE = (
    "- You may read the template for layout, but never add elements that are not listed.\n"
)


def _image_elements_payload(image_elements: ImageElements) -> dict[str, Any]:
    """``{template_id, elements, preview_url?}`` for the ``Image_Elements:`` line
    (P15, Req 15.4, 15.13; D25). ``preview_url`` is re-stripped of its query string
    and omitted when absent, so no Signed_URL reaches the prompt."""
    elements: list[dict[str, Any]] = []
    for spec in image_elements.specs:
        item: dict[str, Any] = {"element_id": spec["element_id"]}
        if "width" in spec and "height" in spec:
            item["width"] = spec["width"]
            item["height"] = spec["height"]
        elements.append(item)
    payload: dict[str, Any] = {"template_id": image_elements.template_id,
                               "elements": elements}
    preview_url = _clean_url(image_elements.preview_url)
    if preview_url:
        payload["preview_url"] = preview_url
    return payload


def _image_elements_block(image_elements: ImageElements) -> str:
    """IMAGE ELEMENTS block + ``Image_Elements:`` line (P15, component 12; D25)."""
    rules = _IMAGE_ELEMENTS_RULES if image_elements.specs else _IMAGE_ELEMENTS_EMPTY_RULE
    return (
        _IMAGE_ELEMENTS_HEADER
        + rules
        + _IMAGE_ELEMENTS_LAYOUT_RULE
        + f"Image_Elements: {_dumps(_image_elements_payload(image_elements))}\n"
    )


def build_image_prompt_message(plan: CreativePlan, slots: list[VariantSlot],
                               copies: list[dict], adset_context_json: str, *,
                               id_adset: int, ad_id: int,
                               image_elements: ImageElements | None = None) -> str:
    """Image_Prompter input for one Creative_Plan: one item per Variant_Slot with its
    ``plan_id`` / ``variant_key`` / ``template_id`` and ``image_prompts`` built from the
    copy of the same ``variant_key`` (Req 5.7, 2.5). ``slots`` may be a subset.

    With ``image_elements`` the IMAGE ELEMENTS block and the ``Image_Elements:`` line
    are inserted after the identity contract and before ``Plan:`` (P15, Req 15.4,
    15.13; D25). With ``None`` the text is byte for byte the previous one."""
    plan_id = plan.get("id", "")
    slot_keys = {s["variant_key"] for s in slots}
    slot_copies = [c for c in copies or []
                   if isinstance(c, dict) and c.get("variant_key") in slot_keys]
    return (
        f"Generate image prompts for ONE creative plan with {len(slots)} variant(s).\n"
        f"Return ONLY a JSON array with exactly {len(slots)} object(s): one per "
        f"Variant_Slot below, no more, no less.\n"
        f"Each object MUST set plan_id={_dumps(plan_id)}, copy `variant_key` and "
        f"`template_id` verbatim from its Variant_Slot (never repeat a variant_key) and "
        f"build `image_prompts` for the copy with the same variant_key.\n"
        + _identity_contract(plan_id, slots, "image-prompt")
        + (_image_elements_block(image_elements) if image_elements is not None else "")
        + f"Plan: {_dumps(_plan_payload(plan))}\n"
        f"Variant_Slots: {_dumps(_slots_payload(slots))}\n"
        f"Copies: {_dumps(slot_copies)}\n"
        f"id_adset={id_adset} ad_id={ad_id}\n"
        + _full_adset_context_block(adset_context_json)
    )


# ---------------------------------------------------------------------------
# Validador_View (P13, D21): reduced proposal that only exists inside the message to
# the Validador_Adset. Never carries image_request / product_image_urls /
# base_image_url / product_id nor the per-proposal plan / ad_id / plan_id / template_id.
# ---------------------------------------------------------------------------

VALIDADOR_VIEW_COPY_FIELDS = ("headline", "primary_text", "description", "cta",
                              "template_elements")
VALIDADOR_VIEW_PROMPT_FIELDS = ("element_id", "image_prompt")


class ValidadorView(TypedDict, total=False):
    variant_key: str
    angle: VariantAngle
    copy: dict[str, Any]  # ⊆ VALIDADOR_VIEW_COPY_FIELDS
    image_prompts: list[dict[str, Any]]  # each ⊆ VALIDADOR_VIEW_PROMPT_FIELDS


def build_validador_view(slot: VariantSlot, proposal: Optional[dict]) -> ValidadorView:
    """Validador_View of one Variant_Slot (D21): ``variant_key`` and ``angle`` from the
    slot; ``copy`` restricted to ``VALIDADOR_VIEW_COPY_FIELDS`` (only those present) and
    ``image_prompts`` restricted to ``VALIDADOR_VIEW_PROMPT_FIELDS`` per dict element.
    A missing or non-dict copy → ``{}``; missing or non-list image_prompts → ``[]``.
    Builds new (shallow) containers; never mutates ``slot`` nor ``proposal``."""
    proposal = proposal if isinstance(proposal, dict) else {}
    copy = proposal.get("copy")
    copy = copy if isinstance(copy, dict) else {}
    prompts = proposal.get("image_prompts")
    prompts = prompts if isinstance(prompts, list) else []
    return {
        "variant_key": slot["variant_key"],
        "angle": slot.get("angle"),
        "copy": {f: copy[f] for f in VALIDADOR_VIEW_COPY_FIELDS if f in copy},
        "image_prompts": [
            {f: el[f] for f in VALIDADOR_VIEW_PROMPT_FIELDS if f in el}
            for el in prompts if isinstance(el, dict)
        ],
    }


def build_validador_views(plan: CreativePlan, proposals: list[dict]) -> list[ValidadorView]:
    """One Validador_View per Variant_Slot of ``plan["variants"]``, in slot order, pairing
    each slot with the proposal of the same ``variant_key`` (missing proposal → empty
    ``copy`` and ``image_prompts``)."""
    proposal_map = _index_by_variant_key(proposals)
    return [build_validador_view(slot, proposal_map.get(slot["variant_key"]))
            for slot in plan.get("variants", []) or []]


def build_validador_message(plan: CreativePlan, proposals: list[dict],
                            forbidden: list[str], adset_context_json: str,
                            deterministic_warnings: list[str]) -> str:
    """Validador_Adset input for one Creative_Plan (Req 7.3, 13.3, 2.5; D21, design §3).

    In order: header with the plan ``id`` and number of variants; the intended shared
    plan/axes/palette/template and the per-variant Variant_Angle; checks (a)–(c); a
    failure needs a concrete violation and an unfollowed angle is not a failure; output
    format; ``variant_keys``; Forbidden_Territories; this iteration's deterministic
    warnings (informative only); the plan once (``_plan_payload``); the Validador_Views;
    and the FULL ADSET CONTEXT block. Proposals are never dumped as such."""
    plan_id = plan.get("id", "")
    views = build_validador_views(plan, proposals)
    variant_keys = [v["variant_key"] for v in views]
    warnings_text = (
        "\n".join(f"- {w}" for w in deterministic_warnings)
        if deterministic_warnings else "- none"
    )
    return (
        f"Validate the {len(views)} variant(s) of creative plan id={_dumps(plan_id)}.\n"
        f"All variants share ON PURPOSE the same creative plan, axes, palette and "
        f"template: that is intended and never a failure. They differ only by their "
        f"Variant_Angle (`angle`: hook, headline_structure, copy_length).\n"
        f"Verify that:\n"
        f"(a) every variant respects the creative plan {_dumps(plan_id)} (concept, anchor, "
        f"axes, palette and tone);\n"
        f"(b) no variant invades any of the Forbidden_Territories listed below;\n"
        f"(c) `subset_to_regenerate` contains ONLY the variant_key of the variants that "
        f"fail (a) or (b) — never plan ids nor other values.\n"
        f"Fail a variant ONLY for a concrete violation you can point to in its copy or "
        f"in an `image_prompt`. Not following its angle is NOT a failure by itself.\n"
        f"Return ONLY a JSON object with `overall_pass` (boolean) and "
        f"`subset_to_regenerate` (list of variant_key).\n"
        f"variant_keys: {_dumps(variant_keys)}\n"
        f"Forbidden_Territories: {_dumps(list(forbidden))}\n"
        f"Deterministic diversity warnings (this iteration, informative only):\n"
        f"{warnings_text}\n"
        f"Plan: {_dumps(_plan_payload(plan))}\n"
        f"Variants: {_dumps(views)}\n"
        + _full_adset_context_block(adset_context_json)
    )
