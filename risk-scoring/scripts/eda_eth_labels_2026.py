"""
ETH-Labels-2026 데이터셋 EDA (docs/EDA_ETH_LABELS_2026.md 근거 자료 생성용).

xblock_eda.py와 같은 형식이지만 스키마가 다름:
- 별도 "extracted"(그래프 통계) 파일 없음 — 멀티홉 그래프를 만들지 않았으므로
- 금액이 USD가 아니라 원시 native/token 단위 (docs/DATA_ETH_LABELS_2026.md 한계 참고)
- source_label(개별 사건명)이 있어서 fraud 표본이 몇 개 사건에 집중됐는지 확인 가능
"""
import json
import statistics
from collections import Counter
from pathlib import Path

project_root = Path(__file__).parent.parent
data = json.load(open(project_root / "data/dataset/eth_labels_2026_transactions.json"))

fraud = [r for r in data if r["ground_truth_label"] == "fraud"]
normal = [r for r in data if r["ground_truth_label"] == "normal"]

print("=" * 70)
print("1) 클래스 균형")
print("=" * 70)
print(f"전체: {len(data)}, fraud: {len(fraud)} ({len(fraud)/len(data)*100:.1f}%), normal: {len(normal)} ({len(normal)/len(data)*100:.1f}%)")

print("\n" + "=" * 70)
print("2) 중복/정합성 체크")
print("=" * 70)
addrs = [r["address"] for r in data]
print("주소 중복 개수:", len(addrs) - len(set(addrs)))
fraud_addrs = set(r["address"] for r in fraud)
normal_addrs = set(r["address"] for r in normal)
print("fraud/normal 라벨 충돌(같은 주소가 둘 다):", len(fraud_addrs & normal_addrs))

print("\n" + "=" * 70)
print("3) source_label 분포 (fraud 표본이 몇 개 사건에 집중됐는지)")
print("=" * 70)
fraud_sources = Counter(r["source_label"] for r in fraud)
for label, count in fraud_sources.most_common():
    print(f"  {label:<28} {count}")

print("\n" + "=" * 70)
print("4) 거래 활동 없는 주소 (sent+received 모두 0건)")
print("=" * 70)
zero_tx = [r for r in data if not r["sent"] and not r["received"]]
zero_fraud = sum(1 for r in zero_tx if r["ground_truth_label"] == "fraud")
zero_normal = sum(1 for r in zero_tx if r["ground_truth_label"] == "normal")
print(f"활동 0건: {len(zero_tx)}개 (fraud {zero_fraud}/{len(fraud)}, normal {zero_normal}/{len(normal)})")


def tx_count(r):
    return len(r["sent"]) + len(r["received"])


def activity_span_days(r):
    ts = [t["ts"] for t in r["sent"]] + [t["ts"] for t in r["received"]]
    if len(ts) < 2:
        return 0
    return (max(ts) - min(ts)) / 86400


def stats(records, transform):
    vals = [transform(r) for r in records]
    vals = [v for v in vals if v is not None]
    if not vals:
        return "N/A"
    return f"median={statistics.median(vals):.2f}  mean={statistics.mean(vals):.2f}  max={max(vals):.2f}  min={min(vals):.2f}"


print("\n" + "=" * 70)
print("5) 실제 거래 건수 (sent+received, 활동 있는 주소만)")
print("=" * 70)
fraud_active = [r for r in fraud if tx_count(r) > 0]
normal_active = [r for r in normal if tx_count(r) > 0]
print("  fraud :", stats(fraud_active, tx_count))
print("  normal:", stats(normal_active, tx_count))

print("\n" + "=" * 70)
print("6) 활동 기간(일) — 첫 거래~마지막 거래 (활동 있는 주소만)")
print("=" * 70)
print("  fraud :", stats(fraud_active, activity_span_days))
print("  normal:", stats(normal_active, activity_span_days))

print("\n" + "=" * 70)
print("7) MAX_TXS_PER_ADDRESS(500) 캡 도달 주소 (거래 내역이 잘렸을 가능성)")
print("=" * 70)
capped = [r for r in data if len(r["sent"]) == 500 or len(r["received"]) == 500]
capped_fraud = sum(1 for r in capped if r["ground_truth_label"] == "fraud")
print(f"캡 도달: {len(capped)}개 (fraud {capped_fraud}, normal {len(capped) - capped_fraud})")

print("\n" + "=" * 70)
print("8) 타임스탬프 범위 (시기 확인 — 2024~2025년이 맞는지)")
print("=" * 70)
all_ts = [t["ts"] for r in data for t in r["sent"] + r["received"] if t["ts"] > 0]
if all_ts:
    import datetime
    print(f"  최소: {datetime.datetime.utcfromtimestamp(min(all_ts))} ({min(all_ts)})")
    print(f"  최대: {datetime.datetime.utcfromtimestamp(max(all_ts))} ({max(all_ts)})")
    print(f"  중앙값: {datetime.datetime.utcfromtimestamp(int(statistics.median(all_ts)))}")
