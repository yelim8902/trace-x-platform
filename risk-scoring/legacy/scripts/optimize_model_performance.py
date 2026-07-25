#!/usr/bin/env python3
"""
모델 성능 최적화 스크립트

하이퍼파라미터 튜닝, Threshold 최적화, 앙상블 모델을 통한 성능 개선

사용법:
    python scripts/optimize_model_performance.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    make_scorer
)
try:
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier
    XGBOOST_AVAILABLE = True
    LIGHTGBM_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    LIGHTGBM_AVAILABLE = False

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.train_mpocryptml_model import extract_features, load_dataset
from scripts.train_hybrid_model import extract_hybrid_features


def find_optimal_threshold(y_true: List[int], y_pred_proba: List[float]) -> float:
    """F1-Score를 최대화하는 최적 Threshold 찾기"""
    best_threshold = 0.5
    best_f1 = 0.0
    
    thresholds = np.arange(0.1, 0.9, 0.01)
    
    for threshold in thresholds:
        y_pred = [1 if prob >= threshold else 0 for prob in y_pred_proba]
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    return best_threshold


def optimize_mpocryptml_model(
    train_path: Path,
    val_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """MPOCryptoML 모델 하이퍼파라미터 튜닝"""
    print("=" * 80)
    print("MPOCryptoML 모델 성능 최적화")
    print("=" * 80)
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    X_train, y_train = load_dataset(train_path)
    X_val, y_val = load_dataset(val_path)
    
    X_train = np.array(X_train)
    X_val = np.array(X_val)
    y_train = np.array(y_train)
    y_val = np.array(y_val)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    results = {}
    
    # 1. Logistic Regression 하이퍼파라미터 튜닝
    print("\n🔍 Logistic Regression 하이퍼파라미터 튜닝 중...")
    param_grid_lr = {
        'C': [0.01, 0.1, 1.0, 10.0, 100.0],
        'penalty': ['l1', 'l2', 'elasticnet'],
        'solver': ['liblinear', 'lbfgs', 'saga'],
        'class_weight': ['balanced', None]
    }
    
    # 일부만 시도 (시간 절약)
    param_grid_lr_small = {
        'C': [0.1, 1.0, 10.0],
        'penalty': ['l2'],
        'solver': ['liblinear', 'lbfgs'],
        'class_weight': ['balanced']
    }
    
    lr_model = LogisticRegression(max_iter=1000, random_state=42)
    grid_search = GridSearchCV(
        lr_model, param_grid_lr_small, 
        cv=3, scoring='f1', n_jobs=-1, verbose=1
    )
    grid_search.fit(X_train_scaled, y_train)
    
    best_lr = grid_search.best_estimator_
    y_pred = best_lr.predict(X_val_scaled)
    y_pred_proba = best_lr.predict_proba(X_val_scaled)[:, 1]
    
    # Threshold 최적화
    optimal_threshold = find_optimal_threshold(y_val.tolist(), y_pred_proba.tolist())
    y_pred_optimized = [1 if prob >= optimal_threshold else 0 for prob in y_pred_proba]
    
    results['logistic_regression'] = {
        'model': best_lr,
        'scaler': scaler,
        'best_params': grid_search.best_params_,
        'optimal_threshold': optimal_threshold,
        'accuracy': accuracy_score(y_val, y_pred_optimized),
        'precision': precision_score(y_val, y_pred_optimized, zero_division=0),
        'recall': recall_score(y_val, y_pred_optimized, zero_division=0),
        'f1_score': f1_score(y_val, y_pred_optimized, zero_division=0),
        'roc_auc': roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
    }
    
    print(f"   최적 파라미터: {grid_search.best_params_}")
    print(f"   최적 Threshold: {optimal_threshold:.4f}")
    print(f"   F1-Score: {results['logistic_regression']['f1_score']:.4f}")
    
    # 2. XGBoost 튜닝 (가능한 경우)
    if XGBOOST_AVAILABLE:
        print("\n🔍 XGBoost 하이퍼파라미터 튜닝 중...")
        param_grid_xgb = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 1.0],
            'colsample_bytree': [0.8, 1.0]
        }
        
        xgb_model = XGBClassifier(random_state=42, eval_metric='logloss')
        grid_search_xgb = GridSearchCV(
            xgb_model, param_grid_xgb,
            cv=3, scoring='f1', n_jobs=-1, verbose=1
        )
        grid_search_xgb.fit(X_train_scaled, y_train)
        
        best_xgb = grid_search_xgb.best_estimator_
        y_pred = best_xgb.predict(X_val_scaled)
        y_pred_proba = best_xgb.predict_proba(X_val_scaled)[:, 1]
        
        optimal_threshold = find_optimal_threshold(y_val.tolist(), y_pred_proba.tolist())
        y_pred_optimized = [1 if prob >= optimal_threshold else 0 for prob in y_pred_proba]
        
        results['xgboost'] = {
            'model': best_xgb,
            'scaler': scaler,
            'best_params': grid_search_xgb.best_params_,
            'optimal_threshold': optimal_threshold,
            'accuracy': accuracy_score(y_val, y_pred_optimized),
            'precision': precision_score(y_val, y_pred_optimized, zero_division=0),
            'recall': recall_score(y_val, y_pred_optimized, zero_division=0),
            'f1_score': f1_score(y_val, y_pred_optimized, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
        }
        
        print(f"   최적 파라미터: {grid_search_xgb.best_params_}")
        print(f"   F1-Score: {results['xgboost']['f1_score']:.4f}")
    
    # 3. LightGBM 튜닝 (가능한 경우)
    if LIGHTGBM_AVAILABLE:
        print("\n🔍 LightGBM 하이퍼파라미터 튜닝 중...")
        param_grid_lgb = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.2],
            'num_leaves': [31, 50, 70]
        }
        
        lgb_model = LGBMClassifier(random_state=42, verbose=-1)
        grid_search_lgb = GridSearchCV(
            lgb_model, param_grid_lgb,
            cv=3, scoring='f1', n_jobs=-1, verbose=1
        )
        grid_search_lgb.fit(X_train_scaled, y_train)
        
        best_lgb = grid_search_lgb.best_estimator_
        y_pred = best_lgb.predict(X_val_scaled)
        y_pred_proba = best_lgb.predict_proba(X_val_scaled)[:, 1]
        
        optimal_threshold = find_optimal_threshold(y_val.tolist(), y_pred_proba.tolist())
        y_pred_optimized = [1 if prob >= optimal_threshold else 0 for prob in y_pred_proba]
        
        results['lightgbm'] = {
            'model': best_lgb,
            'scaler': scaler,
            'best_params': grid_search_lgb.best_params_,
            'optimal_threshold': optimal_threshold,
            'accuracy': accuracy_score(y_val, y_pred_optimized),
            'precision': precision_score(y_val, y_pred_optimized, zero_division=0),
            'recall': recall_score(y_val, y_pred_optimized, zero_division=0),
            'f1_score': f1_score(y_val, y_pred_optimized, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
        }
        
        print(f"   최적 파라미터: {grid_search_lgb.best_params_}")
        print(f"   F1-Score: {results['lightgbm']['f1_score']:.4f}")
    
    # 4. 앙상블 모델 (최고 성능 모델들 결합)
    print("\n🔍 앙상블 모델 구축 중...")
    ensemble_models = []
    
    # 최고 성능 모델들 선택
    sorted_results = sorted(results.items(), key=lambda x: x[1]['f1_score'], reverse=True)
    
    for model_name, model_data in sorted_results[:3]:  # 상위 3개 모델
        ensemble_models.append((model_name, model_data['model']))
    
    if len(ensemble_models) >= 2:
        voting_clf = VotingClassifier(
            estimators=ensemble_models,
            voting='soft'
        )
        voting_clf.fit(X_train_scaled, y_train)
        
        y_pred = voting_clf.predict(X_val_scaled)
        y_pred_proba = voting_clf.predict_proba(X_val_scaled)[:, 1]
        
        optimal_threshold = find_optimal_threshold(y_val.tolist(), y_pred_proba.tolist())
        y_pred_optimized = [1 if prob >= optimal_threshold else 0 for prob in y_pred_proba]
        
        results['ensemble'] = {
            'model': voting_clf,
            'scaler': scaler,
            'optimal_threshold': optimal_threshold,
            'accuracy': accuracy_score(y_val, y_pred_optimized),
            'precision': precision_score(y_val, y_pred_optimized, zero_division=0),
            'recall': recall_score(y_val, y_pred_optimized, zero_division=0),
            'f1_score': f1_score(y_val, y_pred_optimized, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
        }
        
        print(f"   앙상블 F1-Score: {results['ensemble']['f1_score']:.4f}")
    
    # 최고 성능 모델 선택
    best_model_name = max(results.items(), key=lambda x: x[1]['f1_score'])[0]
    best_model_data = results[best_model_name]
    
    print("\n" + "=" * 80)
    print("✅ 최적화 완료!")
    print("=" * 80)
    print(f"\n🏆 최고 성능 모델: {best_model_name}")
    print(f"   F1-Score: {best_model_data['f1_score']:.4f} ({best_model_data['f1_score']*100:.2f}%)")
    print(f"   Accuracy: {best_model_data['accuracy']:.4f} ({best_model_data['accuracy']*100:.2f}%)")
    print(f"   Precision: {best_model_data['precision']:.4f}")
    print(f"   Recall: {best_model_data['recall']:.4f}")
    print(f"   ROC-AUC: {best_model_data['roc_auc']:.4f}")
    
    # 최고 모델 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model_data = {
        'model': best_model_data['model'],
        'scaler': best_model_data['scaler'],
        'optimal_threshold': best_model_data['optimal_threshold'],
        'model_type': best_model_name,
        'best_params': best_model_data.get('best_params', {}),
        'feature_names': [
            "ppr_score", "sdn_ppr", "mixer_ppr", "pattern_score",
            "n_theta", "n_omega", "fan_in_count", "fan_out_count",
            "gather_scatter", "graph_nodes", "graph_edges",
            "pattern_fan_in", "pattern_fan_out", "pattern_gather_scatter",
            "pattern_stack", "pattern_bipartite", "rule_score"
        ]
    }
    
    with open(output_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n💾 최적화된 모델 저장: {output_path}")
    
    return results


def optimize_hybrid_model(
    train_path: Path,
    val_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """Hybrid 모델 하이퍼파라미터 튜닝"""
    print("=" * 80)
    print("Hybrid 모델 성능 최적화")
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
    
    for item in train_data:
        features = extract_hybrid_features(item)
        X_train.append(features)
        label = item.get("ground_truth_label", "normal")
        y_train.append(1 if label == "fraud" else 0)
    
    for item in val_data:
        features = extract_hybrid_features(item)
        X_val.append(features)
        label = item.get("ground_truth_label", "normal")
        y_val.append(1 if label == "fraud" else 0)
    
    X_train = np.array(X_train)
    X_val = np.array(X_val)
    y_train = np.array(y_train)
    y_val = np.array(y_val)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    results = {}
    
    # XGBoost 튜닝
    if XGBOOST_AVAILABLE:
        print("\n🔍 XGBoost 하이퍼파라미터 튜닝 중...")
        param_grid_xgb = {
            'n_estimators': [100, 200],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.1, 0.2],
            'subsample': [0.8, 1.0]
        }
        
        xgb_model = XGBClassifier(random_state=42, eval_metric='logloss')
        grid_search_xgb = GridSearchCV(
            xgb_model, param_grid_xgb,
            cv=3, scoring='f1', n_jobs=-1, verbose=1
        )
        grid_search_xgb.fit(X_train_scaled, y_train)
        
        best_xgb = grid_search_xgb.best_estimator_
        y_pred_proba = best_xgb.predict_proba(X_val_scaled)[:, 1]
        
        optimal_threshold = find_optimal_threshold(y_val.tolist(), y_pred_proba.tolist())
        y_pred_optimized = [1 if prob >= optimal_threshold else 0 for prob in y_pred_proba]
        
        results['xgboost'] = {
            'model': best_xgb,
            'scaler': scaler,
            'best_params': grid_search_xgb.best_params_,
            'optimal_threshold': optimal_threshold,
            'accuracy': accuracy_score(y_val, y_pred_optimized),
            'precision': precision_score(y_val, y_pred_optimized, zero_division=0),
            'recall': recall_score(y_val, y_pred_optimized, zero_division=0),
            'f1_score': f1_score(y_val, y_pred_optimized, zero_division=0),
            'roc_auc': roc_auc_score(y_val, y_pred_proba) if len(set(y_pred_proba)) > 1 else 0.5
        }
        
        print(f"   최적 파라미터: {grid_search_xgb.best_params_}")
        print(f"   F1-Score: {results['xgboost']['f1_score']:.4f}")
    
    # 최고 모델 저장
    if results:
        best_model_name = max(results.items(), key=lambda x: x[1]['f1_score'])[0]
        best_model_data = results[best_model_name]
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model_data = {
            'model': best_model_data['model'],
            'scaler': best_model_data['scaler'],
            'optimal_threshold': best_model_data['optimal_threshold'],
            'model_type': best_model_name,
            'best_params': best_model_data.get('best_params', {})
        }
        
        with open(output_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"\n💾 최적화된 모델 저장: {output_path}")
    
    return results


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="모델 성능 최적화")
    parser.add_argument(
        "--model-type",
        type=str,
        default="both",
        choices=["mpocryptml", "hybrid", "both"],
        help="최적화할 모델 타입"
    )
    args = parser.parse_args()
    
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    models_dir = project_root / "models"
    
    if not train_path.exists() or not val_path.exists():
        print("❌ 학습/검증 데이터를 찾을 수 없습니다.")
        return
    
    all_results = {}
    
    if args.model_type in ["mpocryptml", "both"]:
        output_path = models_dir / "mpocryptml_model_optimized.pkl"
        mpocryptml_results = optimize_mpocryptml_model(train_path, val_path, output_path)
        all_results.update(mpocryptml_results)
    
    if args.model_type in ["hybrid", "both"]:
        output_path = models_dir / "hybrid_model_optimized.pkl"
        hybrid_results = optimize_hybrid_model(train_path, val_path, output_path)
        all_results.update(hybrid_results)
    
    # 결과 저장
    results_path = dataset_dir / "optimization_results.json"
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n📄 최적화 결과 저장: {results_path}")


if __name__ == "__main__":
    main()

