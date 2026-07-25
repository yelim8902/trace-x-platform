"""
개인 기준선(이 주소 자신의 과거 패턴) 대비 이상치 피처.

도메인 조사(docs/DOMAIN_RESEARCH.md 발견 4)에서 이미 밝혔듯 크립토 AML에 특화된
논문 근거는 약하고, "기준선 확립 후 이탈 탐지"라는 일반적인 이상탐지 원칙에 기반함.

기존 B-103(interarrival_std, core/aggregation/stats.py)과의 차이:
B-103은 거래 간격의 원시 표준편차(초 단위, 스케일에 의존)를 그대로 씀.
여기서는 평균 대비 표준편차 비율(변동계수, coefficient of variation)을 써서
스케일 무관하게 "이 주소 활동이 얼마나 불규칙한가"를 정규화된 값으로 봄
— 절대적인 간격 크기가 아니라 상대적인 불규칙성을 포착하는 게 목적이라 다름.
"""

import statistics
from typing import Any, Dict, List, Optional


def _coefficient_of_variation(values: List[float]) -> Optional[float]:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    if mean == 0:
        return None
    try:
        std = statistics.stdev(values)
    except statistics.StatisticsError:
        return None
    return std / mean


def amount_deviation_score(transactions: List[Dict[str, Any]], amount_field: str = "usd") -> Optional[float]:
    """거래 금액의 변동계수 — 이 주소의 거래 금액이 얼마나 들쭉날쭉한지."""
    amounts = [float(t.get(amount_field, 0)) for t in transactions]
    amounts = [a for a in amounts if a > 0]
    return _coefficient_of_variation(amounts)


def frequency_deviation_score(transactions: List[Dict[str, Any]], ts_field: str = "ts") -> Optional[float]:
    """거래 간격의 변동계수 — 이 주소의 거래 타이밍이 얼마나 불규칙한지."""
    timestamps = sorted(int(t.get(ts_field, 0)) for t in transactions if t.get(ts_field))
    if len(timestamps) < 3:
        return None
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:]) if b > a]
    return _coefficient_of_variation(intervals)



# train set 스윕으로 검증된 균형 임계값 (docs/FEATURE_ENGINEERING.md 참고)
AMOUNT_DEVIATION_THRESHOLD = 1.0   # fraud 62.7% / normal 4.20% / lift 14.9
FREQUENCY_DEVIATION_THRESHOLD = 1.0  # fraud 78.2% / normal 5.43% / lift 14.4


def deviation_features(sent: List[Dict[str, Any]], received: List[Dict[str, Any]]) -> Dict[str, Any]:
    """ML 피처용 요약 — sent+received 합쳐서 계산."""
    all_txs = sent + received
    amt = amount_deviation_score(all_txs)
    freq = frequency_deviation_score(all_txs)
    return {
        "amount_deviation_score": amt,
        "frequency_deviation_score": freq,
        "amount_deviation_high": bool(amt is not None and amt >= AMOUNT_DEVIATION_THRESHOLD),
        "frequency_deviation_high": bool(freq is not None and freq >= FREQUENCY_DEVIATION_THRESHOLD),
    }
