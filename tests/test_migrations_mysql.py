"""Run with MYSQL_TEST_URL pointing to a MySQL 8 server with CREATE DATABASE access.

Every case owns and removes a randomly named database; application data is unused.
"""
import os
from pathlib import Path
import uuid

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import verify_password
from app.db.session import Base, get_db
from app.main import app
from app.models import DocType, Gender, User, UserDocument, UserProfile, Vehicle


@pytest.fixture
def mysql_database(monkeypatch):
    server_url = os.environ.get("MYSQL_TEST_URL")
    if not server_url:
        pytest.skip("Set MYSQL_TEST_URL to run isolated MySQL migration tests")
    database = "hackathon_merge_test_" + uuid.uuid4().hex
    url = make_url(server_url)
    admin = create_engine(url.set(database="mysql"), poolclass=NullPool)
    engine = None
    created = False
    try:
        with admin.begin() as connection:
            connection.exec_driver_sql(
                f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 "
                "COLLATE utf8mb4_0900_ai_ci"
            )
        created = True
        url = url.set(database=database)
        engine = create_engine(url, poolclass=NullPool)
        monkeypatch.setattr(settings, "DATABASE_URL", url.render_as_string(hide_password=False))
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        yield engine, config
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.begin() as connection:
                connection.exec_driver_sql(f"DROP DATABASE `{database}`")
        admin.dispose()


@pytest.mark.parametrize("baseline", ["empty", "legacy", "main_schema"])
def test_migration_preserves_registration_and_matches_models(mysql_database, baseline):
    engine, config = mysql_database
    if baseline == "legacy":
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE user (id INT NOT NULL AUTO_INCREMENT PRIMARY KEY, "
                "name VARCHAR(255) NOT NULL)"
            )
            connection.exec_driver_sql("CREATE INDEX ix_user_id ON user (id)")
            connection.exec_driver_sql("INSERT INTO user (id, name) VALUES (1, 'Alice')")
    elif baseline == "main_schema":
        for table in Base.metadata.sorted_tables:
            if table.name not in ("vehicle", "user_session"):
                table.create(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO user (id_user, email, phone_number, password_hash) "
                "VALUES (1, 'existing@example.com', '+971500000000', '!test')"
            )

    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        migration_context = MigrationContext.configure(connection, opts={"compare_type": True})
        assert compare_metadata(migration_context, Base.metadata) == []
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_user_session"
        if baseline == "legacy":
            row = connection.execute(text(
                "SELECT u.id_user, u.user_name, u.status, p.full_name "
                "FROM user u JOIN user_profile p ON p.id_user = u.id_user"
            )).one()
            assert tuple(row) == (1, "alice", "blocked", "Alice")
        elif baseline == "main_schema":
            row = connection.execute(text("SELECT user_name, email FROM user WHERE id_user = 1")).one()
            assert tuple(row) == (None, "existing@example.com")

    def get_test_db():
        with Session(engine) as session:
            yield session

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_db
    client = TestClient(app)
    try:
        response = client.post("/v1/auth/register", json={
            "email": "new@example.com", "phone": "+971503333333", "password": "Secret123",
        })
        assert response.status_code == 201, response.text
        user_id = response.json()["userId"]
        assert isinstance(user_id, str)
        assert client.get(f"/hello/{user_id}").json() == {"message": "Hello new@example.com"}
        assert {"id": user_id} in client.get("/users").json()
        with Session(engine) as session:
            user = session.get(User, int(user_id))
            assert user.user_name is None
            assert verify_password("Secret123", user.password_hash)
    finally:
        client.close()
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


def test_mysql_model_relationships_and_constraints(mysql_database):
    engine, config = mysql_database
    command.upgrade(config, "head")
    with Session(engine) as session:
        user = User(id_user=100, user_name=" Owner ", password_hash="!test")
        user.profile = UserProfile(full_name="Owner", gender=Gender.other)
        user.documents.append(UserDocument(
            id_user_doc=200, doc_type=DocType.id_proof, path="private/document", doc_number="DOC1",
        ))
        user.vehicles.append(Vehicle(
            id_vehicle=300, make="Example", model="Demo", color="Blue",
            registration_number=" ka 01 ab 1234 ", seat_capacity=1, vehicle_type="sedan",
        ))
        session.add(user)
        session.commit()
        session.refresh(user)
        assert user.user_name == "owner"
        assert user.profile.full_name == "Owner"
        assert user.documents[0].is_active is True
        assert user.documents[0].user is user
        vehicle = user.vehicles[0]
        assert vehicle.registration_number == "KA01AB1234"
        assert vehicle.status == "active" and vehicle.is_default == 0
        assert vehicle.user is user
        assert vehicle.created_at and vehicle.updated_at

    values = {
        "id_vehicle": 301, "id_user": 100, "make": "Example", "model": "Demo",
        "color": "Blue", "registration_number": "BOUNDARY8",
        "seat_capacity": 8, "vehicle_type": "suv",
    }
    statement = text(
        "INSERT INTO vehicle (id_vehicle, id_user, make, model, color, registration_number, "
        "seat_capacity, vehicle_type) VALUES (:id_vehicle, :id_user, :make, :model, :color, "
        ":registration_number, :seat_capacity, :vehicle_type)"
    )
    with engine.begin() as connection:
        connection.execute(statement, values)
    for changes, error_code in [
        ({"seat_capacity": 0, "registration_number": "BAD0"}, 3819),
        ({"seat_capacity": 9, "registration_number": "BAD9"}, 3819),
        ({"registration_number": "KA01AB1234"}, 1062),
        ({"id_user": 404, "registration_number": "NOOWNER"}, 1452),
    ]:
        with pytest.raises(DBAPIError) as error:
            with engine.begin() as connection:
                connection.execute(statement, values | changes | {"id_vehicle": 302})
        assert error.value.orig.errno == error_code
    assert any(
        constraint["name"] == "chk_vehicle_seat_capacity"
        for constraint in inspect(engine).get_check_constraints("vehicle")
    )
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE vehicle SET updated_at = '2000-01-01' WHERE id_vehicle = 300")
        connection.exec_driver_sql("UPDATE vehicle SET color = 'Red' WHERE id_vehicle = 300")
        assert connection.execute(text("SELECT YEAR(updated_at) FROM vehicle WHERE id_vehicle = 300")).scalar_one() > 2000


def test_mysql_startup_seeding_uses_migrated_models(mysql_database, monkeypatch):
    import app.main as application

    engine, config = mysql_database
    command.upgrade(config, "head")
    monkeypatch.setattr(application, "SessionLocal", sessionmaker(bind=engine))
    for _ in range(2):
        with TestClient(app):
            pass
    with Session(engine) as session:
        users = session.query(User).all()
        assert {user.user_name for user in users} == {"world", "alice", "bob", "charlie", "diana"}
        assert all(user.profile.full_name for user in users)
        assert all(verify_password("Password1", user.password_hash) for user in users)
