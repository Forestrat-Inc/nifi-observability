"""NiFi API client for interacting with Apache NiFi REST API."""

import logging
from typing import Any

import httpx

from app.config import settings
from app.models import ProcessGroupDetail, FlowStatus, Processor, Connection

logger = logging.getLogger(__name__)


class NiFiAPIError(Exception):
    """Custom exception for NiFi API errors."""
    pass


class NiFiClient:
    """Client for Apache NiFi REST API."""
    
    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        """
        Initialize the NiFi client.
        
        Args:
            base_url: Base URL for the NiFi API (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
        """
        self.base_url = (base_url or settings.nifi_api_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.auth = None
        
        if settings.nifi_username and settings.nifi_password:
            self.auth = (settings.nifi_username, settings.nifi_password)
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check if NiFi API is accessible.
        
        Returns:
            dict: Health check information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/flow/about",
                    auth=self.auth
                )
                response.raise_for_status()
                return {"available": True, "data": response.json()}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"available": False, "error": str(e)}
    
    async def get_root_process_group_id(self) -> str:
        """
        Get the root process group ID.
        
        Returns:
            str: Root process group ID
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/root",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                return data["processGroupFlow"]["id"]
        except Exception as e:
            logger.error(f"Failed to get root process group ID: {e}")
            raise NiFiAPIError(f"Failed to get root process group ID: {e}")
    
    async def get_process_group(self, group_id: str) -> dict[str, Any]:
        """
        Get a specific process group by ID.
        
        Args:
            group_id: The process group ID
            
        Returns:
            dict: Process group data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/process-groups/{group_id}",
                    auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting process group {group_id}: {e}")
            raise NiFiAPIError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to get process group {group_id}: {e}")
            raise NiFiAPIError(f"Failed to get process group: {e}")
    
    async def get_process_group_flow(self, group_id: str) -> dict[str, Any]:
        """
        Get the flow for a specific process group.
        
        Args:
            group_id: The process group ID
            
        Returns:
            dict: Process group flow data
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/{group_id}",
                    auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting process group flow {group_id}: {e}")
            raise NiFiAPIError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to get process group flow {group_id}: {e}")
            raise NiFiAPIError(f"Failed to get process group flow: {e}")
    
    async def get_process_group_status(self, group_id: str) -> dict[str, Any]:
        """
        Get the status of a specific process group.
        
        Args:
            group_id: The process group ID
            
        Returns:
            dict: Process group status
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/{group_id}/status",
                    auth=self.auth
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get process group status {group_id}: {e}")
            # Return empty status on error rather than failing
            return {}
    
    async def get_process_group_hierarchy(self, group_id: str, depth: int = 0, max_depth: int = 10) -> ProcessGroupDetail:
        """
        Recursively fetch process group hierarchy.
        
        Args:
            group_id: The process group ID to start from
            depth: Current recursion depth
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            ProcessGroupDetail: Process group with all children
        """
        if depth > max_depth:
            logger.warning(f"Max recursion depth reached for group {group_id}")
            raise NiFiAPIError("Max recursion depth reached")
        
        logger.info(f"Fetching process group {group_id} at depth {depth}")
        
        # Get the process group details
        pg_data = await self.get_process_group(group_id)
        component = pg_data.get("component", {})
        
        # Get the flow to find child process groups
        flow_data = await self.get_process_group_flow(group_id)
        flow = flow_data.get("processGroupFlow", {}).get("flow", {})
        
        # Extract processors from the flow
        processors = []
        for proc in flow.get("processors", []):
            proc_component = proc.get("component", {})
            try:
                processor = Processor(
                    id=proc_component.get("id", ""),
                    name=proc_component.get("name", "Unknown"),
                    type=proc_component.get("type", "Unknown"),
                    state=proc_component.get("state", "STOPPED"),
                    comments=proc_component.get("comments"),
                    style=proc_component.get("style"),
                    relationships=proc_component.get("relationships", []),
                    config=proc_component.get("config"),
                    inputRequirement=proc_component.get("inputRequirement")
                )
                processors.append(processor)
            except Exception as e:
                logger.warning(f"Failed to parse processor {proc_component.get('id')}: {e}")
        
        # Extract connections from the flow
        connections = []
        for conn in flow.get("connections", []):
            conn_component = conn.get("component", {})
            try:
                connection = Connection(
                    id=conn_component.get("id", ""),
                    name=conn_component.get("name"),
                    sourceId=conn_component.get("source", {}).get("id", ""),
                    sourceName=conn_component.get("source", {}).get("name"),
                    sourceType=conn_component.get("source", {}).get("type"),
                    destinationId=conn_component.get("destination", {}).get("id", ""),
                    destinationName=conn_component.get("destination", {}).get("name"),
                    destinationType=conn_component.get("destination", {}).get("type"),
                    selectedRelationships=conn_component.get("selectedRelationships", []),
                    backPressureDataSizeThreshold=conn_component.get("backPressureDataSizeThreshold"),
                    backPressureObjectThreshold=conn_component.get("backPressureObjectThreshold"),
                    flowFileExpiration=conn_component.get("flowFileExpiration")
                )
                connections.append(connection)
            except Exception as e:
                logger.warning(f"Failed to parse connection {conn_component.get('id')}: {e}")
        
        # Extract basic information
        pg_detail = ProcessGroupDetail(
            id=component.get("id", group_id),
            name=component.get("name", "Unknown"),
            comments=component.get("comments"),
            parentGroupId=component.get("parentGroupId"),
            versionControlInformation=component.get("versionControlInformation"),
            running_count=pg_data.get("runningCount", 0),
            stopped_count=pg_data.get("stoppedCount", 0),
            invalid_count=pg_data.get("invalidCount", 0),
            disabled_count=pg_data.get("disabledCount", 0),
            active_remote_port_count=pg_data.get("activeRemotePortCount", 0),
            inactive_remote_port_count=pg_data.get("inactiveRemotePortCount", 0),
            up_to_date_count=pg_data.get("upToDateCount", 0),
            locally_modified_count=pg_data.get("locallyModifiedCount", 0),
            stale_count=pg_data.get("staleCount", 0),
            locally_modified_and_stale_count=pg_data.get("locallyModifiedAndStaleCount", 0),
            sync_failure_count=pg_data.get("syncFailureCount", 0),
            input_port_count=pg_data.get("inputPortCount", 0),
            output_port_count=pg_data.get("outputPortCount", 0),
            processors=processors,
            connections=connections,
            children=[]
        )
        
        # Get child process groups
        child_groups = flow.get("processGroups", [])
        logger.info(f"Found {len(child_groups)} child groups, {len(processors)} processors, {len(connections)} connections in {pg_detail.name}")
        
        # Recursively fetch children
        for child_pg in child_groups:
            child_id = child_pg.get("id")
            if child_id:
                try:
                    child_detail = await self.get_process_group_hierarchy(
                        child_id, 
                        depth + 1,
                        max_depth
                    )
                    pg_detail.children.append(child_detail)
                except Exception as e:
                    logger.error(f"Failed to fetch child group {child_id}: {e}")
                    # Add a minimal child entry on error
                    pg_detail.children.append(ProcessGroupDetail(
                        id=child_id,
                        name=child_pg.get("component", {}).get("name", "Error Loading"),
                        comments=f"Error: {str(e)}",
                        children=[]
                    ))
        
        return pg_detail
    
    async def get_all_process_groups_hierarchy(self) -> ProcessGroupDetail:
        """
        Get all process groups starting from root with complete hierarchy.
        
        Returns:
            ProcessGroupDetail: Complete process group hierarchy
        """
        root_id = await self.get_root_process_group_id()
        return await self.get_process_group_hierarchy(root_id)
    
    async def get_flow_status(self) -> FlowStatus:
        """
        Get the overall flow status.
        
        Returns:
            FlowStatus: Flow status information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/flow/status",
                    auth=self.auth
                )
                response.raise_for_status()
                data = response.json()
                controller_status = data.get("controllerStatus", {})
                
                return FlowStatus(
                    activeThreadCount=controller_status.get("activeThreadCount", 0),
                    queued=controller_status.get("queued", "0"),
                    queuedSize=controller_status.get("queuedSize", "0 bytes"),
                    bytesQueued=controller_status.get("bytesQueued", 0),
                    flowFilesQueued=controller_status.get("flowFilesQueued", 0),
                    bytesRead=controller_status.get("bytesRead", 0),
                    bytesWritten=controller_status.get("bytesWritten", 0),
                    bytesReceived=controller_status.get("bytesReceived", 0),
                    bytesSent=controller_status.get("bytesSent", 0),
                    flowFilesReceived=controller_status.get("flowFilesReceived", 0),
                    flowFilesSent=controller_status.get("flowFilesSent", 0),
                    flowFilesTransferred=controller_status.get("flowFilesTransferred", 0),
                    bytesTransferred=controller_status.get("bytesTransferred", 0),
                )
        except Exception as e:
            logger.error(f"Failed to get flow status: {e}")
            return FlowStatus()


# Singleton instance
nifi_client = NiFiClient()

