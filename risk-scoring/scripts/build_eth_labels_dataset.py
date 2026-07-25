"""
dawsbot/eth-labels (https://github.com/dawsbot/eth-labels, 2026-07 기준 최신 유지보수)에서
2024~2025년 실제 해킹/사기 사건 라벨 주소를 뽑아 새 데이터셋(ETH-Labels-2026)을 구축.

XBlock(2016~2019 피싱)보다 훨씬 최신 사건(Bybit, WazirX, BingX 등 2024~2025 exploit)이라
"최신 해킹 주소" 검증 목적에 더 맞음.

1단계: 주소 목록만 추출 (API 호출 없음, 빠름)
2단계(별도 스크립트): Etherscan API로 각 주소의 실제 거래내역 수집

실행:
    python3 scripts/build_eth_labels_dataset.py
"""
import json
import random
import urllib.request
from pathlib import Path

project_root = Path(__file__).parent.parent
SEED = 42

ETH_LABELS_SOURCE_URL = "https://raw.githubusercontent.com/dawsbot/eth-labels/v1/data/json/accounts.json"

FRAUD_LABEL_KEYWORDS = ["exploit", "fraud", "scam", "phish", "hack", "theft", "stolen", "malicious"]

# 명확히 정상/합법 카테고리만 선택 — mev-bot, airdrop-hunter, sybil-delegate,
# blocked, parity-bug 등 애매한(적대적이거나 라벨 노이즈 위험 있는) 카테고리는 제외
NORMAL_LABELS = [
    "bitget", "deribit", "bilaxy",       # CEX
    "sushiswap", "balancer", "bancor", "yearn", "aave", "synthetix", "pendle", "the-graph",  # DeFi 프로토콜
    "nonprofit", "charity", "endaoment",  # 비영리
]

NORMAL_SAMPLE_SIZE = 500


def main():
    accounts_path = project_root / "data/dataset/eth_labels_accounts_raw.json"
    if not accounts_path.exists():
        print(f"소스 다운로드 중: {ETH_LABELS_SOURCE_URL}")
        accounts_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(ETH_LABELS_SOURCE_URL, accounts_path)
        print(f"  저장: {accounts_path}")
    else:
        print(f"기존 캐시 사용: {accounts_path} (최신으로 다시 받으려면 이 파일 삭제 후 재실행)")

    with open(accounts_path) as f:
        accounts = json.load(f)

    eth_accounts = [a for a in accounts if a.get("chainId") == 1]
    print(f"Ethereum(chainId=1) 라벨 주소: {len(eth_accounts)}개")

    fraud = [a for a in eth_accounts if any(k in a["label"].lower() for k in FRAUD_LABEL_KEYWORDS)]
    print(f"사기/해킹 관련 주소: {len(fraud)}개")
    fraud_label_counts = {}
    for a in fraud:
        fraud_label_counts[a["label"]] = fraud_label_counts.get(a["label"], 0) + 1
    for label, count in sorted(fraud_label_counts.items(), key=lambda x: -x[1]):
        print(f"  {label}: {count}")

    normal_pool = [a for a in eth_accounts if a["label"] in NORMAL_LABELS]
    print(f"\n정상 후보 풀: {len(normal_pool)}개")

    rng = random.Random(SEED)
    rng.shuffle(normal_pool)
    normal = normal_pool[:NORMAL_SAMPLE_SIZE]

    # 혹시 모를 중복 주소(같은 주소가 fraud/normal 둘 다) 제거
    fraud_addrs = {a["address"].lower() for a in fraud}
    normal = [a for a in normal if a["address"].lower() not in fraud_addrs]
    print(f"정상 샘플(중복 제거 후): {len(normal)}개")

    manifest = []
    for a in fraud:
        manifest.append({"address": a["address"].lower(), "label": "fraud", "source_label": a["label"], "name_tag": a.get("nameTag", "")})
    for a in normal:
        manifest.append({"address": a["address"].lower(), "label": "normal", "source_label": a["label"], "name_tag": a.get("nameTag", "")})

    # 주소 중복 제거 (동일 주소가 여러 라벨을 가질 수 있음 — 먼저 나온 것 우선)
    seen = set()
    deduped = []
    for m in manifest:
        if m["address"] in seen:
            continue
        seen.add(m["address"])
        deduped.append(m)

    out_path = project_root / "data/dataset/eth_labels_2026_manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(deduped, open(out_path, "w"), indent=2)

    fraud_n = sum(1 for m in deduped if m["label"] == "fraud")
    normal_n = sum(1 for m in deduped if m["label"] == "normal")
    print(f"\n저장: {out_path}")
    print(f"최종 — fraud {fraud_n}개 / normal {normal_n}개 / 총 {len(deduped)}개")


if __name__ == "__main__":
    main()
