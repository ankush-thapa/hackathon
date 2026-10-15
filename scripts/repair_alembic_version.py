"""Re-sync alembic's version record with what the database actually contains.

Use when `alembic upgrade head` fails with "Duplicate column" / "Table already exists" or
"Can't locate revision", e.g. after a local migration was renamed. It only inspects the schema
and rewrites the alembic_version table; it never changes your data or other tables.

    venv/bin/python scripts/repair_alembic_version.py      # show what it would stamp
    venv/bin/python scripts/repair_alembic_version.py --apply
    venv/bin/python -m alembic upgrade head
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.core.config import settings  # noqa: E402

engine = create_engine(settings.DATABASE_URL)
insp = inspect(engine)
tables = set(insp.get_table_names())


def has_column(table: str, column: str) -> bool:
    return table in tables and column in {c["name"] for c in insp.get_columns(table)}


with engine.connect() as conn:
    current = (
        [r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version"))]
        if "alembic_version" in tables else []
    )
    stations_seeded = "station" in tables and conn.execute(text("SELECT COUNT(*) FROM station")).scalar() > 0

if "user_session" not in tables:
    sys.exit("user_session table is missing: this database is older than 0004. Run `alembic upgrade head` normally.")

# Branch A (after 0004): refresh token -> rides -> seeded stations
a = "0004_user_session"
if has_column("user_session", "refresh_token_hash"):
    a = "0005_session_refresh_token"
    if {"ride", "ride_booking", "station"} <= tables:
        a = "0006_ride_schema"
        if stations_seeded:
            a = "0007_seed_stations"
# Branch B (after 0004): vehicle photo
b = "0005_vehicle_car_photo" if has_column("vehicle", "car_photo") else None

if a == "0007_seed_stations" and b:
    targets = ["0009_notification"] if "notification" in tables else ["0008_merge_heads"]
else:
    targets = [a] + ([b] if b else [])

print("alembic_version now :", current or "(empty)")
print("schema has          :", {
    "refresh_token_hash": has_column("user_session", "refresh_token_hash"),
    "ride tables": {"ride", "ride_booking", "station"} <= tables,
    "stations seeded": stations_seeded,
    "vehicle.car_photo": has_column("vehicle", "car_photo"),
    "notification table": "notification" in tables,
})
print("will stamp          :", targets)

if "--apply" in sys.argv:
    cfg = Config(str(ROOT / "alembic.ini"))
    command.stamp(cfg, targets, purge=True)
    print("Done. Now run: venv/bin/python -m alembic upgrade head")
else:
    print("Dry run. Re-run with --apply to write it.")
