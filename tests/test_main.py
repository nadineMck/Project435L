"""
Unit tests for main application endpoints.
"""
import pytest


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_health_check_no_auth_required(self, client):
        """Test health check doesn't require authentication."""
        response = client.get("/health")
        assert response.status_code == 200


class TestApplicationSetup:
    """Tests for application configuration."""

    def test_app_title(self, client):
        """Test that the app has correct title."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi = response.json()
        assert "Smart Meeting Room Backend" in openapi["info"]["title"]

    def test_docs_endpoint_exists(self, client):
        """Test that API documentation endpoint is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_endpoint_exists(self, client):
        """Test that ReDoc documentation endpoint is accessible."""
        response = client.get("/redoc")
        assert response.status_code == 200