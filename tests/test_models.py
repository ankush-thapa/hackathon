import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.ids import new_id
from app.db.session import Base
from app.models import DocType, Gender, User, UserDocument, UserProfile, UserStatus


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


def make_user(**kw):
    kw.setdefault("user_name", "jane")
    return User(id_user=new_id(), password_hash="h", **kw)


def test_defaults_and_lowercase_user_name(db):
    u = make_user(user_name="  JaNe ")
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.user_name == "jane"
    assert u.status is UserStatus.active
    assert u.created_at and u.updated_at
    assert u.email is None and u.phone_number is None and u.last_active is None


def test_user_name_is_optional(db):
    for _ in range(2):  # multiple NULLs allowed under the unique key
        db.add(make_user(user_name=None))
    db.commit()


def test_unique_constraints(db):
    db.add(make_user(email="a@b.co", phone_number="+971500000000"))
    db.commit()
    for kw in ({"user_name": "jane"}, {"user_name": "x", "email": "a@b.co"}, {"user_name": "y", "phone_number": "+971500000000"}):
        db.add(make_user(**kw))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_profile_and_documents_relationships(db):
    u = make_user()
    u.profile = UserProfile(full_name="Jane Doe", gender=Gender.prefer_not_to_say)
    u.documents.append(
        UserDocument(id_user_doc=new_id(), doc_type=DocType.driving_license, path="k/1", doc_number="DL1")
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    assert u.profile.full_name == "Jane Doe"
    assert u.documents[0].is_active is True
    assert u.documents[0].user is u


def test_snowflake_ids_unique_and_increasing():
    ids = [new_id() for _ in range(5000)]
    assert len(set(ids)) == 5000 and ids == sorted(ids)
    assert ids[-1] < 2**63
