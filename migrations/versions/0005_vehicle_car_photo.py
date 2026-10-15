"""Add vehicle.car_photo (photo URL) and allow 'car' in vehicle.vehicle_type (the new default).

Revision ID: 0005_vehicle_car_photo
Revises: 0004_user_session
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0005_vehicle_car_photo"
down_revision = "0004_user_session"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("vehicle", sa.Column("car_photo", sa.String(500), nullable=True))  # URL from POST /v1/media/upload
    op.alter_column(
        "vehicle", "vehicle_type",
        existing_type=mysql.ENUM("hatchback", "sedan", "suv", "bike"),
        type_=mysql.ENUM("car", "hatchback", "sedan", "suv", "bike"),
        existing_nullable=False,
        server_default="car",
    )


def downgrade():
    # 'car' has no equivalent in the old enum; map it to the closest generic type first.
    op.execute("UPDATE vehicle SET vehicle_type = 'sedan' WHERE vehicle_type = 'car'")
    op.alter_column(
        "vehicle", "vehicle_type",
        existing_type=mysql.ENUM("car", "hatchback", "sedan", "suv", "bike"),
        type_=mysql.ENUM("hatchback", "sedan", "suv", "bike"),
        existing_nullable=False,
        server_default=None,
    )
    op.drop_column("vehicle", "car_photo")
