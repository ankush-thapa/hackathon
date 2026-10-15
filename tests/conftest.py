import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.fixtures import load_user_fixtures
from app.db.session import Base


@pytest.fixture
def seeded_db():
    """In-memory SQLite session preloaded with fixtures/users.json."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        load_user_fixtures(session)
        yield session
