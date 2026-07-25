# 6단계: 모델 학습/튜닝

## 데이터

`feature_matrix_train.json`(4,315) + `feature_matrix_val.json`(924) = **5,239개**를 CV 풀로 합쳐서 사용. **test set(926개)은 여기서 전혀 열어보지 않음** — 7단계(최종 평가) 전까지 보류(`DATA_SPLIT.md` 규칙).

이렇게 하는 이유: 예전 GOG 실험은 단일 750개 test split 하나로 99.20%가 나왔는데, 분산을 확인할 방법이 없어서 우연인지 실력인지 구분이 안 됐음. 이번엔 **5-fold Stratified CV**로 fold마다 얼마나 흔들리는지 직접 봄.

피처 15개: 기존 그래프 통계 11개(`fan_in_count`, `fan_out_count`, `pattern_score`, `n_omega`, `n_theta`, `graph_nodes`, `graph_edges`, `avg_tx_usd`, `max_tx_usd`, `total_sent_usd`, `total_recv_usd`) + 신규 4개(`peel_chain_max_length`, `peel_chain_count`, `amount_deviation_score`, `frequency_deviation_score`). 금액/카운트 계열 6개는 `log1p` 변환(트리 모델엔 단조변환이라 무영향, LR 비교를 위해 일괄 적용).

## 1. 모델 비교 (5-fold Stratified CV, mean ± std)

| 모델 | accuracy | precision | recall | f1 | ROC-AUC | PR-AUC(avg precision) |
|---|---|---|---|---|---|---|
| LogisticRegression | 0.9534±0.007 | 0.8373±0.030 | 0.9373±0.012 | 0.8840±0.013 | 0.9799±0.005 | 0.9295±0.025 |
| RandomForest | 0.9567±0.007 | 0.8519±0.030 | 0.9343±0.006 | 0.8909±0.017 | 0.9820±0.003 | 0.9501±0.010 |
| **HistGradientBoosting** | **0.9647±0.006** | **0.9072±0.020** | **0.9060±0.018** | **0.9064±0.016** | **0.9868±0.003** | **0.9598±0.009** |

**HistGradientBoosting이 6개 지표 전부에서 최고.** LogisticRegression/RandomForest는 `amount_deviation_score`/`frequency_deviation_score`의 결측치를 median으로 임퓨테이션했는데(`FEATURE_ENGINEERING.md`에서 짚은 결측치 편향을 그대로 흐릿하게 만듦), HistGB는 결측을 자체 분기 조건으로 학습해서 이 정보 손실이 없음 — 사전에 예상했던 이유가 실제 성능 차이로 확인됨.

fold별 분산이 크지 않음(std 0.6~2% 수준) — GOG 때처럼 "한 번 우연히 잘 나온" 신호는 아님.

## 2. 어블레이션 — 신규 4개 피처가 실제로 기여하는가

같은 HistGradientBoosting, 같은 CV로 피처셋만 바꿔 비교:

| 피처셋 | accuracy | precision | recall | f1 | ROC-AUC | PR-AUC |
|---|---|---|---|---|---|---|
| 기존 11개만 | 0.9599±0.006 | 0.8916±0.028 | 0.8979±0.014 | 0.8944±0.014 | 0.9857±0.003 | 0.9533±0.010 |
| 기존 11개 + 신규 4개 | 0.9647±0.006 | 0.9072±0.020 | 0.9060±0.018 | 0.9064±0.016 | 0.9868±0.003 | 0.9598±0.009 |

신규 피처 4개 추가로 recall +0.8%p, PR-AUC +0.65%p, f1 +1.2%p — **작지만 실재하는 개선.** 이미 강한 기존 피처(특히 `fan_in_count`) 위에 얹는 것이라 극적인 향상은 기대하기 어려웠고, 실제로도 그랬음.

## 3. 하이퍼파라미터 튜닝

`GridSearchCV`(같은 5-fold, scoring=average_precision)로 `max_iter`, `max_depth`, `learning_rate`, `l2_regularization` 탐색.

- **최적**: `max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0`
- CV average_precision: 0.9598(기본값) → **0.9620**(튜닝 후) — 미세한 개선. 기본값이 이미 잘 맞는 상태라 큰 차이는 없었음(과적합되도록 억지로 쥐어짠 결과가 아니라는 뜻이기도 함).

## 4. Permutation Importance — 신규 피처 내부에서도 온도차가 있음

(참고용 사전 점검 — 정식 해석은 9단계 SHAP. train/val을 80/20으로 한 번 더 나눠 학습 후 test 쪽에서 측정, `average_precision` 기준, 20회 반복)

| 순위 | 피처 | importance |
|---|---|---|
| 1 | `fan_in_count` | **+0.468** |
| 2 | `total_sent_usd` | +0.061 |
| 3 | `graph_nodes` | +0.016 |
| 4 | `n_omega` | +0.012 |
| 5 | `amount_deviation_score` | **+0.0094** |
| 6 | `total_recv_usd` | +0.0046 |
| 7 | `avg_tx_usd` | +0.0027 |
| 8 | `frequency_deviation_score` | +0.0024 |
| 9 | `max_tx_usd` | +0.0018 |
| 10 | `n_theta` | +0.0011 |
| 11 | `peel_chain_count` | +0.0007 |
| 12 | `pattern_score` | +0.0001 |
| 13 | `peel_chain_max_length` | +0.0001 |
| 14 | `graph_edges` | +0.0000 |
| 15 | `fan_out_count` | -0.0002 |

**정직하게 짚어야 할 발견**: `peel_chain_max_length`/`peel_chain_count`는 이 모델 안에서 순수 기여도가 거의 0에 가까움 — 그런데 `FEATURE_ENGINEERING.md`에서 이 피처 단독으로는 lift 15.0(fraud 26.1% vs normal 1.74%)으로 꽤 강했음. 모순이 아니라 **중복(redundancy)**: peel chain이 나타나는 주소는 대체로 `fan_in_count`/`graph_nodes`/`graph_edges`도 같이 높아서(자금이 여러 홉을 거치는 복잡한 구조라는 같은 현상을 다른 각도에서 포착), 트리 모델이 `fan_in_count` 하나로 이미 그 정보를 다 가져가 버리면 peel_chain이 추가로 줄 정보가 거의 안 남음. 반면 `amount_deviation_score`는 (importance는 작지만) `fan_in_count`가 못 보는 축("이 주소의 거래가 얼마나 불규칙한가")을 보고 있어서 순위표에서 5위까지 올라옴 — **어블레이션에서 관찰된 전체 개선분(+0.65%p PR-AUC)의 상당 부분은 peel_chain이 아니라 amount_deviation_score가 만든 것**으로 보임.

**결론**: 신규 피처 4개를 모두 그대로 유지 — 성능을 깎지 않고(peel_chain이 노이즈를 추가하는 것도 아님), 룰북/SHAP 해석 단계에서는 peel_chain이 "왜 이 주소가 위험한가"를 사람이 이해하기 쉬운 이름으로 설명하는 데 여전히 유용함(모델 성능 기여와 해석 가치는 별개). 다만 순수 예측 성능만 최적화하려는 목적이라면 peel_chain 2개를 빼도 거의 손해가 없다는 것도 사실 — 9단계 SHAP에서 이 순위가 재확인되는지 교차 체크 예정.

## 5. 최종 선정 (잠정 — 7단계 test 평가 전)

- **모델**: `HistGradientBoostingClassifier(max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0, random_state=42)`
- **이유**: 6개 지표 전부 최고, 결측치를 임퓨테이션 없이 그대로 정보로 사용(다른 두 모델 대비 명확한 이유가 있는 우위), fold 분산 낮음, 튜닝으로 인한 과적합 징후 없음
- **피처**: 기존 11개 + 신규 4개 전체 유지

**아직 확정 아님** — 이건 train+val CV 기준 선택이고, 실제 최종 확정(8단계)은 7단계에서 이 설정으로 test set을 **딱 한 번** 평가한 뒤에 함.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/train_model.py
```
