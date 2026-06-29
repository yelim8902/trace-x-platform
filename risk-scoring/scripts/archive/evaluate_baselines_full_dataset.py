#!/usr/bin/env python3
"""
전체 테스트 데이터셋(752개)에서 주요 baseline 모델들 평가
"""
import sys
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    GradientBoostingClassifier, RandomForestClassifier
)
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

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False

from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import StackingClassifier, VotingClassifier, AdaBoostClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score
)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from scripts.improve_stage2_performance import extract_enhanced_features


def load_dataset(file_path: Path) -> Tuple[List[np.ndarray], List[int]]:
    """데이터셋 로드 및 feature 추출"""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    
    features = []
    labels = []
    
    print(f"   Feature 추출 중... ({len(data)}개 샘플)")
    for i, item in enumerate(data):
        if (i + 1) % 100 == 0:
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
            feature_vector = extract_enhanced_features(stage1_result, ml_features, tx_context)
            features.append(feature_vector)
        except Exception as e:
            if i < 5:  # 처음 몇 개만 에러 출력
                print(f"      Warning: {e}")
            features.append(np.zeros(40, dtype=np.float32))
    
    return features, labels


def evaluate_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    model,
    model_name: str,
    scaler: StandardScaler
) -> Dict[str, Any]:
    """모델 학습 및 평가"""
    print(f"\n{'='*80}")
    print(f"{model_name} 평가 중...")
    print(f"{'='*80}")
    
    # 스케일링
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 학습
    print(f"   학습 중... (Train: {len(X_train)}개)")
    model.fit(X_train_scaled, y_train)
    
    # 예측
    print(f"   예측 중... (Test: {len(X_test)}개)")
    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # 성능 계산
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc = roc_auc_score(y_test, y_pred_proba) if len(set(y_test)) > 1 else 0.5
    
    print(f"   ✅ Accuracy: {acc:.4f} ({acc*100:.2f}%)")
    print(f"   ✅ Precision: {prec:.4f}")
    print(f"   ✅ Recall: {rec:.4f}")
    print(f"   ✅ F1-Score: {f1:.4f}")
    print(f"   ✅ ROC-AUC: {roc:.4f}")
    
    return {
        "model_name": model_name,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1_score": f1,
        "roc_auc": roc
    }


def main():
    """메인 함수"""
    print("=" * 80)
    print("전체 테스트 데이터셋에서 주요 Baseline 모델 평가")
    print("=" * 80)
    
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    test_path = dataset_dir / "test.json"
    
    if not train_path.exists() or not test_path.exists():
        print("❌ 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    X_train, y_train = load_dataset(train_path)
    X_test, y_test = load_dataset(test_path)
    
    X_train = np.array(X_train)
    X_test = np.array(X_test)
    y_train = np.array(y_train)
    y_test = np.array(y_test)
    
    print(f"\n📊 데이터셋 정보:")
    print(f"   Train: {len(X_train)}개, Feature 차원: {X_train.shape[1]}")
    print(f"   Test: {len(X_test)}개")
    print(f"   Train - Fraud: {y_train.sum()}개 ({y_train.sum()/len(y_train)*100:.1f}%)")
    print(f"   Test - Fraud: {y_test.sum()}개 ({y_test.sum()/len(X_test)*100:.1f}%)")
    
    # 스케일러 초기화
    scaler = StandardScaler()
    
    # 주요 모델들 평가
    results = []
    
    # 1. Logistic Regression (가장 간단한 baseline)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        LogisticRegression(max_iter=1000, random_state=42),
        "Logistic Regression",
        StandardScaler()
    ))
    
    # 2. Random Forest
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        "Random Forest",
        StandardScaler()
    ))
    
    # 3. Gradient Boosting
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        GradientBoostingClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting",
        StandardScaler()
    ))
    
    # 4. XGBoost (if available)
    if XGBOOST_AVAILABLE:
        results.append(evaluate_model(
            X_train, y_train, X_test, y_test,
            XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42, eval_metric='logloss'),
            "XGBoost",
            StandardScaler()
        ))
    else:
        print("\n⚠️  XGBoost를 사용할 수 없습니다. 건너뜁니다.")
    
    # 5. LightGBM (최신 모델)
    if LIGHTGBM_AVAILABLE:
        results.append(evaluate_model(
            X_train, y_train, X_test, y_test,
            LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.1, random_state=42, verbose=-1),
            "LightGBM",
            StandardScaler()
        ))
    else:
        print("\n⚠️  LightGBM을 사용할 수 없습니다. 건너뜁니다.")
    
    # 6. CatBoost (최신 모델)
    if CATBOOST_AVAILABLE:
        results.append(evaluate_model(
            X_train, y_train, X_test, y_test,
            CatBoostClassifier(iterations=200, depth=6, learning_rate=0.1, random_seed=42, verbose=False),
            "CatBoost",
            StandardScaler()
        ))
    else:
        print("\n⚠️  CatBoost를 사용할 수 없습니다. 건너뜁니다.")
    
    # 7. Neural Network (MLP)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
        "Neural Network (MLP)",
        StandardScaler()
    ))
    
    # 8. Stacking Ensemble (최신 앙상블 기법)
    if XGBOOST_AVAILABLE and LIGHTGBM_AVAILABLE:
        try:
            base_models = [
                ('rf', RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
                ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42)),
            ]
            if XGBOOST_AVAILABLE:
                base_models.append(('xgb', XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')))
            if LIGHTGBM_AVAILABLE:
                base_models.append(('lgbm', LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)))
            
            stacking_model = StackingClassifier(
                estimators=base_models,
                final_estimator=LogisticRegression(max_iter=1000, random_state=42),
                cv=5
            )
            
            results.append(evaluate_model(
                X_train, y_train, X_test, y_test,
                stacking_model,
                "Stacking Ensemble",
                StandardScaler()
            ))
        except Exception as e:
            print(f"\n⚠️  Stacking Ensemble 실패: {e}. 건너뜁니다.")
    
    # 9. 선행 연구 모델들 (유사 구현)
    print("\n" + "=" * 80)
    print("선행 연구 모델 평가 (유사 구현)")
    print("=" * 80)
    
    # DeepFD: Deep Learning 기반 (MLP)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
        "DeepFD (MLP)",
        StandardScaler()
    ))
    
    # OCGTL: Graph-based (Random Forest로 유사 구현)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight='balanced', n_jobs=-1),
        "OCGTL (RF)",
        StandardScaler()
    ))
    
    # ComGA: Community Detection 기반 (Gradient Boosting으로 유사)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        GradientBoostingClassifier(n_estimators=200, max_depth=10, random_state=42),
        "ComGA (GB)",
        StandardScaler()
    ))
    
    # Flowscope: Flow-based (SVM으로 유사)
    results.append(evaluate_model(
        X_train, y_train, X_test, y_test,
        SVC(kernel='rbf', probability=True, random_state=42, class_weight='balanced', C=10.0),
        "Flowscope (SVM)",
        StandardScaler()
    ))
    
    # GUDI: Graph Unsupervised (XGBoost로 유사)
    if XGBOOST_AVAILABLE:
        results.append(evaluate_model(
            X_train, y_train, X_test, y_test,
            XGBClassifier(n_estimators=200, max_depth=10, random_state=42, eval_metric='logloss'),
            "GUDI (XGB)",
            StandardScaler()
        ))
    
    # MACE: Multi-Attribute (Ensemble로 유사)
    try:
        try:
            # sklearn 1.2+에서는 estimator 파라미터 사용
            mace_model = AdaBoostClassifier(
                estimator=RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1),
                n_estimators=50, random_state=42
            )
        except:
            # 구버전 호환
            try:
                mace_model = AdaBoostClassifier(
                    base_estimator=RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42, n_jobs=-1),
                    n_estimators=50, random_state=42
                )
            except:
                # 최후의 수단: 단순 AdaBoost
                mace_model = AdaBoostClassifier(n_estimators=100, random_state=42)
        
        results.append(evaluate_model(
            X_train, y_train, X_test, y_test,
            mace_model,
            "MACE (Ensemble)",
            StandardScaler()
        ))
    except Exception as e:
        print(f"\n⚠️  MACE (Ensemble) 실패: {e}. 건너뜁니다.")
    
    # 10. Voting Ensemble (최신 앙상블 기법)
    if XGBOOST_AVAILABLE:
        try:
            voting_models = [
                ('rf', RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)),
                ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42)),
                ('xgb', XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')),
            ]
            if LIGHTGBM_AVAILABLE:
                voting_models.append(('lgbm', LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)))
            
            voting_model = VotingClassifier(
                estimators=voting_models,
                voting='soft'
            )
            
            results.append(evaluate_model(
                X_train, y_train, X_test, y_test,
                voting_model,
                "Voting Ensemble",
                StandardScaler()
            ))
        except Exception as e:
            print(f"\n⚠️  Voting Ensemble 실패: {e}. 건너뜁니다.")
    
    # 5. 제안 시스템 (최적화된 모델)
    print(f"\n{'='*80}")
    print("제안 시스템 (최적화된 앙상블 모델) 평가 중...")
    print(f"{'='*80}")
    
    model_path = project_root / "models" / "improved_stage2_model.pkl"
    if model_path.exists():
        import pickle
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        model = model_data['model']
        scaler_loaded = model_data.get('scaler', StandardScaler())
        threshold = model_data.get('threshold', 0.42)
        
        X_test_scaled = scaler_loaded.transform(X_test)
        y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
        y_pred = (y_pred_proba >= threshold).astype(int)
        
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        roc = roc_auc_score(y_test, y_pred_proba) if len(set(y_test)) > 1 else 0.5
        
        print(f"   ✅ Accuracy: {acc:.4f} ({acc*100:.2f}%)")
        print(f"   ✅ Precision: {prec:.4f}")
        print(f"   ✅ Recall: {rec:.4f}")
        print(f"   ✅ F1-Score: {f1:.4f}")
        print(f"   ✅ ROC-AUC: {roc:.4f}")
        
        results.append({
            "model_name": "제안 시스템 (앙상블)",
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": roc
        })
    else:
        print("⚠️  제안 시스템 모델을 찾을 수 없습니다. 건너뜁니다.")
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("최종 결과 (전체 테스트 데이터셋 - 752개 샘플)")
    print("=" * 80)
    print(f"{'Model':<30} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'ROC-AUC':<12}")
    print("-" * 80)
    
    # F1-Score 기준 정렬
    results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    for r in results:
        print(f"{r['model_name']:<30} {r['accuracy']*100:>10.2f}%  {r['precision']:>10.4f}  {r['recall']:>10.4f}  {r['f1_score']:>10.4f}  {r['roc_auc']:>10.4f}")
    
    # 결과 저장
    output_path = dataset_dir / "baseline_comparison_full_test.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

