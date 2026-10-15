"""Keep registration without a username compatible with the migrated schema.

Revision ID: 0003_optional_user_name
Revises: 0002_vehicle_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_optional_user_name"
down_revision = "0002_vehicle_schema"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "user", "user_name", existing_type=sa.String(50), nullable=True,
    )


def downgrade():
    count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM user WHERE user_name IS NULL")
    ).scalar_one()
    if count:
        raise RuntimeError(
            "Assign usernames to registered users before making user_name required."
        )
    op.alter_column(
        "user", "user_name", existing_type=sa.String(50), nullable=False,
    )
