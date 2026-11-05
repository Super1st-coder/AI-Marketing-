"""Deterministic Diversity_Checker for the Adset creative-diversity path (Req 6).

The Diversity_Path builds one Creative_Plan per Ad from territories assigned in code
(``services.territory_assignment``). This module is the code-side verification of that
structural diversity: it never calls an LLM or the network and never reads the adset
context. The same input always produces the same output, with messages in a stable
order (by Ad_Slot pair and, for variants, by ``variant_key``).

Errors and warnings are returned separately:

* an *error* is a repetition that should not happen given the available pool or
  vocabulary (Req 6.2, 6.3);
* a *warning* is the same repetition when the pool or vocabulary is exhausted, i.e.
  when the assignment had no choice but to reuse a value (Req 6.10).

Template rule 6.7 follows Decision P11 (one Ad_Template per Ad): every Variant_Slot,
copy and image prompt of an Ad must share the same ``template_id``; a mismatch is
always an error (``TEMPLATE_MIXED_IN_AD``), never a 6.10 warning. Rule 6.12
(``check_ad_templates``) requires distinct Ad_Templates between Ad_Slots while there
are enough Project_Templates; beyond that, repetitions are 6.10 warnings.

Pool sizes are computed by the caller with
``inventory_anchors(unwrap_adset(ctx), side)``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional, Sequence

from schemas.territory_schemas import PRODUCT_ANCHOR_CATEGORIES, AdDescription, Anchor
from services.adset_diversity import ANGLE_VOCABULARY, first_text, is_valid_variant_angle
from services.territory_assignment import AXIS_VOCAB, PALETTE_FAMILIES

if TYPE_CHECKING:  # pragma: no cover - typing only
    from services.adset_diversity import CreativePlan

AnchorSide = Literal["product", "buyer"]
ItemKind = Literal["copy", "image_prompt"]

ANCHOR_REPEATED = "ANCHOR_REPEATED"
AXIS_REPEATED = "AXIS_REPEATED"
PALETTE_REPEATED = "PALETTE_REPEATED"
PLAN_ID_MISMATCH = "PLAN_ID_MISMATCH"
COUNT_MISMATCH = "COUNT_MISMATCH"
TEMPLATE_NOT_IN_PROJECT = "TEMPLATE_NOT_IN_PROJECT"
TEMPLATE_MIXED_IN_AD = "TEMPLATE_MIXED_IN_AD"
COPY_REPEATED = "COPY_REPEATED"
FORBIDDEN_TERRITORY = "FORBIDDEN_TERRITORY"
FORBIDDEN_IS_OWN_ANCHOR = "FORBIDDEN_IS_OWN_ANCHOR"
AD_TEMPLATE_REPEATED = "AD_TEMPLATE_REPEATED"
ANGLE_MISSING = "ANGLE_MISSING"
ANGLE_NOT_IN_VOCABULARY = "ANGLE_NOT_IN_VOCABULARY"
ANGLE_REPEATED = "ANGLE_REPEATED"


@dataclass(frozen=True)
class DiversityIssue:
    """One diversity finding (error or warning)."""

    code: str  # e.g. "ANCHOR_REPEATED", "AXIS_REPEATED", "PLAN_ID_MISMATCH"
    message: str  # human-readable text with slots / variant_key / value
    variant_keys: tuple[str, ...] = ()
    ad_slots: tuple[int, ...] = ()


@dataclass(frozen=True)
class DiversityCheckResult:
    """Errors and warnings of a check, kept in the order they were produced."""

    errors: tuple[DiversityIssue, ...] = ()
    warnings: tuple[DiversityIssue, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors

    def error_messages(self) -> list[str]:
        return [issue.message for issue in self.errors]

    def warning_messages(self) -> list[str]:
        return [issue.message for issue in self.warnings]

    def failing_variant_keys(self) -> set[str]:
        """Union of the ``variant_keys`` of all errors (warnings never trigger regeneration)."""
        return {key for issue in self.errors for key in issue.variant_keys}

    def merged(self, other: "DiversityCheckResult") -> "DiversityCheckResult":
        """Concatenate ``self`` then ``other`` (order preserved, so still deterministic)."""
        return DiversityCheckResult(
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
        )


def anchor_side(anchor: Anchor) -> AnchorSide:
    """Side of an anchor, by membership of its category in PRODUCT_ANCHOR_CATEGORIES."""
    return "product" if anchor.category in PRODUCT_ANCHOR_CATEGORIES else "buyer"


def check_territories(
    territories: Sequence[AdDescription],
    *,
    product_pool_size: int,
    buyer_pool_size: int,
) -> DiversityCheckResult:
    """Req 6.2, 6.3, 6.10. For each pair of Ad_Slots (i < j), slot = index in ``territories``:

    - same ``anchor_primary.text`` (after ``strip()`` + ``casefold()``) → error if the number of slots whose primary anchor
      comes from that side is ≤ the pool size of that side, otherwise warning;
    - same value on an axis of ``AXIS_VOCAB`` or on ``palette_family`` → error if the
      number of slots is ≤ the vocabulary size, otherwise warning.

    Missing (``None``) axis/palette values are not compared. Issues are ordered by
    pair (i, j), then anchor, axes in ``AXIS_VOCAB`` order, palette.
    """
    pool_sizes: dict[AnchorSide, int] = {"product": product_pool_size, "buyer": buyer_pool_size}
    sides: list[AnchorSide] = [anchor_side(t.territory.anchor_primary) for t in territories]
    side_counts: dict[AnchorSide, int] = {
        "product": sides.count("product"),
        "buyer": sides.count("buyer"),
    }
    n_slots = len(territories)

    errors: list[DiversityIssue] = []
    warnings: list[DiversityIssue] = []

    def _add(issue: DiversityIssue, exhausted: bool) -> None:
        (warnings if exhausted else errors).append(issue)

    def _repeated(value_i: Optional[str], value_j: Optional[str]) -> bool:
        return value_i is not None and value_i == value_j

    for i in range(n_slots):
        terr_i = territories[i].territory
        for j in range(i + 1, n_slots):
            terr_j = territories[j].territory

            # Req 6.2 — primary anchor text, compared after strip() + casefold();
            # the message shows the text of slot i.
            text = terr_i.anchor_primary.text
            if _normalize(text) == _normalize(terr_j.anchor_primary.text):
                involved = {sides[i], sides[j]}
                exhausted = all(side_counts[s] > pool_sizes[s] for s in sorted(involved))
                side_label = "/".join(sorted(involved))
                suffix = f" ({side_label} anchor pool exhausted)" if exhausted else ""
                _add(
                    DiversityIssue(
                        code=ANCHOR_REPEATED,
                        message=(
                            f"Ad_Slots {i} and {j} repeat anchor_primary.text "
                            f"{text!r}{suffix}"
                        ),
                        ad_slots=(i, j),
                    ),
                    exhausted,
                )

            # Req 6.3 — style axes.
            for axis, vocab in AXIS_VOCAB.items():
                value = getattr(terr_i.axes, axis)
                if _repeated(value, getattr(terr_j.axes, axis)):
                    exhausted = n_slots > len(vocab)
                    suffix = f" (axis vocabulary of {len(vocab)} exhausted)" if exhausted else ""
                    _add(
                        DiversityIssue(
                            code=AXIS_REPEATED,
                            message=(
                                f"Ad_Slots {i} and {j} repeat axis {axis} = "
                                f"{value!r}{suffix}"
                            ),
                            ad_slots=(i, j),
                        ),
                        exhausted,
                    )

            # Req 6.3 — palette family.
            palette = terr_i.palette_family
            if _repeated(palette, terr_j.palette_family):
                exhausted = n_slots > len(PALETTE_FAMILIES)
                suffix = (
                    f" (palette vocabulary of {len(PALETTE_FAMILIES)} exhausted)"
                    if exhausted
                    else ""
                )
                _add(
                    DiversityIssue(
                        code=PALETTE_REPEATED,
                        message=(
                            f"Ad_Slots {i} and {j} repeat palette_family = "
                            f"{palette!r}{suffix}"
                        ),
                        ad_slots=(i, j),
                    ),
                    exhausted,
                )

    return DiversityCheckResult(errors=tuple(errors), warnings=tuple(warnings))


def check_ad_templates(
    slot_templates: Sequence[str], project_templates: Sequence[str]
) -> DiversityCheckResult:
    """Req 6.12 and 6.10 (Decision P11, D16): Ad_Templates must differ between Ad_Slots.

    ``slot_templates[s]`` is the Ad_Template of Ad_Slot ``s`` (built by the caller with
    ``slot_ad_templates(n_slots, project_templates)``). For each pair ``i < j`` with the
    same ``template_id`` → ``AD_TEMPLATE_REPEATED`` with ``ad_slots=(i, j)``:

    - error if ``len(slot_templates) <= len(project_templates)`` (enough templates for
      every Ad, so a repetition is a regression in the formula or the deduplication);
    - warning otherwise (templates exhausted, rotation is expected — Req 6.10).

    Pure and deterministic: inputs are not mutated and issues are ordered by (i, j).
    """
    templates = list(slot_templates)
    n_slots = len(templates)
    exhausted = n_slots > len(project_templates)
    suffix = f" ({len(project_templates)} Project_Templates exhausted)" if exhausted else ""

    issues: list[DiversityIssue] = []
    for i in range(n_slots):
        for j in range(i + 1, n_slots):
            if templates[i] == templates[j]:
                issues.append(
                    DiversityIssue(
                        code=AD_TEMPLATE_REPEATED,
                        message=(
                            f"Ad_Slots {i} and {j} share Ad_Template "
                            f"{templates[i]!r}{suffix}"
                        ),
                        ad_slots=(i, j),
                    )
                )

    if exhausted:
        return DiversityCheckResult(warnings=tuple(issues))
    return DiversityCheckResult(errors=tuple(issues))


# ---------------------------------------------------------------------------
# Variant rules (Req 6.4–6.9)
# ---------------------------------------------------------------------------

_KIND_LABEL: dict[str, str] = {"copy": "copies", "image_prompt": "image prompts"}


def _normalize(text: str) -> str:
    """Comparison form used by rules 6.2, 6.8 and 6.9: ``strip()`` + ``casefold()``.
    Non-strings (e.g. ``None``) normalise to ``""``."""
    return text.strip().casefold() if isinstance(text, str) else ""


def _slot_keys(plan: "CreativePlan") -> list[str]:
    slots = plan.get("variants") or []
    return [str(slot.get("variant_key", "")) for slot in slots if isinstance(slot, dict)]


def _item_key(item: Any, index: int, slot_keys: Sequence[str]) -> str:
    """``variant_key`` of an item; when missing, the slot key at the same index, or
    ``"#<1-based index>"`` if there is no such slot."""
    if isinstance(item, dict):
        key = item.get("variant_key")
        if isinstance(key, str) and key:
            return key
    return slot_keys[index] if index < len(slot_keys) else f"#{index + 1}"


def _keyed_items(
    items: Sequence[Any], slot_keys: Sequence[str]
) -> list[tuple[str, dict[str, Any]]]:
    """``(variant_key, item)`` per item, in input order (non-dicts become ``{}``)."""
    return [
        (_item_key(item, idx, slot_keys), item if isinstance(item, dict) else {})
        for idx, item in enumerate(items)
    ]


def _template_issues(
    keyed: Sequence[tuple[str, Any]],
    project_templates: Sequence[str],
    label: str,
    plan_id: Any,
) -> list[DiversityIssue]:
    """Rules 6.6 then 6.7 over the ``(variant_key, template_id)`` pairs of one collection.

    - 6.6: a ``template_id`` that is empty, ``None`` or not in ``project_templates``
      → error with the ``variant_key`` and the received value.
    - 6.7 (P11, one template per Ad): the first item's ``template_id`` is the reference;
      every later item with a different value → ``TEMPLATE_MIXED_IN_AD`` error naming
      the Ad (``plan_id``), both ``variant_key`` and both ``template_id``. Always an
      error, regardless of the number of slots or templates (never a 6.10 warning).
    """
    allowed = {t for t in project_templates if isinstance(t, str) and t}
    issues: list[DiversityIssue] = []
    for key, template_id in keyed:
        if not (isinstance(template_id, str) and template_id and template_id in allowed):
            issues.append(
                DiversityIssue(
                    code=TEMPLATE_NOT_IN_PROJECT,
                    message=(
                        f"{label} {key}: template_id {template_id!r} is empty or not "
                        f"in Project_Templates"
                    ),
                    variant_keys=(key,),
                )
            )
    if keyed:
        ref_key, ref_tpl = keyed[0]
        for key, template_id in keyed[1:]:
            if template_id != ref_tpl:
                issues.append(
                    DiversityIssue(
                        code=TEMPLATE_MIXED_IN_AD,
                        message=(
                            f"Ad {plan_id!r}: {label} {ref_key} uses template_id "
                            f"{ref_tpl!r} but {key} uses {template_id!r} "
                            f"(all variants of an Ad must share one template)"
                        ),
                        variant_keys=(ref_key, key),
                    )
                )
    return issues


def check_variant_slots(
    plan: "CreativePlan", project_templates: Sequence[str], n_variants: int
) -> DiversityCheckResult:
    """Req 6.6 and 6.7 on the Variant_Slots of ``plan``.

    - a slot whose ``template_id`` is empty, ``None`` or not in ``project_templates``
      → ``TEMPLATE_NOT_IN_PROJECT`` error;
    - a slot whose ``template_id`` differs from the first slot's → ``TEMPLATE_MIXED_IN_AD``
      error with both ``variant_key`` (P11: one Ad_Template per Ad). Never a warning,
      whatever ``n_variants`` or ``len(project_templates)``.

    ``n_variants`` is kept for API stability; rule 6.7 no longer depends on it.
    Issues follow slot order (6.6 first, then 6.7).
    """
    slots = [s for s in (plan.get("variants") or []) if isinstance(s, dict)]
    keyed = [(str(s.get("variant_key", "")), s.get("template_id")) for s in slots]
    errors = _template_issues(keyed, project_templates, "Variant_Slot", plan.get("id"))
    return DiversityCheckResult(errors=tuple(errors))


def check_variant_angles(plan: "CreativePlan", n_variants: int) -> DiversityCheckResult:
    """Req 6.13 and 6.10 (P14) on the Variant_Slots of ``plan``, in slot order:

    - a slot without an ``angle`` key or with ``None`` → ``ANGLE_MISSING`` error
      (``variant_keys=(key,)``);
    - an ``angle`` that is not a dict equal to an element of ``ANGLE_VOCABULARY``
      → ``ANGLE_NOT_IN_VOCABULARY`` error with the received value;
    - then, for each pair ``i < j`` of slots with valid and equal (``==``) angles
      → ``ANGLE_REPEATED`` with ``variant_keys=(key_i, key_j)``: error if
      ``n_variants <= len(ANGLE_VOCABULARY)``, warning otherwise (vocabulary exhausted).

    Every issue names the Ad (``plan["id"]``). Copies and image prompts are never read
    (Req 14.8). Pure and deterministic: the input is not mutated.
    """
    plan_id = plan.get("id")
    slots = [s for s in (plan.get("variants") or []) if isinstance(s, dict)]
    errors: list[DiversityIssue] = []
    warnings: list[DiversityIssue] = []

    valid: list[tuple[str, Any]] = []  # (variant_key, angle) of slots with a valid angle
    for slot in slots:
        key = str(slot.get("variant_key", ""))
        angle = slot.get("angle")
        if angle is None:
            errors.append(
                DiversityIssue(
                    code=ANGLE_MISSING,
                    message=f"Ad {plan_id!r}: Variant_Slot {key} has no angle",
                    variant_keys=(key,),
                )
            )
        elif not is_valid_variant_angle(angle):
            errors.append(
                DiversityIssue(
                    code=ANGLE_NOT_IN_VOCABULARY,
                    message=(
                        f"Ad {plan_id!r}: Variant_Slot {key} angle {angle!r} is not "
                        f"in Angle_Vocabulary"
                    ),
                    variant_keys=(key,),
                )
            )
        else:
            valid.append((key, angle))

    exhausted = n_variants > len(ANGLE_VOCABULARY)
    suffix = (
        f" (Angle_Vocabulary of {len(ANGLE_VOCABULARY)} exhausted)" if exhausted else ""
    )
    target = warnings if exhausted else errors
    for i in range(len(valid)):
        key_i, angle_i = valid[i]
        for j in range(i + 1, len(valid)):
            key_j, angle_j = valid[j]
            if angle_i == angle_j:
                target.append(
                    DiversityIssue(
                        code=ANGLE_REPEATED,
                        message=(
                            f"Ad {plan_id!r}: Variant_Slots {key_i} and {key_j} share "
                            f"angle {angle_i!r}{suffix}"
                        ),
                        variant_keys=(key_i, key_j),
                    )
                )

    return DiversityCheckResult(errors=tuple(errors), warnings=tuple(warnings))


def _own_anchor(plan: "CreativePlan") -> str:
    territory = plan.get("_territory")
    if isinstance(territory, dict):
        anchor = territory.get("anchor_primary")
        if isinstance(anchor, dict) and isinstance(anchor.get("text"), str):
            return anchor["text"]
    insight = plan.get("target_insight")
    return insight if isinstance(insight, str) else ""


def check_variants(
    plan: "CreativePlan",
    copies: Sequence[dict],
    image_prompts: Sequence[dict],
    *,
    project_templates: Sequence[str],
    n_variants: int,
    forbidden: Sequence[str],
) -> DiversityCheckResult:
    """Req 6.4–6.9 on the copies and image prompts of one Ad (D6).

    Order of issues: 6.5 (counts: copies, image prompts), 6.4 (``plan_id``), 6.6/6.7
    (``template_id``) — each for copies then image prompts — then 6.8 (pairs of copies)
    and 6.9 (copies × forbidden texts). Within a rule, items keep their input order.

    - 6.5's issue lists the slot ``variant_key`` that are missing or duplicated.
    - 6.7 is checked per collection: the first item's ``template_id`` is the reference
      and every item with another value is a ``TEMPLATE_MIXED_IN_AD`` error.
    - 6.8/6.9 use the first ``headline`` / ``primary_text`` (``first_text``) compared after
      ``strip()`` and case-insensitively. For 6.8 both values must be non-empty after
      ``strip()``; the 6.9 message names the field(s) (``headline``, ``primary_text`` or
      both), the ``variant_key`` and the forbidden text.
    - 6.4: a missing or ``None`` ``plan_id`` is always an error (received vs expected).
    - D6: forbidden texts empty after ``strip()`` are ignored; a forbidden text equal to
      the plan's own ``anchor_primary.text`` (pool exhausted, Req 3.10) is not used for
      6.9 and produces a warning instead.
    """
    plan_id = plan.get("id")
    slot_keys = _slot_keys(plan)
    errors: list[DiversityIssue] = []
    warnings: list[DiversityIssue] = []

    groups: list[tuple[ItemKind, list[tuple[str, dict[str, Any]]]]] = [
        ("copy", _keyed_items(copies, slot_keys)),
        ("image_prompt", _keyed_items(image_prompts, slot_keys)),
    ]

    # Req 6.5 — number of copies / image prompts.
    for kind, keyed in groups:
        if len(keyed) != n_variants:
            present = [key for key, _ in keyed]
            affected = tuple(k for k in slot_keys if present.count(k) != 1)
            errors.append(
                DiversityIssue(
                    code=COUNT_MISMATCH,
                    message=(
                        f"Ad {plan_id!r}: expected {n_variants} {_KIND_LABEL[kind]}, "
                        f"got {len(keyed)}"
                    ),
                    variant_keys=affected,
                )
            )

    # Req 6.4 — plan_id of every variant; missing or None is always an error.
    for kind, keyed in groups:
        for key, item in keyed:
            received = item.get("plan_id")
            if received is None or received != plan_id:
                errors.append(
                    DiversityIssue(
                        code=PLAN_ID_MISMATCH,
                        message=(
                            f"{kind} {key}: plan_id {received!r} "
                            f"(missing or wrong), expected {plan_id!r}"
                        ),
                        variant_keys=(key,),
                    )
                )

    # Req 6.6 / 6.7 — template_id of every variant.
    for kind, keyed in groups:
        errors.extend(
            _template_issues(
                [(key, item.get("template_id")) for key, item in keyed],
                project_templates,
                kind,
                plan_id,
            )
        )

    copy_texts = [
        (
            key,
            _normalize(first_text(item.get("headline"))),
            _normalize(first_text(item.get("primary_text"))),
        )
        for key, item in groups[0][1]
    ]

    # Req 6.8 — identical first headline and first primary_text between two variants.
    # Only non-empty values count: missing, None, [] or "" (after strip) never match.
    for a in range(len(copy_texts)):
        key_a, head_a, text_a = copy_texts[a]
        if not (head_a and text_a):
            continue
        for b in range(a + 1, len(copy_texts)):
            key_b, head_b, text_b = copy_texts[b]
            if head_a == head_b and text_a == text_b:
                errors.append(
                    DiversityIssue(
                        code=COPY_REPEATED,
                        message=(
                            f"copies {key_a} and {key_b} repeat the first headline and "
                            f"primary_text"
                        ),
                        variant_keys=(key_a, key_b),
                    )
                )

    # Req 6.9 + D6 — Forbidden_Territories as literal substrings.
    own_anchor = _normalize(_own_anchor(plan))
    active: list[tuple[str, str]] = []  # (original text, normalized), deduplicated
    seen: set[str] = set()
    for text in forbidden:
        if not isinstance(text, str):
            continue
        norm = _normalize(text)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if own_anchor and norm == own_anchor:
            warnings.append(
                DiversityIssue(
                    code=FORBIDDEN_IS_OWN_ANCHOR,
                    message=(
                        f"forbidden text {text.strip()!r} is the plan's own "
                        f"anchor_primary.text; ignored for rule 6.9"
                    ),
                )
            )
            continue
        active.append((text.strip(), norm))

    for key, head, body in copy_texts:
        for original, norm in active:
            fields = [name for name, value in (("headline", head), ("primary_text", body))
                      if norm in value]
            if fields:
                errors.append(
                    DiversityIssue(
                        code=FORBIDDEN_TERRITORY,
                        message=(
                            f"copy {key}: {' and '.join(fields)} "
                            f"contain{'s' if len(fields) == 1 else ''} forbidden "
                            f"territory {original!r}"
                        ),
                        variant_keys=(key,),
                    )
                )

    return DiversityCheckResult(errors=tuple(errors), warnings=tuple(warnings))
