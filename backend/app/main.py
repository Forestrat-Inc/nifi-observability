"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ProcessGroupDetail, FlowStatus, HealthCheckResponse, ProvenanceEventsResponse, ProvenanceQueryRequest, ProvenanceEvent
from app.services.nifi_client import nifi_client, NiFiAPIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting NiFi Observability API")
    logger.info(f"NiFi API URL: {settings.nifi_api_url}")
    
    # Test connection to NiFi
    health = await nifi_client.health_check()
    if health["available"]:
        logger.info("Successfully connected to NiFi API")
    else:
        logger.warning(f"Could not connect to NiFi API: {health.get('error')}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NiFi Observability API")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """
    Root endpoint - health check.
    
    Returns:
        HealthCheckResponse: API health status
    """
    health = await nifi_client.health_check()
    
    return HealthCheckResponse(
        status="healthy" if health["available"] else "degraded",
        nifi_api_url=settings.nifi_api_url,
        nifi_available=health["available"],
        message=health.get("error") if not health["available"] else "NiFi API is accessible"
    )


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthCheckResponse: Detailed health information
    """
    health = await nifi_client.health_check()
    
    return HealthCheckResponse(
        status="healthy" if health["available"] else "unhealthy",
        nifi_api_url=settings.nifi_api_url,
        nifi_available=health["available"],
        message=health.get("error") if not health["available"] else "All systems operational"
    )


@app.get("/api/process-groups", response_model=ProcessGroupDetail)
async def get_all_process_groups():
    """
    Get all process groups with complete hierarchy.
    
    Returns:
        ProcessGroupDetail: Complete process group hierarchy starting from root
        
    Raises:
        HTTPException: If unable to fetch process groups
    """
    try:
        logger.info("Fetching all process groups with hierarchy")
        hierarchy = await nifi_client.get_all_process_groups_hierarchy()
        logger.info(f"Successfully fetched process group hierarchy: {hierarchy.name}")
        return hierarchy
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/process-groups/{group_id}", response_model=ProcessGroupDetail)
async def get_process_group_by_id(group_id: str):
    """
    Get a specific process group with its children.
    
    Args:
        group_id: The process group ID
        
    Returns:
        ProcessGroupDetail: Process group details with hierarchy
        
    Raises:
        HTTPException: If unable to fetch the process group
    """
    try:
        logger.info(f"Fetching process group: {group_id}")
        hierarchy = await nifi_client.get_process_group_hierarchy(group_id)
        return hierarchy
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/flow/status", response_model=FlowStatus)
async def get_flow_status():
    """
    Get the overall flow status.
    
    Returns:
        FlowStatus: Flow status information
        
    Raises:
        HTTPException: If unable to fetch flow status
    """
    try:
        logger.info("Fetching flow status")
        status = await nifi_client.get_flow_status()
        return status
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/provenance/{processor_id}", response_model=ProvenanceEventsResponse)
async def get_provenance_events(
    processor_id: str,
    max_results: int = 100,
    start_date: str | None = None,
    end_date: str | None = None
):
    """
    Get provenance events for a specific processor.
    
    Args:
        processor_id: The processor ID
        max_results: Maximum number of events to return (default: 100, max: 1000)
        start_date: Start date for filtering (ISO 8601 format)
        end_date: End date for filtering (ISO 8601 format)
        
    Returns:
        ProvenanceEventsResponse: Provenance events for the processor
        
    Raises:
        HTTPException: If unable to fetch provenance events
    """
    try:
        logger.info(f"Fetching provenance events for processor: {processor_id}")
        events = await nifi_client.get_provenance_events(
            processor_id=processor_id,
            max_results=min(max_results, 1000),
            start_date=start_date,
            end_date=end_date
        )
        # Serialize using field names (snake_case) instead of aliases (camelCase)
        # Use JSONResponse to bypass FastAPI's automatic serialization
        return JSONResponse(content=events.model_dump(by_alias=False))
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/provenance", response_model=ProvenanceEventsResponse)
async def query_provenance_events(request: ProvenanceQueryRequest):
    """
    Query provenance events for a processor with request body.
    
    Args:
        request: ProvenanceQueryRequest with processor_id and optional filters
        
    Returns:
        ProvenanceEventsResponse: Provenance events for the processor
        
    Raises:
        HTTPException: If unable to fetch provenance events
    """
    try:
        logger.info(f"Fetching provenance events for processor: {request.processor_id}")
        events = await nifi_client.get_provenance_events(
            processor_id=request.processor_id,
            max_results=request.max_results,
            start_date=request.start_date,
            end_date=request.end_date
        )
        # Serialize using field names (snake_case) instead of aliases (camelCase)
        # Use JSONResponse to bypass FastAPI's automatic serialization
        return JSONResponse(content=events.model_dump(by_alias=False))
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/provenance-events/{event_id}", response_model=ProvenanceEvent)
async def get_provenance_event_details(event_id: str):
    """
    Get detailed information for a specific provenance event by ID.
    
    Args:
        event_id: The provenance event ID
        
    Returns:
        ProvenanceEvent: Detailed provenance event information
        
    Raises:
        HTTPException: If unable to fetch the event details
    """
    try:
        logger.info(f"Fetching provenance event details for event ID: {event_id}")
        event = await nifi_client.get_provenance_event_details(event_id)
        # Serialize using field names (snake_case) instead of aliases (camelCase)
        return JSONResponse(content=event.model_dump(by_alias=False))
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/provenance-events/{event_id}/content/{content_type}")
async def get_provenance_event_content(event_id: str, content_type: str):
    """
    Get input or output content for a specific provenance event.
    
    Args:
        event_id: The provenance event ID
        content_type: Either "input" or "output"
        
    Returns:
        dict: Content response with data and metadata
        
    Raises:
        HTTPException: If unable to fetch the content
    """
    if content_type not in ["input", "output"]:
        raise HTTPException(status_code=400, detail="content_type must be 'input' or 'output'")
    
    try:
        logger.info(f"Fetching {content_type} content for provenance event ID: {event_id}")
        content = await nifi_client.get_provenance_event_content(event_id, content_type)
        
        # Determine if content is text or binary
        is_text = isinstance(content, str)
        if not is_text:
            try:
                content = content.decode('utf-8')
                is_text = True
            except UnicodeDecodeError:
                # Binary content - return as base64
                import base64
                content = base64.b64encode(content).decode('utf-8')
                is_text = False
        
        return JSONResponse(content={
            "event_id": event_id,
            "content_type": content_type,
            "data": content,
            "is_text": is_text,
            "size": len(content) if is_text else len(content)
        })
    except NiFiAPIError as e:
        logger.error(f"NiFi API error: {e}")
        raise HTTPException(status_code=502, detail=f"NiFi API error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/debug/token")
async def get_debug_token():
    """
    Debug endpoint to view the cached NiFi access token.
    WARNING: This exposes sensitive authentication information. Use only for debugging.
    
    Returns:
        dict: Token information
    """
    # Ensure token exists by calling _get_headers
    await nifi_client._get_headers()
    
    token = nifi_client.token
    if token:
        # Decode JWT token to show payload (if it's a JWT)
        try:
            import base64
            import json
            
            # JWT tokens have 3 parts separated by dots: header.payload.signature
            parts = token.split('.')
            if len(parts) >= 2:
                # Decode payload (second part)
                payload_b64 = parts[1]
                # Add padding if needed
                payload_b64 += '=' * (4 - len(payload_b64) % 4)
                payload_bytes = base64.urlsafe_b64decode(payload_b64)
                payload = json.loads(payload_bytes)
                
                return {
                    "token_exists": True,
                    "token_length": len(token),
                    "token_preview": f"{token[:50]}...{token[-20:]}" if len(token) > 70 else token,
                    "token_full": token,
                    "jwt_payload": payload,
                    "expires_at": payload.get("exp"),
                    "issued_at": payload.get("iat"),
                    "subject": payload.get("sub"),
                    "token_format": "JWT"
                }
        except Exception as e:
            # Not a JWT or couldn't decode
            return {
                "token_exists": True,
                "token_length": len(token),
                "token_preview": f"{token[:50]}...{token[-20:]}" if len(token) > 70 else token,
                "token_full": token,
                "token_format": "Plain text",
                "decode_error": str(e)
            }
    
    return {
        "token_exists": False,
        "message": "No token cached. Token will be obtained on next API call."
    }


@app.exception_handler(NiFiAPIError)
async def nifi_api_error_handler(request, exc):
    """Handle NiFi API errors."""
    return JSONResponse(
        status_code=502,
        content={"detail": f"NiFi API error: {str(exc)}"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

