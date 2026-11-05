"""Creative-territory schemas — the data model behind Ads Assembly v2.

These two artifacts are the center of gravity of the "distinct by construction"
architecture that defeats Meta Andromeda's Creative-Entity-ID collapse:

    adset.hypothesis  (N2)  — the product x audience hypothesis an Ad Set validates.
    ad.description    (N3)  — the creative "territory" a single Ad occupies.

Division of labor (Arquitectura del Módulo Ads Assembly — v2, §0 & §4):
    * CODE assigns diversity top-down (which anchor / which axes each ad gets) —
      deterministic, so no two ads in an adset share an anchor or axis-cell until
      the category pool is exhausted.
    * The LLM only WRITES creative text WITHIN the contract it is handed. It never
      chooses the territory and never sees sibling ads.

Ref: "Arquitectura del Módulo Ads Assembly — v2" §4 (territories), §5 (variant
operators), §6 (umbrella thread), §10 (dev handoff). Shapes mirror the JSON the
Phase-A "estratega_adset" step produces and persists (user-editable before Phase B).
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Closed vocabularies (§4). Anchors come from two definitive category sets;
# style axes are closed vocabularies and derivatives are TABLE-DRIVEN, never
# free-chosen by the LLM.
# ---------------------------------------------------------------------------

# Product-side anchor categories.
PRODUCT_ANCHOR_CATEGORIES = (
    "features",
    "benefits",
    "value_proposition",
    "competitive_advantage",
    "warranties",
    "promotions",
    "keywords",  # custom / keywords
)

# Buyer-side anchor categories.
BUYER_ANCHOR_CATEGORIES = (
    "pain_points",
    "customer_goal",
    "fears_and_worries",
    "how_they_solve_it_now",
    "barriers_to_change",
    "problem_with_current_solution",
    "customer_location",
)

ANCHOR_CATEGORIES = PRODUCT_ANCHOR_CATEGORIES + BUYER_ANCHOR_CATEGORIES

# How mutually-exclusive Ad Sets are separated (§ AdSet_Hypothesis).
SEPARATION_DIMENSIONS = (
    "tipo_de_uso",
    "territorio",
    "genero",
    "funnel_stage",
    "otro",
)


# ---------------------------------------------------------------------------
# N2 — adset.hypothesis
# ---------------------------------------------------------------------------

class MessageFrame(BaseModel):
    """What this Ad Set may / may not talk about.

    Anti-overlap rule (§4): `hablarle_de` sets must be DISJOINT across the sibling
    Ad Sets of a campaign; each `NO_hablarle_de` is auto-built from the union of the
    siblings' `hablarle_de`. Enforced in code, not by the LLM.
    """
    model_config = ConfigDict(populate_by_name=True)

    hablarle_de: list[str] = Field(default_factory=list, description="Topics/angles THIS adset owns.")
    no_hablarle_de: list[str] = Field(
        default_factory=list,
        alias="NO_hablarle_de",
        description="Topics reserved to sibling adsets — auto-derived, do not overlap.",
    )


class AdsetHypothesis(BaseModel):
    """N2 — the product x audience hypothesis an Ad Set validates.

    Mutually exclusive from its siblings on `separation_dimension`/`separation_value`,
    so audiences and messages never overlap.
    """
    adset_id: int = Field(..., description="Ad Set ID in Strapi.")
    hypothesis: str = Field(..., description="The bet this adset validates, in one sentence.")
    audience_type: Optional[str] = Field(None, description="Audience archetype/segment label.")
    separation_dimension: str = Field(
        ...,
        description=f"Dimension separating this adset from siblings. One of {SEPARATION_DIMENSIONS}.",
    )
    separation_value: str = Field(..., description="This adset's value on the separation dimension.")
    message_frame: MessageFrame = Field(default_factory=MessageFrame)
    creative_angle_ref: Optional[str] = Field(None, description="Reference to the source creative angle.")
    validation_signal: Optional[str] = Field(None, description="Metric/signal that confirms or kills the hypothesis.")


# ---------------------------------------------------------------------------
# N3 — ad.description (the creative territory)
# ---------------------------------------------------------------------------

class Anchor(BaseModel):
    """One content anchor: a category from ANCHOR_CATEGORIES + its concrete text."""
    category: str = Field(..., description=f"One of {ANCHOR_CATEGORIES}.")
    text: str = Field(..., description="The concrete anchor content pulled from product/buyer data.")


class StyleAxes(BaseModel):
    """The closed-vocabulary style cell (§4). Assigned by code; fully disjoint across
    the ads of an adset. `palette_family` is tracked separately on Territory."""
    emocion: Optional[str] = None
    intencion: Optional[str] = None
    visual_dominante: Optional[str] = None
    contexto_uso: Optional[str] = None
    psicologia: Optional[str] = None


class Derivados(BaseModel):
    """Attributes DERIVED from the axes via lookup tables — NOT chosen by the LLM (§4)."""
    headline_structure: Optional[str] = None
    hook: Optional[str] = None
    cta_family: Optional[str] = None
    photo_recipe: Optional[str] = None
    human_presence: Optional[str] = None
    setting: Optional[str] = None


class Territory(BaseModel):
    """The creative territory: one primary anchor + supporting anchors + a disjoint
    style-axis cell + table-derived attributes. ~30 anchors x axes ≈ 150k territories
    per adset, so a creative memory can guarantee non-repetition."""
    anchor_primary: Anchor
    anchor_support: list[Anchor] = Field(default_factory=list)
    axes: StyleAxes = Field(default_factory=StyleAxes)
    palette_family: Optional[str] = None
    derivados: Derivados = Field(default_factory=Derivados)


class AdDescription(BaseModel):
    """N3 — the territory contract for a single Ad. Assigned by CODE, written by the
    LLM, user-editable before variant generation. Variants (N4) are minor iterations
    WITHIN this contract and must never change the anchor, axes, or template (§5)."""
    ad_id: int = Field(..., description="Ad ID in Strapi.")
    adset_id: int = Field(..., description="Parent Ad Set ID.")
    hypothesis_link: Optional[str] = Field(None, description="Reference back to the AdsetHypothesis.")
    territory: Territory
    umbrella_reference: Optional[str] = Field(None, description="Shared umbrella Big-Idea reference (N0).")
    campaign_concept_reference: Optional[str] = Field(None, description="Campaign concept reference (N1).")
    concept: Optional[str] = Field(None, description="One-line concept summary for this ad.")
    territorio_prohibido: list[str] = Field(
        default_factory=list,
        description="Sibling ads' territories this ad must diverge from (max-divergence guard).",
    )
    template_id: Optional[str] = Field(None, description="Distinct Abyssale template for this ad.")
    n_variantes: int = Field(1, ge=1, le=4, description="Variants to generate within this territory (1–4).")
