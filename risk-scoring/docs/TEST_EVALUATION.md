# 7단계: Test Set 최종 평가 + 임계값 설정

**test set(926개)을 여기서 처음이자 마지막으로 열어봄.** 모델 설정(하이퍼파라미터, 피처셋)은 6단계에서 train+val CV만으로 이미 확정한 것을 그대로 사용 — test 결과를 보고 재조정하지 않음(그러면 test가 사실상 val이 되어버려 이번에 고치려던 GOG의 문제를 그대로 반복하게 됨).

## 1. 최종 학습

- `train`(4,315) + `val`(924) = 5,239개 전체로 재학습 (6단계 CV는 이 pool을 5-fold로 쪼개 평가한 것이었고, 최종 모델은 쪼개지 않고 전부 사용)
- 설정: `HistGradientBoostingClassifier(max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0)` — `MODEL_TRAINING.md`에서 확정한 그대로

## 2. Test 결과

| 지표 | CV(train+val, 5-fold 평균) | **test(최초 1회)** |
|---|---|---|
| accuracy | 0.9647 | **0.9698** |
| precision | 0.9072 | **0.9302** |
| recall | 0.9060 | **0.9091** |
| f1 | 0.9064 | **0.9195** |
| ROC-AUC | 0.9868 | **0.9925** |
| PR-AUC(avg precision) | 0.9598 | **0.9729** |

**test 결과가 CV 평균보다 오히려 살짝 높음** — 과적합 징후 없음(과적합됐다면 test가 CV보다 눈에 띄게 낮게 나왔을 것). 그렇다고 GOG 때처럼 99%대의 의심스러운 숫자도 아니고, 6단계 CV가 예측한 범위(fold 표준편차 이내) 안에 있는 자연스러운 결과.

Confusion matrix (threshold=0.5): TN=738, FP=12, FN=16, TP=160 — FPR 1.60%, FNR 9.09%.

## 3. 등급 임계값 설정 (score = 확률×100, 0~100)

Score 분포가 클래스 간에 거의 안 겹침 — normal은 median 0.2 / p90 2.9, fraud는 median 97.5 / p10 63.1. 이 간격을 이용해 룰 엔진과 같은 4단계 명명(`low`/`medium`/`high`/`critical`, `core/scoring/address_analyzer.py`의 `_determine_risk_level`과 이름은 맞추되 **컷오프는 독립적** — 게이팅+병렬 표시 아키텍처에서 룰 점수와 ML 점수는 같은 척도를 공유하지 않음)으로 나눔:

| 등급 | 구간 | fraud (176개 중) | normal (750개 중) |
|---|---|---|---|
| low | [0, 20) | 6 (3.4%) | 730 (97.3%) |
| medium | [20, 50) | 10 (5.7%) | 8 (1.1%) |
| high | [50, 80) | 17 (9.7%) | 6 (0.8%) |
| critical | [80, 100] | **143 (81.3%)** | 6 (0.8%) |

- **critical 하나만으로 fraud의 81.3%를 잡고, normal 오탐은 0.8%(6/750)뿐** — 가장 실무적으로 유용한 단일 컷오프.
- **high 이상(score≥50)으로 넓히면 recall 90.9%**(threshold=0.5 결과와 정확히 일치, 내부 정합성 확인됨), normal 오탐 누적 2.4%(18/750).
- **low 등급인데 실제 fraud인 6개**(FN 상당수)는 9단계 SHAP에서 왜 이 주소들이 낮게 나왔는지 개별 확인 예정 — 모델의 맹점을 아는 게 최종 배포 전 중요.

## 4. 다음 단계와의 연결

- 이 4단계 등급은 **ML 트랙 전용**. 룰북(C/E/B축) 발동 결과는 별도 등급으로 병렬 표시되고, 컴플라이언스 룰(제재 직접 접촉 등)이 발동하면 이 ML 등급과 무관하게 강제 override(게이팅) — 10단계에서 구현.
- 8단계에서 이 test 결과를 근거로 최종 모델 확정 문서 작성.
- `data/dataset/test_evaluation_result.json`에 지표 원본 저장 (재현/추적용).

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/build_feature_matrix.py --split test   # 최초 1회만 실행됨 (이미 실행됨)
python3 scripts/evaluate_test_set.py
```

**주의**: 이 스크립트를 다시 실행하는 건 재현성 확인 목적일 때만 — 결과를 보고 6단계로 돌아가 모델을 다시 튜닝하면 test set의 의미가 사라짐.
