"""
Unit tests for review management endpoints.
"""
import pytest


def get_auth_header(token: str) -> dict:
    """Helper function to create authorization header."""
    return {"Authorization": f"Bearer {token}"}



class TestReviewCreation:
    """Tests for review creation endpoint."""

    def test_create_review_success(self, client, regular_user, sample_room, regular_token):
        """Test successful review creation."""
        response = client.post(
            "/reviews/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "rating": 5,
                "comment": "Excellent room!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["room_id"] == sample_room.id
        assert data["user_id"] == regular_user.id
        assert data["rating"] == 5
        assert data["comment"] == "Excellent room!"
        assert data["flagged"] is False
        assert data["deleted"] is False

    def test_create_review_without_comment(self, client, regular_user, sample_room, regular_token):
        """Test creating review without optional comment."""
        response = client.post(
            "/reviews/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": sample_room.id,
                "rating": 4,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
        assert data["comment"] is None

    def test_create_review_requires_auth(self, client, sample_room):
        """Test creating review without authentication fails."""
        response = client.post(
            "/reviews/",
            json={
                "room_id": sample_room.id,
                "rating": 5,
                "comment": "Great!",
            },
        )
        assert response.status_code == 401

    def test_create_review_nonexistent_room(self, client, regular_user, regular_token):
        """Test creating review for nonexistent room fails."""
        response = client.post(
            "/reviews/",
            headers=get_auth_header(regular_token),
            json={
                "room_id": 99999,
                "rating": 5,
                "comment": "Great!",
            },
        )
        assert response.status_code == 404

    def test_admin_create_review(self, client, admin_user, sample_room, admin_token):
        """Test admin can create reviews."""
        response = client.post(
            "/reviews/",
            headers=get_auth_header(admin_token),
            json={
                "room_id": sample_room.id,
                "rating": 3,
                "comment": "Admin review",
            },
        )
        assert response.status_code == 200

    def test_facility_manager_create_review(
        self, client, facility_manager, sample_room, facility_token
    ):
        """Test facility manager can create reviews."""
        response = client.post(
            "/reviews/",
            headers=get_auth_header(facility_token),
            json={
                "room_id": sample_room.id,
                "rating": 4,
                "comment": "FM review",
            },
        )
        assert response.status_code == 200


class TestReviewRetrieval:
    """Tests for retrieving reviews by room."""

    def test_get_reviews_for_room(self, client, sample_review, sample_room):
        """Test getting reviews for a specific room."""
        response = client.get(f"/reviews/room/{sample_room.id}")
        assert response.status_code == 200
        reviews = response.json()
        assert len(reviews) >= 1
        assert all(r["room_id"] == sample_room.id for r in reviews)

    def test_get_reviews_excludes_deleted(self, client, sample_review, sample_room, db_session):
        """Test that deleted reviews are not returned."""
        # Mark review as deleted
        sample_review.deleted = True
        db_session.commit()
        
        response = client.get(f"/reviews/room/{sample_room.id}")
        assert response.status_code == 200
        reviews = response.json()
        # Should not include the deleted review
        assert not any(r["id"] == sample_review.id for r in reviews)

    def test_get_reviews_includes_flagged(self, client, sample_review, sample_room, db_session):
        """Test that flagged (but not deleted) reviews are still returned."""
        # Flag the review
        sample_review.flagged = True
        db_session.commit()
        
        response = client.get(f"/reviews/room/{sample_room.id}")
        assert response.status_code == 200
        reviews = response.json()
        # Should still include the flagged review
        flagged_review = next((r for r in reviews if r["id"] == sample_review.id), None)
        assert flagged_review is not None
        assert flagged_review["flagged"] is True

    def test_get_reviews_no_auth_required(self, client, sample_room):
        """Test getting reviews doesn't require authentication."""
        response = client.get(f"/reviews/room/{sample_room.id}")
        assert response.status_code == 200

    def test_get_reviews_empty_room(self, client, sample_room):
        """Test getting reviews for room with no reviews."""
        # Create a new room with no reviews
        from app import models
        db_session = next(iter([sample_room]))  # Get db_session from fixture
        # Actually, we'll just use a room ID that has no reviews
        response = client.get("/reviews/room/99999")
        assert response.status_code == 200
        assert response.json() == []


class TestReviewUpdate:
    """Tests for review update endpoint."""

    def test_user_update_own_review(
        self, client, regular_user, sample_review, regular_token
    ):
        """Test user can update their own review."""
        response = client.patch(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(regular_token),
            json={
                "rating": 4,
                "comment": "Updated comment",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 4
        assert data["comment"] == "Updated comment"

    def test_admin_update_any_review(
        self, client, admin_user, sample_review, admin_token
    ):
        """Test admin can update any review."""
        response = client.patch(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(admin_token),
            json={
                "rating": 3,
                "comment": "Admin updated",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 3

    def test_user_cannot_update_others_review(
        self, client, sample_review, db_session
    ):
        """Test user cannot update another user's review."""
        from app.deps import get_password_hash
        from app import models
        
        # Create another user
        other_user = models.User(
            name="Other User",
            username="otheruser3",
            email="other3@example.com",
            hashed_password=get_password_hash("otherpass123"),
            role="regular",
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Login as other user
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        
        login_response = client.post(
            "/users/login",
            params={"username": "otheruser3", "password": "otherpass123"},
        )
        other_token = login_response.json()["access_token"]
        
        # Try to update sample_review
        response = client.patch(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(other_token),
            json={"rating": 1},
        )
        assert response.status_code == 403

    def test_partial_review_update(
        self, client, regular_user, sample_review, regular_token
    ):
        """Test partial update of review (only rating or only comment)."""
        original_comment = sample_review.comment
        
        response = client.patch(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(regular_token),
            json={"rating": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 3
        assert data["comment"] == original_comment

    def test_cannot_update_deleted_review(
        self, client, regular_user, sample_review, regular_token, db_session
    ):
        """Test cannot update a deleted review."""
        # Mark review as deleted
        sample_review.deleted = True
        db_session.commit()
        
        response = client.patch(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(regular_token),
            json={"rating": 5},
        )
        assert response.status_code == 400
        assert "deleted review" in response.json()["detail"]

    def test_update_nonexistent_review(self, client, regular_user, regular_token):
        """Test updating nonexistent review returns 404."""
        response = client.patch(
            "/reviews/99999",
            headers=get_auth_header(regular_token),
            json={"rating": 5},
        )
        assert response.status_code == 404


class TestReviewDeletion:
    """Tests for review soft-deletion endpoint."""

    def test_user_delete_own_review(
        self, client, regular_user, sample_review, regular_token, db_session
    ):
        """Test user can delete their own review (soft delete)."""
        response = client.delete(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 200
        assert "removed" in response.json()["detail"].lower()
        
        # Verify it's soft deleted
        db_session.refresh(sample_review)
        assert sample_review.deleted is True

    def test_admin_delete_any_review(
        self, client, admin_user, sample_review, admin_token, db_session
    ):
        """Test admin can delete any review."""
        response = client.delete(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        
        db_session.refresh(sample_review)
        assert sample_review.deleted is True

    def test_user_cannot_delete_others_review(
        self, client, sample_review, db_session
    ):
        """Test user cannot delete another user's review."""
        from app.deps import get_password_hash
        from app import models
        
        # Create another user
        other_user = models.User(
            name="Other User",
            username="otheruser4",
            email="other4@example.com",
            hashed_password=get_password_hash("otherpass123"),
            role="regular",
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Login as other user
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        
        login_response = client.post(
            "/users/login",
            params={"username": "otheruser4", "password": "otherpass123"},
        )
        other_token = login_response.json()["access_token"]
        
        response = client.delete(
            f"/reviews/{sample_review.id}",
            headers=get_auth_header(other_token),
        )
        assert response.status_code == 403

    def test_delete_nonexistent_review(self, client, regular_user, regular_token):
        """Test deleting nonexistent review returns 404."""
        response = client.delete(
            "/reviews/99999",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 404


class TestReviewModeration:
    """Tests for admin review moderation endpoints."""

    def test_admin_restore_review(
        self, client, admin_user, sample_review, admin_token, db_session
    ):
        """Test admin can restore a deleted review."""
        # First delete the review
        sample_review.deleted = True
        db_session.commit()
        
        # Now restore it
        response = client.post(
            f"/reviews/{sample_review.id}/restore",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        assert "restored" in response.json()["detail"].lower()
        
        db_session.refresh(sample_review)
        assert sample_review.deleted is False

    def test_regular_user_cannot_restore_review(
        self, client, regular_user, sample_review, regular_token, db_session
    ):
        """Test regular user cannot restore reviews."""
        sample_review.deleted = True
        db_session.commit()
        
        response = client.post(
            f"/reviews/{sample_review.id}/restore",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_facility_manager_cannot_restore_review(
        self, client, facility_manager, sample_review, facility_token, db_session
    ):
        """Test facility manager cannot restore reviews."""
        sample_review.deleted = True
        db_session.commit()
        
        response = client.post(
            f"/reviews/{sample_review.id}/restore",
            headers=get_auth_header(facility_token),
        )
        assert response.status_code == 403

    def test_admin_flag_review(
        self, client, admin_user, sample_review, admin_token, db_session
    ):
        """Test admin can flag a review for moderation."""
        response = client.post(
            f"/reviews/{sample_review.id}/flag",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        assert "flagged" in response.json()["detail"].lower()
        
        db_session.refresh(sample_review)
        assert sample_review.flagged is True

    def test_admin_unflag_review(
        self, client, admin_user, sample_review, admin_token, db_session
    ):
        """Test admin can unflag a review."""
        # First flag it
        sample_review.flagged = True
        db_session.commit()
        
        # Now unflag
        response = client.post(
            f"/reviews/{sample_review.id}/unflag",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 200
        assert "unflagged" in response.json()["detail"].lower()
        
        db_session.refresh(sample_review)
        assert sample_review.flagged is False

    def test_regular_user_cannot_flag_review(
        self, client, regular_user, sample_review, regular_token
    ):
        """Test regular user cannot flag reviews."""
        response = client.post(
            f"/reviews/{sample_review.id}/flag",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_regular_user_cannot_unflag_review(
        self, client, regular_user, sample_review, regular_token, db_session
    ):
        """Test regular user cannot unflag reviews."""
        sample_review.flagged = True
        db_session.commit()
        
        response = client.post(
            f"/reviews/{sample_review.id}/unflag",
            headers=get_auth_header(regular_token),
        )
        assert response.status_code == 403

    def test_flag_nonexistent_review(self, client, admin_user, admin_token):
        """Test flagging nonexistent review returns 404."""
        response = client.post(
            "/reviews/99999/flag",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 404

    def test_restore_nonexistent_review(self, client, admin_user, admin_token):
        """Test restoring nonexistent review returns 404."""
        response = client.post(
            "/reviews/99999/restore",
            headers=get_auth_header(admin_token),
        )
        assert response.status_code == 404