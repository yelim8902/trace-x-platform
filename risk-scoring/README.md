# AML Risk Engine

CEX를 위한 주소 추적 및 리스크 스코어링 시스템

룰 베이스드 + AI 집계 방식의 AML (Anti-Money Laundering) 스코어링 엔진

---

## 프로젝트 개요

이 프로젝트는 중앙화 거래소(CEX)를 위한 AML 리스크 스코어링 시스템입니다. 블록체인 주소의 거래 히스토리를 분석하여 리스크를 평가하고, TRACE-X 룰북 기반으로 점수를 계산합니다.

### 주요 기능

- **주소 기반 리스크 분석**: 주소의 거래 히스토리를 분석하여 리스크 스코어 계산
- **2가지 분석 모드**:
  - **기본 모드 (1-hop)**: 빠른 응답 (1-2초), 실시간 대시보드 적합
  - **Multi-hop 모드 (3-hop)**: 정밀 분석 (3-8초), 복잡한 패턴 탐지 (정확도 30-50% 향상)
- **TRACE-X 룰북 기반**: Compliance, Exposure, Behavior 3축 룰 평가
- **그래프 패턴 탐지**: Layering Chain, Cycle, Fan-in/Fan-out 등
- **OFAC SDN 리스트 통합**: 제재 대상 주소 자동 탐지

> 💡 **Multi-hop 모드 권장**: 복잡한 세탁 패턴 탐지를 위해 Multi-hop 모드 사용을 권장합니다.

> 💡 **ML 트랙**: 룰 기반 스코어링과 별개로 학습된 ML 모델(HistGradientBoosting)이 `ml`/`gating` 필드로 병렬 응답됩니다. 어떻게 만들어졌는지는 `docs/README.md`(9~10단계 문서, `MODEL_INTERPRETATION.md`/`GATING_INTEGRATION.md`) 참고.

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/paran-needless-to-say/aml-risk-engine2.git
cd aml-risk-engine2
```

### 2. 의존성 설치

```bash
# Python 3.10+ 필요
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
python3 run_server.py
```

서버가 `http://localhost:5001`에서 실행됩니다. Backend와 Frontend가 이 고정 포트를 사용하므로, 포트 충돌이 나면 기존 프로세스를 종료한 뒤 다시 실행합니다.

### 4. API 문서 확인

브라우저에서 `http://localhost:5001/api-docs` 접속 (Swagger UI)

---

## API 사용

### 시스템 구조

```
프론트엔드 → 백엔드 → 리스크 스코어링 API
              (거래 수집)    (리스크 분석)
```

**백엔드의 역할**:

1. 주소의 거래 데이터 수집 (Etherscan/Alchemy API)
2. 거래 데이터를 표준 형식으로 변환
3. 리스크 스코어링 API에 전송

**리스크 스코어링 API의 역할**:

1. 거래 데이터 분석
2. TRACE-X 룰북 기반 평가
3. 리스크 스코어 + 상세 결과 반환

---

### 주소 분석 API

**엔드포인트**: `POST /api/analyze/address`

#### 백엔드가 보내야 하는 Request 형식

**기본 형식** (필수 필드):

```json
POST /api/analyze/address

{
  "address": "0xhigh_risk_mixer_sanctioned",
  "chain_id": 1,
  "transactions": [
    {
      "tx_hash": "0xtx1_mixer",
      "chain_id": 1,
      "timestamp": "2025-11-15T00:27:17.865209Z",
      "block_height": 1000,
      "from": "0xmixer_service_123",              // 송신: Mixer
      "to": "0xhigh_risk_mixer_sanctioned",       // 수신: Target (유입!)
      "target_address": "0xhigh_risk_mixer_sanctioned",
      "counterparty_address": "0xmixer_service_123",
      "label": "mixer",
      "is_sanctioned": false,
      "is_known_scam": false,
      "is_mixer": true,
      "is_bridge": false,
      "amount_usd": 5000.0,
      "asset_contract": "0xETH"
    },
    {
      "tx_hash": "0xtx2_sanctioned",
      "chain_id": 1,
      "timestamp": "2024-01-01T10:30:00Z",
      "block_height": 1001,
      "from": "0xsanctioned_address_ofac",        // 송신: 제재 주소
      "to": "0xhigh_risk_mixer_sanctioned",       // 수신: Target (유입!)
      "target_address": "0xhigh_risk_mixer_sanctioned",
      "counterparty_address": "0xsanctioned_address_ofac",
      "label": "unknown",
      "is_sanctioned": true,
      "is_known_scam": false,
      "is_mixer": false,
      "is_bridge": false,
      "amount_usd": 3000.0,
      "asset_contract": "0xETH"
    }
  ],
  "analysis_type": "basic"
}
```

**💡 거래 방향 설명**:

- **거래 1**: `Mixer (0xmixer...) → Target (0xhigh_risk...)` - Mixer에서 Target으로 5000 USD 유입
- **거래 2**: `제재 주소 (0xsanctioned...) → Target (0xhigh_risk...)` - 제재 주소에서 Target으로 3000 USD 유입

---

### Response (리스크 스코어링이 백엔드에게 반환)

```json
{
  "target_address": "0xhigh_risk_mixer_sanctioned",
  "risk_score": 78,
  "risk_level": "high",
  "risk_tags": ["mixer_inflow", "sanction_exposure", "high_value_transfer"],
  "fired_rules": [
    { "rule_id": "E-101", "score": 25 },
    { "rule_id": "C-001", "score": 30 },
    { "rule_id": "C-003", "score": 25 }
  ],
  "explanation": "Mixer에서 5000 USD 유입, 제재 주소에서 3000 USD 유입",
  "completed_at": "2025-11-21T10:00:00Z",
  "timestamp": "2025-11-15T00:27:17Z",
  "chain_id": 1,
  "value": 8000.0,
  "ml": {
    "ml_score": 86.9,
    "ml_risk_level": "critical",
    "ml_top_features": [
      { "feature": "fan_in_count", "value": 104.0, "shap_value": 5.18, "direction": "increases_risk", "explanation": "여러 주소로부터 자금이 한 곳으로 집중 유입됨..." }
    ]
  },
  "gating": { "triggered": true, "rule_ids": ["C-001"] }
}
```

**`ml`/`gating`은 룰 트랙(`risk_score`/`risk_level`/`fired_rules`)과 완전히 별개로 계산되는 병렬 트랙입니다** — 하나의 숫자로 합치지 않습니다. `gating.triggered`가 true면 컴플라이언스 룰(제재/믹서 직접 노출)이 발동했다는 뜻이라, `ml_risk_level`이 낮아도 최우선 검토 대상입니다. 자세한 내용과 실제 검증 사례는 `docs/GATING_INTEGRATION.md` 참고.

---

### 선택사항: Multi-hop 데이터 수집 (고급 분석)

**백엔드가 더 많은 거래 데이터를 수집하면 더 정밀한 분석 가능**:

백엔드가 Target 주소뿐만 아니라 **counterparty 주소들의 거래까지 수집**하면:

- ✅ Layering Chain 패턴 탐지 (B-201)
- ✅ Cycle 패턴 탐지 (B-202)
- ✅ 리스크 탐지 정확도 30-50% 향상

**예시: 3-hop 데이터 수집**:

```json
POST /api/analyze/address

{
  "address": "0xhigh_risk_mixer_sanctioned",
  "chain_id": 1,
  "max_hops": 3,
  "analysis_type": "advanced",
  "time_window_hours": 24
}
```

**백엔드가 수집해야 하는 데이터**:

```json
{
  "address": "0xhigh_risk_mixer_sanctioned",
  "chain_id": 1,
  "transactions": [
    // 1-hop: Target의 직접 거래
    {
      "tx_hash": "0xtx1_mixer",
      "hop_level": 1,
      "from": "0xmixer_service_123", // Mixer
      "to": "0xhigh_risk_mixer_sanctioned", // → Target
      "chain_id": 1,
      "timestamp": "2025-11-15T00:27:17Z",
      "block_height": 1000,
      "label": "mixer",
      "is_sanctioned": false,
      "is_mixer": true,
      "amount_usd": 5000.0,
      "asset_contract": "0xETH"
    },

    // 2-hop: Mixer의 이전 거래 (Mixer가 어디서 받았는지)
    {
      "tx_hash": "0xtx_mixer_inflow",
      "hop_level": 2,
      "from": "0xunknown_wallet_1", // 알 수 없는 주소
      "to": "0xmixer_service_123", // → Mixer
      "chain_id": 1,
      "timestamp": "2025-11-15T00:20:00Z",
      "block_height": 999,
      "label": "unknown",
      "is_sanctioned": false,
      "is_mixer": false,
      "amount_usd": 4950.0,
      "asset_contract": "0xETH"
    },

    // 3-hop: 알 수 없는 주소의 이전 거래
    {
      "tx_hash": "0xtx_origin",
      "hop_level": 3,
      "from": "0xsanctioned_address_ofac", // 제재 주소!
      "to": "0xunknown_wallet_1", // → 알 수 없는 주소
      "chain_id": 1,
      "timestamp": "2025-11-15T00:10:00Z",
      "block_height": 998,
      "label": "unknown",
      "is_sanctioned": true,
      "is_mixer": false,
      "amount_usd": 4900.0,
      "asset_contract": "0xETH"
    }
  ]
}
```

**💡 3-hop 경로 추적**:

```
제재 주소 (0xsanctioned...)  [hop 3]
    ↓ 4900 USD
알 수 없는 주소 (0xunknown...)  [hop 2]
    ↓ 4950 USD
Mixer (0xmixer...)  [hop 1]
    ↓ 5000 USD
Target (0xhigh_risk...)  [분석 대상]
```

→ **Layering Chain 패턴 탐지!** (B-201 룰 발동)

**백엔드가 Multi-hop 데이터를 수집하면**:

- ✅ 복잡한 세탁 경로 추적 가능
- ✅ Layering Chain (B-201), Cycle (B-202) 패턴 탐지
- ✅ 리스크 탐지 정확도 30-50% 향상

**참고**: 이 예시의 target_address/from/to는 설명용 가상 주소입니다. 실제 Multi-hop 데이터를 어떻게 수집하고 검증했는지는 `docs/README.md`의 데이터 수집 문서들을 참고하세요.

---

### 단일 트랜잭션 스코어링 API

**엔드포인트**: `POST /api/score/transaction`

주소 전체가 아닌 **하나의 거래만** 분석하는 API입니다.

**백엔드가 보내는 Request**:

```json
{
  "tx_hash": "0xtx1_mixer",
  "chain_id": 1,
  "timestamp": "2025-11-15T00:27:17.865209Z",
  "block_height": 1000,
  "target_address": "0xhigh_risk_mixer_sanctioned",
  "counterparty_address": "0xmixer_service_123",
  "label": "mixer",
  "is_sanctioned": false,
  "is_known_scam": false,
  "is_mixer": true,
  "is_bridge": false,
  "amount_usd": 5000.0,
  "asset_contract": "0xETH"
}
```

**응답 예시**:

```json
{
  "target_address": "0xhigh_risk_mixer_sanctioned",
  "risk_score": 100,
  "risk_level": "critical",
  "risk_tags": ["mixer_inflow", "high_value_transfer"],
  "fired_rules": [
    { "rule_id": "E-101", "score": 32 },
    { "rule_id": "C-003", "score": 25 },
    { "rule_id": "C-004", "score": 20 },
    { "rule_id": "B-101", "score": 15 },
    { "rule_id": "B-501", "score": 6 }
  ],
  "explanation": "1-hop sanctioned mixer에서 5,000USD 이상 유입...",
  "completed_at": "2025-11-20T16:59:19Z",
  "timestamp": "2025-11-15T00:27:17.865209Z",
  "chain_id": 1,
  "value": 5000.0
}
```

---

### 필드 상세 설명

#### 백엔드가 반드시 제공해야 하는 필드

**최상위 레벨**:

- `address` (string): 분석 대상 주소
- `chain_id` (integer): 체인 ID (1=Ethereum, 42161=Arbitrum 등)
- `transactions` (array): 거래 배열

**transactions 배열의 각 거래**:

```json
{
  "tx_hash": "0x123...",
  "chain_id": 1,
  "timestamp": "2025-11-17T12:34:56Z",
  "block_height": 21039493,
  "target_address": "0xTarget",
  "counterparty_address": "0xMixer1",
  "label": "mixer",
  "is_sanctioned": false,
  "is_known_scam": false,
  "is_mixer": true,
  "is_bridge": false,
  "amount_usd": 5000.0,
  "asset_contract": "0xETH"
}
```

#### 백엔드가 준비해야 할 것

1. **거래 데이터 수집**: Etherscan/Alchemy API로 주소의 거래 수집
2. **라벨링**: `label`, `is_sanctioned`, `is_mixer` 등 판단
3. **USD 환산**: `amount_usd` 계산 (시세 API 사용)
4. **방향 명확화**: `from`, `to` 주소 정확히 구분

자세한 내용은 `docs/README.md`(문서 전체 가이드)를 참고하세요.

---

## 프로젝트 구조

```
risk-scoring/
│
├── api/                          # API 서버
│   ├── app.py                    # Flask 서버 메인
│   └── routes/                   # API 라우트
│       ├── scoring.py            # 단일 트랜잭션 스코어링
│       └── address_analysis.py  # 주소 분석 (룰 + ML + 게이팅)
│
├── core/                         # 핵심 로직
│   ├── scoring/                  # 스코어링 엔진
│   │   ├── engine.py             # 단일 트랜잭션 스코어링
│   │   ├── address_analyzer.py   # 주소 기반 룰 분석
│   │   └── ml_scorer.py          # ML 스코어러 (룰과 독립, 병렬 표시용)
│   ├── rules/                    # 룰 평가
│   │   ├── evaluator.py          # 룰 평가기
│   │   └── loader.py             # 룰북 로더
│   ├── aggregation/               # 집계/피처 모듈
│   │   ├── window.py             # 윈도우 기반 집계
│   │   ├── bucket.py             # 버킷 기반 집계
│   │   ├── topology.py           # 그래프 구조 분석
│   │   ├── peel_chain.py         # peel chain 패턴 (ML 피처)
│   │   ├── deviation_features.py # 금액/빈도 이상치 (ML 피처)
│   │   └── exposure_distance.py  # 제재/믹서 hop 거리 (게이팅용)
│   └── data/                     # 데이터 로더
│       └── lists.py              # 리스트 관리
│
├── rules/                        # 룰북 정의
│   └── tracex_rules.yaml         # TRACE-X 룰북
│
├── models/                       # 프로덕션 ML 모델 아티팩트
│   ├── ml_risk_model.joblib       # 학습된 HistGradientBoosting 파이프라인
│   └── ml_risk_model_metadata.json
│
├── data/                         # 데이터
│   ├── lists/                    # 블랙리스트/화이트리스트
│   │   ├── sdn_addresses.json    # OFAC SDN 리스트
│   │   └── cex_addresses.json    # CEX 주소 리스트
│   ├── dataset/                  # 학습/평가용 데이터셋 (gitignore, 스크립트로 재생성)
│   └── cache/                    # 캐시 (자동 생성)
│
├── scripts/                      # 파이프라인 스크립트 (docs/README.md 참고)
│   ├── data_collection/          # 데이터 수집 (XBlock, ETH-Labels-2026)
│   ├── eda/                      # EDA
│   ├── features/                 # 피처 엔지니어링
│   ├── model/                    # 모델 학습/평가/해석
│   └── (최상위)                  # 룰 엔진 유지보수 스크립트
│
├── docs/                         # 문서 — **docs/README.md**에서 전체 가이드 확인
│
├── legacy/                       # 폐기된 GOG(Graph of Graphs) 실험 코드 (재현 불가로 폐기, legacy/README.md 참고)
│
├── run_server.py                 # 서버 실행 스크립트
├── requirements.txt              # Python 의존성
└── README.md                     # 프로젝트 개요 (현재 파일)
```

---

## 주요 기능

### 1. 기본 스코어링 (빠름)

- 응답 시간: 1-2초
- 기본 룰만 평가
- 실시간 탐지, 대시보드에 적합
- `analysis_type: "basic"` 사용

### 2. 심층 분석 (느림)

- 응답 시간: 5-30초
- 모든 룰 평가 (그래프 구조 분석 포함)
- 수동 탐지, 상세 조사에 적합
- `analysis_type: "advanced"` 사용

### 3. TRACE-X 룰북 기반 평가

- Compliance (C): 제재, 고액 거래 관련 룰
- Exposure (E): Mixer, 제재 주소 노출 관련 룰
- Behavior (B): 거래 패턴, 그래프 구조 관련 룰

---

## 테스트

### Swagger UI 사용

1. 서버 실행: `python3 run_server.py`
2. 브라우저에서 `http://localhost:5001/api-docs` 접속
3. "Try it out" 버튼으로 API 테스트

### curl 사용

```bash
# 주소 분석 (위 "Response" 예시와 같은 payload)
curl -X POST http://localhost:5001/api/analyze/address \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0xhigh_risk_mixer_sanctioned",
    "chain_id": 1,
    "transactions": [
      {"tx_hash": "0xtx1", "chain_id": 1, "timestamp": "2025-11-15T00:27:17Z",
       "block_height": 1000, "from": "0xmixer_service_123", "to": "0xhigh_risk_mixer_sanctioned",
       "label": "mixer", "is_sanctioned": false, "is_known_scam": false, "is_mixer": true,
       "is_bridge": false, "amount_usd": 5000.0, "asset_contract": "0xETH"}
    ],
    "analysis_type": "basic"
  }'

# 단일 트랜잭션 스코어링
curl -X POST http://localhost:5001/api/score/transaction \
  -H "Content-Type: application/json" \
  -d '{"tx_hash": "0xtx1", "chain_id": 1, "timestamp": "2025-11-15T00:27:17Z",
       "block_height": 1000, "target_address": "0xhigh_risk_mixer_sanctioned",
       "counterparty_address": "0xmixer_service_123", "label": "mixer",
       "is_sanctioned": false, "is_known_scam": false, "is_mixer": true,
       "is_bridge": false, "amount_usd": 5000.0, "asset_contract": "0xETH"}'
```

---

## 문서

이 리스크 스코어링 엔진은 표준 10단계 ML 라이프사이클(문제 정의 → 데이터 수집 → EDA → 분할 → 피처 엔지니어링 → 학습 → 평가 → 선정 → 해석 → 게이팅 통합)로 재구축됐습니다. 전체 문서 가이드는 **[`docs/README.md`](docs/README.md)**에서 순서대로 확인하세요 — 룰북/데이터/피처/모델/SHAP 해석까지 실제 실행한 명령어와 검증된 수치가 각 단계별로 기록돼 있습니다.

폐기된 이전 실험(GOG 논문 데이터 기반)은 `legacy/`에 보관돼 있으며, 왜 폐기했는지는 `docs/DATA_COLLECTION_OVERVIEW.md`에 설명돼 있습니다.

---

## 체인 ID 매핑

| Chain ID | 체인 이름         |
| -------- | ----------------- |
| 1        | Ethereum Mainnet  |
| 42161    | Arbitrum One      |
| 43114    | Avalanche C-Chain |
| 8453     | Base Mainnet      |
| 137      | Polygon Mainnet   |
| 56       | BSC Mainnet       |
| 250      | Fantom Opera      |
| 10       | Optimism Mainnet  |
| 81457    | Blast Mainnet     |

---

## 라이선스

MIT License

---

## 기여

이 프로젝트는 CEX를 위한 AML 리스크 스코어링 시스템입니다.
