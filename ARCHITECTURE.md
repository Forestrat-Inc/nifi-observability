# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          User's Browser                          │
│                      http://localhost:3000                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                     React Frontend (Port 3000)                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Components:                                             │   │
│  │  - App.js (Main container)                              │   │
│  │  - ProcessGroupTree.js (Hierarchy visualization)        │   │
│  │  - FlowStatus.js (Metrics dashboard)                    │   │
│  │  - LoadingSpinner.js (Loading states)                   │   │
│  │  - ErrorMessage.js (Error handling)                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Services:                                               │   │
│  │  - api.js (Axios HTTP client)                           │   │
│  │    └─> Proxy to http://localhost:8000                   │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST (via proxy)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend (Port 8000)                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  API Endpoints (app/main.py):                           │   │
│  │  - GET /                  → Health check                │   │
│  │  - GET /api/health        → Detailed health             │   │
│  │  - GET /api/process-groups → Full hierarchy            │   │
│  │  - GET /api/process-groups/{id} → Specific group       │   │
│  │  - GET /api/flow/status   → Flow metrics               │   │
│  │  - GET /docs              → Swagger UI                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Configuration (app/config.py):                         │   │
│  │  - Pydantic Settings                                     │   │
│  │  - Environment variables                                 │   │
│  │  - CORS configuration                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Data Models (app/models.py):                           │   │
│  │  - ProcessGroupDetail                                    │   │
│  │  - FlowStatus                                            │   │
│  │  - HealthCheckResponse                                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Services (app/services/nifi_client.py):                │   │
│  │  - NiFiClient class                                      │   │
│  │    - Async HTTP requests with httpx                     │   │
│  │    - Recursive hierarchy fetching                       │   │
│  │    - Error handling                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/REST
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                  Apache NiFi Instance                            │
│              http://18.235.156.98:9090/nifi-api/                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  REST API Endpoints:                                     │   │
│  │  - GET /flow/about                                       │   │
│  │  - GET /flow/process-groups/root                         │   │
│  │  - GET /process-groups/{id}                              │   │
│  │  - GET /flow/process-groups/{id}                         │   │
│  │  - GET /flow/process-groups/{id}/status                  │   │
│  │  - GET /flow/status                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Data:                                                   │   │
│  │  - NiFi Flow (v2.5.0)                                    │   │
│  │  - 15 top-level process groups                           │   │
│  │  - Nested process group hierarchy                        │   │
│  │  - 75 running processors                                 │   │
│  │  - 201 stopped processors                                │   │
│  │  - 93 queued flowfiles (5.88 MB)                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Initiates Request
```
User clicks "Refresh" or page loads
    ↓
React App.js componentDidMount/handleRefresh
    ↓
Call api.getAllProcessGroups()
```

### 2. Frontend → Backend
```
Axios GET request
    ↓
http://localhost:8000/api/process-groups
    ↓
Backend receives request
```

### 3. Backend Processing
```
FastAPI endpoint: get_all_process_groups()
    ↓
nifi_client.get_all_process_groups_hierarchy()
    ↓
get_root_process_group_id()
    ↓
get_process_group_hierarchy(root_id, depth=0)
    ↓
For each process group:
  ├─ get_process_group(group_id)
  ├─ get_process_group_flow(group_id)
  └─ Recursively fetch children (up to max_depth=10)
```

### 4. Backend → NiFi
```
Multiple async HTTP requests to NiFi API:
    ├─ GET /flow/process-groups/root
    ├─ GET /process-groups/{id}
    ├─ GET /flow/process-groups/{id}
    └─ Recursive calls for child groups
```

### 5. Data Transformation
```
Raw NiFi API response
    ↓
Parse and validate with Pydantic models
    ↓
Build ProcessGroupDetail hierarchy
    ↓
Return JSON response to frontend
```

### 6. Frontend Rendering
```
Receive JSON data
    ↓
Update React state
    ↓
ProcessGroupTree component recursively renders:
    ├─ Root process group (depth 0)
    ├─ Child groups (depth 1)
    ├─ Grandchild groups (depth 2)
    └─ Continue recursively...
    ↓
Display with expand/collapse functionality
```

## Component Interaction

### React Component Hierarchy
```
App.js (Main container)
    ├─ Header
    │   ├─ Title & Description
    │   ├─ Health Indicator (Connected/Disconnected)
    │   └─ Refresh Button
    │
    ├─ Summary Bar
    │   ├─ Total Process Groups
    │   ├─ Root Group Name
    │   └─ Direct Children Count
    │
    ├─ FlowStatus Component
    │   └─ Status Cards Grid
    │       ├─ Active Threads
    │       ├─ Queued Items
    │       ├─ FlowFiles
    │       ├─ Received
    │       ├─ Sent
    │       └─ Transferred
    │
    └─ ProcessGroupTree Component (Recursive)
        └─ For each process group:
            ├─ Node Content
            │   ├─ Expand/Collapse Icon
            │   ├─ Folder Icon
            │   ├─ Group Name
            │   ├─ Comments
            │   ├─ Status Badges
            │   └─ ID
            │
            └─ Children Container
                └─ [Recursively render child ProcessGroupTree components]
```

## Technology Stack Details

### Backend Stack
```
Python 3.10+
    └─ FastAPI 0.115.0+ (Web framework)
        ├─ Uvicorn (ASGI server)
        ├─ Pydantic v2 (Data validation)
        ├─ httpx 0.27.0+ (Async HTTP client)
        └─ python-dotenv (Environment config)
```

### Frontend Stack
```
Node.js 18+
    └─ React 18+ (UI library)
        ├─ Create React App (Build tooling)
        ├─ Axios (HTTP client)
        ├─ React Icons (Icon library)
        └─ CSS3 (Styling)
```

### Development Tools
```
Backend:
    ├─ uv (Package manager)
    ├─ pytest (Testing)
    └─ pytest-asyncio (Async testing)

Frontend:
    ├─ npm (Package manager)
    ├─ Jest (Testing - via CRA)
    └─ React Testing Library
```

## API Request/Response Examples

### 1. Health Check
**Request:**
```http
GET /api/health HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "status": "healthy",
  "nifi_api_url": "http://18.235.156.98:9090/nifi-api/",
  "nifi_available": true,
  "message": "All systems operational"
}
```

### 2. Process Groups Hierarchy
**Request:**
```http
GET /api/process-groups HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "id": "82c01e35-0199-1000-5b6e-d2f2f4be3c43",
  "name": "NiFi Flow",
  "comments": null,
  "parent_group_id": null,
  "running_count": 75,
  "stopped_count": 201,
  "invalid_count": 0,
  "disabled_count": 0,
  "children": [
    {
      "id": "cf66beb7-0199-1000-ffff-ffffae78bb78",
      "name": "trade-reporting",
      "running_count": 5,
      "stopped_count": 12,
      "children": [...]
    },
    ...
  ]
}
```

### 3. Flow Status
**Request:**
```http
GET /api/flow/status HTTP/1.1
Host: localhost:8000
```

**Response:**
```json
{
  "activeThreadCount": 0,
  "queued": "93 / 5.88 MB",
  "queuedSize": "0 bytes",
  "bytesQueued": 6164575,
  "flowFilesQueued": 93,
  "bytesReceived": 0,
  "bytesSent": 0,
  "flowFilesReceived": 0,
  "flowFilesSent": 0
}
```

## Error Handling Flow

```
Error occurs in NiFi API call
    ↓
httpx raises exception
    ↓
NiFiClient catches exception
    ↓
Log error message
    ↓
Raise NiFiAPIError with details
    ↓
FastAPI endpoint catches NiFiAPIError
    ↓
Return HTTPException with status code
    ↓
Frontend receives error response
    ↓
Display ErrorMessage component
    ↓
User can retry with refresh button
```

## Security Architecture

### Current Implementation
```
Frontend (Port 3000)
    ↓ CORS: localhost:3000 allowed
Backend (Port 8000)
    ↓ No authentication
NiFi API (Port 9090)
    ↓ No authentication required
```

### Production Recommendations
```
Frontend (HTTPS)
    ↓ CORS: production domain only
Backend (HTTPS)
    ↓ API key authentication
    ↓ Rate limiting
    ↓ Input validation
NiFi API (HTTPS)
    ↓ Certificate-based auth
    ↓ Username/password
```

## Performance Optimization

### Current Implementation
- Async HTTP requests (concurrent fetching)
- Recursive with depth limiting (prevents infinite loops)
- No caching (always fresh data)

### Potential Optimizations
- Redis caching layer (5-minute TTL)
- Background job for periodic refresh
- WebSocket for real-time updates
- Pagination for large hierarchies
- Lazy loading for deep trees
- Database for historical data

## Deployment Architecture

### Development
```
Local Machine
    ├─ Backend: localhost:8000
    └─ Frontend: localhost:3000 (with proxy)
```

### Production Option 1: Single Server
```
Server (e.g., AWS EC2)
    ├─ Nginx (Port 80/443)
    │   ├─ Serves static frontend files
    │   └─ Reverse proxy to backend
    └─ Backend (Port 8000)
        └─ Systemd service
```

### Production Option 2: Docker
```
Docker Host
    ├─ Frontend Container (Port 80)
    │   └─ Nginx serving build files
    └─ Backend Container (Port 8000)
        └─ Uvicorn + FastAPI
```

### Production Option 3: Cloud Native
```
AWS/Azure/GCP
    ├─ Frontend: S3 + CloudFront / Vercel
    └─ Backend: Lambda / Cloud Run / App Service
```

## Monitoring and Observability

### Recommended Monitoring Stack
```
Application
    ↓
Logging: structured logs → ELK/Loki
    ↓
Metrics: Prometheus → Grafana
    ↓
Errors: Sentry
    ↓
Uptime: StatusCake/UptimeRobot
    ↓
Alerts: PagerDuty/Slack
```

## Scalability Considerations

### Current Capacity
- Single backend instance
- Synchronous hierarchy fetching
- No caching
- Suitable for: < 100 process groups

### Scaling Strategy
```
Small (< 100 groups):
    └─ Current architecture

Medium (100-1000 groups):
    ├─ Add Redis caching
    ├─ Multiple backend workers
    └─ Load balancer

Large (> 1000 groups):
    ├─ Microservices architecture
    ├─ Message queue (RabbitMQ/Kafka)
    ├─ Dedicated cache cluster
    ├─ Database for historical data
    └─ CDN for frontend
```

---

**Last Updated:** October 21, 2025  
**Version:** 0.1.0  
**Status:** Production Ready

