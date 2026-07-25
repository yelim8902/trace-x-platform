"""
룰 평가기

TRACE-X 룰북 기반 룰 평가
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional
import statistics
from core.rules.loader import RuleLoader
from core.data.lists import ListLoader
from core.aggregation.window import WindowEvaluator, TransactionHistory
from core.aggregation.bucket import BucketEvaluator
from core.aggregation.ppr_connector import PPRConnector
from core.aggregation.mpocryptml_patterns import MPOCryptoMLPatternDetector
from core.aggregation.stats import StatisticsCalculator
from core.aggregation.topology import TopologyEvaluator


class RuleEvaluator:
    """룰 평가기"""
    
    def __init__(self, rules_path: str = "rules/tracex_rules.yaml", window_evaluator: Optional[WindowEvaluator] = None, bucket_evaluator: Optional[BucketEvaluator] = None):
        """
        Args:
            rules_path: 룰북 YAML 파일 경로
            window_evaluator: 윈도우 평가기 (None이면 새로 생성)
            bucket_evaluator: 버킷 평가기 (None이면 새로 생성)
        """
        self.rule_loader = RuleLoader(rules_path)
        self.list_loader = ListLoader()
        self.ruleset = self.rule_loader.load()
        # lifecycle 룰(B-401/402/403)은 10년치 히스토리가 필요하므로 긴 윈도우 사용
        self.window_evaluator = window_evaluator or WindowEvaluator(
            history=TransactionHistory(max_history_days=3650)
        )
        self.bucket_evaluator = bucket_evaluator or BucketEvaluator()
        self.ppr_connector = PPRConnector()
        self.pattern_detector = None  # 필요 시 생성
        self.stats_calculator = StatisticsCalculator()
        self.topology_evaluator = TopologyEvaluator()
    
    def evaluate_single_transaction(
        self,
        tx_data: Dict[str, Any],
        include_topology: bool = False
    ) -> List[Dict[str, Any]]:
        """
        단일 트랜잭션에 대한 룰 평가
        
        Args:
            tx_data: 트랜잭션 데이터 (from, to, usd_value, timestamp 등)
            include_topology: 그래프 구조 분석 룰 포함 여부 (기본값: False, 성능 최적화)
        
        Returns:
            발동된 룰 목록 [{"rule_id": "...", "score": 30, ...}, ...]
        """
        fired_rules = []
        rules = self.rule_loader.get_rules()
        lists = self.list_loader.get_all_lists()
        
        # 트랜잭션 히스토리에 추가 (윈도우 평가를 위해)
        # target_address를 우선한다 — "to"를 우선하면 송신(outgoing) 거래는 상대방
        # 주소로 히스토리가 쪼개져서, 분석 대상 주소 자신의 버스트/윈도우 집계가 누락된다.
        target_address = tx_data.get("target_address") or tx_data.get("to")
        if target_address:
            self.window_evaluator.history.add_transaction(target_address, tx_data)
        
        for rule in rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            
            # 미지원 룰 타입 건너뛰기
            # state는 아직 미구현
            # bucket은 이제 지원됨
            # prerequisites는 B-103에서 구현됨
            # topology는 B-201, B-202에서 구현됨 (3홉 데이터 필요)
            # E-103은 커스터마이징 항목으로 남김 (백엔드 데이터 필요)
            # B-401, B-402는 state 필드가 있으나 lifecycle으로 구현됨 — state 체크 전에 처리
            if rule_id in ("B-401", "B-402", "B-403A", "B-403B"):
                if self._evaluate_lifecycle_rule(tx_data, rule, lists):
                    if not self._check_exceptions(tx_data, rule, lists):
                        score = rule.get("score", 10)
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(score),
                            "axis": rule.get("axis", "B"),
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "LOW")
                        })
                continue

            if "state" in rule:
                continue  # state 룰은 아직 미구현

            # E-103은 커스터마이징 항목 (백엔드에서 counterparty.risk_score 제공 시 작동)
            if rule_id == "E-103":
                # tag 기반 조건이 없으면 건너뜀 (백엔드 데이터 필요)
                conditions = rule.get("conditions", {})
                if not conditions:
                    continue

            # E-102: PPR로 간접 제재 노출 탐지
            if rule_id == "E-102":
                if self._evaluate_e102_with_ppr(tx_data, rule, lists):
                    # 조건 확인
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    # 예외 확인
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    # 룰 발동
                    score = rule.get("score", 30)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "E"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH"),
                        "source": "PPR"  # PPR 기반 탐지
                    })
                continue  # E-102는 여기서 처리 완료
            
            # B-103: Prerequisites 및 통계 계산 필요
            if rule_id == "B-103":
                if self._evaluate_b103_with_stats(tx_data, rule, lists):
                    # 조건 확인 (interarrival_std는 이미 계산됨)
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    # 예외 확인
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    # 룰 발동
                    score = rule.get("score", 10)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "LOW")
                    })
                continue  # B-103는 여기서 처리 완료
            
            # ── 특금법 신규 룰 특수 처리 ──────────────────────────────────
            # B-504: 심야 집중 거래 (KST 00:00-06:00)
            if rule_id == "B-504":
                if self._evaluate_off_hours_kst(tx_data, rule):
                    if not self._check_exceptions(tx_data, rule, lists):
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(rule.get("score", 10)),
                            "axis": "B",
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "MEDIUM"),
                            "legal_basis": rule.get("legal_basis", ""),
                        })
                continue

            # B-505: CTR 임계값 직하 동일 금액 반복 (스머핑)
            if rule_id == "B-505":
                if self._evaluate_smurfing_below_ctr(tx_data, rule):
                    if not self._check_exceptions(tx_data, rule, lists):
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(rule.get("score", 18)),
                            "axis": "B",
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "HIGH"),
                            "legal_basis": rule.get("legal_basis", ""),
                        })
                continue

            # B-506: 스테이블코인 급속 회전
            if rule_id == "B-506":
                if self._evaluate_stablecoin_rapid_turnover(tx_data, rule, lists):
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(rule.get("score", 15)),
                        "axis": "B",
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "MEDIUM"),
                        "legal_basis": rule.get("legal_basis", ""),
                    })
                continue

            # C-005: CTR 회피 구조화 — 윈도우 기반 처리 (window 키가 있으므로 일반 흐름에서 처리되나
            #         every_lte 집계자가 미구현이므로 별도 처리)
            if rule_id == "C-005":
                if self._evaluate_ctr_avoidance(tx_data, rule):
                    if not self._check_exceptions(tx_data, rule, lists):
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(rule.get("score", 20)),
                            "axis": "C",
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "HIGH"),
                            "legal_basis": rule.get("legal_basis", ""),
                        })
                continue

            # C-006: STR 의심 — 다수 출처 즉시 이체 (rapid_consolidation)
            if rule_id == "C-006":
                if self._evaluate_rapid_consolidation(tx_data, rule):
                    if not self._check_exceptions(tx_data, rule, lists):
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(rule.get("score", 25)),
                            "axis": "C",
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "HIGH"),
                            "legal_basis": rule.get("legal_basis", ""),
                        })
                continue

            # E-106: Travel Rule 미이행 VASP 거래 — 일반 match/condition 흐름으로 처리
            # (특별 로직 불필요, 아래 일반 흐름으로 진입)

            # ─────────────────────────────────────────────────────────
            # B-201, B-202: Topology 기반 룰 (3홉 데이터 필요, 성능 최적화를 위해 옵션)
            if rule_id == "B-201":
                if not include_topology:
                    continue  # 기본 스코어링에서는 제외
                if self._evaluate_topology_rule(tx_data, rule, "layering_chain"):
                    # 조건 확인
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    # 예외 확인
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    # 룰 발동
                    score = rule.get("score", 25)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH")
                    })
                continue
            
            if rule_id == "B-202":
                if not include_topology:
                    continue  # 기본 스코어링에서는 제외
                if self._evaluate_topology_rule(tx_data, rule, "cycle"):
                    # 조건 확인
                    if not self._check_conditions(tx_data, rule, lists):
                        continue
                    # 예외 확인
                    if self._check_exceptions(tx_data, rule, lists):
                        continue
                    # 룰 발동
                    score = rule.get("score", 30)
                    fired_rules.append({
                        "rule_id": rule_id,
                        "score": float(score),
                        "axis": rule.get("axis", "B"),
                        "name": rule.get("name", rule_id),
                        "severity": rule.get("severity", "HIGH")
                    })
                continue
            
            # 버킷 기반 룰인지 확인 (bucket 또는 buckets)
            has_bucket = "bucket" in rule or "buckets" in rule
            
            # B-501: buckets 기반 동적 점수 룰 (특별 처리)
            if rule_id == "B-501":
                buckets_spec = rule.get("buckets")
                if buckets_spec:
                    # 동적 점수 계산
                    field = buckets_spec.get("field", "usd_value")
                    ranges = buckets_spec.get("ranges", [])
                    value = float(tx_data.get(field, 0))
                    
                    # 범위에 맞는 점수 찾기
                    dynamic_score = 0
                    for range_spec in ranges:
                        min_val = range_spec.get("min", 0)
                        max_val = range_spec.get("max", float('inf'))
                        if min_val <= value < max_val:
                            dynamic_score = range_spec.get("score", 0)
                            break
                    
                    # 점수가 0보다 크면 룰 발동
                    if dynamic_score > 0:
                        fired_rules.append({
                            "rule_id": rule_id,
                            "score": float(dynamic_score),
                            "axis": rule.get("axis", "B"),
                            "name": rule.get("name", rule_id),
                            "severity": rule.get("severity", "MEDIUM")
                        })
                continue  # B-501은 여기서 처리 완료
            
            # 윈도우 기반 룰인지 확인
            has_window = "window" in rule or ("aggregations" in rule and not has_bucket)
            
            if has_bucket:
                # 버킷 기반 룰 평가 (B-203, B-204)
                if not self.bucket_evaluator.evaluate_bucket_rule(tx_data, rule):
                    continue
            elif has_window:
                # 윈도우 기반 룰 평가
                if not self.window_evaluator.evaluate_window_rule(tx_data, rule):
                    continue
            else:
                # 단일 트랜잭션 룰 평가
                # 룰 매칭 확인
                if not self._match_rule(tx_data, rule, lists):
                    continue
                
                # 조건 확인
                if not self._check_conditions(tx_data, rule, lists):
                    continue
            
            # 예외 확인
            if self._check_exceptions(tx_data, rule, lists):
                continue
            
            # 룰 발동
            score = rule.get("score", 0)
            # score가 문자열("dynamic" 등)이면 0으로 처리
            if isinstance(score, str):
                try:
                    score = float(score)
                except (ValueError, TypeError):
                    score = 0
            
            fired_rules.append({
                "rule_id": rule_id,
                "score": float(score),
                "axis": rule.get("axis", "B"),
                "name": rule.get("name", rule_id),
                "severity": rule.get("severity", "MEDIUM")
            })
        
        return fired_rules
    
    def _match_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """룰 매칭 확인"""
        match_clause = rule.get("match")
        if not match_clause:
            return True  # match가 없으면 항상 매칭
        
        return self._eval_match_clause(tx_data, match_clause, lists)
    
    def _check_conditions(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """조건 확인"""
        conditions = rule.get("conditions")
        if not conditions:
            return True
        
        return self._eval_conditions(tx_data, conditions, lists)
    
    def _check_exceptions(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """예외 확인 (예외가 있으면 룰 발동 안 함)"""
        exceptions = rule.get("exceptions")
        if not exceptions:
            return False
        
        return self._eval_conditions(tx_data, exceptions, lists)
    
    def _eval_match_clause(
        self,
        tx_data: Dict[str, Any],
        match_clause: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """매칭 절 평가"""
        if "any" in match_clause:
            return any(
                self._eval_single_match(tx_data, item, lists)
                for item in match_clause["any"]
            )
        elif "all" in match_clause:
            return all(
                self._eval_single_match(tx_data, item, lists)
                for item in match_clause["all"]
            )
        else:
            return self._eval_single_match(tx_data, match_clause, lists)
    
    def _eval_single_match(
        self,
        tx_data: Dict[str, Any],
        match_item: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """단일 매칭 항목 평가"""
        if "in_list" in match_item:
            spec = match_item["in_list"]
            field = spec.get("field")
            list_name = spec.get("list")
            value = tx_data.get(field, "").lower() if field else ""
            target_list = lists.get(list_name, set())
            
            # 리스트에 직접 있는지 확인
            if value in target_list:
                return True
            
            # 백엔드에서 제공하는 플래그 활용
            # SDN_LIST: is_sanctioned 플래그 확인
            if list_name == "SDN_LIST" and tx_data.get("is_sanctioned", False):
                return True
            
            # MIXER_LIST: is_mixer 플래그 확인
            if list_name == "MIXER_LIST" and tx_data.get("is_mixer", False):
                return True
            
            return False
        
        return False
    
    def _eval_conditions(
        self,
        tx_data: Dict[str, Any],
        conditions: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """조건 평가"""
        if "all" in conditions:
            return all(
                self._eval_single_condition(tx_data, item, lists)
                for item in conditions["all"]
            )
        elif "any" in conditions:
            return any(
                self._eval_single_condition(tx_data, item, lists)
                for item in conditions["any"]
            )
        else:
            return self._eval_single_condition(tx_data, conditions, lists)
    
    def _evaluate_e102_with_ppr(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """
        E-102 룰 평가: PPR을 사용한 간접 제재 노출 탐지
        
        Args:
            tx_data: 트랜잭션 데이터
            rule: E-102 룰 정의
            lists: 리스트 데이터 (SDN, MIXER 등)
        
        Returns:
            룰 발동 여부
        """
        target_address = tx_data.get("target_address", "") or tx_data.get("to")
        if not target_address:
            return False
        
        # 트랜잭션 히스토리에서 그래프 구축
        # window_evaluator의 history를 활용
        history = self.window_evaluator.history
        
        # 타겟 주소의 트랜잭션 히스토리 가져오기 (최근 365일)
        address_history = history._history.get(target_address.lower(), [])
        
        if len(address_history) < 2:
            # 트랜잭션이 너무 적으면 PPR 계산 불가
            return False
        
        # 그래프 구축
        if self.pattern_detector is None:
            self.pattern_detector = MPOCryptoMLPatternDetector()
        else:
            self.pattern_detector._build_graph()  # 그래프 초기화
        
        # 히스토리 트랜잭션을 그래프에 추가
        for tx in address_history:
            self.pattern_detector.add_transaction(tx)
        
        # 현재 트랜잭션도 추가
        self.pattern_detector.add_transaction(tx_data)
        
        if not self.pattern_detector.graph or target_address.lower() not in self.pattern_detector.graph:
            return False
        
        # SDN 및 믹서 주소 리스트
        sdn_addresses = lists.get("SDN_LIST", set())
        mixer_addresses = lists.get("MIXER_LIST", set())
        
        # PPR 연결성 계산
        ppr_result = self.ppr_connector.calculate_connection_risk(
            target_address,
            self.pattern_detector.graph,
            sdn_addresses,
            mixer_addresses
        )
        
        # 임계값 체크 (PPR >= 0.05면 간접 연결성 높음)
        ppr_threshold = 0.05
        
        return ppr_result["total_ppr"] >= ppr_threshold
    
    def _evaluate_b103_with_stats(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """
        B-103 룰 평가: Prerequisites 및 통계 계산
        
        Args:
            tx_data: 트랜잭션 데이터
            rule: B-103 룰 정의
            lists: 리스트 데이터
        
        Returns:
            룰 발동 여부
        """
        # Prerequisites 체크
        prerequisites = rule.get("prerequisites", [])
        if prerequisites:
            for prereq in prerequisites:
                if "min_edges" in prereq:
                    min_edges = prereq["min_edges"]
                    # 트랜잭션 히스토리에서 거래 수 확인
                    target_address = tx_data.get("target_address", "") or tx_data.get("to")
                    if target_address:
                        history = self.window_evaluator.history
                        address_history = history._history.get(target_address.lower(), [])
                        
                        # 현재 트랜잭션 포함
                        all_transactions = address_history + [tx_data]
                        
                        if not self.stats_calculator.check_prerequisites(all_transactions, min_edges):
                            return False  # Prerequisites 불만족
        
        # 통계 계산
        target_address = tx_data.get("target_address", "") or tx_data.get("to")
        if not target_address:
            return False
        
        history = self.window_evaluator.history
        address_history = history._history.get(target_address.lower(), [])
        
        # 현재 트랜잭션 포함
        all_transactions = address_history + [tx_data]
        
        # 거래 간격 표준편차 계산
        interarrival_std = self.stats_calculator.calculate_interarrival_std(all_transactions)
        
        if interarrival_std is None:
            return False
        
        # tx_data에 계산된 값을 추가 (조건 평가를 위해)
        tx_data["interarrival_std"] = interarrival_std
        
        return True
    
    def _evaluate_topology_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        rule_type: str  # "layering_chain" or "cycle"
    ) -> bool:
        """
        Topology 기반 룰 평가 (B-201, B-202)
        
        Args:
            tx_data: 현재 트랜잭션 데이터
            rule: 룰 정의
            rule_type: 룰 타입 ("layering_chain" or "cycle")
        
        Returns:
            룰 발동 여부
        """
        target_address = tx_data.get("target_address", "") or tx_data.get("to")
        if not target_address:
            return False
        
        # 트랜잭션 히스토리에서 그래프 구축
        # window_evaluator의 history를 활용
        history = self.window_evaluator.history
        
        # 타겟 주소의 트랜잭션 히스토리 가져오기
        address_history = history._history.get(target_address.lower(), [])
        
        # 현재 트랜잭션 포함
        all_transactions = address_history + [tx_data]
        
        # Topology 룰 설정
        topology_spec = rule.get("topology", {})
        
        if rule_type == "layering_chain":
            return self.topology_evaluator.evaluate_layering_chain(
                target_address,
                all_transactions,
                topology_spec
            )
        elif rule_type == "cycle":
            return self.topology_evaluator.evaluate_cycle(
                target_address,
                all_transactions,
                topology_spec
            )
        
        return False
    
    def _eval_single_condition(
        self,
        tx_data: Dict[str, Any],
        condition: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """단일 조건 평가"""
        # gte, lte, gt, lt, eq 등
        for op in ["gte", "lte", "gt", "lt", "eq"]:
            if op in condition:
                spec = condition[op]
                field = spec.get("field")
                value = spec.get("value")
                tx_value = tx_data.get(field, 0)

                if op == "gte":
                    return float(tx_value) >= float(value)
                elif op == "lte":
                    return float(tx_value) <= float(value)
                elif op == "gt":
                    return float(tx_value) > float(value)
                elif op == "lt":
                    return float(tx_value) < float(value)
                elif op == "eq":
                    return tx_value == value

        # tag: 주소 태그 확인 (예: CEX_INTERNAL, MM_BOT — data/lists/address_tags.json)
        if "tag" in condition:
            spec = condition["tag"]
            key = spec.get("key")
            expected = spec.get("equals", True)
            if not key:
                return False

            field = spec.get("field", "address")
            address = self._resolve_tag_address(tx_data, field)
            if not address:
                return False

            tagged_addresses = lists.get(key, set())
            is_tagged = address.lower() in tagged_addresses
            return is_tagged == bool(expected)

        return False

    def _resolve_tag_address(self, tx_data: Dict[str, Any], field: str) -> str:
        """
        tag 조건의 field를 실제 주소 값으로 변환.
        "address"는 윈도우/버킷이 그룹화하는 대상 주소(target_address/to)를 가리키는
        관례적 이름이라 tx_data에 그대로 없는 키이므로 별도로 매핑한다.
        """
        if field == "address":
            return str(tx_data.get("target_address") or tx_data.get("to") or "")
        return str(tx_data.get(field, ""))

    def _evaluate_lifecycle_rule(
        self,
        tx_data: Dict[str, Any],
        rule: Dict[str, Any],
        lists: Dict[str, set]
    ) -> bool:
        """
        B-401, B-402, B-403A, B-403B 평가.
        transaction history에서 생명주기 메트릭을 계산해 tx_data에 주입한 뒤
        기존 _check_conditions()로 평가한다.
        """
        target_address = tx_data.get("target_address", "") or tx_data.get("to")
        if not target_address:
            return False

        history = self.window_evaluator.history
        address_history = history._history.get(target_address.lower(), [])
        all_transactions = address_history + [tx_data]

        metrics = self._compute_lifecycle_metrics(all_transactions, tx_data)
        if not metrics:
            return False

        tx_data.update(metrics)
        return self._check_conditions(tx_data, rule, lists)

    # ──────────────────────────────────────────────────────────────
    # 특금법 신규 룰 평가 메서드
    # ──────────────────────────────────────────────────────────────

    _STABLECOIN_TOKENS = frozenset({
        "usdt", "usdc", "dai", "busd", "tusd", "usdp", "frax", "lusd",
        "0xdac17f958d2ee523a2206206994597c13d831ec7",  # USDT (Ethereum)
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC (Ethereum)
        "0x6b175474e89094c44da98b954eedeac495271d0f",  # DAI (Ethereum)
    })

    def _evaluate_off_hours_kst(self, tx_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """B-504: KST 00:00-06:00 심야 집중 거래 탐지"""
        import datetime
        KST_OFFSET = 9 * 3600  # UTC+9

        ts = tx_data.get("timestamp")
        if not ts:
            return False
        try:
            ts_float = float(ts)
        except (TypeError, ValueError):
            return False

        kst_hour = int((ts_float + KST_OFFSET) % 86400 // 3600)
        if kst_hour >= 6:
            return False  # 심야 시간대가 아님

        target = tx_data.get("target_address", "") or tx_data.get("to")
        if not target:
            return False

        history = self.window_evaluator.history
        window_sec = 21600  # 6시간
        cutoff = ts_float - window_sec
        addr_history = history._history.get(target.lower(), [])
        recent = [
            t for t in addr_history
            if (lambda v: v is not None and float(v) >= cutoff)(
                t.get("timestamp") if isinstance(t.get("timestamp"), (int, float)) else None
            )
        ]
        recent_in_window = []
        for t in recent:
            try:
                t_ts = float(t["timestamp"])
                t_kst_hour = int((t_ts + KST_OFFSET) % 86400 // 3600)
                if t_kst_hour < 6:
                    recent_in_window.append(t)
            except (TypeError, ValueError, KeyError):
                pass
        # 현재 거래 포함
        recent_in_window.append(tx_data)

        if len(recent_in_window) < 5:
            return False
        total_usd = sum(float(t.get("usd_value", 0)) for t in recent_in_window)
        return total_usd >= 1000.0

    def _evaluate_smurfing_below_ctr(self, tx_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """B-505: CTR 임계값($6,000~$7,499) 직하 동일 금액 반복 (스머핑)"""
        usd = float(tx_data.get("usd_value", 0))
        if not (6000.0 <= usd <= 7499.0):
            return False

        target = tx_data.get("target_address", "") or tx_data.get("from")
        if not target:
            return False

        ts = tx_data.get("timestamp")
        try:
            ts_float = float(ts)
        except (TypeError, ValueError):
            return False

        history = self.window_evaluator.history
        cutoff = ts_float - 86400
        addr_history = history._history.get(target.lower(), [])
        matching = []
        for t in addr_history:
            try:
                t_ts = float(t.get("timestamp", 0))
                t_usd = float(t.get("usd_value", 0))
                # 24h 내, 같은 금액 범위($±200), 발신 거래
                if t_ts >= cutoff and 6000.0 <= t_usd <= 7499.0 and abs(t_usd - usd) <= 200:
                    matching.append(t)
            except (TypeError, ValueError):
                pass
        matching.append(tx_data)
        return len(matching) >= 3

    def _evaluate_stablecoin_rapid_turnover(
        self, tx_data: Dict[str, Any], rule: Dict[str, Any], lists: Dict[str, set]
    ) -> bool:
        """B-506: 스테이블코인 수취 후 1시간 내 95% 이상 전송"""
        token = str(tx_data.get("token", "") or tx_data.get("asset_contract", "")).lower()
        is_stablecoin = (
            token in self._STABLECOIN_TOKENS
            or tx_data.get("is_stablecoin", False)
        )
        if not is_stablecoin:
            return False

        usd = float(tx_data.get("usd_value", 0))
        if usd < 500.0:
            return False

        target = tx_data.get("target_address", "") or tx_data.get("to")
        if not target:
            return False

        ts = tx_data.get("timestamp")
        try:
            ts_float = float(ts)
        except (TypeError, ValueError):
            return False

        history = self.window_evaluator.history
        cutoff_receive = ts_float - 3600  # 수취 후 1시간 내
        addr_history = history._history.get(target.lower(), [])

        received_usd = usd  # 현재 거래가 수취
        sent_usd = 0.0
        for t in addr_history:
            try:
                t_ts = float(t.get("timestamp", 0))
                if t_ts < cutoff_receive:
                    continue
                t_usd = float(t.get("usd_value", 0))
                t_from = str(t.get("from", "")).lower()
                t_to = str(t.get("to", "")).lower()
                t_token = str(t.get("token", "") or t.get("asset_contract", "")).lower()
                if t_token not in self._STABLECOIN_TOKENS:
                    continue
                if t_to == target.lower():
                    received_usd += t_usd
                elif t_from == target.lower():
                    sent_usd += t_usd
            except (TypeError, ValueError):
                pass

        if received_usd < 500.0:
            return False
        return sent_usd / received_usd >= 0.95

    def _evaluate_ctr_avoidance(self, tx_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """C-005: 24h 내 $5,000~$7,499 발신 거래 3건 이상 (CTR 회피)"""
        usd = float(tx_data.get("usd_value", 0))
        if not (5000.0 <= usd <= 7499.0):
            return False

        target = tx_data.get("target_address", "") or tx_data.get("from")
        if not target:
            return False

        ts = tx_data.get("timestamp")
        try:
            ts_float = float(ts)
        except (TypeError, ValueError):
            return False

        history = self.window_evaluator.history
        cutoff = ts_float - 86400
        addr_history = history._history.get(target.lower(), [])
        matching = [tx_data]
        for t in addr_history:
            try:
                t_ts = float(t.get("timestamp", 0))
                t_usd = float(t.get("usd_value", 0))
                t_from = str(t.get("from", "")).lower()
                if t_ts >= cutoff and 5000.0 <= t_usd <= 7499.0 and t_from == target.lower():
                    matching.append(t)
            except (TypeError, ValueError):
                pass
        return len(matching) >= 3

    def _evaluate_rapid_consolidation(self, tx_data: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """C-006: 1시간 내 3개+ 출처 수취 후 80%+ 즉시 이체"""
        usd = float(tx_data.get("usd_value", 0))
        target = tx_data.get("target_address", "") or tx_data.get("to")
        if not target or usd < 200:
            return False

        ts = tx_data.get("timestamp")
        try:
            ts_float = float(ts)
        except (TypeError, ValueError):
            return False

        history = self.window_evaluator.history
        cutoff = ts_float - 3600
        addr_history = history._history.get(target.lower(), [])

        senders = set()
        received = usd
        sent = 0.0
        senders.add(str(tx_data.get("from", "")).lower())

        for t in addr_history:
            try:
                t_ts = float(t.get("timestamp", 0))
                if t_ts < cutoff:
                    continue
                t_usd = float(t.get("usd_value", 0))
                t_from = str(t.get("from", "")).lower()
                t_to = str(t.get("to", "")).lower()
                if t_to == target.lower():
                    received += t_usd
                    senders.add(t_from)
                elif t_from == target.lower():
                    sent += t_usd
            except (TypeError, ValueError):
                pass

        if len(senders) < 3 or received < 1000.0:
            return False
        return sent / received >= 0.80

    def _compute_lifecycle_metrics(
        self,
        all_transactions: List[Dict[str, Any]],
        current_tx: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        주소의 생명주기 메트릭 계산.
        모든 값은 보유 중인 transaction history에서 파생된다.
        """
        def parse_ts(val: Any) -> Optional[float]:
            if not val:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            try:
                from datetime import datetime
                s = str(val).replace("Z", "+00:00")
                return datetime.fromisoformat(s).timestamp()
            except Exception:
                try:
                    return float(val)
                except Exception:
                    return None

        timestamps = []
        for tx in all_transactions:
            ts = parse_ts(tx.get("timestamp"))
            if ts is not None:
                timestamps.append(ts)

        if not timestamps:
            return {}

        current_ts = parse_ts(current_tx.get("timestamp")) or max(timestamps)
        first_seen_ts = min(timestamps)
        last_seen_ts = max(timestamps)
        age_days = (current_ts - first_seen_ts) / 86400

        # inactive_days: 현재 거래 직전 마지막 활동과의 간격
        prev_timestamps = [t for t in sorted(timestamps) if t < current_ts]
        inactive_days = (current_ts - prev_timestamps[-1]) / 86400 if prev_timestamps else 0.0

        # first 7일 메트릭
        first7d_cutoff = first_seen_ts + 7 * 86400
        first7d_txs = [
            tx for tx in all_transactions
            if (parse_ts(tx.get("timestamp")) or 0) <= first7d_cutoff
        ]
        first7d_tx_count = len(first7d_txs)
        first7d_usd = sum(float(tx.get("usd_value", 0)) for tx in first7d_txs)

        # 최근 30일 메트릭
        cutoff_30d = current_ts - 30 * 86400
        txs_30d = [
            tx for tx in all_transactions
            if (parse_ts(tx.get("timestamp")) or 0) >= cutoff_30d
        ]
        usd_30d = sorted(float(tx.get("usd_value", 0)) for tx in txs_30d)
        tx_count_30d = len(txs_30d)
        median_usd_30d = statistics.median(usd_30d) if usd_30d else 0.0

        # 전체 메트릭
        all_usd = sorted(float(tx.get("usd_value", 0)) for tx in all_transactions)
        tx_count_total = len(all_transactions)
        total_usd_total = sum(all_usd)
        median_usd_total = statistics.median(all_usd) if all_usd else 0.0

        return {
            "age_days": age_days,
            "inactive_days": inactive_days,
            "first_seen_ts": first_seen_ts,
            "last_seen_ts": last_seen_ts,
            "first7d_tx_count": first7d_tx_count,
            "first7d_usd": first7d_usd,
            "tx_count_30d": tx_count_30d,
            "median_usd_30d": median_usd_30d,
            "tx_count_total": tx_count_total,
            "total_usd_total": total_usd_total,
            "median_usd_total": median_usd_total,
        }

