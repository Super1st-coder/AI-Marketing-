"""Registry tests — pricing table drives estimate/reserve; gated models refuse to price."""
import pytest

from lucas.registry import (
    UnpricedModel,
    gated_models,
    get,
    is_sellable,
    price_lucas,
    sellable_models,
)


# ── confirmed prices produce the PRD Lucas values ────────────────────────────
def test_h3max_full_job_over_clip_cap_still_prices():
    # A 24s video JOB (many shots) reserves fine — max_seconds is per-clip planner metadata,
    # NOT a pricing gate. $0.04 × 24 × 5 ÷ 0.01 = 480. (Durval reserve-bug fix 2026-09-23)
    assert price_lucas("minimax-h3-max", 24) == 480


def test_h3max_within_cap_prices():
    # $0.04/s × 8s × 5 ÷ 0.01 = 160 Lucas
    assert price_lucas("minimax-h3-max", 8) == 160


def test_nano_banana_single_image():
    # $0.067 × 1 × 5 ÷ 0.01 = 33.5 → 34
    assert price_lucas("nano-banana-2", 1) == 34


def test_veo_lite_per_second():
    # $0.05/s × 8s × 5 ÷ 0.01 = 200
    assert price_lucas("veo-3.1-lite", 8) == 200


def test_tts_per_1k_chars():
    # $0.03 × 2 (2k chars) × 5 ÷ 0.01 = 30
    assert price_lucas("tts", 2) == 30


# ── gates: unpriced/unconfirmed models refuse to price ───────────────────────
@pytest.mark.parametrize("model_id", ["flux-3", "seedance-2.5-720p", "seedance-2.5-1080p",
                                      "veo-3.1", "kling"])
def test_gated_models_refuse_to_price(model_id):
    assert not is_sellable(model_id)
    with pytest.raises(UnpricedModel):
        price_lucas(model_id, 8)


def test_gated_models_report_reasons():
    gaps = gated_models()
    assert "flux-3" in gaps and gaps["flux-3"]           # has a reason string
    assert "seedance-2.5-1080p" in gaps
    # the confirmed cheap default is NOT gated
    assert "minimax-h3-max" in sellable_models()


def test_full_video_job_prices_over_clip_length():
    # A 20s job on veo-3.1-lite (8s/clip) prices the whole job, not rejected:
    # $0.05 × 20 × 5 ÷ 0.01 = 500.
    assert price_lucas("veo-3.1-lite", 20) == 500


def test_minimax_resolution_tiers_price_differently():
    # MiniMax prices by resolution (Durval 2026-09-23). 8s each:
    assert price_lucas("minimax-h3-max-480p", 8) == 100    # $0.025 ×8×5÷0.01
    assert price_lucas("minimax-h3-max-768p", 8) == 160    # $0.04
    assert price_lucas("minimax-h3-max-1080p", 8) == 320   # $0.08
    # bare id aliases the 768p default
    assert price_lucas("minimax-h3-max", 8) == 160


def test_minimax_min_and_max_clip_metadata():
    row = get("minimax-h3-max")
    assert row.min_seconds == 5   # fal.ai minimum (Durval 2026-09-23)
    assert row.max_seconds == 15


def test_unknown_model_raises():
    with pytest.raises(KeyError):
        get("does-not-exist")
