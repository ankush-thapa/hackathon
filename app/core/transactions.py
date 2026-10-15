from functools import wraps
from sqlalchemy.exc import OperationalError


def retry_lock_conflicts(method):
    """Retry whole rolled-back transactions for MySQL deadlock/lock-wait errors only."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        for attempt in range(3):
            try:
                return method(self, *args, **kwargs)
            except OperationalError as exc:
                db = getattr(self, "_db", None)
                if db is None:
                    db = self.db
                db.rollback()
                if getattr(exc.orig, "errno", None) not in (1205, 1213) or attempt == 2:
                    raise
    return wrapped
