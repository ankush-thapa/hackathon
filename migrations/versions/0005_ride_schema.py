"""Add stations, rides offered by drivers, and rider bookings.

Revision ID: 0005_ride_schema
Revises: 0004_user_session
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0005_ride_schema"
down_revision = "0004_user_session"
branch_labels = None
depends_on = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _timestamps():
    return [
        sa.Column(
            "created_at", mysql.DATETIME(fsp=3), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(3)"),
        ),
        sa.Column(
            "updated_at", mysql.DATETIME(fsp=3), nullable=False,
            server_default=sa.text(
                "CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"
            ),
        ),
    ]


def upgrade():
    op.create_table(
        "station",
        sa.Column(
            "id_station", mysql.INTEGER(unsigned=True),
            primary_key=True, autoincrement=True,
        ),
        sa.Column("station_name", sa.String(100), nullable=False),
        sa.Column(
            "is_active", mysql.TINYINT(display_width=1),
            nullable=False, server_default=sa.text("1"),
        ),
        sa.Column(
            "created_at", mysql.DATETIME(fsp=3), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(3)"),
        ),
        sa.UniqueConstraint("station_name", name="uk_station_name"),
        **TABLE_OPTIONS,
    )

    op.create_table(
        "ride",
        sa.Column(
            "id_ride", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=False,
        ),
        sa.Column("id_driver", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("id_vehicle", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("id_source_station", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("id_destination_station", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("departure_time", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("estimated_arrival_time", mysql.DATETIME(fsp=3)),
        sa.Column("total_seats", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column("available_seats", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column(
            "price_per_seat", sa.Numeric(10, 2),
            nullable=False, server_default=sa.text("0.00"),
        ),
        sa.Column("notes", sa.String(500)),
        sa.Column(
            "status", mysql.ENUM("open", "full", "started", "completed", "cancelled"),
            nullable=False, server_default="open",
        ),
        sa.Column("cancel_reason", sa.String(255)),
        sa.Column("cancelled_at", mysql.DATETIME(fsp=3)),
        sa.Column(
            "version", mysql.INTEGER(unsigned=True),
            nullable=False, server_default=sa.text("1"),
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["id_source_station"], ["station.id_station"], name="fk_ride_source_station"
        ),
        sa.ForeignKeyConstraint(
            ["id_destination_station"], ["station.id_station"], name="fk_ride_destination_station"
        ),
        sa.CheckConstraint(
            "id_source_station <> id_destination_station", name="chk_ride_diff_stations"
        ),
        sa.CheckConstraint("total_seats BETWEEN 1 AND 8", name="chk_ride_total_seats"),
        sa.CheckConstraint("available_seats <= total_seats", name="chk_ride_available_seats"),
        sa.CheckConstraint("price_per_seat >= 0", name="chk_ride_price"),
        **TABLE_OPTIONS,
    )
    op.create_index(
        "idx_ride_search", "ride",
        ["id_source_station", "id_destination_station", "status", "departure_time"],
    )
    op.create_index("idx_ride_driver_departure", "ride", ["id_driver", "departure_time"])
    op.create_index("idx_ride_vehicle_departure", "ride", ["id_vehicle", "departure_time"])
    op.create_index("idx_ride_status_departure", "ride", ["status", "departure_time"])

    op.create_table(
        "ride_booking",
        sa.Column(
            "id_booking", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=False,
        ),
        sa.Column("id_ride", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("id_rider", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("id_driver", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column(
            "seats_booked", mysql.TINYINT(unsigned=True),
            nullable=False, server_default=sa.text("1"),
        ),
        sa.Column("price_per_seat", sa.Numeric(10, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("rider_note", sa.String(255)),
        sa.Column(
            "status",
            mysql.ENUM(
                "requested", "accepted", "rejected",
                "cancelled_by_rider", "cancelled_by_driver",
                "expired", "completed",
            ),
            nullable=False, server_default="requested",
        ),
        sa.Column("reject_reason", sa.String(255)),
        sa.Column("cancel_reason", sa.String(255)),
        sa.Column("responded_at", mysql.DATETIME(fsp=3)),
        sa.Column("cancelled_at", mysql.DATETIME(fsp=3)),
        sa.Column(
            "version", mysql.INTEGER(unsigned=True),
            nullable=False, server_default=sa.text("1"),
        ),
        *_timestamps(),
        # 1 while active, NULL otherwise -> one active booking per rider per ride.
        sa.Column(
            "active_flag", mysql.TINYINT(),
            sa.Computed(
                "CASE WHEN status IN ('requested', 'accepted') THEN 1 END",
                persisted=True,
            ),
        ),
        sa.UniqueConstraint(
            "id_ride", "id_rider", "active_flag", name="uk_booking_one_active"
        ),
        sa.ForeignKeyConstraint(["id_ride"], ["ride.id_ride"], name="fk_booking_ride"),
        sa.CheckConstraint("seats_booked BETWEEN 1 AND 8", name="chk_booking_seats"),
        sa.CheckConstraint("total_amount >= 0", name="chk_booking_amount"),
        **TABLE_OPTIONS,
    )
    op.create_index("idx_booking_ride_status", "ride_booking", ["id_ride", "status"])
    op.create_index("idx_booking_rider_created", "ride_booking", ["id_rider", "created_at"])
    op.create_index(
        "idx_booking_driver_status", "ride_booking", ["id_driver", "status", "created_at"]
    )


def downgrade():
    op.drop_table("ride_booking")
    op.drop_table("ride")
    op.drop_table("station")
