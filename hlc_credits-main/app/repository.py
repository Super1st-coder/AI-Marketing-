"""Persistence layer — the 4-call contract against Postgres, reusing the `lucas` domain rules.

Each mutating call is one transaction. Correctness comes from two places working together:
- the SCHEMA (reservations.job_id PK, UNIQUE(job_id, step_id)) makes reserve/commit idempotent
  even under concurrency — a replay hits the constraint instead of double-charging;
- the DOMAIN CORE (engine.lucas_for, registry pricing, Account FIFO consumption, the +10%
  tolerance and license→purchased→refund ordering) is reused so the math has ONE source of truth
  and stays identical to the 40 in-memory parity tests.

The $100/org video cap (Gate 1) is enforced here against a DB aggregate of lifetime video
spend, so it holds across process restarts and already-released jobs, not just in memory.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, pricing
from lucas.engine import (
    AUTO_RELEASE_AFTER,
    COMMIT_TOLERANCE,
    Account,
    InsufficientCredits,
    Lot,
    LotKind,
)
from lucas.service import FREE_ACTIONS, VIDEO_CAP_ACTION, VIDEO_CAP_LUCAS


class VideoCapExceeded(Exception):
    """Gate 1: this org's lifetime video spend would pass the $100 cap."""


class FreeActionBilled(Exception):
    """A caller tried to reserve/commit a FREE action (PRD §1.8) — refuse."""


class ReservationNotFound(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Coerce a DB-loaded datetime to tz-aware UTC. SQLite drops tzinfo on round-trip
    (Postgres keeps it), so normalize on read to compare safely against tz-aware `now`."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CreditsRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── org bootstrap ─────────────────────────────────────────────────────────
    def ensure_org(self, org_id: str, name: Optional[str] = None) -> models.Organization:
        org = self.db.get(models.Organization, org_id)
        if org is None:
            org = models.Organization(id=org_id, name=name)
            self.db.add(org)
            self.db.flush()
        return org

    # ── grants ────────────────────────────────────────────────────────────────
    def grant_license(self, org_id: str, lucas: int, cycle_end: datetime) -> models.Lot:
        self.ensure_org(org_id)
        lot = models.Lot(org_id=org_id, kind=LotKind.LICENSE.value, granted=lucas,
                         expires_at=cycle_end)
        self.db.add(lot)
        self._log(org_id, "license_grant", lucas=lucas)
        self.db.commit()
        return lot

    def grant_license_for_price(self, org_id: str, license_price_usd: float,
                                cycle_end: datetime) -> models.Lot:
        """Grant a license lot sized by the §1.2 rule (price_usd × 50, fixed). Callers pass
        the license PRICE, not a pre-computed Lucas amount."""
        from lucas.engine import lucas_for_license
        return self.grant_license(org_id, lucas_for_license(license_price_usd), cycle_end)

    def add_purchased(self, org_id: str, lucas: int, usd_paid: float) -> models.Lot:
        self.ensure_org(org_id)
        lot = models.Lot(org_id=org_id, kind=LotKind.PURCHASED.value, granted=lucas,
                         usd_paid=usd_paid)
        self.db.add(lot)
        self._log(org_id, "purchase", lucas=lucas)
        self.db.commit()
        return lot

    # ── balances ──────────────────────────────────────────────────────────────
    def _lots(self, org_id: str) -> list[models.Lot]:
        return list(self.db.scalars(
            select(models.Lot).where(models.Lot.org_id == org_id)
            .order_by(models.Lot.created_at)))

    def _load_account(self, org_id: str) -> tuple[Account, dict[str, models.Lot]]:
        """Reconstruct a pure Account (lots + ACTIVE reservations) from the DB so we can
        reuse the engine's available()/FIFO. Returns the account and a lot_id->row map."""
        acct = Account(org_id)
        row_by_id: dict[str, models.Lot] = {}
        for row in self._lots(org_id):
            lot = Lot(lot_id=str(row.id), kind=LotKind(row.kind), granted=row.granted,
                      consumed=row.consumed, expires_at=_aware(row.expires_at),
                      usd_paid=row.usd_paid)
            acct.lots.append(lot)
            row_by_id[str(row.id)] = row
        active = self.db.scalars(
            select(models.Reservation).where(models.Reservation.org_id == org_id,
                                             models.Reservation.status == "active"))
        for r in active:
            from lucas.engine import Reservation as DReservation
            acct.reservations[r.job_id] = DReservation(
                job_id=r.job_id, action_id=r.action_id, brand_id=r.brand_id,
                lucas_reserved=r.lucas_reserved, model_id=r.model_id,
                model_version=r.model_version, lucas_committed=r.lucas_committed)
        return acct, row_by_id

    def available(self, org_id: str, now: Optional[datetime] = None) -> int:
        acct, _ = self._load_account(org_id)
        return acct.available(now or _utcnow())

    def balance_detail(self, org_id: str, now: Optional[datetime] = None) -> dict:
        now = now or _utcnow()
        acct, _ = self._load_account(org_id)
        from app.config import settings
        from app.usage_alerts import usage
        consumed, granted, pct = usage(self.db, org_id)
        return {
            "available": acct.available(now),
            "license": acct.license_balance(now),
            "purchased": acct.purchased_balance(now),
            "reserved": acct.reserved_total(),
            "video_spend": self.video_spend(org_id),
            "video_cap": VIDEO_CAP_LUCAS,
            "used": consumed,
            "granted": granted,
            "usage_pct": round(pct, 4),
            "topup_url": settings.LUCA_CREDITS_TOPUP_URL,
        }

    # ── video cap (Gate 1) ──────────────────────────────────────────────────────
    def video_spend(self, org_id: str) -> int:
        """Lifetime video-GENERATION Lucas (video_segment): committed steps (any status) +
        budget still held by ACTIVE video_segment reservations. Survives restarts/released jobs."""
        committed = self.db.execute(
            select(func.coalesce(func.sum(models.ReservationStep.lucas), 0))
            .select_from(models.ReservationStep)
            .join(models.Reservation, models.ReservationStep.job_id == models.Reservation.job_id)
            .where(models.Reservation.org_id == org_id,
                   models.Reservation.action_id == VIDEO_CAP_ACTION)).scalar_one()
        held = self.db.execute(
            select(func.coalesce(
                func.sum(models.Reservation.lucas_reserved - models.Reservation.lucas_committed), 0))
            .where(models.Reservation.org_id == org_id,
                   models.Reservation.status == "active",
                   models.Reservation.action_id == VIDEO_CAP_ACTION)).scalar_one()
        return int(committed) + int(held)

    # ── estimate → reserve → commit → release ───────────────────────────────────
    def estimate(self, model_id: str, qty: float) -> int:
        lucas, _version = pricing.price_current(self.db, model_id, qty)
        return lucas

    def reserve(self, org_id: str, job_id: str, action_id: str, brand_id: str,
                model_id: str, qty: float, *, now: Optional[datetime] = None,
                expected_end_at: Optional[datetime] = None) -> models.Reservation:
        now = now or _utcnow()
        if action_id in FREE_ACTIONS:
            raise FreeActionBilled(f"{action_id} is free and must not be reserved")
        self.ensure_org(org_id)
        existing = self.db.get(models.Reservation, job_id)
        if existing is not None:
            return existing                                   # idempotent by job_id
        # Price at the CURRENT registry version and freeze that version onto the reservation.
        lucas, version = pricing.price_current(self.db, model_id, qty)  # gate + clip enforced
        if action_id == VIDEO_CAP_ACTION and self.video_spend(org_id) + lucas > VIDEO_CAP_LUCAS:
            raise VideoCapExceeded(
                f"video cap ${VIDEO_CAP_LUCAS // 100}/org: "
                f"{self.video_spend(org_id)} used, +{lucas} exceeds {VIDEO_CAP_LUCAS}")
        if lucas > self.available(org_id, now):
            raise InsufficientCredits(
                f"need {lucas} Lucas, {self.available(org_id, now)} available")
        res = models.Reservation(
            job_id=job_id, org_id=org_id, action_id=action_id, brand_id=brand_id,
            lucas_reserved=lucas, model_id=model_id, model_version=version, status="active",
            expected_end_at=expected_end_at or (now + AUTO_RELEASE_AFTER))
        self.db.add(res)
        self._log(org_id, "reserve", lucas=-lucas, job_id=job_id, action_id=action_id)
        self.db.commit()
        return res

    def commit(self, org_id: str, job_id: str, step_id: str, model_id: str,
               qty_real: float, *, now: Optional[datetime] = None) -> int:
        now = now or _utcnow()
        res = self.db.get(models.Reservation, job_id)
        if res is None or res.org_id != org_id:
            raise ReservationNotFound(f"no reservation {job_id} for org {org_id}")
        if res.status != "active":
            raise ValueError(f"reservation {job_id} is {res.status}, not active")
        existing = self.db.scalar(
            select(models.ReservationStep).where(models.ReservationStep.job_id == job_id,
                                                 models.ReservationStep.step_id == step_id))
        if existing is not None:
            return existing.lucas                              # idempotent by (job_id, step_id)
        # Price against the reservation's FROZEN (model_id, version) — a price edit after the
        # reserve must not change what this job is charged.
        lucas_real = pricing.price_at_version(self.db, res.model_id, res.model_version, qty_real)
        ceiling = math.ceil(res.lucas_reserved * (1 + COMMIT_TOLERANCE))
        flagged = (res.lucas_committed + lucas_real) > ceiling
        self._consume_fifo(org_id, lucas_real, now)
        res.lucas_committed += lucas_real
        self.db.add(models.ReservationStep(job_id=job_id, step_id=step_id, lucas=lucas_real,
                                           flagged_over_tolerance=flagged))
        self._log(org_id, "commit", lucas=-lucas_real, job_id=job_id, step_id=step_id,
                  meta={"flagged_over_tolerance": flagged})
        self.db.commit()
        # V1 spend protection: fire 50/75/90% usage alerts as consumption grows (best-effort;
        # never let an alert failure break a commit that already succeeded).
        try:
            from app.usage_alerts import check_and_notify
            check_and_notify(self.db, org_id)
        except Exception as alert_err:  # pragma: no cover
            logger = __import__("logging").getLogger(__name__)
            logger.warning("usage-alert check failed for org %s: %s", org_id, alert_err)
        return lucas_real

    def release(self, org_id: str, job_id: str, reason: str = "done") -> str:
        res = self.db.get(models.Reservation, job_id)
        if res is None or res.org_id != org_id:
            raise ReservationNotFound(f"no reservation {job_id} for org {org_id}")
        if res.status != "active":
            return res.status                                 # already terminal — idempotent
        unspent = max(0, res.lucas_reserved - res.lucas_committed)
        res.status = "settled" if res.lucas_committed > 0 else "released"
        self._log(org_id, "release", lucas=unspent, job_id=job_id,
                  meta={"reason": reason, "status": res.status})
        self.db.commit()
        return res.status

    def sweep_expired(self, now: Optional[datetime] = None) -> int:
        now = now or _utcnow()
        rows = self.db.scalars(
            select(models.Reservation).where(models.Reservation.status == "active"))
        n = 0
        for res in rows:
            end = _aware(res.expected_end_at)
            if end is None or end > now:
                continue
            res.status = "expired"
            self._log(res.org_id, "release", lucas=max(0, res.lucas_reserved - res.lucas_committed),
                      job_id=res.job_id, meta={"reason": "auto_expire", "status": "expired"})
            n += 1
        self.db.commit()
        return n

    # ── internals ───────────────────────────────────────────────────────────────
    def _consume_fifo(self, org_id: str, lucas: int, now: datetime) -> None:
        """Reuse the engine's FIFO ordering by loading lots into an Account, consuming, and
        writing lot.consumed back to the rows — keeps ONE definition of the consumption order."""
        acct, row_by_id = self._load_account(org_id)
        acct._consume_fifo(lucas, now, job_id="", step_id="")   # raises if lots can't cover
        for lot in acct.lots:
            row = row_by_id[lot.lot_id]
            row.consumed = lot.consumed

    def _log(self, org_id: str, entry_type: str, *, lucas: int = 0, job_id: Optional[str] = None,
             step_id: Optional[str] = None, action_id: Optional[str] = None,
             meta: Optional[dict] = None) -> None:
        self.db.add(models.LedgerEntry(
            org_id=org_id, entry_type=entry_type, lucas=lucas, job_id=job_id,
            step_id=step_id, action_id=action_id, meta=meta))
