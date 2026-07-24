#!/usr/bin/env python3
"""
MPOCryptoML 학습용 데이터셋 구축

레거시 데이터에서 3-hop 그래프 구조를 구축하고 MPOCryptoML 피처를 추출

사용법:
    # 레거시 데이터로 MPOCryptoML 데이터셋 구축
    python scripts/build_mpocryptml_dataset.py
    
    # 샘플 테스트
    python scripts/build_mpocryptml_dataset.py --sample-ratio 0.1 --max-txs-per-contract 50
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict
from tqdm import tqdm
import networkx as nx

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.aggregation.mpocryptml_patterns import MPOCryptoMLPatternDetector
from core.aggregation.mpocryptml_scorer import MPOCryptoMLScorer
from core.aggregation.mpocryptml_normalizer import MPOCryptoMLNormalizer
from core.aggregation.ppr_connector import PPRConnector
from core.data.lists import ListLoader

# USD 변환 없이 진행 (Rate limit 이슈로 인해 비활성화)
# MPOCryptoML 학습은 USD 없이도 가능 (PPR, 패턴, N_theta 사용)
USD_CONVERSION_AVAILABLE = False


def build_3hop_graph(
    target_address: str,
    transactions: List[Dict[str, Any]],
    max_hops: int = 3
) -> tuple[nx.DiGraph, List[Dict[str, Any]]]:
    """
    3-hop 그래프 구축
    
    Args:
        target_address: 타겟 주소
        transactions: 타겟 주소의 직접 거래
        max_hops: 최대 홉 수
    
    Returns:
        (graph, transactions_3hop)
    """
    target_address = target_address.lower()
    
    # 1-hop: 타겟 주소의 직접 거래
    hop1_addresses = set()
    transactions_3hop = []
    
    for tx in transactions:
        from_addr = (tx.get("from") or tx.get("counterparty_address", "")).lower()
        to_addr = (tx.get("to") or tx.get("target_address", "")).lower()
        
        if from_addr == target_address:
            hop1_addresses.add(to_addr)
            transactions_3hop.append(tx)
        elif to_addr == target_address:
            hop1_addresses.add(from_addr)
            transactions_3hop.append(tx)
    
    # 2-hop, 3-hop은 현재 데이터로는 제한적
    # 실제로는 백엔드에서 3-hop까지 제공해야 함
    # 여기서는 직접 거래만 사용
    
    # 그래프 구축
    pattern_detector = MPOCryptoMLPatternDetector()
    pattern_detector.build_from_transactions(transactions_3hop)
    
    return pattern_detector.graph, transactions_3hop


def extract_mpocryptml_features(
    target_address: str,
    graph: nx.DiGraph,
    transactions: List[Dict[str, Any]],
    sdn_addresses: Set[str],
    mixer_addresses: Set[str]
) -> Dict[str, Any]:
    """
    MPOCryptoML 피처 추출
    
    Args:
        target_address: 타겟 주소
        graph: 3-hop 그래프
        transactions: 거래 리스트
        sdn_addresses: SDN 리스트
        mixer_addresses: 믹서 리스트
    
    Returns:
        MPOCryptoML 피처 딕셔너리
    """
    if not graph or graph.number_of_nodes() == 0:
        return {
            "ppr_score": 0.0,
            "sdn_ppr": 0.0,
            "mixer_ppr": 0.0,
            "pattern_score": 0.0,
            "n_theta": 0.0,
            "n_omega": 0.0,
            "detected_patterns": [],
            "fan_in_count": 0,
            "fan_out_count": 0,
            "gather_scatter": 0.0
        }
    
    # PPR 점수
    ppr_connector = PPRConnector()
    sdn_list = [addr for addr in sdn_addresses if addr.lower() in graph]
    mixer_list = [addr for addr in mixer_addresses if addr.lower() in graph]
    
    sdn_ppr = 0.0
    mixer_ppr = 0.0
    if sdn_list:
        sdn_ppr = ppr_connector.calculate_ppr(target_address, sdn_list, graph)
    if mixer_list:
        mixer_ppr = ppr_connector.calculate_ppr(target_address, mixer_list, graph)
    
    # Multi-source PPR (소스 노드 자동 탐지)
    ppr_result = ppr_connector.calculate_multi_source_ppr(target_address, graph)
    ppr_score = ppr_result["ppr_score"]
    
    # 패턴 탐지
    pattern_detector = MPOCryptoMLPatternDetector()
    pattern_detector.graph = graph
    patterns = pattern_detector.analyze_address_patterns(target_address)
    
    # 패턴 점수 계산
    pattern_score = 0.0
    detected_patterns = []
    
    if patterns["fan_in"]["pattern"]["is_detected"]:
        pattern_score += 15.0
        detected_patterns.append("fan_in")
    
    if patterns["fan_out"]["pattern"]["is_detected"]:
        pattern_score += 15.0
        detected_patterns.append("fan_out")
    
    # Gather-scatter: fan_in과 fan_out이 동시에 있거나, gather_scatter 값 자체가 임계값 이상
    gather_scatter_value = patterns["gather_scatter"]["value"]
    gather_scatter_count = patterns["gather_scatter"]["count"]
    
    # 패턴 탐지 기준: fan_in과 fan_out이 동시에 탐지되거나, gather_scatter 값이 충분히 큼
    if (patterns["fan_in"]["pattern"]["is_detected"] and patterns["fan_out"]["pattern"]["is_detected"]) or \
       (gather_scatter_value > 0 and gather_scatter_count >= 5):
        pattern_score += 10.0
        detected_patterns.append("gather_scatter")
    
    if patterns["stack_paths"]:
        pattern_score += 20.0
        detected_patterns.append("stack")
    
    if patterns["bipartite"]["is_bipartite"]:
        pattern_score += 15.0
        detected_patterns.append("bipartite")
    
    # Timestamp 정규화
    normalizer = MPOCryptoMLNormalizer()
    n_theta = normalizer.normalize_timestamp(target_address, graph, transactions)
    
    # Weight 정규화
    n_omega = normalizer.normalize_weight(target_address, graph, transactions)
    
    return {
        "ppr_score": ppr_score,
        "sdn_ppr": sdn_ppr,
        "mixer_ppr": mixer_ppr,
        "pattern_score": min(100.0, pattern_score),
        "n_theta": n_theta,
        "n_omega": n_omega,
        "detected_patterns": detected_patterns,
        "fan_in_count": patterns["fan_in"]["count"],
        "fan_out_count": patterns["fan_out"]["count"],
        "gather_scatter": patterns["gather_scatter"]["value"],
        "graph_nodes": graph.number_of_nodes(),
        "graph_edges": graph.number_of_edges()
    }


def build_mpocryptml_dataset(
    features_path: str,
    transactions_dir: str,
    output_path: str,
    max_transactions_per_contract: Optional[int] = None,
    sample_ratio: float = 1.0
) -> List[Dict[str, Any]]:
    """
    MPOCryptoML 학습용 데이터셋 구축
    
    Args:
        features_path: features CSV 파일 경로
        transactions_dir: 거래 데이터 디렉토리
        output_path: 출력 JSON 파일 경로
        max_transactions_per_contract: 주소당 최대 거래 수
        sample_ratio: 샘플링 비율
    
    Returns:
        MPOCryptoML 학습 데이터셋
    """
    print("=" * 60)
    print("MPOCryptoML 학습용 데이터셋 구축")
    print("=" * 60)
    
    # Features 로드
    print(f"\n📂 Features 파일 로드: {features_path}")
    df = pd.read_csv(features_path)
    print(f"   총 {len(df)}개 주소")
    
    # 이더리움만 필터링
    df_eth = df[df['Chain'].str.lower() == 'ethereum'].copy()
    print(f"   이더리움: {len(df_eth)}개 주소")
    
    # 샘플링
    if sample_ratio < 1.0:
        df_eth = df_eth.sample(frac=sample_ratio, random_state=42)
        print(f"   샘플링: {len(df_eth)}개 주소 ({sample_ratio*100:.0f}%)")
    
    # 라벨 분포 확인
    label_counts = df_eth['label'].value_counts()
    print(f"\n📊 라벨 분포:")
    print(f"   Normal (0): {label_counts.get(0, 0)}개")
    print(f"   Fraud (1): {label_counts.get(1, 0)}개")
    
    # SDN/믹서 리스트 로드
    list_loader = ListLoader()
    sdn_addresses = list_loader.get_sdn_list()
    mixer_addresses = list_loader.get_mixer_list()
    print(f"\n📋 리스트 로드:")
    print(f"   SDN: {len(sdn_addresses)}개")
    print(f"   Mixer: {len(mixer_addresses)}개")
    
    dataset = []
    transactions_dir_path = Path(transactions_dir)
    processed_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n🔄 MPOCryptoML 피처 추출 중...")
    print(f"   주소당 최대 거래 수: {max_transactions_per_contract or '제한 없음'}")
    
    for idx, row in tqdm(df_eth.iterrows(), total=len(df_eth), desc="주소 처리"):
        chain = row['Chain'].lower()
        contract = row['Contract']
        label = int(row.get('label', 0))
        
        tx_file = transactions_dir_path / chain / f"{contract}.csv"
        if not tx_file.exists():
            skipped_count += 1
            continue
        
        try:
            # 거래 데이터 로드
            df_tx = pd.read_csv(tx_file)
            if max_transactions_per_contract and len(df_tx) > max_transactions_per_contract:
                df_tx = df_tx.sample(n=max_transactions_per_contract, random_state=42)
            
            # 거래 데이터 변환 (USD 변환 없이 진행)
            # MPOCryptoML 학습은 USD 없이도 가능 (PPR, 패턴, N_theta 사용)
            transactions = []
            for _, tx_row in df_tx.iterrows():
                value_wei = int(tx_row.get("value", 0)) if pd.notna(tx_row.get("value")) else 0
                
                # USD 값은 0.0으로 설정 (USD 변환 없이 진행)
                usd_value = 0.0
                
                tx = {
                    "tx_hash": str(tx_row.get("transaction_hash", "")),
                    "from": str(tx_row.get("from", "")),
                    "to": str(tx_row.get("to", "")),
                    "timestamp": int(tx_row.get("timestamp", 0)) if pd.notna(tx_row.get("timestamp")) else 0,
                    "usd_value": usd_value,
                    "value": value_wei,  # 원본 값도 보관
                    "chain": chain,
                    "asset_contract": contract,
                    "block_height": int(tx_row.get("block_number", 0)) if pd.notna(tx_row.get("block_number")) else 0,
                }
                transactions.append(tx)
            
            if not transactions:
                skipped_count += 1
                continue
            
            # 3-hop 그래프 구축
            graph, transactions_3hop = build_3hop_graph(contract, transactions)
            
            if not graph or graph.number_of_nodes() == 0:
                skipped_count += 1
                continue
            
            # MPOCryptoML 피처 추출
            ml_features = extract_mpocryptml_features(
                contract,
                graph,
                transactions_3hop,
                sdn_addresses,
                mixer_addresses
            )
            
            # Rule-based 피처도 포함 (기존 데이터셋과 호환)
            from core.scoring.dataset_builder import DatasetBuilder
            builder = DatasetBuilder()
            
            rule_results = []
            for tx in transactions[:10]:  # 샘플만 평가 (속도 향상)
                tx_for_eval = builder._convert_transaction(tx)
                rules = builder.rule_evaluator.evaluate_single_transaction(tx_for_eval)
                if rules:
                    rule_results.extend(rules)
            
            # Rule-based 점수 계산
            rule_score = sum(r.get("score", 0) for r in rule_results)
            rule_score = min(100.0, rule_score)
            
            # 실제 라벨 점수
            actual_score = 85.0 if label == 1 else 15.0
            
            # 데이터셋 항목 생성
            dataset_item = {
                "address": contract,
                "chain": chain,
                "ground_truth_label": "fraud" if label == 1 else "normal",
                "actual_risk_score": actual_score,
                
                # Rule-based 피처
                "rule_results": rule_results,
                "rule_score": rule_score,
                
                # MPOCryptoML 피처
                "ml_features": ml_features,
                
                # 메타데이터
                "num_transactions": len(transactions),
                "graph_nodes": ml_features.get("graph_nodes", 0),
                "graph_edges": ml_features.get("graph_edges", 0),
                "data_source": "legacy_mpocryptml"
            }
            
            dataset.append(dataset_item)
            processed_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"\n⚠️  에러 ({contract}): {e}")
            continue
    
    # 결과 저장
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    # 통계 출력
    print("\n" + "=" * 60)
    print("✅ 데이터셋 구축 완료!")
    print("=" * 60)
    print(f"\n📊 통계:")
    print(f"   처리된 주소: {processed_count}개")
    print(f"   건너뛴 주소: {skipped_count}개")
    print(f"   에러: {error_count}개")
    print(f"   총 샘플: {len(dataset)}개")
    
    if dataset:
        label_dist = {
            "fraud": sum(1 for d in dataset if d["ground_truth_label"] == "fraud"),
            "normal": sum(1 for d in dataset if d["ground_truth_label"] == "normal")
        }
        print(f"\n📈 라벨 분포:")
        print(f"   Fraud: {label_dist['fraud']}개 ({label_dist['fraud']/len(dataset)*100:.1f}%)")
        print(f"   Normal: {label_dist['normal']}개 ({label_dist['normal']/len(dataset)*100:.1f}%)")
        
        # MPOCryptoML 피처 통계
        ml_features_list = [d["ml_features"] for d in dataset]
        avg_ppr = sum(f.get("ppr_score", 0) for f in ml_features_list) / len(ml_features_list)
        avg_pattern = sum(f.get("pattern_score", 0) for f in ml_features_list) / len(ml_features_list)
        print(f"\n📊 MPOCryptoML 피처 평균:")
        print(f"   PPR 점수: {avg_ppr:.4f}")
        print(f"   패턴 점수: {avg_pattern:.2f}")
    
    print(f"\n💾 저장 위치: {output_path}")
    print(f"   파일 크기: {Path(output_path).stat().st_size / 1024 / 1024:.2f} MB")
    
    return dataset


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MPOCryptoML 학습용 데이터셋 구축")
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
        default="data/dataset/mpocryptml_ethereum.json",
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
        help="샘플링 비율 (0.0~1.0)"
    )
    
    args = parser.parse_args()
    
    dataset = build_mpocryptml_dataset(
        features_path=args.features_path,
        transactions_dir=args.transactions_dir,
        output_path=args.output_path,
        max_transactions_per_contract=args.max_txs_per_contract,
        sample_ratio=args.sample_ratio
    )
    
    print("\n✅ 완료!")
    print("\n다음 단계:")
    print("1. 데이터셋 분할: python scripts/split_dataset.py --input data/dataset/mpocryptml_ethereum.json")
    print("2. 모델 학습: python scripts/train_mpocryptml_model.py")


if __name__ == "__main__":
    main()

