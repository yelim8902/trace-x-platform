#!/usr/bin/env python3
"""
백엔드 서버 실행 스크립트

사용법:
    python3 run_server.py
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# api.app 모듈 실행
if __name__ == '__main__':
    from api.app import app
    
    # Backend and frontend expect Risk Scoring on this fixed port.
    port = 5001
    
    print("=" * 70)
    print("🚀 AML Risk Engine API 서버 시작")
    print("=" * 70)
    print()
    print("📍 엔드포인트:")
    print(f"   POST http://localhost:{port}/api/score/transaction")
    print(f"   POST http://localhost:{port}/api/analyze/address")
    print("      - analysis_type: 'basic' (기본 스코어링, 빠름, 기본값)")
    print("      - analysis_type: 'advanced' (심층 분석, 느림)")
    print(f"   GET  http://localhost:{port}/health")
    print()
    print("📚 API 문서:")
    print(f"   GET  http://localhost:{port}/api-docs")
    print()
    print("🌐 데모 페이지:")
    print(f"   http://localhost:{port}/")
    print()
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_debugger=False,
        use_reloader=False,
    )
