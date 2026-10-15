"""Seed the fixed list of Gurugram stations.

Ids are explicit so they are identical in every environment. Existing rows
(by id or name) are left untouched, so re-running is safe.

Revision ID: 0007_seed_stations
Revises: 0006_ride_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_seed_stations"
down_revision = "0006_ride_schema"
branch_labels = None
depends_on = None

STATIONS = [
    "Cyber City",
    "Cyber Hub",
    "Udyog Vihar Phase 4",
    "One Horizon Center",
    "Vatika Business Park",
    "Unitech Cyber Park",
    "IMT Manesar",
    "Ambience Mall",
    "Galleria Market",
    "Sector 14 Market",
    "MG Road Metro Station",
    "Millennium City Centre",
    "Sikanderpur Metro Station",
    "IFFCO Chowk",
    "Kingdom of Dreams",
    "Gurugram Railway Station",
    "Medanta – The Medicity",
    "Fortis Memorial Research Institute",
    "DLF Phase 1",
    "South City 1",
    "Sushant Lok 1",
    "Nirvana Country",
    "Sector 56",
    "Golf Course Extension Road",
    "Palam Vihar",
    "New Gurgaon Sector",
]


def upgrade():
    op.get_bind().execute(
        sa.text("INSERT IGNORE INTO station (id_station, station_name) VALUES (:id, :name)"),
        [{"id": i, "name": name} for i, name in enumerate(STATIONS, start=1)],
    )


def downgrade():
    # Only remove stations no ride refers to; the FK blocks deleting used ones.
    op.get_bind().execute(
        sa.text(
            "DELETE FROM station WHERE station_name IN :names AND id_station NOT IN "
            "(SELECT id_source_station FROM ride UNION SELECT id_destination_station FROM ride)"
        ).bindparams(sa.bindparam("names", expanding=True)),
        {"names": STATIONS},
    )
