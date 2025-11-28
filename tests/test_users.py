"""
Unit tests for user management endpoints.
"""
import pytest


def get_auth_header(token: str) -> dict:
    """Helper function to create authorization header."""
    return {"Authorization": f"Bearer {token}"}



class TestUserRegistration:
    """Tests for user registration endpoint."""

    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/users/register",
            json={
                "name": "New User",
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "newpass123",
                "role": "regular",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["role"] == "regular"
        assert "id" in data
        assert "hashed_password" not in data

    def test_register_duplicate_username(self, client, regular_user):
        """Test registration with duplicate username fails."""
        response = client.post(
            "/users/register",
            json={
                "name": "Another User",
                "username": "regularuser",
                "email": "another@example.com",
                "password": "pass123",
                "role": "regular",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_duplicate_email(self, client, regular_user):
        """Test registration with duplicate email fails."""
        response = client.post(
            "/users/register",
            json={
                "name": "Another User",
                "username": "anotheruser",
                "email": "regular@example.com",
                "password": "pass123",
                "role": "regular",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_register_facility_manager(self, client):
        """Test registration of facility manager user."""
        response = client.post(
            "/users/register",
            json={
                "name": "Facility Manager",
                "username": "fm_user",
                "email": "fm@example.com",
                "password": "fmpass123",
                "role": "facility_manager",
            },
        )
        assert response.status_code == 200
        assert response.json()["role"] == "facility_manager"


class TestUserLogin:
    """Tests for user login endpoint."""

    def test_login_success(self, client, admin_user):
        """Test successful login."""
        response = client.post(
            "/users/login",
            params={"username": "admin", "password": "adminpass123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, admin_user):
        """Test login with wrong password fails."""
        response = client.post(
            "/users/login",
            params={"username": "admin", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user fails."""
        response = client.post(
            "/users/login",
            params={"username": "nonexistent", "password": "anypassword"},
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for current user endpoints."""

    def test_get_current_user(self, client, admin_user, admin_token):
        """Test getting current user information."""
        response = client.get(
            "/users/me",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "admin"
        assert data["email"] == "admin@example.com"
        assert data["role"] == "admin"

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication fails."""
        response = client.get("/users/me")
        assert response.status_code == 401

    def test_update_current_user(self, client, regular_user, regular_token):
        """Test updating current user's own profile."""
        response = client.patch(
            "/users/me",
            headers=get_auth_header(regular_token),
            json={"name": "Updated Name", "email": "updated@example.com"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == "updated@example.com"

    def test_regular_user_cannot_change_role(self, client, regular_user, regular_token):
        """Test that regular user cannot change their own role."""
        response = client.patch(
            "/users/me",
            headers=get_auth_header(regular_token),
            json={"role": "admin"},
        )
        assert response.status_code == 403
        assert "Not allowed to change your role" in response.json()["detail"]

    def test_admin_can_change_own_role(self, client, admin_user, admin_token):
        """Test that admin can change their own role."""
        response = client.patch(
            "/users/me",
            headers=get_auth_header(admin_token),
            json={"role": "regular"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "regular"


class TestUserManagement:
    """Tests for admin user management endpoints."""

    def test_admin_list_users(self, client, admin_user, regular_user, admin_token):
        """Test admin can list all users."""
        response = client.get(
            "/users/",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 2
        usernames = [u["username"] for u in users]
        assert "admin" in usernames
        assert "regularuser" in usernames

    def test_regular_user_cannot_list_users(self, client, regular_user, regular_token):
        """Test regular user cannot list all users."""
        response = client.get(
            "/users/",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_admin_get_specific_user(self, client, admin_user, regular_user, admin_token):
        """Test admin can get specific user details."""
        response = client.get(
            "/users/regularuser",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "regularuser"
        assert data["email"] == "regular@example.com"

    def test_admin_get_nonexistent_user(self, client, admin_user, admin_token):
        """Test getting nonexistent user returns 404."""
        response = client.get(
            "/users/nonexistent",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 404

    def test_admin_update_user(self, client, admin_user, regular_user, admin_token):
        """Test admin can update any user."""
        response = client.patch(
            "/users/regularuser",
            headers=get_auth_header(admin_token),
            json={"name": "Admin Updated Name", "role": "facility_manager"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Admin Updated Name"
        assert data["role"] == "facility_manager"

    def test_regular_user_update_other_user(self, client, admin_user, regular_user, regular_token):
        """Test regular user cannot update other users."""
        response = client.patch(
            "/users/admin",
            headers=get_auth_header(regular_token),
            json={"name": "Hacked Name"},
        )
        assert response.status_code == 403

    def test_regular_user_update_own_profile(self, client, regular_user, regular_token):
        """Test regular user can update their own profile."""
        response = client.patch(
            "/users/regularuser",
            headers=get_auth_header(regular_token),
            json={"name": "Self Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Self Updated Name"

    def test_admin_reset_password(self, client, admin_user, regular_user, admin_token):
        """Test admin can reset user password."""
        response = client.post(
            "/users/regularuser/reset-password",
            headers=get_auth_header(admin_token),
            json={"new_password": "newpassword123"},
        )
        assert response.status_code == 200
        assert "Password reset successfully" in response.json()["detail"]

        # Verify user can login with new password
        login_response = client.post(
            "/users/login",
            params={"username": "regularuser", "password": "newpassword123"},
        )
        assert login_response.status_code == 200

    def test_regular_user_cannot_reset_password(self, client, admin_user, regular_user, regular_token):
        """Test regular user cannot reset passwords."""
        response = client.post(
            "/users/admin/reset-password",
            headers=get_auth_header(regular_token),
            json={"new_password": "hackedpassword"},
        )
        assert response.status_code == 403

    def test_admin_delete_user(self, client, admin_user, regular_user, admin_token):
        """Test admin can delete users."""
        response = client.delete(
            "/users/regularuser",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        assert "User deleted" in response.json()["detail"]

        # Verify user is deleted
        get_response = client.get(
            "/users/regularuser",
            headers=get_auth_header(admin_token),
        )
        assert get_response.status_code == 404

    def test_regular_user_cannot_delete_user(self, client, admin_user, regular_user, regular_token):
        """Test regular user cannot delete users."""
        response = client.delete(
            "/users/admin",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403


class TestUserBookingHistory:
    """Tests for user booking history endpoint."""

    def test_admin_get_user_booking_history(
        self, client, admin_user, regular_user, sample_booking, admin_token
    ):
        """Test admin can view user booking history."""
        response = client.get(
            "/users/regularuser/bookings",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        bookings = response.json()
        assert len(bookings) >= 1
        assert bookings[0]["user_id"] == regular_user.id

    def test_regular_user_cannot_view_others_bookings(
        self, client, admin_user, regular_user, admin_token, regular_token
    ):
        """Test regular user cannot view other users' booking history."""
        response = client.get(
            "/users/admin/bookings",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_admin_get_nonexistent_user_bookings(self, client, admin_user, admin_token):
        """Test getting bookings for nonexistent user returns 404."""
        response = client.get(
            "/users/nonexistent/bookings",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 404