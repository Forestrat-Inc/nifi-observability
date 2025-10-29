"""NiFi API client for interacting with Apache NiFi REST API."""

import logging
from typing import Any

import httpx

from app.config import settings
from app.models import ProcessGroupDetail, FlowStatus, Processor, Connection, ProvenanceEvent, ProvenanceEventsResponse

logger = logging.getLogger(__name__)


class NiFiAPIError(Exception):
    """Custom exception for NiFi API errors."""
    pass


class NiFiClient:
    """Client for Apache NiFi REST API."""
    
    def __init__(self, base_url: str | None = None, timeout: int | None = None, verify_ssl: bool = False):
        """
        Initialize the NiFi client.
        
        Args:
            base_url: Base URL for the NiFi API (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
            verify_ssl: Whether to verify SSL certificates (default: False for localhost)
        """
        self.base_url = (base_url or settings.nifi_api_url).rstrip("/")
        self.timeout = timeout or settings.request_timeout
        self.verify_ssl = verify_ssl
        self.auth = None
        self.token = None
        
        if settings.nifi_username and settings.nifi_password:
            # NiFi uses token-based auth, but we'll get it on first request
            self.nifi_username = settings.nifi_username
            self.nifi_password = settings.nifi_password
    
    async def _get_access_token(self) -> str:
        """
        Get an access token from NiFi using username/password.
        
        Returns:
            str: Access token
        """
        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                response = await client.post(
                    f"{self.base_url}/access/token",
                    data={
                        "username": self.nifi_username,
                        "password": self.nifi_password
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                response.raise_for_status()
                token = response.text.strip()
                logger.debug("Successfully obtained NiFi access token")
                return token
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            raise NiFiAPIError(f"Failed to authenticate: {e}")
    
    async def _get_headers(self) -> dict[str, str]:
        """
        Get headers for NiFi API requests, including auth token.
        
        Returns:
            dict: Headers with Authorization
        """
        if not self.token:
            self.token = await self._get_access_token()
        return {"Authorization": f"Bearer {self.token}"}
    
    async def health_check(self) -> dict[str, Any]:
        """
        Check if NiFi API is accessible.
        
        Returns:
            dict: Health check information
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/flow/about",
                    headers=headers
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
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/root",
                    headers=headers
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
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/process-groups/{group_id}",
                    headers=headers
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
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/{group_id}",
                    headers=headers
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
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/flow/process-groups/{group_id}/status",
                    headers=headers
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
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/flow/status",
                    headers=headers
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
    
    async def get_provenance_events(
        self,
        processor_id: str,
        max_results: int = 100,
        start_date: str | None = None,
        end_date: str | None = None
    ) -> ProvenanceEventsResponse:
        """
        Get provenance events for a specific processor.
        
        Args:
            processor_id: The processor ID
            max_results: Maximum number of events to return (default: 100, max: 1000)
            start_date: Start date for filtering (ISO 8601 format)
            end_date: End date for filtering (ISO 8601 format)
            
        Returns:
            ProvenanceEventsResponse: Provenance events for the processor
        """
        try:
            # Build provenance query
            from datetime import datetime
            import asyncio
            
            # Create provenance query per NiFi API (wrap in 'provenance' and use 'ProcessorID')
            query_body = {
                "provenance": {
                    "request": {
                        "incrementalResults": False,
                        "maxResults": min(max_results, 1000),
                        "summarize": True,
                        "searchTerms": {
                            "ProcessorID": {
                                "value": processor_id,
                                "inverse": False
                            }
                        }
                    }
                }
            }
            
            if start_date or end_date:
                query_body["provenance"]["request"]["searchTerms"]["dateRange"] = {}
                if start_date:
                    query_body["provenance"]["request"]["searchTerms"]["dateRange"]["startDate"] = start_date
                if end_date:
                    query_body["provenance"]["request"]["searchTerms"]["dateRange"]["endDate"] = end_date
            
            query_id = None  # Track query ID for cleanup
            async with httpx.AsyncClient(timeout=self.timeout * 2, verify=self.verify_ssl) as client:
                try:
                    # Submit provenance query
                    headers = await self._get_headers()
                    submit_response = await client.post(
                        f"{self.base_url}/provenance",
                        json=query_body,
                        headers=headers
                    )
                    submit_response.raise_for_status()
                    submit_data = submit_response.json()
                    
                    provenance_data = submit_data.get("provenance", {})
                    query_id = provenance_data.get("id")
                    if not query_id:
                        raise NiFiAPIError("Failed to get query ID from provenance request")
                    
                    logger.info(f"Submitted provenance query {query_id} for processor {processor_id}")
                    
                    # Check if results are already available in the POST response (when summarize=true)
                    results_data = provenance_data.get("results", {})
                    events_data = results_data.get("provenanceEvents", [])
                    
                    # Get total count from results (may be different from events_data length when limited)
                    total_count = results_data.get("totalCount")
                    if total_count is None:
                        # Fallback: try parsing total as string
                        total_str = results_data.get("total")
                        if total_str:
                            try:
                                total_count = int(str(total_str).replace(",", ""))
                            except (ValueError, AttributeError):
                                total_count = len(events_data)
                    if total_count is None:
                        total_count = len(events_data)
                    
                    # If results are immediately available, process and return them
                    if events_data:
                        logger.info(f"Results immediately available for query {query_id}, skipping polling (found {len(events_data)} events, total: {total_count})")
                        events = []
                        
                        for event_data in events_data:
                            try:
                                # Use Pydantic's model_validate with populate_by_name to handle both formats
                                event = ProvenanceEvent.model_validate(event_data)
                                events.append(event)
                            except Exception as e:
                                logger.warning(f"Failed to parse provenance event {event_data.get('id', 'unknown')}: {e}")
                                logger.debug(f"Event data: {event_data}")
                        
                        # Sort by event time (most recent first)
                        events.sort(key=lambda x: x.event_time, reverse=True)
                        
                        # Clean up the provenance query before returning
                        await self._delete_provenance_query(client, query_id)
                        
                        return ProvenanceEventsResponse(
                            processorId=processor_id,
                            totalEvents=total_count,  # Use actual total from NiFi
                            events=events[:max_results],  # Limit to max_results
                            queryTime=datetime.now().isoformat()
                        )
                    
                    # Poll for query results (NiFi provenance queries are async when results not immediately available)
                    max_polls = 120  # Increased to 120 polls (2 minutes) for larger queries
                    poll_interval = 1  # seconds
                    
                    for poll_num in range(max_polls):
                        await asyncio.sleep(poll_interval)
                        
                        headers = await self._get_headers()
                        poll_response = await client.get(
                            f"{self.base_url}/provenance/{query_id}",
                            headers=headers
                        )
                        poll_response.raise_for_status()
                        poll_data = poll_response.json()
                        
                        provenance = poll_data.get("provenance", {})
                        status = provenance.get("status")
                        
                        if status == "FINISHED":
                            # Query completed, extract events
                            results_data = provenance.get("results", {})
                            events_data = results_data.get("provenanceEvents", [])
                            
                            # Get total count from results
                            total_count = results_data.get("totalCount")
                            if total_count is None:
                                total_str = results_data.get("total")
                                if total_str:
                                    try:
                                        total_count = int(str(total_str).replace(",", ""))
                                    except (ValueError, AttributeError):
                                        total_count = len(events_data)
                            if total_count is None:
                                total_count = len(events_data)
                            
                            events = []
                            
                            for event_data in events_data:
                                try:
                                    # Use Pydantic's model_validate with populate_by_name to handle both formats
                                    event = ProvenanceEvent.model_validate(event_data)
                                    events.append(event)
                                except Exception as e:
                                    logger.warning(f"Failed to parse provenance event {event_data.get('id', 'unknown')}: {e}")
                                    logger.debug(f"Event data: {event_data}")
                            
                            # Sort by event time (most recent first)
                            events.sort(key=lambda x: x.event_time, reverse=True)
                            
                            # Clean up the provenance query before returning
                            await self._delete_provenance_query(client, query_id)
                            
                            return ProvenanceEventsResponse(
                                processorId=processor_id,
                                totalEvents=total_count,  # Use actual total from NiFi
                                events=events[:max_results],  # Limit to max_results
                                queryTime=datetime.now().isoformat()
                            )
                        elif status == "FAILED":
                            # Delete query even on failure
                            await self._delete_provenance_query(client, query_id)
                            error_message = provenance.get("message", "Query failed")
                            raise NiFiAPIError(f"Provenance query failed: {error_message}")
                        # If still RUNNING, continue polling
                    
                    # Timeout - clean up before raising error
                    await self._delete_provenance_query(client, query_id)
                    raise NiFiAPIError("Provenance query timed out")
                    
                except (NiFiAPIError, httpx.HTTPStatusError):
                    # Re-raise after cleanup
                    if query_id:
                        await self._delete_provenance_query(client, query_id, is_error=True)
                    raise
                except Exception as e:
                    # Clean up on any unexpected error
                    if query_id:
                        await self._delete_provenance_query(client, query_id, is_error=True)
                    raise NiFiAPIError(f"Failed to get provenance events: {e}")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting provenance events for {processor_id}: {e}")
            raise NiFiAPIError(f"HTTP error: {e.response.status_code}")
        except NiFiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get provenance events for {processor_id}: {e}")
            raise NiFiAPIError(f"Failed to get provenance events: {e}")
    
    async def _delete_provenance_query(self, client: httpx.AsyncClient, query_id: str, is_error: bool = False) -> None:
        """
        Helper method to delete a provenance query, ensuring cleanup happens.
        
        Args:
            client: The httpx client to use
            query_id: The query ID to delete
            is_error: Whether this is being called during error handling
        """
        try:
            headers = await self._get_headers()
            await client.delete(
                f"{self.base_url}/provenance/{query_id}",
                headers=headers
            )
            if is_error:
                logger.info(f"Deleted provenance query {query_id} (cleanup after error)")
            else:
                logger.info(f"Deleted provenance query {query_id}")
        except Exception as e:
            logger.warning(f"Failed to delete provenance query {query_id}: {e}")
    
    async def get_provenance_event_details(self, event_id: str) -> ProvenanceEvent:
        """
        Get detailed information for a specific provenance event by ID.
        
        Args:
            event_id: The provenance event ID
            
        Returns:
            ProvenanceEvent: Detailed provenance event information
            
        Raises:
            NiFiAPIError: If unable to fetch the event details
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/provenance-events/{event_id}",
                    headers=headers
                )
                response.raise_for_status()
                event_data = response.json()
                
                # The response structure might be wrapped or direct
                if "provenanceEvent" in event_data:
                    event_data = event_data["provenanceEvent"]
                elif "provenance" in event_data and "event" in event_data["provenance"]:
                    event_data = event_data["provenance"]["event"]
                
                # Parse using Pydantic model
                event = ProvenanceEvent.model_validate(event_data)
                return event
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting provenance event {event_id}: {e}")
            raise NiFiAPIError(f"HTTP error: {e.response.status_code}")
        except NiFiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get provenance event details for {event_id}: {e}")
            raise NiFiAPIError(f"Failed to get provenance event details: {e}")
    
    async def get_provenance_event_content(self, event_id: str, content_type: str) -> str | bytes:
        """
        Get input or output content for a specific provenance event.
        
        Args:
            event_id: The provenance event ID
            content_type: Either "input" or "output"
            
        Returns:
            str | bytes: The content (as text if possible, otherwise bytes)
            
        Raises:
            NiFiAPIError: If unable to fetch the content
        """
        if content_type not in ["input", "output"]:
            raise ValueError(f"content_type must be 'input' or 'output', got '{content_type}'")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify_ssl) as client:
                headers = await self._get_headers()
                response = await client.get(
                    f"{self.base_url}/provenance-events/{event_id}/content/{content_type}",
                    headers=headers
                )
                response.raise_for_status()
                
                # Try to decode as text, otherwise return bytes
                content_type_header = response.headers.get("content-type", "")
                if "text/" in content_type_header or "application/json" in content_type_header:
                    try:
                        return response.text
                    except Exception:
                        return response.content
                else:
                    return response.content
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting provenance event {content_type} content for {event_id}: {e}")
            raise NiFiAPIError(f"HTTP error: {e.response.status_code}")
        except NiFiAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get provenance event {content_type} content for {event_id}: {e}")
            raise NiFiAPIError(f"Failed to get provenance event {content_type} content: {e}")


# Singleton instance
nifi_client = NiFiClient()

