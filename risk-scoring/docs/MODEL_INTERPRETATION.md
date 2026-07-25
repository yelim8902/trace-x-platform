# 9단계: 모델 해석 (SHAP) — 이 코드베이스 최초의 SHAP 구현

## 방법

`shap.TreeExplainer`로 프로덕션 모델(`models/ml_risk_model.joblib`, HistGradientBoostingClassifier)의 SHAP value를 XBlock 전체 6,165개 주소에 대해 계산. 근사가 아니라 트리 구조를 직접 순회하는 정확한 방법(model-specific exact SHAP)이라 신뢰도가 높음.

## 1. 전역 피처 중요도 — 6단계 permutation importance와 교차 검증

| 순위 | Permutation Importance (6단계, train/val 분할) | SHAP mean\|value\| (9단계, 전체 6,165개) |
|---|---|---|
| 1 | fan_in_count | **fan_in_count** |
| 2 | total_sent_usd | **total_sent_usd** |
| 3 | graph_nodes | **graph_nodes** |
| 4 | n_omega | amount_deviation_score |
| 5 | amount_deviation_score | n_omega |
| 6~9 | total_recv_usd, avg_tx_usd, frequency_deviation_score, max_tx_usd | pattern_score, frequency_deviation_score, max_tx_usd, total_recv_usd |
| 하위권 | n_theta, peel_chain_count, pattern_score, graph_edges, fan_out_count | peel_chain_max_length, avg_tx_usd, n_theta, fan_out_count, peel_chain_count, graph_edges |

**상위 3개가 서로 다른 방법(permutation vs SHAP), 다른 데이터(분할 vs 전체)에서 정확히 똑같은 순서로 나옴** — `fan_in_count`가 지배적 신호라는 게 특정 방법의 우연이 아니라 실제 모델 구조에 박혀있는 신호라는 뜻. `amount_deviation_score`도 두 방법 모두 4~5위로 일관되게 중간 정도 기여를 함 — 6단계에서 "어블레이션 개선분의 대부분은 amount_deviation_score가 만든 것으로 보임"이라 추정했던 것이 SHAP로도 재확인됨.

`peel_chain_max_length`/`peel_chain_count`는 이번에도 하위권(10위/14위) — 6단계 결론(단독 lift는 강했지만 `fan_in_count`/`graph_nodes`와 중복이라 모델 안에서는 기여가 작음) 그대로 재확인. `graph_edges`는 SHAP 기준 정확히 0.0000 — 모델이 이 피처로 분기를 만든 적이 사실상 없다는 뜻(`graph_nodes`와 상관관계가 너무 높아 완전히 대체됨).

## 2. SHAP 피처 → 사람이 읽는 설명 문구 매핑

10단계(게이팅+병렬 표시)에서 룰북의 "법적 근거" 설명과 나란히 보여줄 ML 쪽 설명 문구. `scripts/model/shap_analysis.py`의 `FEATURE_EXPLANATIONS`에 구현:

| 피처 | 설명 문구 |
|---|---|
| fan_in_count | 여러 주소로부터 자금이 한 곳으로 집중 유입됨 (자금 분산 후 합류 패턴) |
| total_sent_usd | 누적 송금액이 큼 |
| graph_nodes | 이 주소와 연결된 거래 네트워크가 큼 |
| amount_deviation_score | 거래 금액이 이 주소의 평소 패턴 대비 불규칙함 |
| peel_chain_max_length/count | 금액이 매 홉마다 줄어드는 자금 세탁 체인(peel chain) 패턴 감지 |
| (나머지 10개는 `shap_analysis.py` 참고) | |

주소별 상위 3개 SHAP 피처를 이 표로 치환하면 "왜 이 점수가 나왔는가"에 대한 사람이 읽을 수 있는 근거 문구가 자동 생성됨.

## 3. 개별 주소 예시 — 정탐/미탐/오탐

### 정탐 (critical로 맞게 잡힌 fraud, score=99.1)
```
fan_in_count=12 (SHAP +4.33, 위험도 상승): 여러 주소로부터 자금 집중 유입
pattern_score=26.67 (SHAP +0.94): 정상 패턴과의 유사도 낮음
total_sent_usd=10.68 (SHAP +0.85): 누적 송금액 큼
```
전형적인 케이스 — fan-in이 모델을 지배한다는 게 이 정탐에서도 그대로 드러남.

### 미탐 (실제 fraud인데 score=1.1, low로 분류됨) — 모델의 맹점
```
fan_in_count=0 (SHAP -1.56, 위험도 하강): fan-in 없음
peel_chain_max_length=2 (SHAP +1.45, 위험도 상승): peel chain 패턴 감지됨
graph_nodes=1.10 (SHAP -0.25): 네트워크 작음
```
**이게 이 모델의 진짜 약점을 보여줌**: peel chain 패턴이 실제로 감지됐는데도(+1.45로 위험도를 올리려 함), `fan_in_count=0`이라는 압도적인 하강 신호(-1.56) 하나가 그걸 뒤집어버림. `fan_in_count`에 대한 모델의 과도한 의존이, "fan-in 없이 peel chain만으로 자금을 옮기는" 사기 패턴을 놓치게 만드는 원인. 6단계에서 이미 "peel_chain이 모델 안에서 거의 기여를 못 한다"고 짚었는데, 이 사례는 그게 단순히 "쓸모없다"가 아니라 **"fan_in_count가 없는 경우에 한해 진짜 필요한데, 그 경우엔 fan_in_count의 반대 신호에 압도당한다"**는 더 구체적인 실패 모드였음을 보여줌.

### 오탐 (실제 normal인데 score=90.7, critical로 잘못 분류됨)
```
fan_in_count=9 (SHAP +4.17, 위험도 상승): fan-in 있음
pattern_score=29.59 (SHAP +0.86): 정상 패턴과의 유사도 낮음
total_sent_usd=10.20 (SHAP +0.66): 누적 송금액 큼
```
정탐 사례와 거의 같은 조합의 피처 값 — **정당한 사유로 fan-in이 높은 주소(예: 여러 사람에게 후원/정산을 받는 서비스 주소)는 모델이 fraud와 구분을 못 함**. 이건 ML의 구조적 한계이지 버그가 아님 — 바로 이런 케이스를 위해 애초에 "게이팅+병렬 표시" 아키텍처를 택한 것(10단계): 룰북의 화이트리스트/태그(`CEX_INTERNAL`, `MM_BOT` 등, `data/lists/address_tags.json`)가 ML 점수와 별도로 이런 케이스를 예외 처리할 수 있어야 함.

## 결론

- SHAP과 permutation importance가 상위권에서 정확히 일치 — 모델 신호가 방법론에 좌우되는 인공물이 아니라 실재함을 확인
- `fan_in_count` 의존도가 모델의 최대 강점이자 최대 약점 — 정탐/오탐 예시가 정확히 같은 메커니즘(높은 fan-in)에서 비롯됨
- `peel_chain`은 예측 기여는 작지만, 미탐 사례에서 보듯 "fan-in이 없는 사기"를 잡을 수 있는 유일한 신호였던 경우가 있음 — 순수 SHAP 기여도만으로 피처를 버리면 안 되는 이유(드물지만 중요한 경우에만 발동하는 피처는 평균 기여도가 낮게 나옴)
- 오탐 사례는 ML 단독으로는 구조적으로 못 푸는 문제(정당한 fan-in 서비스 주소)라, 룰북의 화이트리스트/태그 예외 처리가 반드시 병행돼야 함 — 10단계 설계의 직접적 근거

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/model/shap_analysis.py
```
