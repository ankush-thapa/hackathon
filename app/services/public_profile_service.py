from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.public_profile import PublicProfileResponse, PublicVehicle
from app.services.profile_service import age_on


class PublicProfileNotFound(Exception):
    """No such user, deleted user, or the caller isn't allowed to see them (same 404 either way)."""


# Who may see whom:
#   • yourself
#   • anyone offering a ride that is currently bookable (open/full), so riders can check the driver
#   • people who share a ride with you: you drive and they booked, or they drive and you booked
_CAN_VIEW = text(
    "SELECT 1 FROM ride r WHERE r.id_driver = :t AND r.status IN ('open', 'full') "
    "UNION ALL "
    "SELECT 1 FROM ride r JOIN ride_booking b ON b.id_ride = r.id_ride "
    "WHERE (r.id_driver = :v AND b.id_rider = :t) OR (r.id_driver = :t AND b.id_rider = :v) "
    "LIMIT 1"
)

_USER = text(
    "SELECT u.id_user, u.status, u.created_at, p.full_name, p.photo_url, p.about, p.gender, p.date_of_birth "
    "FROM `user` u LEFT JOIN user_profile p ON p.id_user = u.id_user WHERE u.id_user = :t"
)

_RIDES_DRIVEN = text("SELECT COUNT(*) FROM ride WHERE id_driver = :t AND status = 'completed'")
_RIDES_TAKEN = text("SELECT COUNT(*) FROM ride_booking WHERE id_rider = :t AND status = 'completed'")
_VEHICLE = text(
    "SELECT make, model, color, vehicle_type FROM vehicle WHERE id_user = :t AND status = 'active' "
    "ORDER BY is_default DESC, created_at DESC LIMIT 1"
)


def _as_date(value) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])  # SQLite returns strings


def _as_datetime(value) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))


class PublicProfileService:
    def __init__(self, db: Session):
        self._db = db

    def get(self, viewer_id: int, target_id: int) -> PublicProfileResponse:
        params = {"v": viewer_id, "t": target_id}
        if viewer_id != target_id and self._db.execute(_CAN_VIEW, params).first() is None:
            raise PublicProfileNotFound
        row = self._db.execute(_USER, params).mappings().first()
        if row is None or row["status"] == "deleted":
            raise PublicProfileNotFound

        vehicle = self._db.execute(_VEHICLE, params).mappings().first()
        gender = row["gender"]
        return PublicProfileResponse(
            userId=str(row["id_user"]),
            fullName=row["full_name"],
            photoUrl=row["photo_url"],
            about=row["about"],
            gender=getattr(gender, "value", gender),
            age=age_on(_as_date(row["date_of_birth"]), datetime.now(timezone.utc).date()),
            memberSince=_as_datetime(row["created_at"]),
            ridesDriven=self._db.execute(_RIDES_DRIVEN, params).scalar_one(),
            ridesTaken=self._db.execute(_RIDES_TAKEN, params).scalar_one(),
            vehicle=PublicVehicle(
                make=vehicle["make"], model=vehicle["model"], color=vehicle["color"],
                vehicleType=getattr(vehicle["vehicle_type"], "value", vehicle["vehicle_type"]),
            ) if vehicle else None,
        )
