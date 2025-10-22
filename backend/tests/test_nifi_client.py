"""Tests for NiFi client."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.nifi_client import NiFiClient, NiFiAPIError
from app.models import ProcessGroupDetail


@pytest.fixture
def nifi_client():
    """Create a test NiFi client."""
    return NiFiClient(base_url="http://test-nifi:8080/nifi-api")


@pytest.mark.asyncio
async def test_health_check_success(nifi_client):
    """Test successful health check."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.json.return_value = {"about": {"version": "1.0.0"}}
        mock_get.return_value = mock_response
        
        result = await nifi_client.health_check()
        
        assert result["available"] is True
        assert "data" in result


@pytest.mark.asyncio
async def test_health_check_failure(nifi_client):
    """Test failed health check."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = Exception("Connection refused")
        
        result = await nifi_client.health_check()
        
        assert result["available"] is False
        assert "error" in result


@pytest.mark.asyncio
async def test_get_root_process_group_id(nifi_client):
    """Test getting root process group ID."""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.raise_for_status = AsyncMock()
        mock_response.json.return_value = {
            "processGroupFlow": {
                "id": "root-id"
            }
        }
        mock_get.return_value = mock_response
        
        result = await nifi_client.get_root_process_group_id()
        
        assert result == "root-id"


@pytest.mark.asyncio
async def test_get_process_group_hierarchy_no_children(nifi_client):
    """Test getting process group hierarchy with no children."""
    with patch("httpx.AsyncClient.get") as mock_get:
        # Mock process group details
        pg_response = AsyncMock()
        pg_response.raise_for_status = AsyncMock()
        pg_response.json.return_value = {
            "component": {
                "id": "pg-1",
                "name": "Test Group",
                "parentGroupId": "root"
            },
            "runningCount": 2,
            "stoppedCount": 1
        }
        
        # Mock flow (no children)
        flow_response = AsyncMock()
        flow_response.raise_for_status = AsyncMock()
        flow_response.json.return_value = {
            "processGroupFlow": {
                "flow": {
                    "processGroups": []
                }
            }
        }
        
        mock_get.side_effect = [pg_response, flow_response]
        
        result = await nifi_client.get_process_group_hierarchy("pg-1")
        
        assert isinstance(result, ProcessGroupDetail)
        assert result.id == "pg-1"
        assert result.name == "Test Group"
        assert len(result.children) == 0


@pytest.mark.asyncio  
async def test_get_process_group_hierarchy_with_children(nifi_client):
    """Test getting process group hierarchy with children."""
    with patch("httpx.AsyncClient.get") as mock_get:
        # Parent group
        parent_pg_response = AsyncMock()
        parent_pg_response.raise_for_status = AsyncMock()
        parent_pg_response.json.return_value = {
            "component": {
                "id": "parent-1",
                "name": "Parent Group",
            },
            "runningCount": 3
        }
        
        # Parent flow with one child
        parent_flow_response = AsyncMock()
        parent_flow_response.raise_for_status = AsyncMock()
        parent_flow_response.json.return_value = {
            "processGroupFlow": {
                "flow": {
                    "processGroups": [
                        {"id": "child-1", "component": {"name": "Child Group"}}
                    ]
                }
            }
        }
        
        # Child group
        child_pg_response = AsyncMock()
        child_pg_response.raise_for_status = AsyncMock()
        child_pg_response.json.return_value = {
            "component": {
                "id": "child-1",
                "name": "Child Group",
                "parentGroupId": "parent-1"
            },
            "runningCount": 1
        }
        
        # Child flow (no children)
        child_flow_response = AsyncMock()
        child_flow_response.raise_for_status = AsyncMock()
        child_flow_response.json.return_value = {
            "processGroupFlow": {
                "flow": {
                    "processGroups": []
                }
            }
        }
        
        mock_get.side_effect = [
            parent_pg_response,
            parent_flow_response,
            child_pg_response,
            child_flow_response
        ]
        
        result = await nifi_client.get_process_group_hierarchy("parent-1")
        
        assert result.id == "parent-1"
        assert result.name == "Parent Group"
        assert len(result.children) == 1
        assert result.children[0].id == "child-1"
        assert result.children[0].name == "Child Group"

