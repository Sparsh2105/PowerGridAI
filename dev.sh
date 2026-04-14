#!/bin/bash

# Kill any existing processes on ports 8000 and 5173
echo "Cleaning up existing processes..."
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null

# Start Backend
echo "Starting Backend on port 8000..."
./venv/bin/uvicorn server:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting Frontend on port 5173..."
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo "Services are starting..."
echo "Backend: http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"

# Wait for both to finish
wait $BACKEND_PID $FRONTEND_PID
