#!/usr/bin/env python3
"""
1단계 스코어러: Rule-Based + 그래프 통계 기반 Risk Score

Rule-based 점수와 그래프 통계 feature를 결합하여 최종 Risk Score 계산

v2 변경사항 (XBlock 그래프 연구 기반):
  - 시간적 피처 컴포넌트 추가 (TemporalFeatureExtractor 연동)
  - 이웃 오염도 컴포넌트 추가 (NeighborhoodFeatureExtractor 연동)
  - true_ppr_score: 하드코딩 0.05 대신 실제 그래프 기반 값 우선 사용
  - 가중치 재조정: rule(0.35) / graph(0.40) / temporal(0.15) / neighborhood(0.10)
"""
from typing import Dict, List, Any, Optional
import numpy as np

from ..rules.evaluator import RuleEvaluator
from .improved_rule_scorer import ImprovedRuleScorer
from ..aggregation.temporal_features import TemporalFeatureExtractor
from ..aggregation.neighborhood_features import NeighborhoodFeatureExtractor


class Stage1Scorer:
    """
    1단계 스코어러: Rule-Based + 그래프 통계 기반
    
    - Rule-based 스코어링 (ImprovedRuleScorer 사용)
    - 그래프 통계 feature 기반 점수 계산
    - 둘을 결합하여 최종 Risk Score 계산
    """
    
    def __init__(
        self,
        rules_path: str = "rules/tracex_rules.yaml",
        rule_weight: float = 0.35,
        graph_weight: float = 0.40,
        temporal_weight: float = 0.15,
        neighborhood_weight: float = 0.10,
    ):
        """
        Args:
            rules_path           : 룰북 YAML 파일 경로
            rule_weight          : Rule-based 점수 가중치
            graph_weight         : 그래프 통계 점수 가중치
            temporal_weight      : 시간적 피처 점수 가중치  (신규)
            neighborhood_weight  : 이웃 오염도 점수 가중치 (신규)
        """
        self.rule_evaluator = RuleEvaluator(rules_path)
        self.rule_scorer = ImprovedRuleScorer(
            aggregation_method="weighted_sum",
            use_rule_count_bonus=True,
            use_severity_bonus=True,
            use_axis_bonus=True
        )
        self.rule_weight         = rule_weight
        self.graph_weight        = graph_weight
        self.temporal_weight     = temporal_weight
        self.neighborhood_weight = neighborhood_weight

        self._temporal_extractor     = TemporalFeatureExtractor()
        self._neighborhood_extractor = NeighborhoodFeatureExtractor()
    
    def calculate_risk_score(
        self,
        tx_data: Dict[str, Any],
        ml_features: Optional[Dict[str, Any]] = None,
        tx_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        1단계 Risk Score 계산
        
        Args:
            tx_data: 거래 데이터 (from, to, usd_value, timestamp 등)
            ml_features: 그래프 통계 feature (fan_in_count, fan_out_count 등)
            tx_context: 거래 컨텍스트 (num_transactions, graph_nodes 등)
        
        Returns:
            {
                "risk_score": float,  # 0~100
                "rule_score": float,  # Rule-based 점수
                "graph_score": float,  # 그래프 통계 점수
                "rule_results": List[Dict],  # 발동된 룰 목록
                "graph_features_used": Dict,  # 사용된 그래프 feature
                "explanation": str  # 점수 설명
            }
        """
        # 1. Rule-based 점수 계산
        rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
        
        # tx_context에 ml_features 포함
        if tx_context is None:
            tx_context = {}
        if ml_features and "ml_features" not in tx_context:
            tx_context["ml_features"] = ml_features
        
        rule_score = self.rule_scorer.calculate_score(rule_results, tx_context)
        
        # 2. 그래프 통계 점수 계산
        graph_score, graph_features_used = self._calculate_graph_score(
            ml_features or {},
            tx_context or {}
        )

        # 3. 시간적 피처 점수 (신규: ml_features에 사전 계산된 값 우선 사용)
        temporal_score = self._calculate_temporal_score(ml_features or {})

        # 4. 이웃 오염도 점수 (신규: ml_features에 사전 계산된 값 우선 사용)
        neighborhood_score = self._calculate_neighborhood_score(ml_features or {})

        # 5. 최종 Risk Score 계산 (4-component 가중 평균)
        final_score = (
            self.rule_weight         * rule_score +
            self.graph_weight        * graph_score +
            self.temporal_weight     * temporal_score +
            self.neighborhood_weight * neighborhood_score
        )
        final_score = min(100.0, max(0.0, final_score))

        # 6. 설명 생성
        explanation = self._generate_explanation(
            rule_score, graph_score, final_score,
            rule_results, graph_features_used,
            temporal_score, neighborhood_score
        )
        
        return {
            "risk_score":          final_score,
            "rule_score":          rule_score,
            "graph_score":         graph_score,
            "temporal_score":      temporal_score,
            "neighborhood_score":  neighborhood_score,
            "rule_results":        rule_results,
            "graph_features_used": graph_features_used,
            "explanation":         explanation,
        }
    
    def _calculate_graph_score(
        self,
        ml_features: Dict[str, Any],
        tx_context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """
        그래프 통계 feature 기반 점수 계산
        
        Args:
            ml_features: 그래프 통계 feature
            tx_context: 거래 컨텍스트
        
        Returns:
            (graph_score, graph_features_used)
        """
        score = 0.0
        features_used = {}
        
        # 1. Fan-in/out 통계 점수
        fan_in_count = ml_features.get("fan_in_count", 0)
        fan_out_count = ml_features.get("fan_out_count", 0)
        fan_in_value = ml_features.get("fan_in_value", 0.0)
        fan_out_value = ml_features.get("fan_out_value", 0.0)
        
        # 거래별 통계 (우선 사용)
        tx_fan_in_count = ml_features.get("tx_primary_fan_in_count", fan_in_count)
        tx_fan_out_count = ml_features.get("tx_primary_fan_out_count", fan_out_count)
        tx_fan_in_value = ml_features.get("tx_primary_fan_in_value", fan_in_value)
        tx_fan_out_value = ml_features.get("tx_primary_fan_out_value", fan_out_value)
        
        # Fan-in/out 점수 계산 (분석 결과 반영)
        # Fraud는 fan_in_count가 낮고, fan_out_count가 높음
        # Fan-in이 적으면 (자금 집중 부족) 위험도 증가
        if tx_fan_in_count < 5:  # Fraud 평균 8.92, Normal 평균 13.46
            score += 10.0
            features_used["low_fan_in"] = tx_fan_in_count
        elif tx_fan_in_count < 10:
            score += 5.0
            features_used["medium_low_fan_in"] = tx_fan_in_count
        
        # Fan-out이 많으면 (자금 분산) 위험도 증가 (Fraud 평균 28.53)
        if tx_fan_out_count >= 25:  # Fraud 평균 28.53
            score += 12.0
            features_used["very_high_fan_out"] = tx_fan_out_count
        elif tx_fan_out_count >= 15:  # Normal 평균 19.91
            score += 6.0
            features_used["high_fan_out"] = tx_fan_out_count
        
        # Fan-in/out 값 기반 점수
        if tx_fan_in_value > 1000.0:  # USD 또는 ETH 단위
            score += 10.0
            features_used["high_fan_in_value"] = tx_fan_in_value
        if tx_fan_out_value > 1000.0:
            score += 10.0
            features_used["high_fan_out_value"] = tx_fan_out_value
        
        # 2. 패턴 탐지 점수 (중요: Fraud는 pattern_score가 낮음!)
        # Fraud 평균 21.24, Normal 평균 38.40
        pattern_score = ml_features.get("pattern_score", 0.0)
        if pattern_score > 0:
            # pattern_score가 낮으면 Fraud일 가능성 높음 (역방향 점수)
            if pattern_score < 25.0:  # Fraud 평균 21.24
                score += 15.0  # 낮은 패턴 점수 = 높은 위험도
                features_used["low_pattern_score"] = pattern_score
            elif pattern_score < 30.0:
                score += 8.0
                features_used["medium_low_pattern_score"] = pattern_score
            elif pattern_score > 35.0:  # Normal 평균 38.40
                score -= 5.0  # 높은 패턴 점수 = 낮은 위험도 (페널티)
                features_used["high_pattern_score"] = pattern_score
        
        # 패턴 탐지 여부 (점수 감소)
        if ml_features.get("fan_in_detected", 0) == 1:
            score += 3.0
            features_used["fan_in_detected"] = True
        if ml_features.get("fan_out_detected", 0) == 1:
            score += 3.0
            features_used["fan_out_detected"] = True
        if ml_features.get("gather_scatter_detected", 0) == 1:
            score += 5.0
            features_used["gather_scatter_detected"] = True
        
        # 3. 거래 금액 통계 점수
        avg_value = ml_features.get("avg_transaction_value", 0.0)
        max_value = ml_features.get("max_transaction_value", 0.0)
        total_value = ml_features.get("total_transaction_value", 0.0)
        
        # 평균 거래 금액이 크면 위험도 증가 (임계값 상향)
        if avg_value > 50000.0:  # 10000 -> 50000
            score += 10.0  # 12.0 -> 10.0
            features_used["very_high_avg_value"] = avg_value
        elif avg_value > 20000.0:  # 5000 -> 20000
            score += 5.0  # 6.0 -> 5.0
            features_used["high_avg_value"] = avg_value
        
        # 최대 거래 금액이 크면 위험도 증가 (임계값 상향)
        if max_value > 100000.0:  # 50000 -> 100000
            score += 8.0  # 10.0 -> 8.0
            features_used["very_high_max_value"] = max_value
        elif max_value > 50000.0:  # 20000 -> 50000
            score += 4.0  # 5.0 -> 4.0
            features_used["high_max_value"] = max_value
        
        # 4. 그래프 크기 점수 (분석 결과 반영: Fraud가 더 큰 그래프)
        graph_nodes = tx_context.get("graph_nodes", 0)
        graph_edges = tx_context.get("graph_edges", 0)
        num_transactions = tx_context.get("num_transactions", 0)
        
        # Fraud 평균 127.04, Normal 평균 83.35
        if graph_nodes > 120:  # Fraud 평균 127.04
            score += 8.0  # 큰 그래프 = 위험도 증가
            features_used["very_large_graph"] = graph_nodes
        elif graph_nodes > 90:  # Normal 평균 83.35
            score += 4.0
            features_used["large_graph"] = graph_nodes
        elif graph_nodes < 70:  # Normal이 더 작은 그래프
            score -= 2.0  # 작은 그래프 = 낮은 위험도 (약간의 페널티)
            features_used["small_graph"] = graph_nodes
        
        # 거래 개수는 비슷함 (Fraud 92.87, Normal 98.03) - 약간만 반영
        if num_transactions > 100:
            score += 2.0
            features_used["many_transactions"] = num_transactions
        
        # 5. PPR 점수 — true_ppr_score(실제 그래프) 우선, 없으면 기존 ppr_score 사용
        ppr_score = ml_features.get("true_ppr_score", ml_features.get("ppr_score", 0.0))
        if ppr_score >= 0.15:
            score += 15.0
            features_used["very_high_ppr"] = ppr_score
        elif ppr_score > 0.08:
            score += 10.0
            features_used["high_ppr"] = ppr_score
        elif ppr_score > 0.03:
            score += 5.0
            features_used["medium_ppr"] = ppr_score
        
        # 6. 정규화 점수 (NTS, NWS) - 분석 결과 반영
        n_theta = ml_features.get("n_theta", 0.0)
        n_omega = ml_features.get("n_omega", 0.0)
        
        # n_theta는 Fraud와 Normal이 비슷함 (0.82 vs 0.86) - 약간만 반영
        if n_theta > 0.85:  # Normal이 약간 높음
            score -= 2.0  # 높은 n_theta = 낮은 위험도 (약간의 페널티)
            features_used["high_n_theta"] = n_theta
        elif n_theta < 0.80:  # Fraud가 약간 낮음
            score += 3.0
            features_used["low_n_theta"] = n_theta
        
        # n_omega는 Fraud가 낮음 (0.44 vs 0.57) - 중요!
        if n_omega < 0.45:  # Fraud 평균 0.44
            score += 8.0  # 낮은 n_omega = 높은 위험도
            features_used["low_n_omega"] = n_omega
        elif n_omega < 0.50:
            score += 4.0
            features_used["medium_low_n_omega"] = n_omega
        elif n_omega > 0.55:  # Normal 평균 0.57
            score -= 3.0  # 높은 n_omega = 낮은 위험도 (페널티)
            features_used["high_n_omega"] = n_omega
        
        # 최종 점수 (0~100 범위로 제한)
        graph_score = min(100.0, max(0.0, score))

        return graph_score, features_used

    # ── 신규: 시간적 피처 점수 ────────────────────────────────────

    def _calculate_temporal_score(self, ml_features: Dict[str, Any]) -> float:
        """
        ml_features에 사전 계산된 시간적 피처가 있으면 위험 점수로 변환.
        extract_xblock_features.py 또는 실시간 Etherscan 데이터 모두 지원.
        """
        temporal_keys = {"inter_tx_interval_std", "burst_score", "active_days",
                         "tx_density", "night_tx_ratio"}
        if not temporal_keys & set(ml_features.keys()):
            return 0.0

        temporal_feats = {k: ml_features.get(k, 0.0) for k in temporal_keys}
        return self._temporal_extractor.temporal_risk_score(temporal_feats)

    # ── 신규: 이웃 오염도 점수 ────────────────────────────────────

    def _calculate_neighborhood_score(self, ml_features: Dict[str, Any]) -> float:
        """
        ml_features에 사전 계산된 이웃 오염도 피처가 있으면 위험 점수로 변환.
        extract_xblock_features.py 또는 실시간 그래프 분석 모두 지원.
        """
        neighborhood_keys = {"direct_phishing_neighbors", "phishing_neighbor_ratio",
                             "hop2_phishing_count", "hop2_phishing_ratio",
                             "phishing_exposure_score"}
        if not neighborhood_keys & set(ml_features.keys()):
            return 0.0

        nb_feats = {k: ml_features.get(k, 0.0) for k in neighborhood_keys}
        # true_ppr_score도 넘겨줌
        nb_feats["true_ppr_score"] = ml_features.get(
            "true_ppr_score", ml_features.get("ppr_score", 0.05)
        )
        return self._neighborhood_extractor.neighborhood_risk_score(nb_feats)

    # ── 설명 생성 ─────────────────────────────────────────────────

    def _generate_explanation(
        self,
        rule_score: float,
        graph_score: float,
        final_score: float,
        rule_results: List[Dict[str, Any]],
        graph_features_used: Dict[str, Any],
        temporal_score: float = 0.0,
        neighborhood_score: float = 0.0,
    ) -> str:
        parts = []

        if rule_score > 0:
            parts.append(f"Rule-based: {rule_score:.1f}점")
            if rule_results:
                rule_ids = [r.get("rule_id", "") for r in rule_results[:3]]
                parts.append(f"발동룰: {', '.join(rule_ids)}")

        if graph_score > 0:
            parts.append(f"Graph: {graph_score:.1f}점")
            if graph_features_used:
                parts.append(f"주요feature: {', '.join(list(graph_features_used.keys())[:3])}")

        if temporal_score > 0:
            parts.append(f"Temporal: {temporal_score:.1f}점")

        if neighborhood_score > 0:
            parts.append(f"Neighborhood: {neighborhood_score:.1f}점")

        parts.append(f"최종: {final_score:.1f}점")

        return " | ".join(parts)

