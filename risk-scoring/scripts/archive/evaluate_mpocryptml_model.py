#!/usr/bin/env python3
"""
MPOCryptoML 모델 평가 스크립트

테스트 데이터셋으로 MPOCryptoML 모델과 Baseline 모델들을 평가 및 비교

사용법:
    python scripts/evaluate_mpocryptml_model.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.ai_weight_learner import RuleWeightLearner


def extract_features(item: Dict[str, Any]) -> np.ndarray:
    """
    MPOCryptoML 피처 추출 (학습 스크립트와 동일)
    
    Args:
        item: 데이터셋 항목
    
    Returns:
        피처 벡터 (numpy array)
    """
    ml_features = item.get("ml_features", {})
    
    # 숫자형 피처 추출
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
    
    # 패턴 피처 (one-hot encoding)
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    for pattern_type in pattern_types:
        features.append(1.0 if pattern_type in detected_patterns else 0.0)
    
    # Rule-based 점수도 피처로 포함
    rule_score = item.get("rule_score", 0.0)
    features.append(rule_score)
    
    return np.array(features, dtype=np.float32)


class BaselineModels:
    """Baseline 모델들"""
    
    @staticmethod
    def simple_sum(item: Dict[str, Any]) -> float:
        """Baseline 1: Rule-based 단순 합산"""
        rule_results = item.get("rule_results", [])
        return min(100.0, sum(r.get("score", 0) for r in rule_results))
    
    @staticmethod
    def rule_based_weights(item: Dict[str, Any]) -> float:
        """Baseline 2: 규칙 기반 가중치"""
        rule_results = item.get("rule_results", [])
        learner = RuleWeightLearner(use_ai=False)
        return learner.calculate_weighted_score(rule_results)
    
    @staticmethod
    def rule_score_only(item: Dict[str, Any]) -> float:
        """Baseline 3: Rule Score만 사용"""
        return item.get("rule_score", 0.0)
    
    @staticmethod
    def ml_features_only(item: Dict[str, Any]) -> float:
        """Baseline 4: MPOCryptoML 피처만 사용 (가중 평균)"""
        ml_features = item.get("ml_features", {})
        ppr = ml_features.get("ppr_score", 0.0) * 100
        pattern = ml_features.get("pattern_score", 0.0)
        n_theta = ml_features.get("n_theta", 0.0) * 100
        n_omega = ml_features.get("n_omega", 0.0) * 100
        
        # 간단한 가중 평균
        score = (ppr * 0.3 + pattern * 0.4 + n_theta * 0.15 + n_omega * 0.15)
        return min(100.0, max(0.0, score))
    
    @staticmethod
    def majority_class(y_true: List[str]) -> str:
        """Baseline 5: 다수 클래스 분류기"""
        from collections import Counter
        return Counter(y_true).most_common(1)[0][0]
    
    @staticmethod
    def random_classifier(y_true: List[str], random_state: int = 42) -> List[str]:
        """Baseline 6: 랜덤 분류기"""
        np.random.seed(random_state)
        unique_labels = list(set(y_true))
        return [np.random.choice(unique_labels) for _ in y_true]


def score_to_label(score: float, threshold: float = 50.0) -> str:
    """점수를 라벨로 변환"""
    if score >= threshold:
        return "fraud"
    else:
        return "normal"


def evaluate_model(
    test_data: List[Dict[str, Any]],
    model_name: str,
    predict_fn
) -> Dict[str, Any]:
    """
    모델 평가
    
    Args:
        test_data: 테스트 데이터
        model_name: 모델 이름
        predict_fn: 예측 함수 (item -> score 또는 item -> label)
    
    Returns:
        평가 메트릭 딕셔너리
    """
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    for item in test_data:
        actual_label = item.get("ground_truth_label", "normal")
        
        # 예측
        try:
            prediction = predict_fn(item)
            
            # 점수인지 라벨인지 확인
            if isinstance(prediction, (int, float)):
                predicted_score = float(prediction)
                predicted_label = score_to_label(predicted_score)
            else:
                predicted_label = str(prediction)
                # 라벨만 있는 경우 점수 추정
                predicted_score = 85.0 if predicted_label == "fraud" else 15.0
        except Exception as e:
            print(f"⚠️  예측 에러 ({model_name}): {e}")
            predicted_score = 0.0
            predicted_label = "normal"
        
        y_true.append(actual_label)
        y_pred.append(predicted_label)
        y_pred_scores.append(predicted_score)
    
    # 이진 분류로 변환
    y_true_binary = [1 if label == "fraud" else 0 for label in y_true]
    y_pred_binary = [1 if label == "fraud" else 0 for label in y_pred]
    y_pred_proba = [score / 100.0 for score in y_pred_scores]
    
    # 평가 지표 계산
    accuracy = accuracy_score(y_true_binary, y_pred_binary)
    precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    
    # ROC-AUC 및 Average Precision
    try:
        if len(set(y_pred_proba)) > 1:
            roc_auc = roc_auc_score(y_true_binary, y_pred_proba)
            avg_precision = average_precision_score(y_true_binary, y_pred_proba)
        else:
            roc_auc = 0.5
            avg_precision = 0.0
    except Exception as e:
        roc_auc = 0.5
        avg_precision = 0.0
    
    # Confusion Matrix
    cm = confusion_matrix(y_true_binary, y_pred_binary)
    
    metrics = {
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
    
    return metrics


def evaluate_mpocryptml_model(
    test_data: List[Dict[str, Any]],
    model_path: Path
) -> Dict[str, Any]:
    """
    MPOCryptoML 모델 평가
    
    Args:
        test_data: 테스트 데이터
        model_path: 모델 파일 경로
    
    Returns:
        평가 메트릭 딕셔너리
    """
    # 모델 로드
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data["model"]
    scaler = model_data["scaler"]
    
    # 피처 추출 및 스케일링
    X_test = []
    for item in test_data:
        features = extract_features(item)
        X_test.append(features)
    
    X_test = np.array(X_test)
    X_test_scaled = scaler.transform(X_test)
    
    # 예측
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    # 라벨 변환
    y_true = []
    y_pred_labels = []
    y_pred_scores = []
    
    for i, item in enumerate(test_data):
        actual_label = item.get("ground_truth_label", "normal")
        predicted_binary = y_pred[i]
        predicted_label = "fraud" if predicted_binary == 1 else "normal"
        predicted_score = y_pred_proba[i] * 100.0
        
        y_true.append(actual_label)
        y_pred_labels.append(predicted_label)
        y_pred_scores.append(predicted_score)
    
    # 이진 분류로 변환
    y_true_binary = [1 if label == "fraud" else 0 for label in y_true]
    y_pred_binary = [1 if label == "fraud" else 0 for label in y_pred_labels]
    
    # 평가 지표 계산
    accuracy = accuracy_score(y_true_binary, y_pred_binary)
    precision = precision_score(y_true_binary, y_pred_binary, zero_division=0)
    recall = recall_score(y_true_binary, y_pred_binary, zero_division=0)
    f1 = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    
    try:
        if len(set(y_pred_proba)) > 1:
            roc_auc = roc_auc_score(y_true_binary, y_pred_proba)
            avg_precision = average_precision_score(y_true_binary, y_pred_proba)
        else:
            roc_auc = 0.5
            avg_precision = 0.0
    except Exception as e:
        roc_auc = 0.5
        avg_precision = 0.0
    
    cm = confusion_matrix(y_true_binary, y_pred_binary)
    
    metrics = {
        "model_name": "MPOCryptoML (Logistic Regression)",
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
    
    return metrics


def main():
    """메인 함수"""
    print("=" * 60)
    print("MPOCryptoML 모델 평가")
    print("=" * 60)
    
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    model_path = project_root / "models" / "mpocryptml_model.pkl"
    
    if not test_path.exists():
        print(f"❌ 테스트 데이터를 찾을 수 없습니다: {test_path}")
        return
    
    if not model_path.exists():
        print(f"❌ 모델 파일을 찾을 수 없습니다: {model_path}")
        print("   먼저 모델을 학습하세요: python scripts/train_mpocryptml_model.py")
        return
    
    # 테스트 데이터 로드
    print("\n📂 테스트 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   총 {len(test_data)}개 샘플")
    
    # 라벨 분포 확인
    labels = [item.get("ground_truth_label", "normal") for item in test_data]
    from collections import Counter
    label_counts = Counter(labels)
    print(f"   라벨 분포: {dict(label_counts)}")
    
    # 모델 평가
    print("\n" + "=" * 60)
    print("📊 모델 평가 중...")
    print("=" * 60)
    
    all_results = []
    
    # 1. MPOCryptoML 모델
    print("\n1️⃣  MPOCryptoML 모델 평가 중...")
    mpocryptml_results = evaluate_mpocryptml_model(test_data, model_path)
    all_results.append(mpocryptml_results)
    
    # 2. Baseline 모델들
    print("\n2️⃣  Baseline 모델들 평가 중...")
    
    baseline_models = {
        "Simple Sum": lambda item: BaselineModels.simple_sum(item),
        "Rule-based Weights": lambda item: BaselineModels.rule_based_weights(item),
        "Rule Score Only": lambda item: BaselineModels.rule_score_only(item),
        "ML Features Only": lambda item: BaselineModels.ml_features_only(item),
    }
    
    for name, predict_fn in baseline_models.items():
        print(f"   - {name}...")
        results = evaluate_model(test_data, name, predict_fn)
        all_results.append(results)
    
    # 3. Majority Class
    print("   - Majority Class...")
    majority_label = BaselineModels.majority_class(labels)
    majority_results = evaluate_model(
        test_data,
        "Majority Class",
        lambda item: majority_label
    )
    all_results.append(majority_results)
    
    # 4. Random Classifier
    print("   - Random Classifier...")
    random_labels = BaselineModels.random_classifier(labels)
    random_results = evaluate_model(
        test_data,
        "Random Classifier",
        lambda item, idx=iter(range(len(test_data))): random_labels[next(idx)]
    )
    all_results.append(random_results)
    
    # 결과 출력
    print("\n" + "=" * 60)
    print("📈 평가 결과")
    print("=" * 60)
    
    # 테이블 형식으로 출력
    print(f"\n{'모델':<30} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
    print("-" * 80)
    
    for results in all_results:
        name = results["model_name"]
        acc = results["accuracy"]
        prec = results["precision"]
        rec = results["recall"]
        f1 = results["f1_score"]
        auc = results["roc_auc"]
        
        print(f"{name:<30} {acc:<10.4f} {prec:<10.4f} {rec:<10.4f} {f1:<10.4f} {auc:<10.4f}")
    
    # 상세 결과 출력
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
    output_path = dataset_dir / "mpocryptml_evaluation_results.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 평가 결과 저장: {output_path}")
    
    # 최고 성능 모델
    best_model = max(all_results, key=lambda x: x['f1_score'])
    print(f"\n🏆 최고 성능 모델 (F1-Score 기준): {best_model['model_name']}")
    print(f"   F1-Score: {best_model['f1_score']:.4f}")
    print(f"   Accuracy: {best_model['accuracy']:.4f}")


if __name__ == "__main__":
    main()

