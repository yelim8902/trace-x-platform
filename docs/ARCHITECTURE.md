# Architecture

Trace-X는 세 개의 서비스로 나뉩니다.

```text
Frontend (React)
  -> Backend (Flask)
    -> Etherscan V2
    -> Risk Scoring API (Flask)
      -> TRACE-X Rulebook
```

## Frontend

`frontend/`는 사용자가 주소를 입력하고 분석 결과를 확인하는 UI입니다.

주요 화면:

- Dashboard
- Live Detection
- Ad-hoc Analysis
- Report
- Case

주요 호출 대상은 Backend입니다. 브라우저에서 Risk Scoring API를 직접 호출하지 않고, Backend를 API gateway처럼 사용합니다.

## Backend

`backend/`는 데이터 수집과 변환을 담당합니다.

역할:

- Etherscan V2 API로 normal transaction, ERC-20 transfer 수집
- 주소 중심 fund-flow graph 생성
- graph edge를 Risk Scoring API가 받는 transaction 배열로 변환
- Risk Scoring API 호출
- Dashboard/Live Detection/Report API 제공

중요 엔드포인트:

- `GET /health`
- `GET /api/analysis/fund-flow`
- `POST /api/analysis/scoring`
- `POST /api/analysis/risk-scoring`

## Risk Scoring

`risk-scoring/`은 AML 위험도 계산을 담당합니다.

구성:

- `api/`: Flask 라우트
- `core/rules/`: 룰 로더와 평가기
- `core/scoring/`: 주소/거래 스코어링 로직
- `core/aggregation/`: window, topology, pattern 집계
- `rules/tracex_rules.yaml`: TRACE-X 룰북
- `data/lists/`: SDN, scam, CEX, bridge 주소 리스트

룰 축:

- `C-axis`: Compliance. 제재 주소, 고액 거래, 보고 회피 의심
- `E-axis`: Exposure. 믹서, scam, bridge, 위험 주소 노출
- `B-axis`: Behavior. 반복, burst, off-hours, topology 패턴

## Local Runtime Contract

```text
Frontend      http://localhost:5173
Backend       http://localhost:8888
Risk Scoring  http://localhost:5001
```

Backend가 Risk Scoring을 호출할 때는 `RISK_SCORING_API_URL`을 사용합니다.

로컬 기본값:

```text
RISK_SCORING_API_URL=http://localhost:5001
```

Docker compose 내부 기본값:

```text
RISK_SCORING_API_URL=http://risk-scoring:5001
```
