"""
트랜잭션 스코어링 엔진

백엔드에서 받은 트랜잭션 정보를 기반으로 AML 스코어링 수행
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from core.rules.evaluator import RuleEvaluator
from core.data.lists import ListLoader


@dataclass
class TransactionInput:
    """백엔드에서 받는 트랜잭션 정보"""
    tx_hash: str
    chain: str
    timestamp: str  # ISO8601 UTC
    block_height: int
    target_address: str
    counterparty_address: str
    label: str  # mixer | bridge | cex | dex | defi | unknown (이전 entity_type)
    is_sanctioned: bool
    is_known_scam: bool
    is_mixer: bool
    is_bridge: bool
    amount_usd: float
    asset_contract: str


@dataclass
class FiredRule:
    """발동된 룰 정보"""
    rule_id: str
    score: float


@dataclass
class ScoringResult:
    """최종 스코어링 결과"""
    target_address: str
    risk_score: float  # 0~100
    risk_level: str  # low | medium | high | critical
    risk_tags: List[str]
    fired_rules: List[FiredRule]
    explanation: str
    completed_at: str  # ISO8601 UTC 형식의 스코어링 완료 시각
    # 백엔드 요구 필드
    timestamp: str  # 트랜잭션 타임스탬프 (ISO8601 UTC)
    chain_id: int  # 체인 ID (예: 1=Ethereum, 42161=Arbitrum)
    value: float  # 거래 금액 (USD, amount_usd와 동일)


class TransactionScorer:
    """트랜잭션 스코어링 엔진"""
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml"):
        """
        Args:
            rules_path: 룰북 YAML 파일 경로
        """
        self.rule_evaluator = RuleEvaluator(rules_path)
        self.list_loader = ListLoader()
    
    def score_transaction(self, tx_input: TransactionInput) -> ScoringResult:
        """
        트랜잭션 스코어링 수행
        
        Args:
            tx_input: 백엔드에서 받은 트랜잭션 정보
        
        Returns:
            스코어링 결과
        """
        # 1. 백엔드 정보를 룰 평가용 데이터로 변환
        tx_data = self._convert_to_rule_data(tx_input)
        
        # 2. 룰 평가 (TRACE-X 룰북 기반)
        rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
        
        # 3. 점수 계산
        risk_score = self._calculate_risk_score(rule_results)
        
        # 4. Risk Level 결정
        risk_level = self._determine_risk_level(risk_score)
        
        # 5. Risk Tags 생성
        risk_tags = self._generate_risk_tags(rule_results, tx_input)
        
        # 6. Fired Rules 목록 생성
        fired_rules = [
            FiredRule(rule_id=r["rule_id"], score=r["score"])
            for r in rule_results
        ]
        
        # 7. Explanation 생성
        explanation = self._generate_explanation(tx_input, rule_results, risk_level)
        
        # 8. 완료 시각 생성
        completed_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        
        # 9. chain을 chain_id로 변환 (ethereum -> ETH)
        chain_id = self._convert_chain_to_chain_id(tx_input.chain)
        
        return ScoringResult(
            target_address=tx_input.target_address,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_tags=risk_tags,
            fired_rules=fired_rules,
            explanation=explanation,
            completed_at=completed_at,
            timestamp=tx_input.timestamp,  # 트랜잭션 타임스탬프
            chain_id=chain_id,  # 체인 ID
            value=tx_input.amount_usd  # 거래 금액 (USD)
        )
    
    def _convert_to_rule_data(self, tx: TransactionInput) -> Dict[str, Any]:
        """백엔드 JSON을 룰 평가용 데이터로 변환"""
        # 리스트 로드
        sdn_list = self.list_loader.get_sdn_list()
        mixer_list = self.list_loader.get_mixer_list()
        
        return {
            "from": tx.counterparty_address,
            "to": tx.target_address,
            "tx_hash": tx.tx_hash,
            "timestamp": tx.timestamp,
            "usd_value": tx.amount_usd,
            "chain": tx.chain,
            "block_height": tx.block_height,
            # 백엔드에서 제공하는 라벨 정보 활용
            "is_sanctioned": tx.is_sanctioned,
            "is_known_scam": tx.is_known_scam,
            "is_mixer": tx.is_mixer,
            "is_bridge": tx.is_bridge,
            "label": tx.label,  # 이전 entity_type
            "asset_contract": tx.asset_contract,
        }
    
    def _calculate_risk_score(self, rule_results: List[Dict[str, Any]]) -> float:
        """룰 결과를 기반으로 리스크 점수 계산"""
        # AI 기반 가중치 학습기 사용 (선택적)
        try:
            from .ai_weight_learner import RuleWeightLearner
            if not hasattr(self, '_weight_learner'):
                self._weight_learner = RuleWeightLearner(use_ai=False)  # 규칙 기반으로 시작
            
            # 가중치 적용 점수 계산
            return self._weight_learner.calculate_weighted_score(rule_results)
        except (ImportError, AttributeError):
            # AI 모듈이 없으면 기본 방식 사용
            total_score = sum(r.get("score", 0) for r in rule_results)
            # 0~100 범위로 정규화 (최대 점수는 룰북에 따라 조정)
            return min(100.0, total_score)
    
    def _determine_risk_level(self, score: float) -> str:
        """점수 기반 리스크 레벨 결정"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 30:
            return "medium"
        else:
            return "low"
    
    def _convert_chain_to_chain_id(self, chain: str) -> int:
        """체인 이름을 체인 ID(숫자)로 변환"""
        chain_mapping = {
            "ethereum": 1,
            "arbitrum": 42161,
            "avalanche": 43114,
            "base": 8453,
            "polygon": 137,
            "bsc": 56,
            "fantom": 250,
            "optimism": 10,
            "blast": 81457
        }
        # 소문자로 변환하여 매핑 확인
        chain_lower = chain.lower()
        return chain_mapping.get(chain_lower, 1)  # 기본값: Ethereum (1)
    
    def _generate_risk_tags(
        self,
        rule_results: List[Dict[str, Any]],
        tx: TransactionInput
    ) -> List[str]:
        """Risk Tags 생성"""
        tags = set()
        
        # 룰 로더에서 룰 이름 가져오기
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        # 룰 결과에서 태그 추출
        for result in rule_results:
            rule_id = result.get("rule_id", "")
            rule_name = rule_map.get(rule_id, "").lower()
            
            if "mixer" in rule_name or "E-101" in rule_id:
                tags.add("mixer_inflow")
            if "sanction" in rule_name or "C-001" in rule_id:
                tags.add("sanction_exposure")
            if "scam" in rule_name:
                tags.add("scam_exposure")
            if "high-value" in rule_name or "C-003" in rule_id or "C-004" in rule_id:
                tags.add("high_value_transfer")
            if "bridge" in rule_name:
                tags.add("bridge_large_transfer")
            if "cex" in rule_name:
                tags.add("cex_inflow")
        
        return sorted(list(tags))
    
    def _generate_explanation(
        self,
        tx: TransactionInput,
        rule_results: List[Dict[str, Any]],
        risk_level: str
    ) -> str:
        """설명 텍스트 생성 (입출력 포맷에 맞춤)"""
        if not rule_results:
            return "정상 거래 패턴으로 리스크가 낮습니다."
        
        # 룰 로더에서 룰 이름 가져오기
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        rule_map = {rule.get("id"): rule.get("name", rule.get("id")) for rule in rules if rule.get("id")}
        
        parts = []
        
        # Mixer 관련
        mixer_rules = [r for r in rule_results if "E-101" in r.get("rule_id", "")]
        if mixer_rules or tx.is_mixer:
            amount_text = f"{tx.amount_usd:,.0f}USD 이상" if tx.amount_usd >= 1000 else f"{tx.amount_usd:,.0f}USD"
            parts.append(f"1-hop sanctioned mixer에서 {amount_text} 유입")
        
        # 제재 주소 관련
        sanction_rules = [r for r in rule_results if "C-001" in r.get("rule_id", "")]
        if sanction_rules or tx.is_sanctioned:
            parts.append("제재 대상과 거래")
        
        # 고액 거래 관련
        high_value_rules = [r for r in rule_results if "C-003" in r.get("rule_id", "") or "C-004" in r.get("rule_id", "")]
        if high_value_rules or tx.amount_usd >= 1000:
            parts.append(f"고액 거래 ({tx.amount_usd:,.0f}USD)")
        
        if not parts:
            parts.append("일반 거래")
        
        explanation = ", ".join(parts)
        
        # 리스크 레벨에 따른 설명 추가
        if risk_level == "high" or risk_level == "critical":
            explanation += f"로 인해 세탁 자금 유입 패턴에 해당하여 {risk_level}로 분류됨."
        elif risk_level == "medium":
            explanation += f"로 인해 {risk_level} 리스크로 분류됨."
        else:
            explanation += f"로 인해 {risk_level} 리스크로 분류됨."
        
        return explanation

