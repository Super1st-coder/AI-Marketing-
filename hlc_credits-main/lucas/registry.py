"""LucaCredit — versioned model registry (the ONLY editable price table).

Ports the reference prototype's registry.ts. This is the platform pricing authority
Marco mandated (2026-09-09): every module estimates/charges through here, no module
keeps its own price table. Prices are provider_cost_usd PER UNIT; the Lucas charge is
`lucas_for(provider_cost_usd, qty, multiplier)` = ceil(usd × mult × qty ÷ 0.01).

Rules baked in:
- Each entry carries a `version` and a `verified_at` — commit() freezes the model_version
  it charged against so a later price edit never re-prices an in-flight job (PRD §1.5).
- `sellable=False` GATES a model: estimate/reserve refuse it until a real, confirmed price
  exists. Used for the price-or-drop gaps Durval flagged (FLUX 3, Seedance 2.5 1080p tier)
  — pricing a tier we can't cost, or a resolution BytePlus can't serve, would over/under-charge.
- Confirmed prices: PRD §1.3 + Marco's ADK CHANGELOG v2.5. Anything not confirmed is gated,
  not guessed. Real BytePlus/FLUX rates are pending from Luis (HLC-9).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from .engine import DEFAULT_MULTIPLIER, lucas_for


class Unit(str, Enum):
    PER_SECOND = "per_second"      # video: qty = clip seconds
    PER_IMAGE = "per_image"        # image: qty = images
    PER_1K_TOKENS = "per_1k_tokens"
    PER_1K_CHARS = "per_1k_chars"  # TTS


@dataclass(frozen=True)
class ModelPrice:
    model_id: str
    provider_cost_usd: float       # USD per unit (per second / image / 1k tokens / 1k chars)
    unit: Unit
    version: str                   # registry row version; frozen onto commits
    verified_at: str               # ISO date the price was confirmed (or "" if gated)
    max_seconds: Optional[int] = None   # provider per-clip max (video) — shot-planner metadata
    min_seconds: Optional[int] = None   # provider per-clip min (video) — shot-planner metadata
    multiplier: float = DEFAULT_MULTIPLIER
    sellable: bool = True          # False = gated: no estimate/reserve until priced
    gate_reason: str = ""          # why it's gated (shown to callers)
    note: str = ""


class UnpricedModel(Exception):
    """Raised when a caller tries to price/reserve a model that isn't sellable yet."""


# ── the table ────────────────────────────────────────────────────────────────
# provider_cost_usd is REAL provider cost per unit; Lucas = that × multiplier ÷ 0.01.
_ROWS: dict[str, ModelPrice] = {}


def _register(p: ModelPrice) -> None:
    _ROWS[p.model_id] = p


# Video — per second. Default = minimax-h3-max (cheapest/sec; Durval 2026-09-22).
# MiniMax prices by RESOLUTION (Durval 2026-09-23): 480p $0.025 · 768p $0.04 · 1080p $0.08.
# ⚠️ These are fal's LAUNCH-PROMO prices, live until 2026-09-30; on Sep 30 all three DOUBLE
# (480p→$0.05, 768p→$0.08, 1080p→$0.16). Bump via set_price on Sep 30 (versioned, no deploy);
# the weekly drift job flags it if we forget. Base `minimax-h3-max` aliases the 768p default;
# callers pick the tier via the -480p/-768p/-1080p ids. min clip 5s, max 15s (planner metadata).
_register(ModelPrice("minimax-h3-max", 0.04, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-23", max_seconds=15, min_seconds=5,
                     note="768p default alias; promo to 2026-09-30 (then $0.08)"))
_register(ModelPrice("minimax-h3-max-480p", 0.025, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-23", max_seconds=15, min_seconds=5,
                     note="promo to 2026-09-30 (then $0.05)"))
_register(ModelPrice("minimax-h3-max-768p", 0.04, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-23", max_seconds=15, min_seconds=5,
                     note="promo to 2026-09-30 (then $0.08)"))
_register(ModelPrice("minimax-h3-max-1080p", 0.08, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-23", max_seconds=15, min_seconds=5,
                     note="promo to 2026-09-30 (then $0.16)"))
_register(ModelPrice("seedance-2.0-mini", 0.08, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-22", max_seconds=15))
_register(ModelPrice("seedance-2.0-fast", 0.12, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-22", max_seconds=15))
_register(ModelPrice("seedance-2.0-std-720p", 0.15, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-22", max_seconds=15))
_register(ModelPrice("seedance-2.0-std-1080p", 0.37, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-22", max_seconds=15))
_register(ModelPrice("veo-3.1-lite", 0.05, Unit.PER_SECOND, version="1",
                     verified_at="2026-09-22", max_seconds=8,
                     note="Marco ADK CHANGELOG v2.5"))

# GATED video — priced tiers we cannot trust yet (price-or-drop; HLC-9, pending Luis).
_register(ModelPrice("veo-3.1", 0.0, Unit.PER_SECOND, version="0", verified_at="",
                     max_seconds=8, sellable=False,
                     gate_reason="full veo-3.1 per-second rate not confirmed (only Lite $0.05 is)"))
_register(ModelPrice("seedance-2.5-720p", 0.0, Unit.PER_SECOND, version="0", verified_at="",
                     max_seconds=30, sellable=False,
                     gate_reason="PRD $0.231 unconfirmed vs real BytePlus 480/720 rates (HLC-9)"))
_register(ModelPrice("seedance-2.5-1080p", 0.0, Unit.PER_SECOND, version="0", verified_at="",
                     max_seconds=30, sellable=False,
                     gate_reason="BytePlus serves 480p/720p only — no 1080p tier exists to price"))
_register(ModelPrice("flux-3", 0.0, Unit.PER_SECOND, version="0", verified_at="",
                     max_seconds=20, sellable=False,
                     gate_reason="no confirmed price (REGISTRY_GAPS) — price or drop (HLC-9)"))
_register(ModelPrice("kling", 0.0, Unit.PER_SECOND, version="0", verified_at="",
                     sellable=False,
                     gate_reason="video PRD excludes (no audio) — not billable in V1"))

# Image / text / audio — per their units.
_register(ModelPrice("nano-banana-2", 0.067, Unit.PER_IMAGE, version="1",
                     verified_at="2026-09-22"))
_register(ModelPrice("gemini-3.1-pro-input", 0.002, Unit.PER_1K_TOKENS, version="1",
                     verified_at="2026-09-22", note="input tokens"))
_register(ModelPrice("gemini-3.1-pro-output", 0.012, Unit.PER_1K_TOKENS, version="1",
                     verified_at="2026-09-22", note="output tokens"))
_register(ModelPrice("tts", 0.03, Unit.PER_1K_CHARS, version="1", verified_at="2026-09-22"))


# ── lookups ──────────────────────────────────────────────────────────────────
def get(model_id: str) -> ModelPrice:
    row = _ROWS.get(model_id)
    if row is None:
        raise KeyError(f"unknown model_id {model_id!r}")
    return row


def is_sellable(model_id: str) -> bool:
    return get(model_id).sellable


def price_lucas(model_id: str, qty: float) -> int:
    """Lucas charge for `qty` units of `model_id`. Refuses gated models — a caller must
    never get a price for something we can't correctly cost."""
    row = get(model_id)
    if not row.sellable:
        raise UnpricedModel(f"{model_id} is not sellable: {row.gate_reason}")
    # NOTE: max_seconds is the per-CLIP provider cap — it is shot-planner metadata, NOT a
    # pricing gate. A reservation covers a whole video job (many shots, total seconds can
    # exceed one clip's cap); enforcing the cap here refused every real video reserve
    # (PRD §1.5 = one reservation per job). Pricing is just rate × qty. (Durval 2026-09-23)
    return lucas_for(row.provider_cost_usd, qty=qty, multiplier=row.multiplier)


def model_version(model_id: str) -> str:
    """The version string to freeze onto a reservation/commit for this model."""
    return get(model_id).version


def sellable_models() -> list[str]:
    return [m for m, r in _ROWS.items() if r.sellable]


def gated_models() -> dict[str, str]:
    """Gated model_id -> reason (for the drift/reconciliation report and HLC-9 coord)."""
    return {m: r.gate_reason for m, r in _ROWS.items() if not r.sellable}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
