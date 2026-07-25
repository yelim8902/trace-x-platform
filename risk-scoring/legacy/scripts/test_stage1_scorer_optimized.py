#!/usr/bin/env python3
"""
최적화된 1단계 스코어러 테스트
"""
import sys
import json
from pathlib import Path
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    
    if not test_path.exists():
        print("❌ 테스트 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    print("📂 테스트 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   총 {len(test_data)}개 샘플")
    
    # 최적화된 스코어러 (rule_weight=0.9, graph_weight=0.1)
    scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    threshold = 39.0  # Threshold 최적화 결과 (F1 최대화)
    
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    print("\n" + "=" * 80)
    print("최적화된 1단계 스코어러 평가 중...")
    print("=" * 80)
    
    for i, sample in enumerate(test_data):
        if (i + 1) % 100 == 0:
            print(f"  처리 중... {i + 1}/{len(test_data)}")
        
        label = sample.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        
        tx_data = {
            "from": sample.get("from", ""),
            "to": sample.get("to", ""),
            "usd_value": sample.get("usd_value", 0),
            "timestamp": sample.get("timestamp", 0),
            "tx_hash": sample.get("tx_hash", ""),
            "chain": sample.get("chain", "ethereum"),
            "is_sanctioned": sample.get("tx_context", {}).get("is_sanctioned", False),
            "is_mixer": sample.get("tx_context", {}).get("is_mixer", False),
        }
        
        ml_features = sample.get("ml_features", {})
        tx_context = sample.get("tx_context", {})
        
        try:
            result = scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            risk_score = result["risk_score"]
            y_pred_scores.append(risk_score)
            y_pred.append(1 if risk_score >= threshold else 0)
        except Exception as e:
            y_pred_scores.append(0.0)
            y_pred.append(0)
    
    # 지표 계산
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    y_pred_proba = [s / 100.0 for s in y_pred_scores]
    roc_auc = 0.5
    avg_precision = 0.0
    if len(set(y_true)) > 1 and len(set(y_pred_proba)) > 1:
        try:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
            avg_precision = average_precision_score(y_true, y_pred_proba)
        except ValueError:
            pass
    
    cm = confusion_matrix(y_true, y_pred)
    
    print("\n" + "=" * 80)
    print("✅ 최적화된 성능 결과 (Test Set)")
    print("=" * 80)
    print(f"\n📊 성능 지표:")
    print(f"   Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   ROC-AUC:   {roc_auc:.4f}")
    print(f"   Avg Precision: {avg_precision:.4f}")
    
    print(f"\n📋 Confusion Matrix:")
    print(f"   TN: {cm[0][0]}, FP: {cm[0][1]}")
    print(f"   FN: {cm[1][0]}, TP: {cm[1][1]}")
    
    print(f"\n⚙️  사용된 파라미터:")
    print(f"   Rule Weight: 0.9")
    print(f"   Graph Weight: 0.1")
    print(f"   Threshold: {threshold:.1f}")
    
    # 결과 저장
    output_path = dataset_dir / "stage1_scorer_optimized_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "roc_auc": roc_auc,
            "average_precision": avg_precision,
            "confusion_matrix": {
                "true_negative": int(cm[0][0]),
                "false_positive": int(cm[0][1]),
                "false_negative": int(cm[1][0]),
                "true_positive": int(cm[1][1])
            },
            "params": {
                "rule_weight": 0.9,
                "graph_weight": 0.1,
                "threshold": threshold
            }
        }, f, indent=2, ensure_ascii=False)
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

