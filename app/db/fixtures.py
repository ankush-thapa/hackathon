"""Idempotent user fixtures (plain SQL), loaded from fixtures/users.json.

Used for dev startup seeding, tests, and manually: `python -m app.db.fixtures`.
A fixture user is skipped if its id, email, phone or user_name already exists.
"""
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password

FIXTURES_FILE = Path(__file__).resolve().parents[2] / "fixtures" / "users.json"

_EXISTS = text(
    "SELECT 1 FROM `user` WHERE id_user = :id_user OR (email IS NOT NULL AND email = :email) "
    "OR (phone_number IS NOT NULL AND phone_number = :phone_number) "
    "OR (user_name IS NOT NULL AND user_name = :user_name) LIMIT 1"
)
_INSERT_USER = text(
    "INSERT INTO `user` (id_user, user_name, email, phone_number, password_hash) "
    "VALUES (:id_user, :user_name, :email, :phone_number, :password_hash)"
)
_MARK_COMPLETED = text("UPDATE `user` SET is_profile_completed = 1 WHERE id_user = :id_user")
_PROFILE_EXISTS = text("SELECT 1 FROM user_profile WHERE id_user = :id_user LIMIT 1")
_INSERT_PROFILE = text(
    "INSERT INTO user_profile (id_user, full_name, photo_url, about, date_of_birth, gender) "
    "VALUES (:id_user, :full_name, :photo_url, :about, :date_of_birth, :gender)"
)


def load_user_fixtures(db: Session, path: Path = FIXTURES_FILE) -> int:
    """Insert missing fixture users and profiles. Returns the number of users created."""
    data = json.loads(path.read_text())
    pw_hash = None  # hashed lazily, once, only if something needs inserting
    created = 0
    for u in data["users"]:
        uid = int(u["idUser"])
        params = {
            "id_user": uid,
            "user_name": u.get("userName"),
            "email": u.get("email"),
            "phone_number": u.get("phoneNumber"),
        }
        if not db.execute(_EXISTS, params).first():
            pw_hash = pw_hash or hash_password(data["defaultPassword"])
            db.execute(_INSERT_USER, {**params, "password_hash": pw_hash})
            created += 1
        p = u.get("profile")
        user_row_exists = db.execute(text("SELECT 1 FROM `user` WHERE id_user = :i"), {"i": uid}).first()
        if p and user_row_exists and not db.execute(_PROFILE_EXISTS, {"id_user": uid}).first():
            db.execute(
                _INSERT_PROFILE,
                {
                    "id_user": uid,
                    "full_name": p["fullName"],
                    "photo_url": p.get("photoUrl"),
                    "about": p.get("about"),
                    "date_of_birth": p.get("dateOfBirth"),
                    "gender": p.get("gender"),
                },
            )
            db.execute(_MARK_COMPLETED, {"id_user": uid})
    db.commit()
    return created


if __name__ == "__main__":
    from app.db.session import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        print(f"created {load_user_fixtures(session)} user(s)")
