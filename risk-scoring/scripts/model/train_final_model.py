"""
8단계: 최종 모델 확정 — 6/7단계에서 정한 설정으로 프로덕션에 실을 아티팩트를 만든다.

중요한 구분: 7단계 test 지표(accuracy 0.970 등, TEST_EVALUATION.md)는 train+val(5,239)로
학습한 모델을 926개 test에 평가한 것 — "이 설계가 미지의 데이터에서 얼마나 잘 될지"에
대한 정직한 추정치. 반면 여기서 저장하는 실제 배포용 모델은 **train+val+test 전부(6,165개)**로
다시 학습함 — 평가가 이미 끝나서 test를 더 이상 아껴둘 이유가 없고, 데이터를 더 많이 쓰면
실제 서비스 성능은 보통 그만큼(혹은 그 이상) 좋아짐. 즉 "성능 보고 수치"와 "실제 아티팩트"가
다른 모델이라는 걸 명시적으로 알고 있어야 함 — 나중에 "왜 성능이 문서보다 다르지"라는
혼란을 막기 위함.
"""
import json
from pathlib import Path

import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline

from train_model import FEATURE_COLUMNS, LOG1P_COLUMNS, load_split, to_xy

project_root = Path(__file__).parent.parent.parent

BEST_PARAMS = dict(max_iter=100, max_depth=None, learning_rate=0.05, l2_regularization=1.0, random_state=42)

# TEST_EVALUATION.md 3절 — score(0~100) 기준, 컷오프는 룰 엔진(address_analyzer.py)과
# 이름만 같고 척도는 독립적(게이팅+병렬 표시 아키텍처).
RISK_BANDS = [
    {"level": "low", "min_score": 0, "max_score": 20},
    {"level": "medium", "min_score": 20, "max_score": 50},
    {"level": "high", "min_score": 50, "max_score": 80},
    {"level": "critical", "min_score": 80, "max_score": 100},
]


def score_to_level(score: float) -> str:
    for band in RISK_BANDS:
        if band["min_score"] <= score < band["max_score"]:
            return band["level"]
    return "critical" if score >= 80 else "low"


def main():
    all_rows = load_split("train") + load_split("val") + load_split("test")
    X, y = to_xy(all_rows)
    print(f"최종 프로덕션 모델 학습: {len(all_rows)}개 전체(train+val+test), fraud {y.sum()} ({y.mean()*100:.1f}%)")

    model = Pipeline([("clf", HistGradientBoostingClassifier(**BEST_PARAMS))])
    model.fit(X, y)

    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)
    model_path = models_dir / "ml_risk_model.joblib"
    joblib.dump(model, model_path)

    metadata = {
        "model_type": "HistGradientBoostingClassifier",
        "params": BEST_PARAMS,
        "feature_columns": FEATURE_COLUMNS,
        "log1p_columns": sorted(LOG1P_COLUMNS),
        "trained_on": "xblock train+val+test combined (6,165 addresses)",
        "risk_bands": RISK_BANDS,
        "reported_performance_source": (
            "docs/TEST_EVALUATION.md - measured on a train+val-only model evaluated "
            "against the held-out test set, NOT on this artifact (which is refit on all data)"
        ),
        "reported_test_metrics": {
            "accuracy": 0.9698, "precision": 0.9302, "recall": 0.9091,
            "f1": 0.9195, "roc_auc": 0.9925, "average_precision": 0.9729,
        },
    }
    metadata_path = models_dir / "ml_risk_model_metadata.json"
    json.dump(metadata, open(metadata_path, "w"), indent=2)

    print(f"저장: {model_path}")
    print(f"저장: {metadata_path}")


if __name__ == "__main__":
    main()
