"""Price drift reconciliation (Marco §4(2), 2026-09-09).

A weekly job compares the REAL observed provider cost/unit against the registry price and
alerts when they deviate by more than the threshold (default 10%). This is what catches the
"ADK under-costs by 2.5x" and the "H3 Max launch-promo ends, list price jumps" problems.

The observed cost/unit comes from LangFuse traces in production — that feed is the integration
point (Luis is wiring per-model prices + traces, HLC-9). This function takes the observations as
input so the drift LOGIC is testable and ready now, independent of the LangFuse plumbing.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models

DEFAULT_THRESHOLD = 0.10  # >10% deviation → alert


def reconcile(db: Session, observed_cost_usd: dict[str, float],
              threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """Compare observed provider cost/unit to the current registry price for each model.

    `observed_cost_usd` maps model_id -> real USD per unit (from LangFuse). Returns one alert
    per model whose deviation exceeds `threshold`, plus an alert for any observed model that has
    no current registry row (an unpriced model is being used — it should be registered or dropped).
    Gated rows (no confirmed price) are reported separately as needing a price, not as drift.
    """
    alerts: list[dict] = []
    current = {r.model_id: r for r in db.scalars(select(models.ModelRegistryRow).where(
        models.ModelRegistryRow.is_current.is_(True)))}

    for model_id, observed in observed_cost_usd.items():
        row = current.get(model_id)
        if row is None:
            alerts.append({"model_id": model_id, "kind": "unregistered",
                           "observed_cost_usd": observed,
                           "message": "used but not in registry — register or drop"})
            continue
        if not row.sellable:
            alerts.append({"model_id": model_id, "kind": "gated_but_used",
                           "observed_cost_usd": observed, "registry_cost_usd": row.provider_cost_usd,
                           "message": f"gated ({row.gate_reason}) but real cost seen — needs pricing"})
            continue
        registry_cost = row.provider_cost_usd
        if registry_cost <= 0:
            continue
        deviation = abs(observed - registry_cost) / registry_cost
        if deviation > threshold:
            alerts.append({
                "model_id": model_id, "kind": "drift", "version": row.version,
                "registry_cost_usd": registry_cost, "observed_cost_usd": observed,
                "deviation_pct": round(deviation * 100, 1),
                "direction": "under-charging" if observed > registry_cost else "over-charging",
                "message": (f"{model_id} registry ${registry_cost}/unit vs observed "
                            f"${observed}/unit ({round(deviation * 100, 1)}% off)"),
            })
    return alerts


def reconcile_report(db: Session, observed_cost_usd: dict[str, float],
                     threshold: float = DEFAULT_THRESHOLD) -> dict:
    alerts = reconcile(db, observed_cost_usd, threshold)
    return {
        "threshold_pct": round(threshold * 100, 1),
        "models_checked": len(observed_cost_usd),
        "alert_count": len(alerts),
        "alerts": alerts,
    }
