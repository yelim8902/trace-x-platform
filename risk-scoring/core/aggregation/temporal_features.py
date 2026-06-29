"""
시간적 피처 추출 모듈 (XBlock 그래프 연구 기반 신규)

연구 근거:
- Fishing for Phishers (arXiv 2025): 피싱 주소는 단기 집중 + 자동화 패턴
- StableAML (2025): inter-tx interval std가 AML 탐지 핵심 피처
- 기존 XBlock 집계 데이터셋의 한계: 타임스탬프 분포 정보 전무

추출 피처:
    inter_tx_interval_std   : 거래 간격 표준편차 (초) - 낮을수록 자동화 의심
    burst_score             : 가장 바쁜 1시간 거래 비율 (0~1) - 높을수록 집중 활동
    active_days             : 활동 일수 - 낮을수록 일회성 주소
    tx_density              : 일평균 거래 수 - 높을수록 집중 활동
    night_tx_ratio          : 0~6시(UTC) 거래 비율 - 높을수록 봇 의심
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import statistics
import math


class TemporalFeatureExtractor:
    """XBlock MultiDiGraph 엣지의 timestamp 기반 시간적 피처 추출기"""

    NIGHT_HOUR_START = 0   # UTC 0시
    NIGHT_HOUR_END   = 6   # UTC 6시 (exclusive)
    BURST_WINDOW_SEC = 3600  # 1시간 = 3600초

    # ── 공개 API ──────────────────────────────────────────────────

    def extract(self, timestamps: List[int], amounts: Optional[List[float]] = None) -> Dict[str, float]:
        """
        Unix timestamp 리스트에서 시간적 피처를 추출한다.

        Args:
            timestamps : Unix timestamp (초 단위) 리스트 (정렬 불필요)
            amounts    : 각 거래의 금액 리스트 (옵션, burst_score 가중치에 사용)

        Returns:
            {
                "inter_tx_interval_std": float,
                "burst_score"          : float,
                "active_days"          : float,
                "tx_density"           : float,
                "night_tx_ratio"       : float,
            }
        """
        defaults = {
            "inter_tx_interval_std": 0.0,
            "burst_score":           0.0,
            "active_days":           0.0,
            "tx_density":            0.0,
            "night_tx_ratio":        0.0,
        }

        valid_ts = sorted([int(t) for t in timestamps if t and t > 0])
        if len(valid_ts) < 2:
            return defaults

        return {
            "inter_tx_interval_std": self._interval_std(valid_ts),
            "burst_score":           self._burst_score(valid_ts),
            "active_days":           self._active_days(valid_ts),
            "tx_density":            self._tx_density(valid_ts),
            "night_tx_ratio":        self._night_tx_ratio(valid_ts),
        }

    # ── 내부 계산 ─────────────────────────────────────────────────

    def _interval_std(self, sorted_ts: List[int]) -> float:
        """거래 간격 표준편차 (초). 자동화된 봇은 거의 0에 수렴."""
        intervals = [sorted_ts[i] - sorted_ts[i-1] for i in range(1, len(sorted_ts))]
        if len(intervals) < 2:
            return 0.0
        try:
            return statistics.stdev(intervals)
        except statistics.StatisticsError:
            return 0.0

    def _burst_score(self, sorted_ts: List[int]) -> float:
        """
        가장 바쁜 1시간 구간의 거래 수 / 전체 거래 수.
        머니 세탁의 Placement 단계는 단시간 집중 입금 패턴.
        """
        n = len(sorted_ts)
        if n == 0:
            return 0.0

        max_in_window = 0
        left = 0
        for right in range(n):
            while sorted_ts[right] - sorted_ts[left] > self.BURST_WINDOW_SEC:
                left += 1
            max_in_window = max(max_in_window, right - left + 1)

        return max_in_window / n

    def _active_days(self, sorted_ts: List[int]) -> float:
        """활동한 고유 날짜 수 (UTC 기준). 낮을수록 일회성 주소."""
        days = set()
        for ts in sorted_ts:
            try:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                days.add(dt.date())
            except (OSError, OverflowError, ValueError):
                continue
        return float(len(days))

    def _tx_density(self, sorted_ts: List[int]) -> float:
        """
        일평균 거래 수 = 전체 거래 수 / 활동 일수.
        높을수록 집중적이고 자동화된 계정.
        """
        days = self._active_days(sorted_ts)
        if days == 0:
            return float(len(sorted_ts))
        return len(sorted_ts) / days

    def _night_tx_ratio(self, sorted_ts: List[int]) -> float:
        """
        UTC 0~6시 거래 비율. 높을수록 봇/자동화 의심.
        참고: 인간 사용자는 보통 활동 시간대가 있음.
        """
        if not sorted_ts:
            return 0.0

        night_count = 0
        for ts in sorted_ts:
            try:
                hour = datetime.fromtimestamp(ts, tz=timezone.utc).hour
                if self.NIGHT_HOUR_START <= hour < self.NIGHT_HOUR_END:
                    night_count += 1
            except (OSError, OverflowError, ValueError):
                continue

        return night_count / len(sorted_ts)

    # ── 스코어 변환 (Stage1Scorer 연동용) ─────────────────────────

    def temporal_risk_score(self, features: Dict[str, float]) -> float:
        """
        시간적 피처 딕셔너리 → 0~100 위험 점수 변환.
        Stage1Scorer._calculate_graph_score()에서 호출.

        가중치 근거:
          burst_score(35)    : Placement 단계 핵심 시그널
          interval_std(25)   : 자동화 탐지 (낮을수록 위험)
          night_ratio(20)    : 봇 활동 시간대
          active_days(20)    : 일회성 주소 (낮을수록 위험, 역방향)
        """
        score = 0.0

        # 1) burst_score: 높을수록 위험
        burst = features.get("burst_score", 0.0)
        if burst >= 0.7:
            score += 35.0
        elif burst >= 0.5:
            score += 20.0
        elif burst >= 0.3:
            score += 10.0

        # 2) inter_tx_interval_std: 낮을수록 자동화 → 위험
        # 정상 계정: std 수 시간~수일(10000초+), 봇: 수십~수백 초
        std = features.get("inter_tx_interval_std", 0.0)
        if 0 < std < 300:       # 5분 미만 std → 고자동화
            score += 25.0
        elif std < 3600:        # 1시간 미만
            score += 12.0
        elif std < 86400:       # 1일 미만
            score += 5.0

        # 3) night_tx_ratio: 높을수록 봇
        night = features.get("night_tx_ratio", 0.0)
        if night >= 0.6:
            score += 20.0
        elif night >= 0.4:
            score += 12.0
        elif night >= 0.25:
            score += 6.0

        # 4) active_days: 낮을수록 일회성 (역방향)
        days = features.get("active_days", 30.0)
        if days <= 3:
            score += 20.0
        elif days <= 7:
            score += 12.0
        elif days <= 14:
            score += 5.0

        return min(100.0, score)
