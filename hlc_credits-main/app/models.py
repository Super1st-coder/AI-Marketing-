"""LucaCredit ORM models — the durable ledger.

Maps the domain (org=wallet · brand=license · Lucas=fuel) to tables:

    organizations      one wallet per paying company
    lots               license (monthly, expires) / purchased (never) / refund_grant
    reservations       one per job_id (idempotency key) — holds budget, tracks commits
    reservation_steps  one per (job_id, step_id) — the idempotent commit records
    ledger_entries     append-only audit of every grant/reserve/commit/release
    model_registry     the versioned price table (platform pricing authority)

Idempotency is enforced in the schema, not just in code: reservations.job_id is the PK,
and reservation_steps has a UNIQUE(job_id, step_id). A duplicate reserve/commit hits the
constraint even under concurrency, so a retried request can never double-charge.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(TimestampMixin, Base):
    """The wallet root — one paying company. Lots and reservations hang off it."""
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # external org id
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Lot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A grant of Lucas. LICENSE lots expire at cycle_end; PURCHASED/REFUND_GRANT never do.
    Consumption is FIFO: license first, then purchased oldest-first, then refund grants."""
    __tablename__ = "lots"

    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id"),
                                        index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # LotKind value
    granted: Mapped[int] = mapped_column(Integer, nullable=False)
    consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usd_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class Reservation(TimestampMixin, Base):
    """One per job. job_id IS the primary key → reserve is idempotent by construction."""
    __tablename__ = "reservations"

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id"),
                                        index=True, nullable=False)
    action_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    brand_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    lucas_reserved: Mapped[int] = mapped_column(Integer, nullable=False)
    lucas_committed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)  # frozen at reserve
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active", index=True)
    expected_end_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True),
                                                                nullable=True)

    steps: Mapped[list["ReservationStep"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan")


class ReservationStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One committed step. UNIQUE(job_id, step_id) makes commit idempotent per step."""
    __tablename__ = "reservation_steps"
    __table_args__ = (UniqueConstraint("job_id", "step_id", name="uq_step_per_job"),)

    job_id: Mapped[str] = mapped_column(String(128), ForeignKey("reservations.job_id"),
                                        index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    lucas: Mapped[int] = mapped_column(Integer, nullable=False)
    flagged_over_tolerance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reservation: Mapped["Reservation"] = relationship(back_populates="steps")


class LedgerEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only audit. Positive lucas = credit (grant/release), negative = debit."""
    __tablename__ = "ledger_entries"

    org_id: Mapped[str] = mapped_column(String(64), ForeignKey("organizations.id"),
                                        index=True, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    lucas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    job_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    step_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ModelRegistryRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Versioned price table — the platform pricing authority (Marco 2026-09-09).

    A price EDIT inserts a NEW row (model_id, version+1) and flips is_current, so in-flight
    jobs keep charging against the frozen version they reserved. Gated rows (sellable=False)
    refuse to price until a real cost is confirmed (FLUX 3, Seedance 2.5, etc. — HLC-9)."""
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("model_id", "version", name="uq_model_version"),)

    model_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    max_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sellable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gate_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    edited_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
