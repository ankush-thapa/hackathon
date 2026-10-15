"""Create user tables or migrate the original id/name demo schema.

Legacy accounts retain their IDs and display names. They are blocked with an
unusable password marker until a password reset supplies a real password hash.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = "0001_user_schema"
down_revision = None
branch_labels = None
depends_on = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}
EXPECTED_COLUMNS = {
    "user": {
        "id_user", "user_name", "email", "phone_number", "password_hash",
        "status", "created_at", "updated_at", "last_active",
    },
    "user_profile": {
        "id_user", "full_name", "photo_url", "about", "date_of_birth",
        "gender", "created_at", "updated_at",
    },
    "user_documents": {
        "id_user_doc", "id_user", "doc_type", "path", "doc_number",
        "is_active", "created_at", "updated_at",
    },
}


def _timestamps():
    return [
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
    ]


def _create_user():
    op.create_table(
        "user",
        sa.Column("id_user", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=False),
        sa.Column("user_name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone_number", sa.String(20)),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "status", mysql.ENUM("active", "blocked", "deleted"),
            nullable=False, server_default="active",
        ),
        *_timestamps(),
        sa.Column("last_active", mysql.DATETIME(fsp=3)),
        sa.UniqueConstraint("user_name", name="uk_user_user_name"),
        sa.UniqueConstraint("email", name="uk_user_email"),
        sa.UniqueConstraint("phone_number", name="uk_user_phone_number"),
        **TABLE_OPTIONS,
    )


def _migrate_legacy_user(bind):
    # Read names before normalizing them so the profile keeps the display name.
    legacy_users = bind.execute(sa.text("SELECT id, name FROM user")).mappings().all()
    for user in legacy_users:
        if user["id"] < 0 or not user["name"] or len(user["name"]) > 50:
            raise RuntimeError(
                "Legacy users require nonnegative IDs and names of 1-50 characters. "
                "Resolve these rows before retrying; no schema changes were made."
            )
    duplicates = bind.execute(sa.text(
        "SELECT LOWER(CONVERT(name USING utf8mb4)) COLLATE utf8mb4_0900_ai_ci "
        "AS normalized_name FROM user GROUP BY normalized_name HAVING COUNT(*) > 1"
    )).first()
    if duplicates:
        raise RuntimeError(
            "Legacy names collide under the new unique username collation. "
            "Resolve duplicate names before retrying; no schema changes were made."
        )

    for index in sa.inspect(bind).get_indexes("user"):
        if index["name"] == "ix_user_id":
            op.drop_index("ix_user_id", table_name="user")
    op.alter_column(
        "user", "id", new_column_name="id_user",
        existing_type=mysql.INTEGER(), type_=mysql.BIGINT(unsigned=True),
        existing_nullable=False, autoincrement=False,
    )
    op.alter_column(
        "user", "name", new_column_name="user_name",
        existing_type=sa.String(255), type_=sa.String(50), existing_nullable=False,
    )
    op.add_column("user", sa.Column("email", sa.String(255)))
    op.add_column("user", sa.Column("phone_number", sa.String(20)))
    op.add_column("user", sa.Column("password_hash", sa.String(255), nullable=True))
    op.add_column("user", sa.Column(
        "status", mysql.ENUM("active", "blocked", "deleted"),
        nullable=False, server_default="active",
    ))
    for column in _timestamps():
        op.add_column("user", column)
    op.add_column("user", sa.Column("last_active", mysql.DATETIME(fsp=3)))
    bind.execute(sa.text(
        "UPDATE user SET user_name = LOWER(user_name), "
        "password_hash = '!password-reset-required', status = 'blocked'"
    ))
    op.alter_column(
        "user", "password_hash", existing_type=sa.String(255), nullable=False,
    )
    op.execute(sa.text(
        "ALTER TABLE user ENGINE=InnoDB, "
        "CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    ))
    for column in ("user_name", "email", "phone_number"):
        op.create_unique_constraint(f"uk_user_{column}", "user", [column])
    return legacy_users


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "mysql":
        raise RuntimeError("The user schema migration requires MySQL 8.")
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table in tables & EXPECTED_COLUMNS.keys():
        columns = {column["name"] for column in inspector.get_columns(table)}
        if table == "user" and columns == {"id", "name"}:
            continue
        if columns != EXPECTED_COLUMNS[table]:
            raise RuntimeError(f"Unexpected {table} schema; inspect it before migrating.")

    legacy_users = []
    if "user" not in tables:
        _create_user()
    elif {column["name"] for column in inspector.get_columns("user")} == {"id", "name"}:
        legacy_users = _migrate_legacy_user(bind)

    if "user_profile" not in tables:
        op.create_table(
            "user_profile",
            sa.Column("id_user", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=False),
            sa.Column("full_name", sa.String(100), nullable=False),
            sa.Column("photo_url", sa.String(500)),
            sa.Column("about", sa.String(500)),
            sa.Column("date_of_birth", sa.Date()),
            sa.Column("gender", mysql.ENUM("male", "female", "other", "prefer_not_to_say")),
            *_timestamps(),
            sa.ForeignKeyConstraint(["id_user"], ["user.id_user"], name="fk_user_profile_user"),
            **TABLE_OPTIONS,
        )
    if legacy_users:
        profiles = sa.table("user_profile", sa.column("id_user"), sa.column("full_name"))
        op.bulk_insert(profiles, [
            {"id_user": user["id"], "full_name": user["name"]}
            for user in legacy_users
        ])
    if "user_documents" not in tables:
        op.create_table(
            "user_documents",
            sa.Column("id_user_doc", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=False),
            sa.Column("id_user", mysql.BIGINT(unsigned=True), nullable=False),
            sa.Column(
                "doc_type", mysql.ENUM("driving_license", "id_proof", "vehicle_rc", "insurance"),
                nullable=False,
            ),
            sa.Column("path", sa.String(500), nullable=False),
            sa.Column("doc_number", sa.String(50), nullable=False),
            sa.Column("is_active", mysql.TINYINT(display_width=1), nullable=False, server_default=sa.text("1")),
            *_timestamps(),
            sa.ForeignKeyConstraint(["id_user"], ["user.id_user"], name="fk_user_documents_user"),
            **TABLE_OPTIONS,
        )
        op.create_index("idx_user_documents_user_type", "user_documents", ["id_user", "doc_type", "is_active"])
        op.create_index("idx_user_documents_doc_number", "user_documents", ["doc_type", "doc_number"])


def downgrade():
    raise RuntimeError(
        "Automatic downgrade would discard profile and document data. "
        "Restore a database backup or write a deliberate reverse migration."
    )
