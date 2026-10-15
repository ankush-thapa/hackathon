"""Add the ride_created notification type.

Revision ID: 0010_notification_ride_created
Revises: 0009_notification
"""
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0010_notification_ride_created"
down_revision = "0009_notification"
branch_labels = None
depends_on = None

OLD_TYPES = (
    "booking_requested", "booking_accepted", "booking_rejected",
    "booking_cancelled", "ride_cancelled", "ride_modified",
)
NEW_TYPES = OLD_TYPES + ("ride_created",)


def upgrade():
    op.alter_column(
        "notification", "type",
        existing_type=mysql.ENUM(*OLD_TYPES), type_=mysql.ENUM(*NEW_TYPES), existing_nullable=False,
    )


def downgrade():
    op.execute("DELETE FROM notification WHERE type = 'ride_created'")  # the old enum cannot hold them
    op.alter_column(
        "notification", "type",
        existing_type=mysql.ENUM(*NEW_TYPES), type_=mysql.ENUM(*OLD_TYPES), existing_nullable=False,
    )
