from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from .. import schemas, models
from ..deps import get_db, get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


def overlaps(start1, end1, start2, end2) -> bool:
    """
    Check if two time intervals overlap.

    Returns True if the interval [start1, end1) overlaps with [start2, end2).
    """
    return start1 < end2 and start2 < end1


@router.get("/check", response_model=schemas.AvailabilityResponse)
def check_room_availability(
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db),
):
    """
    Check if a room is available in a given time range.

    This does not create a booking. It just verifies if any existing
    bookings overlap with the requested time window.
    """
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    existing = db.query(models.Booking).filter(
        models.Booking.room_id == room_id
    ).all()

    for b in existing:
        if overlaps(start_time, end_time, b.start_time, b.end_time):
            # Not available in that time window
            return schemas.AvailabilityResponse(
                room_id=room_id,
                start_time=start_time,
                end_time=end_time,
                available=False,
            )

    # No conflicts → room is available
    return schemas.AvailabilityResponse(
        room_id=room_id,
        start_time=start_time,
        end_time=end_time,
        available=True,
    )


@router.get("/", response_model=List[schemas.BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List bookings for the current user or all bookings.

    - Admin and facility managers see **all** bookings.
    - Regular users see **only their own** bookings.
    """
    # Admin/facility_manager see all, regular sees only own
    if current_user.role in ("admin", "facility_manager"):
        return db.query(models.Booking).all()
    return db.query(models.Booking).filter(models.Booking.user_id == current_user.id).all()


@router.post("/", response_model=schemas.BookingOut)
def create_booking(
    booking_in: schemas.BookingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new booking for a room.

    Regular users and facility managers must respect room availability:
    overlapping bookings are rejected. Admins can override conflicts and
    create overlapping bookings if needed.
    """
    room = db.query(models.Room).filter(models.Room.id == booking_in.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Check availability based on time overlap
    existing = db.query(models.Booking).filter(
        models.Booking.room_id == booking_in.room_id
    ).all()

    # Admin can override conflicts (RBAC "override/resolve conflicts")
    if current_user.role != "admin":
        for b in existing:
            if overlaps(booking_in.start_time, booking_in.end_time, b.start_time, b.end_time):
                raise HTTPException(status_code=400, detail="Room already booked for that time range")

    booking = models.Booking(
        user_id=current_user.id,
        room_id=booking_in.room_id,
        start_time=booking_in.start_time,
        end_time=booking_in.end_time,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/{booking_id}", response_model=schemas.BookingOut)
def update_booking(
    booking_id: int,
    booking_update: schemas.BookingCreate,  # for simplicity use same schema
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update an existing booking.

    Only the owner of the booking or an admin can update the booking.
    For non-admins, the new time range must not overlap with other
    bookings for the same room.
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # owner or admin can update
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to update this booking")

    # Check overlap again (admin can override)
    existing = db.query(models.Booking).filter(
        models.Booking.room_id == booking_update.room_id,
        models.Booking.id != booking_id
    ).all()

    if current_user.role != "admin":
        for b in existing:
            if overlaps(booking_update.start_time, booking_update.end_time, b.start_time, b.end_time):
                raise HTTPException(status_code=400, detail="Room already booked for that time range")

    booking.room_id = booking_update.room_id
    booking.start_time = booking_update.start_time
    booking.end_time = booking_update.end_time

    db.commit()
    db.refresh(booking)
    return booking


@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Cancel a booking.

    - Regular users and facility managers can cancel their own bookings.
    - Admins can force-cancel any booking (override).
    """
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Regular & facility manager: cancel own bookings.
    # Admin: can force-cancel any booking.
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to cancel this booking")

    db.delete(booking)
    db.commit()
    return {"detail": "Booking cancelled"}
