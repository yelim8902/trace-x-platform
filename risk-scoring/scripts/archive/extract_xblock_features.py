#!/usr/bin/env python3
"""
XBlock MulDiGraph.pkl → 프로젝트 피처 JSON 변환 스크립트

기존 XBlock CSV(집계 테이블)와의 차별점:
  - 실제 그래프 구조에서 피처 추출 (집계값 아님)
  - 시간적 피처: inter_tx_interval_std, burst_score, active_days 등
  - 이웃 오염도 피처: 실제 PPR, phishing_neighbor_ratio 등
  - 기존 ppr_score 하드코딩(0.05) → 실제 그래프 기반 값으로 대체

사용법:
    cd risk-scoring
    python scripts/extract_xblock_features.py
    python scripts/extract_xblock_features.py --normal-sample 5000 --output data/dataset/xblock_graph_features.json
"""
import sys
import json
import argparse
import pickle
import random
import warnings
from pathlib import Path
from typing import Dict, List, Any, Set, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.aggregation.temporal_features import TemporalFeatureExtractor
from core.aggregation.neighborhood_features import NeighborhoodFeatureExtractor

warnings.filterwarnings("ignore")

XBLOCK_PICKLE = project_root / "data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl"
ETH_USD_APPROX = 1500.0   # XBlock 수집 시점(2015~2019) 평균 근사


def load_graph(path: Path):
    print(f"[로드] {path}  ({path.stat().st_size / 1e9:.2f} GB)")
    print("  ※ 1~2분 소요될 수 있습니다...")
    try:
        with open(path, "rb") as f:
            G = pickle.load(f)
        print(f"  노드: {G.number_of_nodes():,}  엣지: {G.number_of_edges():,}")
        return G
    except Exception as e:
        print(f"[오류] pickle 로드 실패: {e}")
        print("  Python 버전 비호환 시 'pip install networkx==2.8' 후 재시도")
        sys.exit(1)


def get_labeled_nodes(G) -> tuple[List[str], List[str]]:
    """피싱(isp=1) / 정상(isp=0) 노드 분리"""
    phishing, normal = [], []
    for node in G.nodes():
        label = G.nodes[node].get("isp", 0)
        if label == 1:
            phishing.append(node)
        else:
            normal.append(node)
    return phishing, normal


def get_node_timestamps(G, node: str) -> List[int]:
    """노드에 연결된 모든 엣지의 timestamp 수집"""
    timestamps = []
    # 나가는 엣지
    for _, _, data in G.out_edges(node, data=True):
        ts = data.get("timestamp", 0)
        if ts and ts > 0:
            timestamps.append(int(ts))
    # 들어오는 엣지
    for _, _, data in G.in_edges(node, data=True):
        ts = data.get("timestamp", 0)
        if ts and ts > 0:
            timestamps.append(int(ts))
    return timestamps


def get_node_amounts(G, node: str) -> Dict[str, float]:
    """노드의 송수신 총액 및 통계"""
    sent, received = [], []
    for _, _, data in G.out_edges(node, data=True):
        amt = float(data.get("amount", 0) or 0)
        if amt > 0:
            sent.append(amt)
    for _, _, data in G.in_edges(node, data=True):
        amt = float(data.get("amount", 0) or 0)
        if amt > 0:
            received.append(amt)

    all_amounts = sent + received
    return {
        "sent": sent,
        "received": received,
        "total_sent_eth":     sum(sent),
        "total_received_eth": sum(received),
        "avg_amount_eth":     sum(all_amounts) / max(len(all_amounts), 1),
        "max_amount_eth":     max(all_amounts) if all_amounts else 0.0,
    }


def extract_node_features(
    node: str,
    G,
    phishing_set: Set[str],
    temporal_extractor: TemporalFeatureExtractor,
    neighborhood_extractor: NeighborhoodFeatureExtractor,
) -> Dict[str, Any]:
    """단일 노드의 전체 피처 추출"""

    timestamps = get_node_timestamps(G, node)
    amounts    = get_node_amounts(G, node)

    in_deg  = G.in_degree(node)
    out_deg = G.out_degree(node)
    total_deg = in_deg + out_deg

    # ── 기본 그래프 피처 ─────────────────────────────────────────
    true_n_omega = out_deg / max(total_deg, 1)
    true_n_theta = min(1.0, total_deg / 1000.0)

    # ── 시간적 피처 ──────────────────────────────────────────────
    temporal = temporal_extractor.extract(timestamps)

    # ── 이웃 오염도 피처 ─────────────────────────────────────────
    neighborhood = neighborhood_extractor.extract(node, G, phishing_set)

    # ── 금액 통계 (ETH → USD 근사) ──────────────────────────────
    avg_tx_usd = amounts["avg_amount_eth"] * ETH_USD_APPROX
    max_tx_usd = amounts["max_amount_eth"] * ETH_USD_APPROX
    total_sent_usd     = amounts["total_sent_eth"]     * ETH_USD_APPROX
    total_received_usd = amounts["total_received_eth"] * ETH_USD_APPROX

    # fan-in/out count (MultiDiGraph은 multi-edge 가능 → edges 개수 사용)
    fan_in_count  = len(set(G.predecessors(node)))
    fan_out_count = len(set(G.successors(node)))

    # ── pattern_score: fan-in/out 불균형 + 이웃 오염도 복합 ─────
    imbalance = abs(fan_out_count - fan_in_count) / max(fan_in_count + fan_out_count, 1)
    pattern_score = min(100.0,
        imbalance * 30.0
        + neighborhood["phishing_exposure_score"] * 0.5
        + temporal["burst_score"] * 20.0
    )

    return {
        # 기본 그래프
        "fan_in_count":               fan_in_count,
        "fan_out_count":              fan_out_count,
        "tx_primary_fan_in_count":    in_deg,
        "tx_primary_fan_out_count":   out_deg,
        "tx_primary_fan_in_value":    round(total_received_usd, 2),
        "tx_primary_fan_out_value":   round(total_sent_usd, 2),
        "avg_transaction_value":      round(avg_tx_usd, 2),
        "max_transaction_value":      round(max_tx_usd, 2),
        "graph_nodes":                total_deg + 1,
        # 정규화 지수
        "n_omega":    round(true_n_omega, 6),
        "n_theta":    round(true_n_theta, 6),
        # 복합 패턴 점수
        "pattern_score": round(pattern_score, 4),
        # PPR (실제 그래프 기반, 이전 하드코딩 0.05 대체)
        "ppr_score":  round(neighborhood["true_ppr_score"], 6),
        # 신규: 시간적 피처
        "inter_tx_interval_std": round(temporal["inter_tx_interval_std"], 2),
        "burst_score":           round(temporal["burst_score"], 6),
        "active_days":           temporal["active_days"],
        "tx_density":            round(temporal["tx_density"], 4),
        "night_tx_ratio":        round(temporal["night_tx_ratio"], 6),
        # 신규: 이웃 오염도 피처
        "direct_phishing_neighbors": neighborhood["direct_phishing_neighbors"],
        "phishing_neighbor_ratio":   round(neighborhood["phishing_neighbor_ratio"], 6),
        "hop2_phishing_count":       neighborhood["hop2_phishing_count"],
        "hop2_phishing_ratio":       round(neighborhood["hop2_phishing_ratio"], 6),
        "phishing_exposure_score":   round(neighborhood["phishing_exposure_score"], 4),
    }


def build_sample(
    node: str,
    label: str,
    G,
    phishing_set: Set[str],
    temporal_extractor: TemporalFeatureExtractor,
    neighborhood_extractor: NeighborhoodFeatureExtractor,
) -> Optional[Dict[str, Any]]:
    """ablation_study.py 호환 샘플 dict 생성"""
    try:
        ml_features = extract_node_features(
            node, G, phishing_set, temporal_extractor, neighborhood_extractor
        )
    except Exception as e:
        return None

    total_txn = ml_features["tx_primary_fan_in_count"] + ml_features["tx_primary_fan_out_count"]

    return {
        "ground_truth_label": label,
        "address": node,
        "rule_score": 0.0,
        "tx_data": {
            "from": node,
            "to":   node,
            "usd_value": ml_features["avg_transaction_value"],
            "timestamp": 1700000000,
            "is_sanctioned": False,
            "is_mixer": False,
        },
        "ml_features": ml_features,
        "num_transactions": total_txn,
        "graph_nodes":  ml_features["graph_nodes"],
        "graph_edges":  total_txn,
    }


def main():
    parser = argparse.ArgumentParser(description="XBlock 그래프 → 프로젝트 피처 JSON")
    parser.add_argument("--graph",         default=str(XBLOCK_PICKLE))
    parser.add_argument("--output",        default="data/dataset/xblock_graph_features.json")
    parser.add_argument("--normal-sample", type=int, default=5000,
                        help="정상 노드 샘플 수 (기본 5000)")
    parser.add_argument("--min-degree",    type=int, default=3,
                        help="최소 degree (너무 작은 노드 제외)")
    parser.add_argument("--seed",          type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    G = load_graph(Path(args.graph))

    phishing_nodes, normal_nodes = get_labeled_nodes(G)
    phishing_set = set(phishing_nodes)
    print(f"  피싱 레이블: {len(phishing_nodes):,}  /  정상 레이블: {len(normal_nodes):,}")

    # 정상 노드: degree 필터링 후 샘플링
    normal_filtered = [n for n in normal_nodes if G.degree(n) >= args.min_degree]
    normal_sampled  = random.sample(normal_filtered, min(args.normal_sample, len(normal_filtered)))
    print(f"  degree≥{args.min_degree} 정상 노드: {len(normal_filtered):,}  →  샘플: {len(normal_sampled):,}")

    temporal_extractor     = TemporalFeatureExtractor()
    neighborhood_extractor = NeighborhoodFeatureExtractor()

    samples = []
    total = len(phishing_nodes) + len(normal_sampled)
    done  = 0

    print(f"\n[피처 추출 시작] 총 {total:,}개 노드")

    for node in phishing_nodes:
        s = build_sample(node, "fraud", G, phishing_set, temporal_extractor, neighborhood_extractor)
        if s:
            samples.append(s)
        done += 1
        if done % 200 == 0:
            print(f"  {done}/{total}  (fraud {len([x for x in samples if x['ground_truth_label']=='fraud'])})")

    for node in normal_sampled:
        s = build_sample(node, "normal", G, phishing_set, temporal_extractor, neighborhood_extractor)
        if s:
            samples.append(s)
        done += 1
        if done % 1000 == 0:
            print(f"  {done}/{total}")

    fraud_n  = sum(1 for s in samples if s["ground_truth_label"] == "fraud")
    normal_n = len(samples) - fraud_n
    print(f"\n[완료] fraud: {fraud_n:,}  normal: {normal_n:,}  합계: {len(samples):,}")

    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)
    print(f"[저장] {output_path}")
    print()
    print("다음 단계:")
    print(f"  python scripts/ablation_study.py --data {args.output}")


if __name__ == "__main__":
    main()
