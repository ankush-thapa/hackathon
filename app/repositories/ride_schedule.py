from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import bindparam, text

from app.core.config import settings
from app.db.types import DateTime3


def lock_driver(db, id_driver: int):
    lock = " FOR UPDATE" if db.get_bind().dialect.name == "mysql" else ""
    state = db.execute(text("SELECT status FROM `user` WHERE id_user = :driver" + lock), {"driver": id_driver}).scalar()
    if state != "active":
        raise HTTPException(403, "driver account is inactive")


def ensure_departure_gap(db, id_driver: int, departure, exclude_ride: int):
    """Caller holds the driver row lock; exact minimum gap is allowed."""
    gap = timedelta(minutes=settings.MIN_RIDE_GAP_MINUTES)
    lock = " FOR UPDATE" if db.get_bind().dialect.name == "mysql" else ""
    query = text(
        "SELECT id_ride FROM ride WHERE id_driver = :driver AND id_ride <> :exclude "
        "AND status IN ('open', 'full', 'started') "
        "AND departure_time > :start AND departure_time < :end LIMIT 1" + lock
    ).bindparams(bindparam("start", type_=DateTime3), bindparam("end", type_=DateTime3))
    conflict = db.execute(query, {"driver": id_driver, "exclude": exclude_ride,
                                 "start": departure-gap, "end": departure+gap}).first()
    if conflict:
        raise HTTPException(409, f"Your active rides must have at least {settings.MIN_RIDE_GAP_MINUTES} minutes between departures")
