"""Join the vehicle-photo and session/ride branches, which both started from 0004.

Revision ID: 0008_merge_heads
Revises: 0005_vehicle_car_photo, 0007_seed_stations
"""

revision = "0008_merge_heads"
down_revision = ("0005_vehicle_car_photo", "0007_seed_stations")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
