from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import schemas, models
from ..deps import get_db, require_roles, get_current_user

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.post("/", response_model=schemas.RoomOut)
def create_room(
    room_in: schemas.RoomCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin", "facility_manager")),
):
    """
    Create a new meeting room.

    Only admins and facility managers can create rooms. The room name must be unique.

    Raises
    ------
    HTTPException
        - 400 if a room with the same name already exists.
    """
    existing = db.query(models.Room).filter(models.Room.name == room_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Room name already exists")
    room = models.Room(**room_in.dict())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

'''
@router.get("/", response_model=List[schemas.RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    min_capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment_contains: Optional[str] = None,
):
    query = db.query(models.Room)
    if min_capacity is not None:
        query = query.filter(models.Room.capacity >= min_capacity)
    if location is not None:
        query = query.filter(models.Room.location == location)
    if equipment_contains is not None:
        query = query.filter(models.Room.equipment.contains(equipment_contains))
    return query.all()
'''
#added:
@router.get("/", response_model=List[schemas.RoomOut])
def list_rooms(
    db: Session = Depends(get_db),
    min_capacity: Optional[int] = None,
    location: Optional[str] = None,
    equipment_contains: Optional[str] = None,
    only_available: bool = False,
):
    """
    List rooms with optional filters.

    Parameters
    ----------
    min_capacity : int, optional
        Minimum room capacity.
    location : str, optional
        Exact location string to match.
    equipment_contains : str, optional
        Filter rooms whose equipment field contains this substring.
    only_available : bool, optional
        If True, only rooms marked as available are returned.
    """
    query = db.query(models.Room)

    if min_capacity is not None:
        query = query.filter(models.Room.capacity >= min_capacity)
    if location is not None:
        query = query.filter(models.Room.location == location)
    if equipment_contains is not None:
        query = query.filter(models.Room.equipment.contains(equipment_contains))
    if only_available:
        query = query.filter(models.Room.is_available == True)

    return query.all()


@router.get("/{room_id}", response_model=schemas.RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a single meeting room by its ID.

    Returns full room details including capacity, equipment, and availability.
    Raises a 404 error if the room does not exist.
    """
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.patch("/{room_id}", response_model=schemas.RoomOut)
def update_room(
    room_id: int,
    room_update: schemas.RoomUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin", "facility_manager")),
):
    """
    Update details of an existing room. *(Admin or Facility Manager)*

    Allows modifying capacity, equipment, location, and availability.
    Raises a 404 error if the room is not found.
    """
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    data = room_update.dict(exclude_unset=True)
    for field, value in data.items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin", "facility_manager")),
):
    """
    Delete a meeting room. *(Admin or Facility Manager)*

    Permanently removes the room from the system.
    Raises a 404 error if the room does not exist.
    """
    room = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    db.delete(room)
    db.commit()
    return {"detail": "Room deleted"}
