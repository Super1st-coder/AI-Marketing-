"""DB-driven pricing — the model_registry table is the runtime source of truth.

Marco's central-authority mandate (2026-09-09): the versioned registry is the ONLY editable
price table; a price changes WITHOUT a deploy. This module reads/writes those rows.

The MATH stays single-source: pricing still goes through lucas.engine.lucas_for (the exact
Decimal formula the 47-parity suite covers). Only the price DATA moves from code to the DB.

Version freezing: reserve() stamps the CURRENT version onto the reservation; commit() prices
against THAT frozen (model_id, version) row — so a price edit mid-job never re-prices in-flight
work. Old rows are kept (is_current=False) precisely so a frozen version stays resolvable.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from lucas.engine import lucas_for
from lucas.registry import UnpricedModel

logger = logging.getLogger(__name__)


class UnknownModel(KeyError):
    """No registry row for this model_id (current, or the requested frozen version)."""


# Finance-notification seam. Marco §4(1): auto-email finance on every price edit. Email isn't
# wired yet, so edits emit a structured event here; swap this for the real notifier later.
_notifier: Callable[[dict], None] = lambda event: logger.info("REGISTRY_EDIT %s", event)


def set_notifier(fn: Callable[[dict], None]) -> None:
    global _notifier
    _notifier = fn


def current_row(db: Session, model_id: str) -> models.ModelRegistryRow:
    row = db.scalar(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == model_id,
        models.ModelRegistryRow.is_current.is_(True)))
    if row is None:
        raise UnknownModel(f"no current registry row for {model_id!r}")
    return row


def row_at_version(db: Session, model_id: str, version: str) -> models.ModelRegistryRow:
    row = db.scalar(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == model_id,
        models.ModelRegistryRow.version == version))
    if row is None:
        raise UnknownModel(f"no registry row for {model_id!r} version {version!r}")
    return row


def price_row(row: models.ModelRegistryRow, qty: float) -> int:
    """Lucas for `qty` units against a specific registry row. Refuses gated rows and clips."""
    if not row.sellable:
        raise UnpricedModel(f"{row.model_id} is not sellable: {row.gate_reason}")
    # max_seconds is per-CLIP shot-planner metadata, NOT a pricing gate: a reservation is a
    # whole video job whose total seconds legitimately exceed one clip's cap. Enforcing it
    # here refused every real video reserve (PRD §1.5). Pricing is rate × qty. (Durval 2026-09-23)
    return lucas_for(row.provider_cost_usd, qty=qty, multiplier=row.multiplier)


def price_current(db: Session, model_id: str, qty: float) -> tuple[int, str]:
    """Price at the current version. Returns (lucas, version) so reserve can freeze the version."""
    row = current_row(db, model_id)
    return price_row(row, qty), row.version


def price_at_version(db: Session, model_id: str, version: str, qty: float) -> int:
    """Price at a FROZEN version — used by commit so a mid-job price edit doesn't apply."""
    return price_row(row_at_version(db, model_id, version), qty)


def set_price(db: Session, model_id: str, *, provider_cost_usd: Optional[float] = None,
              multiplier: Optional[float] = None, sellable: Optional[bool] = None,
              gate_reason: Optional[str] = None, max_seconds: Optional[int] = None,
              verified_at: Optional[str] = None, edited_by: str = "admin") -> models.ModelRegistryRow:
    """Edit a price WITHOUT a deploy: supersede the current row with a new version and notify
    finance. Fields left None inherit from the current row. Returns the new current row.

    Un-gating (sellable False→True) requires a real provider_cost_usd in the same edit —
    you can't flip a gated model live while it still has no confirmed cost."""
    cur = db.scalar(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.model_id == model_id,
        models.ModelRegistryRow.is_current.is_(True)))
    if cur is None:
        raise UnknownModel(f"cannot edit unknown model {model_id!r}")

    new_cost = cur.provider_cost_usd if provider_cost_usd is None else provider_cost_usd
    new_sellable = cur.sellable if sellable is None else sellable
    if new_sellable and not cur.sellable and (provider_cost_usd is None or provider_cost_usd <= 0):
        raise ValueError(f"un-gating {model_id} requires a confirmed provider_cost_usd > 0")

    next_version = str(int(cur.version) + 1) if cur.version.isdigit() else f"{cur.version}+1"
    cur.is_current = False
    new_row = models.ModelRegistryRow(
        model_id=model_id, version=next_version, provider_cost_usd=new_cost,
        unit=cur.unit, multiplier=cur.multiplier if multiplier is None else multiplier,
        max_seconds=cur.max_seconds if max_seconds is None else max_seconds,
        sellable=new_sellable,
        gate_reason=(None if new_sellable else (gate_reason if gate_reason is not None else cur.gate_reason)),
        verified_at=verified_at if verified_at is not None else cur.verified_at,
        is_current=True, edited_by=edited_by)
    db.add(new_row)
    db.commit()
    _notifier({
        "event": "registry_price_edit", "model_id": model_id,
        "from_version": cur.version, "to_version": next_version,
        "old_cost_usd": cur.provider_cost_usd, "new_cost_usd": new_cost,
        "sellable": new_sellable, "edited_by": edited_by,
    })
    return new_row
