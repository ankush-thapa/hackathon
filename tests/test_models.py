from datetime import datetime
from decimal import Decimal
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import StaleDataError

from app.core.ids import new_id
from app.db.session import Base
from app.models import (
    BookingStatus, DocType, Gender, Ride, RideBooking, RideStatus, Station, User, UserDocument, UserProfile,
    UserSession, UserStatus,
)


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


def test_user_session_defaults_and_unique_token_hash(db):
    u = make_user()
    db.add(u)
    db.flush()
    token_hash = hashlib.sha256(b"refresh-token").hexdigest()
    expires_at = datetime(2030, 1, 1)
    s = UserSession(id_session=new_id(), id_user=u.id_user, refresh_token_hash=token_hash, expires_at=expires_at)
    db.add(s)
    db.commit()
    db.refresh(s)
    assert s.revoked_at is None and s.created_at
    assert s.expires_at == expires_at
    db.add(UserSession(id_session=new_id(), id_user=u.id_user, refresh_token_hash=token_hash, expires_at=expires_at))
    with pytest.raises(IntegrityError):
        db.commit()


def make_ride(db, **kw):
    src, dst = Station(station_name="North"), Station(station_name="South")
    db.add_all([src, dst])
    db.flush()
    values = {"id_driver": 1, "id_vehicle": 1, "departure_time": datetime(2030, 1, 1, 8),
              "total_seats": 4, "available_seats": 4, "source_station": src, "destination_station": dst}
    ride = Ride(id_ride=new_id(), **(values | kw))
    db.add(ride)
    return ride


def make_booking(ride, **kw):
    values = {"id_rider": 2, "id_driver": ride.id_driver, "price_per_seat": Decimal("10.00"),
              "total_amount": Decimal("10.00")}
    return RideBooking(id_booking=new_id(), ride=ride, **(values | kw))


def test_ride_and_booking_defaults(db):
    ride = make_ride(db)
    ride.bookings.append(make_booking(ride))
    db.commit()
    db.refresh(ride)
    assert ride.status is RideStatus.open and ride.version == 1
    assert ride.price_per_seat == Decimal("0.00")
    assert ride.source_station.station_name == "North" and ride.source_station.is_active is True
    booking = ride.bookings[0]
    db.refresh(booking)
    assert booking.status is BookingStatus.requested and booking.seats_booked == 1
    assert booking.active_flag == 1 and booking.ride is ride


def test_one_active_booking_per_rider_per_ride(db):
    ride = make_ride(db)
    first = make_booking(ride)
    db.add(first)
    db.commit()
    db.add(make_booking(ride))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    first.status = BookingStatus.cancelled_by_rider
    db.commit()
    db.refresh(first)
    assert first.active_flag is None and first.version == 2
    db.add(make_booking(ride))
    db.commit()


@pytest.mark.parametrize("kw", [
    {"total_seats": 0, "available_seats": 0},
    {"total_seats": 9, "available_seats": 9},
    {"available_seats": 5},
    {"price_per_seat": Decimal("-1")},
])
def test_ride_check_constraints(db, kw):
    make_ride(db, **kw)
    with pytest.raises(IntegrityError):
        db.commit()


def test_ride_requires_different_stations(db):
    ride = make_ride(db)
    ride.destination_station = ride.source_station
    with pytest.raises(IntegrityError):
        db.commit()


def test_ride_version_detects_concurrent_update(db):
    ride = make_ride(db)
    db.commit()
    assert ride.version == 1  # loads the row, as a read-then-write request would
    db.execute(Ride.__table__.update().values(version=Ride.version + 1))  # another writer
    ride.available_seats = 3
    with pytest.raises(StaleDataError):
        db.commit()


def test_snowflake_ids_unique_and_increasing():
    ids = [new_id() for _ in range(5000)]
    assert len(set(ids)) == 5000 and ids == sorted(ids)
    assert ids[-1] < 2**63
