"""
6단계(모델 학습) 준비 — XBlock train/val 각 주소에 대해 최종 ML 피처 매트릭스를 구성.

포함하는 것:
- 기존 그래프 통계(xblock_extracted.json에 이미 있던 것): fan_in_count, fan_out_count,
  pattern_score, n_omega, n_theta, graph_nodes, graph_edges, avg_tx_usd, max_tx_usd,
  total_sent_usd, total_recv_usd
- 신규 검증된 피처 3개: peel_chain_score, amount_deviation_score, frequency_deviation_score

제외하는 것 (게이팅 룰로 이동, ML 피처 아님): sanction_hop_distance, mixer_hop_distance,
privacy_protocol_involved — XBlock에서 전부 상수 0이라 학습 신호가 없음 (docs/FEATURE_ENGINEERING.md)

실행:
    python3 scripts/build_feature_matrix.py --split train
    python3 scripts/build_feature_matrix.py --split val
"""
import argparse
import json
import pickle
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.aggregation.deviation_features import deviation_features
from core.aggregation.peel_chain import peel_chain_score
from core.aggregation.subgraph_utils import build_bounded_subgraph

EXISTING_GRAPH_STAT_FIELDS = [
    "fan_in_count", "fan_out_count", "pattern_score", "n_omega", "n_theta",
    "graph_nodes", "graph_edges", "avg_tx_usd", "max_tx_usd", "total_sent_usd", "total_recv_usd",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=["train", "val", "test"])
    parser.add_argument("--graph", default="data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl")
    args = parser.parse_args()

    if args.split == "test":
        print("⚠️  7단계(최종 평가) 진입 — test set feature matrix를 최초로 생성함. 이후 평가는 딱 한 번만 수행할 것.")

    extracted_path = project_root / f"data/dataset/xblock_split_{args.split}_extracted.json"
    tx_path = project_root / f"data/dataset/xblock_split_{args.split}_transactions.json"
    extracted = {r["address"]: r for r in json.load(open(extracted_path))}
    tx_data = {r["address"]: r for r in json.load(open(tx_path))}

    print(f"그래프 로딩 중 (peel_chain_score 계산용)...")
    t0 = time.time()
    with open(project_root / args.graph, "rb") as f:
        G = pickle.load(f)
    print(f"  로드 완료 ({time.time()-t0:.0f}s)")

    addresses = list(extracted.keys())
    t0 = time.time()
    rows = []
    for i, addr in enumerate(addresses):
        ext = extracted[addr]
        tx = tx_data.get(addr, {"sent": [], "received": []})

        sub = build_bounded_subgraph(G, addr, direction="out")
        peel = peel_chain_score(sub, addr)
        dev = deviation_features(tx["sent"], tx["received"])

        row = {"address": addr, "ground_truth_label": ext["ground_truth_label"]}
        for field in EXISTING_GRAPH_STAT_FIELDS:
            row[field] = ext.get(field)
        row["peel_chain_max_length"] = peel["peel_chain_max_length"]
        row["peel_chain_count"] = peel["peel_chain_count"]
        row["amount_deviation_score"] = dev["amount_deviation_score"]
        row["frequency_deviation_score"] = dev["frequency_deviation_score"]
        rows.append(row)

        if (i + 1) % 500 == 0 or i == len(addresses) - 1:
            print(f"  {i+1}/{len(addresses)} ({time.time()-t0:.0f}s)")

    out_path = project_root / f"data/dataset/feature_matrix_{args.split}.json"
    json.dump(rows, open(out_path, "w"))
    print(f"저장: {out_path} ({len(rows)}개 행)")


if __name__ == "__main__":
    main()
