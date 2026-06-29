#!/usr/bin/env python3
"""
모델 평가 스크립트

Baseline 모델과 AI 모델의 성능을 비교 평가

사용법:
    python scripts/evaluate_model.py
"""
import json
import sys
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.ai_weight_learner import RuleWeightLearner
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix,
    classification_report
)


class BaselineModels:
    """Baseline 모델들"""
    
    @staticmethod
    def simple_sum(rule_results: List[Dict[str, Any]]) -> float:
        """Baseline 1: 단순 합산 (가장 기본)"""
        return min(100.0, sum(r.get("score", 0) for r in rule_results))
    
    @staticmethod
    def rule_based_weights(rule_results: List[Dict[str, Any]]) -> float:
        """Baseline 2: 규칙 기반 가중치 (현재 사용 중)"""
        learner = RuleWeightLearner(use_ai=False)
        return learner.calculate_weighted_score(rule_results)
    
    @staticmethod
    def majority_class(y_true: List[str]) -> str:
        """Baseline 3: 다수 클래스 분류기"""
        from collections import Counter
        return Counter(y_true).most_common(1)[0][0]
    
    @staticmethod
    def random_classifier(y_true: List[str], random_state: int = 42) -> List[str]:
        """Baseline 4: 랜덤 분류기"""
        np.random.seed(random_state)
        unique_labels = list(set(y_true))
        return [np.random.choice(unique_labels) for _ in y_true]


def score_to_label(score: float, threshold: float = 50.0) -> str:
    """점수를 라벨로 변환"""
    if score >= threshold:
        return "fraud"
    else:
        return "normal"


def evaluate_model(
    test_data: List[Dict[str, Any]],
    model_name: str,
    predict_fn
) -> Dict[str, float]:
    """
    모델 평가
    
    Args:
        test_data: 테스트 데이터
        model_name: 모델 이름
        predict_fn: 예측 함수 (rule_results -> score)
    
    Returns:
        평가 메트릭 딕셔너리
    """
    y_true = []
    y_pred = []
    y_pred_scores = []
    
    for item in test_data:
        rule_results = item.get("rule_results", [])
        actual_label = item.get("ground_truth_label", "normal")
        actual_score = item.get("actual_risk_score", 0.0)
        
        # 예측
        try:
            predicted_score = predict_fn(rule_results)
            predicted_label = score_to_label(predicted_score)
        except Exception as e:
            print(f"⚠️  예측 에러 ({model_name}): {e}")
            predicted_score = 0.0
            predicted_label = "normal"
        
        y_true.append(actual_label)
        y_pred.append(predicted_label)
        y_pred_scores.append(predicted_score)
    
    # 라벨을 숫자로 변환 (fraud=1, normal=0)
    y_true_binary = [1 if label == "fraud" else 0 for label in y_true]
    y_pred_binary = [1 if label == "fraud" else 0 for label in y_pred]
    
    # 점수를 확률로 변환 (0~100 -> 0~1)
    y_pred_proba = [score / 100.0 for score in y_pred_scores]
    
    # 메트릭 계산
    metrics = {
        "model_name": model_name,
        "accuracy": accuracy_score(y_true_binary, y_pred_binary),
        "precision": precision_score(y_true_binary, y_pred_binary, zero_division=0),
        "recall": recall_score(y_true_binary, y_pred_binary, zero_division=0),
        "f1_score": f1_score(y_true_binary, y_pred_binary, zero_division=0),
    }
    
    # AUC 계산 (점수가 필요한 경우)
    try:
        if len(set(y_pred_proba)) > 1:  # 모든 값이 같지 않은 경우
            metrics["roc_auc"] = roc_auc_score(y_true_binary, y_pred_proba)
            metrics["average_precision"] = average_precision_score(y_true_binary, y_pred_proba)
        else:
            metrics["roc_auc"] = 0.5  # 랜덤 수준
            metrics["average_precision"] = 0.0
    except Exception as e:
        metrics["roc_auc"] = 0.5
        metrics["average_precision"] = 0.0
    
    # Confusion Matrix
    cm = confusion_matrix(y_true_binary, y_pred_binary)
    metrics["confusion_matrix"] = {
        "true_negative": int(cm[0][0]),
        "false_positive": int(cm[0][1]),
        "false_negative": int(cm[1][0]),
        "true_positive": int(cm[1][1])
    }
    
    return metrics


def main():
    """메인 함수"""
    # 테스트 데이터 로드
    test_path = project_root / "data" / "dataset" / "test.json"
    if not test_path.exists():
        print(f"❌ 테스트 데이터가 없습니다: {test_path}")
        print("   먼저 데이터셋을 분할하세요: python scripts/split_dataset.py")
        return
    
    print("=" * 60)
    print("모델 평가 시작")
    print("=" * 60)
    
    print(f"\n📂 테스트 데이터 로드: {test_path.name}")
    try:
        with open(test_path, 'r') as f:
            test_data = json.load(f)
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return
    
    print(f"📊 테스트 샘플: {len(test_data)}개")
    
    # 라벨 분포 확인
    labels = [item.get("ground_truth_label", "unknown") for item in test_data]
    fraud_count = labels.count("fraud")
    normal_count = labels.count("normal")
    print(f"   Fraud: {fraud_count}개 ({fraud_count/len(test_data)*100:.1f}%)")
    print(f"   Normal: {normal_count}개 ({normal_count/len(test_data)*100:.1f}%)")
    
    # Baseline 모델들 평가
    print("\n" + "=" * 60)
    print("Baseline 모델 평가")
    print("=" * 60)
    
    baseline_results = []
    
    # Baseline 1: 단순 합산
    print("\n1️⃣  Baseline: 단순 합산 (Simple Sum)")
    result1 = evaluate_model(test_data, "Simple Sum", BaselineModels.simple_sum)
    baseline_results.append(result1)
    print(f"   Accuracy: {result1['accuracy']:.4f}")
    print(f"   Precision: {result1['precision']:.4f}")
    print(f"   Recall: {result1['recall']:.4f}")
    print(f"   F1-Score: {result1['f1_score']:.4f}")
    print(f"   ROC-AUC: {result1['roc_auc']:.4f}")
    print(f"   Average Precision: {result1['average_precision']:.4f}")
    
    # Baseline 2: 규칙 기반 가중치
    print("\n2️⃣  Baseline: 규칙 기반 가중치 (Rule-based Weights)")
    result2 = evaluate_model(test_data, "Rule-based", BaselineModels.rule_based_weights)
    baseline_results.append(result2)
    print(f"   Accuracy: {result2['accuracy']:.4f}")
    print(f"   Precision: {result2['precision']:.4f}")
    print(f"   Recall: {result2['recall']:.4f}")
    print(f"   F1-Score: {result2['f1_score']:.4f}")
    print(f"   ROC-AUC: {result2['roc_auc']:.4f}")
    print(f"   Average Precision: {result2['average_precision']:.4f}")
    
    # Baseline 3: 다수 클래스 분류기
    print("\n3️⃣  Baseline: 다수 클래스 분류기 (Majority Class)")
    y_true_labels = [item.get("ground_truth_label", "normal") for item in test_data]
    majority_label = BaselineModels.majority_class(y_true_labels)
    y_pred_majority = [majority_label] * len(test_data)
    
    y_true_binary = [1 if label == "fraud" else 0 for label in y_true_labels]
    y_pred_binary = [1 if label == "fraud" else 0 for label in y_pred_majority]
    
    result3 = {
        "model_name": "Majority Class",
        "accuracy": accuracy_score(y_true_binary, y_pred_binary),
        "precision": precision_score(y_true_binary, y_pred_binary, zero_division=0),
        "recall": recall_score(y_true_binary, y_pred_binary, zero_division=0),
        "f1_score": f1_score(y_true_binary, y_pred_binary, zero_division=0),
        "roc_auc": 0.5,  # 다수 클래스는 AUC 의미 없음
        "average_precision": 0.0,
    }
    baseline_results.append(result3)
    print(f"   Accuracy: {result3['accuracy']:.4f}")
    print(f"   Precision: {result3['precision']:.4f}")
    print(f"   Recall: {result3['recall']:.4f}")
    print(f"   F1-Score: {result3['f1_score']:.4f}")
    print(f"   (Majority class: {majority_label})")
    
    # Baseline 4: 랜덤 분류기
    print("\n4️⃣  Baseline: 랜덤 분류기 (Random)")
    y_pred_random = BaselineModels.random_classifier(y_true_labels)
    y_pred_binary_random = [1 if label == "fraud" else 0 for label in y_pred_random]
    
    result4 = {
        "model_name": "Random",
        "accuracy": accuracy_score(y_true_binary, y_pred_binary_random),
        "precision": precision_score(y_true_binary, y_pred_binary_random, zero_division=0),
        "recall": recall_score(y_true_binary, y_pred_binary_random, zero_division=0),
        "f1_score": f1_score(y_true_binary, y_pred_binary_random, zero_division=0),
        "roc_auc": 0.5,  # 랜덤은 AUC 0.5
        "average_precision": fraud_count / len(test_data),  # 랜덤 예상값
    }
    baseline_results.append(result4)
    print(f"   Accuracy: {result4['accuracy']:.4f}")
    print(f"   Precision: {result4['precision']:.4f}")
    print(f"   Recall: {result4['recall']:.4f}")
    print(f"   F1-Score: {result4['f1_score']:.4f}")
    
    # AI 모델 평가
    print("\n" + "=" * 60)
    print("AI 모델 평가")
    print("=" * 60)
    
    model_path = project_root / "models" / "rule_weights.pkl"
    if not model_path.exists():
        print(f"\n⚠️  AI 모델 파일이 없습니다: {model_path}")
        print("   먼저 모델을 학습하세요: python scripts/train_ai_model.py")
    else:
        print(f"\n📦 AI 모델 로드: {model_path.name}")
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            use_ai = model_data.get("use_ai", False) or model_data.get("model") is not None
            
            if use_ai and model_data.get("model"):
                learner = RuleWeightLearner(use_ai=True)
                learner.model = model_data.get("model")
                learner.scaler = model_data.get("scaler")
                learner.rule_features = model_data.get("rule_features", {})
                
                def ai_predict(rule_results):
                    return learner.calculate_weighted_score(rule_results)
                
                print("\n5️⃣  AI 모델: GradientBoostingClassifier")
                result5 = evaluate_model(test_data, "AI Model", ai_predict)
                print(f"   Accuracy: {result5['accuracy']:.4f}")
                print(f"   Precision: {result5['precision']:.4f}")
                print(f"   Recall: {result5['recall']:.4f}")
                print(f"   F1-Score: {result5['f1_score']:.4f}")
                print(f"   ROC-AUC: {result5['roc_auc']:.4f}")
                print(f"   Average Precision: {result5['average_precision']:.4f}")
            else:
                print("\n⚠️  저장된 모델이 규칙 기반 가중치입니다.")
                print("   AI 모델을 학습하려면: python scripts/train_ai_model.py")
        except Exception as e:
            print(f"\n❌ 모델 로드 실패: {e}")
            import traceback
            traceback.print_exc()
    
    # 결과 비교 테이블
    print("\n" + "=" * 60)
    print("📊 결과 비교")
    print("=" * 60)
    
    print(f"\n{'모델':<25} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
    print("-" * 75)
    
    for result in baseline_results:
        print(f"{result['model_name']:<25} "
              f"{result['accuracy']:<10.4f} "
              f"{result['precision']:<10.4f} "
              f"{result['recall']:<10.4f} "
              f"{result['f1_score']:<10.4f} "
              f"{result['roc_auc']:<10.4f}")
    
    # 결과 저장
    output_path = project_root / "data" / "dataset" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    all_results = {
        "test_samples": len(test_data),
        "label_distribution": {
            "fraud": fraud_count,
            "normal": normal_count
        },
        "baseline_results": baseline_results
    }
    
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 평가 결과 저장: {output_path}")
    print("\n✅ 평가 완료!")


if __name__ == "__main__":
    main()

