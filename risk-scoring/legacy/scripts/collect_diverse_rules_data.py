#!/usr/bin/env python3
"""
다양한 룰이 발동되도록 데이터 수집 및 개선

현재 문제: 모든 샘플이 B-501만 발동
해결: 더 많은 룰이 발동되도록 데이터 수집 및 룰 평가 개선
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Set
from tqdm import tqdm
from collections import Counter
import networkx as nx
import numpy as np

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.dataset_builder import DatasetBuilder
from core.data.lists import ListLoader
from core.data.etherscan_client import EtherscanClient


def enhance_transaction_data(
    tx: Dict[str, Any],
    sdn_addresses: Set[str],
    mixer_addresses: Set[str],
    etherscan_client: EtherscanClient = None
) -> Dict[str, Any]:
    """
    거래 데이터를 향상시켜 더 많은 룰이 발동되도록 함
    
    - SDN/Mixer 플래그 추가
    - USD 값 추정 (Wei -> ETH -> USD 대략적 추정)
    - 주소 태그 정보 추가
    """
    from_addr = tx.get("from", "").lower()
    to_addr = tx.get("to", "").lower()
    
    # SDN/Mixer 플래그 추가
    tx["is_sanctioned"] = (from_addr in sdn_addresses or to_addr in sdn_addresses)
    tx["is_mixer"] = (from_addr in mixer_addresses or to_addr in mixer_addresses)
    
    # USD 값 추정 (Wei -> ETH -> USD 대략적 추정)
    # ETH 가격을 2000 USD로 가정 (대략적)
    if tx.get("usd_value", 0) == 0:
        value_wei = tx.get("value", 0)
        if value_wei > 0:
            # Wei -> ETH 변환
            value_eth = value_wei / 1e18
            # ETH -> USD 대략적 추정 (2000 USD/ETH 가정)
            estimated_usd = value_eth * 2000.0
            tx["usd_value"] = estimated_usd
            tx["amount_usd"] = estimated_usd
    
    # 주소 태그 정보 추가 (Etherscan API 사용 가능한 경우)
    if etherscan_client:
        try:
            from_tags = etherscan_client.get_address_tags(from_addr)
            to_tags = etherscan_client.get_address_tags(to_addr)
            
            # 태그 정보를 플래그로 변환
            if from_tags.get("is_exchange") or to_tags.get("is_exchange"):
                tx["is_cex"] = True
            if from_tags.get("is_bridge") or to_tags.get("is_bridge"):
                tx["is_bridge"] = True
        except:
            pass
    
    return tx


def collect_diverse_rules_data(
    features_path: str,
    transactions_dir: str,
    output_path: str,
    max_transactions_per_contract: int = 100,
    sample_ratio: float = 1.0,
    use_etherscan: bool = False
) -> List[Dict[str, Any]]:
    """
    다양한 룰이 발동되도록 데이터 수집
    
    Args:
        features_path: features CSV 파일 경로
        transactions_dir: 거래 데이터 디렉토리
        output_path: 출력 JSON 파일 경로
        max_transactions_per_contract: 주소당 최대 거래 수
        sample_ratio: 샘플링 비율
        use_etherscan: Etherscan API 사용 여부 (Rate limit 주의)
    """
    print("=" * 80)
    print("다양한 룰 발동을 위한 데이터 수집")
    print("=" * 80)
    
    # Features 로드
    print(f"\n📂 Features 파일 로드: {features_path}")
    df = pd.read_csv(features_path)
    df_eth = df[df['Chain'].str.lower() == 'ethereum'].copy()
    
    if sample_ratio < 1.0:
        df_eth = df_eth.sample(frac=sample_ratio, random_state=42)
    
    print(f"   처리할 주소: {len(df_eth)}개")
    
    # 리스트 로드
    list_loader = ListLoader()
    sdn_addresses = list_loader.get_sdn_list()
    mixer_addresses = list_loader.get_mixer_list()
    
    print(f"\n📋 리스트:")
    print(f"   SDN: {len(sdn_addresses)}개")
    print(f"   Mixer: {len(mixer_addresses)}개")
    
    # Etherscan 클라이언트 (선택적)
    etherscan_client = None
    if use_etherscan:
        print("\n⚠️  Etherscan API 사용 (Rate limit 주의)")
        etherscan_client = EtherscanClient()
    
    # 데이터셋 구축기
    builder = DatasetBuilder()
    
    dataset = []
    transactions_dir_path = Path(transactions_dir)
    
    rule_counter = Counter()
    enhanced_count = 0
    
    print(f"\n🔄 데이터 수집 및 향상 중...")
    
    for idx, row in tqdm(df_eth.iterrows(), total=len(df_eth), desc="주소 처리"):
        chain = row['Chain'].lower()
        contract = row['Contract']
        label = int(row.get('label', 0))
        
        tx_file = transactions_dir_path / chain / f"{contract}.csv"
        if not tx_file.exists():
            continue
        
        try:
            df_tx = pd.read_csv(tx_file)
            if max_transactions_per_contract and len(df_tx) > max_transactions_per_contract:
                df_tx = df_tx.sample(n=max_transactions_per_contract, random_state=42)
            
            transactions = []
            for _, tx_row in df_tx.iterrows():
                tx = {
                    "tx_hash": str(tx_row.get("transaction_hash", "")),
                    "from": str(tx_row.get("from", "")),
                    "to": str(tx_row.get("to", "")),
                    "timestamp": int(tx_row.get("timestamp", 0)) if pd.notna(tx_row.get("timestamp")) else 0,
                    "value": int(tx_row.get("value", 0)) if pd.notna(tx_row.get("value")) else 0,
                    "usd_value": 0.0,
                    "chain": chain,
                    "asset_contract": contract,
                    "block_height": int(tx_row.get("block_number", 0)) if pd.notna(tx_row.get("block_number")) else 0,
                }
                
                # 데이터 향상 (SDN/Mixer 플래그, USD 값 추정)
                tx = enhance_transaction_data(tx, sdn_addresses, mixer_addresses, etherscan_client)
                transactions.append(tx)
            
            if not transactions:
                continue
            
            # MPOCryptoML 피처 추출을 위한 그래프 구축
            graph = nx.DiGraph()
            for tx in transactions:
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                weight = tx.get("usd_value", tx.get("value", 0) / 1e18)  # USD 없으면 ETH로
                if from_addr and to_addr and weight > 0:
                    graph.add_edge(from_addr, to_addr, weight=weight, timestamp=tx.get("timestamp", 0))
            
            # MPOCryptoML 피처 계산
            ml_features = {}
            if graph.nodes:
                from core.aggregation.mpocryptml_patterns import MPOCryptoMLPatternDetector
                from core.aggregation.mpocryptml_normalizer import MPOCryptoMLNormalizer
                from core.aggregation.ppr_connector import PPRConnector
                
                ppr_connector = PPRConnector()
                pattern_detector = MPOCryptoMLPatternDetector()
                normalizer = MPOCryptoMLNormalizer()
                
                # PPR
                ppr_result = ppr_connector.calculate_multi_source_ppr(contract, graph, auto_detect_sources=True)
                ml_features["ppr_score"] = ppr_result.get("total_ppr", 0.0)
                ml_features["sdn_ppr"] = ppr_result.get("sdn_ppr", 0.0)
                ml_features["mixer_ppr"] = ppr_result.get("mixer_ppr", 0.0)

                # Patterns
                pattern_detector._build_graph()  # 초기화
                for tx in transactions:
                    pattern_detector.add_transaction(tx)
                
                # contract 주소가 그래프에 있는지 확인
                contract_lower = contract.lower()
                contract_in_graph = contract_lower in pattern_detector.graph.nodes() if pattern_detector.graph else False
                
                # 패턴 탐지 및 점수 계산
                if contract_in_graph:
                    # contract 주소가 그래프에 있으면 해당 주소 사용
                    target_address = contract_lower
                else:
                    # contract 주소가 그래프에 없으면 그래프의 모든 노드에 대한 통계 집계
                    # 가장 많이 연결된 노드를 대표 주소로 사용
                    if pattern_detector.graph and len(pattern_detector.graph.nodes()) > 0:
                        # in_degree + out_degree가 가장 큰 노드 선택
                        max_degree = -1
                        target_address = None
                        for node in pattern_detector.graph.nodes():
                            degree = pattern_detector.graph.in_degree(node) + pattern_detector.graph.out_degree(node)
                            if degree > max_degree:
                                max_degree = degree
                                target_address = node
                        if target_address is None:
                            target_address = list(pattern_detector.graph.nodes())[0]
                    else:
                        target_address = contract_lower
                
                fan_in = pattern_detector.detect_fan_in_pattern(target_address)
                fan_out = pattern_detector.detect_fan_out_pattern(target_address)
                gather_scatter_value = pattern_detector.gather_scatter(target_address)
                gather_scatter_count = pattern_detector.gather_scatter_count(target_address)
                stack_paths = pattern_detector.detect_stack_pattern(target_address)  # 리스트 반환
                bipartite = pattern_detector.detect_bipartite_pattern([target_address])
                
                # 그래프 통계 Feature 추가
                # Fan-in/out 개수 및 값 (항상 계산, contract가 그래프에 없어도 대표 주소 사용)
                ml_features["fan_in_count"] = fan_in.get("fan_in_count", 0)
                ml_features["fan_out_count"] = fan_out.get("fan_out_count", 0)
                ml_features["fan_in_value"] = fan_in.get("total_value", 0.0)
                ml_features["fan_out_value"] = fan_out.get("total_value", 0.0)
                
                # 추가: 그래프 전체 통계 (contract와 무관하게)
                if pattern_detector.graph:
                    # 그래프의 모든 노드에 대한 fan-in/out 집계
                    total_fan_in_count = sum(pattern_detector.graph.in_degree(n) for n in pattern_detector.graph.nodes())
                    total_fan_out_count = sum(pattern_detector.graph.out_degree(n) for n in pattern_detector.graph.nodes())
                    total_fan_in_value = sum(pattern_detector.fan_in(n) for n in pattern_detector.graph.nodes())
                    total_fan_out_value = sum(pattern_detector.fan_out(n) for n in pattern_detector.graph.nodes())
                    
                    # 평균값으로 정규화
                    num_nodes = len(pattern_detector.graph.nodes())
                    if num_nodes > 0:
                        ml_features["avg_fan_in_count"] = total_fan_in_count / num_nodes
                        ml_features["avg_fan_out_count"] = total_fan_out_count / num_nodes
                        ml_features["avg_fan_in_value"] = total_fan_in_value / num_nodes
                        ml_features["avg_fan_out_value"] = total_fan_out_value / num_nodes
                    else:
                        ml_features["avg_fan_in_count"] = 0.0
                        ml_features["avg_fan_out_count"] = 0.0
                        ml_features["avg_fan_in_value"] = 0.0
                        ml_features["avg_fan_out_value"] = 0.0
                else:
                    ml_features["avg_fan_in_count"] = 0.0
                    ml_features["avg_fan_out_count"] = 0.0
                    ml_features["avg_fan_in_value"] = 0.0
                    ml_features["avg_fan_out_value"] = 0.0
                
                # 패턴 점수 계산
                pattern_score = 0.0
                detected_patterns = []
                if fan_in.get("is_detected", False):
                    pattern_score += 10.0
                    detected_patterns.append("fan_in")
                if fan_out.get("is_detected", False):
                    pattern_score += 10.0
                    detected_patterns.append("fan_out")
                # Gather-scatter: fan_in과 fan_out이 동시에 있거나, gather_scatter 값 자체가 임계값 이상
                if (fan_in.get("is_detected", False) and 
                    fan_out.get("is_detected", False)) or \
                   (gather_scatter_value > 0 and gather_scatter_count >= 5):
                    pattern_score += 10.0
                    detected_patterns.append("gather_scatter")
                if isinstance(stack_paths, list) and len(stack_paths) > 0:
                    pattern_score += 10.0
                    detected_patterns.append("stack")
                if bipartite.get("is_bipartite", False):
                    pattern_score += 10.0
                    detected_patterns.append("bipartite")
                
                ml_features["pattern_score"] = pattern_score
                ml_features["fan_in_detected"] = 1 if "fan_in" in detected_patterns else 0
                ml_features["fan_out_detected"] = 1 if "fan_out" in detected_patterns else 0
                ml_features["gather_scatter_detected"] = 1 if "gather_scatter" in detected_patterns else 0
                ml_features["stack_detected"] = 1 if "stack" in detected_patterns else 0
                ml_features["bipartite_detected"] = 1 if "bipartite" in detected_patterns else 0
                
                # 거래 금액 통계 Feature 추가
                import numpy as np
                transaction_values = []
                for tx in transactions:
                    value = tx.get("usd_value", 0)
                    if value > 0:
                        transaction_values.append(value)
                
                if transaction_values:
                    ml_features["avg_transaction_value"] = float(np.mean(transaction_values))
                    ml_features["max_transaction_value"] = float(np.max(transaction_values))
                    ml_features["min_transaction_value"] = float(np.min(transaction_values))
                    ml_features["total_transaction_value"] = float(np.sum(transaction_values))
                    ml_features["transaction_count"] = len(transaction_values)
                else:
                    # USD 값이 없으면 Wei 값 사용 (ETH로 변환)
                    wei_values = []
                    for tx in transactions:
                        wei_value = tx.get("value", 0)
                        if wei_value > 0:
                            eth_value = wei_value / 1e18
                            wei_values.append(eth_value)
                    
                    if wei_values:
                        ml_features["avg_transaction_value"] = float(np.mean(wei_values))
                        ml_features["max_transaction_value"] = float(np.max(wei_values))
                        ml_features["min_transaction_value"] = float(np.min(wei_values))
                        ml_features["total_transaction_value"] = float(np.sum(wei_values))
                        ml_features["transaction_count"] = len(wei_values)
                    else:
                        ml_features["avg_transaction_value"] = 0.0
                        ml_features["max_transaction_value"] = 0.0
                        ml_features["min_transaction_value"] = 0.0
                        ml_features["total_transaction_value"] = 0.0
                        ml_features["transaction_count"] = 0

                # NTS, NWS
                n_theta = normalizer.normalize_timestamp(contract, graph, transactions)
                n_omega = normalizer.normalize_weight(contract, graph, transactions)
                ml_features["n_theta"] = n_theta
                ml_features["n_omega"] = n_omega
            
            # 각 거래에 대해 데이터셋 추가 (룰 평가 결과 제거)
            for tx in transactions:
                # 룰 평가는 학습 시에만 수행 (데이터 누수 방지)
                # 여기서는 룰 평가 결과를 수집만 함 (통계용)
                tx_for_eval = builder._convert_transaction(tx)
                rule_results = builder.rule_evaluator.evaluate_single_transaction(tx_for_eval)
                
                # 발동된 룰 ID 수집 (통계용)
                for rule in rule_results:
                    rule_counter[rule.get("rule_id")] += 1
                
                # 데이터 향상 여부 확인
                if tx.get("is_sanctioned") or tx.get("is_mixer") or tx.get("usd_value", 0) > 0:
                    enhanced_count += 1
                
                actual_score = builder._label_to_score(label)
                
                # 각 거래별 fan-in/out 통계 계산 (거래의 from/to 주소 기준)
                tx_ml_features = ml_features.copy()  # 기본 ML 피처 복사
                
                if pattern_detector.graph:
                    from_addr = tx.get("from", "").lower()
                    to_addr = tx.get("to", "").lower()
                    
                    # from 주소 기준 fan-out 계산
                    if from_addr in pattern_detector.graph.nodes():
                        from_fan_out = pattern_detector.detect_fan_out_pattern(from_addr)
                        tx_ml_features["tx_from_fan_out_count"] = from_fan_out.get("fan_out_count", 0)
                        tx_ml_features["tx_from_fan_out_value"] = from_fan_out.get("total_value", 0.0)
                    else:
                        tx_ml_features["tx_from_fan_out_count"] = 0
                        tx_ml_features["tx_from_fan_out_value"] = 0.0
                    
                    # to 주소 기준 fan-in 계산
                    if to_addr in pattern_detector.graph.nodes():
                        to_fan_in = pattern_detector.detect_fan_in_pattern(to_addr)
                        tx_ml_features["tx_to_fan_in_count"] = to_fan_in.get("fan_in_count", 0)
                        tx_ml_features["tx_to_fan_in_value"] = to_fan_in.get("total_value", 0.0)
                    else:
                        tx_ml_features["tx_to_fan_in_count"] = 0
                        tx_ml_features["tx_to_fan_in_value"] = 0.0
                    
                    # 거래 방향성: from -> to
                    # 거래의 주체 주소를 결정 (from 또는 to 중 더 많은 연결을 가진 주소)
                    if from_addr in pattern_detector.graph.nodes() and to_addr in pattern_detector.graph.nodes():
                        from_degree = pattern_detector.graph.out_degree(from_addr) + pattern_detector.graph.in_degree(from_addr)
                        to_degree = pattern_detector.graph.out_degree(to_addr) + pattern_detector.graph.in_degree(to_addr)
                        primary_address = from_addr if from_degree >= to_degree else to_addr
                    elif from_addr in pattern_detector.graph.nodes():
                        primary_address = from_addr
                    elif to_addr in pattern_detector.graph.nodes():
                        primary_address = to_addr
                    else:
                        primary_address = None
                    
                    if primary_address:
                        primary_fan_in = pattern_detector.detect_fan_in_pattern(primary_address)
                        primary_fan_out = pattern_detector.detect_fan_out_pattern(primary_address)
                        tx_ml_features["tx_primary_fan_in_count"] = primary_fan_in.get("fan_in_count", 0)
                        tx_ml_features["tx_primary_fan_in_value"] = primary_fan_in.get("total_value", 0.0)
                        tx_ml_features["tx_primary_fan_out_count"] = primary_fan_out.get("fan_out_count", 0)
                        tx_ml_features["tx_primary_fan_out_value"] = primary_fan_out.get("total_value", 0.0)
                    else:
                        tx_ml_features["tx_primary_fan_in_count"] = 0
                        tx_ml_features["tx_primary_fan_in_value"] = 0.0
                        tx_ml_features["tx_primary_fan_out_count"] = 0
                        tx_ml_features["tx_primary_fan_out_value"] = 0.0
                else:
                    tx_ml_features["tx_from_fan_out_count"] = 0
                    tx_ml_features["tx_from_fan_out_value"] = 0.0
                    tx_ml_features["tx_to_fan_in_count"] = 0
                    tx_ml_features["tx_to_fan_in_value"] = 0.0
                    tx_ml_features["tx_primary_fan_in_count"] = 0
                    tx_ml_features["tx_primary_fan_in_value"] = 0.0
                    tx_ml_features["tx_primary_fan_out_count"] = 0
                    tx_ml_features["tx_primary_fan_out_value"] = 0.0
                
                # 거래 컨텍스트
                tx_context = {
                    "amount_usd": tx.get("usd_value", 0),
                    "is_sanctioned": tx.get("is_sanctioned", False),
                    "is_mixer": tx.get("is_mixer", False),
                    "chain": chain,
                    "num_transactions": len(transactions),
                    "graph_nodes": graph.number_of_nodes(),
                    "graph_edges": graph.number_of_edges(),
                }
                
                # 데이터셋 추가 (rule_results, rule_score 제거)
                dataset.append({
                    # 원본 트랜잭션 데이터
                    "tx_hash": tx.get("tx_hash", ""),
                    "from": tx.get("from", ""),
                    "to": tx.get("to", ""),
                    "timestamp": tx.get("timestamp", 0),
                    "usd_value": tx.get("usd_value", 0),
                    "value": tx.get("value", 0),  # 원본 Wei 값
                    "chain": chain,
                    "block_height": tx.get("block_height", 0),
                    
                    # 거래 컨텍스트
                    "tx_context": tx_context,
                    
                    # ML 피처 (거래별 통계 포함)
                    "ml_features": tx_ml_features,
                    
                    # Ground truth
                    "ground_truth_label": "fraud" if label == 1 else "normal",
                    "actual_risk_score": actual_score,
                    
                    # 메타데이터
                    "address": contract,
                    "data_source": "legacy_enhanced"
                    
                    # ❌ rule_results 제거 (데이터 누수 방지)
                    # ❌ rule_score 제거 (데이터 누수 방지)
                })
        
        except Exception as e:
            print(f"\n⚠️  에러 ({contract}): {e}")
            continue
    
    print("\n" + "=" * 80)
    print("✅ 데이터 수집 완료!")
    print("=" * 80)
    print(f"\n📊 통계:")
    print(f"   총 샘플: {len(dataset)}개")
    if len(dataset) > 0:
        print(f"   향상된 샘플: {enhanced_count}개 ({enhanced_count/len(dataset)*100:.1f}%)")
    else:
        print(f"   향상된 샘플: {enhanced_count}개")
    
    print(f"\n📈 발동된 룰 분포:")
    for rule_id, count in rule_counter.most_common(10):
        print(f"   {rule_id}: {count}회 ({count/len(dataset)*100:.1f}%)")
    
    # 저장
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 저장 위치: {output_path}")
    print(f"   파일 크기: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    return dataset


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="다양한 룰 발동을 위한 데이터 수집")
    parser.add_argument(
        "--features-path",
        type=str,
        default="legacy/data/features/ethereum_basic_metrics_processed.csv",
        help="Features CSV 파일 경로"
    )
    parser.add_argument(
        "--transactions-dir",
        type=str,
        default="legacy/data/transactions",
        help="거래 데이터 디렉토리"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="data/dataset/diverse_rules.json",
        help="출력 JSON 파일 경로"
    )
    parser.add_argument(
        "--max-txs-per-contract",
        type=int,
        default=100,
        help="주소당 최대 거래 수"
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=1.0,
        help="샘플링 비율 (0.0 ~ 1.0)"
    )
    parser.add_argument(
        "--use-etherscan",
        action="store_true",
        help="Etherscan API 사용 (Rate limit 주의)"
    )
    
    args = parser.parse_args()
    
    dataset = collect_diverse_rules_data(
        features_path=args.features_path,
        transactions_dir=args.transactions_dir,
        output_path=args.output_path,
        max_transactions_per_contract=args.max_txs_per_contract,
        sample_ratio=args.sample_ratio,
        use_etherscan=args.use_etherscan
    )
    
    print("\n✅ 완료!")
    print("\n다음 단계:")
    print("1. 데이터셋 분할: python scripts/split_dataset.py")
    print("2. Rule-based 모델 재학습: python scripts/optimize_rule_based.py")


if __name__ == "__main__":
    main()

