"""
10단계: ML 스코어러 — 게이팅 + 병렬 표시 아키텍처의 ML 트랙.

`AddressAnalyzer`(룰 엔진)와 완전히 독립적으로 동작하고 서로의 점수에
관여하지 않는다. 최종 API 응답에서 `ml_score`/`ml_risk_level`/
`ml_top_features`로 룰 결과(`risk_score`/`risk_level`/`fired_rules`)와
나란히 표시되며, 두 트랙을 하나의 숫자로 블렌딩하지 않는다
(docs/MODEL_TRAINING.md, docs/DATA_COLLECTION_OVERVIEW.md — 예전 GOG
설계가 룰 플래그를 ML 피처로 섞어 "누가 기여했는지 알 수 없는" 문제를
만든 것에 대한 직접적인 교정).

알려진 한계: `peel_chain_max_length`/`peel_chain_count`는 멀티홉 그래프가
있어야 계산되는데, 이 API는 대상 주소의 1-hop 거래만 입력받으므로 계산이
불가능해 항상 None(NaN)으로 채운다. `HistGradientBoostingClassifier`가
NaN을 자체 분기 조건으로 처리하도록 학습됐고, 9단계 SHAP/permutation
importance 검증에서 이미 이 두 피처의 전역 기여도가 거의 0에 가깝다는
게 확인됐으므로(`docs/MODEL_INTERPRETATION.md`) 실서비스 영향은 제한적
— 단, fan_in_count=0인 예외 케이스에서는 peel chain만이 유일한 신호일
수 있다는 것도 같은 문서에서 확인된 사실이라, 향후 멀티홉 데이터 소스가
붙으면 우선적으로 채워야 할 피처로 기록해둔다.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import shap

from ..aggregation.deviation_features import deviation_features

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models"

# 9단계 SHAP 분석(docs/MODEL_INTERPRETATION.md)에서 그대로 가져온 설명 매핑 —
# 룰북의 "법적 근거" 문구와 나란히 보여줄 ML 쪽 "왜 이 점수인가" 근거.
FEATURE_EXPLANATIONS = {
    "fan_in_count": "여러 주소로부터 자금이 한 곳으로 집중 유입됨 (자금 분산 후 합류 패턴)",
    "fan_out_count": "한 주소에서 여러 주소로 자금이 분산 유출됨",
    "pattern_score": "그래프 구조상 정상 거래 패턴과의 유사도가 낮음",
    "n_omega": "수신 편향 — 보내는 것보다 받는 거래가 두드러짐",
    "n_theta": "다단계 자금 이동 구조 지표",
    "graph_nodes": "이 주소와 연결된 거래 네트워크가 큼 (관련 주소 수 많음)",
    "graph_edges": "이 주소를 둘러싼 거래(엣지) 수가 많음",
    "avg_tx_usd": "평균 거래 금액이 큼",
    "max_tx_usd": "단일 거래 중 최대 금액이 큼",
    "total_sent_usd": "누적 송금액이 큼",
    "total_recv_usd": "누적 수신액이 큼",
    "peel_chain_max_length": "금액이 매 홉마다 줄어드는 자금 세탁 체인(peel chain) 패턴 감지",
    "peel_chain_count": "peel chain 패턴이 여러 건 감지됨",
    "amount_deviation_score": "거래 금액이 이 주소의 평소 패턴 대비 불규칙함",
    "frequency_deviation_score": "거래 발생 간격이 이 주소의 평소 패턴 대비 불규칙함",
}


def _parse_ts(value: Any) -> int:
    """ISO8601 문자열 또는 unix timestamp를 unix int로 변환"""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return int(dt.timestamp())
    except (ValueError, TypeError):
        return 0


class MLScorer:
    """프로덕션 ML 모델(models/ml_risk_model.joblib) 래퍼 — 싱글턴으로 재사용"""

    _instance: Optional["MLScorer"] = None

    def __init__(self):
        self.model = joblib.load(_MODELS_DIR / "ml_risk_model.joblib")
        self.metadata = json.load(open(_MODELS_DIR / "ml_risk_model_metadata.json"))
        self.feature_columns: List[str] = self.metadata["feature_columns"]
        self.log1p_columns = set(self.metadata["log1p_columns"])
        self.risk_bands = self.metadata["risk_bands"]
        self.clf = self.model.named_steps["clf"]
        self.explainer = shap.TreeExplainer(self.clf)

    @classmethod
    def get_instance(cls) -> "MLScorer":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _score_to_level(self, score: float) -> str:
        for band in self.risk_bands:
            if band["min_score"] <= score < band["max_score"]:
                return band["level"]
        return "critical" if score >= 80 else "low"

    @staticmethod
    def _graph_stat_features(sent: List[Dict[str, Any]], received: List[Dict[str, Any]]) -> Dict[str, float]:
        """scripts/extract_features_from_pkl.py의 extract_node_features()와 동일한 정의.
        차이는 멀티홉 그래프가 아니라 대상 주소의 1-hop 거래 리스트에서 직접 계산한다는 것 —
        XBlock의 graph_nodes/graph_edges도 원래 1-hop 이웃 기준이라 정의가 동일하다."""
        fan_in_counterparties = {t["from"] for t in received if t.get("from")}
        fan_out_counterparties = {t["to"] for t in sent if t.get("to")}
        fan_in = len(fan_in_counterparties)
        fan_out = len(fan_out_counterparties)

        sent_usd = [float(t.get("usd", 0)) for t in sent if float(t.get("usd", 0) or 0) > 0]
        recv_usd = [float(t.get("usd", 0)) for t in received if float(t.get("usd", 0) or 0) > 0]
        total_sent = sum(sent_usd)
        total_recv = sum(recv_usd)
        avg_sent = total_sent / len(sent_usd) if sent_usd else 0
        avg_recv = total_recv / len(recv_usd) if recv_usd else 0
        avg_tx_usd = (avg_sent + avg_recv) / 2
        max_tx_usd = max(sent_usd + recv_usd) if (sent_usd or recv_usd) else 0

        total_txn = len(sent_usd) + len(recv_usd)
        denom = fan_in + fan_out
        n_omega = (fan_out / denom) if denom > 0 else 0.5
        n_theta = min(total_txn / 1000.0, 1.0)
        imbalance = abs(fan_out - fan_in) / max(denom, 1)
        fanout_ratio = fan_out / max(total_txn, 1)
        pattern_score = min(100.0, imbalance * 40 + fanout_ratio * 60)

        neighbors = fan_in_counterparties | fan_out_counterparties
        graph_nodes = len(neighbors) + 1
        graph_edges = total_txn

        return {
            "fan_in_count": fan_in, "fan_out_count": fan_out, "pattern_score": pattern_score,
            "n_omega": n_omega, "n_theta": n_theta, "graph_nodes": graph_nodes, "graph_edges": graph_edges,
            "avg_tx_usd": avg_tx_usd, "max_tx_usd": max_tx_usd,
            "total_sent_usd": total_sent, "total_recv_usd": total_recv,
        }

    def score(self, address: str, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Args:
            address: 분석 대상 주소
            transactions: address_analysis.py 라우트가 받는 것과 같은 스키마
                (from/to 또는 counterparty_address/target_address, amount_usd, timestamp)
        """
        address_lower = address.lower()
        sent, received = [], []
        for tx in transactions:
            from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
            to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
            usd = tx.get("amount_usd", 0.0)
            ts = _parse_ts(tx.get("timestamp"))
            if from_addr == address_lower:
                sent.append({"to": to_addr, "usd": usd, "ts": ts})
            if to_addr == address_lower:
                received.append({"from": from_addr, "usd": usd, "ts": ts})

        if not sent and not received:
            return {"ml_score": 0.0, "ml_risk_level": "low", "ml_top_features": []}

        graph_stats = self._graph_stat_features(sent, received)
        dev = deviation_features(sent, received)
        row = {
            **graph_stats,
            "peel_chain_max_length": None,  # 한계: 멀티홉 그래프 필요, 위 모듈 docstring 참고
            "peel_chain_count": None,
            "amount_deviation_score": dev["amount_deviation_score"],
            "frequency_deviation_score": dev["frequency_deviation_score"],
        }

        X = np.full((1, len(self.feature_columns)), np.nan, dtype=float)
        for j, col in enumerate(self.feature_columns):
            v = row.get(col)
            if v is None:
                continue
            X[0, j] = np.log1p(v) if col in self.log1p_columns else v

        proba = float(self.clf.predict_proba(X)[0, 1])
        score = proba * 100
        level = self._score_to_level(score)

        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        shap_row = shap_values[0]
        order = np.argsort(-np.abs(shap_row))[:3]
        top_features = [
            {
                "feature": self.feature_columns[i],
                "value": None if np.isnan(X[0, i]) else round(float(X[0, i]), 4),
                "shap_value": round(float(shap_row[i]), 4),
                "direction": "increases_risk" if shap_row[i] > 0 else "decreases_risk",
                "explanation": FEATURE_EXPLANATIONS.get(self.feature_columns[i], ""),
            }
            for i in order
        ]

        return {
            "ml_score": round(score, 1),
            "ml_risk_level": level,
            "ml_top_features": top_features,
        }
