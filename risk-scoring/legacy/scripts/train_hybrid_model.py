#!/usr/bin/env python3
"""
Hybrid 모델 학습 스크립트

Rule-based 점수 + MPOCryptoML 피처를 결합하여 최종 리스크 점수 예측

사용법:
    python scripts/train_hybrid_model.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_hybrid_features(item: Dict[str, Any]) -> np.ndarray:
    """
    Hybrid 모델용 피처 추출
    
    Rule-based 점수 + MPOCryptoML 피처를 모두 포함
    
    Args:
        item: 데이터셋 항목
    
    Returns:
        피처 벡터 (numpy array)
    """
    # 1. Rule-based 피처
    rule_score = item.get("rule_score", 0.0)
    rule_results = item.get("rule_results", [])
    
    # Rule-based 세부 피처
    rule_axis_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
    rule_severity_scores = {"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0, "CRITICAL": 0.0}
    rule_count = len(rule_results)
    
    for rule in rule_results:
        axis = rule.get("axis", "B")
        severity = rule.get("severity", "MEDIUM")
        score = rule.get("score", 0.0)
        
        if axis in rule_axis_scores:
            rule_axis_scores[axis] += score
        if severity in rule_severity_scores:
            rule_severity_scores[severity] += score
    
    # 2. MPOCryptoML 피처
    ml_features = item.get("ml_features", {})
    
    ml_numeric_features = [
        ml_features.get("ppr_score", 0.0),
        ml_features.get("sdn_ppr", 0.0),
        ml_features.get("mixer_ppr", 0.0),
        ml_features.get("pattern_score", 0.0),
        ml_features.get("n_theta", 0.0),
        ml_features.get("n_omega", 0.0),
        ml_features.get("fan_in_count", 0),
        ml_features.get("fan_out_count", 0),
        ml_features.get("gather_scatter", 0.0),
        ml_features.get("graph_nodes", 0),
        ml_features.get("graph_edges", 0),
    ]
    
    # 패턴 피처 (one-hot encoding)
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    pattern_features = [1.0 if pattern_type in detected_patterns else 0.0 
                        for pattern_type in pattern_types]
    
    # 3. 통합 피처 벡터
    features = [
        # Rule-based 기본
        rule_score,
        rule_count,
        # Rule-based Axis별 점수
        rule_axis_scores["A"],
        rule_axis_scores["B"],
        rule_axis_scores["C"],
        rule_axis_scores["D"],
        # Rule-based Severity별 점수
        rule_severity_scores["LOW"],
        rule_severity_scores["MEDIUM"],
        rule_severity_scores["HIGH"],
        rule_severity_scores["CRITICAL"],
        # MPOCryptoML 피처
        *ml_numeric_features,
        *pattern_features,
    ]
    
    return np.array(features, dtype=np.float32)


def load_dataset(file_path: Path) -> Tuple[List[np.ndarray], List[int]]:
    """
    데이터셋 로드 및 피처/라벨 추출
    
    Args:
        file_path: 데이터셋 JSON 파일 경로
    
    Returns:
        (features, labels) 튜플
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    features = []
    labels = []
    
    for item in data:
        # 피처 추출
        feature_vector = extract_hybrid_features(item)
        features.append(feature_vector)
        
        # 라벨 변환 (fraud=1, normal=0)
        label = item.get("ground_truth_label", "normal")
        labels.append(1 if label == "fraud" else 0)
    
    return features, labels


def train_hybrid_model(
    train_path: Path,
    val_path: Path,
    output_path: Path,
    model_type: str = "logistic"
) -> Dict[str, Any]:
    """
    Hybrid 모델 학습
    
    Args:
        train_path: 학습 데이터셋 경로
        val_path: 검증 데이터셋 경로
        output_path: 모델 저장 경로
        model_type: 모델 타입 ("logistic", "gradient_boosting", "random_forest")
    
    Returns:
        학습 결과 딕셔너리
    """
    print("=" * 60)
    print("Hybrid 모델 학습 (Rule-based + MPOCryptoML)")
    print("=" * 60)
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    X_train, y_train = load_dataset(train_path)
    X_val, y_val = load_dataset(val_path)
    
    X_train = np.array(X_train)
    X_val = np.array(X_val)
    y_train = np.array(y_train)
    y_val = np.array(y_val)
    
    print(f"   학습 데이터: {len(X_train)}개")
    print(f"   검증 데이터: {len(X_val)}개")
    print(f"   피처 차원: {X_train.shape[1]}개")
    
    # 피처 스케일링
    print("\n🔧 피처 스케일링 중...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 모델 선택 및 학습
    print(f"\n🎯 모델 학습 중 ({model_type})...")
    
    if model_type == "logistic":
        model = LogisticRegression(
            max_iter=1000,
            random_state=42,
            class_weight='balanced'
        )
    elif model_type == "gradient_boosting":
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42
        )
    elif model_type == "random_forest":
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            class_weight='balanced'
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    model.fit(X_train_scaled, y_train)
    
    # 검증 데이터 예측
    y_pred = model.predict(X_val_scaled)
    y_pred_proba = model.predict_proba(X_val_scaled)[:, 1]
    
    # 평가 지표 계산
    accuracy = accuracy_score(y_val, y_pred)
    precision = precision_score(y_val, y_pred, zero_division=0)
    recall = recall_score(y_val, y_pred, zero_division=0)
    f1 = f1_score(y_val, y_pred, zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
        avg_precision = average_precision_score(y_val, y_pred_proba)
    except:
        roc_auc = 0.5
        avg_precision = 0.0
    
    cm = confusion_matrix(y_val, y_pred)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("✅ 학습 완료!")
    print("=" * 60)
    print(f"\n📊 검증 성능:")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   ROC-AUC:   {roc_auc:.4f}")
    print(f"   Avg Precision: {avg_precision:.4f}")
    
    print(f"\n📈 Confusion Matrix:")
    print(f"   True Negative:  {cm[0][0]}")
    print(f"   False Positive: {cm[0][1]}")
    print(f"   False Negative: {cm[1][0]}")
    print(f"   True Positive:  {cm[1][1]}")
    
    # 모델 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        "model": model,
        "scaler": scaler,
        "model_type": model_type,
        "feature_names": [
            "rule_score", "rule_count",
            "rule_axis_A", "rule_axis_B", "rule_axis_C", "rule_axis_D",
            "rule_severity_LOW", "rule_severity_MEDIUM", "rule_severity_HIGH", "rule_severity_CRITICAL",
            "ppr_score", "sdn_ppr", "mixer_ppr", "pattern_score",
            "n_theta", "n_omega", "fan_in_count", "fan_out_count",
            "gather_scatter", "graph_nodes", "graph_edges",
            "pattern_fan_in", "pattern_fan_out", "pattern_gather_scatter",
            "pattern_stack", "pattern_bipartite"
        ]
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n💾 모델 저장 완료: {output_path}")
    
    # 학습 결과 반환
    results = {
        "model_type": model_type,
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "roc_auc": float(roc_auc),
        "average_precision": float(avg_precision),
        "confusion_matrix": {
            "true_negative": int(cm[0][0]),
            "false_positive": int(cm[0][1]),
            "false_negative": int(cm[1][0]),
            "true_positive": int(cm[1][1])
        }
    }
    
    return results


def compare_models(
    train_path: Path,
    val_path: Path,
    output_dir: Path
) -> Dict[str, Any]:
    """
    여러 모델 타입 비교 학습
    
    Args:
        train_path: 학습 데이터셋 경로
        val_path: 검증 데이터셋 경로
        output_dir: 모델 저장 디렉토리
    
    Returns:
        모든 모델의 학습 결과
    """
    model_types = ["logistic", "gradient_boosting", "random_forest"]
    all_results = {}
    
    for model_type in model_types:
        print(f"\n{'='*60}")
        print(f"모델 타입: {model_type}")
        print(f"{'='*60}")
        
        output_path = output_dir / f"hybrid_model_{model_type}.pkl"
        results = train_hybrid_model(train_path, val_path, output_path, model_type)
        all_results[model_type] = results
    
    # 최고 성능 모델 선택
    best_model = max(all_results.items(), key=lambda x: x[1]['f1_score'])
    print(f"\n{'='*60}")
    print(f"🏆 최고 성능 모델: {best_model[0]}")
    print(f"   F1-Score: {best_model[1]['f1_score']:.4f}")
    print(f"   Accuracy: {best_model[1]['accuracy']:.4f}")
    print(f"{'='*60}")
    
    return all_results


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hybrid 모델 학습")
    parser.add_argument(
        "--model-type",
        type=str,
        default="all",
        choices=["logistic", "gradient_boosting", "random_forest", "all"],
        help="학습할 모델 타입 (기본: all)"
    )
    args = parser.parse_args()
    
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    models_dir = project_root / "models"
    
    if not train_path.exists():
        print(f"❌ 학습 데이터를 찾을 수 없습니다: {train_path}")
        return
    
    if not val_path.exists():
        print(f"❌ 검증 데이터를 찾을 수 없습니다: {val_path}")
        return
    
    models_dir.mkdir(parents=True, exist_ok=True)
    
    if args.model_type == "all":
        # 모든 모델 비교 학습
        all_results = compare_models(train_path, val_path, models_dir)
        
        # 결과 저장
        results_path = dataset_dir / "hybrid_training_results.json"
        with open(results_path, 'w') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 학습 결과 저장: {results_path}")
    else:
        # 단일 모델 학습
        output_path = models_dir / f"hybrid_model_{args.model_type}.pkl"
        results = train_hybrid_model(train_path, val_path, output_path, args.model_type)
        
        # 결과 저장
        results_path = dataset_dir / f"hybrid_training_results_{args.model_type}.json"
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 학습 결과 저장: {results_path}")
    
    print("\n다음 단계:")
    print("1. 모델 평가: python scripts/evaluate_hybrid_model.py")
    print("2. Rule-based, MPOCryptoML, Hybrid 모델 비교")


if __name__ == "__main__":
    main()

