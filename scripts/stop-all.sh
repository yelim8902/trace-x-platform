#!/bin/bash

echo "⏹️  Stopping Trace-X Platform..."
echo ""

# Kill by PID files if they exist
if [ -d .pids ]; then
    for pidfile in .pids/*.pid; do
        if [ -f "$pidfile" ]; then
            pid=$(cat "$pidfile")
            service=$(basename "$pidfile" .pid)
            if kill -0 "$pid" 2>/dev/null; then
                echo "Stopping $service (PID: $pid)..."
                kill "$pid" 2>/dev/null
            fi
            rm "$pidfile"
        fi
    done
    rmdir .pids 2>/dev/null
fi

# Fallback: kill by port
echo "Checking for processes on ports..."

# Port 5001 (Risk Scoring)
PID_5001=$(lsof -ti:5001)
if [ ! -z "$PID_5001" ]; then
    echo "Killing process on port 5001 (PID: $PID_5001)"
    kill -9 $PID_5001 2>/dev/null
fi

# Port 8888 (Backend)
PID_8888=$(lsof -ti:8888)
if [ ! -z "$PID_8888" ]; then
    echo "Killing process on port 8888 (PID: $PID_8888)"
    kill -9 $PID_8888 2>/dev/null
fi

# Port 5173 (Frontend)
PID_5173=$(lsof -ti:5173)
if [ ! -z "$PID_5173" ]; then
    echo "Killing process on port 5173 (PID: $PID_5173)"
    kill -9 $PID_5173 2>/dev/null
fi

echo ""
echo "✅ All services stopped!"

