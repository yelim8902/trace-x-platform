#!/usr/bin/env python3
"""
모든 스코어러와 Baseline 모델 비교 평가
"""
import sys
import json
from pathlib import Path
from typing import Dict, List, Any
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
from collections import Counter
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage1_scorer import Stage1Scorer
from core.scoring.stage2_scorer import Stage2Scorer
from core.scoring.improved_rule_scorer import ImprovedRuleScorer
from core.rules.evaluator import RuleEvaluator


def evaluate_model(
    test_data: List[Dict[str, Any]],
    model_name: str,
    predict_fn,
    threshold: float = 50.0
) -> Dict[str, Any]:
    """
    모델 평가
    
    Args:
        test_data: 테스트 데이터
        model_name: 모델 이름
        predict_fn: 예측 함수 (sample -> score)
        threshold: 임계값
    """
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    for sample in test_data:
        label = sample.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        
        try:
            score = predict_fn(sample)
            y_pred_scores.append(score)
            y_pred.append(1 if score >= threshold else 0)
        except Exception as e:
            y_pred_scores.append(0.0)
            y_pred.append(0)
    
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
    
    return {
        "model_name": model_name,
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
    test_path = dataset_dir / "test.json"
    train_path = dataset_dir / "train.json"
    
    if not test_path.exists():
        print("❌ 테스트 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    print("📂 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    with open(train_path, 'r') as f:
        train_data = json.load(f)
    
    print(f"   Test: {len(test_data)}개")
    print(f"   Train: {len(train_data)}개")
    
    results = []
    
    # 1. Baseline: Simple Sum
    print("\n" + "=" * 80)
    print("Baseline: Simple Sum")
    print("=" * 80)
    
    def simple_sum_predict(sample):
        rule_evaluator = RuleEvaluator()
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
        rule_results = rule_evaluator.evaluate_single_transaction(tx_data)
        return min(100.0, sum(r.get("score", 0) for r in rule_results))
    
    results.append(evaluate_model(test_data, "Simple Sum", simple_sum_predict, threshold=50.0))
    
    # 2. Baseline: Rule-based Weights
    print("\n" + "=" * 80)
    print("Baseline: Rule-based Weights")
    print("=" * 80)
    
    def rule_based_weights_predict(sample):
        rule_evaluator = RuleEvaluator()
        scorer = ImprovedRuleScorer()
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
        rule_results = rule_evaluator.evaluate_single_transaction(tx_data)
        tx_context = sample.get("tx_context", {})
        if "ml_features" not in tx_context:
            tx_context["ml_features"] = sample.get("ml_features", {})
        return scorer.calculate_score(rule_results, tx_context)
    
    results.append(evaluate_model(test_data, "Rule-based Weights", rule_based_weights_predict, threshold=50.0))
    
    # 3. Stage 1 Scorer
    print("\n" + "=" * 80)
    print("Stage 1 Scorer")
    print("=" * 80)
    
    stage1_scorer = Stage1Scorer(rule_weight=0.9, graph_weight=0.1)
    
    def stage1_predict(sample):
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
        result = stage1_scorer.calculate_risk_score(tx_data, ml_features, tx_context)
        return result["risk_score"]
    
    results.append(evaluate_model(test_data, "Stage 1 Scorer", stage1_predict, threshold=39.0))
    
    # 4. Stage 2 Scorer (여러 모델)
    print("\n" + "=" * 80)
    print("Stage 2 Scorer 학습 및 평가")
    print("=" * 80)
    
    model_types = ["logistic", "random_forest", "gradient_boosting"]
    
    for model_type in model_types:
        print(f"\n{model_type.upper()} 모델:")
        model_path = dataset_dir / f"stage2_scorer_{model_type}.pkl"
        
        if not model_path.exists():
            print(f"  ⚠️  모델 파일이 없습니다. 학습 중...")
            scorer = Stage2Scorer(model_type=model_type, use_ppr_features=True)
            scorer.train(train_data)
            scorer.save_model(model_path)
        else:
            scorer = Stage2Scorer(model_type=model_type, use_ppr_features=True)
            scorer.load_model(model_path)
        
        def stage2_predict(sample):
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
            result = scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            return result["risk_score"]
        
        result = evaluate_model(test_data, f"Stage 2 ({model_type})", stage2_predict, threshold=50.0)
        results.append(result)
    
    # 5. Baseline: Majority Class
    print("\n" + "=" * 80)
    print("Baseline: Majority Class")
    print("=" * 80)
    
    labels = [s.get("ground_truth_label", "normal") for s in test_data]
    majority_label = Counter(labels).most_common(1)[0][0]
    
    def majority_predict(sample):
        return 100.0 if majority_label == "fraud" else 0.0
    
    results.append(evaluate_model(test_data, "Majority Class", majority_predict, threshold=50.0))
    
    # 6. Baseline: Random Classifier
    print("\n" + "=" * 80)
    print("Baseline: Random Classifier")
    print("=" * 80)
    
    np.random.seed(42)
    
    def random_predict(sample):
        return np.random.uniform(0, 100)
    
    results.append(evaluate_model(test_data, "Random Classifier", random_predict, threshold=50.0))
    
    # 결과 출력
    print("\n" + "=" * 80)
    print("✅ 전체 모델 비교 결과")
    print("=" * 80)
    
    # F1-Score 기준 정렬
    results_sorted = sorted(results, key=lambda x: x["f1_score"], reverse=True)
    
    print(f"\n{'순위':<4} {'모델명':<30} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
    print("-" * 100)
    
    for i, result in enumerate(results_sorted, 1):
        print(f"{i:<4} {result['model_name']:<30} "
              f"{result['accuracy']*100:>6.2f}%   "
              f"{result['precision']:>8.4f}   "
              f"{result['recall']:>8.4f}   "
              f"{result['f1_score']:>8.4f}   "
              f"{result['roc_auc']:>8.4f}")
    
    # 결과 저장
    output_path = dataset_dir / "all_scorers_comparison.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 결과 저장: {output_path}")


if __name__ == "__main__":
    main()

