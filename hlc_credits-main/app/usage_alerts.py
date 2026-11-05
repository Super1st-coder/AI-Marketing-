"""Usage alerts — V1 spend protection (Marco 2026-09-23).

Email the org at 50% / 75% / 90% of its Lucas used, each with a top-up link, so a client
never silently hits zero and calls Marco because they can't generate ads. Each threshold
fires once (deduped against the ledger). Email isn't wired yet, so the alert goes through a
notifier SEAM (same pattern as the finance-notify hook in pricing.py) — swap it for real
email later. The top-up link is `LUCA_CREDITS_TOPUP_URL` (a static Stripe Payment Link in V1).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings

logger = logging.getLogger(__name__)

# Fire at these fractions of Lucas used. Ordered low→high.
THRESHOLDS: tuple[float, ...] = (0.50, 0.75, 0.90)

_ALERT_ENTRY = "usage_alert"   # ledger entry_type used to dedupe

# Notifier seam. Real email goes here later; for now it logs a structured event.
_notifier: Callable[[dict], None] = lambda event: logger.info("USAGE_ALERT %s", event)


def set_alert_notifier(fn: Callable[[dict], None]) -> None:
    global _notifier
    _notifier = fn


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def usage(db: Session, org_id: str) -> tuple[int, int, float]:
    """Return (consumed, granted, pct_used) across the org's lots. pct is consumed/granted."""
    lots = db.scalars(select(models.Lot).where(models.Lot.org_id == org_id)).all()
    granted = sum(l.granted for l in lots)
    consumed = sum(l.consumed for l in lots)
    pct = (consumed / granted) if granted else 0.0
    return consumed, granted, pct


def _already_notified(db: Session, org_id: str) -> set[float]:
    """Thresholds already alerted for this org (from the ledger). V1 dedupes org-lifetime;
    the cycle-renewal job will reset these when it lands."""
    rows = db.scalars(
        select(models.LedgerEntry).where(models.LedgerEntry.org_id == org_id,
                                         models.LedgerEntry.entry_type == _ALERT_ENTRY)).all()
    sent: set[float] = set()
    for r in rows:
        t = (r.meta or {}).get("threshold")
        if isinstance(t, (int, float)):
            sent.add(float(t))
    return sent


def check_and_notify(db: Session, org_id: str, *, commit: bool = True) -> list[float]:
    """Fire any newly-crossed thresholds for the org. Returns the thresholds fired.
    Idempotent: a threshold already recorded in the ledger never fires again."""
    consumed, granted, pct = usage(db, org_id)
    if granted <= 0:
        return []
    already = _already_notified(db, org_id)
    fired: list[float] = []
    for t in THRESHOLDS:
        if pct >= t and t not in already:
            _notifier({
                "event": "usage_alert", "org_id": org_id, "threshold": t,
                "pct_used": round(pct, 4), "consumed": consumed, "granted": granted,
                "top_up_url": settings.LUCA_CREDITS_TOPUP_URL,
            })
            db.add(models.LedgerEntry(
                org_id=org_id, entry_type=_ALERT_ENTRY, lucas=0,
                meta={"threshold": t, "pct_used": round(pct, 4)}))
            fired.append(t)
    if fired and commit:
        db.commit()
    return fired
