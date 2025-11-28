from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from fastapi.security import OAuth2PasswordRequestForm

from .. import schemas, models
from ..deps import (
    get_db,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=schemas.UserOut)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(
        (models.User.username == user_in.username) | (models.User.email == user_in.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    user = models.User(
        name=user_in.name,
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token, tags=["auth"], include_in_schema=False)
def login_for_access_token(
    username: str,
    password: str,
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token({"sub": user.username, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_current_user(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Regular / facility_manager / admin can manage their own profile.
    Non-admin users CANNOT change their role.
    """
    data = user_update.dict(exclude_unset=True)

    if "role" in data and current_user.role != "admin":
        # Regular or facility_manager not allowed to change role
        raise HTTPException(status_code=403, detail="Not allowed to change your role")

    for field, value in data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: full user listing.
    """
    return db.query(models.User).all()


@router.get("/{username}", response_model=schemas.UserOut)
def get_user(
    username: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: view any specific user.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{username}", response_model=schemas.UserOut)
def update_user(
    username: str,
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    - Admin: update any user (including role).
    - Any user: update own profile (but not role unless admin).
    - Facility manager has no user-admin over others.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Permission check
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(status_code=403, detail="Not allowed to update this user")

    data = user_update.dict(exclude_unset=True)

    # Only admin can change roles
    if "role" in data and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to change role")

    for field, value in data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/{username}/reset-password")
def reset_user_password(
    username: str,
    payload: schemas.UserPasswordReset,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: reset any user's password.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"detail": "Password reset successfully"}


@router.delete("/{username}")
def delete_user(
    username: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}


@router.get("/{username}/bookings", response_model=list[schemas.BookingOut])
def get_user_booking_history(
    username: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Admin-only: view any user's booking history.
    Regular users see their own history via /bookings/ or /users/me.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    bookings = db.query(models.Booking).filter(models.Booking.user_id == user.id).all()
    return bookings
