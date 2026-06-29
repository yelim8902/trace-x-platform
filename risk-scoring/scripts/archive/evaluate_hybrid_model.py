#!/usr/bin/env python3
"""
Hybrid 모델 평가 스크립트

테스트 데이터셋으로 Hybrid 모델 평가 및 Rule-based, MPOCryptoML과 비교

사용법:
    python scripts/evaluate_hybrid_model.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.ai_weight_learner import RuleWeightLearner


def extract_hybrid_features(item: Dict[str, Any]) -> np.ndarray:
    """Hybrid 모델용 피처 추출 (학습 스크립트와 동일)"""
    # 1. Rule-based 피처
    rule_score = item.get("rule_score", 0.0)
    rule_results = item.get("rule_results", [])
    
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
    
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    pattern_features = [1.0 if pattern_type in detected_patterns else 0.0 
                        for pattern_type in pattern_types]
    
    # 3. 통합 피처 벡터
    features = [
        rule_score, rule_count,
        rule_axis_scores["A"], rule_axis_scores["B"], rule_axis_scores["C"], rule_axis_scores["D"],
        rule_severity_scores["LOW"], rule_severity_scores["MEDIUM"], 
        rule_severity_scores["HIGH"], rule_severity_scores["CRITICAL"],
        *ml_numeric_features,
        *pattern_features,
    ]
    
    return np.array(features, dtype=np.float32)


def extract_mpocryptml_features(item: Dict[str, Any]) -> np.ndarray:
    """MPOCryptoML 모델용 피처 추출"""
    ml_features = item.get("ml_features", {})
    
    features = [
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
    
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    for pattern_type in pattern_types:
        features.append(1.0 if pattern_type in detected_patterns else 0.0)
    
    rule_score = item.get("rule_score", 0.0)
    features.append(rule_score)
    
    return np.array(features, dtype=np.float32)


def evaluate_model_with_predictions(
    y_true: List[int],
    y_pred: List[int],
    y_pred_proba: List[float],
    model_name: str
) -> Dict[str, Any]:
    """예측 결과로부터 평가 지표 계산"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    try:
        if len(set(y_pred_proba)) > 1:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
            avg_precision = average_precision_score(y_true, y_pred_proba)
        else:
            roc_auc = 0.5
            avg_precision = 0.0
    except:
        roc_auc = 0.5
        avg_precision = 0.0
    
    cm = confusion_matrix(y_true, y_pred)
    
    return {
        "model_name": model_name,
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


def evaluate_hybrid_model(test_data: List[Dict[str, Any]], model_path: Path) -> Dict[str, Any]:
    """Hybrid 모델 평가"""
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data["model"]
    scaler = model_data["scaler"]
    
    X_test = []
    for item in test_data:
        features = extract_hybrid_features(item)
        X_test.append(features)
    
    X_test = np.array(X_test)
    X_test_scaled = scaler.transform(X_test)
    
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    y_true = []
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
    
    return evaluate_model_with_predictions(y_true, y_pred, y_pred_proba, "Hybrid (Logistic Regression)")


def evaluate_mpocryptml_model(test_data: List[Dict[str, Any]], model_path: Path) -> Dict[str, Any]:
    """MPOCryptoML 모델 평가"""
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data["model"]
    scaler = model_data["scaler"]
    
    X_test = []
    for item in test_data:
        features = extract_mpocryptml_features(item)
        X_test.append(features)
    
    X_test = np.array(X_test)
    X_test_scaled = scaler.transform(X_test)
    
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    y_true = []
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
    
    return evaluate_model_with_predictions(y_true, y_pred, y_pred_proba, "MPOCryptoML (Logistic Regression)")


def evaluate_rule_based(test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Rule-based 모델 평가"""
    y_true = []
    y_pred_scores = []
    
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        
        # Rule-based 점수
        rule_score = item.get("rule_score", 0.0)
        y_pred_scores.append(rule_score / 100.0)
    
    # Threshold 50.0으로 분류
    y_pred = [1 if score >= 0.5 else 0 for score in y_pred_scores]
    
    return evaluate_model_with_predictions(y_true, y_pred, y_pred_scores, "Rule-based")


def main():
    """메인 함수"""
    print("=" * 60)
    print("Hybrid 모델 평가 및 비교")
    print("=" * 60)
    
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    hybrid_model_path = project_root / "models" / "hybrid_model_logistic.pkl"
    mpocryptml_model_path = project_root / "models" / "mpocryptml_model.pkl"
    
    if not test_path.exists():
        print(f"❌ 테스트 데이터를 찾을 수 없습니다: {test_path}")
        return
    
    # 테스트 데이터 로드
    print("\n📂 테스트 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   총 {len(test_data)}개 샘플")
    
    from collections import Counter
    labels = [item.get("ground_truth_label", "normal") for item in test_data]
    label_counts = Counter(labels)
    print(f"   라벨 분포: {dict(label_counts)}")
    
    # 모델 평가
    print("\n" + "=" * 60)
    print("📊 모델 평가 중...")
    print("=" * 60)
    
    all_results = []
    
    # 1. Rule-based
    print("\n1️⃣  Rule-based 모델 평가 중...")
    rule_results = evaluate_rule_based(test_data)
    all_results.append(rule_results)
    
    # 2. MPOCryptoML
    if mpocryptml_model_path.exists():
        print("\n2️⃣  MPOCryptoML 모델 평가 중...")
        mpocryptml_results = evaluate_mpocryptml_model(test_data, mpocryptml_model_path)
        all_results.append(mpocryptml_results)
    else:
        print("\n⚠️  MPOCryptoML 모델을 찾을 수 없습니다. 건너뜁니다.")
    
    # 3. Hybrid
    if hybrid_model_path.exists():
        print("\n3️⃣  Hybrid 모델 평가 중...")
        hybrid_results = evaluate_hybrid_model(test_data, hybrid_model_path)
        all_results.append(hybrid_results)
    else:
        print("\n⚠️  Hybrid 모델을 찾을 수 없습니다. 건너뜁니다.")
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📈 평가 결과 비교")
    print("=" * 60)
    
    print(f"\n{'모델':<35} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
    print("-" * 85)
    
    for results in all_results:
        name = results["model_name"]
        acc = results["accuracy"]
        prec = results["precision"]
        rec = results["recall"]
        f1 = results["f1_score"]
        auc = results["roc_auc"]
        
        print(f"{name:<35} {acc:<10.4f} {prec:<10.4f} {rec:<10.4f} {f1:<10.4f} {auc:<10.4f}")
    
    # 상세 결과
    print("\n" + "=" * 60)
    print("📋 상세 결과")
    print("=" * 60)
    
    for results in all_results:
        print(f"\n🔹 {results['model_name']}:")
        print(f"   Accuracy:        {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
        print(f"   Precision:       {results['precision']:.4f}")
        print(f"   Recall:          {results['recall']:.4f}")
        print(f"   F1-Score:        {results['f1_score']:.4f}")
        print(f"   ROC-AUC:         {results['roc_auc']:.4f}")
        print(f"   Average Precision: {results['average_precision']:.4f}")
        cm = results['confusion_matrix']
        print(f"   Confusion Matrix:")
        print(f"      TN: {cm['true_negative']}, FP: {cm['false_positive']}")
        print(f"      FN: {cm['false_negative']}, TP: {cm['true_positive']}")
    
    # 결과 저장
    output_path = dataset_dir / "hybrid_evaluation_results.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 평가 결과 저장: {output_path}")
    
    # 최고 성능 모델
    if all_results:
        best_model = max(all_results, key=lambda x: x['f1_score'])
        print(f"\n🏆 최고 성능 모델 (F1-Score 기준): {best_model['model_name']}")
        print(f"   F1-Score: {best_model['f1_score']:.4f}")
        print(f"   Accuracy: {best_model['accuracy']:.4f}")


if __name__ == "__main__":
    main()

