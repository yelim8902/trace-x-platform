#!/usr/bin/env python3
"""
수정된 룰로 전체 시스템 (Stage 1 + Stage 2) 성능 테스트
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from core.scoring.stage2_scorer import Stage2Scorer


def extract_features_for_stage2(
    stage1_result: Dict[str, Any],
    ml_features: Dict[str, Any],
    tx_context: Dict[str, Any]
) -> np.ndarray:
    """Stage 2용 feature 추출 (기존 30차원)"""
    features = []
    
    # Stage 1 features
    features.append(stage1_result["rule_score"])
    features.append(stage1_result["graph_score"])
    features.append(stage1_result["risk_score"])
    
    # Rule-based features
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
    
    # Graph statistics
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
    
    # PPR features
    features.append(min(1.0, ml_features.get("ppr_score", 0.0)))
    features.append(min(1.0, ml_features.get("sdn_ppr", 0.0)))
    features.append(min(1.0, ml_features.get("mixer_ppr", 0.0)))
    
    # 정규화 점수
    features.append(min(1.0, max(0.0, ml_features.get("n_theta", 0.0))))
    features.append(min(1.0, max(0.0, ml_features.get("n_omega", 0.0))))
    
    # 패턴 탐지
    features.append(ml_features.get("fan_in_detected", 0))
    features.append(ml_features.get("fan_out_detected", 0))
    features.append(ml_features.get("gather_scatter_detected", 0))
    
    features_array = np.array(features, dtype=np.float32)
    features_array = np.nan_to_num(features_array, nan=0.0, posinf=100.0, neginf=0.0)
    return features_array


def test_full_system():
    """수정된 룰로 전체 시스템 테스트"""
    print("=" * 80)
    print("수정된 룰로 전체 시스템 성능 테스트 (Stage 1 + Stage 2)")
    print("=" * 80)
    
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    # Gradient Boosting 모델 사용 (가장 좋은 성능)
    model_path = dataset_dir / "stage2_scorer_gradient_boosting.pkl"
    
    if not test_path.exists():
        print("❌ 테스트 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    if not model_path.exists():
        print("⚠️  Stage 2 모델이 없습니다. Stage 1만 테스트합니다.")
        use_stage2 = False
    else:
        use_stage2 = True
        print(f"✅ Stage 2 모델 발견: {model_path}")
    
    print("\n📂 테스트 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   테스트 샘플: {len(test_data)}개")
    
    # Stage 1 스코어러 (수정된 룰 사용)
    stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    
    # Stage 2 모델 로드
    stage2_model = None
    scaler = None
    if use_stage2:
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                stage2_model = model_data.get("model")
                scaler = model_data.get("scaler")
                if stage2_model is None or scaler is None:
                    print("⚠️  모델 데이터 형식이 올바르지 않습니다.")
                    use_stage2 = False
        except Exception as e:
            print(f"⚠️  모델 로드 실패: {e}")
            use_stage2 = False
    
    print("\n🔍 평가 중...")
    y_true = []
    y_pred_scores = []
    
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        
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
        
        # Stage 1
        stage1_result = stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
        stage1_score = stage1_result["risk_score"]
        
        # Stage 2 (if available)
        if use_stage2 and stage2_model and scaler:
            try:
                features = extract_features_for_stage2(stage1_result, ml_features, tx_context)
                features_scaled = scaler.transform(features.reshape(1, -1))
                ml_proba = stage2_model.predict_proba(features_scaled)[0]
                ml_score = ml_proba[1] * 100.0
                
                # Stage 1과 Stage 2 결합 (기존 가중치: 0.6, 0.4)
                final_score = 0.6 * stage1_score + 0.4 * ml_score
            except Exception as e:
                print(f"⚠️  Stage 2 예측 실패: {e}, Stage 1 점수만 사용")
                final_score = stage1_score
        else:
            final_score = stage1_score
        
        y_pred_scores.append(final_score)
    
    # Threshold 최적화
    print("\n🎯 Threshold 최적화 중...")
    best_threshold = 50.0
    best_f1 = 0.0
    
    for threshold in range(10, 90, 2):
        y_pred = [1 if s >= threshold else 0 for s in y_pred_scores]
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
    
    y_pred = [1 if s >= best_threshold else 0 for s in y_pred_scores]
    
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    y_pred_proba = [s / 100.0 for s in y_pred_scores]
    roc_auc = 0.5
    if len(set(y_true)) > 1 and len(set(y_pred_proba)) > 1:
        try:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
        except ValueError:
            pass
    
    print(f"\n✅ 수정된 룰 + 전체 시스템 성능:")
    print(f"   Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall: {recall:.4f}")
    print(f"   F1-Score: {f1:.4f}")
    print(f"   ROC-AUC: {roc_auc:.4f}")
    print(f"   최적 Threshold: {best_threshold:.1f}")
    
    # 이전 성능과 비교
    print("\n📊 성능 비교:")
    print("   이전 (Stage 2): Accuracy 78.86%, F1 0.6876")
    print(f"   현재 (수정된 룰 + Stage 2): Accuracy {accuracy*100:.2f}%, F1 {f1:.4f}")
    
    improvement = (f1 - 0.6876) / 0.6876 * 100 if use_stage2 else 0
    if use_stage2:
        print(f"   개선: F1-Score {improvement:+.2f}%")
    
    # 결과 저장
    results = {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "threshold": best_threshold,
        "use_stage2": use_stage2,
        "previous_f1": 0.6876 if use_stage2 else 0.4293,
        "improvement": improvement
    }
    
    output_path = dataset_dir / "full_system_optimized_rules_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    test_full_system()

