"""
통계 계산 모듈

거래 간격, 표준편차 등 통계량 계산
B-103 룰에 사용
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import statistics


class StatisticsCalculator:
    """통계 계산기"""
    
    def calculate_interarrival_std(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        거래 간격 표준편차 계산
        
        Args:
            transactions: 트랜잭션 리스트 (시간순 정렬 필요)
        
        Returns:
            거래 간격 표준편차 (None if insufficient data)
        """
        if len(transactions) < 2:
            return None
        
        # 타임스탬프 추출 및 정렬
        timestamps = []
        for tx in transactions:
            ts = self._get_timestamp_int(tx)
            if ts:
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return None
        
        timestamps.sort()
        
        # 거래 간격 계산
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            if interval > 0:  # 양수만
                intervals.append(interval)
        
        if len(intervals) < 2:
            return None
        
        # 표준편차 계산
        try:
            return statistics.stdev(intervals)
        except statistics.StatisticsError:
            return None
    
    def calculate_interarrival_mean(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Optional[float]:
        """
        거래 간격 평균 계산
        
        Args:
            transactions: 트랜잭션 리스트
        
        Returns:
            거래 간격 평균 (초)
        """
        if len(transactions) < 2:
            return None
        
        timestamps = []
        for tx in transactions:
            ts = self._get_timestamp_int(tx)
            if ts:
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return None
        
        timestamps.sort()
        
        intervals = []
        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i-1]
            if interval > 0:
                intervals.append(interval)
        
        if not intervals:
            return None
        
        try:
            return statistics.mean(intervals)
        except statistics.StatisticsError:
            return None
    
    def _get_timestamp_int(self, tx: Dict[str, Any]) -> Optional[int]:
        """타임스탬프를 정수로 변환"""
        timestamp = tx.get("timestamp", 0)
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return None
        return int(timestamp) if timestamp else None
    
    def check_prerequisites(
        self,
        transactions: List[Dict[str, Any]],
        min_edges: int = 10
    ) -> bool:
        """
        Prerequisites 체크
        
        Args:
            transactions: 트랜잭션 리스트
            min_edges: 최소 거래 수
        
        Returns:
            Prerequisites 만족 여부
        """
        return len(transactions) >= min_edges

