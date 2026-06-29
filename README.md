# Trace-X Platform

Trace-X는 블록체인 주소의 거래 흐름을 수집하고 AML 룰 기반으로 위험도를 분석하는 통합 플랫폼입니다.

## 구성

```text
frontend      React + TypeScript UI
backend       Flask API, Etherscan 데이터 수집, 그래프 변환
risk-scoring  Flask API, TRACE-X 룰북 기반 리스크 스코어링
scripts       로컬 실행, 중지, 헬스체크 스크립트
docs          구조, API, 배포, 문제 해결 문서
```

## 기본 포트

| Service | Port | Health |
| --- | ---: | --- |
| Frontend | 5173 | http://localhost:5173 |
| Backend | 8888 | http://localhost:8888/health |
| Risk Scoring | 5001 | http://localhost:5001/health |

## 빠른 시작

```bash
cp .env.example .env
# .env에 ETHERSCAN_API_KEY 입력

./scripts/start-all.sh
./scripts/health-check.sh
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

## Docker 실행

```bash
cp .env.example .env
# .env에 ETHERSCAN_API_KEY 입력

docker compose up --build
```

## 핵심 분석 흐름

```text
사용자 주소 입력
  -> Frontend
  -> Backend /api/analysis/risk-scoring
  -> Etherscan V2 거래 수집
  -> Backend 그래프/거래 포맷 변환
  -> Risk Scoring /api/analyze/address
  -> TRACE-X 룰북 평가
  -> Frontend 결과 표시
```

## 문서

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 정리 기준

이 레포는 실행 가능한 최종본을 기준으로 정리했습니다. 원본 연구 자료, PDF, 대용량 XML/ZIP, 로컬 DB, venv, cache, 모델 pickle 파일은 Git에 올리지 않습니다.
