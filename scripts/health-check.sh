#!/bin/bash

echo "🏥 Trace-X Health Check"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_service() {
    local name=$1
    local url=$2
    local port=$3
    
    echo -n "[$name] "
    
    # Check if port is open
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        # Port is open, check HTTP
        response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
        
        if [ "$response" == "200" ]; then
            echo -e "${GREEN}✓ Running${NC} (port $port)"
        else
            echo -e "${YELLOW}⚠ Port open but HTTP failed${NC} (HTTP $response)"
        fi
    else
        echo -e "${RED}✗ Not running${NC} (port $port not listening)"
    fi
}

echo "Service Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
check_service "Risk Scoring" "http://localhost:5001/health" 5001
check_service "Backend     " "http://localhost:8888/health" 8888
check_service "Frontend    " "http://localhost:5173" 5173
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "Access URLs:"
echo "  🌐 Frontend:       http://localhost:5173"
echo "  🔧 Backend:        http://localhost:8888"
echo "  📊 Risk Scoring:   http://localhost:5001"
echo ""
