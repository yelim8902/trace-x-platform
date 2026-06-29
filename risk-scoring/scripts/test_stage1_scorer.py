#!/usr/bin/env python3
"""
1단계 스코어러 테스트 및 평가 스크립트
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer


def evaluate_stage1_scorer(
    test_data: List[Dict[str, Any]],
    threshold: float = 50.0
) -> Dict[str, Any]:
    """
    1단계 스코어러 평가
    
    Args:
        test_data: 테스트 데이터
        threshold: Risk Score 임계값 (기본 50.0)
    
    Returns:
        평가 결과 딕셔너리
    """
    scorer = Stage1Scorer()
    
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    rule_scores = []
    graph_scores = []
    
    print("=" * 80)
    print("1단계 스코어러 평가 중...")
    print("=" * 80)
    
    for i, sample in enumerate(test_data):
        if (i + 1) % 100 == 0:
            print(f"  처리 중... {i + 1}/{len(test_data)}")
        
        # Ground truth
        label = sample.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        
        # 거래 데이터 준비
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
        
        # ML features
        ml_features = sample.get("ml_features", {})
        
        # TX context
        tx_context = sample.get("tx_context", {})
        
        # 점수 계산
        try:
            result = scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            risk_score = result["risk_score"]
            rule_score = result["rule_score"]
            graph_score = result["graph_score"]
            
            y_pred_scores.append(risk_score)
            rule_scores.append(rule_score)
            graph_scores.append(graph_score)
            
            # 예측 라벨
            predicted_label = "fraud" if risk_score >= threshold else "normal"
            y_pred.append(1 if predicted_label == "fraud" else 0)
        except Exception as e:
            print(f"  ⚠️  에러 (샘플 {i}): {e}")
            y_pred_scores.append(0.0)
            y_pred.append(0)
            rule_scores.append(0.0)
            graph_scores.append(0.0)
    
    # 지표 계산
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # ROC-AUC 및 Average Precision
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
    
    # 통계
    avg_rule_score = sum(rule_scores) / len(rule_scores) if rule_scores else 0.0
    avg_graph_score = sum(graph_scores) / len(graph_scores) if graph_scores else 0.0
    avg_risk_score = sum(y_pred_scores) / len(y_pred_scores) if y_pred_scores else 0.0
    
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
        },
        "statistics": {
            "avg_rule_score": avg_rule_score,
            "avg_graph_score": avg_graph_score,
            "avg_risk_score": avg_risk_score,
            "threshold": threshold
        }
    }


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    
    if not test_path.exists():
        print("❌ 테스트 데이터셋 파일을 찾을 수 없습니다.")
        print(f"   경로: {test_path}")
        return
    
    # 데이터 로드
    print("📂 테스트 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    print(f"   총 {len(test_data)}개 샘플")
    
    # 라벨 분포 확인
    labels = [item.get("ground_truth_label", "normal") for item in test_data]
    label_counts = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\n라벨 분포:")
    for label, count in label_counts.items():
        print(f"  {label}: {count}개 ({count/len(test_data)*100:.1f}%)")
    
    # 평가
    results = evaluate_stage1_scorer(test_data, threshold=50.0)
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("✅ 평가 결과")
    print("=" * 80)
    print(f"\n📊 성능 지표:")
    print(f"   Accuracy:  {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
    print(f"   Precision: {results['precision']:.4f}")
    print(f"   Recall:    {results['recall']:.4f}")
    print(f"   F1-Score:  {results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {results['roc_auc']:.4f}")
    print(f"   Avg Precision: {results['average_precision']:.4f}")
    
    print(f"\n📈 통계:")
    stats = results['statistics']
    print(f"   평균 Rule Score: {stats['avg_rule_score']:.2f}")
    print(f"   평균 Graph Score: {stats['avg_graph_score']:.2f}")
    print(f"   평균 Risk Score: {stats['avg_risk_score']:.2f}")
    print(f"   Threshold: {stats['threshold']:.1f}")
    
    print(f"\n📋 Confusion Matrix:")
    cm = results['confusion_matrix']
    print(f"   TN: {cm['true_negative']}, FP: {cm['false_positive']}")
    print(f"   FN: {cm['false_negative']}, TP: {cm['true_positive']}")
    
    # 결과 저장
    output_path = dataset_dir / "stage1_scorer_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

