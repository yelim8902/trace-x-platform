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
    "fired_rules": [
      {
        "rule_id": "C-001",
        "score": 30,
        "count": 1,
        "name": "Sanction Direct Touch",
        "axis": "C",
        "severity": "HIGH",
        "description": "...",
        "legal_basis": "특금법 제4조의2(의심거래보고) — 제재 대상자와의 직접 거래; ..."
      }
    ],
    "explanation": "...",
    "completed_at": "2026-06-29T00:00:00Z",
    "timestamp": "...",
    "chain_id": 1,
    "value": 0,
    "ml": {
      "ml_score": 86.9,
      "ml_risk_level": "critical",
      "ml_top_features": [
        {
          "feature": "fan_in_count",
          "value": 12.0,
          "shap_value": 5.18,
          "direction": "increases_risk",
          "explanation": "여러 주소로부터 자금이 한 곳으로 집중 유입됨 (자금 분산 후 합류 패턴)"
        }
      ]
    },
    "gating": {
      "triggered": false,
      "rule_ids": []
    },
    "combined_explanation": "[룰 판단] ... [ML 판단] ... [종합] ..."
  }
}
```

`ml`/`gating`은 `fired_rules`/`risk_score`와 완전히 독립적으로 계산되는 병렬 트랙입니다 — 하나의 숫자로 합치지 않습니다. `gating.triggered`가 true면 컴플라이언스 룰(제재·믹서 직접 노출)이 발동했다는 뜻으로, `ml_risk_level`이 낮아도 최우선 검토 대상입니다. `combined_explanation`은 두 트랙의 판단과 권장 조치를 결정론적 템플릿으로 합친 서술(LLM 미사용)이며, 기존 `explanation` 필드는 하위 호환을 위해 그대로 유지됩니다. 자세한 설계 근거는 [`risk-scoring/docs/GATING_INTEGRATION.md`](../risk-scoring/docs/GATING_INTEGRATION.md) 참고.

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

Response는 위 "Risk Scoring Through Backend"의 `data` 객체와 동일한 스키마입니다(`risk_score`/`fired_rules`, `ml`, `gating`, `combined_explanation`을 최상위 필드로 반환 — `{"data": ...}`로 감싸지 않는다는 점만 다름).

## Known Scope

현재 정리본의 핵심 데모 경로는 주소 기반 Ad-hoc 분석입니다. 프론트 코드에 남아 있는 transaction-hash 기반 helper는 후순위 기능이며, Backend의 공식 API 계약에는 아직 포함하지 않습니다.
