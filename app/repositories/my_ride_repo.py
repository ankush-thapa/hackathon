from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.ride_sql import RIDE_COLUMNS as _RIDE_COLUMNS
from app.repositories.ride_sql import RIDE_JOINS as _RIDE_JOINS

# A ride is "upcoming" while it is still bookable/ahead of us, or in progress.
_RIDE_UPCOMING = "((r.status IN ('open', 'full') AND r.departure_time >= :now) OR r.status = 'started')"

_ROLES = {
    "driver": {
        "select": f"""SELECT {_RIDE_COLUMNS},
       (SELECT COUNT(*) FROM ride_booking b
         WHERE b.id_ride = r.id_ride AND b.status = 'requested') AS pending_requests,
       (SELECT COALESCE(SUM(b.seats_booked), 0) FROM ride_booking b
         WHERE b.id_ride = r.id_ride AND b.status = 'accepted') AS accepted_seats
FROM ride r {_RIDE_JOINS}""",
        "owner": "r.id_driver = :me",
        "upcoming": _RIDE_UPCOMING,
        "key": "r.id_ride",  # unique per row
        "key_alias": "id_ride",
    },
    "rider": {
        "select": f"""SELECT {_RIDE_COLUMNS},
       b.id_booking, b.seats_booked, b.price_per_seat AS booking_price_per_seat, b.total_amount,
       b.status AS booking_status, b.rider_note, b.created_at AS booking_created_at
FROM ride_booking b
JOIN ride r ON r.id_ride = b.id_ride {_RIDE_JOINS}""",
        "owner": "b.id_rider = :me",
        "upcoming": f"(b.status IN ('requested', 'accepted') AND {_RIDE_UPCOMING})",
        "key": "b.id_booking",  # a rider can rebook a ride, so rows are keyed per booking
        "key_alias": "id_booking",
    },
}


class MyRideRepository:
    """Plain-SQL reads of a user's own rides (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def get_offered(self, id_user: int, id_ride: int) -> dict | None:
        sql = _ROLES["driver"]["select"] + " WHERE r.id_driver = :me AND r.id_ride = :ride"
        row = self._db.execute(text(sql), {"me": id_user, "ride": id_ride}).mappings().first()
        return dict(row) if row else None

    def list_offered(self, **kw) -> list[dict]:
        """Rides the user offered as a driver."""
        return self._list("driver", **kw)

    def list_booked(self, **kw) -> list[dict]:
        """Bookings the user made as a rider, joined with their rides (one row per booking)."""
        return self._list("rider", **kw)

    def _list(
        self,
        role: str,
        *,
        id_user: int,
        scope: str,
        now: datetime,
        position: tuple[datetime, int] | None,
        going_back: bool,
        limit: int,
    ) -> list[dict]:
        """Rows in the scope's sort order; when `going_back` they arrive nearest-first (callers reverse them)."""
        cfg = _ROLES[role]
        sort_desc = scope != "upcoming"  # upcoming: soonest first; otherwise most recent first
        where = [cfg["owner"]]
        if scope == "upcoming":
            where.append(cfg["upcoming"])
        elif scope == "past":
            where.append(f"NOT {cfg['upcoming']}")
        params: dict = {"me": id_user, "now": now, "limit": limit}

        # 'n' moves along the sort order, 'p' against it.
        fetch_desc = sort_desc != going_back
        if position is not None:
            op = "<" if fetch_desc else ">"
            where.append(
                f"(r.departure_time {op} :cursor_time OR (r.departure_time = :cursor_time AND {cfg['key']} {op} :cursor_id))"
            )
            params["cursor_time"], params["cursor_id"] = position
        direction = "DESC" if fetch_desc else "ASC"
        sql = (
            f"{cfg['select']}\nWHERE " + "\n  AND ".join(where)
            + f"\nORDER BY r.departure_time {direction}, {cfg['key']} {direction}\nLIMIT :limit"
        )
        rows = self._db.execute(text(sql), params).mappings().all()
        out = []
        for row in rows:
            d = dict(row)
            d["row_id"] = d[cfg["key_alias"]]  # key used for cursors
            out.append(d)
        return out
