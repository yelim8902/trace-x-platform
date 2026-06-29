#!/bin/bash

# 이 스크립트는 trace-x-platform/ 루트에서 실행해야 합니다.
# 사용법: ./scripts/start-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

echo "Starting Trace-X Platform..."
echo ""

# .env 확인
if [ ! -f .env ]; then
    echo "ERROR: .env 파일이 없습니다."
    echo "  ETHERSCAN_API_KEY=your_key 를 포함한 .env 파일을 만들어주세요."
    exit 1
fi

export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

if [ -z "$ETHERSCAN_API_KEY" ]; then
    echo "ERROR: .env에 ETHERSCAN_API_KEY가 없습니다."
    exit 1
fi

export RISK_SCORING_API_URL="${RISK_SCORING_API_URL:-http://localhost:5001}"

mkdir -p logs .pids

# ── 1. Risk Scoring API (포트 5001) ──────────────────────────────────────
echo "[1/3] Risk Scoring API 시작 중 (port 5001)..."
cd "$ROOT_DIR/risk-scoring"

if [ ! -f venv/bin/activate ]; then
    echo "  venv 없음 → 생성 중..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt
python run_server.py > "$ROOT_DIR/logs/risk-scoring.log" 2>&1 &
RISK_PID=$!
deactivate
cd "$ROOT_DIR"

# 헬스체크 대기 (최대 15초)
for i in $(seq 1 15); do
    sleep 1
    if curl -sf http://localhost:5001/health > /dev/null 2>&1; then
        echo "  Risk Scoring API 준비됨 (PID: $RISK_PID)"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "  ERROR: Risk Scoring API가 시작되지 않았습니다."
        echo "  로그: tail -f logs/risk-scoring.log"
        exit 1
    fi
done
echo ""

# ── 2. Backend API (포트 8888) ────────────────────────────────────────────
echo "[2/3] Backend API 시작 중 (port 8888)..."
cd "$ROOT_DIR/backend"

if [ ! -f venv/bin/activate ]; then
    echo "  venv 없음 → 생성 중..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -e .
python main.py > "$ROOT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
deactivate
cd "$ROOT_DIR"

# 헬스체크 대기 (최대 30초)
for i in $(seq 1 30); do
    sleep 1
    if curl -sf http://localhost:8888/api/dashboard/summary > /dev/null 2>&1; then
        echo "  Backend API 준비됨 (PID: $BACKEND_PID)"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ERROR: Backend API가 시작되지 않았습니다."
        echo "  로그: tail -f logs/backend.log"
        exit 1
    fi
done
echo ""

# ── 3. Frontend (포트 5173) ───────────────────────────────────────────────
echo "[3/3] Frontend 시작 중 (port 5173)..."
cd "$ROOT_DIR/frontend"
if [ ! -d node_modules ]; then
    echo "  node_modules 없음 → npm install 실행 중..."
    npm install
fi
node node_modules/.bin/vite --host 0.0.0.0 > "$ROOT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
cd "$ROOT_DIR"

sleep 4
echo "  Frontend 준비됨 (PID: $FRONTEND_PID)"
echo ""

# PID 저장
echo "$RISK_PID"     > .pids/risk-scoring.pid
echo "$BACKEND_PID"  > .pids/backend.pid
echo "$FRONTEND_PID" > .pids/frontend.pid

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "All services running!"
echo ""
echo "  Frontend:      http://localhost:5173"
echo "  Backend:       http://localhost:8888"
echo "  Risk Scoring:  http://localhost:5001"
echo "  API Docs:      http://localhost:5001/api-docs"
echo ""
echo "  로그 보기:"
echo "    tail -f logs/risk-scoring.log"
echo "    tail -f logs/backend.log"
echo "    tail -f logs/frontend.log"
echo ""
echo "  종료: ./scripts/stop-all.sh  또는  Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

trap "echo ''; echo 'Stopping...'; ./scripts/stop-all.sh; exit" INT TERM
wait
