"""
제재/믹서 리스트까지의 hop 거리 기반 노출 점수.

Elliptic/TRM Labs/Scorechain 등 실무 스크리닝 도구의 공통 관행:
직접 접촉(1-hop)은 강한 신호, 2-hop 이상은 감쇠된 약한 신호로 처리.
(docs/DOMAIN_RESEARCH.md "발견 1" 참고)

지금 룰북의 E-102(간접 제재 노출)는 PPR 기반 이진 판정만 있어서,
"몇 hop인지"에 따라 연속적으로 grade하는 이 피처와는 역할이 다름.
"""

from typing import Any, Dict, Optional, Set

import networkx as nx


def hop_distance_to_any(graph: nx.DiGraph, start: str, targets: Set[str]) -> Optional[int]:
    """
    start에서 targets(주소 집합) 중 아무 곳으로든 도달하는 최단 hop 거리.
    방향 무관(자금이 어느 방향으로 흘렀든 노출은 노출) — undirected로 계산.

    targets가 클 수 있으므로(SDN 리스트 등), 작은 쪽(도달 가능한 서브그래프
    노드들)을 순회하며 멤버십 체크하는 방향으로 구현 — O(subgraph) 시간.
    """
    if start not in graph:
        return None
    start = start.lower()
    undirected = graph.to_undirected()
    if start not in undirected:
        return None

    lengths = nx.single_source_shortest_path_length(undirected, start)
    candidates = [dist for node, dist in lengths.items() if node in targets]
    return min(candidates) if candidates else None


def exposure_score_from_hops(
    hops: Optional[int],
    hop0_score: float = 100.0,
    decay: float = 0.4,
    max_useful_hops: int = 5,
) -> float:
    """
    hop 거리를 0~100 감쇠 점수로 변환.
    decay=0.4 기준: hop0=100, hop1=40, hop2=16, hop3=6.4, hop4=2.56...
    max_useful_hops를 넘으면 0 (너무 멀면 노출로 안 봄).
    """
    if hops is None or hops > max_useful_hops:
        return 0.0
    return hop0_score * (decay ** hops)


def exposure_features(
    graph: nx.DiGraph,
    start: str,
    sdn_list: Set[str],
    mixer_list: Set[str],
    **kwargs: Any,
) -> Dict[str, Any]:
    """ML 피처용 요약 — sanction/mixer 각각의 hop 거리 + 감쇠 점수."""
    sanction_hops = hop_distance_to_any(graph, start, sdn_list)
    mixer_hops = hop_distance_to_any(graph, start, mixer_list)
    return {
        "sanction_hop_distance": sanction_hops if sanction_hops is not None else -1,
        "sanction_exposure_score": exposure_score_from_hops(sanction_hops, **kwargs),
        "mixer_hop_distance": mixer_hops if mixer_hops is not None else -1,
        "mixer_exposure_score": exposure_score_from_hops(mixer_hops, **kwargs),
    }
