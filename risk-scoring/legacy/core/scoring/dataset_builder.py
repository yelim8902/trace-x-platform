"""
학습/검증/테스트 데이터셋 구축 모듈

레거시 데이터와 규칙 기반 라벨링을 활용하여 학습 데이터셋 구축
"""
from __future__ import annotations

import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import random

from core.scoring.engine import TransactionScorer, TransactionInput
from core.scoring.address_analyzer import AddressAnalyzer
from core.rules.evaluator import RuleEvaluator


class DatasetBuilder:
    """학습 데이터셋 구축기"""
    
    def __init__(self):
        self.scorer = TransactionScorer()
        self.analyzer = AddressAnalyzer()
        self.rule_evaluator = RuleEvaluator()
    
    def build_from_legacy_features(
        self,
        features_path: str,
        transactions_dir: str,
        output_path: str
    ) -> List[Dict[str, Any]]:
        """
        레거시 features 데이터에서 학습 데이터셋 구축
        
        Args:
            features_path: features CSV 파일 경로 (label 컬럼 포함)
            transactions_dir: 거래 데이터 디렉토리
            output_path: 출력 JSON 파일 경로
        
        Returns:
            학습 데이터셋 리스트
        """
        # Features 로드
        df = pd.read_csv(features_path)
        
        dataset = []
        
        for _, row in df.iterrows():
            chain = row['Chain'].lower()
            contract = row['Contract']
            label = int(row.get('label', 0))  # 0: normal, 1: fraud
            
            # 거래 데이터 로드
            tx_file = Path(transactions_dir) / chain / f"{contract}.csv"
            if not tx_file.exists():
                continue
            
            # 거래 데이터 읽기
            transactions = self._load_transactions_from_csv(tx_file, chain, contract)
            
            if not transactions:
                continue
            
            # 각 거래에 대해 룰 평가
            for tx in transactions:
                rule_results = self.rule_evaluator.evaluate_single_transaction(tx)
                
                # 실제 리스크 점수 계산 (라벨 기반)
                actual_score = self._label_to_score(label)
                
                # 컨텍스트
                tx_context = {
                    "amount_usd": tx.get("usd_value", tx.get("amount_usd", 0)),
                    "is_sanctioned": tx.get("is_sanctioned", False),
                    "is_mixer": tx.get("is_mixer", False),
                    "chain": chain,
                }
                
                dataset.append({
                    "rule_results": rule_results,
                    "actual_risk_score": actual_score,
                    "tx_context": tx_context,
                    "ground_truth_label": "fraud" if label == 1 else "normal",
                    "tx_hash": tx.get("tx_hash", ""),
                    "chain": chain,
                    "contract": contract
                })
        
        # 저장
        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"데이터셋 구축 완료: {len(dataset)}개 샘플")
        return dataset
    
    def build_from_demo_scenarios(
        self,
        demo_dir: str = "demo/transactions",
        output_path: str = "data/dataset/demo_labeled.json"
    ) -> List[Dict[str, Any]]:
        """
        Demo 시나리오 데이터에서 학습 데이터셋 구축
        
        Args:
            demo_dir: demo 거래 데이터 디렉토리
            output_path: 출력 JSON 파일 경로
        
        Returns:
            학습 데이터셋 리스트
        """
        demo_path = Path(demo_dir)
        dataset = []
        
        # 시나리오별 라벨 매핑
        scenario_labels = {
            "high_risk": {"label": "fraud", "score": 85.0},
            "medium_risk": {"label": "suspicious", "score": 60.0},
            "low_risk": {"label": "normal", "score": 15.0},
        }
        
        for tx_file in demo_path.glob("*.json"):
            # 시나리오 타입 추출
            scenario_type = None
            for key in scenario_labels.keys():
                if key in tx_file.stem:
                    scenario_type = key
                    break
            
            if not scenario_type:
                continue
            
            label_info = scenario_labels[scenario_type]
            
            # 거래 데이터 로드
            with open(tx_file, 'r') as f:
                transactions = json.load(f)
            
            # 각 거래에 대해 룰 평가
            for tx in transactions:
                # 트랜잭션 데이터 변환
                tx_data = self._convert_demo_tx(tx)
                
                # 룰 평가
                rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
                
                # 컨텍스트
                tx_context = {
                    "amount_usd": tx.get("amount_usd", 0),
                    "is_sanctioned": tx.get("is_sanctioned", False),
                    "is_mixer": tx.get("is_mixer", False),
                    "chain": tx.get("chain", "ethereum"),
                }
                
                dataset.append({
                    "rule_results": rule_results,
                    "actual_risk_score": label_info["score"],
                    "tx_context": tx_context,
                    "ground_truth_label": label_info["label"],
                    "tx_hash": tx.get("tx_hash", ""),
                    "chain": tx.get("chain", "ethereum"),
                    "scenario": scenario_type
                })
        
        # 저장
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        print(f"Demo 데이터셋 구축 완료: {len(dataset)}개 샘플")
        return dataset
    
    def build_from_rule_based_labeling(
        self,
        transactions: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        규칙 기반 자동 라벨링으로 데이터셋 구축
        
        현재 룰로 스코어링한 결과를 라벨로 사용
        (초기 데이터셋 구축용)
        
        Args:
            transactions: 거래 리스트
            output_path: 출력 파일 경로 (선택적)
        
        Returns:
            학습 데이터셋 리스트
        """
        dataset = []
        
        for tx in transactions:
            # 트랜잭션 데이터 변환
            tx_data = self._convert_transaction(tx)
            
            # 룰 평가
            rule_results = self.rule_evaluator.evaluate_single_transaction(tx_data)
            
            # 규칙 기반 점수 계산 (현재 룰로)
            rule_based_score = sum(r.get("score", 0) for r in rule_results)
            rule_based_score = min(100.0, rule_based_score)
            
            # 라벨 결정
            if rule_based_score >= 60:
                label = "fraud"
            elif rule_based_score >= 30:
                label = "suspicious"
            else:
                label = "normal"
            
            # 컨텍스트
            tx_context = {
                "amount_usd": tx.get("amount_usd", tx.get("usd_value", 0)),
                "is_sanctioned": tx.get("is_sanctioned", False),
                "is_mixer": tx.get("is_mixer", False),
                "chain": tx.get("chain", "ethereum"),
            }
            
            dataset.append({
                "rule_results": rule_results,
                "actual_risk_score": rule_based_score,  # 규칙 기반 점수를 라벨로 사용
                "tx_context": tx_context,
                "ground_truth_label": label,
                "tx_hash": tx.get("tx_hash", ""),
                "chain": tx.get("chain", "ethereum"),
                "labeling_method": "rule_based"
            })
        
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
        
        return dataset
    
    def split_dataset(
        self,
        dataset: List[Dict[str, Any]],
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        stratify: bool = True
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        데이터셋을 학습/검증/테스트로 분할
        
        Args:
            dataset: 전체 데이터셋
            train_ratio: 학습 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            stratify: 라벨별 비율 유지 여부
        
        Returns:
            (train_dataset, val_dataset, test_dataset)
        """
        if stratify:
            # 라벨별로 분할
            fraud_data = [d for d in dataset if d.get("ground_truth_label") == "fraud"]
            suspicious_data = [d for d in dataset if d.get("ground_truth_label") == "suspicious"]
            normal_data = [d for d in dataset if d.get("ground_truth_label") == "normal"]
            
            # 각 라벨별로 분할
            def split_list(lst, train_r, val_r):
                random.shuffle(lst)
                n = len(lst)
                train_end = int(n * train_r)
                val_end = train_end + int(n * val_r)
                return lst[:train_end], lst[train_end:val_end], lst[val_end:]
            
            train_fraud, val_fraud, test_fraud = split_list(fraud_data, train_ratio, val_ratio)
            train_susp, val_susp, test_susp = split_list(suspicious_data, train_ratio, val_ratio)
            train_normal, val_normal, test_normal = split_list(normal_data, train_ratio, val_ratio)
            
            train_dataset = train_fraud + train_susp + train_normal
            val_dataset = val_fraud + val_susp + val_normal
            test_dataset = test_fraud + test_susp + test_normal
            
            random.shuffle(train_dataset)
            random.shuffle(val_dataset)
            random.shuffle(test_dataset)
        else:
            # 랜덤 분할
            random.shuffle(dataset)
            n = len(dataset)
            train_end = int(n * train_ratio)
            val_end = train_end + int(n * val_ratio)
            
            train_dataset = dataset[:train_end]
            val_dataset = dataset[train_end:val_end]
            test_dataset = dataset[val_end:]
        
        return train_dataset, val_dataset, test_dataset
    
    def _load_transactions_from_csv(
        self,
        csv_path: Path,
        chain: str,
        contract: str
    ) -> List[Dict[str, Any]]:
        """CSV 파일에서 거래 데이터 로드"""
        transactions = []
        
        try:
            df = pd.read_csv(csv_path)
            for _, row in df.iterrows():
                tx = {
                    "tx_hash": row.get("transaction_hash", ""),
                    "from": row.get("from", ""),
                    "to": row.get("to", ""),
                    "timestamp": row.get("timestamp", 0),
                    "usd_value": 0.0,  # USD 변환 필요
                    "chain": chain,
                    "asset_contract": contract,
                }
                transactions.append(tx)
        except Exception as e:
            print(f"Error loading {csv_path}: {e}")
        
        return transactions
    
    def _convert_demo_tx(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """Demo 거래 데이터를 룰 평가용 형식으로 변환"""
        return {
            "from": tx.get("from") or tx.get("counterparty_address", ""),
            "to": tx.get("to") or tx.get("target_address", ""),
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", 0.0),
            "chain": tx.get("chain", "ethereum"),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", "unknown"),
            "asset_contract": tx.get("asset_contract", ""),
        }
    
    def _convert_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """일반 거래 데이터를 룰 평가용 형식으로 변환"""
        return {
            "from": tx.get("from") or tx.get("counterparty_address", ""),
            "to": tx.get("to") or tx.get("target_address", ""),
            "tx_hash": tx.get("tx_hash", ""),
            "timestamp": tx.get("timestamp", ""),
            "usd_value": tx.get("amount_usd", tx.get("usd_value", 0.0)),
            "chain": tx.get("chain", "ethereum"),
            "block_height": tx.get("block_height", 0),
            "is_sanctioned": tx.get("is_sanctioned", False),
            "is_known_scam": tx.get("is_known_scam", False),
            "is_mixer": tx.get("is_mixer", False),
            "is_bridge": tx.get("is_bridge", False),
            "label": tx.get("label", "unknown"),
            "asset_contract": tx.get("asset_contract", ""),
        }
    
    def _label_to_score(self, label: int) -> float:
        """라벨을 점수로 변환"""
        if label == 1:  # fraud
            return 85.0
        else:  # normal
            return 15.0


class ExpertLabelingTool:
    """전문가 라벨링 도구"""
    
    def __init__(self, dataset_path: str):
        """
        Args:
            dataset_path: 라벨링할 데이터셋 경로
        """
        self.dataset_path = Path(dataset_path)
        self.labeled_path = self.dataset_path.parent / f"{self.dataset_path.stem}_labeled.json"
    
    def create_labeling_template(self, output_path: str) -> None:
        """라벨링 템플릿 생성"""
        with open(self.dataset_path, 'r') as f:
            dataset = json.load(f)
        
        template = []
        for i, item in enumerate(dataset):
            template.append({
                "id": i,
                "tx_hash": item.get("tx_hash", ""),
                "rule_results": item.get("rule_results", []),
                "rule_based_score": sum(r.get("score", 0) for r in item.get("rule_results", [])),
                "expert_label": None,  # 전문가가 채울 필드
                "expert_score": None,  # 전문가가 채울 필드 (0~100)
                "notes": ""  # 메모
            })
        
        with open(output_path, 'w') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        print(f"라벨링 템플릿 생성: {output_path}")
        print(f"총 {len(template)}개 샘플")
    
    def load_labeled_data(self, labeled_path: str) -> List[Dict[str, Any]]:
        """라벨링된 데이터 로드"""
        with open(labeled_path, 'r') as f:
            labeled = json.load(f)
        
        # 원본 데이터와 병합
        with open(self.dataset_path, 'r') as f:
            original = json.load(f)
        
        # ID로 매칭
        labeled_dict = {item["id"]: item for item in labeled}
        
        merged = []
        for i, item in enumerate(original):
            if i in labeled_dict:
                label_info = labeled_dict[i]
                item["actual_risk_score"] = label_info.get("expert_score", item.get("actual_risk_score", 0))
                item["ground_truth_label"] = self._score_to_label(label_info.get("expert_score", 0))
                item["labeling_method"] = "expert"
                item["expert_notes"] = label_info.get("notes", "")
            
            merged.append(item)
        
        return merged
    
    def _score_to_label(self, score: float) -> str:
        """점수를 라벨로 변환"""
        if score >= 60:
            return "fraud"
        elif score >= 30:
            return "suspicious"
        else:
            return "normal"


# 사용 예시
if __name__ == "__main__":
    builder = DatasetBuilder()
    
    # 방법 1: Demo 시나리오에서 구축
    demo_dataset = builder.build_from_demo_scenarios(
        demo_dir="demo/transactions",
        output_path="data/dataset/demo_labeled.json"
    )
    
    # 방법 2: 레거시 features에서 구축
    # legacy_dataset = builder.build_from_legacy_features(
    #     features_path="legacy/data/features/ethereum_basic_metrics_processed.csv",
    #     transactions_dir="legacy/data/transactions",
    #     output_path="data/dataset/legacy_labeled.json"
    # )
    
    # 방법 3: 규칙 기반 자동 라벨링
    # transactions = [...]  # 거래 리스트
    # rule_based_dataset = builder.build_from_rule_based_labeling(
    #     transactions,
    #     output_path="data/dataset/rule_based_labeled.json"
    # )
    
    # 데이터셋 분할
    train, val, test = builder.split_dataset(demo_dataset)
    
    print(f"학습: {len(train)}개, 검증: {len(val)}개, 테스트: {len(test)}개")

