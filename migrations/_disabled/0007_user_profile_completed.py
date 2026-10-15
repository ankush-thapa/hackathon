"""Flag users who have completed their profile, so login can route new users to profile setup.

Revision ID: 0007_user_profile_completed
Revises: 0006_ride_schema
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0007_user_profile_completed"
down_revision = "0006_ride_schema"
branch_labels = None
depends_on = None


def upgrade():
    # Skip the ADD if the column is already there: a local DB may have it from this migration's
    # earlier draft (numbered 0005 before upstream's 0005/0006 landed).
    columns = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("user")}
    if "is_profile_completed" not in columns:
        op.add_column(
            "user",
            sa.Column(
                "is_profile_completed", mysql.TINYINT(display_width=1),
                nullable=False, server_default=sa.text("0"),
            ),
        )
    # Existing users who already saved a profile count as completed.
    op.execute(
        "UPDATE `user` u JOIN user_profile p ON p.id_user = u.id_user SET u.is_profile_completed = 1"
    )


def downgrade():
    op.drop_column("user", "is_profile_completed")
