"""Add in-app notifications for booking and ride events.

Revision ID: 0009_notification
Revises: 0008_merge_heads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0009_notification"
down_revision = "0008_merge_heads"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification",
        sa.Column(
            "id_notification", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=False,
        ),
        sa.Column("id_user", mysql.BIGINT(unsigned=True), nullable=False),  # recipient
        sa.Column(
            "type",
            mysql.ENUM(
                "booking_requested", "booking_accepted", "booking_rejected",
                "booking_cancelled", "ride_cancelled", "ride_modified",
            ),
            nullable=False,
        ),
        sa.Column("id_ride", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("id_booking", mysql.BIGINT(unsigned=True)),
        sa.Column("message", sa.String(255), nullable=False),
        sa.Column(
            "is_read", mysql.TINYINT(display_width=1),
            nullable=False, server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at", mysql.DATETIME(fsp=3), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(3)"),
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index(
        "idx_notification_user", "notification", ["id_user", "is_read", "created_at"]
    )


def downgrade():
    op.drop_table("notification")
