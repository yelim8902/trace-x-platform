"""
버킷 기반 집계 모듈

시간 버킷으로 트랜잭션을 그룹화하고 집계하는 기능
B-203 (Fan-out), B-204 (Fan-in) 룰에 사용
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta


class BucketEvaluator:
    """버킷 기반 룰 평가기"""
    
    def __init__(self, max_history_days: int = 365):
        """
        Args:
            max_history_days: 최대 보관 기간 (일)
        """
        self.max_history_days = max_history_days
        # 주소별 버킷 히스토리
        # {address: {bucket_key: [tx1, tx2, ...]}}
        self._buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    
    def add_transaction(self, tx: Dict[str, Any], bucket_spec: Dict[str, Any]):
        """
        트랜잭션을 버킷에 추가
        
        Args:
            tx: 트랜잭션 데이터
            bucket_spec: 버킷 설정 {
                "size_sec": int,  # 버킷 크기 (초)
                "group": List[str]  # 그룹화 필드
            }
        """
        size_sec = bucket_spec.get("size_sec", 600)  # 기본 10분
        group_fields = bucket_spec.get("group", [])
        
        # 그룹 키 생성
        group_key = self._get_group_key(tx, group_fields)
        if not group_key:
            return
        
        # 버킷 키 생성 (시간 기반)
        bucket_key = self._get_bucket_key(tx, size_sec)
        if not bucket_key:
            return
        
        # 버킷에 추가
        self._buckets[group_key][bucket_key].append(tx)
        
        # 오래된 버킷 정리
        self._cleanup_old_buckets(group_key, bucket_key, size_sec)
    
    def _get_group_key(self, tx: Dict[str, Any], group_fields: List[str]) -> Optional[str]:
        """그룹 키 생성"""
        if not group_fields:
            return None
        
        key_parts = []
        for field in group_fields:
            if field == "bucket_10m":
                # 버킷 키는 별도로 처리
                continue
            value = tx.get(field, "")
            if value:
                key_parts.append(str(value).lower())
        
        return "_".join(key_parts) if key_parts else None
    
    def _get_bucket_key(self, tx: Dict[str, Any], size_sec: int) -> Optional[str]:
        """버킷 키 생성 (시간 기반)"""
        timestamp = self._get_timestamp_int(tx)
        if not timestamp:
            return None
        
        # 버킷 시작 시간 계산
        bucket_start = (timestamp // size_sec) * size_sec
        return str(bucket_start)
    
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
    
    def _cleanup_old_buckets(self, group_key: str, current_bucket_key: str, size_sec: int):
        """오래된 버킷 정리"""
        max_timestamp = int(datetime.now().timestamp()) - (self.max_history_days * 86400)
        current_bucket_start = int(current_bucket_key)
        max_bucket_start = (max_timestamp // size_sec) * size_sec
        
        buckets_to_remove = []
        for bucket_key in self._buckets[group_key].keys():
            bucket_start = int(bucket_key)
            if bucket_start < max_bucket_start:
                buckets_to_remove.append(bucket_key)
        
        for bucket_key in buckets_to_remove:
            del self._buckets[group_key][bucket_key]
    
    def get_bucket_transactions(
        self,
        tx: Dict[str, Any],
        bucket_spec: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        현재 트랜잭션이 속한 버킷의 모든 트랜잭션 반환
        
        Args:
            tx: 현재 트랜잭션
            bucket_spec: 버킷 설정
        
        Returns:
            버킷 내 트랜잭션 리스트
        """
        size_sec = bucket_spec.get("size_sec", 600)
        group_fields = bucket_spec.get("group", [])
        
        group_key = self._get_group_key(tx, group_fields)
        bucket_key = self._get_bucket_key(tx, size_sec)
        
        if not group_key or not bucket_key:
            return []
        
        return self._buckets[group_key].get(bucket_key, [])
    
    def evaluate_bucket_rule(
        self,
        tx: Dict[str, Any],
        rule: Dict[str, Any]
    ) -> bool:
        """
        버킷 기반 룰 평가
        
        Args:
            tx: 현재 트랜잭션
            rule: 룰 정의 (bucket, aggregations 포함)
        
        Returns:
            룰 발동 여부
        """
        bucket_spec = rule.get("bucket")
        if not bucket_spec:
            return False
        
        # 버킷에 트랜잭션 추가
        self.add_transaction(tx, bucket_spec)
        
        # 버킷 내 트랜잭션 수집
        bucket_txs = self.get_bucket_transactions(tx, bucket_spec)
        
        # 현재 트랜잭션도 포함
        if tx not in bucket_txs:
            bucket_txs.append(tx)
        
        # 집계 조건 평가
        aggregations = rule.get("aggregations", [])
        if not aggregations:
            return False
        
        return self._evaluate_aggregations(bucket_txs, aggregations)
    
    def _evaluate_aggregations(
        self,
        txs: List[Dict[str, Any]],
        aggregations: List[Dict[str, Any]]
    ) -> bool:
        """집계 조건 평가"""
        from core.aggregation.window import WindowEvaluator
        
        # WindowEvaluator의 집계 로직 재사용
        window_eval = WindowEvaluator()
        return window_eval._evaluate_aggregations(txs, aggregations)

