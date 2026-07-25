#!/usr/bin/env python3
"""
1단계 스코어러 성능 최적화 스크립트

가중치와 그래프 점수 로직을 최적화하여 성능 향상
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score
)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer


def evaluate_with_params(
    val_data: List[Dict[str, Any]],
    rule_weight: float,
    graph_weight: float,
    threshold: float = 50.0,
    graph_score_multiplier: float = 1.0
) -> Dict[str, Any]:
    """
    특정 파라미터로 평가
    
    Args:
        val_data: 검증 데이터
        rule_weight: Rule-based 점수 가중치
        graph_weight: 그래프 통계 점수 가중치
        threshold: Risk Score 임계값
        graph_score_multiplier: 그래프 점수 배율 (조정용)
    """
    # Stage1Scorer를 수정하여 그래프 점수 배율 적용
    scorer = Stage1Scorer(rule_weight=rule_weight, graph_weight=graph_weight)
    
    # 그래프 점수 계산 메서드를 임시로 수정
    original_calculate_graph_score = scorer._calculate_graph_score
    
    def modified_calculate_graph_score(ml_features, tx_context):
        score, features = original_calculate_graph_score(ml_features, tx_context)
        return score * graph_score_multiplier, features
    
    scorer._calculate_graph_score = modified_calculate_graph_score
    
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    for sample in val_data:
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
    if len(set(y_true)) > 1 and len(set(y_pred_proba)) > 1:
        try:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
        except ValueError:
            pass
    
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "roc_auc": roc_auc,
        "params": {
            "rule_weight": rule_weight,
            "graph_weight": graph_weight,
            "threshold": threshold,
            "graph_score_multiplier": graph_score_multiplier
        }
    }


def optimize_stage1_scorer(
    val_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    최적 파라미터 찾기
    """
    print("=" * 80)
    print("1단계 스코어러 최적화")
    print("=" * 80)
    
    best_f1 = -1.0
    best_params = None
    best_results = None
    
    # 파라미터 그리드 탐색 (축소: 더 빠른 탐색)
    rule_weights = [0.6, 0.7, 0.8, 0.9]
    graph_weights = [0.4, 0.3, 0.2, 0.1]
    graph_multipliers = [0.4, 0.5, 0.6, 0.7]
    thresholds = [45.0, 50.0, 55.0]
    
    total_combinations = len(rule_weights) * len(graph_weights) * len(graph_multipliers) * len(thresholds)
    current = 0
    
    print(f"\n총 {total_combinations}개 조합 탐색 중...\n")
    
    for rule_w in rule_weights:
        for graph_w in graph_weights:
            # 가중치 합이 1.0이 되도록 조정
            if abs(rule_w + graph_w - 1.0) > 0.01:
                continue
            
            for graph_mult in graph_multipliers:
                for threshold in thresholds:
                    current += 1
                    if current % 50 == 0:
                        print(f"  진행 중... {current}/{total_combinations} (현재 최고 F1: {best_f1:.4f})")
                    
                    results = evaluate_with_params(
                        val_data,
                        rule_weight=rule_w,
                        graph_weight=graph_w,
                        threshold=threshold,
                        graph_score_multiplier=graph_mult
                    )
                    
                    f1 = results["f1_score"]
                    
                    if f1 > best_f1:
                        best_f1 = f1
                        best_params = results["params"]
                        best_results = results
                        
                        print(f"\n  ✅ 새로운 최고 성능 발견!")
                        print(f"     F1-Score: {f1:.4f}")
                        print(f"     Accuracy: {results['accuracy']:.4f}")
                        print(f"     Precision: {results['precision']:.4f}")
                        print(f"     Recall: {results['recall']:.4f}")
                        print(f"     ROC-AUC: {results['roc_auc']:.4f}")
                        print(f"     Params: rule_weight={rule_w}, graph_weight={graph_w}, "
                              f"graph_mult={graph_mult}, threshold={threshold}")
    
    return {
        "best_params": best_params,
        "best_results": best_results
    }


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    val_path = dataset_dir / "val.json"
    
    if not val_path.exists():
        print("❌ 검증 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    print("📂 검증 데이터 로드 중...")
    with open(val_path, 'r') as f:
        val_data = json.load(f)
    
    print(f"   총 {len(val_data)}개 샘플")
    
    # 최적화
    optimization_result = optimize_stage1_scorer(val_data)
    
    best_params = optimization_result["best_params"]
    best_results = optimization_result["best_results"]
    
    print("\n" + "=" * 80)
    print("✅ 최적화 완료")
    print("=" * 80)
    print(f"\n📊 최적 파라미터:")
    print(f"   Rule Weight: {best_params['rule_weight']:.2f}")
    print(f"   Graph Weight: {best_params['graph_weight']:.2f}")
    print(f"   Graph Score Multiplier: {best_params['graph_score_multiplier']:.2f}")
    print(f"   Threshold: {best_params['threshold']:.1f}")
    
    print(f"\n📈 최적 성능 (Validation Set):")
    print(f"   Accuracy:  {best_results['accuracy']:.4f} ({best_results['accuracy']*100:.2f}%)")
    print(f"   Precision: {best_results['precision']:.4f}")
    print(f"   Recall:    {best_results['recall']:.4f}")
    print(f"   F1-Score:  {best_results['f1_score']:.4f}")
    print(f"   ROC-AUC:   {best_results['roc_auc']:.4f}")
    
    # 결과 저장
    output_path = dataset_dir / "stage1_scorer_optimization.json"
    with open(output_path, 'w') as f:
        json.dump(optimization_result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

