from sqlalchemy import text

from app.core.security import verify_password
from app.db.fixtures import load_user_fixtures


def test_fixture_users_and_profiles_loaded(seeded_db):
    users = seeded_db.execute(text("SELECT COUNT(*) FROM `user`")).scalar()
    profiles = seeded_db.execute(text("SELECT COUNT(*) FROM user_profile")).scalar()
    assert users == profiles == 8
    row = seeded_db.execute(text("SELECT password_hash FROM `user` WHERE email = 'amar@gmail.com'")).one()
    assert verify_password("Password1", row.password_hash)


def test_loading_twice_is_idempotent(seeded_db):
    assert load_user_fixtures(seeded_db) == 0
    assert seeded_db.execute(text("SELECT COUNT(*) FROM `user`")).scalar() == 8


def test_existing_email_is_not_duplicated(seeded_db):
    seeded_db.execute(text("DELETE FROM user_profile WHERE id_user = 236357292134498304"))
    seeded_db.execute(text("UPDATE `user` SET id_user = 1 WHERE id_user = 236357292134498304"))
    seeded_db.commit()
    assert load_user_fixtures(seeded_db) == 0  # same email under another id: skipped, not a unique-key error
