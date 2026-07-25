"""
원본 그래프(networkx MultiDiGraph, 예: XBlock MulDiGraph.pkl)에서
주소 하나를 기준으로 depth/breadth 제한된 BFS 서브그래프를 뽑는 공용 유틸.

peel_chain(출금 방향만 필요)과 exposure_distance(양방향 필요) 둘 다 이걸 씀.
"""

from typing import Literal

import networkx as nx

ETH_TO_USD = 1500.0  # 데이터 수집 시점(2017~2019) 근사 환율 — 기존 추출 스크립트와 동일

DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_BREADTH = 5   # 노드당 최대 이웃 수 (가중치 상위 N개만)
DEFAULT_MAX_NODES = 300   # 서브그래프 최대 노드 수 (안전장치)


def _top_neighbors(G, node: str, edge_dir: Literal["out", "in"], max_breadth: int):
    """가중치(usd 환산) 상위 max_breadth개 이웃만 반환."""
    neighbors = G.successors(node) if edge_dir == "out" else G.predecessors(node)
    candidates = []
    for nbr in neighbors:
        edges = G[node][nbr] if edge_dir == "out" else G[nbr][node]
        for key in edges:
            amt = edges[key].get("amount", 0)
            if amt and float(amt) > 0:
                candidates.append((nbr, float(amt) * ETH_TO_USD))
                break  # 병렬 엣지 중 첫 값만 (속도 위해 단순화)
    candidates.sort(key=lambda x: -x[1])
    return candidates[:max_breadth]


def build_bounded_subgraph(
    G,
    start: str,
    direction: Literal["out", "both"] = "out",
    max_depth: int = DEFAULT_MAX_DEPTH,
    max_breadth: int = DEFAULT_MAX_BREADTH,
    max_nodes: int = DEFAULT_MAX_NODES,
) -> nx.DiGraph:
    """
    start에서 출발해 depth/breadth 제한된 BFS로 서브그래프 구성.

    Args:
        direction: "out"이면 successor(출금) 방향만, "both"면 predecessor(입금)도 포함
    """
    sub = nx.DiGraph()
    if start not in G:
        return sub

    frontier = [(start, 0)]
    visited = {start}

    while frontier and len(visited) < max_nodes:
        node, depth = frontier.pop(0)
        if depth >= max_depth:
            continue

        edge_dirs = ["out"] if direction == "out" else ["out", "in"]

        for edge_dir in edge_dirs:
            for nbr, usd in _top_neighbors(G, node, edge_dir, max_breadth):
                if edge_dir == "out":
                    sub.add_edge(node, nbr, weight=usd)
                else:
                    sub.add_edge(nbr, node, weight=usd)
                if nbr not in visited:
                    visited.add(nbr)
                    if len(visited) < max_nodes:
                        frontier.append((nbr, depth + 1))

    return sub
