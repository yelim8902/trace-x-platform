# Deployment

## Local Scripts

```bash
cp .env.example .env
# ETHERSCAN_API_KEY 입력

./scripts/start-all.sh
./scripts/health-check.sh
```

중지:

```bash
./scripts/stop-all.sh
```

## Docker Compose

```bash
cp .env.example .env
# ETHERSCAN_API_KEY 입력

docker compose up --build
```

서비스:

| Service | Container | Port |
| --- | --- | ---: |
| Frontend | trace-x-frontend | 5173 |
| Backend | trace-x-backend | 8888 |
| Risk Scoring | trace-x-risk-scoring | 5001 |

## Environment Variables

필수:

```text
ETHERSCAN_API_KEY
```

로컬 기본값:

```text
RISK_SCORING_API_URL=http://localhost:5001
VITE_BACKEND_API_URL=http://localhost:8888
```

Docker compose 내부에서는 Backend가 아래 주소로 Risk Scoring 컨테이너를 호출합니다.

```text
RISK_SCORING_API_URL=http://risk-scoring:5001
```

선택:

```text
ALCHEMY_URL
DUNE_API_KEY
DB_HOST
DB_USER
DB_PASSWORD
DB_NAME
SECRET_KEY
```

DB 환경변수가 없으면 Backend는 SQLite local DB를 사용합니다. 이 DB 파일은 Git에 올리지 않습니다.

## Production Notes

운영 배포에서는 다음을 바꿉니다.

- `SECRET_KEY`를 안전한 값으로 설정
- MySQL 등 외부 DB 연결
- `VITE_BACKEND_API_URL`을 실제 Backend URL로 설정
- CORS 정책을 배포 도메인 기준으로 제한
- 큰 모델/데이터 파일은 Git이 아니라 object storage 또는 release artifact로 관리
