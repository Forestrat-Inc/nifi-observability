"""Grafana/Loki client for querying logs."""

import logging
import httpx
from typing import Any
from datetime import datetime, timedelta
from app.config import settings

logger = logging.getLogger(__name__)


class GrafanaAPIError(Exception):
    """Error when interacting with Grafana API."""
    pass


class GrafanaClient:
    """Client for querying Grafana Loki datasource."""
    
    def __init__(
        self,
        grafana_url: str | None = None,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        loki_datasource_uid: str | None = None,
        loki_direct_url: str | None = None,
        timeout: int = 30
    ):
        """
        Initialize Grafana/Loki client.
        
        Args:
            grafana_url: Grafana instance URL (defaults to settings.grafana_url)
            api_key: Grafana API key (preferred authentication method)
            username: Grafana username (alternative to API key)
            password: Grafana password (alternative to API key)
            loki_datasource_uid: Loki datasource UID in Grafana (required if using Grafana proxy)
            loki_direct_url: Direct Loki API URL (alternative to Grafana proxy, e.g., "http://loki:3100")
            timeout: Request timeout in seconds
        """
        self.grafana_url = (grafana_url or settings.grafana_url).rstrip('/')
        self.api_key = api_key or settings.grafana_api_key
        self.username = username or settings.grafana_username
        self.password = password or settings.grafana_password
        self.loki_datasource_uid = loki_datasource_uid or settings.loki_datasource_uid
        self.loki_direct_url = loki_direct_url or settings.loki_direct_url
        self.timeout = timeout
        
        if not self.api_key and (not self.username or not self.password):
            logger.warning("No Grafana/Loki authentication credentials provided")
    
    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for Grafana API requests."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.username and self.password:
            # Basic auth
            import base64
            credentials = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        return headers
    
    async def query_loki(
        self,
        logql: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Query Loki using LogQL.
        
        Supports two methods:
        1. Direct Loki API (if loki_direct_url is configured)
        2. Grafana datasource proxy (if loki_datasource_uid is configured)
        
        Args:
            logql: LogQL query string
            start_time: Start time for query (defaults to 1 hour ago)
            end_time: End time for query (defaults to now)
            limit: Maximum number of log entries to return
            
        Returns:
            List of log entries with parsed attributes
        """
        # Default time range: last hour
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=1)
        
        # Log time ranges in both UTC and EDT for debugging
        from datetime import timezone
        edt_tz = timezone(timedelta(hours=-4))  # EDT is UTC-4
        start_time_edt = start_time.replace(tzinfo=timezone.utc).astimezone(edt_tz)
        end_time_edt = end_time.replace(tzinfo=timezone.utc).astimezone(edt_tz)
        
        logger.info(f"Query time range - Start (UTC): {start_time.isoformat()}, End (UTC): {end_time.isoformat()}")
        logger.info(f"Query time range - Start (EDT): {start_time_edt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}, End (EDT): {end_time_edt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        
        # Convert to nanoseconds (Unix timestamp) - Unix timestamps are timezone-agnostic
        start_ns = int(start_time.timestamp() * 1_000_000_000)
        end_ns = int(end_time.timestamp() * 1_000_000_000)
        
        logger.info(f"Query parameters - Start (ns): {start_ns}, End (ns): {end_ns}, Limit: {limit}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=True) as client:
                # Determine query method: direct Loki or Grafana proxy
                if self.loki_direct_url:
                    # Direct Loki API query
                    url = f"{self.loki_direct_url.rstrip('/')}/loki/api/v1/query_range"
                    headers = {}  # Direct Loki might not need auth, or use different auth
                    logger.debug(f"Querying Loki directly: {logql}")
                elif self.loki_datasource_uid:
                    # Query via Grafana datasource proxy
                    url = f"{self.grafana_url}/api/datasources/proxy/uid/{self.loki_datasource_uid}/loki/api/v1/query_range"
                    headers = self._get_headers()
                    logger.info(f"Querying Loki via Grafana proxy")
                    logger.info(f"  LogQL: {logql}")
                    logger.info(f"  URL: {url}")
                    logger.info(f"  Start (ns): {start_ns}, End (ns): {end_ns}, Limit: {limit}")
                else:
                    # Use Grafana Explore API - need to find Loki datasource first
                    # First, list datasources to find Loki datasource
                    url = f"{self.grafana_url}/api/datasources"
                    headers = self._get_headers()
                    
                    logger.debug("Fetching datasources to find Loki datasource")
                    ds_response = await client.get(url, headers=headers)
                    ds_response.raise_for_status()
                    datasources = ds_response.json()
                    
                    # Find Loki datasource
                    # Prefer datasource with UID "grafanacloud-logs" if it exists, otherwise use first Loki datasource
                    loki_ds = None
                    preferred_uid = "grafanacloud-logs"
                    
                    # First, try to find the preferred datasource
                    for ds in datasources:
                        if ds.get("type") == "loki" and ds.get("uid") == preferred_uid:
                            loki_ds = ds
                            break
                    
                    # If preferred not found, use first Loki datasource
                    if not loki_ds:
                        for ds in datasources:
                            if ds.get("type") == "loki":
                                loki_ds = ds
                                break
                    
                    if not loki_ds:
                        raise GrafanaAPIError("No Loki datasource found in Grafana")
                    
                    loki_uid = loki_ds.get("uid")
                    if not loki_uid:
                        raise GrafanaAPIError("Loki datasource found but has no UID")
                    
                    logger.info(f"Using Loki datasource: {loki_ds.get('name')} (UID: {loki_uid})")
                    
                    # Now query using the datasource proxy with the discovered UID
                    url = f"{self.grafana_url}/api/datasources/proxy/uid/{loki_uid}/loki/api/v1/query_range"
                    
                    params = {
                        "query": logql,
                        "start": start_ns,
                        "end": end_ns,
                        "limit": limit
                    }
                    
                    logger.debug(f"Querying Loki via Grafana proxy (discovered UID): {logql}")
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Parse Loki response
                    logs = []
                    if "data" in data and "result" in data["data"]:
                        for stream in data["data"]["result"]:
                            if "values" in stream:
                                for entry in stream["values"]:
                                    # Loki returns [timestamp_ns, log_line]
                                    timestamp_ns, log_line = entry
                                    timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000)
                                    
                                    logs.append({
                                        "timestamp": timestamp.isoformat(),
                                        "message": log_line,
                                        "stream": stream.get("stream", {})
                                    })
                    
                    logs.sort(key=lambda x: x["timestamp"], reverse=True)
                    return logs
                
                # For direct Loki or Grafana proxy
                params = {
                    "query": logql,
                    "start": start_ns,
                    "end": end_ns,
                    "limit": limit
                }
                
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Parse Loki response
                logs = []
                if "data" in data and "result" in data["data"]:
                    for stream in data["data"]["result"]:
                        if "values" in stream:
                            for entry in stream["values"]:
                                # Loki returns [timestamp_ns, log_line]
                                timestamp_ns, log_line = entry
                                timestamp = datetime.fromtimestamp(int(timestamp_ns) / 1_000_000_000)
                                
                                logs.append({
                                    "timestamp": timestamp.isoformat(),
                                    "message": log_line,
                                    "stream": stream.get("stream", {})
                                })
                
                # Sort by timestamp (newest first)
                logs.sort(key=lambda x: x["timestamp"], reverse=True)
                
                return logs
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error querying Grafana Loki: {e}")
            error_detail = ""
            try:
                error_response = e.response.json()
                if isinstance(error_response, dict):
                    error_detail = error_response.get("message", error_response.get("error", ""))
            except Exception:
                error_detail = e.response.text[:200] if e.response.text else ""
            
            if e.response.status_code == 401:
                raise GrafanaAPIError(f"Grafana authentication failed. Check API key or credentials. {error_detail}")
            elif e.response.status_code == 403:
                raise GrafanaAPIError(f"Grafana access forbidden. Check API key permissions. {error_detail}")
            elif e.response.status_code == 404:
                if self.loki_datasource_uid:
                    raise GrafanaAPIError(f"Loki datasource '{self.loki_datasource_uid}' not found. {error_detail}")
                else:
                    raise GrafanaAPIError(f"Loki datasource not found. {error_detail}")
            raise GrafanaAPIError(f"HTTP error {e.response.status_code}: {error_detail}")
        except Exception as e:
            logger.error(f"Failed to query Grafana Loki: {e}")
            raise GrafanaAPIError(f"Failed to query logs: {e}")
    
    async def get_processor_logs(
        self,
        processor_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get logs for a specific NiFi processor.
        
        Args:
            processor_id: The NiFi processor ID
            start_time: Start time for query (defaults to 1 hour ago)
            end_time: End time for query (defaults to now)
            limit: Maximum number of log entries to return
            
        Returns:
            List of parsed log entries
        """
        # LogQL query: filter by service_name label and attributes_processor_id from JSON attributes
        # The service_name is a label in Loki, attributes_processor_id is in the JSON attributes
        # Format: {service_name="nifi-local-instance"} | json | attributes_processor_id="processor_id"
        logql = f'{{service_name="nifi-local-instance"}} | json | attributes_processor_id="{processor_id}"'
        
        logger.info(f"LogQL Query: {logql}")
        logger.info(f"Processor ID: {processor_id}")
        if start_time:
            from datetime import timezone
            edt_tz = timezone(timedelta(hours=-4))
            start_time_edt = start_time.replace(tzinfo=timezone.utc).astimezone(edt_tz)
            logger.info(f"Start Time - UTC: {start_time.isoformat()}, EDT: {start_time_edt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        if end_time:
            from datetime import timezone
            edt_tz = timezone(timedelta(hours=-4))
            end_time_edt = end_time.replace(tzinfo=timezone.utc).astimezone(edt_tz)
            logger.info(f"End Time - UTC: {end_time.isoformat()}, EDT: {end_time_edt.strftime('%Y-%m-%d %I:%M:%S %p %Z')}")
        
        try:
            raw_logs = await self.query_loki(logql, start_time, end_time, limit)
            logger.info(f"Raw logs returned from Loki: {len(raw_logs)} entries")
            
            # Parse and enrich log entries
            parsed_logs = []
            for log_entry in raw_logs:
                try:
                    import json
                    # Try to parse the message as JSON
                    # Based on the provided format, the log might be in the "body" field
                    message = log_entry.get("message", "")
                    
                    # The log format shows JSON structure with body and attributes
                    parsed_entry = {
                        "timestamp": log_entry.get("timestamp"),
                        "raw_message": message,
                        "stream": log_entry.get("stream", {})
                    }
                    
                    # Try to parse JSON if present
                    try:
                        if message.strip().startswith("{"):
                            log_data = json.loads(message)
                            parsed_entry["body"] = log_data.get("body", message)
                            parsed_entry["attributes"] = log_data.get("attributes", {})
                            parsed_entry["resources"] = log_data.get("resources", {})
                        else:
                            # If not JSON, treat entire message as body
                            parsed_entry["body"] = message
                            parsed_entry["attributes"] = {}
                            parsed_entry["resources"] = {}
                    except json.JSONDecodeError:
                        # Not JSON, use as-is
                        parsed_entry["body"] = message
                        parsed_entry["attributes"] = {}
                        parsed_entry["resources"] = {}
                    
                    parsed_logs.append(parsed_entry)
                except Exception as e:
                    logger.warning(f"Failed to parse log entry: {e}")
                    # Include raw entry if parsing fails
                    parsed_logs.append({
                        "timestamp": log_entry.get("timestamp"),
                        "body": log_entry.get("message", ""),
                        "attributes": {},
                        "resources": {},
                        "parse_error": str(e)
                    })
            
            return parsed_logs
            
        except GrafanaAPIError:
            raise
        except Exception as e:
            logger.error(f"Failed to get processor logs for {processor_id}: {e}")
            raise GrafanaAPIError(f"Failed to get processor logs: {e}")


# Global instance
grafana_client = GrafanaClient()

