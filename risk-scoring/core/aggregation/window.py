"""
시간 윈도우 처리 모듈

룰북의 window 조건을 처리하여 시간 기반 트랜잭션 집계
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class TransactionHistory:
    """트랜잭션 히스토리 관리"""
    
    def __init__(self, max_history_days: int = 365):
        """
        Args:
            max_history_days: 최대 보관 기간 (일, 기본 365일)
        """
        self.max_history_days = max_history_days
        # 주소별 트랜잭션 히스토리
        # {address: [{"timestamp": int, "usd_value": float, "from": str, "to": str, ...}, ...]}
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def add_transaction(self, address: str, tx_data: Dict[str, Any]) -> None:
        """트랜잭션 추가"""
        self._history[address].append(tx_data)
        self._cleanup_old_transactions(address)
    
    def get_window_transactions(
        self,
        address: str,
        current_timestamp: int,
        duration_sec: int
    ) -> List[Dict[str, Any]]:
        """
        시간 윈도우 내 트랜잭션 반환
        
        Args:
            address: 주소
            current_timestamp: 현재 시간 (Unix timestamp)
            duration_sec: 윈도우 크기 (초)
        
        Returns:
            윈도우 내 트랜잭션 리스트
        """
        txs = self._history.get(address, [])
        window_start = current_timestamp - duration_sec
        
        def get_timestamp_int(tx: Dict[str, Any]) -> int:
            """트랜잭션의 타임스탬프를 정수로 변환"""
            timestamp = tx.get("timestamp", 0)
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp())
                except:
                    return 0
            return int(timestamp) if timestamp else 0
        
        return [
            tx for tx in txs
            if window_start <= get_timestamp_int(tx) <= current_timestamp
        ]
    
    def _cleanup_old_transactions(self, address: str) -> None:
        """오래된 트랜잭션 삭제"""
        max_timestamp = int(datetime.now().timestamp()) - (self.max_history_days * 86400)
        
        def get_timestamp_int(tx: Dict[str, Any]) -> int:
            """트랜잭션의 타임스탬프를 정수로 변환"""
            timestamp = tx.get("timestamp", 0)
            if isinstance(timestamp, str):
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    return int(dt.timestamp())
                except:
                    return 0
            return int(timestamp) if timestamp else 0
        
        self._history[address] = [
            tx for tx in self._history[address]
            if get_timestamp_int(tx) >= max_timestamp
        ]


class WindowEvaluator:
    """윈도우 기반 룰 평가기"""
    
    def __init__(self, history: Optional[TransactionHistory] = None):
        """
        Args:
            history: 트랜잭션 히스토리 (None이면 새로 생성)
        """
        self.history = history or TransactionHistory()
    
    def evaluate_window_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        """
        윈도우 기반 룰 평가
        
        Args:
            tx_data: 현재 트랜잭션 데이터
            rule: 룰 정의 (window, aggregations 포함)
        
        Returns:
            룰 발동 여부
        """
        window_spec = rule.get("window")
        if not window_spec:
            return False  # window가 없으면 단일 트랜잭션 룰
        
        # 윈도우 파라미터 추출
        duration_sec = window_spec.get("duration_sec", 0)
        group_by = window_spec.get("group_by", ["address"])
        
        # 그룹 키 생성 (예: address)
        group_key = self._get_group_key(tx_data, group_by)
        if not group_key:
            return False
        
        # 윈도우 내 트랜잭션 수집
        current_timestamp = self._get_timestamp(tx_data)
        window_txs = self.history.get_window_transactions(
            group_key,
            current_timestamp,
            duration_sec
        )
        
        # 현재 트랜잭션도 포함
        window_txs.append(tx_data)
        
        # 집계 조건 평가
        aggregations = rule.get("aggregations", [])
        if not aggregations:
            return False
        
        return self._evaluate_aggregations(window_txs, aggregations)
    
    def _get_group_key(
        self,
        tx_data: Dict[str, Any],
        group_by: List[str]
    ) -> Optional[str]:
        """그룹 키 생성"""
        # group_by가 ["address"]인 경우 target_address 사용
        if "address" in group_by:
            return tx_data.get("to") or tx_data.get("target_address")
        # 다른 그룹 키는 추후 확장
        return None
    
    def _get_timestamp(self, tx_data: Dict[str, Any]) -> int:
        """타임스탬프 추출 (Unix timestamp)"""
        timestamp = tx_data.get("timestamp")
        if isinstance(timestamp, str):
            # ISO8601 형식 파싱
            try:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                return int(dt.timestamp())
            except:
                return 0
        return int(timestamp) if timestamp else 0
    
    def _evaluate_aggregations(
        self,
        txs: List[Dict[str, Any]],
        aggregations: List[Dict[str, Any]]
    ) -> bool:
        """집계 조건 평가"""
        if not txs:
            return False
        
        for agg in aggregations:
            if not self._evaluate_single_aggregation(txs, agg):
                return False  # 하나라도 실패하면 False
        
        return True  # 모든 조건 만족
    
    def _evaluate_single_aggregation(
        self,
        txs: List[Dict[str, Any]],
        agg: Dict[str, Any]
    ) -> bool:
        """단일 집계 조건 평가"""
        def get_field_value(tx: Dict[str, Any], field: str) -> float:
            """필드 값 추출 (필드명 매핑 포함)"""
            # usd_value -> amount_usd 매핑
            if field == "usd_value":
                return float(tx.get("amount_usd", tx.get("usd_value", 0)))
            return float(tx.get(field, 0))
        
        # sum_gte: 합계 >= 값
        if "sum_gte" in agg:
            spec = agg["sum_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            total = sum(get_field_value(tx, field) for tx in txs)
            return total >= float(value)
        
        # count_gte: 개수 >= 값
        if "count_gte" in agg:
            value = agg["count_gte"].get("value", 0)
            return len(txs) >= int(value)
        
        # every_gte: 모든 값 >= 값
        if "every_gte" in agg:
            spec = agg["every_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            return all(get_field_value(tx, field) >= float(value) for tx in txs)
        
        # distinct_gte: 고유값 개수 >= 값
        if "distinct_gte" in agg:
            spec = agg["distinct_gte"]
            field = spec.get("field")
            value = spec.get("value", 0)
            if not field:
                return False
            distinct_values = set(tx.get(field) for tx in txs if tx.get(field))
            return len(distinct_values) >= int(value)
        
        # any_gte: 하나라도 >= 값
        if "any_gte" in agg:
            spec = agg["any_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            return any(get_field_value(tx, field) >= float(value) for tx in txs)
        
        # avg_gte: 평균 >= 값
        if "avg_gte" in agg:
            spec = agg["avg_gte"]
            field = spec.get("field", "usd_value")
            value = spec.get("value", 0)
            if not txs:
                return False
            avg = sum(get_field_value(tx, field) for tx in txs) / len(txs)
            return avg >= float(value)
        
        return False

