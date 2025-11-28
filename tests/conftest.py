"""
Pytest configuration and shared fixtures for testing the Smart Meeting Room API.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app
from app.deps import get_db, get_password_hash
from app import models


# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create a test client with the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """
    Create an admin user for testing.
    """
    user = models.User(
        name="Admin User",
        username="admin",
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass123"),
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def regular_user(db_session):
    """
    Create a regular user for testing.
    """
    user = models.User(
        name="Regular User",
        username="regularuser",
        email="regular@example.com",
        hashed_password=get_password_hash("regularpass123"),
        role="regular",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def facility_manager(db_session):
    """
    Create a facility manager user for testing.
    """
    user = models.User(
        name="Facility Manager",
        username="facilitymanager",
        email="facility@example.com",
        hashed_password=get_password_hash("facilitypass123"),
        role="facility_manager",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(client):
    """
    Get an admin authentication token.
    """
    response = client.post(
        "/users/login",
        params={"username": "admin", "password": "adminpass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def regular_token(client):
    """
    Get a regular user authentication token.
    """
    response = client.post(
        "/users/login",
        params={"username": "regularuser", "password": "regularpass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def facility_token(client):
    """
    Get a facility manager authentication token.
    """
    response = client.post(
        "/users/login",
        params={"username": "facilitymanager", "password": "facilitypass123"},
    )
    return response.json()["access_token"]


@pytest.fixture
def sample_room(db_session):
    """
    Create a sample room for testing.
    """
    room = models.Room(
        name="Conference Room A",
        capacity=10,
        equipment="Projector, Whiteboard",
        location="Building 1, Floor 2",
        is_available=True,
    )
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    return room


@pytest.fixture
def sample_rooms(db_session):
    """
    Create multiple sample rooms for testing.
    """
    rooms = [
        models.Room(
            name="Small Meeting Room",
            capacity=4,
            equipment="TV Screen",
            location="Building 1, Floor 1",
            is_available=True,
        ),
        models.Room(
            name="Large Conference Hall",
            capacity=50,
            equipment="Projector, Sound System, Whiteboard",
            location="Building 2, Floor 3",
            is_available=True,
        ),
        models.Room(
            name="Board Room",
            capacity=12,
            equipment="Video Conference System",
            location="Building 1, Floor 3",
            is_available=False,
        ),
    ]
    for room in rooms:
        db_session.add(room)
    db_session.commit()
    for room in rooms:
        db_session.refresh(room)
    return rooms


@pytest.fixture
def sample_booking(db_session, regular_user, sample_room):
    """
    Create a sample booking for testing.
    """
    from datetime import datetime, timedelta
    
    booking = models.Booking(
        user_id=regular_user.id,
        room_id=sample_room.id,
        start_time=datetime.utcnow() + timedelta(hours=1),
        end_time=datetime.utcnow() + timedelta(hours=2),
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    return booking


@pytest.fixture
def sample_review(db_session, regular_user, sample_room):
    """
    Create a sample review for testing.
    """
    review = models.Review(
        user_id=regular_user.id,
        room_id=sample_room.id,
        rating=5,
        comment="Great room with excellent facilities!",
        flagged=False,
        deleted=False,
    )
    db_session.add(review)
    db_session.commit()
    db_session.refresh(review)
    return review


def get_auth_header(token: str) -> dict:
    """
    Helper function to create authorization header.
    """
    return {"Authorization": f"Bearer {token}"}