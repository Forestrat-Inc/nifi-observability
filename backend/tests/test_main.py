"""Tests for main API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app
from app.models import ProcessGroupDetail, FlowStatus


client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns health check."""
    with patch("app.main.nifi_client.health_check") as mock_health:
        mock_health.return_value = {"available": True}
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "nifi_available" in data


def test_health_endpoint():
    """Test health check endpoint."""
    with patch("app.main.nifi_client.health_check") as mock_health:
        mock_health.return_value = {"available": True}
        
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["nifi_available"] is True


def test_get_all_process_groups():
    """Test getting all process groups."""
    mock_pg = ProcessGroupDetail(
        id="root",
        name="NiFi Flow",
        children=[]
    )
    
    with patch("app.main.nifi_client.get_all_process_groups_hierarchy") as mock_get:
        mock_get.return_value = mock_pg
        
        response = client.get("/api/process-groups")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "root"
        assert data["name"] == "NiFi Flow"


def test_get_flow_status():
    """Test getting flow status."""
    mock_status = FlowStatus()
    
    with patch("app.main.nifi_client.get_flow_status") as mock_get:
        mock_get.return_value = mock_status
        
        response = client.get("/api/flow/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_thread_count" in data

