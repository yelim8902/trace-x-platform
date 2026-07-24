#!/usr/bin/env python3
"""
실제 Etherscan 데이터 수집 스크립트

사용법:
    export ETHERSCAN_API_KEY="your_api_key"
    python scripts/collect_real_data.py
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.real_dataset_builder import RealDatasetBuilder
from core.data.lists import ListLoader


def main():
    """메인 함수"""
    # API 키 확인 (기본값 사용)
    api_key = os.getenv("ETHERSCAN_API_KEY", "91FZVKNIX7GYPESECU5PHPZIMKD72REX43")
    if not api_key:
        print("Error: ETHERSCAN_API_KEY 환경변수를 설정하세요")
        print("예: export ETHERSCAN_API_KEY='your_api_key_here'")
        print("\nAPI 키 발급: https://etherscan.io/apis")
        return
    
    print(f"API 키 사용: {api_key[:10]}...")
    
    print("=" * 60)
    print("실제 Etherscan 데이터 수집 시작")
    print("=" * 60)
    
    # 리스트 로더
    list_loader = ListLoader()
    
    # 고위험 주소 수집
    sdn_list = list(list_loader.get_sdn_list())
    mixer_list = list(list_loader.get_mixer_list())
    
    print(f"\n제재 주소: {len(sdn_list)}개")
    print(f"믹서 주소: {len(mixer_list)}개")
    
    # 데이터셋 구축기 생성
    builder = RealDatasetBuilder(api_key=api_key, chain="ethereum")
    
    # 옵션 선택
    print("\n수집 방법 선택:")
    print("1. 고위험 주소만 (빠름, 불균형)")
    print("2. 고위험 + 정상 주소 (느림, 균형)")
    
    choice = input("선택 (1 또는 2): ").strip()
    
    if choice == "1":
        # 고위험 주소만
        high_risk_addresses = sdn_list[:20] + mixer_list[:20]  # 각 20개씩
        
        print(f"\n고위험 주소 {len(high_risk_addresses)}개에서 거래 수집 중...")
        
        dataset = builder.build_from_high_risk_addresses(
            addresses=high_risk_addresses,
            max_transactions_per_address=50,
            output_path="data/dataset/real_high_risk.json"
        )
        
    elif choice == "2":
        # 고위험 + 정상 주소
        high_risk_addresses = sdn_list[:10] + mixer_list[:10]
        
        # 정상 주소 (CEX 등) - 예시
        normal_addresses = [
            "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",  # Binance
            "0xd551234Ae421e3BCBA99A0Da6d736074f22192FF",  # Binance 2
            "0x564286362092D8e7936f0549571a803B203aAceD",  # Binance 3
            "0x0681d8Db095565FE8A346fA0277bffDE9c0EDbbF",  # Binance 4
            "0xfe9e8709d3215310075d67E3ED32A380CCf451C8",  # Binance 5
        ]
        
        print(f"\n고위험 주소 {len(high_risk_addresses)}개 + 정상 주소 {len(normal_addresses)}개 수집 중...")
        
        dataset = builder.build_from_known_addresses(
            high_risk_addresses=high_risk_addresses,
            normal_addresses=normal_addresses,
            max_transactions_per_address=30,
            output_path="data/dataset/real_balanced.json"
        )
    
    else:
        print("잘못된 선택입니다.")
        return
    
    print("\n" + "=" * 60)
    print("수집 완료!")
    print("=" * 60)
    print(f"\n데이터셋 위치: data/dataset/")
    print(f"총 샘플 수: {len(dataset)}개")
    
    # 통계
    if len(dataset) > 0:
        fraud_count = sum(1 for d in dataset if d['ground_truth_label'] == 'fraud')
        normal_count = sum(1 for d in dataset if d['ground_truth_label'] == 'normal')
        
        print(f"\n라벨 분포:")
        print(f"  Fraud: {fraud_count}개 ({fraud_count/len(dataset)*100:.1f}%)")
        print(f"  Normal: {normal_count}개 ({normal_count/len(dataset)*100:.1f}%)")
    else:
        print("\n⚠️  수집된 데이터가 없습니다.")
        print("   Etherscan API 에러를 확인하세요.")
    
    # 다음 단계 안내
    print("\n다음 단계:")
    print("1. 데이터셋 분할: python scripts/split_dataset.py")
    print("2. AI 모델 학습: python scripts/train_model.py")


if __name__ == "__main__":
    main()

