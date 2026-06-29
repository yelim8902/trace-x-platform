#!/usr/bin/env python3
"""
레거시 features 라벨을 거래 데이터와 매칭 (테스트용)

사용법:
    # 작은 샘플 테스트 (10%, 주소당 최대 50건)
    python scripts/match_legacy_labels.py
    
    # 더 작은 샘플
    python scripts/match_legacy_labels.py --sample-ratio 0.05 --max-txs-per-contract 20
"""
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.dataset_builder import DatasetBuilder
from tqdm import tqdm


def match_legacy_labels(
    features_path: str,
    transactions_dir: str,
    output_path: str,
    max_transactions_per_contract: int = None,
    sample_ratio: float = 1.0
) -> List[Dict[str, Any]]:
    """
    레거시 features 라벨을 거래 데이터와 매칭
    
    Args:
        features_path: features CSV 파일 경로
        transactions_dir: 거래 데이터 디렉토리
        output_path: 출력 JSON 파일 경로
        max_transactions_per_contract: 주소당 최대 거래 수 (None이면 모두)
        sample_ratio: 샘플링 비율 (1.0 = 100%, 0.1 = 10%)
    
    Returns:
        학습 데이터셋 리스트
    """
    print("=" * 60)
    print("레거시 라벨 매칭 시작 (테스트 모드)")
    print("=" * 60)
    
    # Features 로드
    print(f"\n📂 Features 파일 로드: {features_path}")
    df = pd.read_csv(features_path)
    print(f"   총 {len(df)}개 주소")
    
    # 이더리움만 필터링
    df_eth = df[df['Chain'].str.lower() == 'ethereum'].copy()
    print(f"   이더리움: {len(df_eth)}개 주소")
    
    # 샘플링 (테스트용)
    if sample_ratio < 1.0:
        df_eth = df_eth.sample(frac=sample_ratio, random_state=42)
        print(f"   샘플링: {len(df_eth)}개 주소 ({sample_ratio*100:.0f}%)")
    
    # 라벨 분포 확인
    label_counts = df_eth['label'].value_counts()
    print(f"\n📊 라벨 분포:")
    print(f"   Normal (0): {label_counts.get(0, 0)}개")
    print(f"   Fraud (1): {label_counts.get(1, 0)}개")
    
    # 데이터셋 구축기 생성
    builder = DatasetBuilder()
    
    dataset = []
    transactions_dir_path = Path(transactions_dir)
    processed_count = 0
    skipped_count = 0
    
    print(f"\n🔄 거래 데이터 매칭 중...")
    print(f"   주소당 최대 거래 수: {max_transactions_per_contract or '제한 없음'}")
    
    # 진행 상황 표시
    for idx, row in tqdm(df_eth.iterrows(), total=len(df_eth), desc="주소 처리"):
        chain = row['Chain'].lower()
        contract = row['Contract']
        label = int(row.get('label', 0))
        
        # 거래 데이터 파일 경로
        tx_file = transactions_dir_path / chain / f"{contract}.csv"
        
        if not tx_file.exists():
            skipped_count += 1
            continue
        
        try:
            # 거래 데이터 읽기
            df_tx = pd.read_csv(tx_file)
            
            # 최대 거래 수 제한
            if max_transactions_per_contract and len(df_tx) > max_transactions_per_contract:
                df_tx = df_tx.sample(n=max_transactions_per_contract, random_state=42)
            
            # 거래 데이터 변환
            transactions = []
            for _, tx_row in df_tx.iterrows():
                tx = {
                    "tx_hash": str(tx_row.get("transaction_hash", "")),
                    "from": str(tx_row.get("from", "")),
                    "to": str(tx_row.get("to", "")),
                    "timestamp": int(tx_row.get("timestamp", 0)) if pd.notna(tx_row.get("timestamp")) else 0,
                    "usd_value": 0.0,  # USD 변환 필요 (선택적)
                    "chain": chain,
                    "asset_contract": contract,
                    "block_height": int(tx_row.get("block_number", 0)) if pd.notna(tx_row.get("block_number")) else 0,
                }
                transactions.append(tx)
            
            if not transactions:
                skipped_count += 1
                continue
            
            # 각 거래에 대해 룰 평가 및 데이터셋 추가
            for tx in transactions:
                # 룰 평가용 데이터 변환
                tx_for_eval = builder._convert_transaction(tx)
                
                # 룰 평가
                rule_results = builder.rule_evaluator.evaluate_single_transaction(tx_for_eval)
                
                # 실제 리스크 점수 계산 (라벨 기반)
                actual_score = builder._label_to_score(label)
                
                # 컨텍스트
                tx_context = {
                    "amount_usd": tx.get("usd_value", 0),
                    "is_sanctioned": False,  # features에는 없음
                    "is_mixer": False,  # features에는 없음
                    "chain": chain,
                }
                
                dataset.append({
                    "rule_results": rule_results,
                    "actual_risk_score": actual_score,
                    "tx_context": tx_context,
                    "ground_truth_label": "fraud" if label == 1 else "normal",
                    "tx_hash": tx.get("tx_hash", ""),
                    "chain": chain,
                    "contract": contract,
                    "data_source": "legacy_features"
                })
            
            processed_count += 1
        
        except Exception as e:
            print(f"\n⚠️  에러 ({contract}): {e}")
            skipped_count += 1
            continue
    
    # 저장
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 데이터셋 저장 중: {output_path}")
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 매칭 완료!")
    print(f"   처리된 주소: {processed_count}개")
    print(f"   건너뛴 주소: {skipped_count}개")
    print(f"   총 샘플 수: {len(dataset)}개")
    
    # 최종 통계
    if dataset:
        fraud_count = sum(1 for d in dataset if d['ground_truth_label'] == 'fraud')
        normal_count = sum(1 for d in dataset if d['ground_truth_label'] == 'normal')
        
        print(f"\n📊 최종 라벨 분포:")
        print(f"   Fraud: {fraud_count}개 ({fraud_count/len(dataset)*100:.1f}%)")
        print(f"   Normal: {normal_count}개 ({normal_count/len(dataset)*100:.1f}%)")
    
    return dataset


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="레거시 features 라벨을 거래 데이터와 매칭")
    parser.add_argument(
        "--features-path",
        default="legacy/data/features/ethereum_basic_metrics_processed.csv",
        help="Features CSV 파일 경로"
    )
    parser.add_argument(
        "--transactions-dir",
        default="legacy/data/transactions",
        help="거래 데이터 디렉토리"
    )
    parser.add_argument(
        "--output-path",
        default="data/dataset/legacy_ethereum_test.json",
        help="출력 JSON 파일 경로"
    )
    parser.add_argument(
        "--max-txs-per-contract",
        type=int,
        default=50,
        help="주소당 최대 거래 수 (기본값: 50, 테스트용)"
    )
    parser.add_argument(
        "--sample-ratio",
        type=float,
        default=0.1,
        help="샘플링 비율 (기본값: 0.1 = 10%, 테스트용)"
    )
    
    args = parser.parse_args()
    
    # 매칭 실행
    dataset = match_legacy_labels(
        features_path=args.features_path,
        transactions_dir=args.transactions_dir,
        output_path=args.output_path,
        max_transactions_per_contract=args.max_txs_per_contract,
        sample_ratio=args.sample_ratio
    )
    
    print(f"\n📁 결과 파일: {args.output_path}")
    print(f"\n💡 다음 단계:")
    print(f"   전체 데이터 처리: python scripts/match_legacy_labels.py --sample-ratio 1.0 --max-txs-per-contract 100")
    print(f"   데이터셋 분할: python scripts/split_dataset.py")


if __name__ == "__main__":
    main()

