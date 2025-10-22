# Deployment Guide

## Production Deployment

### Backend Deployment

#### Using uv (Recommended)

1. **Setup Production Environment**

```bash
cd backend

# Create production virtual environment
uv venv --python 3.10

# Activate environment
source .venv/bin/activate  # Unix/macOS
# OR
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -r requirements.txt
```

2. **Configure Environment Variables**

Create a `.env` file in the `backend` directory:

```env
# NiFi Configuration
NIFI_API_URL=http://18.235.156.98:9090/nifi-api/
# NIFI_USERNAME=admin  # Optional: if authentication is required
# NIFI_PASSWORD=secret  # Optional: if authentication is required

# API Configuration
API_TITLE=NiFi Observability API
API_VERSION=0.1.0

# CORS Configuration (adjust for production)
CORS_ORIGINS=["https://your-frontend-domain.com"]

# Request Configuration
REQUEST_TIMEOUT=30
```

3. **Run with Production Server**

```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or using gunicorn with uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

4. **Using systemd (Linux)**

Create `/etc/systemd/system/nifi-observability-backend.service`:

```ini
[Unit]
Description=NiFi Observability Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/nifi-observability/backend
Environment="PATH=/opt/nifi-observability/backend/.venv/bin"
ExecStart=/opt/nifi-observability/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable nifi-observability-backend
sudo systemctl start nifi-observability-backend
```

### Frontend Deployment

#### Build for Production

```bash
cd frontend

# Install dependencies
npm install

# Build production bundle
npm run build
```

The optimized production files will be in the `frontend/build` directory.

#### Deployment Options

##### Option 1: Nginx

1. Install nginx:
```bash
sudo apt-get install nginx  # Ubuntu/Debian
sudo yum install nginx      # CentOS/RHEL
```

2. Configure nginx (`/etc/nginx/sites-available/nifi-observability`):

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /opt/nifi-observability/frontend/build;
    index index.html;
    
    # Frontend
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # Backend API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

3. Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/nifi-observability /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

##### Option 2: Docker

1. **Backend Dockerfile**

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN uv pip install --system -r requirements.txt

# Copy application
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Frontend Dockerfile**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Build
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy build files
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

3. **Docker Compose**

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - NIFI_API_URL=http://18.235.156.98:9090/nifi-api/
    restart: unless-stopped
    
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

Run:
```bash
docker-compose up -d
```

##### Option 3: Cloud Platforms

**Heroku:**

```bash
# Backend
cd backend
heroku create nifi-observability-backend
git push heroku main

# Frontend
cd frontend
npm run build
# Deploy using Heroku buildpacks or static site hosting
```

**AWS (EC2):**

1. Launch EC2 instance
2. Install dependencies (Python, Node.js, nginx)
3. Follow systemd setup for backend
4. Follow nginx setup for frontend
5. Configure security groups for ports 80, 8000

**Vercel (Frontend only):**

```bash
cd frontend
vercel --prod
```

**Railway:**

```bash
railway init
railway up
```

### SSL/TLS Configuration

#### Using Let's Encrypt with Certbot

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Nginx will be automatically configured for HTTPS.

### Environment-Specific Configuration

#### Development
```env
NIFI_API_URL=http://localhost:9090/nifi-api/
CORS_ORIGINS=["http://localhost:3000"]
```

#### Staging
```env
NIFI_API_URL=http://staging-nifi.company.com:9090/nifi-api/
CORS_ORIGINS=["https://staging.company.com"]
```

#### Production
```env
NIFI_API_URL=https://nifi.company.com/nifi-api/
CORS_ORIGINS=["https://observability.company.com"]
REQUEST_TIMEOUT=60
```

### Monitoring and Logging

#### Application Logs

Backend logs are written to stdout. Configure log aggregation:

**Using systemd journal:**
```bash
journalctl -u nifi-observability-backend -f
```

**Using file logging:**

Update `backend/app/main.py`:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("/var/log/nifi-observability/app.log"),
        logging.StreamHandler()
    ]
)
```

#### Health Monitoring

Set up monitoring for the `/api/health` endpoint:

**Using uptimerobot, pingdom, or similar:**
- Monitor: `https://your-domain.com/api/health`
- Interval: 5 minutes
- Alert on non-200 response or `nifi_available: false`

#### Performance Monitoring

Consider integrating:
- **Sentry** for error tracking
- **Prometheus + Grafana** for metrics
- **ELK Stack** for log aggregation

### Backup and Recovery

#### Backup Configuration

1. Backend configuration: `.env` file
2. Frontend build artifacts: `frontend/build/`
3. Database (if added in future)

#### Recovery Steps

1. Restore configuration files
2. Rebuild virtual environment
3. Rebuild frontend
4. Restart services

### Scaling Considerations

#### Backend Scaling

- Use multiple uvicorn workers
- Consider using gunicorn with multiple workers
- Implement caching for process group data
- Use load balancer for multiple instances

#### Frontend Scaling

- Use CDN for static assets
- Enable gzip compression
- Implement browser caching headers
- Consider server-side rendering (SSR) if needed

### Security Checklist

- [ ] Use HTTPS in production
- [ ] Secure NiFi API credentials (if required)
- [ ] Configure proper CORS origins
- [ ] Implement rate limiting
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Monitor for vulnerabilities
- [ ] Use environment variables for sensitive data
- [ ] Implement API authentication (if required)
- [ ] Regular backup of configurations

### Maintenance

#### Update Dependencies

Backend:
```bash
cd backend
source .venv/bin/activate
uv pip list --outdated
uv pip install --upgrade <package>
```

Frontend:
```bash
cd frontend
npm outdated
npm update
```

#### Update Application

```bash
git pull origin main
cd backend && uv pip install -r requirements.txt
cd ../frontend && npm install && npm run build
sudo systemctl restart nifi-observability-backend
sudo systemctl restart nginx
```

