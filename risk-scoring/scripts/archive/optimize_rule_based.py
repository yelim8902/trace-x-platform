#!/usr/bin/env python3
"""
Rule-based 스코어러 최적화 스크립트

다양한 집계 방식과 가중치 조절로 성능 개선
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.improved_rule_scorer import optimize_rule_scorer, ImprovedRuleScorer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)


def evaluate_rule_scorer(
    test_data: List[dict],
    scorer: ImprovedRuleScorer,
    threshold: float = 50.0
) -> dict:
    """Rule-based 스코어러 평가"""
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    for item in test_data:
        rule_results = item.get("rule_results", [])
        label = item.get("ground_truth_label", "normal")
        
        # 거래 컨텍스트 전달 (ML 피처 포함)
        tx_context = {
            "num_transactions": item.get("num_transactions", 0),
            "graph_nodes": item.get("graph_nodes", 0),
            "graph_edges": item.get("graph_edges", 0),
            "ml_features": item.get("ml_features", {})
        }
        
        score = scorer.calculate_score(rule_results, tx_context)
        predicted_label = "fraud" if score >= threshold else "normal"
        
        y_true.append(1 if label == "fraud" else 0)
        y_pred.append(1 if predicted_label == "fraud" else 0)
        y_pred_scores.append(score / 100.0)  # 0~1 범위로 정규화
    
    # 지표 계산
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    try:
        roc_auc = roc_auc_score(y_true, y_pred_scores) if len(set(y_pred_scores)) > 1 else 0.5
        avg_precision = average_precision_score(y_true, y_pred_scores)
    except:
        roc_auc = 0.5
        avg_precision = 0.0
    
    cm = confusion_matrix(y_true, y_pred)
    
    return {
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
        }
    }


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
    with open(train_path, 'r') as f:
        train_data = json.load(f)
    with open(val_path, 'r') as f:
        val_data = json.load(f)
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   Train: {len(train_data)}개")
    print(f"   Val: {len(val_data)}개")
    print(f"   Test: {len(test_data)}개")
    
    # 최적화
    print("\n🔍 Rule-based 스코어러 최적화 중...")
    optimization_result = optimize_rule_scorer(train_data, val_data)
    
    best_config = optimization_result["config"]
    best_scorer = optimization_result["scorer"]
    
    # 테스트 데이터로 최종 평가
    print("\n📊 테스트 데이터로 최종 평가...")
    threshold = best_config.get("threshold", 50.0)
    test_results = evaluate_rule_scorer(test_data, best_scorer, threshold)
    
    print("\n" + "=" * 80)
    print("✅ 최종 성능 (Test Set)")
    print("=" * 80)
    print(f"   Accuracy:  {test_results['accuracy']:.4f} ({test_results['accuracy']*100:.2f}%)")
    print(f"   Precision: {test_results['precision']:.4f}")
    print(f"   Recall:    {test_results['recall']:.4f}")
    print(f"   F1-Score:  {test_results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {test_results['roc_auc']:.4f}")
    print(f"   Avg Precision: {test_results['average_precision']:.4f}")
    
    cm = test_results['confusion_matrix']
    print(f"\n   Confusion Matrix:")
    print(f"     TN: {cm['true_negative']}, FP: {cm['false_positive']}")
    print(f"     FN: {cm['false_negative']}, TP: {cm['true_positive']}")
    
    # 결과 저장
    output_path = dataset_dir / "rule_based_optimization_results.json"
    with open(output_path, 'w') as f:
        json.dump({
            "config": best_config,
            "validation_results": optimization_result["results"],
            "test_results": test_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

