"""
시간 윈도우 룰 평가 스크립트

xblock_transactions.json (개별 트랜잭션 리스트)을 읽어
시간 윈도우 기반 룰을 직접 평가하고,
각 주소에 대해 룰 발동 여부를 이진 플래그로 출력.

평가 룰:
  B-101: 10분 내 2건 이상 거래
  B-102: 1분 내 3건 이상 거래
  B-203: 10분 내 3개 이상 수신자에게 $500+ 송금
  B-204: 10분 내 3개 이상 출처에서 $500+ 수취
  C-004: 24시간 내 $5,000+ 합산, 2건 이상
  C-005: 24시간 내 $5,000~$7,499 송금 3건 이상 (CTR 회피)
  B-504: KST 00~06시 거래 5건 이상, 합계 $1,000+
  B-505: 24시간 내 $6,000~$7,499 동일 금액대 3건 이상 (스머핑)

실행:
    python3 evaluate_time_window_rules.py \
        --txs xblock_transactions.json \
        --features xblock_extracted.json \
        --output xblock_with_rules.json
"""

import json
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict

KST = timezone(timedelta(hours=9))


# ── 슬라이딩 윈도우 헬퍼 ────────────────────────────────────────

def sliding_window_check(txs, window_sec, check_fn):
    """타임스탬프 정렬된 txs에 슬라이딩 윈도우를 적용해 check_fn이 True인 구간이 있으면 True"""
    if not txs:
        return False
    ts_list = [t["ts"] for t in txs]
    left = 0
    for right in range(len(txs)):
        while ts_list[right] - ts_list[left] > window_sec:
            left += 1
        if check_fn(txs[left:right + 1]):
            return True
    return False


# ── 룰 평가 함수들 ───────────────────────────────────────────────

def eval_B101(sent, received):
    """10분(600s) 내 총 거래 2건 이상"""
    all_txs = sorted(
        [{"ts": t["ts"]} for t in sent] + [{"ts": t["ts"]} for t in received],
        key=lambda x: x["ts"]
    )
    return sliding_window_check(all_txs, 600, lambda w: len(w) >= 2)


def eval_B102(sent, received):
    """1분(60s) 내 총 거래 3건 이상"""
    all_txs = sorted(
        [{"ts": t["ts"]} for t in sent] + [{"ts": t["ts"]} for t in received],
        key=lambda x: x["ts"]
    )
    return sliding_window_check(all_txs, 60, lambda w: len(w) >= 3)


def eval_B203(sent):
    """10분 내 3개 이상 고유 수신자에게 합계 $500+ 송금"""
    def check(w):
        recipients = set(t["to"] for t in w)
        total = sum(t["usd"] for t in w)
        return len(recipients) >= 3 and total >= 500
    return sliding_window_check(sent, 600, check)


def eval_B204(received):
    """10분 내 3개 이상 고유 출처에서 합계 $500+ 수취"""
    def check(w):
        senders = set(t["from"] for t in w)
        total = sum(t["usd"] for t in w)
        return len(senders) >= 3 and total >= 500
    return sliding_window_check(received, 600, check)


def eval_C004(received):
    """24시간 내 합계 $5,000+ 수취, 2건 이상"""
    def check(w):
        return len(w) >= 2 and sum(t["usd"] for t in w) >= 5000
    return sliding_window_check(received, 86400, check)


def eval_C005(sent):
    """24시간 내 $5,000~$7,499 송금 3건 이상 (CTR 회피 구조화)"""
    filtered = [t for t in sent if 5000 <= t["usd"] <= 7499]
    def check(w):
        return len(w) >= 3
    return sliding_window_check(filtered, 86400, check)


def eval_B504(sent, received):
    """KST 00~06시 거래 5건 이상, 합계 $1,000+"""
    all_txs = sent + received
    night_txs = []
    for t in all_txs:
        dt = datetime.fromtimestamp(t["ts"], tz=KST)
        if 0 <= dt.hour < 6:
            night_txs.append(t)
    if len(night_txs) < 5:
        return False
    total = sum(t["usd"] for t in night_txs)
    return total >= 1000


def eval_B505(sent):
    """24시간 내 $6,000~$7,499 거래 3건 이상 (스머핑)"""
    filtered = [t for t in sent if 6000 <= t["usd"] <= 7499]
    def check(w):
        return len(w) >= 3
    return sliding_window_check(filtered, 86400, check)


# ── 메인 ────────────────────────────────────────────────────────

RULE_EVALS = {
    "B101_fired": lambda s, r: eval_B101(s, r),
    "B102_fired": lambda s, r: eval_B102(s, r),
    "B203_fired": lambda s, r: eval_B203(s),
    "B204_fired": lambda s, r: eval_B204(r),
    "C004_fired": lambda s, r: eval_C004(r),
    "C005_fired": lambda s, r: eval_C005(s),
    "B504_fired": lambda s, r: eval_B504(s, r),
    "B505_fired": lambda s, r: eval_B505(s),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--txs", default="xblock_transactions.json")
    parser.add_argument("--features", default="xblock_extracted.json")
    parser.add_argument("--output", default="xblock_with_rules.json")
    args = parser.parse_args()

    with open(args.txs) as f:
        tx_data = {d["address"]: d for d in json.load(f)}

    with open(args.features) as f:
        features = json.load(f)

    print(f"📋 평가 대상: {len(features):,}개 주소")

    results = []
    fired_counts = defaultdict(int)

    for i, sample in enumerate(features):
        addr = sample["address"]
        tx = tx_data.get(addr, {"sent": [], "received": []})
        sent = tx.get("sent", [])
        received = tx.get("received", [])

        rule_flags = {}
        for rule_name, fn in RULE_EVALS.items():
            fired = bool(fn(sent, received))
            rule_flags[rule_name] = int(fired)
            if fired:
                fired_counts[rule_name] += 1

        results.append({**sample, **rule_flags})

        if i % 500 == 0:
            print(f"   {i}/{len(features)} 처리 중...", end="\r")

    print(f"\n\n✅ 완료: {len(results):,}개")
    print("\n📊 룰별 발동률:")
    fraud_total = sum(1 for r in results if r["ground_truth_label"] == "fraud")
    normal_total = len(results) - fraud_total

    for rule in RULE_EVALS:
        fraud_fired = sum(1 for r in results if r["ground_truth_label"] == "fraud" and r[rule])
        normal_fired = sum(1 for r in results if r["ground_truth_label"] == "normal" and r[rule])
        fraud_rate = fraud_fired / fraud_total * 100
        normal_rate = normal_fired / normal_total * 100
        lift = (fraud_rate / normal_rate) if normal_rate > 0 else float("inf")
        print(f"  {rule:<15} fraud {fraud_rate:5.1f}% / normal {normal_rate:5.1f}% / lift {lift:.2f}")

    with open(args.output, "w") as f:
        json.dump(results, f)
    print(f"\n💾 저장: {args.output}")


if __name__ == "__main__":
    main()
