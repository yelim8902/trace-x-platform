#!/bin/bash

# EC2에서 trace-x 디렉토리 구조 설정 스크립트
# 중첩 Git 저장소 문제 해결을 위해 각 컴포넌트를 별도로 클론

set -e

echo "=========================================="
echo "Trace-X 디렉토리 구조 설정"
echo "=========================================="
echo ""

# 현재 디렉토리 확인
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ 오류: trace-x 디렉토리에서 실행해야 합니다!"
    echo "   cd ~/trace-x 후 다시 실행하세요."
    exit 1
fi

echo "📍 현재 디렉토리: $(pwd)"
echo ""

# 1. risk-scoring 설정
echo "1️⃣  risk-scoring 설정 중..."
if [ -d "risk-scoring" ]; then
    if [ ! -f "risk-scoring/Dockerfile" ]; then
        echo "   기존 risk-scoring 디렉토리 제거 중..."
        rm -rf risk-scoring
        echo "   risk-scoring 클론 중..."
        git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
    else
        echo "   ✅ risk-scoring 이미 설정됨"
    fi
else
    echo "   risk-scoring 클론 중..."
    git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git risk-scoring
fi

if [ -f "risk-scoring/Dockerfile" ]; then
    echo "   ✅ risk-scoring Dockerfile 확인됨"
else
    echo "   ❌ risk-scoring Dockerfile 없음!"
    exit 1
fi
echo ""

# 2. frontend 설정
echo "2️⃣  frontend 설정 중..."
if [ -d "frontend" ]; then
    if [ ! -f "frontend/Dockerfile.prod" ]; then
        echo "   기존 frontend 디렉토리 제거 중..."
        rm -rf frontend
        echo "   frontend 클론 중..."
        git clone https://github.com/paran-needless-to-say/frontend.git frontend
    else
        echo "   ✅ frontend 이미 설정됨"
    fi
else
    echo "   frontend 클론 중..."
    git clone https://github.com/paran-needless-to-say/frontend.git frontend
fi

if [ -f "frontend/Dockerfile.prod" ]; then
    echo "   ✅ frontend Dockerfile.prod 확인됨"
else
    echo "   ❌ frontend Dockerfile.prod 없음!"
    exit 1
fi
echo ""

# 3. backend 설정
echo "3️⃣  backend 설정 중..."
if [ -d "backend" ]; then
    if [ ! -f "backend/Dockerfile" ]; then
        echo "   기존 backend 디렉토리 제거 중..."
        rm -rf backend
        echo "   backend 클론 중..."
        git clone https://github.com/paran-needless-to-say/100end.git backend
    else
        echo "   ✅ backend 이미 설정됨"
    fi
else
    echo "   backend 클론 중..."
    git clone https://github.com/paran-needless-to-say/100end.git backend
fi

if [ -f "backend/Dockerfile" ]; then
    echo "   ✅ backend Dockerfile 확인됨"
else
    echo "   ❌ backend Dockerfile 없음!"
    exit 1
fi
echo ""

# 최종 확인
echo "=========================================="
echo "✅ 모든 디렉토리 설정 완료!"
echo "=========================================="
echo ""
echo "확인된 파일:"
echo "  ✅ risk-scoring/Dockerfile"
echo "  ✅ frontend/Dockerfile.prod"
echo "  ✅ backend/Dockerfile"
echo ""
echo "다음 단계:"
echo "  ./scripts/deploy.sh  # 배포 실행"
echo ""

