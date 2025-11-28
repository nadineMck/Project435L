"""
Unit tests for room management endpoints.
"""
import pytest


def get_auth_header(token: str) -> dict:
    """Helper function to create authorization header."""
    return {"Authorization": f"Bearer {token}"}



class TestRoomCreation:
    """Tests for room creation endpoint."""

    def test_admin_create_room(self, client, admin_user, admin_token):
        """Test admin can create a room."""
        response = client.post(
            "/rooms/",
            headers=get_auth_header(admin_token),
            json={
                "name": "Test Room",
                "capacity": 20,
                "equipment": "Projector, Whiteboard",
                "location": "Building 1, Floor 1",
                "is_available": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Room"
        assert data["capacity"] == 20
        assert data["equipment"] == "Projector, Whiteboard"
        assert data["is_available"] is True

    def test_facility_manager_create_room(self, client, facility_manager, facility_token):
        """Test facility manager can create a room."""
        response = client.post(
            "/rooms/",
            headers=get_auth_header(facility_token),
            json={
                "name": "FM Room",
                "capacity": 15,
                "equipment": "TV",
                "location": "Building 2, Floor 1",
            },
        )
        assert response.status_code == 200
        assert response.json()["name"] == "FM Room"

    def test_regular_user_cannot_create_room(self, client, regular_user, regular_token):
        """Test regular user cannot create a room."""
        response = client.post(
            "/rooms/",
            headers=get_auth_header(regular_token),
            json={
                "name": "Unauthorized Room",
                "capacity": 10,
                "location": "Building 1",
            },
        )
        assert response.status_code == 403

    def test_create_duplicate_room_name(self, client, admin_user, sample_room, admin_token):
        """Test creating room with duplicate name fails."""
        response = client.post(
            "/rooms/",
            headers=get_auth_header(admin_token),
            json={
                "name": "Conference Room A",
                "capacity": 10,
                "location": "Building 1",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_room_without_equipment(self, client, admin_user, admin_token):
        """Test creating room without equipment (optional field)."""
        response = client.post(
            "/rooms/",
            headers=get_auth_header(admin_token),
            json={
                "name": "Basic Room",
                "capacity": 5,
                "location": "Building 3",
            },
        )
        assert response.status_code == 200
        assert response.json()["equipment"] is None


class TestRoomListing:
    """Tests for room listing endpoint."""

    def test_list_all_rooms(self, client, sample_rooms):
        """Test listing all rooms without filters."""
        response = client.get("/rooms/")
        assert response.status_code == 200
        rooms = response.json()
        assert len(rooms) == 3

    def test_filter_by_min_capacity(self, client, sample_rooms):
        """Test filtering rooms by minimum capacity."""
        response = client.get("/rooms/?min_capacity=12")
        assert response.status_code == 200
        rooms = response.json()
        assert all(room["capacity"] >= 12 for room in rooms)
        assert len(rooms) == 2  # Large Conference Hall (50) and Board Room (12)

    def test_filter_by_location(self, client, sample_rooms):
        """Test filtering rooms by location."""
        response = client.get("/rooms/?location=Building 1, Floor 1")
        assert response.status_code == 200
        rooms = response.json()
        assert len(rooms) == 1
        assert rooms[0]["name"] == "Small Meeting Room"

    def test_filter_by_equipment(self, client, sample_rooms):
        """Test filtering rooms by equipment."""
        response = client.get("/rooms/?equipment_contains=Projector")
        assert response.status_code == 200
        rooms = response.json()
        assert all("Projector" in (room["equipment"] or "") for room in rooms)

    def test_filter_only_available(self, client, sample_rooms):
        """Test filtering only available rooms."""
        response = client.get("/rooms/?only_available=true")
        assert response.status_code == 200
        rooms = response.json()
        assert all(room["is_available"] is True for room in rooms)
        assert len(rooms) == 2  # Board Room is not available

    def test_combined_filters(self, client, sample_rooms):
        """Test using multiple filters together."""
        response = client.get(
            "/rooms/?min_capacity=10&only_available=true"
        )
        assert response.status_code == 200
        rooms = response.json()
        assert all(room["capacity"] >= 10 and room["is_available"] for room in rooms)

    def test_list_rooms_no_auth_required(self, client, sample_rooms):
        """Test listing rooms doesn't require authentication."""
        response = client.get("/rooms/")
        assert response.status_code == 200


class TestRoomRetrieval:
    """Tests for getting specific room endpoint."""

    def test_get_room_by_id(self, client, sample_room):
        """Test getting a room by ID."""
        response = client.get(f"/rooms/{sample_room.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_room.id
        assert data["name"] == sample_room.name

    def test_get_nonexistent_room(self, client):
        """Test getting nonexistent room returns 404."""
        response = client.get("/rooms/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRoomUpdate:
    """Tests for room update endpoint."""

    def test_admin_update_room(self, client, admin_user, sample_room, admin_token):
        """Test admin can update a room."""
        response = client.patch(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(admin_token),
            json={
                "capacity": 15,
                "equipment": "Updated Equipment",
                "is_available": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["capacity"] == 15
        assert data["equipment"] == "Updated Equipment"
        assert data["is_available"] is False

    def test_facility_manager_update_room(
        self, client, facility_manager, sample_room, facility_token
    ):
        """Test facility manager can update a room."""
        response = client.patch(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(facility_token),
            json={"location": "New Location"},
        )
        assert response.status_code == 200
        assert response.json()["location"] == "New Location"

    def test_regular_user_cannot_update_room(
        self, client, regular_user, sample_room, regular_token
    ):
        """Test regular user cannot update a room."""
        response = client.patch(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(regular_token),
            json={"capacity": 100},
        )
        assert response.status_code == 403

    def test_update_nonexistent_room(self, client, admin_user, admin_token):
        """Test updating nonexistent room returns 404."""
        response = client.patch(
            "/rooms/99999",
            headers=get_auth_header(admin_token),
            json={"capacity": 20},
        )
        assert response.status_code == 404

    def test_partial_room_update(self, client, admin_user, sample_room, admin_token):
        """Test partial update of room (only some fields)."""
        original_name = sample_room.name
        response = client.patch(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(admin_token),
            json={"capacity": 25},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["capacity"] == 25
        assert data["name"] == original_name  # Unchanged


class TestRoomDeletion:
    """Tests for room deletion endpoint."""

    def test_admin_delete_room(self, client, admin_user, sample_room, admin_token):
        """Test admin can delete a room."""
        response = client.delete(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        assert "deleted" in response.json()["detail"].lower()

        # Verify room is deleted
        get_response = client.get(f"/rooms/{sample_room.id}")
        assert get_response.status_code == 404

    def test_facility_manager_delete_room(
        self, client, facility_manager, sample_room, facility_token
    ):
        """Test facility manager can delete a room."""
        response = client.delete(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(facility_token),
        )
        assert response.status_code == 200

    def test_regular_user_cannot_delete_room(
        self, client, regular_user, sample_room, regular_token
    ):
        """Test regular user cannot delete a room."""
        response = client.delete(
            f"/rooms/{sample_room.id}",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_delete_nonexistent_room(self, client, admin_user, admin_token):
        """Test deleting nonexistent room returns 404."""
        response = client.delete(
            "/rooms/99999",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 404