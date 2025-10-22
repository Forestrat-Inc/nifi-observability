"""Main FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import ProcessGroupDetail, FlowStatus, HealthCheckResponse
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

