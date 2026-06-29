#!/usr/bin/env python3
"""
고급 피처 엔지니어링 스크립트

상호작용 피처, 다항식 피처, 통계 피처 등을 추가하여 성능 개선

사용법:
    python scripts/advanced_feature_engineering.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score
)
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.train_mpocryptml_model import extract_features, load_dataset
from scripts.train_hybrid_model import extract_hybrid_features


def extract_enhanced_features(item: Dict[str, Any]) -> np.ndarray:
    """
    고급 피처 엔지니어링
    
    기존 피처 + 상호작용 피처 + 통계 피처
    """
    # 기본 피처 추출
    base_features = extract_features(item)
    
    # 추가 통계 피처
    ml_features = item.get("ml_features", {})
    rule_results = item.get("rule_results", [])
    rule_score = item.get("rule_score", 0.0)
    
    # 1. PPR 관련 상호작용 피처
    ppr_score = ml_features.get("ppr_score", 0.0)
    sdn_ppr = ml_features.get("sdn_ppr", 0.0)
    mixer_ppr = ml_features.get("mixer_ppr", 0.0)
    
    # 2. 패턴 관련 상호작용 피처
    pattern_score = ml_features.get("pattern_score", 0.0)
    fan_in_count = ml_features.get("fan_in_count", 0)
    fan_out_count = ml_features.get("fan_out_count", 0)
    gather_scatter = ml_features.get("gather_scatter", 0.0)
    
    # 3. 정규화 점수 상호작용
    n_theta = ml_features.get("n_theta", 0.0)
    n_omega = ml_features.get("n_omega", 0.0)
    
    # 4. 그래프 구조 피처
    graph_nodes = ml_features.get("graph_nodes", 0)
    graph_edges = ml_features.get("graph_edges", 0)
    graph_density = graph_edges / (graph_nodes * (graph_nodes - 1)) if graph_nodes > 1 else 0.0
    
    # 5. Rule-based 상호작용
    rule_count = len(rule_results)
    rule_axis_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
    rule_severity_scores = {"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0, "CRITICAL": 0.0}
    
    for rule in rule_results:
        axis = rule.get("axis", "B")
        severity = rule.get("severity", "MEDIUM")
        score = rule.get("score", 0.0)
        
        if axis in rule_axis_scores:
            rule_axis_scores[axis] += score
        if severity in rule_severity_scores:
            rule_severity_scores[severity] += score
    
    # 상호작용 피처 생성
    interaction_features = [
        # PPR 상호작용
        ppr_score * sdn_ppr,
        ppr_score * mixer_ppr,
        sdn_ppr * mixer_ppr,
        ppr_score * pattern_score,
        
        # 패턴 상호작용
        fan_in_count * fan_out_count,
        pattern_score * n_theta,
        pattern_score * n_omega,
        gather_scatter * n_theta,
        
        # Rule-based 상호작용
        rule_score * ppr_score,
        rule_score * pattern_score,
        rule_count * pattern_score,
        
        # 정규화 점수 상호작용
        n_theta * n_omega,
        
        # 그래프 구조 상호작용
        graph_density * pattern_score,
        (graph_edges / graph_nodes) if graph_nodes > 0 else 0.0,  # 평균 연결도
        
        # 통계 피처
        np.sqrt(ppr_score) if ppr_score >= 0 else 0.0,
        np.log1p(pattern_score),
        np.log1p(rule_score),
        
        # 비율 피처
        (sdn_ppr / (ppr_score + 1e-6)) if ppr_score > 0 else 0.0,  # SDN 비율
        (mixer_ppr / (ppr_score + 1e-6)) if ppr_score > 0 else 0.0,  # Mixer 비율
        (fan_in_count / (fan_in_count + fan_out_count + 1)) if (fan_in_count + fan_out_count) > 0 else 0.0,  # Fan-in 비율
    ]
    
    # 모든 피처 결합
    enhanced_features = np.concatenate([
        base_features,
        np.array(interaction_features, dtype=np.float32)
    ])
    
    return enhanced_features


def train_with_enhanced_features(
    train_path: Path,
    val_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """고급 피처로 모델 학습"""
    print("=" * 80)
    print("고급 피처 엔지니어링 모델 학습")
    print("=" * 80)
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    with open(train_path, 'r') as f:
        train_data = json.load(f)
    with open(val_path, 'r') as f:
        val_data = json.load(f)
    
    X_train = []
    y_train = []
    X_val = []
    y_val = []
    
    print("   피처 추출 중...")
    for item in train_data:
        features = extract_enhanced_features(item)
        X_train.append(features)
        label = item.get("ground_truth_label", "normal")
        y_train.append(1 if label == "fraud" else 0)
    
    for item in val_data:
        features = extract_enhanced_features(item)
        X_val.append(features)
        label = item.get("ground_truth_label", "normal")
        y_val.append(1 if label == "fraud" else 0)
    
    X_train = np.array(X_train)
    X_val = np.array(X_val)
    y_train = np.array(y_train)
    y_val = np.array(y_val)
    
    print(f"   학습 데이터: {len(X_train)}개")
    print(f"   검증 데이터: {len(X_val)}개")
    print(f"   기본 피처 차원: 17개")
    print(f"   향상된 피처 차원: {X_train.shape[1]}개")
    print(f"   추가된 피처: {X_train.shape[1] - 17}개")
    
    # 피처 스케일링
    print("\n🔧 피처 스케일링 중...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    results = {}
    
    # 여러 모델 시도
    models_to_try = [
        ("Logistic Regression", LogisticRegression(
            max_iter=2000, random_state=42, class_weight='balanced', C=1.0
        )),
        ("Gradient Boosting", GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42
        )),
        ("Random Forest", RandomForestClassifier(
            n_estimators=200, max_depth=7, class_weight='balanced', random_state=42
        )),
    ]
    
    if XGBOOST_AVAILABLE:
        models_to_try.append(("XGBoost", XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            random_state=42, eval_metric='logloss'
        )))
    
    best_f1 = 0.0
    best_model = None
    best_name = None
    
    for model_name, model in models_to_try:
        print(f"\n🎯 {model_name} 학습 중...")
        model.fit(X_train_scaled, y_train)
        
        y_pred = model.predict(X_val_scaled)
        y_pred_proba = model.predict_proba(X_val_scaled)[:, 1]
        
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
        
        results[model_name] = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1,
            'roc_auc': roc_auc,
            'average_precision': avg_precision
        }
        
        print(f"   F1-Score: {f1:.4f} | Accuracy: {accuracy:.4f} | Precision: {precision:.4f} | Recall: {recall:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_name = model_name
    
    # 최고 모델 저장
    if best_model:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model': best_model,
            'scaler': scaler,
            'model_type': best_name,
            'feature_dim': X_train.shape[1]
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\n💾 최고 모델 저장: {output_path}")
        print(f"   모델: {best_name}")
        print(f"   F1-Score: {best_f1:.4f} ({best_f1*100:.2f}%)")
    
    return results


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    models_dir = project_root / "models"
    output_path = models_dir / "enhanced_feature_model.pkl"
    
    if not train_path.exists() or not val_path.exists():
        print("❌ 학습/검증 데이터를 찾을 수 없습니다.")
        return
    
    results = train_with_enhanced_features(train_path, val_path, output_path)
    
    # 결과 저장
    results_path = dataset_dir / "enhanced_feature_results.json"
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 결과 저장: {results_path}")


if __name__ == "__main__":
    main()

