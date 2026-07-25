"""
MulDiGraph.pkl에서 주소별 멀티홉 이웃 서브그래프를 뽑아 peel_chain_score를 계산.

xblock_transactions.json(1홉만 있음)으로는 peel chain(여러 홉 필요)을
검증할 수 없어서, 원본 그래프에서 직접 depth/breadth 제한된 BFS로
서브그래프를 만들고 그 위에서 peel chain을 탐색한다.

실행:
    python3 scripts/extract_peel_chain_features.py --limit 20          # 속도 테스트
    python3 scripts/extract_peel_chain_features.py --split train       # 전체 train
"""
import argparse
import json
import pickle
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.aggregation.subgraph_utils import build_bounded_subgraph  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl")
    parser.add_argument("--manifest", default="data/dataset/split_manifest_train.txt")
    parser.add_argument("--output", default="data/dataset/peel_chain_train.json")
    parser.add_argument("--limit", type=int, default=None, help="테스트용 — 앞에서 N개 주소만")
    args = parser.parse_args()

    from core.aggregation.peel_chain import peel_chain_score

    print("그래프 로딩 중...")
    t0 = time.time()
    with open(project_root / args.input, "rb") as f:
        G = pickle.load(f)
    print(f"  로드 완료 ({time.time()-t0:.0f}s) — 노드 {G.number_of_nodes():,} / 엣지 {G.number_of_edges():,}")

    addresses = []
    with open(project_root / args.manifest) as f:
        for line in f:
            addr, label = line.strip().split(",")
            addresses.append((addr, label))

    if args.limit:
        addresses = addresses[:args.limit]

    results = []
    t0 = time.time()
    for i, (addr, label) in enumerate(addresses):
        sub = build_bounded_subgraph(G, addr)
        score = peel_chain_score(sub, addr)  # 검증된 기본값 사용 (min_hops=2, decay 0.3~0.97) — docs/FEATURE_ENGINEERING.md
        results.append({"address": addr, "label": label, "subgraph_nodes": sub.number_of_nodes(), **score})
        if (i + 1) % 10 == 0 or i == len(addresses) - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{len(addresses)}  ({elapsed:.1f}s, {rate:.2f}개/s, 예상 전체 소요 {len(addresses)/rate:.0f}s)", end="\r")

    print()
    out_path = project_root / args.output
    json.dump(results, open(out_path, "w"))
    print(f"저장: {out_path}")

    fraud = [r for r in results if r["label"] == "fraud"]
    normal = [r for r in results if r["label"] == "normal"]
    if fraud and normal:
        f_rate = sum(1 for r in fraud if r["peel_chain_detected"]) / len(fraud) * 100
        n_rate = sum(1 for r in normal if r["peel_chain_detected"]) / len(normal) * 100
        lift = (f_rate / n_rate) if n_rate > 0 else float("inf")
        print(f"\npeel_chain_detected: fraud {f_rate:.1f}% ({len(fraud)}개 중) / normal {n_rate:.2f}% ({len(normal)}개 중) / lift {lift}")


if __name__ == "__main__":
    main()
