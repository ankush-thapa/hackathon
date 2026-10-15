"""Add refresh-token sessions for JWT auth.

Revision ID: 0004_user_session
Revises: 0003_optional_user_name
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0004_user_session"
down_revision = "0003_optional_user_name"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_session",
        sa.Column(
            "id_session", mysql.BIGINT(unsigned=True),
            primary_key=True, autoincrement=False,
        ),
        sa.Column("id_user", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("refresh_token_hash", sa.CHAR(64), nullable=False),
        sa.Column("expires_at", mysql.DATETIME(fsp=3), nullable=False),
        sa.Column("revoked_at", mysql.DATETIME(fsp=3)),
        sa.Column(
            "created_at", mysql.DATETIME(fsp=3), nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP(3)"),
        ),
        sa.UniqueConstraint(
            "refresh_token_hash", name="uk_session_refresh_token"
        ),
        sa.ForeignKeyConstraint(
            ["id_user"], ["user.id_user"], name="fk_user_session_user"
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
    )
    op.create_index("idx_session_user", "user_session", ["id_user"])


def downgrade():
    op.drop_table("user_session")
