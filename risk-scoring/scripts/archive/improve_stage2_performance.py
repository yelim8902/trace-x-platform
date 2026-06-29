#!/usr/bin/env python3
"""
Stage 2 성능 개선 스크립트

1. 하이퍼파라미터 튜닝
2. Feature Engineering 개선
3. 앙상블 모델
4. Threshold 최적화
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import (
    GradientBoostingClassifier, RandomForestClassifier,
    VotingClassifier, StackingClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, make_scorer
)
from scipy.stats import randint, uniform

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from core.scoring.stage2_scorer import Stage2Scorer


def extract_enhanced_features(
    stage1_result: Dict[str, Any],
    ml_features: Dict[str, Any],
    tx_context: Dict[str, Any]
) -> np.ndarray:
    """
    개선된 Feature 추출
    
    기존 30차원 + 추가 feature
    """
    features = []
    
    # 1. Stage 1 features (기존)
    features.append(stage1_result["rule_score"])
    features.append(stage1_result["graph_score"])
    features.append(stage1_result["risk_score"])
    
    # 2. Rule-based features (기존)
    rule_results = stage1_result.get("rule_results", [])
    features.append(len(rule_results))
    
    axes = [r.get("axis", "B") for r in rule_results]
    features.append(axes.count("A"))
    features.append(axes.count("B"))
    features.append(axes.count("C"))
    features.append(axes.count("D"))
    features.append(axes.count("E"))
    
    severities = [r.get("severity", "MEDIUM") for r in rule_results]
    features.append(severities.count("CRITICAL"))
    features.append(severities.count("HIGH"))
    features.append(severities.count("MEDIUM"))
    features.append(severities.count("LOW"))
    
    # 3. Graph statistics features (기존)
    features.append(min(100, ml_features.get("fan_in_count", 0)))
    features.append(min(100, ml_features.get("fan_out_count", 0)))
    features.append(min(100, ml_features.get("tx_primary_fan_in_count", 0)))
    features.append(min(100, ml_features.get("tx_primary_fan_out_count", 0)))
    features.append(min(100.0, ml_features.get("pattern_score", 0.0)))
    
    avg_value = ml_features.get("avg_transaction_value", 0.0)
    max_value = ml_features.get("max_transaction_value", 0.0)
    if avg_value > 0:
        features.append(min(20.0, np.log1p(avg_value)))
    else:
        features.append(0.0)
    if max_value > 0:
        features.append(min(20.0, np.log1p(max_value)))
    else:
        features.append(0.0)
    
    features.append(min(200, ml_features.get("graph_nodes", tx_context.get("graph_nodes", 0))))
    features.append(min(200, ml_features.get("num_transactions", tx_context.get("num_transactions", 0))))
    
    # 4. PPR features (기존)
    features.append(min(1.0, ml_features.get("ppr_score", 0.0)))
    features.append(min(1.0, ml_features.get("sdn_ppr", 0.0)))
    features.append(min(1.0, ml_features.get("mixer_ppr", 0.0)))
    
    # 5. 정규화 점수 (기존)
    features.append(min(1.0, max(0.0, ml_features.get("n_theta", 0.0))))
    features.append(min(1.0, max(0.0, ml_features.get("n_omega", 0.0))))
    
    # 6. 패턴 탐지 여부 (기존)
    features.append(ml_features.get("fan_in_detected", 0))
    features.append(ml_features.get("fan_out_detected", 0))
    features.append(ml_features.get("gather_scatter_detected", 0))
    
    # ===== 새로운 Feature 추가 =====
    
    # 7. 상호작용 Feature
    rule_score = stage1_result["rule_score"]
    graph_score = stage1_result["graph_score"]
    features.append(rule_score * graph_score / 100.0)  # 정규화된 곱
    features.append(rule_score / (graph_score + 1.0))  # 비율
    features.append((rule_score + graph_score) / 2.0)  # 평균
    
    # 8. Fan-in/out 비율
    fan_in_count = ml_features.get("fan_in_count", 0)
    fan_out_count = ml_features.get("fan_out_count", 0)
    total_fan = fan_in_count + fan_out_count
    if total_fan > 0:
        features.append(fan_in_count / total_fan)  # Fan-in 비율
        features.append(fan_out_count / total_fan)  # Fan-out 비율
    else:
        features.extend([0.0, 0.0])
    
    # 9. 거래 금액 통계
    min_value = ml_features.get("min_transaction_value", 0.0)
    total_value = ml_features.get("total_transaction_value", 0.0)
    transaction_count = ml_features.get("transaction_count", 0)
    
    if transaction_count > 0:
        features.append(total_value / transaction_count)  # 평균 (중복이지만 다른 계산)
        if max_value > 0 and min_value > 0:
            features.append(max_value / min_value)  # 최대/최소 비율
        else:
            features.append(0.0)
    else:
        features.extend([0.0, 0.0])
    
    # 10. 그래프 밀도
    graph_nodes = ml_features.get("graph_nodes", tx_context.get("graph_nodes", 0))
    graph_edges = ml_features.get("graph_edges", tx_context.get("graph_edges", 0))
    if graph_nodes > 1:
        max_edges = graph_nodes * (graph_nodes - 1)
        if max_edges > 0:
            features.append(graph_edges / max_edges)  # 그래프 밀도
        else:
            features.append(0.0)
    else:
        features.append(0.0)
    
    # 11. Rule 다양성
    unique_rules = len(set(r.get("rule_id", "") for r in rule_results))
    if len(rule_results) > 0:
        features.append(unique_rules / len(rule_results))  # Rule 다양성 비율
    else:
        features.append(0.0)
    
    # 12. 심각도 가중 평균
    severity_scores = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    if len(severities) > 0:
        avg_severity = np.mean([severity_scores.get(s, 2) for s in severities])
        features.append(avg_severity / 4.0)  # 정규화
    else:
        features.append(0.0)
    
    # NaN, Inf 체크
    features_array = np.array(features, dtype=np.float32)
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=100.0, neginf=0.0)
    
    return features_array


def load_dataset(file_path: Path) -> Tuple[List[np.ndarray], List[int]]:
    """데이터셋 로드 및 feature 추출"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    
    features = []
    labels = []
    
    for item in data:
        label = item.get("ground_truth_label", "normal")
        labels.append(1 if label == "fraud" else 0)
        
        tx_data = {
            "from": item.get("from", ""),
            "to": item.get("to", ""),
            "usd_value": item.get("usd_value", 0),
            "timestamp": item.get("timestamp", 0),
            "tx_hash": item.get("tx_hash", ""),
            "chain": item.get("chain", "ethereum"),
            "is_sanctioned": item.get("tx_context", {}).get("is_sanctioned", False),
            "is_mixer": item.get("tx_context", {}).get("is_mixer", False),
        }
        
        ml_features = item.get("ml_features", {})
        tx_context = item.get("tx_context", {})
        
        try:
            stage1_result = stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            feature_vector = extract_enhanced_features(stage1_result, ml_features, tx_context)
            features.append(feature_vector)
        except Exception as e:
            print(f"Error processing item: {e}")
            features.append(np.zeros(45, dtype=np.float32))  # 새 feature 차원: 45
    
    return features, labels


def optimize_hyperparameters(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray
) -> Dict[str, Any]:
    """하이퍼파라미터 최적화"""
    print("=" * 80)
    print("하이퍼파라미터 최적화")
    print("=" * 80)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Gradient Boosting 파라미터 그리드
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.01, 0.1, 0.2],
        'subsample': [0.8, 0.9, 1.0],
        'min_samples_split': [2, 5, 10]
    }
    
    # F1-Score를 최대화하는 모델 선택
    f1_scorer = make_scorer(f1_score)
    
    print("\n🔍 GridSearchCV 실행 중...")
    gb = GradientBoostingClassifier(random_state=42)
    grid_search = GridSearchCV(
        gb,
        param_grid,
        cv=3,
        scoring=f1_scorer,
        n_jobs=-1,
        verbose=1
    )
    grid_search.fit(X_train_scaled, y_train)
    
    best_model = grid_search.best_estimator_
    best_params = grid_search.best_params_
    best_score = grid_search.best_score_
    
    print(f"\n✅ 최적 파라미터:")
    for param, value in best_params.items():
        print(f"   {param}: {value}")
    print(f"   CV F1-Score: {best_score:.4f}")
    
    # 검증 데이터로 평가
    y_pred = best_model.predict(X_val_scaled)
    y_pred_proba = best_model.predict_proba(X_val_scaled)[:, 1]
    
    val_accuracy = accuracy_score(y_val, y_pred)
    val_precision = precision_score(y_val, y_pred, zero_division=0)
    val_recall = recall_score(y_val, y_pred, zero_division=0)
    val_f1 = f1_score(y_val, y_pred, zero_division=0)
    val_roc_auc = roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    
    print(f"\n📊 검증 성능:")
    print(f"   Accuracy: {val_accuracy:.4f}")
    print(f"   Precision: {val_precision:.4f}")
    print(f"   Recall: {val_recall:.4f}")
    print(f"   F1-Score: {val_f1:.4f}")
    print(f"   ROC-AUC: {val_roc_auc:.4f}")
    
    return {
        "model": best_model,
        "scaler": scaler,
        "params": best_params,
        "cv_score": best_score,
        "val_metrics": {
            "accuracy": val_accuracy,
            "precision": val_precision,
            "recall": val_recall,
            "f1_score": val_f1,
            "roc_auc": val_roc_auc
        }
    }


def create_ensemble_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray
) -> Dict[str, Any]:
    """앙상블 모델 생성"""
    print("=" * 80)
    print("앙상블 모델 생성")
    print("=" * 80)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 개별 모델들
    gb = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    
    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        random_state=42,
        class_weight='balanced'
    )
    
    lr = LogisticRegression(
        random_state=42,
        solver='liblinear',
        class_weight='balanced',
        max_iter=1000
    )
    
    # Voting Classifier (Soft)
    voting_clf = VotingClassifier(
        estimators=[
            ('gb', gb),
            ('rf', rf),
            ('lr', lr)
        ],
        voting='soft',
        weights=[2, 1, 1]  # GB에 더 가중치
    )
    
    print("\n🤖 앙상블 모델 학습 중...")
    voting_clf.fit(X_train_scaled, y_train)
    
    # 검증 데이터로 평가
    y_pred = voting_clf.predict(X_val_scaled)
    y_pred_proba = voting_clf.predict_proba(X_val_scaled)[:, 1]
    
    val_accuracy = accuracy_score(y_val, y_pred)
    val_precision = precision_score(y_val, y_pred, zero_division=0)
    val_recall = recall_score(y_val, y_pred, zero_division=0)
    val_f1 = f1_score(y_val, y_pred, zero_division=0)
    val_roc_auc = roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    
    print(f"\n📊 앙상블 모델 성능:")
    print(f"   Accuracy: {val_accuracy:.4f}")
    print(f"   Precision: {val_precision:.4f}")
    print(f"   Recall: {val_recall:.4f}")
    print(f"   F1-Score: {val_f1:.4f}")
    print(f"   ROC-AUC: {val_roc_auc:.4f}")
    
    return {
        "model": voting_clf,
        "scaler": scaler,
        "val_metrics": {
            "accuracy": val_accuracy,
            "precision": val_precision,
            "recall": val_recall,
            "f1_score": val_f1,
            "roc_auc": val_roc_auc
        }
    }


def optimize_threshold(
    y_true: List[int],
    y_pred_proba: List[float]
) -> Tuple[float, Dict[str, float]]:
    """Threshold 최적화 (F1-Score 최대화)"""
    print("=" * 80)
    print("Threshold 최적화")
    print("=" * 80)
    
    best_threshold = 0.5
    best_f1 = 0.0
    best_metrics = {}
    
    thresholds = np.arange(0.1, 0.9, 0.01)
    
    for threshold in thresholds:
        y_pred = [1 if p >= threshold else 0 for p in y_pred_proba]
        
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        accuracy = accuracy_score(y_true, y_pred)
        
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = {
                "threshold": threshold,
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1
            }
    
    print(f"\n✅ 최적 Threshold: {best_threshold:.3f}")
    print(f"   Accuracy: {best_metrics['accuracy']:.4f}")
    print(f"   Precision: {best_metrics['precision']:.4f}")
    print(f"   Recall: {best_metrics['recall']:.4f}")
    print(f"   F1-Score: {best_metrics['f1_score']:.4f}")
    
    return best_threshold, best_metrics


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    test_path = dataset_dir / "test.json"
    
    if not train_path.exists() or not val_path.exists() or not test_path.exists():
        print("❌ 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    # 데이터 로드
    print("📂 데이터 로드 중...")
    X_train, y_train = load_dataset(train_path)
    X_val, y_val = load_dataset(val_path)
    X_test, y_test = load_dataset(test_path)
    
    X_train = np.array(X_train)
    X_val = np.array(X_val)
    X_test = np.array(X_test)
    
    print(f"   Train: {len(X_train)}개, Feature 차원: {X_train.shape[1]}")
    print(f"   Val: {len(X_val)}개")
    print(f"   Test: {len(X_test)}개")
    
    # 1. 하이퍼파라미터 최적화
    print("\n" + "=" * 80)
    print("1. 하이퍼파라미터 최적화")
    print("=" * 80)
    opt_result = optimize_hyperparameters(X_train, y_train, X_val, y_val)
    
    # 2. 앙상블 모델
    print("\n" + "=" * 80)
    print("2. 앙상블 모델")
    print("=" * 80)
    ensemble_result = create_ensemble_model(X_train, y_train, X_val, y_val)
    
    # 3. Threshold 최적화 (앙상블 모델 사용)
    print("\n" + "=" * 80)
    print("3. Threshold 최적화")
    print("=" * 80)
    X_val_scaled = ensemble_result["scaler"].transform(X_val)
    y_val_proba = ensemble_result["model"].predict_proba(X_val_scaled)[:, 1]
    best_threshold, threshold_metrics = optimize_threshold(y_val, y_val_proba)
    
    # 4. 테스트 데이터로 최종 평가
    print("\n" + "=" * 80)
    print("4. 테스트 데이터 최종 평가")
    print("=" * 80)
    X_test_scaled = ensemble_result["scaler"].transform(X_test)
    y_test_proba = ensemble_result["model"].predict_proba(X_test_scaled)[:, 1]
    y_test_pred = [1 if p >= best_threshold else 0 for p in y_test_proba]
    
    test_accuracy = accuracy_score(y_test, y_test_pred)
    test_precision = precision_score(y_test, y_test_pred, zero_division=0)
    test_recall = recall_score(y_test, y_test_pred, zero_division=0)
    test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
    test_roc_auc = roc_auc_score(y_test, y_test_proba) if len(set(y_test)) > 1 else 0.5
    
    print(f"\n📊 최종 성능 (Test Set):")
    print(f"   Accuracy: {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
    print(f"   Precision: {test_precision:.4f}")
    print(f"   Recall: {test_recall:.4f}")
    print(f"   F1-Score: {test_f1:.4f}")
    print(f"   ROC-AUC: {test_roc_auc:.4f}")
    print(f"   Threshold: {best_threshold:.3f}")
    
    # 모델 저장
    output_dir = project_root / "models"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "improved_stage2_model.pkl", 'wb') as f:
        pickle.dump({
            "model": ensemble_result["model"],
            "scaler": ensemble_result["scaler"],
            "threshold": best_threshold,
            "feature_dim": X_train.shape[1]
        }, f)
    
    print(f"\n💾 모델 저장: {output_dir / 'improved_stage2_model.pkl'}")
    
    # 결과 저장
    results = {
        "optimization": {
            "best_params": opt_result["params"],
            "cv_score": opt_result["cv_score"],
            "val_metrics": opt_result["val_metrics"]
        },
        "ensemble": {
            "val_metrics": ensemble_result["val_metrics"]
        },
        "threshold": {
            "best_threshold": best_threshold,
            "metrics": threshold_metrics
        },
        "test_metrics": {
            "accuracy": test_accuracy,
            "precision": test_precision,
            "recall": test_recall,
            "f1_score": test_f1,
            "roc_auc": test_roc_auc
        }
    }
    
    with open(output_dir / "improvement_results.json", 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 결과 저장: {output_dir / 'improvement_results.json'}")


if __name__ == "__main__":
    main()

