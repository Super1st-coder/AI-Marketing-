"""LucaCredit — billing service facade (the 4-call contract other modules call).

Ties the registry (price table) to Account (ledger) and layers V1 spend-protection on top.
This is what the FastAPI endpoints wrap 1:1 and what Durval's video module calls:

    POST /api/v1/billing/estimate   -> estimate(org, model_id, qty)          [FREE]
    POST /api/v1/billing/reserve    -> reserve(org, job_id, action, ..., model_id, qty)
    POST /api/v1/billing/commit     -> commit(org, job_id, step_id, model_id, qty_real)
    POST /api/v1/billing/release    -> release(org, job_id, reason)

Callers pass model_id + qty (seconds / images / 1k-tokens), never Lucas — pricing is the
service's job so no module keeps its own price table (Marco's platform-authority mandate).

Gate 1 (MAX priority, Marco 2026-09-18): video spend is capped at $100 PER ORGANIZATION.
Enforced at reserve: (committed video Lucas + active video reservations + this request)
must stay under the cap. estimate stays free and never blocks (PRD Annex A #8) — the cap
bites only when a job actually tries to hold budget.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from . import registry
from .engine import Account, InsufficientCredits, Reservation, lucas_for

# Gate 1: $100/org video cap → 10,000 Lucas (100 Lucas = $1).
VIDEO_CAP_LUCAS = 100 * 100

# Billable video actions (Durval's integration contract 2026-09-22).
VIDEO_ACTIONS = frozenset({
    "video_scripts", "video_andromeda_score", "video_storyboard", "video_voiceover",
    "video_segment", "video_visual_direction", "video_edit_shot", "video_regenerate_audio",
})

# The $100/org cap is enforced on VIDEO GENERATION only — the "Select the variants to
# generate" step (Marco + Video PRD §1.8, 2026-09-23), which is the expensive one. The
# cheaper adjacent steps (scripts/scoring/storyboard/voiceover) don't count toward it.
# Extensions fold into video_segment (same action_id, more qty), so they can't dodge it.
VIDEO_CAP_ACTION = "video_segment"

# Steps that must NEVER bill (PRD §1.8) — the service refuses to reserve/commit them.
FREE_ACTIONS = frozenset({
    "video_scripts_only", "video_regenerate_ai_edited", "restore_history",
})


class VideoCapExceeded(Exception):
    """Gate 1: this org's video spend would pass the $100 cap."""


class FreeActionBilled(Exception):
    """A caller tried to reserve/commit a FREE action — refuse (PRD §1.8)."""


class BillingService:
    """Holds one Account per organization and enforces V1 spend protection.

    In production the Account state is persisted (lots/reservations/ledger tables); this
    facade is the same regardless — swap the in-memory dict for a repository.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, Account] = {}

    def account(self, org_id: str) -> Account:
        acct = self._accounts.get(org_id)
        if acct is None:
            acct = self._accounts[org_id] = Account(org_id)
        return acct

    # ── estimate (FREE) ──────────────────────────────────────────────────────
    def estimate(self, org_id: str, model_id: str, qty: float) -> int:
        """Price a request in Lucas. Free, holds nothing, never blocks. Refuses gated models
        (registry raises UnpricedModel) so callers never get a price we can't cost."""
        return registry.price_lucas(model_id, qty)

    # ── reserve ──────────────────────────────────────────────────────────────
    def reserve(self, org_id: str, job_id: str, action_id: str, brand_id: str,
                model_id: str, qty: float, *, now: Optional[datetime] = None,
                expected_end_at: Optional[datetime] = None) -> Reservation:
        if action_id in FREE_ACTIONS:
            raise FreeActionBilled(f"{action_id} is free and must not be reserved")
        acct = self.account(org_id)
        lucas = registry.price_lucas(model_id, qty)   # also enforces gate + clip cap
        if action_id == VIDEO_CAP_ACTION:
            self._check_video_cap(acct, additional=lucas)
        return acct.reserve(job_id, action_id, brand_id, lucas,
                            model_id=model_id, model_version=registry.model_version(model_id),
                            now=now, expected_end_at=expected_end_at)

    # ── commit ───────────────────────────────────────────────────────────────
    def commit(self, org_id: str, job_id: str, step_id: str, model_id: str,
               qty_real: float, *, now: Optional[datetime] = None) -> int:
        """Charge real usage for one step. Priced from the SAME registry; the reservation's
        frozen model_version guards against a price edit mid-job."""
        acct = self.account(org_id)
        lucas_real = registry.price_lucas(model_id, qty_real)
        return acct.commit(job_id, step_id, lucas_real, now=now)

    # ── release ──────────────────────────────────────────────────────────────
    def release(self, org_id: str, job_id: str, reason: str = "done"):
        return self.account(org_id).release(job_id, reason)

    # ── balances / gate helpers ──────────────────────────────────────────────
    def balance(self, org_id: str, now: Optional[datetime] = None) -> int:
        return self.account(org_id).available(now)

    def video_spend(self, acct: Account) -> int:
        """Lucas committed + still held by active video-GENERATION reservations (video_segment)."""
        committed = sum(e.get("lucas", 0) for e in acct.ledger
                        if e["type"] == "commit" and self._is_video_step(acct, e))
        # commit log entries store negative lucas (a debit); count magnitude
        committed = -committed if committed < 0 else committed
        reserved = sum(r.unspent for r in acct.reservations.values()
                       if r.action_id == VIDEO_CAP_ACTION and r.status.value == "active")
        return committed + reserved

    def _check_video_cap(self, acct: Account, additional: int) -> None:
        current = self.video_spend(acct)
        if current + additional > VIDEO_CAP_LUCAS:
            raise VideoCapExceeded(
                f"video cap ${VIDEO_CAP_LUCAS // 100}/org: {current} Lucas used, "
                f"+{additional} would exceed {VIDEO_CAP_LUCAS}")

    @staticmethod
    def _is_video_step(acct: Account, entry: dict) -> bool:
        res = acct.reservations.get(entry.get("job_id"))
        return res is not None and res.action_id == VIDEO_CAP_ACTION
