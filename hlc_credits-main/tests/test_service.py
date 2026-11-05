"""Service-facade tests — the 4-call contract + Gate 1 ($100/org video cap)."""
from datetime import datetime, timezone

import pytest

from lucas.registry import UnpricedModel
from lucas.service import (
    VIDEO_CAP_LUCAS,
    BillingService,
    FreeActionBilled,
    VideoCapExceeded,
)

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=timezone.utc)
CYCLE_END = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)


def _funded(cap_headroom_lucas=1_000_000):
    """A service whose org has plenty of balance so the video cap, not balance, is what bites."""
    svc = BillingService()
    svc.account("org1").grant_license("lic", cap_headroom_lucas, CYCLE_END)
    return svc


# ── estimate is free, priced from the registry ───────────────────────────────
def test_estimate_prices_from_registry_and_holds_nothing():
    svc = _funded()
    before = svc.balance("org1", NOW)
    est = svc.estimate("org1", "minimax-h3-max", 8)  # $0.04×8×5÷0.01 = 160
    assert est == 160
    assert svc.balance("org1", NOW) == before  # free


def test_estimate_refuses_gated_model():
    svc = _funded()
    with pytest.raises(UnpricedModel):
        svc.estimate("org1", "flux-3", 8)


# ── full estimate → reserve → commit → release ───────────────────────────────
def test_reserve_commit_release_roundtrip():
    svc = _funded()
    svc.reserve("org1", "job1", "video_segment", "brand1", "minimax-h3-max", 8, now=NOW)
    # reserved 160; commit real 8s again = 160
    svc.commit("org1", "job1", "v1:video:1", "minimax-h3-max", 8, now=NOW)
    status = svc.release("org1", "job1")
    assert status.value == "settled"


def test_reserve_freezes_model_version():
    svc = _funded()
    res = svc.reserve("org1", "job1", "video_segment", "brand1", "minimax-h3-max", 8, now=NOW)
    assert res.model_version == "1"  # registry version frozen onto the reservation


# ── free actions must never bill ─────────────────────────────────────────────
def test_free_action_refused_at_reserve():
    svc = _funded()
    with pytest.raises(FreeActionBilled):
        svc.reserve("org1", "job1", "video_scripts_only", "brand1", "minimax-h3-max", 8, now=NOW)


# ── Gate 1: $100/org video cap ───────────────────────────────────────────────
def test_video_cap_blocks_beyond_100_dollars():
    svc = _funded()
    # cap is 10,000 Lucas. minimax 15s = $0.04×15×5÷0.01 = 300 Lucas per reserve.
    # 33 reserves = 9,900 (ok); the 34th (=10,200) must trip the cap.
    for i in range(33):
        svc.reserve("org1", f"job{i}", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)
    with pytest.raises(VideoCapExceeded):
        svc.reserve("org1", "job33", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)


def test_video_cap_is_per_org_not_global():
    svc = _funded()
    svc.account("org2").grant_license("lic2", 1_000_000, CYCLE_END)
    # org1 near the cap
    for i in range(33):
        svc.reserve("org1", f"job{i}", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)
    # org2 is unaffected — its own budget is clean
    r = svc.reserve("org2", "jobA", "video_segment", "brandX", "minimax-h3-max", 15, now=NOW)
    assert r.lucas_reserved == 300


def test_non_video_action_ignores_video_cap():
    svc = _funded()
    # burn video budget to just under the cap
    for i in range(33):
        svc.reserve("org1", f"job{i}", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)
    # an image action is not subject to the video cap
    r = svc.reserve("org1", "img1", "image_single", "brand1", "nano-banana-2", 1, now=NOW)
    assert r.lucas_reserved == 34


def test_released_video_frees_cap_headroom():
    svc = _funded()
    for i in range(33):
        svc.reserve("org1", f"job{i}", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)
    # release one WITHOUT committing → its 300 Lucas returns to headroom
    svc.release("org1", "job0", reason="cancelled")
    r = svc.reserve("org1", "job33", "video_segment", "brand1", "minimax-h3-max", 15, now=NOW)
    assert r.lucas_reserved == 300  # now fits under the cap again


def test_cap_constant_is_100_dollars():
    assert VIDEO_CAP_LUCAS == 10_000
