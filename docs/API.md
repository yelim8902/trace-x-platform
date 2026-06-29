# API

## Backend

Base URL:

```text
http://localhost:8888
```

### Health

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "service": "trace-x-backend"
}
```

### Fund Flow

```http
GET /api/analysis/fund-flow?chain_id=1&address=0x...
```

Backend가 Etherscan V2에서 주소의 normal transaction과 ERC-20 transfer를 가져와 graph 형태로 반환합니다.

Response shape:

```json
{
  "data": {
    "nodes": [],
    "edges": []
  }
}
```

### Graph For Scoring

```http
POST /api/analysis/scoring
Content-Type: application/json
```

Request:

```json
{
  "address": "0x...",
  "chain_id": 1,
  "max_hops": 1,
  "max_addresses_per_direction": 10
}
```

### Risk Scoring Through Backend

```http
POST /api/analysis/risk-scoring
Content-Type: application/json
```

Request:

```json
{
  "address": "0x...",
  "chain_id": 1,
  "max_hops": 1,
  "max_addresses_per_direction": 10,
  "analysis_type": "basic"
}
```

Response shape:

```json
{
  "data": {
    "target_address": "0x...",
    "risk_score": 30,
    "risk_level": "medium",
    "risk_tags": [],
    "fired_rules": [],
    "explanation": "...",
    "completed_at": "2026-06-29T00:00:00Z",
    "timestamp": "...",
    "chain_id": 1,
    "value": 0
  }
}
```

## Risk Scoring API

Base URL:

```text
http://localhost:5001
```

### Health

```http
GET /health
```

### Address Analysis

```http
POST /api/analyze/address
Content-Type: application/json
```

Request:

```json
{
  "address": "0x...",
  "chain_id": 1,
  "transactions": [
    {
      "tx_hash": "0x...",
      "chain_id": 1,
      "timestamp": "2026-06-29T00:00:00Z",
      "block_height": 0,
      "target_address": "0x...",
      "counterparty_address": "0x...",
      "label": "unknown",
      "is_sanctioned": false,
      "is_known_scam": false,
      "is_mixer": false,
      "is_bridge": false,
      "amount_usd": 0,
      "asset_contract": "0xETH"
    }
  ],
  "analysis_type": "basic"
}
```

`analysis_type`:

- `basic`: 기본 룰 중심, 빠른 분석
- `advanced`: topology 등 무거운 분석 포함

## Known Scope

현재 정리본의 핵심 데모 경로는 주소 기반 Ad-hoc 분석입니다. 프론트 코드에 남아 있는 transaction-hash 기반 helper는 후순위 기능이며, Backend의 공식 API 계약에는 아직 포함하지 않습니다.
