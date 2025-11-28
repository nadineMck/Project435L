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
    """
    Register a new user.

    This endpoint creates a new user account with a given role
    (``admin``, ``regular``, or ``facility_manager``). It validates that the
    username and email are unique.

    Parameters
    ----------
    user_in : UserCreate
        User details including name, username, email, role, and password.
    db : Session
        Database session.

    Raises
    ------
    HTTPException
        - 400 if the username or email already exists.
    """
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
    """
    Authenticate a user and return a JWT access token.

    This endpoint checks the provided username and password, and if valid,
    issues a short-lived JWT token that is used for authenticated API calls.

    Parameters
    ----------
    username : str
        Username of the account.
    password : str
        Plain-text password.
    db : Session
        Database session.

    Raises
    ------
    HTTPException
        - 401 if credentials are invalid.
    """
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
    """
    Get the currently authenticated user.

    Returns the profile information of the user associated with the provided
    Bearer token.
    """
    return current_user


@router.patch("/me", response_model=schemas.UserOut)
def update_current_user(
    user_update: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update the profile of the current user.

    Regular users and facility managers can update their own profile fields
    (name, email). Only admins are allowed to change their own role.

    Raises
    ------
    HTTPException
        - 403 if a non-admin tries to change their role.
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
    List all registered users. *(Admin-only)*

    This endpoint returns full profile information for every user in the system,
    including their roles, emails, and account details. Only administrators are
    permitted to access this endpoint because it reveals sensitive user data.

    Returns
    -------
    List[UserOut]
        A list of all users stored in the database.
    """
    return db.query(models.User).all()


@router.get("/{username}", response_model=schemas.UserOut)
def get_user(
    username: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """
    Get a user by username. *(Admin-only)*

    Administrators can fetch the full profile of any user in the system
    using their unique username. This is useful for inspection,
    troubleshooting, or verifying user account details.

    Raises
    ------
    HTTPException
        - 404 if the user does not exist.
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
    Update any user's account information.

    - Administrators can update **any** user’s profile, including name, email,
      and role.
    - Regular users may update **only their own** name and email.
    - Only administrators can modify a user's role.

    This endpoint applies validation to ensure users cannot escalate their own
    privileges or alter protected fields.

    Raises
    ------
    HTTPException
        - 403 if a non-admin attempts to modify someone else's profile or change roles.
        - 404 if the target user does not exist.
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
    Reset a user's password. *(Admin-only)*

    This endpoint allows administrators to forcibly reset the password of
    any existing user. A new password is generated or assigned, depending
    on implementation.

    Raises
    ------
    HTTPException
        - 404 if the user does not exist.
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
    """
    Delete a user from the system. *(Admin-only)*

    This operation permanently removes a user account and all associated
    database records. Only administrators may delete user accounts, as this
    action is irreversible.

    Raises
    ------
    HTTPException
        - 404 if the user does not exist.
    """
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
    View any user's full booking history. *(Admin-only)*

    Administrators can inspect all bookings made by a specific user,
    including both past and future reservations. This is useful for audits,
    troubleshooting disputes, or system monitoring.

    Raises
    ------
    HTTPException
        - 404 if the user does not exist.
    """
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    bookings = db.query(models.Booking).filter(models.Booking.user_id == user.id).all()
    return bookings
