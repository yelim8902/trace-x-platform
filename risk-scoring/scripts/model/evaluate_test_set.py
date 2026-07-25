"""
7단계: test set 최종 평가 + 임계값 설정. **이 스크립트는 test set을 딱 한 번만 본다.**

- 모델 설정은 6단계(MODEL_TRAINING.md)에서 train+val CV로 이미 확정한 것을 그대로 씀
  (test 결과를 보고 하이퍼파라미터를 다시 고르지 않음 — 그러면 test가 val이 되어버림)
- train+val(5,239) 전체로 최종 학습 후 test(926)에서 딱 한 번 평가
- 룰 엔진의 low/medium/high/critical 4단계 명명을 그대로 따르되, 컷오프는 규칙과
  무관하게 이 ML 점수 자체의 test set 분포를 보고 독립적으로 정함(게이팅+병렬 표시
  아키텍처 — ML 점수와 룰 점수는 같은 척도를 공유하지 않음, DATA_COLLECTION_OVERVIEW.md)
"""
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, average_precision_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline

from train_model import FEATURE_COLUMNS, load_split, to_xy

project_root = Path(__file__).parent.parent.parent

BEST_PARAMS = dict(max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0, random_state=42)


def main():
    train_rows = load_split("train")
    val_rows = load_split("val")
    test_rows = load_split("test")

    X_trainval, y_trainval = to_xy(train_rows + val_rows)
    X_test, y_test = to_xy(test_rows)

    print(f"최종 학습 pool: {len(train_rows)+len(val_rows)}개 (train+val)")
    print(f"test set (최초/유일 평가): {len(test_rows)}개, fraud {y_test.sum()} ({y_test.mean()*100:.1f}%)")

    model = Pipeline([("clf", HistGradientBoostingClassifier(**BEST_PARAMS))])
    model.fit(X_trainval, y_trainval)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    print("\n" + "=" * 70)
    print("test set 최종 지표 (threshold=0.5)")
    print("=" * 70)
    print(f"  accuracy           {accuracy_score(y_test, pred):.4f}")
    print(f"  precision          {precision_score(y_test, pred):.4f}")
    print(f"  recall             {recall_score(y_test, pred):.4f}")
    print(f"  f1                 {f1_score(y_test, pred):.4f}")
    print(f"  roc_auc            {roc_auc_score(y_test, proba):.4f}")
    print(f"  average_precision  {average_precision_score(y_test, proba):.4f}")

    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    print(f"\n  confusion matrix: TN={tn} FP={fp} FN={fn} TP={tp}")
    print(f"  FPR={fp/(fp+tn)*100:.2f}%  FNR={fn/(fn+tp)*100:.2f}%")

    print("\n" + "=" * 70)
    print("6단계 CV 예측치와 test 실측치 비교 (과적합 징후 확인)")
    print("=" * 70)
    print("  CV(train+val, 5-fold 평균)   accuracy=0.9647 precision=0.9072 recall=0.9060 f1=0.9064 roc_auc=0.9868 ap=0.9598")
    print(f"  test(최초 1회)               accuracy={accuracy_score(y_test,pred):.4f} precision={precision_score(y_test,pred):.4f} "
          f"recall={recall_score(y_test,pred):.4f} f1={f1_score(y_test,pred):.4f} roc_auc={roc_auc_score(y_test,proba):.4f} ap={average_precision_score(y_test,proba):.4f}")

    print("\n" + "=" * 70)
    print("임계값 설정 — score(0~100) = proba*100, threshold별 precision/recall")
    print("=" * 70)
    score = proba * 100
    for cutoff in [10, 20, 30, 40, 50, 60, 70, 80, 90]:
        flagged = score >= cutoff
        if flagged.sum() == 0:
            continue
        p = precision_score(y_test, flagged.astype(int))
        r = recall_score(y_test, flagged.astype(int))
        n_fraud_in = int((flagged & (y_test == 1)).sum())
        n_normal_in = int((flagged & (y_test == 0)).sum())
        print(f"  score>={cutoff:>3}  flagged={flagged.sum():>4}  precision={p:.3f}  recall={r:.3f}  (fraud {n_fraud_in}, normal {n_normal_in})")

    print("\n  score 분포 (percentile, fraud vs normal)")
    for label, mask in [("fraud", y_test == 1), ("normal", y_test == 0)]:
        s = score[mask]
        print(f"    {label:<7} p10={np.percentile(s,10):.1f} p50={np.percentile(s,50):.1f} p90={np.percentile(s,90):.1f} mean={s.mean():.1f}")

    print("\n" + "=" * 70)
    print("4단계 등급 (low/medium/high/critical) 후보 컷오프별 구간 분포")
    print("=" * 70)
    bands = [(0, 20, "low"), (20, 50, "medium"), (50, 80, "high"), (80, 101, "critical")]
    for lo, hi, name in bands:
        mask = (score >= lo) & (score < hi)
        f = int((mask & (y_test == 1)).sum())
        n = int((mask & (y_test == 0)).sum())
        print(f"  {name:<10} [{lo:>3},{hi:<3})  fraud {f:>4}/{y_test.sum()}  normal {n:>4}/{(y_test==0).sum()}")

    out = {
        "test_metrics": {
            "accuracy": float(accuracy_score(y_test, pred)),
            "precision": float(precision_score(y_test, pred)),
            "recall": float(recall_score(y_test, pred)),
            "f1": float(f1_score(y_test, pred)),
            "roc_auc": float(roc_auc_score(y_test, proba)),
            "average_precision": float(average_precision_score(y_test, proba)),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        },
        "model_params": BEST_PARAMS,
        "n_train_val": len(train_rows) + len(val_rows),
        "n_test": len(test_rows),
    }
    out_path = project_root / "data/dataset/test_evaluation_result.json"
    json.dump(out, open(out_path, "w"), indent=2)
    print(f"\n저장: {out_path}")


if __name__ == "__main__":
    main()
