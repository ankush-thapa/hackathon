"""Merge the session/ride/station branch with the vehicle car-photo branch.

Revision ID: 0008_merge_heads
Revises: 0007_seed_stations, 0005_vehicle_car_photo
"""

revision = "0008_merge_heads"
down_revision = ("0007_seed_stations", "0005_vehicle_car_photo")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
