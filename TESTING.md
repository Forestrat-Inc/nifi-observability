# Testing Guide

## Backend Testing

### Automated Tests

Run the test suite:

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

Run tests with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

### Manual API Testing

1. **Health Check**
   ```bash
   curl http://localhost:8000/api/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "nifi_api_url": "http://18.235.156.98:9090/nifi-api/",
     "nifi_available": true,
     "message": "All systems operational"
   }
   ```

2. **Get Process Groups**
   ```bash
   curl http://localhost:8000/api/process-groups
   ```
   
   Returns complete hierarchy of process groups.

3. **Get Flow Status**
   ```bash
   curl http://localhost:8000/api/flow/status
   ```
   
   Returns current flow statistics.

4. **API Documentation**
   
   Visit: http://localhost:8000/docs
   
   Interactive Swagger UI documentation is available.

### Connection Test Script

Run the connection test:

```bash
cd backend
source .venv/bin/activate
python test_connection.py
```

This will test:
- Health check connectivity
- Root process group retrieval
- Hierarchy fetching (limited depth)
- Flow status retrieval

## Frontend Testing

### Run Development Server

```bash
cd frontend
npm start
```

The app will open at http://localhost:3000

### Manual Testing Checklist

- [ ] App loads without errors
- [ ] Health indicator shows "Connected" (green)
- [ ] Flow status cards display data
- [ ] Summary bar shows correct counts
- [ ] Process group tree is displayed
- [ ] Process groups can be expanded/collapsed
- [ ] Status badges (running, stopped, etc.) are visible
- [ ] Refresh button works
- [ ] Responsive design works on mobile

### Run Frontend Tests

```bash
cd frontend
npm test
```

### Build Production Bundle

```bash
cd frontend
npm run build
```

## Integration Testing

### Full Stack Test

1. Start Backend:
   ```bash
   ./start-backend.sh
   ```

2. In a new terminal, start Frontend:
   ```bash
   ./start-frontend.sh
   ```

3. Open browser to http://localhost:3000

4. Verify:
   - Connection status is "Connected"
   - Process groups load and display
   - Flow statistics are shown
   - Hierarchy is navigable
   - Refresh button updates data

## Performance Testing

### Backend Performance

Test response times:

```bash
time curl -s http://localhost:8000/api/process-groups > /dev/null
```

Typical response time for 15 top-level groups with full hierarchy: 2-5 seconds

### Load Testing

Using Apache Bench:

```bash
ab -n 100 -c 10 http://localhost:8000/api/health
```

## Troubleshooting

### Backend Issues

1. **Connection to NiFi fails**
   - Verify NiFi is running at http://18.235.156.98:9090/nifi-api/
   - Check firewall/network connectivity
   - Review backend logs

2. **Port 8000 already in use**
   ```bash
   lsof -ti:8000 | xargs kill -9
   ```

3. **Import errors**
   - Ensure virtual environment is activated
   - Reinstall dependencies: `uv pip install -r requirements.txt`

### Frontend Issues

1. **Cannot connect to backend**
   - Verify backend is running on port 8000
   - Check CORS settings in backend
   - Clear browser cache

2. **Build fails**
   ```bash
   rm -rf node_modules
   npm install
   ```

3. **Port 3000 already in use**
   - Kill the process: `lsof -ti:3000 | xargs kill -9`
   - Or use a different port: `PORT=3001 npm start`

## Test Results

### Verified Functionality

✅ Backend API endpoints working
✅ NiFi API connectivity established
✅ Process group hierarchy retrieval (15 top-level groups)
✅ Flow status tracking
✅ CORS properly configured
✅ Health checks functional
✅ Error handling working
✅ Recursive hierarchy with depth limiting

### Test Data

From running instance:
- Root Group: "NiFi Flow"
- Total Top-Level Groups: 15
- Sample groups: trade-reporting, Test, MSIM_Restricted_List, Manispace-FM-BAML-locates, trade-capture, etc.
- Running processors: 75
- Stopped processors: 201
- Queued items: 93 / 5.88 MB

## Continuous Testing

For development, consider:
1. Running backend with `--reload` flag (already configured)
2. Frontend hot-reload is enabled by default with `npm start`
3. Add pre-commit hooks for linting
4. Set up CI/CD pipeline for automated testing

