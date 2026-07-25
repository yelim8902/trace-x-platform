"""
Peel Chain 탐지

큰 금액이 들어온 뒤, 매 홉마다 소액을 떼어내고(peel) 남은 금액을
새 주소로 계속 전달하는 자금세탁 패턴. 비트코인 도난 사건의 약 70%에서
나타나는 대표 기법 (Chainalysis, Merkle Science, AMLTRIX 문서 참고 —
docs/DOMAIN_RESEARCH.md).

B-201(Layering Chain, topology.py)과 반대되는 금액 조건을 씀 — B-201은
각 홉 금액이 서로 ±5% 이내로 "비슷해야" 발동하는데, peel chain은 정의상
매 홉 금액이 "계속 줄어들어야" 함. 그래서 B-201은 peel chain을 못 잡음.
"""

from typing import Any, Dict, List

import networkx as nx


def _path_is_decaying(
    weights: List[float],
    min_decay_pct: float,
    max_decay_pct: float,
) -> bool:
    """
    연속된 홉의 금액이 [이전 금액 * min_decay_pct, 이전 금액 * max_decay_pct]
    구간 안에서 계속 줄어드는지 확인.

    min_decay_pct=0.5, max_decay_pct=0.95면: 매 홉마다 이전 금액의 50~95%만
    남아 다음 홉으로 전달됨(즉 5~50%가 매 홉 peel됨). 너무 급격히 줄면(<50%)
    peel이라기보단 그냥 다른 거래일 가능성이 크고, 너무 안 줄면(>95%) B-201의
    "비슷한 금액" 영역과 겹쳐서 구분이 안 됨.
    """
    if len(weights) < 2:
        return False
    for prev, cur in zip(weights, weights[1:]):
        if prev <= 0:
            return False
        ratio = cur / prev
        if not (min_decay_pct <= ratio <= max_decay_pct):
            return False
    return True


def find_peel_chains(
    graph: nx.DiGraph,
    start: str,
    min_hops: int = 2,
    min_decay_pct: float = 0.3,
    max_decay_pct: float = 0.97,
    min_start_value: float = 100.0,
    max_search_depth: int = 10,
) -> List[Dict[str, Any]]:
    """
    start 주소에서 시작하는 peel chain을 DFS로 탐색.

    Args:
        graph: networkx DiGraph, 엣지에 weight(usd_value) 속성 필요
        start: 탐색 시작 주소 (소문자)
        min_hops: 최소 홉 수 (기본 3 — 그 이하는 우연의 일치일 가능성이 큼)
        min_decay_pct / max_decay_pct: 홉 간 금액 유지 비율 허용 구간
        min_start_value: 체인 시작 금액 최소값 (너무 작은 금액의 우연한 감소는 제외)
        max_search_depth: DFS 최대 깊이 (무한 루프 방지)

    Returns:
        발견된 체인들의 리스트. 각 체인: {"path": [...], "weights": [...], "length": int}
    """
    if start not in graph:
        return []

    start = start.lower()
    detected: List[Dict[str, Any]] = []

    def dfs(current: str, path: List[str], weights: List[float], visited: set):
        if len(path) >= min_hops + 1 and _path_is_decaying(weights, min_decay_pct, max_decay_pct):
            detected.append({
                "path": path.copy(),
                "weights": weights.copy(),
                "length": len(path) - 1,
            })
            # 더 긴 체인도 볼 수 있게 여기서 return하지 않고 계속 탐색

        if len(path) - 1 >= max_search_depth:
            return

        for successor in graph.successors(current):
            if successor in visited:
                continue
            edge_weight = graph[current][successor].get("weight", 0)
            if edge_weight <= 0:
                continue
            if not weights and edge_weight < min_start_value:
                continue
            visited.add(successor)
            path.append(successor)
            weights.append(edge_weight)
            dfs(successor, path, weights, visited)
            path.pop()
            weights.pop()
            visited.remove(successor)

    dfs(start, [start], [], {start})
    return detected


def peel_chain_score(
    graph: nx.DiGraph,
    start: str,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    ML 피처용 스칼라 점수로 요약.

    Returns:
        {
            "peel_chain_detected": bool,
            "peel_chain_max_length": int,   # 가장 긴 체인의 홉 수
            "peel_chain_count": int,        # 발견된 체인 개수
        }
    """
    chains = find_peel_chains(graph, start, **kwargs)
    if not chains:
        return {
            "peel_chain_detected": False,
            "peel_chain_max_length": 0,
            "peel_chain_count": 0,
        }
    return {
        "peel_chain_detected": True,
        "peel_chain_max_length": max(c["length"] for c in chains),
        "peel_chain_count": len(chains),
    }
