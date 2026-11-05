"""Seed / sync the model_registry table from the code registry (lucas/registry.py).

V1 prices at runtime from the code registry (that IS the reference-prototype parity suite).
This seeds those same prices into the DB model_registry table so the versioned, edit-without-
deploy, and weekly drift-reconciliation requirements (Marco 2026-09-09, HLC-2/HLC-9) have their
durable home. A price EDIT later becomes: insert a new (model_id, version) row + flip is_current,
and switch the repository to read the current row — the table is already shaped for it.

Idempotent: re-running upserts the current row per model_id without duplicating versions.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from lucas import registry


def seed_registry(db: Session, edited_by: str = "seed") -> int:
    """Insert/update the current row for every model in the code registry. Returns rows written."""
    written = 0
    for model_id, row in registry._ROWS.items():
        existing = db.scalar(
            select(models.ModelRegistryRow).where(
                models.ModelRegistryRow.model_id == model_id,
                models.ModelRegistryRow.version == row.version,
                models.ModelRegistryRow.is_current.is_(True)))
        if existing is not None:
            existing.provider_cost_usd = row.provider_cost_usd
            existing.unit = row.unit.value
            existing.multiplier = row.multiplier
            existing.max_seconds = row.max_seconds
            existing.sellable = row.sellable
            existing.gate_reason = row.gate_reason or None
            existing.verified_at = row.verified_at or None
        else:
            # a new version supersedes prior current rows for this model
            for prior in db.scalars(select(models.ModelRegistryRow).where(
                    models.ModelRegistryRow.model_id == model_id,
                    models.ModelRegistryRow.is_current.is_(True))):
                prior.is_current = False
            db.add(models.ModelRegistryRow(
                model_id=model_id, version=row.version,
                provider_cost_usd=row.provider_cost_usd, unit=row.unit.value,
                multiplier=row.multiplier, max_seconds=row.max_seconds,
                sellable=row.sellable, gate_reason=row.gate_reason or None,
                verified_at=row.verified_at or None, is_current=True, edited_by=edited_by))
        written += 1
    db.commit()
    return written


if __name__ == "__main__":  # `python -m app.seed` after migrations
    from app.database import SessionLocal
    with SessionLocal() as _db:
        n = seed_registry(_db)
        print(f"seeded/updated {n} registry rows")
