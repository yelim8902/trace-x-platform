"""
이웃 오염도(Neighborhood Contamination) 피처 추출 모듈 (신규)

연구 근거:
- Chen et al. IJCAI 2020: 피싱 주소는 알려진 사기 주소 클러스터 내에 위치
- Elliptic++ (KDD 2023): 2-hop 이웃의 레이블 전파가 GNN 성능의 핵심
- GrabPhisher (IEEE 2024): 직접 이웃의 오염도가 단일 최강 피처

기존 XBlock 집계 테이블의 한계:
  - 이웃 주소의 레이블 정보가 전혀 없음 (단순 개수만 존재)
  - 이 모듈은 실제 그래프 구조를 활용해 오염 전파를 정량화

추출 피처:
    direct_phishing_neighbors : 직접 연결된 피싱 주소 수
    phishing_neighbor_ratio   : 직접 이웃 중 피싱 비율 (0~1)
    hop2_phishing_count       : 2-hop 이내 피싱 주소 수 (중복 제거)
    hop2_phishing_ratio       : 2-hop 이웃 중 피싱 비율 (0~1)
    phishing_exposure_score   : 1/2-hop 가중 오염 점수 (0~100)
    true_ppr_score            : 실제 그래프 기반 PPR (이전 하드코딩 0.05 대체)
"""

from typing import Dict, Any, Set, Optional
import networkx as nx


class NeighborhoodFeatureExtractor:
    """NetworkX 그래프 기반 이웃 오염도 피처 추출기"""

    # 1-hop vs 2-hop 가중치
    HOP1_WEIGHT = 0.7
    HOP2_WEIGHT = 0.3

    # PPR 하이퍼파라미터
    PPR_ALPHA   = 0.85
    PPR_MAX_ITER = 50   # 로컬 서브그래프는 수렴이 빠름

    # ── 공개 API ──────────────────────────────────────────────────

    def extract(
        self,
        target: str,
        graph: nx.MultiDiGraph,
        phishing_set: Set[str],
    ) -> Dict[str, float]:
        """
        target 노드의 이웃 오염도 피처를 추출한다.

        Args:
            target      : 분석 대상 주소 (소문자)
            graph       : XBlock MultiDiGraph (전체 또는 서브그래프)
            phishing_set: 알려진 피싱 주소 집합

        Returns:
            {
                "direct_phishing_neighbors": float,
                "phishing_neighbor_ratio"  : float,
                "hop2_phishing_count"      : float,
                "hop2_phishing_ratio"      : float,
                "phishing_exposure_score"  : float,
                "true_ppr_score"           : float,
            }
        """
        defaults = {
            "direct_phishing_neighbors": 0.0,
            "phishing_neighbor_ratio":   0.0,
            "hop2_phishing_count":       0.0,
            "hop2_phishing_ratio":       0.0,
            "phishing_exposure_score":   0.0,
            "true_ppr_score":            0.05,  # 기존 하드코딩 기본값 유지
        }

        if target not in graph:
            return defaults

        # 1-hop 이웃 (방향 무관 = 직접 연결 전체)
        hop1 = set(graph.predecessors(target)) | set(graph.successors(target))
        hop1.discard(target)

        hop1_phishing = hop1 & phishing_set
        hop1_ratio = len(hop1_phishing) / max(len(hop1), 1)

        # 2-hop 이웃 (1-hop 이웃의 이웃, 1-hop 제외)
        hop2 = set()
        for nb in hop1:
            hop2 |= set(graph.predecessors(nb)) | set(graph.successors(nb))
        hop2 -= hop1
        hop2.discard(target)

        hop2_phishing = hop2 & phishing_set
        hop2_ratio = len(hop2_phishing) / max(len(hop2), 1)

        # 가중 오염 점수 (0~100)
        exposure = min(100.0, (
            self.HOP1_WEIGHT * hop1_ratio +
            self.HOP2_WEIGHT * hop2_ratio
        ) * 100.0)

        # 실제 PPR (로컬 서브그래프 기반)
        ppr = self._local_ppr(target, graph, phishing_set)

        return {
            "direct_phishing_neighbors": float(len(hop1_phishing)),
            "phishing_neighbor_ratio":   round(hop1_ratio, 6),
            "hop2_phishing_count":       float(len(hop2_phishing)),
            "hop2_phishing_ratio":       round(hop2_ratio, 6),
            "phishing_exposure_score":   round(exposure, 4),
            "true_ppr_score":            round(ppr, 6),
        }

    # ── 내부 계산 ─────────────────────────────────────────────────

    def _local_ppr(
        self,
        target: str,
        graph: nx.MultiDiGraph,
        phishing_set: Set[str],
        hop: int = 2,
    ) -> float:
        """
        target 주변 ego 서브그래프에서 Multi-source PPR 계산.

        기존 ppr_connector.py는 라이브 API 그래프를 대상으로 하지만,
        이 메서드는 XBlock의 실제 그래프를 사용해 정확한 값을 제공.

        피싱 노드들을 personalization seed로 사용하는 방식은
        MPOCryptoML 논문의 Algorithm 1 (Multi-source PPR)과 동일.
        """
        # ego 서브그래프 추출 (hop 반경)
        try:
            ego = nx.ego_graph(graph, target, radius=hop, undirected=True)
        except Exception:
            return 0.05

        if ego.number_of_nodes() < 3:
            return 0.05

        # 단순 DiGraph으로 변환 (MultiDiGraph → DiGraph, 가중치 합산)
        dg = nx.DiGraph()
        for u, v, data in ego.edges(data=True):
            w = float(data.get("amount", 1.0))
            if dg.has_edge(u, v):
                dg[u][v]["weight"] += w
            else:
                dg.add_edge(u, v, weight=w)

        sources_in_ego = [n for n in dg.nodes() if n in phishing_set and n != target]
        if not sources_in_ego:
            return 0.0

        # personalization: 피싱 노드에 균등 확률 배분
        personalization = {n: 0.0 for n in dg.nodes()}
        for s in sources_in_ego:
            personalization[s] = 1.0 / len(sources_in_ego)

        try:
            ppr_scores = nx.pagerank(
                dg,
                alpha=self.PPR_ALPHA,
                personalization=personalization,
                max_iter=self.PPR_MAX_ITER,
                weight="weight",
            )
            return ppr_scores.get(target, 0.0)
        except Exception:
            return 0.0

    # ── 스코어 변환 (Stage1Scorer 연동용) ─────────────────────────

    def neighborhood_risk_score(self, features: Dict[str, float]) -> float:
        """
        이웃 오염도 피처 → 0~100 위험 점수 변환.

        가중치 근거:
          true_ppr_score(40)          : 실제 그래프 기반 오염 전파 (핵심)
          phishing_exposure_score(30) : 1+2-hop 복합 오염
          direct_phishing(20)         : 직접 접촉
          hop2_phishing_ratio(10)     : 간접 오염
        """
        score = 0.0

        # 1) 실제 PPR 기반 점수
        ppr = features.get("true_ppr_score", features.get("ppr_score", 0.0))
        if ppr >= 0.15:
            score += 40.0
        elif ppr >= 0.08:
            score += 25.0
        elif ppr >= 0.03:
            score += 12.0

        # 2) 복합 오염 노출 점수
        exposure = features.get("phishing_exposure_score", 0.0)
        if exposure >= 50.0:
            score += 30.0
        elif exposure >= 20.0:
            score += 18.0
        elif exposure >= 5.0:
            score += 8.0

        # 3) 직접 피싱 이웃
        direct = features.get("direct_phishing_neighbors", 0.0)
        if direct >= 3:
            score += 20.0
        elif direct >= 1:
            score += 12.0

        # 4) 2-hop 간접 오염
        hop2_ratio = features.get("hop2_phishing_ratio", 0.0)
        if hop2_ratio >= 0.3:
            score += 10.0
        elif hop2_ratio >= 0.1:
            score += 5.0

        return min(100.0, score)
