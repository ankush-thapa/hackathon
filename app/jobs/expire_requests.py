"""Run periodically: python -m app.jobs.expire_requests --limit 100.

Uses existing tables only. Multiple runners are safe because each mutation locks its ride.
Deploy with a scheduler; the API does not start an in-process background scheduler.
"""
import argparse
from datetime import datetime, timezone
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import Ride, RideBooking, BookingStatus
from app.services.ride_actions import RideActions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000: parser.error('--limit must be 1-1000')
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with SessionLocal() as db:
        rows = db.execute(select(Ride.id_ride, Ride.id_driver).where(Ride.departure_time <= now,
            select(RideBooking.id_booking).where(RideBooking.id_ride == Ride.id_ride,
                RideBooking.status == BookingStatus.requested).exists(),
        ).order_by(Ride.departure_time, Ride.id_ride).limit(args.limit)).all()
    count = 0
    for ride_id, driver in rows:
        with SessionLocal() as db: count += RideActions(db).expire(ride_id, driver)
    print(f'Expired {count} pending requests')


if __name__ == '__main__': main()
