# 10단계: 게이팅 + 병렬 표시 — 라이브 API 통합 (백엔드만)

이번 단계는 **백엔드 API 응답 스키마에 필드를 추가하는 것까지만** 함 — 프론트엔드 연동은 별도 단계로 미룸(사용자 결정: 스키마/게이팅을 먼저 API 레벨에서 curl로 검증하고, 검증되면 프론트를 그 위에 얹기).

## 아키텍처

- `core/scoring/ml_scorer.py` (신규): `AddressAnalyzer`(룰 엔진)와 완전히 독립적으로 동작하는 ML 스코어러. 서로의 점수에 관여하지 않음.
- `api/routes/address_analysis.py`: 라우트 레벨에서 두 결과를 합쳐 응답 생성 — **하나의 숫자로 블렌딩하지 않고 별도 필드로 병렬 반환**.
- 게이팅: `GATING_RULE_IDS = {"C-001", "E-101", "E-102"}`(제재 직접 접촉/믹서 직접 노출/간접 제재 노출) 중 하나라도 발동하면 `gating.triggered=true` — ML 점수와 무관하게 이 신호를 최우선으로 처리해야 함을 명시. 5단계에서 이 3개 노출 피처를 "ML 학습 피처가 아니라 게이팅 룰로 다룬다"고 확정했던 것의 실제 구현.

## API 응답 스키마 변경 (추가만, 기존 필드 무변경)

```json
{
  "target_address": "...", "risk_score": 29, "risk_level": "low",
  "risk_tags": [...], "fired_rules": [...], "explanation": "...",
  "ml": {
    "ml_score": 98.6,
    "ml_risk_level": "critical",
    "ml_top_features": [
      {"feature": "fan_in_count", "value": 12.0, "shap_value": 5.22, "direction": "increases_risk", "explanation": "여러 주소로부터 자금이 한 곳으로 집중 유입됨..."}
    ]
  },
  "gating": { "triggered": false, "rule_ids": [] }
}
```

## 라이브 ML 피처 계산의 한계 — peel_chain 제외

`amount_deviation_score`/`frequency_deviation_score`와 11개 그래프 통계는 대상 주소의 1-hop 거래 리스트만으로 계산 가능(XBlock의 `graph_nodes`/`graph_edges`도 원래 1-hop 이웃 기준 정의라 그대로 재현 가능, `scripts/data_collection/extract_features_from_pkl.py`와 동일 공식을 `ml_scorer.py`에 이식). 그런데 `peel_chain_max_length`/`peel_chain_count`는 멀티홉 그래프가 있어야 계산되는데, 이 API는 대상 주소의 1-hop 거래만 입력받으므로 **항상 None으로 채움**(HistGB가 NaN을 분기 조건으로 처리). 9단계에서 이미 이 두 피처의 전역 기여도가 거의 0이라는 걸 확인했으므로 대부분 영향 없지만, `fan_in_count=0`인 예외 케이스(9단계 미탐 사례)에서는 유일한 신호일 수 있다는 것도 같은 문서에 기록해둠 — 멀티홉 데이터 소스가 붙으면 우선 보완 대상.

## 검증 (curl, 로컬 서버)

### 시나리오 1 — fan-in 패턴 (룰은 못 잡고 ML만 잡음)

12개 서로 다른 주소로부터 소액이 모이는 거래 + 대형 단일 송금 2건 입력:

| | 결과 |
|---|---|
| 룰 트랙 | `risk_level=low`(29점), `fired_rules=[B-501, C-003]` — 트랜잭션 단위 룰만 발동, 집계 패턴 룰(B-203/204는 basic 모드 윈도우 밖이라 미발동)은 못 잡음 |
| ML 트랙 | `ml_risk_level=critical`(98.6점), top feature `fan_in_count=12` |
| 게이팅 | 미발동 |

룰과 ML이 서로 다른 것을 보고 있다는 걸 실제로 보여주는 사례 — 병렬 표시 없이 룰 점수만 봤다면 이 패턴을 완전히 놓쳤을 것.

### 시나리오 2 — 제재 대상 직접 접촉 (게이팅 발동)

OFAC SDN_LIST 실제 주소로부터 소액($500) 단일 거래 입력:

| | 결과 |
|---|---|
| 룰 트랙 | `risk_level=medium`(30점) — 소액 1건이라 룰 점수 자체는 임계값을 겨우 넘는 수준 |
| ML 트랙 | `ml_risk_level=low`(1.4점) — 행동 패턴만 보면 지극히 평범한 주소 |
| 게이팅 | **`triggered=true, rule_ids=["C-001"]`** |

이게 게이팅이 필요한 이유를 정확히 보여줌 — 룰/ML 둘 다 개별로는 "그렇게 위험해 보이지 않음"으로 나오는데, "제재 대상과 직접 거래했다"는 사실 자체는 두 점수와 무관하게 즉시 최우선 처리돼야 하는 컴플라이언스 신호. 게이팅 필드가 이걸 명시적으로 신호함.

### 그 외 확인

- 빈 거래 리스트: 에러 없이 `ml_score=0.0, low` 반환
- `analysis_type=advanced`에서도 ML 트랙 정상 동작(룰 트랙만 그래프 토폴로지 분석 추가, ML은 analysis_type 무관하게 항상 동일 계산)
- 응답 시간 약 0.1초(모델/SHAP explainer가 프로세스당 1회만 로드되는 싱글턴이라 요청마다 재로드 없음)
- ML 계산 실패 시(모델 로드 실패 등) 룰 기반 응답은 그대로 반환되고 `ml.error`에 메시지만 추가 — 컴플라이언스 룰은 ML 없이도 항상 동작해야 하므로 ML 실패가 전체 요청을 죽이지 않게 함

### 확인된 기존 결함 (이번 변경과 무관)

`api/test_address_analysis.py`가 `AddressAnalyzer`의 `fired_rules`에 `name`/`count` 키를 기대하는데 실제로는 `{rule_id, score}`만 반환해서 `KeyError`로 실패함 — `git stash`로 확인한 결과 이번 세션 변경 이전부터 있던 기존 버그(커밋 `b6c4fc7` 이후 상태), 이번 10단계 작업과 무관해서 범위 밖으로 두고 기록만 해둠.

## 아직 안 한 것

- **프론트엔드 연동** — 이번 단계에서 의도적으로 제외. `ml`/`gating` 필드를 실제 화면에 어떻게 나란히 보여줄지는 별도 단계.
- `analysis_type=advanced`의 그래프 토폴로지 분석 결과를 ML 피처(특히 peel_chain)에 연결하는 것 — 지금은 완전히 분리돼 있음.

## 재현 명령어

```bash
cd risk-scoring
PYTHONPATH=. venv/bin/python -m api.app
# 다른 터미널에서
curl -X POST http://localhost:5001/api/analyze/address -H "Content-Type: application/json" -d '{...}'
```
