"""Add vehicles owned by users.

Revision ID: 0002_vehicle_schema
Revises: 0001_user_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0002_vehicle_schema"
down_revision = "0001_user_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vehicle",
        sa.Column(
            "id_vehicle", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=False,
        ),
        sa.Column("id_user", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("make", sa.String(50), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("color", sa.String(30), nullable=False),
        sa.Column("registration_number", sa.String(20), nullable=False),
        sa.Column("seat_capacity", mysql.TINYINT(unsigned=True), nullable=False),
        sa.Column(
            "vehicle_type", mysql.ENUM("hatchback", "sedan", "suv", "bike"),
            nullable=False,
        ),
        sa.Column(
            "is_default", mysql.TINYINT(display_width=1),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "status", mysql.ENUM("active", "inactive", "deleted"),
            nullable=False, server_default="active",
        ),
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
        sa.UniqueConstraint(
            "registration_number", name="uk_vehicle_registration_number"
        ),
        sa.ForeignKeyConstraint(
            ["id_user"], ["user.id_user"], name="fk_vehicle_user"
        ),
        sa.CheckConstraint(
            "seat_capacity BETWEEN 1 AND 8", name="chk_vehicle_seat_capacity"
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_vehicle_user_status", "vehicle", ["id_user", "status"])


def downgrade():
    op.drop_table("vehicle")
