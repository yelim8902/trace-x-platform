"""
MPOCryptoML 통합 스코어 계산기

Rule-based 점수와 MPOCryptoML 점수를 결합하여 최종 리스크 점수 계산
"""

from typing import Dict, List, Set, Optional, Any
import networkx as nx
from collections import defaultdict

from .mpocryptml_patterns import MPOCryptoMLPatternDetector
from .ppr_connector import PPRConnector
from .mpocryptml_normalizer import MPOCryptoMLNormalizer


class MPOCryptoMLScorer:
    """
    MPOCryptoML 방법론 기반 스코어 계산기
    
    논문의 방법론을 따라:
    1. Multi-source PPR 점수 계산
    2. 그래프 패턴 탐지 (Fan-in, Fan-out, Gather-scatter, Stack, Bipartite)
    3. Timestamp 정규화 (NTS)
    4. Weight 정규화 (NWS)
    5. 최종 점수 결합
    """
    
    def __init__(
        self,
        damping_factor: float = 0.85,
        max_iter: int = 1000,
        rule_weight: float = 0.7,
        ml_weight: float = 0.3
    ):
        """
        Args:
            damping_factor: PPR damping factor (논문: α = 0.5)
            max_iter: PPR 최대 반복 횟수
            rule_weight: Rule-based 점수 가중치 (기본 0.7)
            ml_weight: MPOCryptoML 점수 가중치 (기본 0.3)
        """
        self.pattern_detector = MPOCryptoMLPatternDetector()
        self.ppr_connector = PPRConnector(damping_factor=damping_factor, max_iter=max_iter)
        self.normalizer = MPOCryptoMLNormalizer()
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight
    
    def build_graph_from_transactions(
        self,
        transactions: List[Dict[str, Any]]
    ) -> nx.DiGraph:
        """
        3-hop 거래 데이터로부터 그래프 구축
        
        Args:
            transactions: 거래 리스트 (3-hop까지 포함)
        
        Returns:
            방향성 그래프 G = (V, E, W, T)
        """
        self.pattern_detector.build_from_transactions(transactions)
        return self.pattern_detector.graph
    
    def calculate_ppr_score(
        self,
        target_address: str,
        graph: nx.DiGraph,
        source_addresses: Optional[List[str]] = None,
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, float]:
        """
        Multi-source PPR 점수 계산
        
        논문 Algorithm 1: Multi-source Personalized PageRank
        
        Args:
            target_address: 분석 대상 주소
            graph: 거래 그래프
            source_addresses: 소스 주소 리스트 (None이면 자동 탐지)
            sdn_addresses: SDN 리스트
            mixer_addresses: 믹서 리스트
        
        Returns:
            {
                "ppr_score": float,  # PPR 점수
                "sdn_ppr": float,    # SDN과의 연결성
                "mixer_ppr": float,   # 믹서와의 연결성
                "total_ppr": float    # 종합 PPR 점수
            }
        """
        if not graph or target_address.lower() not in graph:
            return {
                "ppr_score": 0.0,
                "sdn_ppr": 0.0,
                "mixer_ppr": 0.0,
                "total_ppr": 0.0
            }
        
        # 소스 주소 자동 탐지 (논문: out-degree가 0이 아닌 노드)
        if source_addresses is None:
            source_addresses = [
                node for node in graph.nodes()
                if graph.out_degree(node) > 0 and graph.in_degree(node) == 0
            ]
        
        # SDN/믹서와의 연결성 계산
        sdn_ppr = 0.0
        mixer_ppr = 0.0
        
        if sdn_addresses:
            sdn_list = [addr for addr in sdn_addresses if addr.lower() in graph]
            if sdn_list:
                sdn_ppr = self.ppr_connector.calculate_ppr(
                    target_address, sdn_list, graph
                )
        
        if mixer_addresses:
            mixer_list = [addr for addr in mixer_addresses if addr.lower() in graph]
            if mixer_list:
                mixer_ppr = self.ppr_connector.calculate_ppr(
                    target_address, mixer_list, graph
                )
        
        # Multi-source PPR 계산
        if source_addresses:
            ppr_score = self.ppr_connector.calculate_ppr(
                target_address, source_addresses, graph
            )
        else:
            ppr_score = 0.0
        
        # 종합 PPR 점수 (논문 방식)
        total_ppr = ppr_score * 0.4 + sdn_ppr * 0.4 + mixer_ppr * 0.2
        
        return {
            "ppr_score": ppr_score,
            "sdn_ppr": sdn_ppr,
            "mixer_ppr": mixer_ppr,
            "total_ppr": total_ppr
        }
    
    def calculate_pattern_score(
        self,
        target_address: str,
        graph: nx.DiGraph
    ) -> Dict[str, Any]:
        """
        그래프 패턴 점수 계산
        
        논문의 패턴들: Fan-in, Fan-out, Gather-scatter, Stack, Bipartite
        
        Args:
            target_address: 분석 대상 주소
            graph: 거래 그래프
        
        Returns:
            패턴 탐지 결과 및 점수
        """
        patterns = self.pattern_detector.analyze_address_patterns(target_address)
        
        # 패턴 점수 계산 (각 패턴이 탐지되면 점수 부여)
        pattern_score = 0.0
        detected_patterns = []
        
        # Fan-in 패턴
        if patterns["fan_in"]["pattern"]["is_detected"]:
            pattern_score += 12.0
            detected_patterns.append("fan_in")

        # Fan-out 패턴
        if patterns["fan_out"]["pattern"]["is_detected"]:
            pattern_score += 12.0
            detected_patterns.append("fan_out")

        # Gather-scatter 패턴 (Fan-in + Fan-out)
        if (patterns["fan_in"]["pattern"]["is_detected"] and
            patterns["fan_out"]["pattern"]["is_detected"]):
            pattern_score += 8.0  # 보너스
            detected_patterns.append("gather_scatter")
        
        # Stack 패턴
        if patterns["stack_paths"]:
            pattern_score += 20.0
            detected_patterns.append("stack")
        
        # Bipartite 패턴
        if patterns["bipartite"]["is_bipartite"]:
            pattern_score += 15.0
            detected_patterns.append("bipartite")
        
        return {
            "pattern_score": min(100.0, pattern_score),
            "detected_patterns": detected_patterns,
            "patterns": patterns
        }
    
    def calculate_ml_score(
        self,
        target_address: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]],
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        MPOCryptoML 종합 점수 계산
        
        논문의 방법론에 따라:
        1. PPR 점수
        2. 패턴 점수
        3. Timestamp 정규화 (NTS)
        4. Weight 정규화 (NWS)
        
        Args:
            target_address: 분석 대상 주소
            graph: 거래 그래프
            transactions: 거래 리스트
            sdn_addresses: SDN 리스트
            mixer_addresses: 믹서 리스트
        
        Returns:
            {
                "ml_score": float,  # MPOCryptoML 점수 (0~100)
                "ppr_score": float,
                "pattern_score": float,
                "n_theta": float,
                "n_omega": float,
                "details": Dict
            }
        """
        # 1. PPR 점수
        ppr_result = self.calculate_ppr_score(
            target_address, graph, None, sdn_addresses, mixer_addresses
        )
        ppr_score = ppr_result["total_ppr"] * 100  # 0~1 -> 0~100
        
        # 2. 패턴 점수
        pattern_result = self.calculate_pattern_score(target_address, graph)
        pattern_score = pattern_result["pattern_score"]
        
        # 3. Timestamp 정규화 (NTS)
        n_theta = self.normalizer.normalize_timestamp(
            target_address, graph, transactions
        )
        nts_score = n_theta * 20  # 0~1 -> 0~20
        
        # 4. Weight 정규화 (NWS)
        n_omega = self.normalizer.normalize_weight(
            target_address, graph, transactions
        )
        nws_score = n_omega * 20  # 0~1 -> 0~20
        
        # 종합 점수 계산 (논문 방식)
        # 논문에서는 Logistic Regression 사용하지만, 여기서는 가중 평균
        ml_score = (
            ppr_score * 0.3 +
            pattern_score * 0.4 +
            nts_score * 0.15 +
            nws_score * 0.15
        )
        
        return {
            "ml_score": min(100.0, ml_score),
            "ppr_score": ppr_score,
            "pattern_score": pattern_score,
            "nts_score": nts_score,
            "nws_score": nws_score,
            "n_theta": n_theta,
            "n_omega": n_omega,
            "details": {
                "ppr": ppr_result,
                "patterns": pattern_result,
                "detected_patterns": pattern_result["detected_patterns"]
            }
        }
    
    def calculate_hybrid_score(
        self,
        rule_based_score: float,
        target_address: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]],
        sdn_addresses: Optional[Set[str]] = None,
        mixer_addresses: Optional[Set[str]] = None
    ) -> Dict[str, Any]:
        """
        하이브리드 점수 계산: Rule-based + MPOCryptoML
        
        Args:
            rule_based_score: Rule-based 점수 (0~100)
            target_address: 분석 대상 주소
            graph: 거래 그래프
            transactions: 거래 리스트
            sdn_addresses: SDN 리스트
            mixer_addresses: 믹서 리스트
        
        Returns:
            {
                "final_score": float,  # 최종 점수 (0~100)
                "rule_score": float,
                "ml_score": float,
                "ml_details": Dict
            }
        """
        # MPOCryptoML 점수 계산
        ml_result = self.calculate_ml_score(
            target_address, graph, transactions, sdn_addresses, mixer_addresses
        )
        ml_score = ml_result["ml_score"]
        
        # 하이브리드 점수: Rule-based (70%) + MPOCryptoML (30%)
        final_score = (
            rule_based_score * self.rule_weight +
            ml_score * self.ml_weight
        )
        
        return {
            "final_score": min(100.0, final_score),
            "rule_score": rule_based_score,
            "ml_score": ml_score,
            "ml_details": ml_result
        }

