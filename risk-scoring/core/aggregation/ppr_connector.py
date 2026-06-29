"""
PPR (Personalized PageRank) 연결성 분석 모듈

MPOCryptoML 논문의 오프체인 연결성 분석을 위한 PPR 계산
"""

from typing import Dict, List, Set, Optional, Any
import networkx as nx
from collections import defaultdict


class PPRConnector:
    """
    Personalized PageRank 기반 연결성 분석기
    
    오프체인 거래 그래프에서 제재 주소, 믹서 등과의 연결성을 측정
    """
    
    def __init__(self, damping_factor: float = 0.85, max_iter: int = 100):
        """
        Args:
            damping_factor: PPR damping factor (기본 0.85)
            max_iter: 최대 반복 횟수
        """
        self.damping_factor = damping_factor
        self.max_iter = max_iter
    
    def calculate_ppr(
        self,
        target_address: str,
        source_addresses: List[str],
        graph: nx.DiGraph
    ) -> float:
        """
        Multi-source Personalized PageRank 계산
        
        논문 Algorithm 1: Multi-source PPR
        여러 소스 주소들에서 시작하는 랜덤 워크를 통해 타겟 주소의 연결성 측정
        
        Args:
            target_address: 분석 대상 주소
            source_addresses: 소스 주소 리스트 (제재 주소, 믹서 등)
            graph: 거래 그래프 G = (V, E, W, T)
        
        Returns:
            PPR 점수 (0~1, 높을수록 연결성 강함)
        """
        if not graph or target_address.lower() not in graph:
            return 0.0
        
        target_address = target_address.lower()
        source_addresses = [addr.lower() for addr in source_addresses]
        
        # 소스 주소가 그래프에 없으면 0 반환
        valid_sources = [addr for addr in source_addresses if addr in graph]
        if not valid_sources:
            return 0.0
        
        # Multi-source Personalized PageRank 계산
        # 논문: 각 소스 노드에서 동일한 가중치로 시작
        try:
            # NetworkX의 pagerank 활용 (personalization 파라미터 사용)
            # 논문 Algorithm 1: 모든 소스 노드에 동일한 확률 분배
            personalization = {addr: 1.0 / len(valid_sources) for addr in valid_sources}
            
            # 나머지 노드는 0으로 설정
            for node in graph.nodes():
                if node not in personalization:
                    personalization[node] = 0.0
            
            # Multi-source PPR 계산
            # 논문: α = 0.5 (damping_factor), 하지만 기본값 0.85도 사용 가능
            ppr_scores = nx.pagerank(
                graph,
                alpha=self.damping_factor,
                personalization=personalization,
                max_iter=self.max_iter
            )
            
            # 타겟 주소의 PPR 점수 반환
            # 논문: SPS (Set of PPR Scores)에 저장되는 값
            return ppr_scores.get(target_address, 0.0)
        
        except Exception:
            return 0.0
    
    def calculate_multi_source_ppr(
        self,
        target_address: str,
        graph: nx.DiGraph,
        auto_detect_sources: bool = True
    ) -> Dict[str, Any]:
        """
        논문 Algorithm 1: Multi-source PPR (전체 구현)
        
        소스 노드 자동 탐지 및 PPR 점수 계산
        
        Args:
            target_address: 분석 대상 주소
            graph: 거래 그래프
            auto_detect_sources: 소스 노드 자동 탐지 여부
        
        Returns:
            {
                "ppr_score": float,
                "source_nodes": List[str],
                "visited_nodes": List[str]
            }
        """
        if not graph or target_address.lower() not in graph:
            return {
                "ppr_score": 0.0,
                "source_nodes": [],
                "visited_nodes": []
            }
        
        target_address = target_address.lower()
        
        # 논문 Algorithm 1, Line 3-4: 소스 노드 탐지
        # 소스 노드: out-degree > 0, in-degree == 0
        if auto_detect_sources:
            source_nodes = [
                node for node in graph.nodes()
                if graph.out_degree(node) > 0 and graph.in_degree(node) == 0
            ]
        else:
            source_nodes = []
        
        if not source_nodes:
            return {
                "ppr_score": 0.0,
                "source_nodes": [],
                "visited_nodes": []
            }
        
        # Multi-source PPR 계산
        ppr_score = self.calculate_ppr(target_address, source_nodes, graph)
        
        # 방문한 노드들 (PPR 점수가 0이 아닌 노드들)
        # 실제로는 PPR 계산 시 모든 노드에 점수가 부여되지만,
        # 여기서는 의미있는 점수를 가진 노드만 반환
        try:
            personalization = {addr: 1.0 / len(source_nodes) for addr in source_nodes}
            for node in graph.nodes():
                if node not in personalization:
                    personalization[node] = 0.0
            
            ppr_scores = nx.pagerank(
                graph,
                alpha=self.damping_factor,
                personalization=personalization,
                max_iter=self.max_iter
            )
            
            # 의미있는 점수를 가진 노드들 (threshold: 0.001)
            visited_nodes = [
                node for node, score in ppr_scores.items()
                if score > 0.001
            ]
        except:
            visited_nodes = []
        
        return {
            "ppr_score": ppr_score,
            "source_nodes": source_nodes,
            "visited_nodes": visited_nodes
        }
    
    def calculate_connection_risk(
        self,
        target_address: str,
        graph: nx.DiGraph,
        sdn_addresses: Set[str],
        mixer_addresses: Set[str]
    ) -> Dict[str, Any]:
        """
        연결성 리스크 계산
        
        제재 주소 및 믹서와의 연결성을 종합적으로 평가
        
        Args:
            target_address: 분석 대상 주소
            graph: 거래 그래프
            sdn_addresses: SDN 리스트
            mixer_addresses: 믹서 리스트
        
        Returns:
            {
                "sdn_ppr": float,  # SDN과의 PPR 연결성
                "mixer_ppr": float,  # 믹서와의 PPR 연결성
                "total_ppr": float,  # 전체 연결성
                "risk_level": str  # low | medium | high
            }
        """
        sdn_list = [addr.lower() for addr in sdn_addresses if addr.lower() in graph]
        mixer_list = [addr.lower() for addr in mixer_addresses if addr.lower() in graph]
        
        sdn_ppr = 0.0
        mixer_ppr = 0.0
        
        if sdn_list:
            sdn_ppr = self.calculate_ppr(target_address, sdn_list, graph)
        
        if mixer_list:
            mixer_ppr = self.calculate_ppr(target_address, mixer_list, graph)
        
        # 전체 연결성 (가중 평균)
        total_ppr = (sdn_ppr * 0.6 + mixer_ppr * 0.4)  # SDN이 더 중요
        
        # 리스크 레벨 결정
        if total_ppr >= 0.1:
            risk_level = "high"
        elif total_ppr >= 0.05:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "sdn_ppr": sdn_ppr,
            "mixer_ppr": mixer_ppr,
            "total_ppr": total_ppr,
            "risk_level": risk_level
        }

