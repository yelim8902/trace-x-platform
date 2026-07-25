import json
import statistics
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
extracted = json.load(open(project_root / "data/dataset/xblock_extracted.json"))
tx_data = json.load(open(project_root / "data/dataset/xblock_transactions.json"))
tx_by_addr = {r["address"]: r for r in tx_data}

fraud = [r for r in extracted if r["ground_truth_label"] == "fraud"]
normal = [r for r in extracted if r["ground_truth_label"] == "normal"]

print("=" * 70)
print("1) 클래스 균형")
print("=" * 70)
print(f"전체: {len(extracted)}, fraud: {len(fraud)} ({len(fraud)/len(extracted)*100:.1f}%), normal: {len(normal)} ({len(normal)/len(extracted)*100:.1f}%)")

print("\n" + "=" * 70)
print("2) 중복/정합성 체크")
print("=" * 70)
addrs = [r["address"] for r in extracted]
print("extracted 주소 중복 개수:", len(addrs) - len(set(addrs)))
fraud_addrs = set(r["address"] for r in fraud)
normal_addrs = set(r["address"] for r in normal)
print("fraud/normal 라벨 충돌(같은 주소가 둘 다):", len(fraud_addrs & normal_addrs))
extracted_addrs = set(addrs)
tx_addrs = set(tx_by_addr.keys())
print("extracted에는 있는데 transactions.json에는 없는 주소:", len(extracted_addrs - tx_addrs))
print("transactions.json에는 있는데 extracted에는 없는 주소:", len(tx_addrs - extracted_addrs))

print("\n" + "=" * 70)
print("3) 결측/0값 체크 (extracted 필드)")
print("=" * 70)
numeric_fields = ["fan_in_count", "fan_out_count", "pattern_score", "n_omega", "n_theta",
                   "ppr_score", "graph_nodes", "graph_edges", "avg_tx_usd", "max_tx_usd",
                   "total_sent_usd", "total_recv_usd"]
for field in numeric_fields:
    none_count = sum(1 for r in extracted if r.get(field) is None)
    zero_count = sum(1 for r in extracted if r.get(field) == 0)
    print(f"  {field:<20} None: {none_count:>5}  ==0: {zero_count:>5} / {len(extracted)}")

print("\n" + "=" * 70)
print("4) 거래 개수 0건인 주소 (extract_txs_for_rules.py에서 누락됐을 가능성)")
print("=" * 70)
zero_tx = [r for r in tx_data if len(r["sent"]) == 0 and len(r["received"]) == 0]
zero_tx_fraud = sum(1 for r in zero_tx if r["ground_truth_label"] == "fraud")
zero_tx_normal = sum(1 for r in zero_tx if r["ground_truth_label"] == "normal")
print(f"sent+received 모두 0건: {len(zero_tx)}개 (fraud {zero_tx_fraud}, normal {zero_tx_normal})")

print("\n" + "=" * 70)
print("5) fraud vs normal 분포 비교 (median, mean, max)")
print("=" * 70)


def stats(records, field, transform=lambda r: r.get(field, 0)):
    vals = [transform(r) for r in records]
    vals = [v for v in vals if v is not None]
    if not vals:
        return "N/A"
    return f"median={statistics.median(vals):.2f}  mean={statistics.mean(vals):.2f}  max={max(vals):.2f}  min={min(vals):.2f}"


for field in ["fan_in_count", "fan_out_count", "pattern_score", "n_omega", "n_theta",
              "graph_nodes", "graph_edges", "avg_tx_usd", "max_tx_usd", "total_sent_usd", "total_recv_usd"]:
    print(f"\n  [{field}]")
    print(f"    fraud : {stats(fraud, field)}")
    print(f"    normal: {stats(normal, field)}")

print("\n" + "=" * 70)
print("6) 실제 거래 건수 & 활동 기간 (xblock_transactions.json 기준)")
print("=" * 70)


def tx_count(addr):
    r = tx_by_addr.get(addr)
    if not r:
        return 0
    return len(r["sent"]) + len(r["received"])


def activity_span_days(addr):
    r = tx_by_addr.get(addr)
    if not r:
        return None
    ts = [t["ts"] for t in r["sent"]] + [t["ts"] for t in r["received"]]
    if len(ts) < 2:
        return 0
    return (max(ts) - min(ts)) / 86400


print("\n  [실제 거래 건수 (sent+received)]")
print("    fraud : ", stats(fraud, None, lambda r: tx_count(r["address"])))
print("    normal: ", stats(normal, None, lambda r: tx_count(r["address"])))

print("\n  [활동 기간(일) — 첫 거래~마지막 거래]")
print("    fraud : ", stats(fraud, None, lambda r: activity_span_days(r["address"])))
print("    normal: ", stats(normal, None, lambda r: activity_span_days(r["address"])))

print("\n" + "=" * 70)
print("7) 극단치 (top 1% 확인) — total_sent_usd 기준")
print("=" * 70)
all_sent = sorted([(r["total_sent_usd"], r["address"], r["ground_truth_label"]) for r in extracted], reverse=True)
for val, addr, label in all_sent[:5]:
    print(f"  {val:>15,.2f} USD  {addr}  [{label}]")

print("\n" + "=" * 70)
print("8) MAX_TXS_PER_ADDRESS(500) 캡에 걸린 주소 수 (거래 내역이 잘렸을 가능성)")
print("=" * 70)
capped = [r for r in tx_data if len(r["sent"]) == 500 or len(r["received"]) == 500]
print(f"sent 또는 received가 정확히 500건(캡 도달)인 주소: {len(capped)}개")
capped_fraud = sum(1 for r in capped if r["ground_truth_label"] == "fraud")
print(f"  fraud: {capped_fraud}, normal: {len(capped) - capped_fraud}")
