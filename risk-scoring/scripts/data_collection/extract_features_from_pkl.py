"""
MulDiGraph.pkl → 학습 데이터 추출 스크립트

XBlock EPTransNet 그래프에서 각 주소의 피처를 추출하여
ablation_study.py / train_stage2_scorer.py 가 사용할 수 있는
JSON 형식으로 저장.

실행 (AWS r5.xlarge 권장):
    python scripts/extract_features_from_pkl.py
    python scripts/extract_features_from_pkl.py --normal-samples 5000
    python scripts/extract_features_from_pkl.py \
        --input data/xblock/Ethereum\ Phishing\ Transaction\ Network/MulDiGraph.pkl \
        --output data/dataset/xblock_extracted.json
"""

import sys
import json
import pickle
import argparse
import random
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

ETH_TO_USD = 1500.0  # 데이터 수집 시점(2017~2019) 근사 환율


def load_graph(pkl_path: Path):
    print(f"📂 그래프 로딩 중: {pkl_path}")
    print("   (메모리 8~15GB 사용, 수 분 소요)")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)
    print(f"   ✅ 로드 완료 — 노드 {G.number_of_nodes():,}개 / 엣지 {G.number_of_edges():,}개")
    return G


def extract_node_features(G, node) -> dict:
    """단일 노드의 피처 추출"""

    # 수신 엣지 (다른 노드 → 이 노드)
    in_edges = list(G.in_edges(node, data=True))
    # 발신 엣지 (이 노드 → 다른 노드)
    out_edges = list(G.out_edges(node, data=True))

    # fan-in / fan-out (고유 상대방 수)
    fan_in  = len(set(u for u, _, _ in in_edges))
    fan_out = len(set(v for _, v, _ in out_edges))

    # 금액 집계 (ETH → USD)
    def amounts(edges, direction="out"):
        vals = []
        for u, v, data in edges:
            for key in data:  # MultiDiGraph: 동일 노드 쌍에 여러 엣지 가능
                edge_data = G[u][v][key] if direction == "out" else data
                amt = edge_data.get("amount", 0) if isinstance(edge_data, dict) else 0
                if amt and amt > 0:
                    vals.append(float(amt) * ETH_TO_USD)
        return vals

    sent_usd_list = []
    for _, v, data in out_edges:
        for key in G[node][v]:
            amt = G[node][v][key].get("amount", 0)
            if amt and float(amt) > 0:
                sent_usd_list.append(float(amt) * ETH_TO_USD)

    recv_usd_list = []
    for u, _, data in in_edges:
        for key in G[u][node]:
            amt = G[u][node][key].get("amount", 0)
            if amt and float(amt) > 0:
                recv_usd_list.append(float(amt) * ETH_TO_USD)

    total_sent = sum(sent_usd_list)
    total_recv = sum(recv_usd_list)
    avg_sent   = total_sent / len(sent_usd_list) if sent_usd_list else 0
    avg_recv   = total_recv / len(recv_usd_list) if recv_usd_list else 0
    max_sent   = max(sent_usd_list) if sent_usd_list else 0
    max_recv   = max(recv_usd_list) if recv_usd_list else 0
    avg_tx_usd = (avg_sent + avg_recv) / 2
    max_tx_usd = max(max_sent, max_recv)

    # 타임스탬프 기반 피처
    timestamps = []
    for u, v, data in in_edges + out_edges:
        for key in (G[u][v] if (u, v) != (node, node) else G[node][node]):
            ts = G[u][v][key].get("timestamp", 0) if (u != node or v != node) else 0
            if ts:
                timestamps.append(int(ts))
    timestamps = sorted(set(timestamps))

    total_txn = len(sent_usd_list) + len(recv_usd_list)

    # n_omega: 송신 방향 편향 (0=수신 전용, 1=송신 전용)
    denom  = fan_in + fan_out
    n_omega = (fan_out / denom) if denom > 0 else 0.5

    # n_theta: 거래 활성도 (1000건 기준 정규화)
    n_theta = min(total_txn / 1000.0, 1.0)

    # pattern_score: fan-out 편향 이상 점수 (0~100)
    imbalance    = abs(fan_out - fan_in) / max(denom, 1)
    fanout_ratio = fan_out / max(total_txn, 1)
    pattern_score = min(100.0, imbalance * 40 + fanout_ratio * 60)

    # graph_nodes: 1-hop 이웃 수
    neighbors = set(v for _, v, _ in out_edges) | set(u for u, _, _ in in_edges)
    graph_nodes = len(neighbors) + 1
    graph_edges = total_txn

    return {
        "fan_in_count":            fan_in,
        "fan_out_count":           fan_out,
        "pattern_score":           round(pattern_score, 4),
        "n_omega":                 round(n_omega, 4),
        "n_theta":                 round(n_theta, 4),
        "ppr_score":               0.05,        # 그래프 전체 PPR 연산은 OOM 위험 → 근사값
        "graph_nodes":             graph_nodes,
        "graph_edges":             graph_edges,
        "tx_primary_fan_in_count": len(recv_usd_list),
        "tx_primary_fan_out_count":len(sent_usd_list),
        "avg_tx_usd":              round(avg_tx_usd, 2),
        "max_tx_usd":              round(max_tx_usd, 2),
        "total_sent_usd":          round(total_sent, 2),
        "total_recv_usd":          round(total_recv, 2),
        "tx_data": {
            "from":       str(node),
            "to":         str(node),
            "usd_value":  round(avg_tx_usd, 2),
            "timestamp":  timestamps[-1] if timestamps else 1700000000,
            "is_sanctioned": False,
            "is_mixer":      False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl",
    )
    parser.add_argument("--output", default="data/dataset/xblock_extracted.json")
    parser.add_argument("--normal-samples", type=int, default=5000,
                        help="정상 주소 샘플 수 (피싱은 전체 1,165개 사용)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    pkl_path = project_root / args.input
    out_path = project_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)

    G = load_graph(pkl_path)

    # 노드 분류
    fraud_nodes  = [n for n, d in G.nodes(data=True) if d.get("isp", 0) == 1]
    normal_nodes = [n for n, d in G.nodes(data=True) if d.get("isp", 0) == 0]

    print(f"\n📊 레이블 분포")
    print(f"   피싱(fraud):  {len(fraud_nodes):,}개 (전체 사용)")
    print(f"   정상(normal): {len(normal_nodes):,}개 → {args.normal_samples:,}개 샘플링")

    sampled_normal = random.sample(normal_nodes, min(args.normal_samples, len(normal_nodes)))
    target_nodes   = [(n, "fraud") for n in fraud_nodes] + \
                     [(n, "normal") for n in sampled_normal]
    random.shuffle(target_nodes)

    results = []
    total = len(target_nodes)
    for i, (node, label) in enumerate(target_nodes):
        if i % 100 == 0:
            print(f"   {i}/{total} 처리 중...", end="\r")
        try:
            features = extract_node_features(G, node)
            features["address"]             = str(node)
            features["ground_truth_label"]  = label
            results.append(features)
        except Exception as e:
            pass  # 엣지 없는 고립 노드 스킵

    print(f"\n✅ 추출 완료: {len(results):,}개 샘플")
    fraud_count  = sum(1 for r in results if r["ground_truth_label"] == "fraud")
    normal_count = sum(1 for r in results if r["ground_truth_label"] == "normal")
    print(f"   fraud: {fraud_count}, normal: {normal_count}")

    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"💾 저장: {out_path}")
    print(f"\n다음 단계:")
    print(f"  python scripts/train_stage2_scorer.py")
    print(f"  python scripts/ablation_study.py")


if __name__ == "__main__":
    main()
