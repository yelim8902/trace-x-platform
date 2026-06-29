"""
MPOCryptoML Timestamp 및 Weight 정규화 모듈

논문의 Nθ(vi) (Normalized Timestamp Score) 및 Nω(vi) (Normalized Weight Score) 구현
"""

from typing import Dict, List, Set, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx
import numpy as np


class MPOCryptoMLNormalizer:
    """
    MPOCryptoML 논문의 정규화 점수 계산기
    
    - Nθ(vi): Normalized Timestamp Score - 시간적 비대칭성
    - Nω(vi): Normalized Weight Score - 거래 금액 불균형
    """
    
    def __init__(self):
        pass
    
    def normalize_timestamp(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> float:
        """
        Normalized Timestamp Score (NTS) 계산: Nθ(vi)
        
        논문: 시간적 비대칭성을 측정하여 transient intermediary accounts 탐지
        - 들어오는 거래와 나가는 거래의 시간 분포 차이 측정
        - 세탁 계정은 유입과 유출 사이의 시간 간격이 짧음
        
        Args:
            vertex: 분석 대상 주소
            graph: 거래 그래프 G = (V, E, W, T)
            transactions: 거래 리스트 (타임스탬프 포함)
        
        Returns:
            Nθ(vi) ∈ [0, 1] - 0에 가까울수록 시간적 균형, 1에 가까울수록 비대칭
        """
        if not graph or vertex.lower() not in graph:
            return 0.0
        
        vertex = vertex.lower()
        
        # In-degree timestamps (들어오는 거래의 타임스탬프)
        ts_in = []
        for predecessor in graph.predecessors(vertex):
            edge_data = graph[predecessor][vertex]
            if "transactions" in edge_data:
                for tx in edge_data["transactions"]:
                    ts = self._extract_timestamp(tx.get("timestamp"))
                    if ts > 0:
                        ts_in.append(ts)
        
        # Out-degree timestamps (나가는 거래의 타임스탬프)
        ts_out = []
        for successor in graph.successors(vertex):
            edge_data = graph[vertex][successor]
            if "transactions" in edge_data:
                for tx in edge_data["transactions"]:
                    ts = self._extract_timestamp(tx.get("timestamp"))
                    if ts > 0:
                        ts_out.append(ts)
        
        # 타임스탬프가 없으면 그래프의 거래에서 직접 추출
        if not ts_in or not ts_out:
            ts_in, ts_out = self._extract_timestamps_from_transactions(
                vertex, transactions
            )
        
        if not ts_in or not ts_out:
            return 0.0
        
        # Temporal spread 계산
        # 논문: TS_in(vi) = max(TS_in) - min(TS_in)
        ts_in_spread = max(ts_in) - min(ts_in) if len(ts_in) > 1 else 0
        ts_out_spread = max(ts_out) - min(ts_out) if len(ts_out) > 1 else 0
        
        # 평균 타임스탬프
        ts_in_avg = np.mean(ts_in)
        ts_out_avg = np.mean(ts_out)
        
        # 시간적 비대칭성: 유입과 유출의 시간 차이
        # 세탁 계정은 유입 후 빠르게 유출하므로 시간 차이가 작음
        time_diff = abs(ts_out_avg - ts_in_avg)
        
        # 정규화: 시간 차이를 0~1 범위로 변환
        # 논문의 정규화 방식에 따라 조정
        if ts_in_spread + ts_out_spread > 0:
            # 시간 분포가 넓을수록 정규화 값이 작아짐
            normalized_diff = time_diff / (ts_in_spread + ts_out_spread + 1)
        else:
            # 단일 in/out 거래: 절대 시간 기준으로 판단
            # 1시간 이내 = 즉시 통과 (suspicious), 7일 초과 = safe, 사이는 선형 보간
            RAPID_SEC = 3600        # 1시간
            SAFE_SEC  = 86400 * 7   # 7일
            if time_diff <= RAPID_SEC:
                normalized_diff = 0.0
            elif time_diff >= SAFE_SEC:
                normalized_diff = 1.0
            else:
                normalized_diff = (time_diff - RAPID_SEC) / (SAFE_SEC - RAPID_SEC)
        
        # 세탁 계정은 시간 차이가 작으므로, 작은 값일수록 의심스러움
        # 반대로 변환: 1 - normalized_diff (작은 시간 차이 = 높은 점수)
        n_theta = 1.0 - min(1.0, normalized_diff)
        
        return n_theta
    
    def normalize_weight(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> float:
        """
        Normalized Weight Score (NWS) 계산: Nω(vi)
        
        논문: 거래 금액의 불균형을 측정
        - 들어오는 거래와 나가는 거래의 금액 분포 차이
        - 세탁 계정은 유입과 유출 금액이 불균형적일 수 있음
        
        Args:
            vertex: 분석 대상 주소
            graph: 거래 그래프 G = (V, E, W, T)
            transactions: 거래 리스트 (금액 포함)
        
        Returns:
            Nω(vi) ∈ [0, 1] - 0에 가까울수록 균형, 1에 가까울수록 불균형
        """
        if not graph or vertex.lower() not in graph:
            return 0.0
        
        vertex = vertex.lower()
        
        # In-degree weights (들어오는 거래의 금액)
        weights_in = []
        for predecessor in graph.predecessors(vertex):
            edge_data = graph[predecessor][vertex]
            weight = edge_data.get("weight", 0)
            if weight > 0:
                weights_in.append(weight)
        
        # Out-degree weights (나가는 거래의 금액)
        weights_out = []
        for successor in graph.successors(vertex):
            edge_data = graph[vertex][successor]
            weight = edge_data.get("weight", 0)
            if weight > 0:
                weights_out.append(weight)
        
        # 금액이 없으면 거래에서 직접 추출
        if not weights_in or not weights_out:
            weights_in, weights_out = self._extract_weights_from_transactions(
                vertex, transactions
            )
        
        if not weights_in or not weights_out:
            return 0.0
        
        # 총 금액
        total_in = sum(weights_in)
        total_out = sum(weights_out)
        
        # 평균 금액
        avg_in = np.mean(weights_in) if weights_in else 0
        avg_out = np.mean(weights_out) if weights_out else 0
        
        # 금액 불균형 계산
        # 논문: 유입과 유출의 금액 차이를 측정
        if total_in + total_out > 0:
            # 비율 차이
            ratio_in = total_in / (total_in + total_out)
            ratio_out = total_out / (total_in + total_out)
            
            # 불균형도: 비율 차이의 절댓값
            imbalance = abs(ratio_in - ratio_out)
        else:
            imbalance = 0.0
        
        # 평균 금액 차이도 고려
        if avg_in + avg_out > 0:
            avg_imbalance = abs(avg_in - avg_out) / (avg_in + avg_out)
        else:
            avg_imbalance = 0.0
        
        # 정규화: 불균형도를 0~1 범위로 변환
        # 논문의 정규화 방식
        n_omega = (imbalance + avg_imbalance) / 2.0
        
        return min(1.0, n_omega)
    
    def _extract_timestamp(self, timestamp: Any) -> int:
        """타임스탬프를 정수로 변환"""
        if isinstance(timestamp, int):
            return timestamp
        elif isinstance(timestamp, str):
            try:
                from datetime import datetime
                if 'T' in timestamp or ' ' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return int(dt.timestamp())
                else:
                    return int(timestamp)
            except:
                return 0
        return 0
    
    def _extract_timestamps_from_transactions(
        self,
        vertex: str,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[int], List[int]]:
        """거래 리스트에서 타임스탬프 추출"""
        vertex = vertex.lower()
        ts_in = []
        ts_out = []
        
        for tx in transactions:
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            ts = self._extract_timestamp(tx.get("timestamp"))
            
            if ts > 0:
                if to_addr == vertex:
                    ts_in.append(ts)
                elif from_addr == vertex:
                    ts_out.append(ts)
        
        return ts_in, ts_out
    
    def _extract_weights_from_transactions(
        self,
        vertex: str,
        transactions: List[Dict[str, Any]]
    ) -> Tuple[List[float], List[float]]:
        """거래 리스트에서 금액 추출 (USD 우선, 없으면 Wei 사용)"""
        vertex = vertex.lower()
        weights_in = []
        weights_out = []
        
        for tx in transactions:
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            
            # USD 값 우선, 없으면 Wei 값 사용 (정규화를 위해 1e18로 나눔)
            usd_value = float(tx.get("usd_value", tx.get("amount_usd", 0)))
            if usd_value > 0:
                weight = usd_value
            else:
                # Wei 단위 값을 사용 (1 ETH = 1e18 Wei)
                wei_value = float(tx.get("value", 0))
                if wei_value > 0:
                    # Wei를 ETH로 변환 (정규화)
                    weight = wei_value / 1e18
                else:
                    continue  # 값이 없으면 스킵
            
            if weight > 0:
                if to_addr == vertex:
                    weights_in.append(weight)
                elif from_addr == vertex:
                    weights_out.append(weight)
        
        return weights_in, weights_out
    
    def calculate_feature_vector(
        self,
        vertex: str,
        graph: nx.DiGraph,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        논문의 F(θ,ω) 피처 벡터 계산
        
        Args:
            vertex: 분석 대상 주소
            graph: 거래 그래프
            transactions: 거래 리스트
        
        Returns:
            {
                "n_theta": float,  # Nθ(vi)
                "n_omega": float,   # Nω(vi)
                "feature_vector": List[float]  # F(θ,ω)
            }
        """
        n_theta = self.normalize_timestamp(vertex, graph, transactions)
        n_omega = self.normalize_weight(vertex, graph, transactions)
        
        # 논문의 F(θ,ω) = [Nθ(vi), Nω(vi)]
        feature_vector = [n_theta, n_omega]
        
        return {
            "n_theta": n_theta,
            "n_omega": n_omega,
            "feature_vector": feature_vector
        }

