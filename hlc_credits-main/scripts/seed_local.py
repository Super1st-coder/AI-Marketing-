"""Local dev helper — build the SQLite DB, seed the price registry, and fund two demo orgs
so you can exercise the API via /docs without Postgres.

    python -m scripts.seed_local     (run from the hlc_credits root, uses .env -> local.db)

Then start the server and open the Swagger UI:
    .venv/Scripts/uvicorn app.main:app --reload
    -> http://127.0.0.1:8000/docs   (click Authorize, key = LUCA_CREDITS_INTERNAL_KEY from .env)
"""
from datetime import datetime, timedelta, timezone

from app.database import Base, SessionLocal, engine
from app.repository import CreditsRepository
from app.seed import seed_registry


def main() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        n = seed_registry(db)
        repo = CreditsRepository(db)
        cycle_end = datetime.now(timezone.utc) + timedelta(days=30)
        # demo-org: a full $750 license (37,500 Lucas) for exploring reserve/commit/release.
        repo.grant_license_for_price("demo-org", 750, cycle_end)
        # alert-org: a small grant so a couple of commits cross the 50/75/90% usage alerts.
        repo.grant_license("alert-org", 1_000, cycle_end)
        print(f"Seeded local.db: {n} registry rows.")
        print("  demo-org  -> 37,500 Lucas (license $750)")
        print("  alert-org -> 1,000 Lucas (commit ~600 then ~900 to trip usage alerts)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
