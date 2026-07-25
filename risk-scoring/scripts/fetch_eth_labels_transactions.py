"""
eth_labels_2026_manifest.json의 주소들에 대해 Etherscan API로 실제 거래내역 수집.

xblock_transactions.json과 같은 스키마로 저장
({"address", "ground_truth_label", "sent": [...], "received": [...]})
— 기존 피처 검증 스크립트(peel_chain 등)를 최소 수정으로 재사용 가능하게.

실행:
    python3 scripts/fetch_eth_labels_transactions.py --limit 20   # 속도/정상동작 테스트
    python3 scripts/fetch_eth_labels_transactions.py              # 전체
"""
import argparse
import json
import os
import time
from pathlib import Path

import requests

project_root = Path(__file__).parent.parent
BASE_URL = "https://api.etherscan.io/v2/api"
CHAIN_ID = 1
MAX_TXS_PER_ADDRESS = 500
REQUEST_INTERVAL_SEC = 0.25  # 무료 티어 5 req/sec 안전 마진


def load_api_key() -> str:
    env_path = project_root.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("ETHERSCAN_API_KEY="):
                return line.split("=", 1)[1].strip()
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key:
        raise RuntimeError("ETHERSCAN_API_KEY를 .env 또는 환경변수에서 찾을 수 없음")
    return key


def call_etherscan(api_key: str, params: dict) -> list:
    params = {**params, "apikey": api_key, "chainid": CHAIN_ID}
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") == "0" and data.get("message") not in ("No transactions found", "OK"):
        return []
    result = data.get("result", [])
    return result if isinstance(result, list) else []


def fetch_address_transactions(api_key: str, address: str) -> dict:
    normal_txs = call_etherscan(api_key, {
        "module": "account", "action": "txlist", "address": address,
        "startblock": 0, "endblock": 99999999, "page": 1, "offset": MAX_TXS_PER_ADDRESS, "sort": "desc",
    })
    time.sleep(REQUEST_INTERVAL_SEC)
    token_txs = call_etherscan(api_key, {
        "module": "account", "action": "tokentx", "address": address,
        "startblock": 0, "endblock": 99999999, "page": 1, "offset": MAX_TXS_PER_ADDRESS, "sort": "desc",
    })
    time.sleep(REQUEST_INTERVAL_SEC)

    sent, received = [], []
    for tx in normal_txs + token_txs:
        try:
            value_wei = int(tx.get("value", 0))
            decimals = int(tx.get("tokenDecimal", 18)) if tx.get("tokenDecimal") else 18
            amount = value_wei / (10 ** decimals)
        except (ValueError, TypeError):
            continue
        if amount <= 0:
            continue
        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()
        ts = int(tx.get("timeStamp", 0))
        if from_addr == address.lower():
            sent.append({"to": to_addr, "usd": amount, "ts": ts})  # usd 필드명 유지(스키마 호환), 실제는 native/token 단위 근사치
        if to_addr == address.lower():
            received.append({"from": from_addr, "usd": amount, "ts": ts})

    return {"sent": sent[:MAX_TXS_PER_ADDRESS], "received": received[:MAX_TXS_PER_ADDRESS]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/dataset/eth_labels_2026_manifest.json")
    parser.add_argument("--output", default="data/dataset/eth_labels_2026_transactions.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    api_key = load_api_key()
    manifest = json.load(open(project_root / args.manifest))
    if args.limit:
        manifest = manifest[:args.limit]

    results = []
    t0 = time.time()
    for i, entry in enumerate(manifest):
        try:
            txs = fetch_address_transactions(api_key, entry["address"])
        except Exception as e:
            print(f"  ⚠️ {entry['address']} 실패: {e}")
            txs = {"sent": [], "received": []}

        results.append({
            "address": entry["address"],
            "ground_truth_label": entry["label"],
            "source_label": entry["source_label"],
            **txs,
        })

        if (i + 1) % 10 == 0 or i == len(manifest) - 1:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (len(manifest) - i - 1)
            print(f"  {i+1}/{len(manifest)}  ({elapsed:.0f}s 경과, 남은 예상 {eta:.0f}s)")

    out_path = project_root / args.output
    json.dump(results, open(out_path, "w"))
    print(f"\n저장: {out_path}")

    fraud = [r for r in results if r["ground_truth_label"] == "fraud"]
    normal = [r for r in results if r["ground_truth_label"] == "normal"]
    fraud_with_tx = sum(1 for r in fraud if r["sent"] or r["received"])
    normal_with_tx = sum(1 for r in normal if r["sent"] or r["received"])
    print(f"fraud {len(fraud)}개 중 거래 있음 {fraud_with_tx}개 / normal {len(normal)}개 중 거래 있음 {normal_with_tx}개")


if __name__ == "__main__":
    main()
