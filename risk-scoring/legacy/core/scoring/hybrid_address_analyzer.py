"""
하이브리드 주소 분석기

Rule-based 스코어링 + MPOCryptoML 방법론 통합
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import networkx as nx

from .address_analyzer import AddressAnalyzer, AddressAnalysisResult
from ..aggregation.mpocryptml_scorer import MPOCryptoMLScorer
from ..data.lists import ListLoader


@dataclass
class HybridAddressAnalysisResult(AddressAnalysisResult):
    """하이브리드 주소 분석 결과"""
    rule_score: float = 0.0  # Rule-based 점수
    ml_score: float = 0.0    # MPOCryptoML 점수
    ml_details: Dict[str, Any] = field(default_factory=dict)  # MPOCryptoML 상세 정보


class HybridAddressAnalyzer:
    """
    하이브리드 주소 분석기
    
    Rule-based (70%) + MPOCryptoML (30%) 통합 스코어링
    """
    
    def __init__(
        self,
        rules_path: str = "rules/tracex_rules.yaml",
        rule_weight: float = 0.7,
        ml_weight: float = 0.3,
        use_ml: bool = True
    ):
        """
        Args:
            rules_path: 룰북 YAML 파일 경로
            rule_weight: Rule-based 점수 가중치 (기본 0.7)
            ml_weight: MPOCryptoML 점수 가중치 (기본 0.3)
            use_ml: MPOCryptoML 사용 여부 (기본 True)
        """
        self.rule_analyzer = AddressAnalyzer(rules_path)
        self.ml_scorer = MPOCryptoMLScorer(
            rule_weight=rule_weight,
            ml_weight=ml_weight
        ) if use_ml else None
        self.list_loader = ListLoader()
        self.use_ml = use_ml
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight
    
    def analyze_address(
        self,
        address: str,
        chain: str,
        transactions: List[Dict[str, Any]],
        transactions_3hop: Optional[List[Dict[str, Any]]] = None,
        time_range: Optional[Dict[str, str]] = None,
        analysis_type: str = "hybrid"  # "basic", "rule_only", "hybrid"
    ) -> HybridAddressAnalysisResult:
        """
        주소의 거래 히스토리를 분석하여 하이브리드 리스크 스코어 계산
        
        Args:
            address: 분석할 주소
            chain: 블록체인 (ethereum, bsc, polygon)
            transactions: 주소의 직접 거래 히스토리
            transactions_3hop: 3-hop까지의 거래 데이터 (MPOCryptoML용)
            time_range: 시간 범위 (선택사항)
            analysis_type: 분석 타입
                - "basic": Rule-based만 사용 (빠름)
                - "rule_only": Rule-based만 사용
                - "hybrid": Rule-based + MPOCryptoML (기본값)
        
        Returns:
            하이브리드 주소 분석 결과
        """
        # 1. Rule-based 분석
        rule_result = self.rule_analyzer.analyze_address(
            address, chain, transactions, time_range, analysis_type="basic"
        )
        rule_score = rule_result.risk_score
        
        # MPOCryptoML 사용 안 함
        if not self.use_ml or analysis_type in ["basic", "rule_only"]:
            return HybridAddressAnalysisResult(
                address=rule_result.address,
                chain=rule_result.chain,
                risk_score=rule_score,
                risk_level=rule_result.risk_level,
                analysis_summary=rule_result.analysis_summary,
                fired_rules=rule_result.fired_rules,
                risk_tags=rule_result.risk_tags,
                transaction_patterns=rule_result.transaction_patterns,
                timeline=rule_result.timeline,
                explanation=rule_result.explanation,
                completed_at=rule_result.completed_at,
                rule_score=rule_score,
                ml_score=0.0,
                ml_details={}
            )
        
        # 2. MPOCryptoML 분석 (3-hop 데이터 필요)
        ml_score = 0.0
        ml_details = {}
        
        if transactions_3hop and len(transactions_3hop) > 0:
            try:
                # 그래프 구축
                graph = self.ml_scorer.build_graph_from_transactions(transactions_3hop)
                
                if graph and graph.number_of_nodes() > 0:
                    # SDN/믹서 리스트 로드
                    sdn_addresses = self.list_loader.get_sdn_list()
                    mixer_addresses = self.list_loader.get_mixer_list()
                    
                    # 하이브리드 점수 계산
                    hybrid_result = self.ml_scorer.calculate_hybrid_score(
                        rule_score,
                        address,
                        graph,
                        transactions_3hop,
                        sdn_addresses,
                        mixer_addresses
                    )
                    
                    ml_score = hybrid_result["ml_score"]
                    ml_details = hybrid_result["ml_details"]
                    final_score = hybrid_result["final_score"]
                    
                    # 최종 점수 업데이트
                    rule_score = final_score
                    
                    # Risk level 재계산
                    risk_level = self._determine_risk_level(final_score)
                    
                    # Explanation 업데이트
                    explanation = self._generate_hybrid_explanation(
                        rule_result, hybrid_result
                    )
                    
                    # Risk tags 업데이트 (ML 패턴 추가)
                    risk_tags = rule_result.risk_tags.copy()
                    if ml_details.get("detected_patterns"):
                        for pattern in ml_details["detected_patterns"]:
                            risk_tags.append(f"ml_pattern_{pattern}")
                    
                    return HybridAddressAnalysisResult(
                        address=address,
                        chain=chain,
                        risk_score=final_score,
                        risk_level=risk_level,
                        analysis_summary={
                            **rule_result.analysis_summary,
                            "ml_analysis": {
                                "ppr_score": hybrid_result["ml_details"].get("ppr_score", 0),
                                "pattern_score": hybrid_result["ml_details"].get("pattern_score", 0),
                                "detected_patterns": ml_details.get("detected_patterns", [])
                            }
                        },
                        fired_rules=rule_result.fired_rules,
                        risk_tags=risk_tags,
                        transaction_patterns={
                            **rule_result.transaction_patterns,
                            "ml_patterns": ml_details.get("patterns", {})
                        },
                        timeline=rule_result.timeline,
                        explanation=explanation,
                        completed_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                        rule_score=rule_result.risk_score,
                        ml_score=ml_score,
                        ml_details=ml_details
                    )
            except Exception as e:
                # ML 분석 실패 시 Rule-based만 사용
                print(f"⚠️  MPOCryptoML 분석 실패: {e}")
        
        # ML 분석 실패 또는 3-hop 데이터 없음
        return HybridAddressAnalysisResult(
            address=rule_result.address,
            chain=rule_result.chain,
            risk_score=rule_score,
            risk_level=rule_result.risk_level,
            analysis_summary=rule_result.analysis_summary,
            fired_rules=rule_result.fired_rules,
            risk_tags=rule_result.risk_tags,
            transaction_patterns=rule_result.transaction_patterns,
            timeline=rule_result.timeline,
            explanation=rule_result.explanation + " (MPOCryptoML 분석 미적용)",
            completed_at=rule_result.completed_at,
            rule_score=rule_score,
            ml_score=0.0,
            ml_details={"error": "MPOCryptoML analysis not available"}
        )
    
    def _determine_risk_level(self, score: float) -> str:
        """점수 기반 리스크 레벨 결정"""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        else:
            return "low"
    
    def _generate_hybrid_explanation(
        self,
        rule_result: AddressAnalysisResult,
        hybrid_result: Dict[str, Any]
    ) -> str:
        """하이브리드 분석 설명 생성"""
        base_explanation = rule_result.explanation
        
        ml_details = hybrid_result.get("ml_details", {})
        detected_patterns = ml_details.get("detected_patterns", [])
        
        if detected_patterns:
            pattern_names = {
                "fan_in": "Fan-in 패턴",
                "fan_out": "Fan-out 패턴",
                "gather_scatter": "Gather-scatter 패턴",
                "stack": "Stack 패턴",
                "bipartite": "Bipartite 패턴"
            }
            pattern_desc = ", ".join([
                pattern_names.get(p, p) for p in detected_patterns
            ])
            
            ml_explanation = f" MPOCryptoML 분석 결과 {pattern_desc}이 탐지되었습니다."
            return base_explanation + ml_explanation
        
        return base_explanation

