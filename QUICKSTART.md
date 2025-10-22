# Quick Start Guide

Get the NiFi Observability application up and running in minutes!

## Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- uv (Python package manager)
- Running NiFi instance (default: http://18.235.156.98:9090/nifi-api/)

## Installation

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Set Up Backend

```bash
cd backend

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# OR
.venv\Scripts\activate     # On Windows

# Install dependencies
uv pip install -r requirements.txt
```

### 3. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install
```

## Running the Application

### Option 1: Using Startup Scripts (Recommended)

**Terminal 1 - Backend:**
```bash
./start-backend.sh
```

**Terminal 2 - Frontend:**
```bash
./start-frontend.sh
```

### Option 2: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

## Access the Application

- **Frontend UI:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs

## Quick Test

### Test Backend Connectivity

```bash
cd backend
source .venv/bin/activate
python test_connection.py
```

Expected output:
```
Testing NiFi API connection...
✓ Health check passed!
✓ Root process group ID: ...
✓ Successfully fetched hierarchy!
✓ Flow status retrieved!
All tests passed! ✓
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# Get process groups
curl http://localhost:8000/api/process-groups

# Get flow status
curl http://localhost:8000/api/flow/status
```

## Configuration

### Backend Configuration

Edit `backend/app/config.py` or create `backend/.env`:

```env
NIFI_API_URL=http://18.235.156.98:9090/nifi-api/
CORS_ORIGINS=["http://localhost:3000"]
REQUEST_TIMEOUT=30
```

### Frontend Configuration

The frontend uses a proxy configuration in `package.json`:
```json
"proxy": "http://localhost:8000"
```

To change the API URL for production, set the environment variable:
```bash
REACT_APP_API_URL=http://your-backend-url npm start
```

## What You'll See

### Frontend Features

1. **Header**
   - Application title and description
   - Connection status indicator (green = connected)
   - Refresh button to reload data
   - Last update timestamp

2. **Summary Bar**
   - Total number of process groups
   - Root group name
   - Count of direct children

3. **Flow Status Dashboard**
   - Active threads
   - Queued items (count and size)
   - FlowFiles queued
   - Received/Sent statistics
   - Transfer metrics

4. **Process Group Hierarchy Tree**
   - Expandable/collapsible tree structure
   - Color-coded by depth level
   - Status badges (running, stopped, invalid, disabled)
   - Process group IDs
   - Child count indicators
   - Comments/descriptions

### Navigation

- **Click** on a process group with children to expand/collapse
- **Hover** over process groups to see highlighting
- **Scroll** through the hierarchy
- **Click Refresh** to update all data from NiFi

## Project Structure

```
nifi-observability/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py       # Configuration
│   │   ├── main.py         # FastAPI app & endpoints
│   │   ├── models.py       # Pydantic models
│   │   └── services/
│   │       └── nifi_client.py  # NiFi API client
│   ├── tests/              # Backend tests
│   ├── requirements.txt    # Python dependencies
│   ├── pyproject.toml      # Python project config
│   └── test_connection.py  # Connection test script
├── frontend/               # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── ProcessGroupTree.js
│   │   │   ├── FlowStatus.js
│   │   │   ├── LoadingSpinner.js
│   │   │   └── ErrorMessage.js
│   │   ├── services/
│   │   │   └── api.js      # API service
│   │   ├── App.js          # Main app component
│   │   ├── App.css
│   │   └── index.js
│   └── package.json        # Node dependencies
├── start-backend.sh        # Backend startup script
├── start-frontend.sh       # Frontend startup script
├── README.md              # Main documentation
├── QUICKSTART.md          # This file
├── TESTING.md             # Testing guide
└── DEPLOYMENT.md          # Deployment guide
```

## Troubleshooting

### Backend Won't Start

1. **Port 8000 already in use:**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

2. **Cannot connect to NiFi:**
   - Verify NiFi is running
   - Check the URL in `backend/app/config.py`
   - Test manually: `curl http://18.235.156.98:9090/nifi-api/flow/about`

3. **Import errors:**
   - Ensure virtual environment is activated
   - Reinstall: `uv pip install -r requirements.txt`

### Frontend Won't Start

1. **Port 3000 already in use:**
   ```bash
   lsof -ti:3000 | xargs kill -9
   ```
   Or use different port: `PORT=3001 npm start`

2. **Cannot connect to backend:**
   - Verify backend is running on port 8000
   - Check browser console for errors
   - Try: `curl http://localhost:8000/api/health`

3. **Build issues:**
   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

### Common Issues

1. **Empty tree or "Loading..." forever:**
   - Check backend logs for errors
   - Verify NiFi API is accessible
   - Check browser console for network errors

2. **"Disconnected" status:**
   - Backend cannot reach NiFi API
   - Check network/firewall settings
   - Verify NiFi URL configuration

3. **CORS errors:**
   - Ensure `CORS_ORIGINS` includes your frontend URL
   - For development, should include `http://localhost:3000`

## Next Steps

- Explore the **API documentation** at http://localhost:8000/docs
- Read **TESTING.md** for comprehensive testing guide
- Read **DEPLOYMENT.md** for production deployment
- Customize the UI in `frontend/src/components/`
- Extend the backend in `backend/app/`

## Features Overview

### Current Features ✅

- ✅ Real-time process group hierarchy visualization
- ✅ Complete tree structure with expand/collapse
- ✅ Flow statistics dashboard
- ✅ Status indicators (running, stopped, invalid, disabled)
- ✅ Health monitoring
- ✅ Auto-refresh capability
- ✅ Responsive design
- ✅ Error handling
- ✅ Beautiful, modern UI

### Potential Enhancements 💡

- Auto-refresh with configurable intervals
- Search/filter process groups
- Processor-level details
- Connection queue visualization
- Historical metrics
- Alert notifications
- User authentication
- Export functionality
- Dark mode

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the logs in terminal
3. Check the browser console for frontend errors
4. Refer to TESTING.md and DEPLOYMENT.md

## Success Indicators

When everything is working correctly, you should see:

1. ✅ Backend console shows:
   ```
   INFO: Successfully connected to NiFi API
   INFO: Uvicorn running on http://0.0.0.0:8000
   ```

2. ✅ Frontend browser shows:
   - Green "Connected" indicator
   - Summary bar with process group counts
   - Flow status with metrics
   - Expandable process group tree

3. ✅ Test connection script shows:
   ```
   All tests passed! ✓
   ```

Enjoy using NiFi Observability! 🚀

