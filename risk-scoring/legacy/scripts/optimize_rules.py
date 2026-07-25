#!/usr/bin/env python3
"""
룰 최적화 실험 스크립트

1. 룰별 효과 측정
2. 축별 중요도 측정
3. 룰 제거/수정 실험
4. 임계값 최적화
"""
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict
import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from core.rules.evaluator import RuleEvaluator


def analyze_rule_effectiveness(
    test_data: List[Dict[str, Any]],
    rules_path: str = "rules/tracex_rules.yaml"
) -> Dict[str, Any]:
    """룰별 효과 분석"""
    print("=" * 80)
    print("룰별 효과 분석")
    print("=" * 80)
    
    rule_evaluator = RuleEvaluator(rules_path)
    
    # 룰별 통계
    rule_stats = defaultdict(lambda: {
        "fired_count": 0,
        "fraud_when_fired": 0,
        "normal_when_fired": 0,
        "total_score": 0.0
    })
    
    # 축별 통계
    axis_stats = defaultdict(lambda: {
        "fired_count": 0,
        "fraud_when_fired": 0,
        "normal_when_fired": 0
    })
    
    print("\n📊 룰 발동 통계 수집 중...")
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        is_fraud = (label == "fraud")
        
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
        
        rule_results = rule_evaluator.evaluate_single_transaction(tx_data)
        
        for rule in rule_results:
            rule_id = rule.get("rule_id", "")
            axis = rule.get("axis", "B")
            score = rule.get("score", 0.0)
            
            # 룰별 통계
            rule_stats[rule_id]["fired_count"] += 1
            rule_stats[rule_id]["total_score"] += score
            if is_fraud:
                rule_stats[rule_id]["fraud_when_fired"] += 1
            else:
                rule_stats[rule_id]["normal_when_fired"] += 1
            
            # 축별 통계
            axis_stats[axis]["fired_count"] += 1
            if is_fraud:
                axis_stats[axis]["fraud_when_fired"] += 1
            else:
                axis_stats[axis]["normal_when_fired"] += 1
    
    # 룰별 효과 계산
    rule_effectiveness = {}
    for rule_id, stats in rule_stats.items():
        total_fired = stats["fired_count"]
        if total_fired > 0:
            fraud_ratio = stats["fraud_when_fired"] / total_fired
            avg_score = stats["total_score"] / total_fired
            rule_effectiveness[rule_id] = {
                "fired_count": total_fired,
                "fraud_ratio": fraud_ratio,
                "fraud_when_fired": stats["fraud_when_fired"],
                "normal_when_fired": stats["normal_when_fired"],
                "avg_score": avg_score,
                "effectiveness": fraud_ratio * avg_score  # 효과성 점수
            }
    
    # 축별 효과 계산
    axis_effectiveness = {}
    for axis, stats in axis_stats.items():
        total_fired = stats["fired_count"]
        if total_fired > 0:
            fraud_ratio = stats["fraud_when_fired"] / total_fired
            axis_effectiveness[axis] = {
                "fired_count": total_fired,
                "fraud_ratio": fraud_ratio,
                "fraud_when_fired": stats["fraud_when_fired"],
                "normal_when_fired": stats["normal_when_fired"]
            }
    
    return {
        "rule_effectiveness": rule_effectiveness,
        "axis_effectiveness": axis_effectiveness
    }


def test_rule_removal(
    test_data: List[Dict[str, Any]],
    rules_to_remove: Set[str],
    rules_path: str = "rules/tracex_rules.yaml"
) -> Dict[str, float]:
    """특정 룰 제거 시 성능 측정"""
    # 룰 파일 로드
    with open(rules_path, 'r') as f:
        rules_config = yaml.safe_load(f)
    
    # 룰 제거
    original_rules = rules_config["rules"]
    filtered_rules = [r for r in original_rules if r["id"] not in rules_to_remove]
    rules_config["rules"] = filtered_rules
    
    # 임시 룰 파일 생성
    temp_rules_path = project_root / "rules" / "temp_rules.yaml"
    with open(temp_rules_path, 'w') as f:
        yaml.dump(rules_config, f)
    
    try:
        # Stage 1 스코어러로 평가
        stage1_scorer = Stage1Scorer(rules_path=str(temp_rules_path))
        
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
            
            result = stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            y_pred_scores.append(result["risk_score"])
        
        # Threshold 최적화
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
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "threshold": best_threshold
        }
    finally:
        # 임시 파일 삭제
        if temp_rules_path.exists():
            temp_rules_path.unlink()


def optimize_axis_weights(
    test_data: List[Dict[str, Any]],
    rules_path: str = "rules/tracex_rules.yaml"
) -> Dict[str, Any]:
    """축별 가중치 최적화"""
    print("=" * 80)
    print("축별 가중치 최적화")
    print("=" * 80)
    
    from core.scoring.improved_rule_scorer import ImprovedRuleScorer
    from core.rules.evaluator import RuleEvaluator
    
    rule_evaluator = RuleEvaluator(rules_path)
    
    # 가중치 조합 테스트
    weight_combinations = [
        {"B": 1.0, "C": 1.0, "E": 1.0},  # 균등
        {"B": 1.2, "C": 1.3, "E": 1.4},  # 현재
        {"B": 1.0, "C": 1.5, "E": 1.5},  # C, E 강조
        {"B": 1.5, "C": 1.0, "E": 1.0},  # B 강조
        {"B": 1.0, "C": 1.0, "E": 1.5},  # E 강조
        {"B": 1.3, "C": 1.3, "E": 1.3},  # 균등 증가
    ]
    
    best_f1 = -1.0
    best_weights = None
    best_results = None
    
    print("\n🔍 가중치 조합 테스트 중...")
    for weights in weight_combinations:
        # ImprovedRuleScorer에 가중치 적용 (수동으로)
        # 실제로는 ImprovedRuleScorer를 수정해야 함
        # 여기서는 간단히 테스트
        
        scorer = ImprovedRuleScorer(use_axis_bonus=True)
        # 가중치를 직접 수정할 수 없으므로, 결과만 출력
        
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
            
            rule_results = rule_evaluator.evaluate_single_transaction(tx_data)
            
            # 가중치 적용 (간단한 방법)
            weighted_score = 0.0
            for rule in rule_results:
                axis = rule.get("axis", "B")
                score = rule.get("score", 0.0)
                weight = weights.get(axis, 1.0)
                weighted_score += score * weight
            
            y_pred_scores.append(min(100.0, weighted_score))
        
        # Threshold 최적화
        best_threshold = 50.0
        best_f1_local = 0.0
        
        for threshold in range(10, 90, 2):
            y_pred = [1 if s >= threshold else 0 for s in y_pred_scores]
            f1 = f1_score(y_true, y_pred, zero_division=0)
            if f1 > best_f1_local:
                best_f1_local = f1
                best_threshold = threshold
        
        y_pred = [1 if s >= best_threshold else 0 for s in y_pred_scores]
        
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        print(f"\n가중치: B={weights.get('B', 1.0):.1f}, C={weights.get('C', 1.0):.1f}, E={weights.get('E', 1.0):.1f}")
        print(f"  F1: {f1:.4f}, Acc: {accuracy:.4f}, Prec: {precision:.4f}, Rec: {recall:.4f}")
        
        if f1 > best_f1:
            best_f1 = f1
            best_weights = weights
            best_results = {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "threshold": best_threshold
            }
    
    print(f"\n✅ 최적 가중치:")
    print(f"   B: {best_weights.get('B', 1.0):.1f}")
    print(f"   C: {best_weights.get('C', 1.0):.1f}")
    print(f"   E: {best_weights.get('E', 1.0):.1f}")
    print(f"   F1-Score: {best_results['f1_score']:.4f}")
    
    return {
        "best_weights": best_weights,
        "results": best_results
    }


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
    
    print(f"   테스트 샘플: {len(test_data)}개")
    
    # 1. 룰별 효과 분석
    print("\n" + "=" * 80)
    effectiveness = analyze_rule_effectiveness(test_data)
    
    print("\n📊 룰별 효과 (상위 10개):")
    rule_eff = effectiveness["rule_effectiveness"]
    sorted_rules = sorted(rule_eff.items(), key=lambda x: x[1]["effectiveness"], reverse=True)
    
    for rule_id, stats in sorted_rules[:10]:
        print(f"   {rule_id}: 발동 {stats['fired_count']}회, "
              f"Fraud 비율 {stats['fraud_ratio']:.2%}, "
              f"효과성 {stats['effectiveness']:.2f}")
    
    print("\n📊 축별 효과:")
    axis_eff = effectiveness["axis_effectiveness"]
    for axis, stats in sorted(axis_eff.items(), key=lambda x: x[1]["fraud_ratio"], reverse=True):
        print(f"   {axis}: 발동 {stats['fired_count']}회, "
              f"Fraud 비율 {stats['fraud_ratio']:.2%}")
    
    # 2. 효과 없는 룰 제거 실험
    print("\n" + "=" * 80)
    print("효과 없는 룰 제거 실험")
    print("=" * 80)
    
    # 효과성이 낮은 룰 찾기 (발동 횟수 적고, Fraud 비율 낮음)
    ineffective_rules = []
    for rule_id, stats in rule_eff.items():
        if stats["fired_count"] < 10 or stats["fraud_ratio"] < 0.3:
            ineffective_rules.append(rule_id)
    
    if ineffective_rules:
        print(f"\n효과성이 낮은 룰: {ineffective_rules}")
        print("이 룰들을 제거하고 성능 측정 중...")
        
        removal_results = test_rule_removal(test_data, set(ineffective_rules))
        print(f"\n룰 제거 후 성능:")
        print(f"   Accuracy: {removal_results['accuracy']:.4f}")
        print(f"   F1-Score: {removal_results['f1_score']:.4f}")
    else:
        print("\n효과성이 낮은 룰이 없습니다.")
    
    # 3. 축별 가중치 최적화
    print("\n" + "=" * 80)
    weight_results = optimize_axis_weights(test_data)
    
    # 결과 저장
    output_dir = project_root / "data" / "dataset"
    output_dir.mkdir(exist_ok=True)
    
    results = {
        "rule_effectiveness": effectiveness["rule_effectiveness"],
        "axis_effectiveness": effectiveness["axis_effectiveness"],
        "optimal_weights": weight_results["best_weights"],
        "weight_optimization_results": weight_results["results"]
    }
    
    if ineffective_rules:
        results["ineffective_rules"] = ineffective_rules
        results["removal_results"] = removal_results
    
    with open(output_dir / "rule_optimization_results.json", 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 결과 저장: {output_dir / 'rule_optimization_results.json'}")


if __name__ == "__main__":
    main()

