"""Deterministic creative-territory assignment (Ads Assembly v2, Phase A / step A1).

This is the CODE half of the "distinct by construction" doctrine: given an Ad Set's
context, assign one disjoint creative territory to each of the N ad-slots BEFORE any
LLM runs. The LLM (Phase-A "estratega_adset") then only WRITES the Ad_Description text
for a territory it was handed — it never chooses the territory and never sees siblings.

Guarantees enforced here (Arquitectura del Módulo Ads Assembly — v2, §4):
  * one primary anchor per ad;
  * no two ads in an adset share a primary anchor OR its category, until the pool is
    exhausted (then it wraps and we log the collapse);
  * product/buyer rotation by slot parity (even slot → product, odd slot → buyer);
  * style-axis cells fully disjoint across ads, until a vocabulary is exhausted;
  * each ad's `territorio_prohibido` = the other ads' primary-anchor texts.

The output is a list of `AdDescription` skeletons (territory assigned, text fields left
for the LLM). Nothing here calls an LLM or Sinergia; it is a pure function over context.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from core.logging import get_logger
from schemas.territory_schemas import (
    AdDescription,
    Anchor,
    Derivados,
    StyleAxes,
    Territory,
    PRODUCT_ANCHOR_CATEGORIES,
    BUYER_ANCHOR_CATEGORIES,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Closed style-axis vocabularies (§4). Kept in code so assignment is deterministic.
# Mirrors the axis examples the legacy estratega prompt used, promoted to real config.
# ---------------------------------------------------------------------------

AXIS_VOCAB: dict[str, list[str]] = {
    "emocion": ["alegria", "orgullo", "urgencia", "curiosidad", "confianza", "aspiracion"],
    "intencion": ["informar", "persuadir", "inspirar", "entretener", "recordar"],
    "visual_dominante": ["producto", "lifestyle", "abstracto", "testimonial", "comparativo"],
    "contexto_uso": ["hogar", "trabajo", "viaje", "ejercicio", "social"],
    "psicologia": ["FOMO", "pertenencia", "autoexpresion", "logro", "seguridad"],
}

PALETTE_FAMILIES = ["calido", "frio", "monocromo", "vibrante", "pastel", "terroso"]

# Where anchor content lives inside the (unwrapped) adset payload, per category.
# (source_path, key). buyer.attributes is richer than campaign.bperson_details, so
# buyer categories read from there with a fallback handled in _read_list.
_PRODUCT_SOURCES = {cat: ("campaign", "product_details", cat) for cat in PRODUCT_ANCHOR_CATEGORIES}
_BUYER_KEY_ALIASES = {
    # our canonical category  ->  key as it appears in the Sinergia payload
    "barriers_to_change": "barriers_to_making_a_change",
    "customer_location": "hometown",
}


# ---------------------------------------------------------------------------
# Payload normalization
# ---------------------------------------------------------------------------

def unwrap_adset(tool_result: dict[str, Any]) -> dict[str, Any]:
    """Return the adset data dict regardless of mock vs real wrapping.

    Mock  get_adset_context -> {"ok":True, "adset": {"data": {...}}}   (double-wrapped)
    Real  get_adset_context -> {"ok":True, "adset": {...}}             (single-wrapped)
    """
    adset = tool_result.get("adset", tool_result) if isinstance(tool_result, dict) else {}
    if isinstance(adset, dict) and isinstance(adset.get("data"), dict):
        return adset["data"]
    return adset or {}


def _read_list(adset: dict[str, Any], side: str, category: str) -> list[str]:
    """Pull the concrete anchor texts for a category, normalized to a list[str]."""
    if side == "product":
        node = (adset.get("campaign") or {}).get("product_details") or {}
        raw = node.get(category)
    else:
        key = _BUYER_KEY_ALIASES.get(category, category)
        attrs = (adset.get("buyer") or {}).get("attributes") or {}
        raw = attrs.get(key)
        if not raw:  # fallback to the sparser campaign.bperson_details
            raw = ((adset.get("campaign") or {}).get("bperson_details") or {}).get(key)
    if not raw:
        return []
    if isinstance(raw, str):
        raw = [raw]
    return [str(x).strip() for x in raw if str(x).strip()]


def _umbrella_thread(campaign: dict[str, Any]) -> dict[str, Any]:
    """Normalize Sinergia's umbrella payload into the shared thread every ad echoes.

    Reads the canonical ``summary`` object (the consolidated final artifact, generated
    from the umbrella the user selected — internally consistent and complete) plus the
    umbrella ``title``/``description``. Falls back to the user-selected top-level fields
    if ``summary`` is absent, so it works whether or not Sinergia keeps the duplicated
    top-level keys. Shape confirmed with Luis (real /adset/{id} payload)."""
    umb = campaign.get("umbrella") or {}
    summ = umb.get("summary") or {}
    return {
        "concept_name": umb.get("title"),
        "description": umb.get("description"),
        "big_idea": summ.get("big_idea") or umb.get("big_idea"),
        "core_message": summ.get("core_message") or umb.get("message"),
        "hook": summ.get("hook") or umb.get("hook"),
        "hero": summ.get("hero_story"),
        "emotional_conflict": summ.get("emotional_conflict"),
        "solution": summ.get("solution"),
        "customer_reality": summ.get("customer_reality"),
        "concept_reality_resonance": summ.get("concept_reality_resonance"),
        "customer_journey": summ.get("customer_journey"),
    }


# ---------------------------------------------------------------------------
# Anchor inventory (A1, first half)
# ---------------------------------------------------------------------------

def inventory_anchors(adset: dict[str, Any], side: str) -> list[Anchor]:
    """Collect anchors for one side, category-interleaved so sequential picks spread
    across categories before repeating one. Empty categories are skipped."""
    categories = PRODUCT_ANCHOR_CATEGORIES if side == "product" else BUYER_ANCHOR_CATEGORIES
    by_cat: dict[str, list[str]] = {}
    for cat in categories:
        vals = _read_list(adset, side, cat)
        if vals:
            by_cat[cat] = vals
    # Interleave: 1st item of each category, then 2nd of each, ...
    ordered: list[Anchor] = []
    depth = max((len(v) for v in by_cat.values()), default=0)
    for i in range(depth):
        for cat, vals in by_cat.items():
            if i < len(vals):
                ordered.append(Anchor(category=cat, text=vals[i]))
    return ordered


# ---------------------------------------------------------------------------
# Territory assignment (A1, second half)
# ---------------------------------------------------------------------------

def _axis_cell(slot: int) -> tuple[StyleAxes, str]:
    """Assign a disjoint style-axis cell + palette to slot `i`. Disjoint while
    slot < len(vocab); wraps (with a warning) beyond that."""
    axes = StyleAxes(**{ax: vocab[slot % len(vocab)] for ax, vocab in AXIS_VOCAB.items()})
    palette = PALETTE_FAMILIES[slot % len(PALETTE_FAMILIES)]
    return axes, palette


def _derivados_for(axes: StyleAxes) -> Derivados:
    """Table-driven derivatives from the axes (§4: derived, not LLM-chosen).
    v1 lookup — deliberately simple; the full compatibility table is a follow-up."""
    hook_by_emocion = {
        "urgencia": "pregunta-directa", "curiosidad": "pregunta-abierta",
        "orgullo": "afirmacion-aspiracional", "confianza": "prueba-social",
        "alegria": "escena-positiva", "aspiracion": "vision-futura",
    }
    cta_by_intencion = {
        "persuadir": "compra", "informar": "descubre", "inspirar": "imagina",
        "entretener": "mira", "recordar": "vuelve",
    }
    return Derivados(
        headline_structure="beneficio+producto" if axes.visual_dominante == "producto" else "escena+beneficio",
        hook=hook_by_emocion.get(axes.emocion or "", "gancho-neutro"),
        cta_family=cta_by_intencion.get(axes.intencion or "", "descubre"),
        photo_recipe=f"{axes.visual_dominante or 'producto'}-{axes.contexto_uso or 'social'}",
        human_presence="con-persona" if axes.visual_dominante in ("lifestyle", "testimonial") else "sin-persona",
        setting=axes.contexto_uso,
    )


def assign_territories(
    tool_result: dict[str, Any],
    n_ads: int,
    *,
    adset_id: Optional[int] = None,
    hypothesis_link: Optional[str] = None,
    template_ids: Optional[list[str]] = None,
    n_variantes: int = 1,
) -> list[AdDescription]:
    """Assign N disjoint territories to N ad-slots. Pure, deterministic.

    Args:
        tool_result: the raw get_adset_context(...) return (mock or real).
        n_ads: number of ad-slots (territories) to produce.
        adset_id / hypothesis_link: references stamped onto each AdDescription.
        template_ids: distinct Abyssale templates to round-robin across ads.
        n_variantes: variants each ad will later expand into (1–4).
    """
    adset = unwrap_adset(tool_result)
    resolved_adset_id = adset_id if adset_id is not None else int(adset.get("id") or 0)

    product_pool = inventory_anchors(adset, "product")
    buyer_pool = inventory_anchors(adset, "buyer")
    if not product_pool and not buyer_pool:
        logger.warning("assign_territories: no anchors found in adset context; returning empty")
        return []

    thread = _umbrella_thread(adset.get("campaign") or {})
    umbrella_ref = thread.get("big_idea")
    concept_ref = thread.get("concept_name")

    ads: list[AdDescription] = []
    p_idx = b_idx = 0  # per-side cursors so within-side picks stay category-spread

    for slot in range(n_ads):
        # §4 rotation: even slot → product, odd slot → buyer (fall back to the
        # other side if one pool is empty).
        use_product = (slot % 2 == 0)
        if use_product and not product_pool:
            use_product = False
        elif not use_product and not buyer_pool:
            use_product = True

        if use_product:
            primary = product_pool[p_idx % len(product_pool)]
            if p_idx >= len(product_pool):
                logger.warning("assign_territories: product anchor pool exhausted at slot %d (reuse)", slot)
            p_idx += 1
            support_pool = buyer_pool
        else:
            primary = buyer_pool[b_idx % len(buyer_pool)]
            if b_idx >= len(buyer_pool):
                logger.warning("assign_territories: buyer anchor pool exhausted at slot %d (reuse)", slot)
            b_idx += 1
            support_pool = product_pool

        axes, palette = _axis_cell(slot)
        support = [support_pool[slot % len(support_pool)]] if support_pool else []
        template_id = template_ids[slot % len(template_ids)] if template_ids else None

        ads.append(
            AdDescription(
                ad_id=0,  # assigned on persist
                adset_id=resolved_adset_id,
                hypothesis_link=hypothesis_link,
                territory=Territory(
                    anchor_primary=primary,
                    anchor_support=support,
                    axes=axes,
                    palette_family=palette,
                    derivados=_derivados_for(axes),
                ),
                umbrella_reference=umbrella_ref,
                campaign_concept_reference=concept_ref,
                concept=None,  # LLM writes this in Phase A
                territorio_prohibido=[],  # filled below once all primaries known
                template_id=template_id,
                n_variantes=n_variantes,
            )
        )

    # Max-divergence guard: each ad must diverge from every other ad's primary territory.
    all_primaries = [a.territory.anchor_primary.text for a in ads]
    for i, ad in enumerate(ads):
        ad.territorio_prohibido = [t for j, t in enumerate(all_primaries) if j != i]

    return ads


# ---------------------------------------------------------------------------
# Phase-A LLM bridge (feeds estratega_adset_agent; pure, no LLM call here)
# ---------------------------------------------------------------------------

def build_estratega_adset_input(
    tool_result: dict[str, Any],
    territories: list[AdDescription],
    *,
    adset_hypothesis: Optional[dict[str, Any]] = None,
) -> str:
    """Build the injected message for the estratega_adset agent: umbrella thread +
    campaign concept + hypothesis + the code-assigned territories (indexed). The agent
    writes concepts WITHIN these; it never re-assigns them."""
    adset = unwrap_adset(tool_result)
    payload = {
        "umbrella": _umbrella_thread(adset.get("campaign") or {}),
        "adset_hypothesis": adset_hypothesis or {},
        "territories": [
            {
                "index": i,
                "anchor_primary": t.territory.anchor_primary.model_dump(),
                "anchor_support": [a.model_dump() for a in t.territory.anchor_support],
                "axes": t.territory.axes.model_dump(),
                "palette_family": t.territory.palette_family,
                "derivados": t.territory.derivados.model_dump(),
                "territorio_prohibido": t.territorio_prohibido,
            }
            for i, t in enumerate(territories)
        ],
    }
    return (
        "Write one Ad_Description per assigned territory. The anchor + axes are FIXED "
        "by code — write the creative concept WITHIN them and stay out of each ad's "
        "`territorio_prohibido`.\n"
        f"CONTEXT + ASSIGNED TERRITORIES:\n{json.dumps(payload, ensure_ascii=False)}\n"
    )


def apply_descriptions(
    territories: list[AdDescription],
    llm_items: list[dict[str, Any]],
) -> list[AdDescription]:
    """Merge the estratega_adset JSON output back onto the assigned territories by
    `index` (falls back to positional order). Only the written `concept` is applied;
    the assigned territory (anchor/axes/template) is never mutated."""
    by_index: dict[int, dict[str, Any]] = {}
    for pos, item in enumerate(llm_items or []):
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        by_index[int(idx) if isinstance(idx, int) else pos] = item

    for i, ad in enumerate(territories):
        item = by_index.get(i)
        if not item:
            logger.warning("apply_descriptions: no LLM concept for territory index %d", i)
            continue
        concept = item.get("concept")
        if concept:
            ad.concept = str(concept).strip()
    return territories


def territory_to_plan(ad: AdDescription, index: int) -> dict[str, Any]:
    """Adapt a territory (AdDescription) to the legacy `strategy_plan` shape that the
    copywriter / image_prompter / validador steps already consume. The axis names line
    up 1:1 with the legacy estratega's 5 axes, so downstream code is untouched — the
    only difference is that diversity is now assigned by code, not by the LLM."""
    t = ad.territory
    return {
        "id": f"plan_{index + 1}",
        "concept": ad.concept or "",
        "emocion": t.axes.emocion,
        "intencion": t.axes.intencion,
        "visual_dominante": t.axes.visual_dominante,
        "contexto_uso": t.axes.contexto_uso,
        "psicologia": t.axes.psicologia,
        "tone": t.derivados.hook,
        "color_palette": t.palette_family,
        "target_insight": t.anchor_primary.text,
        "template_id": ad.template_id,
        "template_selection_reason": "territory-assigned (deterministic)",
        # territory provenance — lets Phase B / validation see the contract it must honor
        "_territory": {
            "anchor_primary": t.anchor_primary.model_dump(),
            "palette_family": t.palette_family,
            "derivados": t.derivados.model_dump(),
            "territorio_prohibido": ad.territorio_prohibido,
        },
    }
