"""Store a hash of each session's current refresh token.

Revision ID: 0005_session_refresh_token
Revises: 0004_user_session
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_session_refresh_token"
down_revision = "0004_user_session"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable: sessions created before this revision have no refresh token.
    op.add_column(
        "user_session", sa.Column("refresh_token_hash", sa.String(64), nullable=True),
    )


def downgrade():
    op.drop_column("user_session", "refresh_token_hash")
