"""
프라이버시 프로토콜(Tornado Cash, Railgun, Aztec 등 믹서/프라이버시 컨트랙트) 직접 접촉 여부.

FATF Red Flag: "공개 블록체인에서 AEC/privacy coin으로 전환" — 이더리움에는 별도
privacy coin이 없어서, 가장 가까운 대응은 프라이버시 프로토콜/믹서와의 직접 접촉.
mixer_hop_distance(exposure_distance.py)와 달리 이건 1-hop 직접 접촉만 보는
단순 이진 피처라 멀티홉 그래프 없이 1-hop 거래 목록만으로 계산 가능.

주소 목록 출처: data/lists/bridge_contracts.json의 mixer_services
(dawsbot/eth-labels의 tornado-cash/mixer/ethereum-mixer/aztec 라벨에서 추출, 67개).
"""

from typing import Any, Dict, List, Set


def privacy_protocol_involved(
    sent: List[Dict[str, Any]],
    received: List[Dict[str, Any]],
    privacy_addresses: Set[str],
) -> Dict[str, Any]:
    """
    sent/received 거래 목록(xblock_transactions.json 스키마와 동일:
    sent=[{"to":..}], received=[{"from":..}])에서 프라이버시 프로토콜 직접 접촉 확인.
    """
    privacy_addresses = {a.lower() for a in privacy_addresses}

    touched_out = [t for t in sent if t.get("to", "").lower() in privacy_addresses]
    touched_in = [t for t in received if t.get("from", "").lower() in privacy_addresses]

    return {
        "privacy_protocol_involved": bool(touched_out or touched_in),
        "privacy_protocol_sent_count": len(touched_out),
        "privacy_protocol_received_count": len(touched_in),
    }
