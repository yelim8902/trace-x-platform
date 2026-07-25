#!/usr/bin/env python3
"""
MPOCryptoML 모델 학습 스크립트

논문의 방법론에 따라 MPOCryptoML 피처를 사용하여 Logistic Regression 모델 학습

사용법:
    python scripts/train_mpocryptml_model.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def extract_features(item: Dict[str, Any]) -> np.ndarray:
    """
    MPOCryptoML 피처 추출
    
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
    
    # Rule-based 점수도 피처로 포함 (선택적)
    rule_score = item.get("rule_score", 0.0)
    features.append(rule_score)
    
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
        feature_vector = extract_features(item)
        features.append(feature_vector)
        
        # 라벨 변환 (fraud=1, normal=0)
        label = item.get("ground_truth_label", "normal")
        labels.append(1 if label == "fraud" else 0)
    
    return features, labels


def train_mpocryptml_model(
    train_path: Path,
    val_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    MPOCryptoML 모델 학습
    
    Args:
        train_path: 학습 데이터셋 경로
        val_path: 검증 데이터셋 경로
        output_path: 모델 저장 경로
    
    Returns:
        학습 결과 딕셔너리
    """
    print("=" * 60)
    print("MPOCryptoML 모델 학습")
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
    
    # 모델 학습
    print("\n🎯 모델 학습 중...")
    model = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced'  # 불균형 데이터 처리
    )
    
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
        "feature_names": [
            "ppr_score", "sdn_ppr", "mixer_ppr", "pattern_score",
            "n_theta", "n_omega", "fan_in_count", "fan_out_count",
            "gather_scatter", "graph_nodes", "graph_edges",
            "pattern_fan_in", "pattern_fan_out", "pattern_gather_scatter",
            "pattern_stack", "pattern_bipartite", "rule_score"
        ]
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n💾 모델 저장 완료: {output_path}")
    
    # 학습 결과 반환
    results = {
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


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    model_path = project_root / "models" / "mpocryptml_model.pkl"
    
    if not train_path.exists():
        print(f"❌ 학습 데이터를 찾을 수 없습니다: {train_path}")
        return
    
    if not val_path.exists():
        print(f"❌ 검증 데이터를 찾을 수 없습니다: {val_path}")
        return
    
    # 모델 학습
    results = train_mpocryptml_model(train_path, val_path, model_path)
    
    # 결과 저장
    results_path = dataset_dir / "mpocryptml_training_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📄 학습 결과 저장: {results_path}")
    print("\n다음 단계:")
    print("1. 모델 평가: python scripts/evaluate_mpocryptml_model.py")
    print("2. Hybrid 모델 학습 (Rule-based + MPOCryptoML)")


if __name__ == "__main__":
    main()

