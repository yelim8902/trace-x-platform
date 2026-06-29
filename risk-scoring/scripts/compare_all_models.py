#!/usr/bin/env python3
"""
전체 모델 비교 평가 스크립트

Rule-based, MPOCryptoML, Hybrid 모델과 논문 Baseline 모델들을 모두 비교

사용법:
    python scripts/compare_all_models.py
"""
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Any, Tuple
import numpy as np
from collections import Counter

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, AdaBoostClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.svm import SVC
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import SGDClassifier
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, confusion_matrix
)
from core.scoring.ai_weight_learner import RuleWeightLearner


def extract_hybrid_features(item: Dict[str, Any]) -> np.ndarray:
    """Hybrid 모델용 피처 추출"""
    rule_score = item.get("rule_score", 0.0)
    rule_results = item.get("rule_results", [])
    
    rule_axis_scores = {"A": 0.0, "B": 0.0, "C": 0.0, "D": 0.0}
    rule_severity_scores = {"LOW": 0.0, "MEDIUM": 0.0, "HIGH": 0.0, "CRITICAL": 0.0}
    rule_count = len(rule_results)
    
    for rule in rule_results:
        axis = rule.get("axis", "B")
        severity = rule.get("severity", "MEDIUM")
        score = rule.get("score", 0.0)
        
        if axis in rule_axis_scores:
            rule_axis_scores[axis] += score
        if severity in rule_severity_scores:
            rule_severity_scores[severity] += score
    
    ml_features = item.get("ml_features", {})
    
    ml_numeric_features = [
        ml_features.get("ppr_score", 0.0),
        ml_features.get("sdn_ppr", 0.0),
        ml_features.get("mixer_ppr", 0.0),
        ml_features.get("pattern_score", 0.0),
        ml_features.get("n_theta", 0.0),
        ml_features.get("n_omega", 0.0),
        ml_features.get("fan_in_count", 0),
        ml_features.get("fan_out_count", 0),
        ml_features.get("gather_scatter", 0.0),
        ml_features.get("graph_nodes", 0),
        ml_features.get("graph_edges", 0),
    ]
    
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    pattern_features = [1.0 if pattern_type in detected_patterns else 0.0 
                        for pattern_type in pattern_types]
    
    features = [
        rule_score, rule_count,
        rule_axis_scores["A"], rule_axis_scores["B"], rule_axis_scores["C"], rule_axis_scores["D"],
        rule_severity_scores["LOW"], rule_severity_scores["MEDIUM"], 
        rule_severity_scores["HIGH"], rule_severity_scores["CRITICAL"],
        *ml_numeric_features,
        *pattern_features,
    ]
    
    return np.array(features, dtype=np.float32)


def extract_mpocryptml_features(item: Dict[str, Any]) -> np.ndarray:
    """MPOCryptoML 모델용 피처 추출"""
    ml_features = item.get("ml_features", {})
    
    features = [
        ml_features.get("ppr_score", 0.0),
        ml_features.get("sdn_ppr", 0.0),
        ml_features.get("mixer_ppr", 0.0),
        ml_features.get("pattern_score", 0.0),
        ml_features.get("n_theta", 0.0),
        ml_features.get("n_omega", 0.0),
        ml_features.get("fan_in_count", 0),
        ml_features.get("fan_out_count", 0),
        ml_features.get("gather_scatter", 0.0),
        ml_features.get("graph_nodes", 0),
        ml_features.get("graph_edges", 0),
    ]
    
    detected_patterns = ml_features.get("detected_patterns", [])
    pattern_types = ["fan_in", "fan_out", "gather_scatter", "stack", "bipartite"]
    for pattern_type in pattern_types:
        features.append(1.0 if pattern_type in detected_patterns else 0.0)
    
    rule_score = item.get("rule_score", 0.0)
    features.append(rule_score)
    
    return np.array(features, dtype=np.float32)


def calculate_precision_at_k(y_true: List[int], y_pred_proba: List[float], k: int = None) -> float:
    """Precision@K 계산 (논문 지표)"""
    if k is None:
        # K를 fraud 샘플 수로 설정
        k = sum(y_true)
        if k == 0:
            return 0.0
    
    # 확률 기준으로 정렬하여 상위 K개 선택
    indices = np.argsort(y_pred_proba)[::-1][:k]
    top_k_pred = [y_true[i] for i in indices]
    
    if len(top_k_pred) == 0:
        return 0.0
    
    return sum(top_k_pred) / len(top_k_pred)


def calculate_recall_at_k(y_true: List[int], y_pred_proba: List[float], k: int = None) -> float:
    """Recall@K 계산 (논문 지표)"""
    total_positive = sum(y_true)
    if total_positive == 0:
        return 0.0
    
    if k is None:
        k = total_positive
    
    # 확률 기준으로 정렬하여 상위 K개 선택
    indices = np.argsort(y_pred_proba)[::-1][:k]
    top_k_pred = [y_true[i] for i in indices]
    
    true_positives = sum(top_k_pred)
    return true_positives / total_positive if total_positive > 0 else 0.0


def evaluate_model_with_predictions(
    y_true: List[int],
    y_pred: List[int],
    y_pred_proba: List[float],
    model_name: str
) -> Dict[str, Any]:
    """예측 결과로부터 평가 지표 계산 (논문 지표 포함)"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    # Precision@K, Recall@K 계산
    k = sum(y_true)  # fraud 샘플 수
    precision_at_k = calculate_precision_at_k(y_true, y_pred_proba, k)
    recall_at_k = calculate_recall_at_k(y_true, y_pred_proba, k)
    
    try:
        if len(set(y_pred_proba)) > 1:
            roc_auc = roc_auc_score(y_true, y_pred_proba)
            avg_precision = average_precision_score(y_true, y_pred_proba)
        else:
            roc_auc = 0.5
            avg_precision = 0.0
    except:
        roc_auc = 0.5
        avg_precision = 0.0
    
    cm = confusion_matrix(y_true, y_pred)
    
    return {
        "model_name": model_name,
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "precision_at_k": float(precision_at_k),
        "recall_at_k": float(recall_at_k),
        "roc_auc": float(roc_auc),
        "average_precision": float(avg_precision),
        "confusion_matrix": {
            "true_negative": int(cm[0][0]),
            "false_positive": int(cm[0][1]),
            "false_negative": int(cm[1][0]),
            "true_positive": int(cm[1][1])
        }
    }


def evaluate_rule_based_variants(test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rule-based 변형 모델들 평가"""
    results = []
    
    # 1. Rule Score (기본)
    y_true = []
    y_pred_scores = []
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
        rule_score = item.get("rule_score", 0.0)
        y_pred_scores.append(rule_score / 100.0)
    y_pred = [1 if score >= 0.5 else 0 for score in y_pred_scores]
    results.append(evaluate_model_with_predictions(y_true, y_pred, y_pred_scores, "Rule-based (Score)"))
    
    # 2. Simple Sum
    y_pred_scores = []
    for item in test_data:
        rule_results = item.get("rule_results", [])
        score = min(100.0, sum(r.get("score", 0) for r in rule_results)) / 100.0
        y_pred_scores.append(score)
    y_pred = [1 if score >= 0.5 else 0 for score in y_pred_scores]
    results.append(evaluate_model_with_predictions(y_true, y_pred, y_pred_scores, "Rule-based (Simple Sum)"))
    
    # 3. Rule-based Weights
    learner = RuleWeightLearner(use_ai=False)
    y_pred_scores = []
    for item in test_data:
        rule_results = item.get("rule_results", [])
        score = learner.calculate_weighted_score(rule_results) / 100.0
        y_pred_scores.append(score)
    y_pred = [1 if score >= 0.5 else 0 for score in y_pred_scores]
    results.append(evaluate_model_with_predictions(y_true, y_pred, y_pred_scores, "Rule-based (Weighted)"))
    
    return results


def evaluate_simple_baselines(test_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """간단한 Baseline 모델들 평가"""
    results = []
    
    labels = [item.get("ground_truth_label", "normal") for item in test_data]
    y_true = [1 if label == "fraud" else 0 for label in labels]
    
    # 1. Majority Class
    majority_label = Counter(labels).most_common(1)[0][0]
    y_pred = [1 if majority_label == "fraud" else 0] * len(test_data)
    y_pred_proba = [0.5] * len(test_data)  # 더미 확률
    results.append(evaluate_model_with_predictions(y_true, y_pred, y_pred_proba, "Majority Class"))
    
    # 2. Random Classifier
    np.random.seed(42)
    y_pred = np.random.choice([0, 1], size=len(test_data))
    y_pred_proba = np.random.random(size=len(test_data))
    results.append(evaluate_model_with_predictions(y_true, y_pred.tolist(), y_pred_proba.tolist(), "Random Classifier"))
    
    # 3. ML Features Only (가중 평균)
    y_pred_scores = []
    for item in test_data:
        ml_features = item.get("ml_features", {})
        ppr = ml_features.get("ppr_score", 0.0) * 100
        pattern = ml_features.get("pattern_score", 0.0)
        n_theta = ml_features.get("n_theta", 0.0) * 100
        n_omega = ml_features.get("n_omega", 0.0) * 100
        score = (ppr * 0.3 + pattern * 0.4 + n_theta * 0.15 + n_omega * 0.15) / 100.0
        y_pred_scores.append(score)
    y_pred = [1 if score >= 0.5 else 0 for score in y_pred_scores]
    results.append(evaluate_model_with_predictions(y_true, y_pred, y_pred_scores, "ML Features Only (Weighted)"))
    
    return results


def evaluate_ml_model(test_data: List[Dict[str, Any]], model_path: Path, 
                      extract_fn, model_name: str) -> Dict[str, Any]:
    """ML 모델 평가 (공통 함수)"""
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    
    model = model_data["model"]
    scaler = model_data["scaler"]
    
    X_test = []
    for item in test_data:
        features = extract_fn(item)
        X_test.append(features)
    
    X_test = np.array(X_test)
    X_test_scaled = scaler.transform(X_test)
    
    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred = model.predict(X_test_scaled)
    
    y_true = []
    for item in test_data:
        label = item.get("ground_truth_label", "normal")
        y_true.append(1 if label == "fraud" else 0)
    
    return evaluate_model_with_predictions(y_true, y_pred, y_pred_proba, model_name)


def train_ml_baseline_models(test_data: List[Dict[str, Any]], train_data: List[Dict[str, Any]]):
    """ML Baseline 모델들 학습 및 평가"""
    from sklearn.preprocessing import StandardScaler
    
    # 피처 추출
    X_train = []
    y_train = []
    X_test = []
    y_test = []
    
    for item in train_data:
        features = extract_hybrid_features(item)
        X_train.append(features)
        label = item.get("ground_truth_label", "normal")
        y_train.append(1 if label == "fraud" else 0)
    
    for item in test_data:
        features = extract_hybrid_features(item)
        X_test.append(features)
        label = item.get("ground_truth_label", "normal")
        y_test.append(1 if label == "fraud" else 0)
    
    X_train = np.array(X_train)
    X_test = np.array(X_test)
    y_train = np.array(y_train)
    y_test = np.array(y_test)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    results = []
    
    # 논문 Baseline 모델들 (Ensemble)
    ml_models = [
        ("XGBoost", lambda: XGBClassifier(n_estimators=100, max_depth=5, random_state=42, eval_metric='logloss'), XGBOOST_AVAILABLE),
        ("Gradient Boosting", lambda: GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42), True),
        ("Random Forest", lambda: RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, class_weight='balanced'), True),
        ("AdaBoost", lambda: AdaBoostClassifier(n_estimators=100, random_state=42), True),
    ]
    
    # 논문 Baseline 모델들 (추가 - 유사 구현)
    # DeepFD, OCGTL, ComGA, Flowscope, GUDI, MACE는 특정 그래프 신경망 방법론이므로
    # 유사한 접근 방식으로 구현 (간단한 버전)
    
    # DeepFD 유사: Deep Learning 기반 (간단한 MLP)
    try:
        from sklearn.neural_network import MLPClassifier
        ml_models.append(("DeepFD (MLP)", lambda: MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42), True))
    except:
        pass
    
    # OCGTL 유사: Graph-based (Random Forest로 유사 구현)
    ml_models.append(("OCGTL (RF)", lambda: RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42, class_weight='balanced'), True))
    
    # ComGA 유사: Community Detection 기반 (Gradient Boosting으로 유사)
    ml_models.append(("ComGA (GB)", lambda: GradientBoostingClassifier(n_estimators=200, max_depth=10, random_state=42), True))
    
    # Flowscope 유사: Flow-based (SVM으로 유사)
    ml_models.append(("Flowscope (SVM)", lambda: SVC(kernel='rbf', probability=True, random_state=42, class_weight='balanced', C=10.0), True))
    
    # GUDI 유사: Graph Unsupervised (XGBoost로 유사)
    if XGBOOST_AVAILABLE:
        ml_models.append(("GUDI (XGB)", lambda: XGBClassifier(n_estimators=200, max_depth=10, random_state=42, eval_metric='logloss'), True))
    
    # MACE 유사: Multi-Attribute (Ensemble로 유사)
    try:
        # sklearn 1.2+에서는 estimator 파라미터 사용
        ml_models.append(("MACE (Ensemble)", lambda: AdaBoostClassifier(
            estimator=RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42),
            n_estimators=50, random_state=42
        ), True))
    except:
        # 구버전 호환
        try:
            ml_models.append(("MACE (Ensemble)", lambda: AdaBoostClassifier(
                base_estimator=RandomForestClassifier(n_estimators=50, max_depth=5, random_state=42),
                n_estimators=50, random_state=42
            ), True))
        except:
            # 최후의 수단: 단순 AdaBoost
            ml_models.append(("MACE (Ensemble)", lambda: AdaBoostClassifier(
                n_estimators=100, random_state=42
            ), True))
    
    for name, model_fn, available in ml_models:
        if not available:
            print(f"   ⚠️  {name}가 사용 불가능합니다. 건너뜁니다.")
            continue
        try:
            print(f"   - {name} 학습 중...")
            model = model_fn()
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            results.append(evaluate_model_with_predictions(y_test, y_pred, y_pred_proba, name))
        except Exception as e:
            print(f"   ⚠️  {name} 학습 실패: {e}")
    
    # 단일 모델들
    single_models = [
        ("Decision Tree", lambda: DecisionTreeClassifier(max_depth=5, random_state=42, class_weight='balanced')),
        ("SVM (RBF)", lambda: SVC(kernel='rbf', probability=True, random_state=42, class_weight='balanced')),
        ("SVM (Linear)", lambda: SVC(kernel='linear', probability=True, random_state=42, class_weight='balanced')),
        ("Naive Bayes", lambda: GaussianNB()),
        ("K-Nearest Neighbors", lambda: KNeighborsClassifier(n_neighbors=5)),
        ("SGD Classifier", lambda: SGDClassifier(loss='log_loss', random_state=42, class_weight='balanced')),
    ]
    
    for name, model_fn in single_models:
        try:
            print(f"   - {name} 학습 중...")
            model = model_fn()
            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)
            try:
                y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
            except:
                # SGD는 decision_function 사용
                if hasattr(model, 'decision_function'):
                    decision_scores = model.decision_function(X_test_scaled)
                    y_pred_proba = 1 / (1 + np.exp(-decision_scores))  # sigmoid 변환
                else:
                    y_pred_proba = y_pred.astype(float)
            results.append(evaluate_model_with_predictions(y_test, y_pred, y_pred_proba, name))
        except Exception as e:
            print(f"   ⚠️  {name} 학습 실패: {e}")
    
    return results


def main():
    """메인 함수"""
    print("=" * 80)
    print("전체 모델 비교 평가 (Rule-based, MPOCryptoML, Hybrid, Baseline)")
    print("=" * 80)
    
    dataset_dir = project_root / "data" / "dataset"
    test_path = dataset_dir / "test.json"
    train_path = dataset_dir / "train.json"
    
    models_dir = project_root / "models"
    hybrid_model_path = models_dir / "hybrid_model_logistic.pkl"
    mpocryptml_model_path = models_dir / "mpocryptml_model.pkl"
    
    if not test_path.exists():
        print(f"❌ 테스트 데이터를 찾을 수 없습니다: {test_path}")
        return
    
    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    with open(test_path, 'r') as f:
        test_data = json.load(f)
    
    with open(train_path, 'r') as f:
        train_data = json.load(f)
    
    print(f"   테스트 데이터: {len(test_data)}개")
    print(f"   학습 데이터: {len(train_data)}개")
    
    from collections import Counter
    labels = [item.get("ground_truth_label", "normal") for item in test_data]
    label_counts = Counter(labels)
    print(f"   테스트 라벨 분포: {dict(label_counts)}")
    
    # 모델 평가
    print("\n" + "=" * 80)
    print("📊 모델 평가 중...")
    print("=" * 80)
    
    all_results = []
    
    # 1. Rule-based 변형들
    print("\n1️⃣  Rule-based 변형 모델들 평가 중...")
    rule_results = evaluate_rule_based_variants(test_data)
    all_results.extend(rule_results)
    
    # 2. MPOCryptoML
    if mpocryptml_model_path.exists():
        print("\n2️⃣  MPOCryptoML 모델 평가 중...")
        mpocryptml_results = evaluate_ml_model(
            test_data, mpocryptml_model_path, 
            extract_mpocryptml_features, 
            "MPOCryptoML (Logistic Regression)"
        )
        all_results.append(mpocryptml_results)
    else:
        print("\n⚠️  MPOCryptoML 모델을 찾을 수 없습니다.")
    
    # 3. Hybrid
    if hybrid_model_path.exists():
        print("\n3️⃣  Hybrid 모델 평가 중...")
        hybrid_results = evaluate_ml_model(
            test_data, hybrid_model_path,
            extract_hybrid_features,
            "Hybrid (Logistic Regression)"
        )
        all_results.append(hybrid_results)
    else:
        print("\n⚠️  Hybrid 모델을 찾을 수 없습니다.")
    
    # 4. 간단한 Baseline 모델들
    print("\n4️⃣  간단한 Baseline 모델들 평가 중...")
    simple_baselines = evaluate_simple_baselines(test_data)
    all_results.extend(simple_baselines)
    
    # 5. ML Baseline 모델들
    print("\n5️⃣  ML Baseline 모델들 학습 및 평가 중...")
    ml_baselines = train_ml_baseline_models(test_data, train_data)
    all_results.extend(ml_baselines)
    
    # 결과 출력
    print("\n" + "=" * 100)
    print("📈 전체 모델 비교 결과 (논문 형식)")
    print("=" * 100)
    
    # F1-Score 기준 정렬
    all_results.sort(key=lambda x: x['f1_score'], reverse=True)
    
    # 논문 형식 표 출력
    print(f"\n{'순위':<5} {'모델':<30} {'Pre@K':<10} {'Recall@K':<10} {'F1-Score':<10} {'ACC(%)':<10} {'AUC(%)':<10}")
    print("-" * 100)
    
    for idx, results in enumerate(all_results, 1):
        name = results["model_name"]
        prec_at_k = results.get("precision_at_k", 0.0)
        recall_at_k = results.get("recall_at_k", 0.0)
        f1 = results["f1_score"]
        acc = results["accuracy"]
        auc = results["roc_auc"]
        
        print(f"{idx:<5} {name:<30} {prec_at_k:<10.4f} {recall_at_k:<10.4f} {f1:<10.4f} {acc:<10.4f} {auc:<10.4f}")
    
    # 상세 표도 출력
    print(f"\n{'순위':<5} {'모델':<40} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1-Score':<10} {'ROC-AUC':<10}")
    print("-" * 95)
    
    for idx, results in enumerate(all_results, 1):
        name = results["model_name"]
        acc = results["accuracy"]
        prec = results["precision"]
        rec = results["recall"]
        f1 = results["f1_score"]
        auc = results["roc_auc"]
        
        print(f"{idx:<5} {name:<40} {acc:<10.4f} {prec:<10.4f} {rec:<10.4f} {f1:<10.4f} {auc:<10.4f}")
    
    # 상세 결과
    print("\n" + "=" * 80)
    print("📋 상세 결과 (F1-Score 순)")
    print("=" * 80)
    
    for idx, results in enumerate(all_results, 1):
        print(f"\n{idx}. {results['model_name']}:")
        print(f"   Precision@K:     {results.get('precision_at_k', 0.0):.4f} ({results.get('precision_at_k', 0.0)*100:.2f}%)")
        print(f"   Recall@K:        {results.get('recall_at_k', 0.0):.4f} ({results.get('recall_at_k', 0.0)*100:.2f}%)")
        print(f"   F1-Score:        {results['f1_score']:.4f} ({results['f1_score']*100:.2f}%)")
        print(f"   Accuracy:        {results['accuracy']:.4f} ({results['accuracy']*100:.2f}%)")
        print(f"   AUC(%):          {results['roc_auc']:.4f} ({results['roc_auc']*100:.2f}%)")
        print(f"   Precision:       {results['precision']:.4f}")
        print(f"   Recall:          {results['recall']:.4f}")
        print(f"   Average Precision: {results['average_precision']:.4f}")
        cm = results['confusion_matrix']
        print(f"   Confusion Matrix:")
        print(f"      TN: {cm['true_negative']}, FP: {cm['false_positive']}")
        print(f"      FN: {cm['false_negative']}, TP: {cm['true_positive']}")
    
    # 결과 저장
    output_path = dataset_dir / "all_models_comparison.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 비교 결과 저장: {output_path}")
    
    # 최고 성능 모델
    if all_results:
        best_model = all_results[0]
        print(f"\n🏆 최고 성능 모델 (F1-Score 기준): {best_model['model_name']}")
        print(f"   F1-Score: {best_model['f1_score']:.4f}")
        print(f"   Accuracy: {best_model['accuracy']:.4f}")
        print(f"   ROC-AUC:  {best_model['roc_auc']:.4f}")


if __name__ == "__main__":
    main()

