#!/usr/bin/env python3
"""
개선된 Rule-based 스코어러

룰 점수가 0이어도 룰 발동 자체를 점수로 활용
다양한 집계 방식과 가중치 조절 지원
"""
from typing import List, Dict, Any, Optional
import numpy as np


class ImprovedRuleScorer:
    """개선된 Rule-based 스코어러"""
    
    # 심각도별 기본 점수 (룰 점수가 0일 때 사용) - 성능 향상을 위해 증가
    SEVERITY_SCORES = {
        "CRITICAL": 25.0,  # 15 -> 25
        "HIGH": 20.0,      # 10 -> 20
        "MEDIUM": 10.0,    # 5 -> 10
        "LOW": 5.0         # 2 -> 5
    }
    
    # 축별 가중치 - 성능 향상을 위해 증가
    AXIS_WEIGHTS = {
        "A": 1.5,  # 금액 관련 (가장 중요) - 1.2 -> 1.5
        "B": 1.2,  # 행동 패턴 - 1.0 -> 1.2
        "C": 1.3,  # 연결성 - 1.1 -> 1.3
        "D": 1.0,  # 시간 패턴 - 0.9 -> 1.0
        "E": 1.4   # 노출 - 추가
    }
    
    def __init__(
        self,
        aggregation_method: str = "weighted_sum",
        use_rule_count_bonus: bool = True,
        use_severity_bonus: bool = True,
        use_axis_bonus: bool = True
    ):
        """
        Args:
            aggregation_method: 집계 방식
                - "simple_sum": 단순 합산
                - "weighted_sum": 가중 합산 (기본)
                - "max": 최대값
                - "mean": 평균
                - "sqrt_sum": 제곱근 합산 (중복 룰 페널티)
            use_rule_count_bonus: 룰 개수 보너스 사용 여부
            use_severity_bonus: 심각도 보너스 사용 여부
            use_axis_bonus: 축별 가중치 사용 여부
        """
        self.aggregation_method = aggregation_method
        self.use_rule_count_bonus = use_rule_count_bonus
        self.use_severity_bonus = use_severity_bonus
        self.use_axis_bonus = use_axis_bonus
    
    def calculate_score(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        개선된 Rule-based 점수 계산
        
        Args:
            rule_results: 발동된 룰 목록
            tx_context: 트랜잭션 컨텍스트 (선택적)
        
        Returns:
            최종 점수 (0~100)
        """
        if not rule_results:
            return 0.0
        
        # 1. 각 룰의 점수 계산 (룰 점수가 0이어도 발동 자체를 점수로)
        rule_scores = []
        for rule in rule_results:
            score = self._calculate_rule_score(rule)
            rule_scores.append(score)
        
        # 2. 집계 방식에 따라 최종 점수 계산
        base_score = self._aggregate_scores(rule_scores, rule_results)
        
        # 3. 보너스 점수 추가
        bonus_score = 0.0
        if self.use_rule_count_bonus:
            bonus_score += self._calculate_rule_count_bonus(rule_results)
        if self.use_severity_bonus:
            bonus_score += self._calculate_severity_bonus(rule_results)
        if self.use_axis_bonus:
            bonus_score += self._calculate_axis_bonus(rule_results)
        
        # 4. 룰 다양성 보너스 (같은 룰이 반복되면 페널티) - 완화
        # diversity_penalty = self._calculate_diversity_penalty(rule_results)
        # base_score += diversity_penalty
        # 주석 처리: 모든 샘플이 같은 룰만 반복되는 경우가 많아서 페널티가 과도함
        
        # 5. 거래 컨텍스트 기반 점수 (가능한 경우)
        if tx_context:
            context_score = self._calculate_context_score(tx_context, rule_results)
            base_score += context_score
        
        # 6. ML 피처 활용 (Rule-based만으로는 부족할 때)
        # ML 피처가 있으면 활용 (PPR, 패턴 점수 등)
        if tx_context and "ml_features" in tx_context:
            ml_score = self._calculate_ml_bonus(tx_context["ml_features"])
            base_score += ml_score
        
        # 7. 점수 역전 보정 (Normal이 더 높은 점수를 받는 문제 해결)
        # Normal이 더 많은 룰을 발동시키므로, 룰 개수와 패턴으로 보정
        rule_count = len(rule_results)
        rule_ids = [r.get("rule_id") for r in rule_results]
        
        # Normal이 많이 발동하는 룰 (B-501, C-003)이 있으면 점수 감소 (완화)
        if "B-501" in rule_ids and "C-003" in rule_ids:
            # 두 룰이 동시에 발동되면 Normal일 가능성 높음
            base_score -= 15.0  # 25 -> 15로 완화
        elif "B-501" in rule_ids or "C-003" in rule_ids:
            # 하나만 발동되면 약간 감소
            base_score -= 5.0   # 10 -> 5로 완화
        
        # 룰 개수 기반 보정 (완화)
        if rule_count <= 1:
            # 룰이 적게 발동되면 fraud일 가능성 높음
            base_score += 15.0  # 25 -> 15로 완화
        elif rule_count >= 3:
            # 룰이 많이 발동되면 normal일 가능성 높음
            base_score -= 10.0  # 20 -> 10으로 완화, 조건도 2 -> 3으로 완화
        
        # 8. 최종 점수 (0~100 범위로 제한)
        final_score = min(100.0, max(0.0, base_score + bonus_score))
        
        return final_score
    
    def _calculate_diversity_penalty(
        self,
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """룰 다양성 페널티 (같은 룰이 반복되면 점수 감소)"""
        if not rule_results:
            return 0.0
        
        unique_rules = len(set(r.get("rule_id", "") for r in rule_results))
        total_rules = len(rule_results)
        
        # 다양성 비율
        diversity_ratio = unique_rules / total_rules if total_rules > 0 else 0.0
        
        # 다양성이 낮으면 페널티 (같은 룰만 반복)
        if diversity_ratio < 0.3:  # 30% 미만 다양성
            return -10.0  # 페널티
        elif diversity_ratio < 0.5:
            return -5.0
        else:
            return 0.0
    
    def _calculate_context_score(
        self,
        tx_context: Dict[str, Any],
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """거래 컨텍스트 기반 점수"""
        score = 0.0
        
        # 거래 개수 기반 (더 세밀하게) - 성능 향상을 위해 증가
        num_transactions = tx_context.get("num_transactions", 0)
        if num_transactions > 100:
            score += 15.0  # 10 -> 15
        elif num_transactions > 80:
            score += 12.0  # 7 -> 12
        elif num_transactions > 50:
            score += 8.0   # 5 -> 8
        elif num_transactions > 30:
            score += 5.0   # 2 -> 5
        
        # 그래프 크기 기반 (더 세밀하게) - 성능 향상을 위해 증가
        graph_nodes = tx_context.get("graph_nodes", 0)
        if graph_nodes > 50:
            score += 12.0  # 8 -> 12
        elif graph_nodes > 30:
            score += 8.0   # 5 -> 8
        elif graph_nodes > 20:
            score += 5.0   # 3 -> 5
        elif graph_nodes > 10:
            score += 2.0   # 1 -> 2
        
        # 룰 개수 기반 (중요!) - 성능 향상을 위해 증가
        rule_count = len(rule_results)
        if rule_count > 20:
            score += 20.0  # 15 -> 20
        elif rule_count > 15:
            score += 15.0  # 10 -> 15
        elif rule_count > 10:
            score += 10.0  # 5 -> 10
        elif rule_count > 5:
            score += 5.0   # 2 -> 5
        
        return score
    
    def _calculate_ml_bonus(
        self,
        ml_features: Dict[str, Any]
    ) -> float:
        """ML 피처 기반 보너스 (Rule-based 보조)"""
        bonus = 0.0
        
        # PPR 점수가 높으면 보너스 (위험 주소와의 연결)
        ppr_score = ml_features.get("ppr_score", 0.0)
        if ppr_score > 0.5:
            bonus += 8.0
        elif ppr_score > 0.3:
            bonus += 4.0
        
        # 패턴 점수가 낮으면 보너스 (Fraud는 패턴 점수가 낮음)
        pattern_score = ml_features.get("pattern_score", 0.0)
        if pattern_score < 15:  # Fraud 평균 17.03
            bonus += 12.0
        elif pattern_score < 20:
            bonus += 6.0
        elif pattern_score > 30:  # Normal 평균 29.77 - 페널티
            bonus -= 5.0
        
        # n_theta가 높으면 보너스 (시간 비대칭 - Fraud 특징)
        n_theta = ml_features.get("n_theta", 0.0)
        if n_theta > 0.8:
            bonus += 6.0
        elif n_theta > 0.5:
            bonus += 3.0
        
        # n_omega가 높으면 보너스 (금액 불균형 - Fraud 특징)
        n_omega = ml_features.get("n_omega", 0.0)
        if n_omega > 0.7:
            bonus += 5.0
        elif n_omega > 0.4:
            bonus += 2.0
        
        return bonus
    
    def _calculate_rule_score(self, rule: Dict[str, Any]) -> float:
        """개별 룰의 점수 계산"""
        # 1. 룰의 score 필드 확인
        rule_score = rule.get("score", 0.0)
        if isinstance(rule_score, str):
            try:
                rule_score = float(rule_score)
            except (ValueError, TypeError):
                rule_score = 0.0
        
        # 2. 룰 점수가 0이면 심각도 기반 점수 사용
        if rule_score == 0.0:
            severity = rule.get("severity", "MEDIUM")
            rule_score = self.SEVERITY_SCORES.get(severity, 15.0)
        
        # 3. 축별 가중치 적용
        if self.use_axis_bonus:
            axis = rule.get("axis", "B")
            weight = self.AXIS_WEIGHTS.get(axis, 1.0)
            rule_score *= weight
        
        return rule_score
    
    def _aggregate_scores(
        self,
        rule_scores: List[float],
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """집계 방식에 따라 점수 계산"""
        if not rule_scores:
            return 0.0
        
        if self.aggregation_method == "simple_sum":
            # 중복 룰 페널티 적용
            unique_rules = {}
            for rule, score in zip(rule_results, rule_scores):
                rule_id = rule.get("rule_id", "")
                if rule_id not in unique_rules:
                    unique_rules[rule_id] = []
                unique_rules[rule_id].append(score)
            
            total = 0.0
            for rule_id, scores in unique_rules.items():
                # 첫 번째는 전체, 나머지는 30%만
                total += scores[0] + sum(s * 0.3 for s in scores[1:])
            
            return total
        
        elif self.aggregation_method == "weighted_sum":
            # 중복 룰 페널티 적용 (같은 룰이 여러 번 발동되면 가중치 감소)
            unique_rules = {}
            for rule, score in zip(rule_results, rule_scores):
                rule_id = rule.get("rule_id", "")
                if rule_id not in unique_rules:
                    unique_rules[rule_id] = []
                unique_rules[rule_id].append(score)
            
            total = 0.0
            for rule_id, scores in unique_rules.items():
                if len(scores) == 1:
                    total += scores[0]
                else:
                    # 중복 룰: 첫 번째는 전체, 나머지는 20%만 (더 강한 페널티)
                    total += scores[0] + sum(s * 0.2 for s in scores[1:])
            
            return total
        
        elif self.aggregation_method == "max":
            return max(rule_scores)
        
        elif self.aggregation_method == "mean":
            return np.mean(rule_scores)
        
        elif self.aggregation_method == "sqrt_sum":
            # 제곱근 합산: 중복 룰 페널티
            unique_rules = {}
            for rule, score in zip(rule_results, rule_scores):
                rule_id = rule.get("rule_id", "")
                if rule_id not in unique_rules:
                    unique_rules[rule_id] = 0
                unique_rules[rule_id] += 1
            
            total = 0.0
            for rule_id, count in unique_rules.items():
                # 해당 룰의 점수 찾기
                rule_score = next(
                    (s for r, s in zip(rule_results, rule_scores) 
                     if r.get("rule_id") == rule_id),
                    0.0
                )
                # 제곱근으로 중복 페널티
                total += rule_score * np.sqrt(count)
            
            return total
        
        else:
            return sum(rule_scores)
    
    def _calculate_rule_count_bonus(
        self,
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """룰 개수 보너스"""
        unique_rules = len(set(r.get("rule_id", "") for r in rule_results))
        total_rules = len(rule_results)
        
        # 고유 룰이 많을수록 보너스 - 성능 향상을 위해 증가
        bonus = 0.0
        if unique_rules >= 10:
            bonus += 15.0  # 8 -> 15
        elif unique_rules >= 5:
            bonus += 10.0  # 5 -> 10
        elif unique_rules >= 3:
            bonus += 5.0   # 2 -> 5
        
        # 중복 룰이 많으면 페널티 (같은 룰이 반복 발동)
        if total_rules > unique_rules * 2:
            bonus -= 2.0  # 중복 페널티 완화 (3 -> 2)
        
        return max(0.0, bonus)
    
    def _calculate_severity_bonus(
        self,
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """심각도 보너스"""
        severities = [r.get("severity", "MEDIUM") for r in rule_results]
        
        bonus = 0.0
        if "CRITICAL" in severities:
            bonus += 10.0  # 5 -> 10
        if "HIGH" in severities:
            bonus += 8.0   # 3 -> 8
        if severities.count("CRITICAL") >= 2:
            bonus += 8.0   # 여러 CRITICAL 룰 - 3 -> 8
        
        return bonus
    
    def _calculate_axis_bonus(
        self,
        rule_results: List[Dict[str, Any]]
    ) -> float:
        """축별 보너스 (다양한 축에서 룰 발동)"""
        axes = set(r.get("axis", "B") for r in rule_results)
        
        # 여러 축에서 룰이 발동되면 보너스 - 성능 향상을 위해 증가
        if len(axes) >= 3:
            return 10.0  # 5 -> 10
        elif len(axes) >= 2:
            return 5.0   # 2 -> 5
        else:
            return 0.0


def optimize_rule_scorer(
    train_data: List[Dict[str, Any]],
    val_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Rule-based 스코어러 최적화
    
    다양한 집계 방식과 가중치 조합을 시도하여 최적의 성능 찾기
    """
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    
    aggregation_methods = [
        "simple_sum",
        "weighted_sum",
        "max",
        "mean",
        "sqrt_sum"
    ]
    
    best_score = -1.0  # 음수로 시작하여 최소한 하나는 선택되도록
    best_config = None
    best_results = None
    
    print("=" * 80)
    print("Rule-based 스코어러 최적화")
    print("=" * 80)
    
    for method in aggregation_methods:
        for use_count in [True, False]:
            for use_severity in [True, False]:
                for use_axis in [True, False]:
                    scorer = ImprovedRuleScorer(
                        aggregation_method=method,
                        use_rule_count_bonus=use_count,
                        use_severity_bonus=use_severity,
                        use_axis_bonus=use_axis
                    )
                    
                    # 검증 데이터로 평가
                    y_true = []
                    y_pred_scores = []
                    
                    for item in val_data:
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
                        
                        y_true.append(1 if label == "fraud" else 0)
                        y_pred_scores.append(score)
                    
                    # Threshold 최적화 (F1-Score 최대화)
                    best_threshold = 50.0
                    best_f1 = 0.0
                    
                    for threshold in range(10, 90, 2):
                        y_pred = [1 if s >= threshold else 0 for s in y_pred_scores]
                        f1 = f1_score(y_true, y_pred, zero_division=0)
                        if f1 > best_f1:
                            best_f1 = f1
                            best_threshold = threshold
                    
                    y_pred = [1 if s >= best_threshold else 0 for s in y_pred_scores]
                    
                    # 성능 평가
                    accuracy = accuracy_score(y_true, y_pred)
                    precision = precision_score(y_true, y_pred, zero_division=0)
                    recall = recall_score(y_true, y_pred, zero_division=0)
                    f1 = f1_score(y_true, y_pred, zero_division=0)
                    
                    # F1-Score를 기준으로 최적 선택 (최소한 하나는 선택)
                    if f1 > best_score or best_config is None:
                        best_score = f1
                        best_config = {
                            "aggregation_method": method,
                            "use_rule_count_bonus": use_count,
                            "use_severity_bonus": use_severity,
                            "use_axis_bonus": use_axis,
                            "threshold": best_threshold
                        }
                        best_results = {
                            "accuracy": accuracy,
                            "precision": precision,
                            "recall": recall,
                            "f1_score": f1
                        }
                    
                    print(f"\n{method} | count={use_count} | severity={use_severity} | axis={use_axis} | threshold={best_threshold}")
                    print(f"  F1: {f1:.4f}, Acc: {accuracy:.4f}, Prec: {precision:.4f}, Rec: {recall:.4f}")
    
    print("\n" + "=" * 80)
    print("✅ 최적 설정:")
    print("=" * 80)
    print(f"  집계 방식: {best_config['aggregation_method']}")
    print(f"  룰 개수 보너스: {best_config['use_rule_count_bonus']}")
    print(f"  심각도 보너스: {best_config['use_severity_bonus']}")
    print(f"  축별 가중치: {best_config['use_axis_bonus']}")
    print(f"  최적 Threshold: {best_config.get('threshold', 50.0)}")
    print(f"\n  성능:")
    print(f"    F1-Score: {best_results['f1_score']:.4f}")
    print(f"    Accuracy: {best_results['accuracy']:.4f}")
    print(f"    Precision: {best_results['precision']:.4f}")
    print(f"    Recall: {best_results['recall']:.4f}")
    
    # threshold는 scorer의 인자가 아니므로 제거
    scorer_config = {k: v for k, v in best_config.items() if k != "threshold"}
    
    return {
        "config": best_config,
        "results": best_results,
        "scorer": ImprovedRuleScorer(**scorer_config)
    }

