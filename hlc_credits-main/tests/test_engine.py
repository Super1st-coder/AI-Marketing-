"""Parity tests for the Lucas ledger core — encode the Luca Credits PRD §1.3–§1.6 rules.

Mirrors the reference prototype's 47-test intent; swap in the exact reference cases
once we have engine.ts's suite. Run: `cd hlc_credits && python -m pytest -q`.
"""
from datetime import datetime, timedelta, timezone

import pytest

from lucas.engine import (
    Account,
    InsufficientCredits,
    LotKind,
    ReservationStatus,
    lucas_for,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
CYCLE_END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)


# ── pricing formula (the ÷0.01 that Durval caught) ──────────────────────────────
def test_formula_prd_example_nano_banana():
    # $0.067 × 5 ÷ 0.01 = 33.5 → 34 Lucas
    assert lucas_for(0.067, qty=1, multiplier=5.0) == 34


def test_formula_video_24s_h3max():
    # 24s × $0.04/s = $0.96 provider cost → ×5 ÷ 0.01 = 480 Lucas ($4.80)
    assert lucas_for(0.04, qty=24, multiplier=5.0) == 480


def test_formula_is_not_the_10000x_undercharge():
    # the ×0.01 bug would have yielded ~0/1 Lucas — assert we're nowhere near it
    assert lucas_for(0.96, qty=1, multiplier=5.0) == 480


def test_formula_rejects_negative():
    with pytest.raises(ValueError):
        lucas_for(-1.0)


# ── balance math ────────────────────────────────────────────────────────────────
def test_available_is_license_plus_purchased_minus_reserved():
    acct = Account("org1")
    acct.grant_license("lic-oct", 10_000, CYCLE_END)
    acct.add_purchased("pack-1", 10_000, usd_paid=100.0)
    assert acct.available(NOW) == 20_000
    acct.reserve("job1", "video_segment", "brand1", 5_000,
                 model_id="veo-3.1-lite", model_version="v1", now=NOW)
    assert acct.available(NOW) == 15_000  # reservation holds 5k


def test_estimate_is_free_and_holds_nothing():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    before_avail = acct.available(NOW)
    before_entries = len(acct.ledger)  # the grant legitimately logged one entry
    est = acct.estimate(0.10, qty=10)  # $0.10 × 5 × 10 ÷ 0.01 = 500 Lucas
    assert est == 500
    assert acct.available(NOW) == before_avail   # holds nothing
    assert len(acct.ledger) == before_entries    # estimate itself writes nothing


# ── reserve ─────────────────────────────────────────────────────────────────────
def test_reserve_blocks_when_insufficient():
    acct = Account("org1")
    acct.grant_license("lic", 100, CYCLE_END)
    with pytest.raises(InsufficientCredits):
        acct.reserve("job1", "video_segment", "brand1", 101,
                     model_id="m", model_version="v1", now=NOW)


def test_reserve_is_idempotent_by_job_id():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    r1 = acct.reserve("job1", "a", "b", 100, model_id="m", model_version="v1", now=NOW)
    r2 = acct.reserve("job1", "a", "b", 100, model_id="m", model_version="v1", now=NOW)
    assert r1 is r2
    assert acct.reserved_total() == 100  # not doubled


# ── commit: idempotent, +10% tolerance, FIFO ────────────────────────────────────
def test_commit_idempotent_by_step():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "shot1", 100, now=NOW)
    acct.commit("job1", "shot1", 100, now=NOW)  # replay
    res = acct.reservations["job1"]
    assert res.lucas_committed == 100  # counted once


def test_commit_consumes_license_before_purchased_fifo():
    acct = Account("org1")
    acct.grant_license("lic", 300, CYCLE_END)
    acct.add_purchased("pack-old", 300, usd_paid=3.0)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "s1", 400, now=NOW)  # 300 from license, 100 from purchased
    lic = next(l for l in acct.lots if l.kind is LotKind.LICENSE)
    pack = next(l for l in acct.lots if l.kind is LotKind.PURCHASED)
    assert lic.remaining == 0
    assert pack.remaining == 200


def test_commit_within_10pct_tolerance_not_flagged():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 100, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "s1", 110, now=NOW)  # exactly +10%
    assert acct.ledger[-1]["flagged_over_tolerance"] is False


def test_commit_beyond_tolerance_is_flagged():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 100, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "s1", 120, now=NOW)  # +20%
    assert acct.ledger[-1]["flagged_over_tolerance"] is True


# ── release ─────────────────────────────────────────────────────────────────────
def test_release_settled_when_committed():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "s1", 300, now=NOW)
    assert acct.release("job1") is ReservationStatus.SETTLED
    assert acct.reserved_total() == 0  # unspent 200 freed


def test_release_released_when_no_commits():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1", now=NOW)
    assert acct.release("job1") is ReservationStatus.RELEASED


def test_failed_shot_returns_balance_on_release():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1", now=NOW)
    acct.commit("job1", "s1", 200, now=NOW)  # s2 "fails" → never commits
    acct.release("job1")
    assert acct.available(NOW) == 800  # only the 200 real usage was charged


# ── expiry ──────────────────────────────────────────────────────────────────────
def test_license_expires_at_cycle_end_purchased_does_not():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.add_purchased("pack", 1_000, usd_paid=10.0)
    after = CYCLE_END + timedelta(days=1)
    assert acct.license_balance(after) == 0        # license expired
    assert acct.purchased_balance(after) == 1_000  # purchased survives


def test_orphaned_reservation_auto_releases():
    acct = Account("org1")
    acct.grant_license("lic", 1_000, CYCLE_END)
    acct.reserve("job1", "a", "b", 500, model_id="m", model_version="v1",
                 now=NOW, expected_end_at=NOW + timedelta(minutes=30))
    swept = acct.sweep_expired(now=NOW + timedelta(minutes=31))
    assert swept == 1
    assert acct.reservations["job1"].status is ReservationStatus.EXPIRED
    assert acct.available(NOW + timedelta(minutes=31)) == 1_000
