"""Bidirectional keyset pagination shared by list endpoints.

A cursor marks a position `(sort time, unique id)` plus a direction relative to the endpoint's sort order:
'n' = rows further along the order, 'p' = rows before the position. Clients treat tokens as opaque.
"""
import base64
from datetime import datetime
from typing import Callable


class InvalidCursorError(Exception):
    pass


def as_datetime(v: datetime | str) -> datetime:
    """MySQL returns datetime objects; SQLite (tests) returns ISO strings for raw queries."""
    return datetime.fromisoformat(v) if isinstance(v, str) else v


def encode_cursor(direction: str, when: datetime, row_id: int) -> str:
    return base64.urlsafe_b64encode(f"{direction}|{when.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(cursor: str) -> tuple[str, datetime, int]:
    try:
        direction, time_part, id_part = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        if direction not in ("n", "p"):
            raise ValueError
        return direction, datetime.fromisoformat(time_part), int(id_part)
    except (ValueError, UnicodeDecodeError):
        raise InvalidCursorError from None


def paginate(
    rows: list[dict], page_size: int, direction: str | None, key_of: Callable[[dict], tuple[datetime, int]]
) -> tuple[list[dict], str | None, str | None]:
    """Turn `page_size + 1` fetched rows into (page, next_page, prev_page).

    Rows fetched while going back arrive nearest-first and are reversed to the endpoint's order.
    """
    going_back = direction == "p"
    page, has_more = rows[:page_size], len(rows) > page_size
    if going_back:
        page.reverse()
    if not page:
        return [], None, None
    # Moving in a direction means we came from the other side, so that link always exists.
    has_next = True if going_back else has_more
    has_prev = has_more if going_back else direction == "n"

    def token(d: str, row: dict) -> str:
        when, row_id = key_of(row)
        return encode_cursor(d, as_datetime(when), row_id)

    return page, token("n", page[-1]) if has_next else None, token("p", page[0]) if has_prev else None
