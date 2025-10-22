"""Data models for the application."""

from typing import Any
from pydantic import BaseModel, Field


class ProcessGroupSummary(BaseModel):
    """Summary information about a process group."""
    
    id: str
    name: str
    comments: str | None = None
    version_control_information: dict[str, Any] | None = Field(None, alias="versionControlInformation")
    parent_group_id: str | None = Field(None, alias="parentGroupId")
    running_count: int = 0
    stopped_count: int = 0
    invalid_count: int = 0
    disabled_count: int = 0
    active_remote_port_count: int = 0
    inactive_remote_port_count: int = 0
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class Processor(BaseModel):
    """Processor information."""
    
    id: str
    name: str
    type: str
    state: str  # RUNNING, STOPPED, DISABLED, INVALID
    comments: str | None = None
    style: dict[str, Any] | None = None
    relationships: list[dict[str, Any]] = []
    config: dict[str, Any] | None = None
    input_requirement: str | None = Field(None, alias="inputRequirement")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class Connection(BaseModel):
    """Connection/Relationship information."""
    
    id: str
    name: str | None = None
    source_id: str = Field(..., alias="sourceId")
    source_name: str | None = Field(None, alias="sourceName")
    source_type: str | None = Field(None, alias="sourceType")
    destination_id: str = Field(..., alias="destinationId")
    destination_name: str | None = Field(None, alias="destinationName")
    destination_type: str | None = Field(None, alias="destinationType")
    selected_relationships: list[str] = Field(default_factory=list, alias="selectedRelationships")
    backpressure_data_size_threshold: str | None = Field(None, alias="backPressureDataSizeThreshold")
    backpressure_object_threshold: int | None = Field(None, alias="backPressureObjectThreshold")
    flowfile_expiration: str | None = Field(None, alias="flowFileExpiration")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class ProcessGroupDetail(BaseModel):
    """Detailed information about a process group including its children."""
    
    id: str
    name: str
    comments: str | None = None
    parent_group_id: str | None = Field(None, alias="parentGroupId")
    version_control_information: dict[str, Any] | None = Field(None, alias="versionControlInformation")
    running_count: int = 0
    stopped_count: int = 0
    invalid_count: int = 0
    disabled_count: int = 0
    active_remote_port_count: int = 0
    inactive_remote_port_count: int = 0
    up_to_date_count: int = 0
    locally_modified_count: int = 0
    stale_count: int = 0
    locally_modified_and_stale_count: int = 0
    sync_failure_count: int = 0
    input_port_count: int = 0
    output_port_count: int = 0
    processors: list[Processor] = []
    connections: list[Connection] = []
    children: list["ProcessGroupDetail"] = []
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class FlowStatus(BaseModel):
    """Status information for the flow."""
    
    active_thread_count: int = Field(0, alias="activeThreadCount")
    queued_count: str = Field("0", alias="queued")
    queued_size: str = Field("0 bytes", alias="queuedSize")
    bytes_queued: int = Field(0, alias="bytesQueued")
    flowfiles_queued: int = Field(0, alias="flowFilesQueued")
    bytes_read: int = Field(0, alias="bytesRead")
    bytes_written: int = Field(0, alias="bytesWritten")
    bytes_received: int = Field(0, alias="bytesReceived")
    bytes_sent: int = Field(0, alias="bytesSent")
    flowfiles_received: int = Field(0, alias="flowFilesReceived")
    flowfiles_sent: int = Field(0, alias="flowFilesSent")
    flowfiles_transferred: int = Field(0, alias="flowFilesTransferred")
    bytes_transferred: int = Field(0, alias="bytesTransferred")
    
    class Config:
        """Pydantic configuration."""
        populate_by_name = True


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str
    nifi_api_url: str
    nifi_available: bool = False
    message: str | None = None

