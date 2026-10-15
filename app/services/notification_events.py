"""Turns booking/ride events emitted by the repositories into notifications.

Repositories call the hook just before they commit, so each notification is saved in the same transaction as
the change that caused it: no notification for a change that rolled back, and none lost after one that committed.
"""
from app.core.pagination import as_datetime
from app.models.notification import NotificationType
from app.services.notification_service import NotificationService


def _when(value) -> str:
    return as_datetime(value).strftime("%d %b, %H:%M UTC")


def _seats(n: int) -> str:
    return f"{n} seat" + ("" if n == 1 else "s")


def _reason(ctx: dict) -> str:
    return f" Reason: {ctx['reason']}" if ctx.get("reason") else ""


def notify_event(notifications: NotificationService, ctx: dict) -> None:
    """Queue the notification(s) for one event. `ctx["event"]` is one of the cases below."""
    event = ctx["event"]
    ride = f"{ctx['route']} ride on {_when(ctx['departure_time'])}"
    rider = ctx.get("rider_name") or "A rider"
    driver = ctx.get("driver_name") or "The driver"
    send = lambda to, type_, message: notifications.notify(  # noqa: E731
        to, type_, ctx["id_ride"], message, id_booking=ctx.get("id_booking")
    )

    if event == "ride_created":
        send(ctx["id_driver"], NotificationType.ride_created, f"Your {ride} is live with {_seats(ctx['seats'])} available.")
    elif event == "booking_requested":
        send(ctx["id_driver"], NotificationType.booking_requested, f"{rider} requested {_seats(ctx['seats'])} on your {ride}.")
    elif event == "booking_accepted":
        send(ctx["id_rider"], NotificationType.booking_accepted, f"{driver} approved your request for {_seats(ctx['seats'])} on the {ride}.")
    elif event == "booking_rejected":
        send(ctx["id_rider"], NotificationType.booking_rejected, f"{driver} declined your request for {_seats(ctx['seats'])} on the {ride}.{_reason(ctx)}")
    elif event == "booking_cancelled":
        if ctx["actor"] == "rider":  # the driver is told
            send(ctx["id_driver"], NotificationType.booking_cancelled, f"{rider} cancelled their booking of {_seats(ctx['seats'])} on your {ride}.{_reason(ctx)}")
        else:  # the rider is told
            send(ctx["id_rider"], NotificationType.booking_cancelled, f"{driver} cancelled your booking of {_seats(ctx['seats'])} on the {ride}.{_reason(ctx)}")
    else:
        raise ValueError(f"unknown event {event!r}")
