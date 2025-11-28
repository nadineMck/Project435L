from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ----- Users -----
class UserBase(BaseModel):
    name: str
    username: str
    email: EmailStr
    role: str = "regular"   # admin, regular, facility_manager


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True


class UserPasswordReset(BaseModel):
    new_password: str


# ----- Bookings (for nested views) -----
class BookingBase(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime


class BookingCreate(BookingBase):
    pass


class BookingOut(BookingBase):
    id: int
    user_id: int

    class Config:
        orm_mode = True


# ----- Rooms -----
class RoomBase(BaseModel):
    name: str
    capacity: int
    equipment: Optional[str] = None
    location: str
    is_available: bool = True


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    capacity: Optional[int] = None
    equipment: Optional[str] = None
    location: Optional[str] = None
    is_available: Optional[bool] = None


class RoomOut(RoomBase):
    id: int

    class Config:
        orm_mode = True


# ----- Reviews -----
class ReviewBase(BaseModel):
    room_id: int
    rating: int
    comment: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None


class ReviewOut(ReviewBase):
    id: int
    user_id: int
    flagged: bool
    deleted: bool

    class Config:
        orm_mode = True


# ----- Auth -----
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ----- Availability responses -----
class AvailabilityResponse(BaseModel):
    room_id: int
    start_time: datetime
    end_time: datetime
    available: bool
