# Troubleshooting

## `.env`가 없다고 나올 때

```bash
cp .env.example .env
```

그리고 `ETHERSCAN_API_KEY`를 입력합니다.

## Backend가 Risk Scoring을 못 찾을 때

로컬 실행에서는 `.env`에 아래 값이 있어야 합니다.

```text
RISK_SCORING_API_URL=http://localhost:5001
```

Docker compose에서는 자동으로 아래 값이 들어갑니다.

```text
RISK_SCORING_API_URL=http://risk-scoring:5001
```

## 포트 충돌

사용 포트:

```text
5173 Frontend
8888 Backend
5001 Risk Scoring
```

확인:

```bash
lsof -i :5173
lsof -i :8888
lsof -i :5001
```

중지:

```bash
./scripts/stop-all.sh
```

## Dashboard가 0으로 보일 때

Dashboard는 일부 데이터를 Dune 또는 로컬 DB 집계에서 가져옵니다. `DUNE_API_KEY`가 없거나 아직 분석 결과가 저장되지 않았다면 0 값이 정상적으로 표시될 수 있습니다.

주소 분석 데모는 `Ad-hoc Analysis` 화면을 먼저 확인합니다.

## Frontend가 Backend를 못 부를 때

Frontend 환경변수:

```text
VITE_BACKEND_API_URL=http://localhost:8888
```

Backend health 확인:

```bash
curl http://localhost:8888/health
```

## Risk Scoring health 확인

```bash
curl http://localhost:5001/health
```

## Git에 올리지 않을 것

- `.env`
- `venv/`, `node_modules/`
- `logs/`, `.pids/`
- `*.db`
- 큰 PDF, ZIP, XML 원본 데이터
- `*.pkl` 모델 파일
