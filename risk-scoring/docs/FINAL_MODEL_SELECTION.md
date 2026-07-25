# 8단계: 최종 모델 선정

6~7단계에서 이미 근거가 다 나와서 이 문서는 결정 사항만 짧게 정리한다.

## 선정 결과

| 항목 | 값 |
|---|---|
| 모델 | `HistGradientBoostingClassifier` (scikit-learn) |
| 하이퍼파라미터 | `max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0` |
| 피처 | 15개 (기존 그래프 통계 11 + 신규 4: `peel_chain_max_length/count`, `amount/frequency_deviation_score`) |
| 결측치 처리 | 임퓨테이션 없음 — 모델이 NaN을 자체 분기 조건으로 학습 |
| 등급 임계값 | score(0~100) 기준 low<20 / medium 20~50 / high 50~80 / critical≥80 |

## 왜 이 모델인가 (요약, 근거는 MODEL_TRAINING.md/TEST_EVALUATION.md)

1. **6단계 CV**: LogisticRegression/RandomForest 대비 6개 지표(accuracy/precision/recall/f1/ROC-AUC/PR-AUC) 전부 우위 — 특히 결측치를 임퓨테이션 없이 다뤄서 `amount_deviation_score` 등의 결측치 편향(FEATURE_ENGINEERING.md)을 흐리지 않았다는 명확한 구조적 이유가 있음.
2. **어블레이션**: 신규 피처 4개가 실제로 PR-AUC를 +0.65%p 끌어올림(과장 없이 작지만 실재).
3. **7단계 test 평가**: CV 평균과 비슷하거나 살짝 높은 test 성능(accuracy 0.970, PR-AUC 0.973) — 과적합도, GOG 때 같은 의심스러운 수치도 아님.
4. **하이퍼파라미터 튜닝이 기본값에서 거의 안 움직임** — 특정 test/val 분포에 억지로 맞춘 결과가 아니라는 방증.

## 프로덕션 아티팩트

7단계 성능 수치(test 지표)는 **train+val(5,239개)로만 학습한 모델**을 test(926개)에 평가한 것 — 이제 평가가 끝났으니 test를 더 아껴둘 이유가 없어서, 실제로 서비스에 실을 모델은 **train+val+test 전부(6,165개)**로 다시 학습함. 즉 "보고된 성능 수치"와 "실제 배포 아티팩트"는 설정은 같지만 학습에 쓴 데이터 양이 다른 별개의 모델 — 이 구분을 명시해두지 않으면 나중에 "왜 실제론 문서 수치랑 다르지"라는 혼란이 생기므로 `models/ml_risk_model_metadata.json`에도 그대로 기록해둠.

- `models/ml_risk_model.joblib` — 학습된 파이프라인 (377KB)
- `models/ml_risk_model_metadata.json` — 피처 목록, log1p 대상 컬럼, 등급 임계값, 학습 데이터 출처, "보고된 성능은 이 아티팩트가 아니라 train+val 모델 기준" 명시

10단계(API 통합)에서 이 두 파일을 그대로 로드해서 씀.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/train_final_model.py
```
