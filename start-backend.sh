#!/bin/bash

# Start NiFi Observability Backend

echo "Starting NiFi Observability Backend..."
echo "======================================="

cd backend

# Activate virtual environment
source .venv/bin/activate

# Start the server
echo "Starting FastAPI server on http://localhost:8000"
echo "API documentation available at http://localhost:8000/docs"
echo ""

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

