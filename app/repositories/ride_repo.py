from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

_STATION_EXISTS = text("SELECT 1 FROM station WHERE id_station = :id AND is_active = 1 LIMIT 1")

# Fixed fragments only: every user-supplied value is a bound parameter.
_SEARCH_SELECT = """
SELECT r.id_ride, r.id_driver,
       r.id_source_station, ss.station_name AS source_station_name,
       r.id_destination_station, ds.station_name AS destination_station_name,
       r.departure_time, r.estimated_arrival_time, r.total_seats, r.available_seats,
       r.price_per_seat, r.notes,
       p.full_name AS driver_name, p.photo_url AS driver_photo_url,
       v.make AS vehicle_make, v.model AS vehicle_model, v.color AS vehicle_color,
       v.vehicle_type AS vehicle_type
FROM ride r
JOIN station ss ON ss.id_station = r.id_source_station
JOIN station ds ON ds.id_station = r.id_destination_station
LEFT JOIN user_profile p ON p.id_user = r.id_driver
LEFT JOIN vehicle v ON v.id_vehicle = r.id_vehicle
WHERE r.id_source_station = :id_source_station
  AND r.id_destination_station = :id_destination_station
  AND r.status = 'open'
  AND r.available_seats >= :seats
  AND r.departure_time >= :departure_from
  AND r.departure_time < :departure_until
"""
_AFTER_CURSOR = "  AND (r.departure_time > :cursor_time OR (r.departure_time = :cursor_time AND r.id_ride > :cursor_id))\n"
_BEFORE_CURSOR = "  AND (r.departure_time < :cursor_time OR (r.departure_time = :cursor_time AND r.id_ride < :cursor_id))\n"
_ORDER_ASC = "ORDER BY r.departure_time, r.id_ride\nLIMIT :limit"
_ORDER_DESC = "ORDER BY r.departure_time DESC, r.id_ride DESC\nLIMIT :limit"


class RideRepository:
    """Plain-SQL reads over `ride` (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def station_exists(self, id_station: int) -> bool:
        return self._db.execute(_STATION_EXISTS, {"id": id_station}).first() is not None

    def search_open(
        self,
        *,
        id_source_station: int,
        id_destination_station: int,
        seats: int,
        departure_from: datetime,
        departure_until: datetime,
        after: tuple[datetime, int] | None,
        before: tuple[datetime, int] | None,
        limit: int,
    ) -> list[dict]:
        """Rows in departure order. `before` pages backwards (rows come back nearest-first, so callers reverse them)."""
        sql = _SEARCH_SELECT
        params: dict = {
            "id_source_station": id_source_station,
            "id_destination_station": id_destination_station,
            "seats": seats,
            "departure_from": departure_from,  # inclusive
            "departure_until": departure_until,  # exclusive
            "limit": limit,
        }
        if after is not None:
            sql += _AFTER_CURSOR
            params["cursor_time"], params["cursor_id"] = after
        elif before is not None:
            sql += _BEFORE_CURSOR
            params["cursor_time"], params["cursor_id"] = before
        order = _ORDER_DESC if before is not None else _ORDER_ASC
        rows = self._db.execute(text(sql + order), params).mappings().all()
        return [dict(r) for r in rows]
