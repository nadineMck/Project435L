"""
Unit tests for booking management endpoints.
"""
import pytest
from datetime import datetime, timedelta


def get_auth_header(token: str) -> dict:
    """Helper function to create authorization header."""
    return {"Authorization": f"Bearer {token}"}



class TestBookingAvailabilityCheck:
    """Tests for checking room availability."""

    def test_check_available_room(self, client, sample_room):
        """Test checking availability for a free room."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = datetime.utcnow() + timedelta(hours=2)
        
        response = client.get(
            f"/bookings/check?room_id={sample_room.id}"
            f"&start_time={start.isoformat()}"
            f"&end_time={end.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is True
        assert data["room_id"] == sample_room.id

    def test_check_unavailable_room(self, client, sample_room, sample_booking):
        """Test checking availability for a booked room."""
        # Try to book at the same time as existing booking
        start = sample_booking.start_time
        end = sample_booking.end_time
        
        response = client.get(
            f"/bookings/check?room_id={sample_room.id}"
            f"&start_time={start.isoformat()}"
            f"&end_time={end.isoformat()}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["available"] is False

    def test_check_overlapping_booking(self, client, sample_room, sample_booking):
        """Test checking availability with partial time overlap."""
        # Start before existing booking, end during it
        start = sample_booking.start_time - timedelta(minutes=30)
        end = sample_booking.start_time + timedelta(minutes=30)
        
        response = client.get(
            f"/bookings/check?room_id={sample_room.id}"
            f"&start_time={start.isoformat()}"
            f"&end_time={end.isoformat()}"
        )
        assert response.status_code == 200
        assert response.json()["available"] is False

    def test_check_nonexistent_room(self, client):
        """Test checking availability for nonexistent room."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = datetime.utcnow() + timedelta(hours=2)
        
        response = client.get(
            f"/bookings/check?room_id=99999"
            f"&start_time={start.isoformat()}"
            f"&end_time={end.isoformat()}"
        )
        assert response.status_code == 404


class TestBookingCreation:
    """Tests for booking creation endpoint."""

    def test_create_booking_success(self, client, regular_user, sample_room, regular_token):
        """Test successful booking creation."""
        start = datetime.utcnow() + timedelta(hours=3)
        end = datetime.utcnow() + timedelta(hours=4)
        
        response = client.post(
            "/bookings/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == sample_room.id
        assert data["user_id"] == regular_user.id
        assert "id" in data

    def test_create_booking_requires_auth(self, client, sample_room):
        """Test creating booking without authentication fails."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = datetime.utcnow() + timedelta(hours=2)
        
        response = client.post(
            "/bookings/",
            json={
                "room_id": sample_room.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )
        assert response.status_code == 401

    def test_create_booking_nonexistent_room(self, client, regular_user, regular_token):
        """Test booking nonexistent room fails."""
        start = datetime.utcnow() + timedelta(hours=1)
        end = datetime.utcnow() + timedelta(hours=2)
        
        response = client.post(
            "/bookings/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": 99999,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )
        assert response.status_code == 404

    def test_create_overlapping_booking_regular_user(
        self, client, regular_user, sample_room, sample_booking, regular_token
    ):
        """Test regular user cannot create overlapping booking."""
        # Try to book same time as existing booking
        response = client.post(
            "/bookings/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "start_time": sample_booking.start_time.isoformat(),
                "end_time": sample_booking.end_time.isoformat(),
            },
        )
        assert response.status_code == 400
        assert "already booked" in response.json()["detail"]

    def test_admin_can_override_booking_conflict(
        self, client, admin_user, sample_room, sample_booking, admin_token
    ):
        """Test admin can override booking conflicts."""
        # Admin should be able to book over existing booking
        response = client.post(
            "/bookings/",
            headers=get_auth_header(admin_token),
            json={
                "room_id": sample_room.id,
                "start_time": sample_booking.start_time.isoformat(),
                "end_time": sample_booking.end_time.isoformat(),
            },
        )
        assert response.status_code == 200

    def test_create_adjacent_bookings(self, client, regular_user, sample_room, regular_token):
        """Test creating back-to-back bookings (should succeed)."""
        start1 = datetime.utcnow() + timedelta(hours=5)
        end1 = datetime.utcnow() + timedelta(hours=6)
        start2 = end1  # Start exactly when first ends
        end2 = datetime.utcnow() + timedelta(hours=7)
        
        # Create first booking
        response1 = client.post(
            "/bookings/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "start_time": start1.isoformat(),
                "end_time": end1.isoformat(),
            },
        )
        assert response1.status_code == 200
        
        # Create adjacent booking (should succeed - no overlap)
        response2 = client.post(
            "/bookings/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "start_time": start2.isoformat(),
                "end_time": end2.isoformat(),
            },
        )
        assert response2.status_code == 200


class TestBookingListing:
    """Tests for listing bookings endpoint."""

    def test_admin_list_all_bookings(
        self, client, admin_user, regular_user, sample_booking, admin_token
    ):
        """Test admin can see all bookings."""
        response = client.get(
            "/bookings/",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        bookings = response.json()
        assert len(bookings) >= 1

    def test_facility_manager_list_all_bookings(
        self, client, facility_manager, sample_booking, facility_token
    ):
        """Test facility manager can see all bookings."""
        response = client.get(
            "/bookings/",
            headers=get_auth_header(facility_token),
        )
        assert response.status_code == 200
        bookings = response.json()
        assert len(bookings) >= 1

    def test_regular_user_list_own_bookings(
        self, client, regular_user, sample_booking, regular_token, db_session, admin_user, sample_room
    ):
        """Test regular user only sees their own bookings."""
        # Create a booking by admin
        from app import models
        admin_booking = models.Booking(
            user_id=admin_user.id,
            room_id=sample_room.id,
            start_time=datetime.utcnow() + timedelta(hours=10),
            end_time=datetime.utcnow() + timedelta(hours=11),
        )
        db_session.add(admin_booking)
        db_session.commit()
        
        response = client.get(
            "/bookings/",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 200
        bookings = response.json()
        # Should only see their own booking
        assert all(b["user_id"] == regular_user.id for b in bookings)

    def test_list_bookings_requires_auth(self, client):
        """Test listing bookings requires authentication."""
        response = client.get("/bookings/")
        assert response.status_code == 401


class TestBookingUpdate:
    """Tests for booking update endpoint."""

    def test_user_update_own_booking(
        self, client, regular_user, sample_booking, sample_rooms, regular_token
    ):
        """Test user can update their own booking."""
        new_start = datetime.utcnow() + timedelta(hours=5)
        new_end = datetime.utcnow() + timedelta(hours=6)
        
        response = client.patch(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_booking.room_id,
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_booking.id

    def test_admin_update_any_booking(
        self, client, admin_user, sample_booking, admin_token
    ):
        """Test admin can update any booking."""
        new_start = datetime.utcnow() + timedelta(hours=7)
        new_end = datetime.utcnow() + timedelta(hours=8)
        
        response = client.patch(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(admin_token),
            json={
                "room_id": sample_booking.room_id,
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
            },
        )
        assert response.status_code == 200

    def test_user_cannot_update_others_booking(
        self, client, regular_user, sample_booking, db_session, admin_user, sample_room
    ):
        """Test user cannot update another user's booking."""
        # Create another regular user
        from app.deps import get_password_hash
        from app import models
        
        other_user = models.User(
            name="Other User",
            username="otheruser",
            email="other@example.com",
            hashed_password=get_password_hash("otherpass123"),
            role="regular",
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Login as other user
        login_response = client.post(
            "/users/login",
            params={"username": "otheruser", "password": "otherpass123"},
        )
        other_token = login_response.json()["access_token"]
        
        # Try to update regular_user's booking
        new_start = datetime.utcnow() + timedelta(hours=9)
        new_end = datetime.utcnow() + timedelta(hours=10)
        
        response = client.patch(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(other_token),
            json={
                "room_id": sample_booking.room_id,
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
            },
        )
        assert response.status_code == 403

    def test_update_booking_with_conflict(
        self, client, regular_user, sample_room, regular_token, db_session
    ):
        """Test updating booking that would create conflict fails for regular user."""
        from app import models
        
        # Create two bookings
        booking1 = models.Booking(
            user_id=regular_user.id,
            room_id=sample_room.id,
            start_time=datetime.utcnow() + timedelta(hours=1),
            end_time=datetime.utcnow() + timedelta(hours=2),
        )
        booking2 = models.Booking(
            user_id=regular_user.id,
            room_id=sample_room.id,
            start_time=datetime.utcnow() + timedelta(hours=3),
            end_time=datetime.utcnow() + timedelta(hours=4),
        )
        db_session.add(booking1)
        db_session.add(booking2)
        db_session.commit()
        db_session.refresh(booking1)
        db_session.refresh(booking2)
        
        # Try to update booking2 to overlap with booking1
        response = client.patch(
            f"/bookings/{booking2.id}",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "start_time": booking1.start_time.isoformat(),
                "end_time": booking1.end_time.isoformat(),
            },
        )
        assert response.status_code == 400

    def test_update_nonexistent_booking(self, client, regular_user, regular_token):
        """Test updating nonexistent booking returns 404."""
        new_start = datetime.utcnow() + timedelta(hours=1)
        new_end = datetime.utcnow() + timedelta(hours=2)
        
        response = client.patch(
            "/bookings/99999",
            headers=get_auth_header(regular_token),
            json={
                "room_id": 1,
                "start_time": new_start.isoformat(),
                "end_time": new_end.isoformat(),
            },
        )
        assert response.status_code == 404


class TestBookingDeletion:
    """Tests for booking cancellation endpoint."""

    def test_user_cancel_own_booking(
        self, client, regular_user, sample_booking, regular_token
    ):
        """Test user can cancel their own booking."""
        response = client.delete(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 200
        assert "cancelled" in response.json()["detail"].lower()

    def test_admin_cancel_any_booking(
        self, client, admin_user, sample_booking, admin_token
    ):
        """Test admin can cancel any booking."""
        response = client.delete(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200

    def test_user_cannot_cancel_others_booking(
        self, client, regular_user, sample_booking, db_session
    ):
        """Test user cannot cancel another user's booking."""
        from app.deps import get_password_hash
        from app import models
        
        # Create another user
        other_user = models.User(
            name="Other User",
            username="otheruser2",
            email="other2@example.com",
            hashed_password=get_password_hash("otherpass123"),
            role="regular",
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Login as other user
        login_response = client.post(
            "/users/login",
            params={"username": "otheruser2", "password": "otherpass123"},
        )
        other_token = login_response.json()["access_token"]
        
        # Try to cancel regular_user's booking
        response = client.delete(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(other_token),
        )
        assert response.status_code == 403

    def test_delete_nonexistent_booking(self, client, regular_user, regular_token):
        """Test deleting nonexistent booking returns 404."""
        response = client.delete(
            "/bookings/99999",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 404

    def test_facility_manager_cannot_cancel_others_booking(
        self, client, facility_manager, sample_booking, facility_token
    ):
        """Test facility manager cannot cancel other users' bookings."""
        response = client.delete(
            f"/bookings/{sample_booking.id}",
            headers=get_auth_header(facility_token),
        )
        assert response.status_code == 403