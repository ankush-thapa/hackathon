from app.core.ids import new_id
from fastapi import HTTPException
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import NotificationItem, NotificationListResponse, SendNotificationRequest


class NotificationNotFoundError(Exception):
    pass


class RideNotFoundError(Exception):
    pass


class NotRideParticipantError(Exception):
    """Sender or recipient is neither the ride's driver nor a rider who booked it."""

    def __init__(self, who: str):
        self.who = who
        super().__init__(f"{who} is not part of this ride")


class BookingNotOnRideError(Exception):
    pass


def _item(r: dict) -> NotificationItem:
    return NotificationItem(
        idNotification=r["id_notification"],
        type=r["type"],
        idRide=r["id_ride"],
        idBooking=r["id_booking"],
        message=r["message"],
        createdAt=r["created_at"],
        read=bool(r.get("is_read", False)),
    )


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self._repo = repo

    def notify(
        self,
        id_user: int,
        type: NotificationType,
        id_ride: int,
        message: str,
        id_booking: int | None = None,
    ) -> int:
        """Queue a notification for `id_user` in the current transaction; the caller commits.

        Call this from booking/ride flows next to the state change, e.g.
        notify(ride.id_driver, NotificationType.booking_requested, ride.id_ride,
               "Rahul requested 2 seats on your 9:00 AM ride", id_booking=booking.id_booking)
        """
        id_notification = new_id()
        self._repo.add({
            "id_notification": id_notification,
            "id_user": id_user,
            "type": NotificationType(type).value,
            "id_ride": id_ride,
            "id_booking": id_booking,
            "message": message[:255],
        })
        return id_notification

    def send(self, id_sender: int, req: SendNotificationRequest) -> NotificationItem:
        """Send a notification to another participant of the same ride, and commit it."""
        participants = self._repo.ride_participants(req.idRide)
        if participants is None:
            raise RideNotFoundError
        if id_sender not in participants:
            raise NotRideParticipantError("sender")
        if req.idUser not in participants:
            raise NotRideParticipantError("idUser")
        if req.idBooking is not None and not self._repo.booking_on_ride(req.idBooking, req.idRide):
            raise BookingNotOnRideError
        event = self._repo.event_state(req.idRide, req.idBooking)
        kind = req.type.value
        if kind.startswith("booking_"):
            if event is None or event["booking_status"] is None:
                raise HTTPException(422, "idBooking is required for booking notifications")
            driver, rider = event["id_driver"], event["id_rider"]
            expected = {
                "booking_requested": ({"requested"}, rider, driver),
                "booking_accepted": ({"accepted"}, driver, rider),
                "booking_rejected": ({"rejected"}, driver, rider),
            }
            if kind in expected:
                states, sender, recipient = expected[kind]
                if event["booking_status"] not in states or (id_sender, req.idUser) != (sender, recipient):
                    raise HTTPException(403, "notification does not match booking state or actor")
            elif kind == "booking_cancelled":
                status = event["booking_status"]
                sender, recipient = (rider, driver) if status == "cancelled_by_rider" else (driver, rider)
                if status not in ("cancelled_by_rider", "cancelled_by_driver") or (id_sender, req.idUser) != (sender, recipient):
                    raise HTTPException(403, "notification does not match cancellation")
        elif id_sender != event["id_driver"] or (kind == "ride_cancelled" and event["ride_status"] != "cancelled"):
            raise HTTPException(403, "only the driver can send matching ride events")
        id_notification = self.notify(req.idUser, req.type, req.idRide, req.message, id_booking=req.idBooking)
        self._repo.commit()
        return _item(self._repo.get(id_notification))

    def unread(self, id_user: int, limit: int) -> NotificationListResponse:
        rows = self._repo.list_unread(id_user, limit)
        return NotificationListResponse(
            items=[_item(r) for r in rows],
            unreadCount=self._repo.count_unread(id_user),
        )

    def mark_read(self, id_user: int, id_notification: int) -> None:
        if not self._repo.mark_read(id_user, id_notification):
            raise NotificationNotFoundError

    def mark_all_read(self, id_user: int) -> int:
        return self._repo.mark_all_read(id_user)
