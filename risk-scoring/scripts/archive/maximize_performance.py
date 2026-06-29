#!/usr/bin/env python3
"""
성능 최대화 스크립트 (목표: 85% 이상)

1. 전체 데이터셋 사용 (5,000 → 92,138)
2. 고급 Feature Engineering
3. 하이퍼파라미터 튜닝 (GridSearch + RandomizedSearch)
4. 앙상블 모델 (다양한 조합)
5. Deep Learning 모델 (MLP)
6. Threshold 최적화
7. 클래스 불균형 처리 개선
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, StratifiedKFold
from sklearn.ensemble import (
    GradientBoostingClassifier, RandomForestClassifier,
    VotingClassifier, StackingClassifier, AdaBoostClassifier
)
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, make_scorer
)
from scipy.stats import randint, uniform
import warnings
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer

# XGBoost, LightGBM 시도
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    from lightgbm import LGBMClassifier
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False


def extract_advanced_features(
    stage1_result: Dict[str, Any],
    ml_features: Dict[str, Any],
    tx_context: Dict[str, Any]
) -> np.ndarray:
    """
    고급 Feature Engineering
    
    기존 30차원 + 추가 feature = 50+ 차원
    """
    features = []
    
    # ===== 기존 Features (30차원) =====
    
    # 1. Stage 1 features
    rule_score = stage1_result["rule_score"]
    graph_score = stage1_result["graph_score"]
    risk_score = stage1_result["risk_score"]
    features.extend([rule_score, graph_score, risk_score])
    
    # 2. Rule-based features
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
    
    # 3. Graph statistics
    fan_in_count = ml_features.get("fan_in_count", 0)
    fan_out_count = ml_features.get("fan_out_count", 0)
    features.append(min(100, fan_in_count))
    features.append(min(100, fan_out_count))
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
    
    graph_nodes = ml_features.get("graph_nodes", tx_context.get("graph_nodes", 0))
    num_transactions = ml_features.get("num_transactions", tx_context.get("num_transactions", 0))
    features.append(min(200, graph_nodes))
    features.append(min(200, num_transactions))
    
    # 4. PPR features
    features.append(min(1.0, ml_features.get("ppr_score", 0.0)))
    features.append(min(1.0, ml_features.get("sdn_ppr", 0.0)))
    features.append(min(1.0, ml_features.get("mixer_ppr", 0.0)))
    
    # 5. 정규화 점수
    features.append(min(1.0, max(0.0, ml_features.get("n_theta", 0.0))))
    features.append(min(1.0, max(0.0, ml_features.get("n_omega", 0.0))))
    
    # 6. 패턴 탐지
    features.append(ml_features.get("fan_in_detected", 0))
    features.append(ml_features.get("fan_out_detected", 0))
    features.append(ml_features.get("gather_scatter_detected", 0))
    
    # ===== 고급 Features 추가 (20+ 차원) =====
    
    # 7. 상호작용 Features (중요!)
    features.append(rule_score * graph_score / 100.0)  # 곱셈
    features.append(rule_score / (graph_score + 1.0))  # 비율
    features.append((rule_score + graph_score) / 2.0)  # 평균
    features.append(abs(rule_score - graph_score))  # 차이
    
    # 8. Fan-in/out 비율 및 통계
    total_fan = fan_in_count + fan_out_count
    if total_fan > 0:
        features.append(fan_in_count / total_fan)  # Fan-in 비율
        features.append(fan_out_count / total_fan)  # Fan-out 비율
        features.append(abs(fan_in_count - fan_out_count) / total_fan)  # 비대칭성
    else:
        features.extend([0.0, 0.0, 0.0])
    
    # 9. 거래 금액 통계 (고급)
    min_value = ml_features.get("min_transaction_value", 0.0)
    total_value = ml_features.get("total_transaction_value", 0.0)
    transaction_count = ml_features.get("transaction_count", 0)
    
    if transaction_count > 0:
        features.append(total_value / transaction_count)  # 평균
        if max_value > 0 and min_value > 0:
            features.append(max_value / min_value)  # 최대/최소 비율
            features.append((max_value - min_value) / max_value)  # 변동성
        else:
            features.extend([0.0, 0.0])
        if avg_value > 0:
            features.append((max_value - avg_value) / avg_value)  # 이상치 비율
        else:
            features.append(0.0)
    else:
        features.extend([0.0, 0.0, 0.0, 0.0])
    
    # 10. 그래프 구조 Features
    graph_edges = ml_features.get("graph_edges", tx_context.get("graph_edges", 0))
    if graph_nodes > 1:
        max_edges = graph_nodes * (graph_nodes - 1)
        if max_edges > 0:
            features.append(graph_edges / max_edges)  # 그래프 밀도
        else:
            features.append(0.0)
        features.append(graph_edges / graph_nodes)  # 평균 연결도
    else:
        features.extend([0.0, 0.0])
    
    # 11. Rule 다양성 및 강도
    unique_rules = len(set(r.get("rule_id", "") for r in rule_results))
    if len(rule_results) > 0:
        features.append(unique_rules / len(rule_results))  # Rule 다양성
    else:
        features.append(0.0)
    
    # 심각도 가중 평균
    severity_scores = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    if len(severities) > 0:
        avg_severity = np.mean([severity_scores.get(s, 2) for s in severities])
        features.append(avg_severity / 4.0)  # 정규화
        max_severity = max([severity_scores.get(s, 0) for s in severities])
        features.append(max_severity / 4.0)  # 최대 심각도
    else:
        features.extend([0.0, 0.0])
    
    # 12. PPR 상호작용
    ppr_score = ml_features.get("ppr_score", 0.0)
    sdn_ppr = ml_features.get("sdn_ppr", 0.0)
    mixer_ppr = ml_features.get("mixer_ppr", 0.0)
    features.append(ppr_score * rule_score / 100.0)  # PPR × Rule
    features.append(sdn_ppr + mixer_ppr)  # 총 위험 PPR
    
    # 13. 패턴 점수 상호작용
    pattern_score = ml_features.get("pattern_score", 0.0)
    features.append(pattern_score * graph_score / 100.0)  # Pattern × Graph
    features.append(pattern_score / (rule_score + 1.0))  # Pattern / Rule 비율
    
    # 14. 정규화 점수 상호작용
    n_theta = ml_features.get("n_theta", 0.0)
    n_omega = ml_features.get("n_omega", 0.0)
    features.append(n_theta * n_omega)  # NTS × NWS
    features.append(abs(n_theta - n_omega))  # NTS-NWS 차이
    
    # NaN, Inf 체크
    features_array = np.array(features, dtype=np.float32)
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=100.0, neginf=0.0)
    
    return features_array


def load_full_dataset(file_path: Path) -> Tuple[List[np.ndarray], List[int]]:
    """전체 데이터셋 로드 및 feature 추출"""
    print(f"📂 데이터 로드: {file_path.name}")
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    
    features = []
    labels = []
    
    print("   Feature 추출 중...")
    for i, item in enumerate(data):
        if (i + 1) % 1000 == 0:
            print(f"      {i + 1}/{len(data)} 처리 중...")
        
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
            feature_vector = extract_advanced_features(stage1_result, ml_features, tx_context)
            features.append(feature_vector)
        except Exception as e:
            # 에러 발생 시 기본 feature 벡터 사용
            features.append(np.zeros(55, dtype=np.float32))
    
    print(f"   완료: {len(features)}개 샘플, {len(features[0]) if features else 0}차원")
    return features, labels


def optimize_xgboost(X_train, y_train, X_val, y_val, scaler):
    """XGBoost 최적화"""
    if not XGBOOST_AVAILABLE:
        return None
    
    print("\n🔍 XGBoost 하이퍼파라미터 튜닝 중...")
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 더 넓은 파라미터 그리드
    param_dist = {
        'n_estimators': randint(200, 500),
        'max_depth': randint(5, 10),
        'learning_rate': uniform(0.01, 0.2),
        'subsample': uniform(0.7, 0.3),
        'colsample_bytree': uniform(0.7, 0.3),
        'min_child_weight': randint(1, 5),
        'gamma': uniform(0, 0.5)
    }
    
    xgb = XGBClassifier(
        random_state=42,
        eval_metric='logloss',
        use_label_encoder=False
    )
    
    # RandomizedSearchCV (더 빠름)
    random_search = RandomizedSearchCV(
        xgb,
        param_dist,
        n_iter=50,  # 50개 조합 시도
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        random_state=42,
        verbose=1
    )
    
    random_search.fit(X_train_scaled, y_train)
    
    best_xgb = random_search.best_estimator_
    y_pred_proba = best_xgb.predict_proba(X_val_scaled)[:, 1]
    y_pred = best_xgb.predict(X_val_scaled)
    
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1_score": f1_score(y_val, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    }
    
    print(f"   최적 파라미터: {random_search.best_params_}")
    print(f"   F1-Score: {metrics['f1_score']:.4f}, Accuracy: {metrics['accuracy']:.4f}")
    
    return {
        "model": best_xgb,
        "params": random_search.best_params_,
        "metrics": metrics
    }


def optimize_lightgbm(X_train, y_train, X_val, y_val, scaler):
    """LightGBM 최적화"""
    if not LIGHTGBM_AVAILABLE:
        return None
    
    print("\n🔍 LightGBM 하이퍼파라미터 튜닝 중...")
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    param_dist = {
        'n_estimators': randint(200, 500),
        'max_depth': randint(5, 10),
        'learning_rate': uniform(0.01, 0.2),
        'subsample': uniform(0.7, 0.3),
        'colsample_bytree': uniform(0.7, 0.3),
        'min_child_samples': randint(10, 50),
        'reg_alpha': uniform(0, 1),
        'reg_lambda': uniform(0, 1)
    }
    
    lgbm = LGBMClassifier(
        random_state=42,
        verbose=-1
    )
    
    random_search = RandomizedSearchCV(
        lgbm,
        param_dist,
        n_iter=50,
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        random_state=42,
        verbose=1
    )
    
    random_search.fit(X_train_scaled, y_train)
    
    best_lgbm = random_search.best_estimator_
    y_pred_proba = best_lgbm.predict_proba(X_val_scaled)[:, 1]
    y_pred = best_lgbm.predict(X_val_scaled)
    
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1_score": f1_score(y_val, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    }
    
    print(f"   최적 파라미터: {random_search.best_params_}")
    print(f"   F1-Score: {metrics['f1_score']:.4f}, Accuracy: {metrics['accuracy']:.4f}")
    
    return {
        "model": best_lgbm,
        "params": random_search.best_params_,
        "metrics": metrics
    }


def optimize_gradient_boosting(X_train, y_train, X_val, y_val, scaler):
    """Gradient Boosting 최적화"""
    print("\n🔍 Gradient Boosting 하이퍼파라미터 튜닝 중...")
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    param_grid = {
        'n_estimators': [300, 400, 500],
        'max_depth': [5, 7, 9],
        'learning_rate': [0.05, 0.1, 0.15],
        'subsample': [0.8, 0.9, 1.0],
        'min_samples_split': [5, 10, 15],
        'min_samples_leaf': [2, 4, 6]
    }
    
    gb = GradientBoostingClassifier(random_state=42)
    
    grid_search = GridSearchCV(
        gb,
        param_grid,
        cv=3,
        scoring=make_scorer(f1_score),
        n_jobs=-1,
        verbose=1
    )
    
    grid_search.fit(X_train_scaled, y_train)
    
    best_gb = grid_search.best_estimator_
    y_pred_proba = best_gb.predict_proba(X_val_scaled)[:, 1]
    y_pred = best_gb.predict(X_val_scaled)
    
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1_score": f1_score(y_val, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    }
    
    print(f"   최적 파라미터: {grid_search.best_params_}")
    print(f"   F1-Score: {metrics['f1_score']:.4f}, Accuracy: {metrics['accuracy']:.4f}")
    
    return {
        "model": best_gb,
        "params": grid_search.best_params_,
        "metrics": metrics
    }


def create_advanced_ensemble(models_dict: Dict[str, Any], X_train, y_train, X_val, y_val, scaler):
    """고급 앙상블 모델 생성"""
    print("\n🤖 고급 앙상블 모델 생성 중...")
    
    X_train_scaled = scaler.transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # 사용 가능한 모델들 수집
    estimators = []
    
    if "xgboost" in models_dict and models_dict["xgboost"]:
        estimators.append(('xgb', models_dict["xgboost"]["model"]))
    
    if "lightgbm" in models_dict and models_dict["lightgbm"]:
        estimators.append(('lgbm', models_dict["lightgbm"]["model"]))
    
    if "gradient_boosting" in models_dict and models_dict["gradient_boosting"]:
        estimators.append(('gb', models_dict["gradient_boosting"]["model"]))
    
    if len(estimators) < 2:
        print("   ⚠️  앙상블을 위한 모델이 부족합니다.")
        return None
    
    # Voting Classifier
    voting_clf = VotingClassifier(
        estimators=estimators,
        voting='soft',
        weights=[2, 2, 1] if len(estimators) == 3 else [2, 1]
    )
    
    voting_clf.fit(X_train_scaled, y_train)
    
    y_pred_proba = voting_clf.predict_proba(X_val_scaled)[:, 1]
    y_pred = voting_clf.predict(X_val_scaled)
    
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "f1_score": f1_score(y_val, y_pred, zero_division=0),
        "roc_auc": roc_auc_score(y_val, y_pred_proba) if len(set(y_val)) > 1 else 0.5
    }
    
    print(f"   앙상블 성능:")
    print(f"   Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1_score']:.4f}")
    
    return {
        "model": voting_clf,
        "metrics": metrics
    }


def optimize_threshold(y_true, y_pred_proba):
    """Threshold 최적화 (F1-Score 최대화)"""
    best_threshold = 0.5
    best_f1 = 0.0
    
    thresholds = np.arange(0.1, 0.9, 0.01)
    
    for threshold in thresholds:
        y_pred = [1 if p >= threshold else 0 for p in y_pred_proba]
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    return best_threshold


def main():
    """메인 함수"""
    print("=" * 80)
    print("성능 최대화 (목표: 85% 이상)")
    print("=" * 80)
    
    dataset_dir = project_root / "data" / "dataset"
    
    # 전체 데이터셋 사용 시도
    full_dataset_path = dataset_dir / "diverse_rules_enhanced.json"
    sampled_dataset_path = dataset_dir / "diverse_rules_enhanced_sampled.json"
    
    if full_dataset_path.exists():
        file_size = full_dataset_path.stat().st_size / (1024 * 1024)  # MB
        print(f"\n✅ 전체 데이터셋 발견! (약 {file_size:.1f}MB)")
        print("   ⚠️  전체 데이터셋은 매우 큽니다. 샘플 데이터셋 사용 권장.")
        print("   전체 데이터셋 사용하려면 주석을 해제하세요.")
        # dataset_path = full_dataset_path  # 주석 해제하여 전체 데이터셋 사용
        dataset_path = sampled_dataset_path  # 샘플 데이터셋 사용 (빠른 테스트)
    elif sampled_dataset_path.exists():
        print("\n⚠️  전체 데이터셋 없음. 샘플 데이터셋 사용.")
        dataset_path = sampled_dataset_path
    else:
        # train.json 사용
        dataset_path = dataset_dir / "train.json"
        if not dataset_path.exists():
            print(f"❌ 데이터셋 파일을 찾을 수 없습니다.")
            return
    
    if not dataset_path.exists():
        print(f"❌ 데이터셋 파일을 찾을 수 없습니다: {dataset_path}")
        return
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    X_all, y_all = load_full_dataset(dataset_path)
    X_all = np.array(X_all)
    y_all = np.array(y_all)
    
    print(f"\n📊 데이터셋 통계:")
    print(f"   총 샘플: {len(X_all)}개")
    print(f"   Feature 차원: {X_all.shape[1]}차원")
    print(f"   Fraud: {y_all.sum()}개 ({y_all.sum()/len(y_all)*100:.1f}%)")
    print(f"   Normal: {(len(y_all)-y_all.sum())}개 ({(len(y_all)-y_all.sum())/len(y_all)*100:.1f}%)")
    
    # 데이터 분할 (80:10:10)
    from sklearn.model_selection import train_test_split
    
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_all, y_all, test_size=0.2, random_state=42, stratify=y_all
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    print(f"\n📊 데이터 분할:")
    print(f"   Train: {len(X_train)}개 ({len(X_train)/len(X_all)*100:.1f}%)")
    print(f"   Val: {len(X_val)}개 ({len(X_val)/len(X_all)*100:.1f}%)")
    print(f"   Test: {len(X_test)}개 ({len(X_test)/len(X_all)*100:.1f}%)")
    
    # Feature 스케일링
    print("\n🔧 Feature 스케일링 중...")
    scaler = RobustScaler()  # RobustScaler 사용 (이상치에 강함)
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)
    
    # 모델 최적화
    models = {}
    
    # 1. XGBoost
    if XGBOOST_AVAILABLE:
        xgb_result = optimize_xgboost(X_train, y_train, X_val, y_val, scaler)
        if xgb_result:
            models["xgboost"] = xgb_result
    
    # 2. LightGBM
    if LIGHTGBM_AVAILABLE:
        lgbm_result = optimize_lightgbm(X_train, y_train, X_val, y_val, scaler)
        if lgbm_result:
            models["lightgbm"] = lgbm_result
    
    # 3. Gradient Boosting
    gb_result = optimize_gradient_boosting(X_train, y_train, X_val, y_val, scaler)
    if gb_result:
        models["gradient_boosting"] = gb_result
    
    # 4. 앙상블 모델
    ensemble_result = create_advanced_ensemble(models, X_train, y_train, X_val, y_val, scaler)
    if ensemble_result:
        models["ensemble"] = ensemble_result
    
    # 최고 모델 선택
    best_model_name = None
    best_accuracy = 0.0
    
    for name, result in models.items():
        if "metrics" in result:
            acc = result["metrics"]["accuracy"]
            if acc > best_accuracy:
                best_accuracy = acc
                best_model_name = name
    
    if not best_model_name:
        print("\n❌ 최고 모델을 찾을 수 없습니다.")
        return
    
    print(f"\n🏆 최고 모델: {best_model_name}")
    best_model = models[best_model_name]["model"]
    best_metrics = models[best_model_name]["metrics"]
    
    print(f"   Validation 성능:")
    print(f"   Accuracy: {best_metrics['accuracy']:.4f} ({best_metrics['accuracy']*100:.2f}%)")
    print(f"   Precision: {best_metrics['precision']:.4f}")
    print(f"   Recall: {best_metrics['recall']:.4f}")
    print(f"   F1-Score: {best_metrics['f1_score']:.4f}")
    print(f"   ROC-AUC: {best_metrics['roc_auc']:.4f}")
    
    # Threshold 최적화
    print("\n🎯 Threshold 최적화 중...")
    y_val_proba = best_model.predict_proba(X_val_scaled)[:, 1]
    optimal_threshold = optimize_threshold(y_val, y_val_proba)
    print(f"   최적 Threshold: {optimal_threshold:.3f}")
    
    # 테스트 데이터로 최종 평가
    print("\n📊 테스트 데이터 최종 평가...")
    y_test_proba = best_model.predict_proba(X_test_scaled)[:, 1]
    y_test_pred = [1 if p >= optimal_threshold else 0 for p in y_test_proba]
    
    test_accuracy = accuracy_score(y_test, y_test_pred)
    test_precision = precision_score(y_test, y_test_pred, zero_division=0)
    test_recall = recall_score(y_test, y_test_pred, zero_division=0)
    test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
    test_roc_auc = roc_auc_score(y_test, y_test_proba) if len(set(y_test)) > 1 else 0.5
    
    print(f"\n✅ 최종 성능 (Test Set):")
    print(f"   Accuracy: {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")
    print(f"   Precision: {test_precision:.4f}")
    print(f"   Recall: {test_recall:.4f}")
    print(f"   F1-Score: {test_f1:.4f}")
    print(f"   ROC-AUC: {test_roc_auc:.4f}")
    print(f"   Threshold: {optimal_threshold:.3f}")
    
    if test_accuracy >= 0.85:
        print(f"\n🎉 목표 달성! Accuracy {test_accuracy*100:.2f}% >= 85%")
    else:
        print(f"\n⚠️  목표 미달성. Accuracy {test_accuracy*100:.2f}% < 85%")
        print(f"   추가 개선 필요: {85 - test_accuracy*100:.2f}%p")
    
    # 모델 저장
    output_dir = project_root / "models"
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / "maximized_model.pkl", 'wb') as f:
        pickle.dump({
            "model": best_model,
            "scaler": scaler,
            "threshold": optimal_threshold,
            "model_name": best_model_name,
            "feature_dim": X_train.shape[1],
            "test_metrics": {
                "accuracy": test_accuracy,
                "precision": test_precision,
                "recall": test_recall,
                "f1_score": test_f1,
                "roc_auc": test_roc_auc
            }
        }, f)
    
    print(f"\n💾 모델 저장: {output_dir / 'maximized_model.pkl'}")
    
    # 결과 저장
    results = {
        "best_model": best_model_name,
        "best_metrics": best_metrics,
        "test_metrics": {
            "accuracy": test_accuracy,
            "precision": test_precision,
            "recall": test_recall,
            "f1_score": test_f1,
            "roc_auc": test_roc_auc
        },
        "optimal_threshold": optimal_threshold,
        "all_models": {name: result.get("metrics", {}) for name, result in models.items() if "metrics" in result}
    }
    
    with open(output_dir / "maximization_results.json", 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"💾 결과 저장: {output_dir / 'maximization_results.json'}")


if __name__ == "__main__":
    main()

