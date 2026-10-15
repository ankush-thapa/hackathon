from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.types import DateTime3


class StationRepository:
    """Read the fixed pickup/drop-off station list using bound query parameters."""

    def __init__(self, db: Session):
        self._db = db

    def list(self, *, search: str | None, include_inactive: bool, limit: int, offset: int) -> dict:
        conditions = []
        params = {"limit": limit, "offset": offset}
        if not include_inactive:
            conditions.append("is_active = 1")
        search = search.strip() if search else ""
        if search:
            # Treat %, _ and the escape character as literal search text.
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            conditions.append("LOWER(station_name) LIKE LOWER(:search) ESCAPE '!'")
            params["search"] = f"%{escaped}%"
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        total = self._db.execute(text("SELECT COUNT(*) FROM station" + where), params).scalar_one()
        query = text(
            "SELECT id_station, station_name, is_active, created_at FROM station" + where
            + " ORDER BY station_name, id_station LIMIT :limit OFFSET :offset"
        ).columns(created_at=DateTime3)
        items = [dict(row) for row in self._db.execute(query, params).mappings()]
        return {"items": items, "total": total, "limit": limit, "offset": offset}
