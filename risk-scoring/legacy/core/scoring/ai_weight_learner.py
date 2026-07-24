"""
AI 기반 룰 가중치 학습 모듈

룰의 특성(axis, severity, 점수, 패턴 유형)을 반영하여 최적의 가중치를 학습
"""
from __future__ import annotations

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import defaultdict

# 머신러닝 라이브러리 (선택적)
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Using simple rule-based weights.")


@dataclass
class RuleFeature:
    """룰 특성"""
    rule_id: str
    axis: str  # C, E, B
    severity: str  # HIGH, MEDIUM, LOW
    base_score: float
    pattern_type: str  # single, window, bucket, topology, stats
    name: str


class RuleWeightLearner:
    """룰 가중치 학습기"""
    
    def __init__(self, use_ai: bool = True):
        """
        Args:
            use_ai: AI 모델 사용 여부 (False면 규칙 기반 가중치 사용)
        """
        self.use_ai = use_ai and SKLEARN_AVAILABLE
        self.model = None
        self.scaler = None
        self.rule_features = self._load_rule_features()
        
        # 규칙 기반 가중치 (AI 없을 때 사용)
        self.rule_based_weights = self._calculate_rule_based_weights()
    
    def _load_rule_features(self) -> Dict[str, RuleFeature]:
        """룰 특성 로드"""
        from ..rules.loader import RuleLoader
        rule_loader = RuleLoader()
        rules = rule_loader.get_rules()
        
        features = {}
        for rule in rules:
            rule_id = rule.get("id")
            if not rule_id:
                continue
            
            # 패턴 유형 결정
            pattern_type = "single"
            if "window" in rule:
                pattern_type = "window"
            elif "bucket" in rule:
                pattern_type = "bucket"
            elif "topology" in rule:
                pattern_type = "topology"
            elif "prerequisites" in rule:
                pattern_type = "stats"
            
            # score 처리 (dynamic인 경우 기본값 사용)
            score_value = rule.get("score", 0)
            if isinstance(score_value, str) and score_value.lower() == "dynamic":
                # dynamic 점수는 기본값 15 사용 (중간값)
                base_score = 15.0
            else:
                try:
                    base_score = float(score_value)
                except (ValueError, TypeError):
                    base_score = 0.0
            
            features[rule_id] = RuleFeature(
                rule_id=rule_id,
                axis=rule.get("axis", "B"),
                severity=rule.get("severity", "MEDIUM"),
                base_score=base_score,
                pattern_type=pattern_type,
                name=rule.get("name", rule_id)
            )
        
        return features
    
    def _calculate_rule_based_weights(self) -> Dict[str, float]:
        """규칙 기반 가중치 계산 (AI 없을 때 사용)"""
        weights = {}
        
        for rule_id, feature in self.rule_features.items():
            weight = 1.0
            
            # Severity 기반 가중치
            if feature.severity == "HIGH":
                weight *= 1.2
            elif feature.severity == "MEDIUM":
                weight *= 1.0
            elif feature.severity == "LOW":
                weight *= 0.8
            
            # Axis 기반 가중치
            if feature.axis == "C":  # Compliance는 중요
                weight *= 1.1
            elif feature.axis == "E":  # Exposure도 중요
                weight *= 1.1
            elif feature.axis == "B":  # Behavior는 상대적으로 덜 중요
                weight *= 0.95
            
            # 패턴 유형 기반 가중치
            if feature.pattern_type == "topology":  # 그래프 패턴은 중요
                weight *= 1.15
            elif feature.pattern_type == "window":  # 시간 패턴도 중요
                weight *= 1.05
            
            weights[rule_id] = weight
        
        return weights
    
    def extract_features(self, rule_results: List[Dict[str, Any]], tx_context: Optional[Dict[str, Any]] = None) -> np.ndarray:
        """
        룰 결과에서 피처 추출
        
        Args:
            rule_results: 발동된 룰 목록
            tx_context: 트랜잭션 컨텍스트 (선택적)
        
        Returns:
            피처 벡터
        """
        # 각 룰에 대한 피처
        feature_vectors = []
        
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            if rule_id not in self.rule_features:
                continue
            
            feature = self.rule_features[rule_id]
            
            # 피처 벡터 생성
            fv = [
                # Axis (one-hot encoding)
                1.0 if feature.axis == "C" else 0.0,
                1.0 if feature.axis == "E" else 0.0,
                1.0 if feature.axis == "B" else 0.0,
                
                # Severity (one-hot encoding)
                1.0 if feature.severity == "HIGH" else 0.0,
                1.0 if feature.severity == "MEDIUM" else 0.0,
                1.0 if feature.severity == "LOW" else 0.0,
                
                # Base score (정규화)
                feature.base_score / 30.0,  # 최대 점수 30으로 정규화
                
                # Pattern type (one-hot encoding)
                1.0 if feature.pattern_type == "single" else 0.0,
                1.0 if feature.pattern_type == "window" else 0.0,
                1.0 if feature.pattern_type == "bucket" else 0.0,
                1.0 if feature.pattern_type == "topology" else 0.0,
                1.0 if feature.pattern_type == "stats" else 0.0,
                
                # 룰 조합 피처 (다른 룰과의 조합)
                self._get_combination_features(rule_id, rule_results),
            ]
            
            feature_vectors.append(fv)
        
        # 여러 룰이 발동된 경우 평균 또는 합산
        if not feature_vectors:
            return np.zeros(15)  # 기본 피처 수
        
        # 룰별 가중치를 피처로 사용
        return np.mean(feature_vectors, axis=0)
    
    def _get_combination_features(self, rule_id: str, all_rules: List[Dict[str, Any]]) -> float:
        """룰 조합 피처 계산"""
        other_rule_ids = [r.get("rule_id") for r in all_rules if r.get("rule_id") != rule_id]
        
        # 위험한 조합 확인
        dangerous_combinations = {
            ("C-001", "E-101"): 1.0,  # 제재 + 믹서
            ("C-001", "B-201"): 0.8,  # 제재 + 레이어링
            ("E-101", "B-202"): 0.9,  # 믹서 + 순환
            ("C-003", "B-101"): 0.5,  # 고액 + Burst
        }
        
        max_combination_score = 0.0
        for (r1, r2), score in dangerous_combinations.items():
            if (rule_id == r1 and r2 in other_rule_ids) or (rule_id == r2 and r1 in other_rule_ids):
                max_combination_score = max(max_combination_score, score)
        
        return max_combination_score
    
    def train(
        self,
        training_data: List[Tuple[List[Dict[str, Any]], float, Optional[Dict[str, Any]]]]
    ) -> None:
        """
        모델 학습
        
        Args:
            training_data: [(rule_results, actual_risk_score, tx_context), ...]
                - rule_results: 발동된 룰 목록
                - actual_risk_score: 실제 리스크 점수 (0~100)
                - tx_context: 트랜잭션 컨텍스트 (선택적)
        """
        if not self.use_ai:
            print("AI 모델 사용 불가. 규칙 기반 가중치 사용.")
            return
        
        # 피처 추출
        X = []
        y = []
        
        for rule_results, actual_score, tx_context in training_data:
            features = self.extract_features(rule_results, tx_context)
            X.append(features)
            y.append(actual_score)
        
        X = np.array(X)
        y = np.array(y)
        
        # 정규화
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # 학습/검증 분할
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        
        # 모델 선택 및 학습
        # 회귀 문제이므로 여러 모델 시도
        models = {
            "gradient_boosting": GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            ),
            "random_forest": RandomForestClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            ),
        }
        
        best_model = None
        best_score = 0.0
        
        for name, model in models.items():
            # 분류 문제로 변환 (리스크 레벨 예측)
            y_train_levels = self._score_to_level(y_train)
            y_val_levels = self._score_to_level(y_val)
            
            model.fit(X_train, y_train_levels)
            score = model.score(X_val, y_val_levels)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        self.model = best_model
        print(f"모델 학습 완료. 검증 정확도: {best_score:.2%}")
    
    def _score_to_level(self, scores: np.ndarray) -> np.ndarray:
        """점수를 리스크 레벨로 변환"""
        levels = []
        for score in scores:
            if score >= 80:
                levels.append(3)  # critical
            elif score >= 60:
                levels.append(2)  # high
            elif score >= 30:
                levels.append(1)  # medium
            else:
                levels.append(0)  # low
        return np.array(levels)
    
    def get_weights(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        룰별 가중치 계산
        
        Args:
            rule_results: 발동된 룰 목록
            tx_context: 트랜잭션 컨텍스트 (선택적)
        
        Returns:
            {rule_id: weight} 딕셔너리
        """
        if not self.use_ai or self.model is None:
            # 규칙 기반 가중치 사용
            return {
                r.get("rule_id"): self.rule_based_weights.get(r.get("rule_id"), 1.0)
                for r in rule_results
            }
        
        # AI 모델로 가중치 예측
        features = self.extract_features(rule_results, tx_context)
        features_scaled = self.scaler.transform([features])
        
        # 예측 (리스크 레벨)
        predicted_level = self.model.predict(features_scaled)[0]
        
        # 레벨에 따른 기본 가중치
        level_weights = {0: 0.8, 1: 1.0, 2: 1.2, 3: 1.5}
        base_weight = level_weights.get(predicted_level, 1.0)
        
        # 룰별 가중치 계산
        weights = {}
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            if rule_id not in self.rule_features:
                weights[rule_id] = 1.0
                continue
            
            feature = self.rule_features[rule_id]
            
            # 규칙 기반 가중치
            rule_weight = self.rule_based_weights.get(rule_id, 1.0)
            
            # AI 예측과 결합
            final_weight = rule_weight * base_weight
            
            weights[rule_id] = final_weight
        
        return weights
    
    def calculate_weighted_score(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        가중치를 적용한 최종 점수 계산
        
        Args:
            rule_results: 발동된 룰 목록
            tx_context: 트랜잭션 컨텍스트 (선택적)
        
        Returns:
            가중치 적용된 최종 점수
        """
        weights = self.get_weights(rule_results, tx_context)
        
        total_score = 0.0
        for rule in rule_results:
            rule_id = rule.get("rule_id")
            base_score = rule.get("score", 0)
            weight = weights.get(rule_id, 1.0)
            
            total_score += base_score * weight
        
        return min(100.0, total_score)


class ContextAwareWeightLearner(RuleWeightLearner):
    """컨텍스트 인식 가중치 학습기"""
    
    def extract_features(
        self,
        rule_results: List[Dict[str, Any]],
        tx_context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """컨텍스트를 포함한 피처 추출"""
        base_features = super().extract_features(rule_results, tx_context)
        
        if tx_context is None:
            return base_features
        
        # 컨텍스트 피처 추가
        context_features = [
            tx_context.get("amount_usd", 0) / 10000.0,  # 정규화된 거래액
            1.0 if tx_context.get("is_sanctioned", False) else 0.0,
            1.0 if tx_context.get("is_mixer", False) else 0.0,
            tx_context.get("address_age_days", 0) / 365.0,  # 정규화된 주소 나이
        ]
        
        return np.concatenate([base_features, context_features])


# 간단한 사용 예시
if __name__ == "__main__":
    learner = RuleWeightLearner(use_ai=False)  # 규칙 기반으로 시작
    
    # 예시: 룰 결과
    rule_results = [
        {"rule_id": "C-001", "score": 30, "axis": "C", "severity": "HIGH"},
        {"rule_id": "E-101", "score": 25, "axis": "E", "severity": "HIGH"},
    ]
    
    # 가중치 계산
    weights = learner.get_weights(rule_results)
    print("룰별 가중치:", weights)
    
    # 가중치 적용 점수
    weighted_score = learner.calculate_weighted_score(rule_results)
    print("가중치 적용 점수:", weighted_score)
    
    # 단순 합산과 비교
    simple_score = sum(r.get("score", 0) for r in rule_results)
    print("단순 합산 점수:", simple_score)

