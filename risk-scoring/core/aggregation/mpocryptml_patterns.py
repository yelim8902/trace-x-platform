"""
MPOCryptoML 패턴 탐지 모듈

논문의 수학적 정의에 따른 패턴 탐지 구현:
- Fan-in: d_i^-(S) = Σ_{v_k ∈ M_{l-1} ∧ (k,v) ∈ E} e_{kv}
- Fan-out: d_i^+(S) = Σ_{v_j ∈ M_{l+1} ∧ (v,j) ∈ E} e_{vj}
- Gather-Scatter: fan-in(v) + fan-out(v)
- Stack: directed path P = (v1, v2, ..., vk)
- Bipartite: ∀(u, v) ∈ E, u ∈ M_l ⇒ v ∈ M_{l+1}
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict
from datetime import datetime
import networkx as nx


class MPOCryptoMLPatternDetector:
    """
    MPOCryptoML 논문의 패턴 정의에 따른 탐지기
    
    그래프 G = (V, E, W, T)에서:
    - V: vertices (주소들)
    - E: edges (트랜잭션들)
    - W: weights (거래 금액, usd_value)
    - T: timestamps
    """
    
    def __init__(self):
        self.graph: Optional[nx.DiGraph] = None
        self._build_graph()
    
    def _build_graph(self):
        """방향성 그래프 초기화"""
        self.graph = nx.DiGraph()
    
    def add_transaction(self, tx: Dict[str, Any]):
        """
        트랜잭션을 그래프에 추가
        
        Args:
            tx: {
                "from": str,
                "to": str,
                "usd_value": float,
                "timestamp": str/int,
                "tx_hash": str
            }
        """
        if not self.graph:
            self._build_graph()
        
        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()
        
        # USD 값 우선, 없으면 Wei 값 사용 (정규화를 위해 1e18로 나눔)
        usd_value = float(tx.get("usd_value", tx.get("amount_usd", 0)))
        if usd_value > 0:
            weight = usd_value
        else:
            # Wei 단위 값을 사용 (1 ETH = 1e18 Wei)
            wei_value = float(tx.get("value", 0))
            if wei_value > 0:
                # Wei를 ETH로 변환 (정규화)
                weight = wei_value / 1e18
            else:
                weight = 0.0
        
        timestamp = tx.get("timestamp", "")
        
        if not from_addr or not to_addr or weight <= 0:
            return
        
        # 노드 추가
        self.graph.add_node(from_addr)
        self.graph.add_node(to_addr)
        
        # 엣지 추가 (가중치 포함)
        if self.graph.has_edge(from_addr, to_addr):
            # 기존 엣지가 있으면 가중치 누적
            current_weight = self.graph[from_addr][to_addr].get("weight", 0)
            self.graph[from_addr][to_addr]["weight"] = current_weight + weight
            # 트랜잭션 리스트에 추가
            if "transactions" not in self.graph[from_addr][to_addr]:
                self.graph[from_addr][to_addr]["transactions"] = []
            self.graph[from_addr][to_addr]["transactions"].append({
                "tx_hash": tx.get("tx_hash", ""),
                "timestamp": timestamp,
                "usd_value": weight
            })
        else:
            self.graph.add_edge(
                from_addr,
                to_addr,
                weight=weight,
                transactions=[{
                    "tx_hash": tx.get("tx_hash", ""),
                    "timestamp": timestamp,
                    "usd_value": weight
                }]
            )
    
    def build_from_transactions(self, transactions: List[Dict[str, Any]]):
        """트랜잭션 리스트로부터 그래프 구축"""
        self._build_graph()
        for tx in transactions:
            self.add_transaction(tx)
    
    def fan_in(self, vertex: str) -> float:
        """
        Fan-in 계산: d_i^-(S) = Σ_{v_k ∈ M_{l-1} ∧ (k,v) ∈ E} e_{kv}
        
        Args:
            vertex: 주소 (소문자)
        
        Returns:
            fan-in 값 (가중치 합계)
        """
        if not self.graph or vertex.lower() not in self.graph:
            return 0.0
        
        vertex = vertex.lower()
        fan_in_value = 0.0
        
        # 들어오는 엣지들의 가중치 합계
        for predecessor in self.graph.predecessors(vertex):
            edge_weight = self.graph[predecessor][vertex].get("weight", 0)
            fan_in_value += edge_weight
        
        return fan_in_value
    
    def fan_in_count(self, vertex: str) -> int:
        """
        Fan-in 개수: |{u ∈ V | (u, v) ∈ E}|
        
        Args:
            vertex: 주소
        
        Returns:
            들어오는 엣지 개수
        """
        if not self.graph or vertex.lower() not in self.graph:
            return 0
        
        return self.graph.in_degree(vertex.lower())
    
    def fan_out(self, vertex: str) -> float:
        """
        Fan-out 계산: d_i^+(S) = Σ_{v_j ∈ M_{l+1} ∧ (v,j) ∈ E} e_{vj}
        
        Args:
            vertex: 주소 (소문자)
        
        Returns:
            fan-out 값 (가중치 합계)
        """
        if not self.graph or vertex.lower() not in self.graph:
            return 0.0
        
        vertex = vertex.lower()
        fan_out_value = 0.0
        
        # 나가는 엣지들의 가중치 합계
        for successor in self.graph.successors(vertex):
            edge_weight = self.graph[vertex][successor].get("weight", 0)
            fan_out_value += edge_weight
        
        return fan_out_value
    
    def fan_out_count(self, vertex: str) -> int:
        """
        Fan-out 개수: |{w ∈ V | (v, w) ∈ E}|
        
        Args:
            vertex: 주소
        
        Returns:
            나가는 엣지 개수
        """
        if not self.graph or vertex.lower() not in self.graph:
            return 0
        
        return self.graph.out_degree(vertex.lower())
    
    def gather_scatter(self, vertex: str) -> float:
        """
        Gather-Scatter: fan-in(v) + fan-out(v)
        
        Args:
            vertex: 주소
        
        Returns:
            gather-scatter 값
        """
        return self.fan_in(vertex) + self.fan_out(vertex)
    
    def gather_scatter_count(self, vertex: str) -> int:
        """
        Gather-Scatter 개수: fan-in_count + fan-out_count
        
        Args:
            vertex: 주소
        
        Returns:
            총 연결 개수
        """
        return self.fan_in_count(vertex) + self.fan_out_count(vertex)
    
    def detect_fan_in_pattern(
        self,
        vertex: str,
        min_fan_in_count: int = 10,
        min_total_value: float = 0.1,   # ETH 단위 (USD ~300+)
        min_each_value: float = 0.01    # ETH 단위 (USD ~30+)
    ) -> Dict[str, Any]:
        """
        Fan-in 패턴 탐지 (B-204와 유사)
        
        여러 주소에서 하나의 주소로 자금이 집중되는 패턴
        
        Args:
            vertex: 분석 대상 주소
            min_fan_in_count: 최소 fan-in 개수
            min_total_value: 최소 총 유입 금액 (USD)
            min_each_value: 각 유입의 최소 금액 (USD)
        
        Returns:
            {
                "is_detected": bool,
                "fan_in_count": int,
                "total_value": float,
                "sources": List[str],
                "min_each_value": float
            }
        """
        if not self.graph or vertex.lower() not in self.graph:
            return {
                "is_detected": False,
                "fan_in_count": 0,
                "total_value": 0.0,
                "sources": [],
                "min_each_value": 0.0
            }
        
        vertex = vertex.lower()
        sources = []
        total_value = 0.0
        min_each = float('inf')
        
        for predecessor in self.graph.predecessors(vertex):
            edge_weight = self.graph[predecessor][vertex].get("weight", 0)
            if edge_weight >= min_each_value:
                sources.append(predecessor)
                total_value += edge_weight
                min_each = min(min_each, edge_weight)
        
        is_detected = (
            len(sources) >= min_fan_in_count and
            total_value >= min_total_value and
            min_each >= min_each_value
        )
        
        return {
            "is_detected": is_detected,
            "fan_in_count": len(sources),
            "total_value": total_value,
            "sources": sources,
            "min_each_value": min_each if min_each != float('inf') else 0.0
        }
    
    def detect_fan_out_pattern(
        self,
        vertex: str,
        min_fan_out_count: int = 10,
        min_total_value: float = 0.1,   # ETH 단위 (USD ~300+)
        min_each_value: float = 0.01    # ETH 단위 (USD ~30+)
    ) -> Dict[str, Any]:
        """
        Fan-out 패턴 탐지 (B-203와 유사)
        
        하나의 주소에서 여러 주소로 자금이 분산되는 패턴
        
        Args:
            vertex: 분석 대상 주소
            min_fan_out_count: 최소 fan-out 개수
            min_total_value: 최소 총 유출 금액 (USD)
            min_each_value: 각 유출의 최소 금액 (USD)
        
        Returns:
            {
                "is_detected": bool,
                "fan_out_count": int,
                "total_value": float,
                "targets": List[str],
                "min_each_value": float
            }
        """
        if not self.graph or vertex.lower() not in self.graph:
            return {
                "is_detected": False,
                "fan_out_count": 0,
                "total_value": 0.0,
                "targets": [],
                "min_each_value": 0.0
            }
        
        vertex = vertex.lower()
        targets = []
        total_value = 0.0
        min_each = float('inf')
        
        for successor in self.graph.successors(vertex):
            edge_weight = self.graph[vertex][successor].get("weight", 0)
            if edge_weight >= min_each_value:
                targets.append(successor)
                total_value += edge_weight
                min_each = min(min_each, edge_weight)
        
        is_detected = (
            len(targets) >= min_fan_out_count and
            total_value >= min_total_value and
            min_each >= min_each_value
        )
        
        return {
            "is_detected": is_detected,
            "fan_out_count": len(targets),
            "total_value": total_value,
            "targets": targets,
            "min_each_value": min_each if min_each != float('inf') else 0.0
        }
    
    def detect_stack_pattern(
        self,
        start_vertex: str,
        min_length: int = 3,
        min_path_value: float = 100.0
    ) -> List[Dict[str, Any]]:
        """
        Stack 패턴 탐지: directed path P = (v1, v2, ..., vk)
        
        Args:
            start_vertex: 시작 주소
            min_length: 최소 경로 길이
            min_path_value: 최소 경로 총 가치
        
        Returns:
            List of paths, each path is {
                "path": List[str],
                "length": int,
                "total_value": float
            }
        """
        if not self.graph or start_vertex.lower() not in self.graph:
            return []
        
        start_vertex = start_vertex.lower()
        detected_paths = []
        
        # DFS로 모든 경로 탐색
        def dfs(current: str, path: List[str], visited: Set[str], path_value: float):
            if len(path) >= min_length:
                if path_value >= min_path_value:
                    detected_paths.append({
                        "path": path.copy(),
                        "length": len(path),
                        "total_value": path_value
                    })
            
            if len(path) >= 10:  # 너무 긴 경로 방지
                return
            
            for successor in self.graph.successors(current):
                if successor not in visited:
                    edge_weight = self.graph[current][successor].get("weight", 0)
                    visited.add(successor)
                    path.append(successor)
                    dfs(successor, path, visited, path_value + edge_weight)
                    path.pop()
                    visited.remove(successor)
        
        dfs(start_vertex, [start_vertex], {start_vertex}, 0.0)
        
        return detected_paths
    
    def detect_bipartite_pattern(
        self,
        vertices: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Bipartite 패턴 탐지: ∀(u, v) ∈ E, u ∈ M_l ⇒ v ∈ M_{l+1}
        
        두 개의 레이어로 나뉘어진 그래프 구조
        
        Args:
            vertices: 분석할 주소 리스트 (None이면 전체 그래프)
        
        Returns:
            {
                "is_bipartite": bool,
                "layer1": Set[str],
                "layer2": Set[str],
                "edges_between_layers": int
            }
        """
        if not self.graph:
            return {
                "is_bipartite": False,
                "layer1": set(),
                "layer2": set(),
                "edges_between_layers": 0
            }
        
        if vertices is None:
            vertices = list(self.graph.nodes())
        else:
            vertices = [v.lower() for v in vertices]
        
        # NetworkX의 bipartite 체크
        try:
            # 서브그래프 생성
            subgraph = self.graph.subgraph(vertices)
            
            # 방향성 그래프를 무방향으로 변환하여 bipartite 체크
            undirected = subgraph.to_undirected()
            
            # NetworkX bipartite 체크
            if nx.is_bipartite(undirected):
                # 두 레이어 분리
                layer1, layer2 = nx.bipartite.sets(undirected)
                edges_between = sum(1 for u, v in subgraph.edges() 
                                   if (u in layer1 and v in layer2) or 
                                      (u in layer2 and v in layer1))
                
                return {
                    "is_bipartite": True,
                    "layer1": layer1,
                    "layer2": layer2,
                    "edges_between_layers": edges_between
                }
        except Exception:
            pass
        
        return {
            "is_bipartite": False,
            "layer1": set(),
            "layer2": set(),
            "edges_between_layers": 0
        }
    
    def analyze_address_patterns(self, vertex: str) -> Dict[str, Any]:
        """
        주소의 모든 패턴 분석
        
        Args:
            vertex: 분석 대상 주소
        
        Returns:
            {
                "fan_in": {...},
                "fan_out": {...},
                "gather_scatter": float,
                "stack_paths": [...],
                "bipartite": {...}
            }
        """
        return {
            "fan_in": {
                "value": self.fan_in(vertex),
                "count": self.fan_in_count(vertex),
                "pattern": self.detect_fan_in_pattern(vertex)
            },
            "fan_out": {
                "value": self.fan_out(vertex),
                "count": self.fan_out_count(vertex),
                "pattern": self.detect_fan_out_pattern(vertex)
            },
            "gather_scatter": {
                "value": self.gather_scatter(vertex),
                "count": self.gather_scatter_count(vertex)
            },
            "stack_paths": self.detect_stack_pattern(vertex),
            "bipartite": self.detect_bipartite_pattern([vertex])
        }

