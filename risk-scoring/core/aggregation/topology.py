"""
토폴로지 기반 룰 평가 모듈

그래프 구조 분석을 통한 B-201 (Layering Chain), B-202 (Cycle) 룰 구현
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx

from .mpocryptml_patterns import MPOCryptoMLPatternDetector


class TopologyEvaluator:
    """
    토폴로지 기반 룰 평가기
    
    B-201 (Layering Chain), B-202 (Cycle) 룰 평가
    """
    
    def __init__(self):
        self.pattern_detector = MPOCryptoMLPatternDetector()
    
    def evaluate_layering_chain(
        self,
        target_address: str,
        transactions: List[Dict[str, Any]],
        rule_spec: Dict[str, Any]
    ) -> bool:
        """
        B-201: Layering Chain 룰 평가
        
        조건:
        - same_token: true (동일 토큰)
        - hop_length_gte: 3 (3홉 이상)
        - hop_amount_delta_pct_lte: 5 (각 홉 금액 차이 <= 5%)
        - min_usd_value: 100 (최소 거래액)
        
        Args:
            target_address: 분석 대상 주소
            transactions: 거래 히스토리 (3홉까지 포함 가능)
            rule_spec: 룰 설정
        
        Returns:
            룰 발동 여부
        """
        same_token = rule_spec.get("same_token", False)
        hop_length_gte = rule_spec.get("hop_length_gte", 3)
        hop_amount_delta_pct_lte = rule_spec.get("hop_amount_delta_pct_lte", 5)
        min_usd_value = rule_spec.get("min_usd_value", 100)
        
        # 그래프 구축
        self.pattern_detector._build_graph()
        for tx in transactions:
            self.pattern_detector.add_transaction(tx)
        
        if not self.pattern_detector.graph:
            return False
        
        target_address = target_address.lower()
        
        # 토큰별로 그래프 분리 (same_token이 true인 경우)
        if same_token:
            # asset_contract별로 그래프 분리
            token_graphs = self._build_token_graphs(transactions)
            for token, graph in token_graphs.items():
                if self._find_layering_chain_in_graph(
                    target_address,
                    graph,
                    hop_length_gte,
                    hop_amount_delta_pct_lte,
                    min_usd_value
                ):
                    return True
        else:
            # 토큰 구분 없이 전체 그래프에서 탐색
            if self._find_layering_chain_in_graph(
                target_address,
                self.pattern_detector.graph,
                hop_length_gte,
                hop_amount_delta_pct_lte,
                min_usd_value
            ):
                return True
        
        return False
    
    def evaluate_cycle(
        self,
        target_address: str,
        transactions: List[Dict[str, Any]],
        rule_spec: Dict[str, Any]
    ) -> bool:
        """
        B-202: Cycle 룰 평가
        
        조건:
        - same_token: true (동일 토큰)
        - cycle_length_in: [2, 3] (2-3홉 순환)
        - cycle_total_usd_gte: 100 (순환 총액 >= 100 USD)
        
        Args:
            target_address: 분석 대상 주소
            transactions: 거래 히스토리 (3홉까지 포함 가능)
            rule_spec: 룰 설정
        
        Returns:
            룰 발동 여부
        """
        same_token = rule_spec.get("same_token", False)
        cycle_length_in = rule_spec.get("cycle_length_in", [2, 3])
        cycle_total_usd_gte = rule_spec.get("cycle_total_usd_gte", 100)
        
        # 그래프 구축
        self.pattern_detector._build_graph()
        for tx in transactions:
            self.pattern_detector.add_transaction(tx)
        
        if not self.pattern_detector.graph:
            return False
        
        target_address = target_address.lower()
        
        # 토큰별로 그래프 분리
        if same_token:
            token_graphs = self._build_token_graphs(transactions)
            for token, graph in token_graphs.items():
                if self._find_cycle_in_graph(
                    target_address,
                    graph,
                    cycle_length_in,
                    cycle_total_usd_gte
                ):
                    return True
        else:
            if self._find_cycle_in_graph(
                target_address,
                self.pattern_detector.graph,
                cycle_length_in,
                cycle_total_usd_gte
            ):
                return True
        
        return False
    
    def _build_token_graphs(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, nx.DiGraph]:
        """
        토큰별로 그래프 분리
        
        Args:
            transactions: 거래 리스트
        
        Returns:
            {token: graph} 딕셔너리
        """
        token_graphs: Dict[str, nx.DiGraph] = defaultdict(lambda: nx.DiGraph())
        
        for tx in transactions:
            token = tx.get("asset_contract", "").lower()
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            weight = float(tx.get("usd_value", tx.get("amount_usd", 0)))
            
            if not from_addr or not to_addr:
                continue
            
            token_graphs[token].add_node(from_addr)
            token_graphs[token].add_node(to_addr)
            
            if token_graphs[token].has_edge(from_addr, to_addr):
                current_weight = token_graphs[token][from_addr][to_addr].get("weight", 0)
                token_graphs[token][from_addr][to_addr]["weight"] = current_weight + weight
            else:
                token_graphs[token].add_edge(from_addr, to_addr, weight=weight)
        
        return dict(token_graphs)
    
    def _find_layering_chain_in_graph(
        self,
        start_address: str,
        graph: nx.DiGraph,
        min_hops: int,
        max_amount_delta_pct: float,
        min_usd_value: float
    ) -> bool:
        """
        그래프에서 레이어링 체인 찾기
        
        Args:
            start_address: 시작 주소
            graph: 그래프
            min_hops: 최소 홉 수
            max_amount_delta_pct: 최대 금액 차이 (%)
            min_usd_value: 최소 거래액
        
        Returns:
            레이어링 체인 발견 여부
        """
        if start_address not in graph:
            return False
        
        # DFS로 경로 탐색
        def dfs(current: str, path: List[str], path_weights: List[float], visited: Set[str]):
            if len(path) >= min_hops + 1:  # min_hops 홉 = min_hops+1 노드
                # 금액 차이 체크
                if self._check_amount_delta(path_weights, max_amount_delta_pct):
                    return True
            
            if len(path) >= 10:  # 너무 긴 경로 방지
                return False
            
            for successor in graph.successors(current):
                if successor in visited:
                    continue
                
                edge_weight = graph[current][successor].get("weight", 0)
                if edge_weight < min_usd_value:
                    continue
                
                visited.add(successor)
                path.append(successor)
                path_weights.append(edge_weight)
                
                if dfs(successor, path, path_weights, visited):
                    return True
                
                path.pop()
                path_weights.pop()
                visited.remove(successor)
            
            return False
        
        return dfs(start_address, [start_address], [], {start_address})
    
    def _find_cycle_in_graph(
        self,
        target_address: str,
        graph: nx.DiGraph,
        cycle_lengths: List[int],
        min_total_usd: float
    ) -> bool:
        """
        그래프에서 순환 찾기
        
        Args:
            target_address: 대상 주소
            graph: 그래프
            cycle_lengths: 순환 길이 리스트 (예: [2, 3])
            min_total_usd: 최소 순환 총액
        
        Returns:
            순환 발견 여부
        """
        if target_address not in graph:
            return False
        
        # NetworkX의 simple_cycles 사용 (작은 그래프에만 적합)
        try:
            # target_address를 포함하는 순환만 찾기
            # 간단한 방법: DFS로 순환 탐지
            for cycle_length in cycle_lengths:
                if self._find_cycle_of_length(target_address, graph, cycle_length, min_total_usd):
                    return True
        except Exception:
            pass
        
        return False
    
    def _find_cycle_of_length(
        self,
        start_address: str,
        graph: nx.DiGraph,
        cycle_length: int,
        min_total_usd: float
    ) -> bool:
        """
        특정 길이의 순환 찾기
        
        Args:
            start_address: 시작 주소
            graph: 그래프
            cycle_length: 순환 길이 (홉 수)
            min_total_usd: 최소 총액
        
        Returns:
            순환 발견 여부
        """
        def dfs(current: str, path: List[str], path_weights: List[float], visited: Set[str]):
            if len(path) == cycle_length + 1:  # cycle_length 홉 = cycle_length+1 노드
                # 시작 주소로 돌아왔는지 체크
                if path[-1] == start_address:
                    total_usd = sum(path_weights)
                    if total_usd >= min_total_usd:
                        return True
                return False
            
            if len(path) > cycle_length + 1:
                return False
            
            for successor in graph.successors(current):
                # 마지막 홉이면 시작 주소로 가야 함
                if len(path) == cycle_length:
                    if successor != start_address:
                        continue
                elif successor in visited:
                    continue
                
                edge_weight = graph[current][successor].get("weight", 0)
                
                visited.add(successor)
                path.append(successor)
                path_weights.append(edge_weight)
                
                if dfs(successor, path, path_weights, visited):
                    return True
                
                path.pop()
                path_weights.pop()
                visited.remove(successor)
            
            return False
        
        return dfs(start_address, [start_address], [], {start_address})
    
    def _check_amount_delta(
        self,
        amounts: List[float],
        max_delta_pct: float
    ) -> bool:
        """
        금액 차이 체크
        
        각 홉의 금액 차이가 max_delta_pct 이내인지 확인
        
        Args:
            amounts: 각 홉의 금액 리스트
            max_delta_pct: 최대 차이 (%)
        
        Returns:
            모든 홉의 차이가 max_delta_pct 이내면 True
        """
        if len(amounts) < 2:
            return True
        
        # 첫 번째 금액을 기준으로
        base_amount = amounts[0]
        
        for amount in amounts[1:]:
            if base_amount == 0:
                return False
            
            delta_pct = abs(amount - base_amount) / base_amount * 100
            if delta_pct > max_delta_pct:
                return False
        
        return True

