"""
XBlock MulDiGraph.pkl → 개별 트랜잭션 리스트 추출

기존 extract_features_from_pkl.py는 집계값만 뽑아서
시간 윈도우 룰(B-101, B-203, B-504 등)을 평가할 수 없었음.
이 스크립트는 각 주소의 개별 트랜잭션(타임스탬프 포함)을 추출.

실행 (AWS r5.xlarge):
    python3 extract_txs_for_rules.py \
        --input MulDiGraph.pkl \
        --addresses xblock_extracted.json \
        --output xblock_transactions.json
"""

import sys
import json
import pickle
import argparse
from pathlib import Path

ETH_TO_USD = 1500.0
MAX_TXS_PER_ADDRESS = 500  # 주소당 최대 트랜잭션 수 (메모리 제한)


def load_graph(pkl_path: Path):
    print(f"📂 그래프 로딩 중: {pkl_path}")
    with open(pkl_path, "rb") as f:
        G = pickle.load(f)
    print(f"   ✅ 노드 {G.number_of_nodes():,}개 / 엣지 {G.number_of_edges():,}개")
    return G


def extract_transactions(G, node) -> dict:
    """주소의 개별 송수신 트랜잭션 리스트 추출"""
    sent = []
    received = []

    for _, v, _ in G.out_edges(node, data=True):
        for key in G[node][v]:
            d = G[node][v][key]
            amt = d.get("amount", 0)
            ts = d.get("timestamp", 0)
            if amt and float(amt) > 0 and ts:
                sent.append({
                    "to": str(v),
                    "usd": round(float(amt) * ETH_TO_USD, 2),
                    "ts": int(ts),
                })

    for u, _, _ in G.in_edges(node, data=True):
        for key in G[u][node]:
            d = G[u][node][key]
            amt = d.get("amount", 0)
            ts = d.get("timestamp", 0)
            if amt and float(amt) > 0 and ts:
                received.append({
                    "from": str(u),
                    "usd": round(float(amt) * ETH_TO_USD, 2),
                    "ts": int(ts),
                })

    # 타임스탬프 정렬, 최대 수 제한
    sent = sorted(sent, key=lambda x: x["ts"])[:MAX_TXS_PER_ADDRESS]
    received = sorted(received, key=lambda x: x["ts"])[:MAX_TXS_PER_ADDRESS]

    return {"sent": sent, "received": received}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="MulDiGraph.pkl")
    parser.add_argument("--addresses", default="xblock_extracted.json",
                        help="xblock_extracted.json (대상 주소 목록)")
    parser.add_argument("--output", default="xblock_transactions.json")
    args = parser.parse_args()

    # 대상 주소 로드
    with open(args.addresses) as f:
        samples = json.load(f)
    target_addresses = {s["address"]: s["ground_truth_label"] for s in samples}
    print(f"📋 대상 주소: {len(target_addresses):,}개")

    G = load_graph(Path(args.input))

    results = []
    total = len(target_addresses)
    for i, (addr, label) in enumerate(target_addresses.items()):
        if i % 200 == 0:
            print(f"   {i}/{total} 처리 중...", end="\r")
        try:
            txs = extract_transactions(G, addr)
            results.append({
                "address": addr,
                "ground_truth_label": label,
                **txs,
            })
        except Exception:
            results.append({
                "address": addr,
                "ground_truth_label": label,
                "sent": [],
                "received": [],
            })

    with open(args.output, "w") as f:
        json.dump(results, f)

    print(f"\n✅ 완료: {len(results):,}개 → {args.output}")
    fraud = sum(1 for r in results if r["ground_truth_label"] == "fraud")
    print(f"   fraud: {fraud}, normal: {len(results)-fraud}")


if __name__ == "__main__":
    main()
