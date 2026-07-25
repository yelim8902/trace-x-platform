"""
6단계: 모델 학습/튜닝 — train+val 전체를 stratified K-fold CV로 비교.

test set(926개)은 여기서 절대 건드리지 않음 — 7단계(최종 평가)까지 보류.

- 단일 750개 test split으로 99% 나왔던 예전 GOG 결과가 의심스러웠던 이유가
  "분산을 확인할 방법이 없었다"는 것 — 여기서는 5-fold CV로 fold별 분산을 직접 봄.
- 세 모델 비교: LogisticRegression/RandomForestClassifier(median 임퓨테이션 필요)
  vs HistGradientBoostingClassifier(NaN 네이티브 처리, amount/frequency_deviation_score의
  결측치 편향을 임퓨테이션으로 감추지 않음 — FEATURE_ENGINEERING.md 참고).
- 그래프/금액 기반 피처는 log1p 변환(스케일 민감한 LR에는 필요, 트리 모델은 단조변환이라
  분할에 영향 없음 — 일관성을 위해 전부 동일 파이프라인 적용).
"""
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

project_root = Path(__file__).parent.parent.parent

OLD_GRAPH_STAT_COLUMNS = [
    "fan_in_count", "fan_out_count", "pattern_score", "n_omega", "n_theta",
    "graph_nodes", "graph_edges", "avg_tx_usd", "max_tx_usd", "total_sent_usd", "total_recv_usd",
]
NEW_FEATURE_COLUMNS = [
    "peel_chain_max_length", "peel_chain_count",
    "amount_deviation_score", "frequency_deviation_score",
]
FEATURE_COLUMNS = OLD_GRAPH_STAT_COLUMNS + NEW_FEATURE_COLUMNS
LOG1P_COLUMNS = {"graph_nodes", "graph_edges", "avg_tx_usd", "max_tx_usd", "total_sent_usd", "total_recv_usd"}


def load_split(name):
    return json.load(open(project_root / f"data/dataset/feature_matrix_{name}.json"))


def to_xy(rows):
    X = np.full((len(rows), len(FEATURE_COLUMNS)), np.nan, dtype=float)
    for i, r in enumerate(rows):
        for j, col in enumerate(FEATURE_COLUMNS):
            v = r.get(col)
            if v is None:
                continue
            X[i, j] = np.log1p(v) if col in LOG1P_COLUMNS else v
    y = np.array([1 if r["ground_truth_label"] == "fraud" else 0 for r in rows])
    return X, y


def main():
    train_rows = load_split("train")
    val_rows = load_split("val")
    rows = train_rows + val_rows
    X, y = to_xy(rows)
    print(f"CV pool: {len(rows)}개 (train {len(train_rows)} + val {len(val_rows)}), fraud {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"피처 {len(FEATURE_COLUMNS)}개: {FEATURE_COLUMNS}")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ["accuracy", "precision", "recall", "f1", "roc_auc", "average_precision"]

    models = {
        "LogisticRegression": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ]),
        "RandomForest": Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("clf", RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=42, n_jobs=-1)),
        ]),
        "HistGradientBoosting": Pipeline([
            ("passthrough", FunctionTransformer(lambda x: x)),  # NaN 그대로 통과
            ("clf", HistGradientBoostingClassifier(random_state=42)),
        ]),
    }

    print("\n" + "=" * 70)
    print("5-fold Stratified CV 결과 (mean ± std)")
    print("=" * 70)
    for name, pipe in models.items():
        result = cross_validate(pipe, X, y, cv=cv, scoring=scoring, n_jobs=-1)
        print(f"\n[{name}]")
        for metric in scoring:
            vals = result[f"test_{metric}"]
            print(f"  {metric:<20} {vals.mean():.4f} ± {vals.std():.4f}   (folds: {[round(v,3) for v in vals]})")

    # --- 어블레이션: 신규 피처 3개(peel_chain, amount/frequency_deviation)가 실제로 기여하는가 ---
    print("\n" + "=" * 70)
    print("어블레이션 — 기존 그래프 통계만 vs 기존+신규 피처 (HistGradientBoosting)")
    print("=" * 70)
    old_idx = [FEATURE_COLUMNS.index(c) for c in OLD_GRAPH_STAT_COLUMNS]
    X_old = X[:, old_idx]
    hgb = Pipeline([("clf", HistGradientBoostingClassifier(random_state=42))])
    for label, Xi in [("기존 11개 피처만", X_old), ("기존 11개 + 신규 4개 (전체 15개)", X)]:
        result = cross_validate(hgb, Xi, y, cv=cv, scoring=scoring, n_jobs=-1)
        print(f"\n[{label}]")
        for metric in scoring:
            vals = result[f"test_{metric}"]
            print(f"  {metric:<20} {vals.mean():.4f} ± {vals.std():.4f}")

    # --- 하이퍼파라미터 튜닝 (HistGradientBoosting, average_precision 기준) ---
    print("\n" + "=" * 70)
    print("하이퍼파라미터 튜닝 (HistGradientBoosting, GridSearchCV, scoring=average_precision)")
    print("=" * 70)
    param_grid = {
        "clf__max_iter": [100, 200],
        "clf__max_depth": [None, 6],
        "clf__learning_rate": [0.05, 0.1],
        "clf__l2_regularization": [0.0, 1.0],
    }
    grid = GridSearchCV(
        Pipeline([("clf", HistGradientBoostingClassifier(random_state=42))]),
        param_grid, cv=cv, scoring="average_precision", n_jobs=-1,
    )
    grid.fit(X, y)
    print(f"best params: {grid.best_params_}")
    print(f"best CV average_precision: {grid.best_score_:.4f}")

    # 튜닝된 최적 설정으로 전체 6개 지표 재확인
    best_pipe = grid.best_estimator_
    result = cross_validate(best_pipe, X, y, cv=cv, scoring=scoring, n_jobs=-1)
    print("\n[튜닝된 최적 모델 — 전체 지표]")
    for metric in scoring:
        vals = result[f"test_{metric}"]
        print(f"  {metric:<20} {vals.mean():.4f} ± {vals.std():.4f}")

    # --- Permutation importance (train/val 단일 분할로 빠르게 확인, 정식 SHAP은 9단계) ---
    print("\n" + "=" * 70)
    print("Permutation Importance (참고용 — 정식 해석은 9단계 SHAP)")
    print("=" * 70)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    best_pipe.fit(X_tr, y_tr)
    perm = permutation_importance(best_pipe, X_te, y_te, scoring="average_precision", n_repeats=20, random_state=42, n_jobs=-1)
    order = np.argsort(perm.importances_mean)[::-1]
    for i in order:
        print(f"  {FEATURE_COLUMNS[i]:<28} {perm.importances_mean[i]:+.4f} ± {perm.importances_std[i]:.4f}")


if __name__ == "__main__":
    main()
