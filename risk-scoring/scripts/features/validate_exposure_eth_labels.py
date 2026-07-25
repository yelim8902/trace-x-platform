"""
sanction/mixer/privacy 노출 피처를 ETH-Labels-2026(2024~2025년, 시기 정합)으로 재검증.

XBlock 때와 다른 제약: 멀티홉 그래프(MulDiGraph.pkl 같은 전체 그래프)가 없고
주소별 1-hop 거래 목록(sent/received)만 있음. 그래서 hop_distance_to_any()의
멀티홉 BFS는 그대로 재현 불가 — 대신 **1-hop 직접 접촉 여부**만 확인.
(exposure_score_from_hops 기준 hop=1 -> score 40에 해당하는 경우만 검출,
hop=2 이상은 이 데이터로 판단 불가 = 과소측정 가능성 있음, 문서에 명시)

MIXER_LIST와 privacy_protocol.py가 쓰는 주소 목록이 둘 다
data/lists/bridge_contracts.json의 mixer_services라 동일 소스임 —
이 스크립트에서 "믹서 직접 접촉"과 "프라이버시 프로토콜 직접 접촉"은
같은 계산이 된다(1-hop 데이터에서는 구분 불가).
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.data.lists import ListLoader

loader = ListLoader(data_dir=str(project_root / "data/lists"))
sdn_list = loader.get_sdn_list()
mixer_list = loader.get_mixer_list()

print(f"SDN_LIST: {len(sdn_list)}개, MIXER_LIST: {len(mixer_list)}개")

data = json.load(open(project_root / "data/dataset/eth_labels_2026_transactions.json"))
fraud = [r for r in data if r["ground_truth_label"] == "fraud"]
normal = [r for r in data if r["ground_truth_label"] == "normal"]


def direct_contact(record: dict, target_list: set) -> bool:
    for t in record["sent"]:
        if t.get("to", "").lower() in target_list:
            return True
    for t in record["received"]:
        if t.get("from", "").lower() in target_list:
            return True
    return False


def summarize(name, target_list):
    print(f"\n[{name}]")
    fraud_hit = [r for r in fraud if direct_contact(r, target_list)]
    normal_hit = [r for r in normal if direct_contact(r, target_list)]
    fraud_rate = len(fraud_hit) / len(fraud) * 100
    normal_rate = len(normal_hit) / len(normal) * 100
    lift = fraud_rate / normal_rate if normal_rate > 0 else float("inf")
    print(f"  fraud : {len(fraud_hit)}/{len(fraud)} ({fraud_rate:.2f}%)")
    print(f"  normal: {len(normal_hit)}/{len(normal)} ({normal_rate:.2f}%)")
    print(f"  lift  : {lift:.1f}")
    if fraud_hit:
        print("  fraud 적중 예시 (최대 5개):")
        for r in fraud_hit[:5]:
            print(f"    {r['address']} [{r['source_label']}]")
    return fraud_hit, normal_hit


summarize("sanction_hop_distance (1-hop 직접 접촉, SDN_LIST 947개)", sdn_list)
summarize("mixer_hop_distance / privacy_protocol_involved (1-hop 직접 접촉, MIXER_LIST 67개)", mixer_list)
