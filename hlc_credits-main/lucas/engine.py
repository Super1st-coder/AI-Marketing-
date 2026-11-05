"""LucaCredit — Lucas ledger core (pure domain logic, no DB/framework).

Ports the reference prototype (engine.ts + registry.ts + types.ts) to Python so it
can drop into the production Credits service on kpp.hiluca.com. Persistence + the
FastAPI layer wrap this; the rules here mirror the Luca Credits PRD §1.3–§1.6 and
are what the 47 parity tests exercise.

Model: org = wallet · brand = license · Lucas = fuel.
- License lots refill monthly and EXPIRE at cycle_end; purchased/refund_grant lots NEVER expire.
- estimate (free, writes nothing) → reserve (blocks on available, no partial, idempotent by job_id)
  → commit (N, idempotent by job_id:step_id, frozen price, +10% tolerance, consumes lots FIFO)
  → release (terminal; SETTLED if any commits else RELEASED; returns unspent).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import ROUND_CEILING, Decimal
from enum import Enum
from typing import Optional


# 100 Lucas = $1  →  1 Lucas = $0.01. lucas = ceil(usd × multiplier ÷ 0.01) = usd × mult × 100.
USD_PER_LUCA = 0.01
DEFAULT_MULTIPLIER = 5.0
COMMIT_TOLERANCE = 0.10          # commit may exceed the reservation by up to +10% (PRD §1.5)
AUTO_RELEASE_AFTER = timedelta(minutes=30)   # orphaned ACTIVE reservations auto-expire

# License grant: PRD §1.2 hard rule `included_lucas = license_price_usd × 50`.
# FIXED constant, deliberately independent of DEFAULT_MULTIPLIER — Marco 2026-09-24:
# "the ×50 grant must NOT be derived from the multiplier; if a model's multiplier changes
# in the registry the grant stays ×50." ($750 license → 37,500 Lucas.) Do NOT implement the
# "10% of license" wording literally — that's the same number expressed in real cost, not a
# second formula (10% of $750 at 100 Lucas/$1 would be 7,500 = 5× too few).
LICENSE_LUCAS_PER_USD = 50


def lucas_for_license(license_price_usd: float) -> int:
    """Lucas granted for a brand license (§1.2): price_usd × 50, fixed. Not tied to the
    consumption multiplier."""
    if license_price_usd < 0:
        raise ValueError("license_price_usd must be non-negative")
    return int(round(license_price_usd * LICENSE_LUCAS_PER_USD))


def lucas_for(provider_cost_usd: float, qty: float = 1.0, multiplier: float = DEFAULT_MULTIPLIER) -> int:
    """PRD §1.3 pricing formula. Divide by 0.01 (× 100), NOT multiply — the ×0.01 form
    under-charges 10,000×. Example: nano-banana-2 $0.067 × 5 ÷ 0.01 = 33.5 → 34 Lucas.

    Uses Decimal so the ceil is exact: in float, $0.04 × 24 × 5 ÷ 0.01 = 480.00000000000006,
    which would ceil to 481 and over-charge the customer by 1 Lucas. Decimal(str(x)) keeps
    the numbers at their written precision, so 24s of h3max is exactly 480."""
    if provider_cost_usd < 0 or qty < 0:
        raise ValueError("provider_cost_usd and qty must be non-negative")
    lucas = (Decimal(str(provider_cost_usd)) * Decimal(str(multiplier)) * Decimal(str(qty))
             / Decimal(str(USD_PER_LUCA)))
    return int(lucas.to_integral_value(rounding=ROUND_CEILING))


class LotKind(str, Enum):
    LICENSE = "license"          # refilled monthly, expires at cycle_end
    PURCHASED = "purchased"      # bought pack, never expires
    REFUND_GRANT = "refund_grant"  # behaves like purchased


class ReservationStatus(str, Enum):
    ACTIVE = "active"
    SETTLED = "settled"          # released after >=1 commit
    RELEASED = "released"        # released with no commits
    EXPIRED = "expired"          # auto-released after the timeout


@dataclass
class Lot:
    lot_id: str
    kind: LotKind
    granted: int                 # Lucas granted to this lot
    consumed: int = 0            # Lucas consumed from it
    expires_at: Optional[datetime] = None
    usd_paid: float = 0.0

    @property
    def remaining(self) -> int:
        return self.granted - self.consumed

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at is not None and now >= self.expires_at


@dataclass
class Reservation:
    job_id: str
    action_id: str
    brand_id: str
    lucas_reserved: int
    model_id: str
    model_version: str
    status: ReservationStatus = ReservationStatus.ACTIVE
    lucas_committed: int = 0
    expected_end_at: Optional[datetime] = None
    committed_steps: dict[str, int] = field(default_factory=dict)  # step_id -> lucas (idempotency)

    @property
    def unspent(self) -> int:
        return max(0, self.lucas_reserved - self.lucas_committed)


class InsufficientCredits(Exception):
    """reserve() failed: requested Lucas exceed available balance."""


class Account:
    """One organization's Lucas wallet: its lots + reservations + a running ledger.

    Pure in-memory; the production service persists lots/reservations/ledger_entries and
    wraps these same operations behind the estimate/reserve/commit/release endpoints.
    """

    def __init__(self, org_id: str):
        self.org_id = org_id
        self.lots: list[Lot] = []
        self.reservations: dict[str, Reservation] = {}
        self.ledger: list[dict] = []

    # ── grants ────────────────────────────────────────────────────────────────
    def grant_license(self, lot_id: str, lucas: int, cycle_end: datetime) -> Lot:
        lot = Lot(lot_id, LotKind.LICENSE, granted=lucas, expires_at=cycle_end)
        self.lots.append(lot)
        self._log("license_grant", lucas=lucas, lot_id=lot_id)
        return lot

    def grant_license_for_price(self, lot_id: str, license_price_usd: float,
                                cycle_end: datetime) -> Lot:
        """Grant a license lot sized by the §1.2 rule (price_usd × 50). Convenience over
        grant_license so callers pass the license PRICE, not a pre-computed Lucas amount."""
        return self.grant_license(lot_id, lucas_for_license(license_price_usd), cycle_end)

    def add_purchased(self, lot_id: str, lucas: int, usd_paid: float) -> Lot:
        lot = Lot(lot_id, LotKind.PURCHASED, granted=lucas, usd_paid=usd_paid)  # no expiry
        self.lots.append(lot)
        self._log("purchase", lucas=lucas, lot_id=lot_id)
        return lot

    # ── balance (PRD balance math) ──────────────────────────────────────────────
    def license_balance(self, now: datetime) -> int:
        return sum(l.remaining for l in self.lots if l.kind is LotKind.LICENSE and not l.is_expired(now))

    def purchased_balance(self, now: datetime) -> int:
        return sum(l.remaining for l in self.lots
                   if l.kind in (LotKind.PURCHASED, LotKind.REFUND_GRANT) and not l.is_expired(now))

    def reserved_total(self) -> int:
        return sum(r.unspent for r in self.reservations.values() if r.status is ReservationStatus.ACTIVE)

    def available(self, now: Optional[datetime] = None) -> int:
        now = now or _utcnow()
        return self.license_balance(now) + self.purchased_balance(now) - self.reserved_total()

    # ── estimate → reserve → commit → release ───────────────────────────────────
    def estimate(self, provider_cost_usd: float, qty: float = 1.0,
                 multiplier: float = DEFAULT_MULTIPLIER) -> int:
        """FREE — writes nothing, holds nothing (PRD Annex A #8)."""
        return lucas_for(provider_cost_usd, qty, multiplier)

    def reserve(self, job_id: str, action_id: str, brand_id: str, lucas: int, *,
                model_id: str, model_version: str, now: Optional[datetime] = None,
                expected_end_at: Optional[datetime] = None) -> Reservation:
        """Blocks HERE (and only here) against available. No partial reservations.
        Idempotent by job_id: re-reserving the same job returns the existing reservation."""
        now = now or _utcnow()
        if job_id in self.reservations:
            return self.reservations[job_id]            # idempotent
        if lucas > self.available(now):
            raise InsufficientCredits(
                f"need {lucas} Lucas, {self.available(now)} available")
        res = Reservation(job_id, action_id, brand_id, lucas_reserved=lucas,
                          model_id=model_id, model_version=model_version,
                          expected_end_at=expected_end_at or (now + AUTO_RELEASE_AFTER))
        self.reservations[job_id] = res
        self._log("reserve", lucas=-lucas, job_id=job_id, action_id=action_id)
        return res

    def commit(self, job_id: str, step_id: str, lucas_real: int,
               now: Optional[datetime] = None) -> int:
        """One commit per step, idempotent by (job_id, step_id). Consumes lots FIFO.
        Accepts real usage up to +10% over the reservation; beyond that it's flagged."""
        now = now or _utcnow()
        res = self._active(job_id)
        if step_id in res.committed_steps:               # idempotent
            return res.committed_steps[step_id]
        ceiling = math.ceil(res.lucas_reserved * (1 + COMMIT_TOLERANCE))
        flagged = (res.lucas_committed + lucas_real) > ceiling
        self._consume_fifo(lucas_real, now, job_id, step_id)
        res.lucas_committed += lucas_real
        res.committed_steps[step_id] = lucas_real
        self._log("commit", lucas=-lucas_real, job_id=job_id, step_id=step_id,
                  flagged_over_tolerance=flagged)
        return lucas_real

    def release(self, job_id: str, reason: str = "done") -> ReservationStatus:
        """Terminal. SETTLED if it had commits, else RELEASED. Frees the unspent hold."""
        res = self._active(job_id)
        unspent = res.unspent
        res.status = ReservationStatus.SETTLED if res.lucas_committed > 0 else ReservationStatus.RELEASED
        self._log("release", lucas=unspent, job_id=job_id, reason=reason, status=res.status.value)
        return res.status

    def sweep_expired(self, now: Optional[datetime] = None) -> int:
        """Auto-release ACTIVE reservations past expected_end_at (orphan guard). Returns count."""
        now = now or _utcnow()
        n = 0
        for res in self.reservations.values():
            if res.status is ReservationStatus.ACTIVE and res.expected_end_at and now >= res.expected_end_at:
                res.status = ReservationStatus.EXPIRED
                self._log("release", lucas=res.unspent, job_id=res.job_id,
                          reason="auto_expire", status=res.status.value)
                n += 1
        return n

    # ── internals ───────────────────────────────────────────────────────────────
    def _consume_fifo(self, lucas: int, now: datetime, job_id: str, step_id: str) -> None:
        """Consume from: current license lot → purchased oldest-first → refund_grant (PRD §1.6)."""
        order = (
            [l for l in self.lots if l.kind is LotKind.LICENSE and not l.is_expired(now)]
            + [l for l in self.lots if l.kind is LotKind.PURCHASED and not l.is_expired(now)]
            + [l for l in self.lots if l.kind is LotKind.REFUND_GRANT and not l.is_expired(now)]
        )
        need = lucas
        for lot in order:
            if need <= 0:
                break
            take = min(need, lot.remaining)
            if take <= 0:
                continue
            lot.consumed += take
            need -= take
        if need > 0:
            # Reservation guaranteed availability, so this means the reservation was bypassed.
            raise InsufficientCredits(f"commit {lucas} exceeds available lots by {need}")

    def _active(self, job_id: str) -> Reservation:
        res = self.reservations.get(job_id)
        if res is None:
            raise KeyError(f"no reservation for job {job_id}")
        if res.status is not ReservationStatus.ACTIVE:
            raise ValueError(f"reservation {job_id} is {res.status.value}, not active")
        return res

    def _log(self, entry_type: str, **fields) -> None:
        self.ledger.append({"type": entry_type, "at": _utcnow().isoformat(), **fields})


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
