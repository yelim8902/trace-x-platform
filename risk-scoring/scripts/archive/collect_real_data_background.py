#!/usr/bin/env python3
"""
백그라운드에서 데이터 수집 실행

사용법:
    nohup python scripts/collect_real_data_background.py > logs/collect.log 2>&1 &
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.real_dataset_builder import RealDatasetBuilder
from core.data.lists import ListLoader


def main():
    """백그라운드 실행용 메인 함수"""
    # 로그 디렉토리 생성
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 진행 상황 로그 파일
    progress_file = log_dir / "collection_progress.json"
    
    print("=" * 60)
    print("백그라운드 데이터 수집 시작")
    print(f"로그 파일: {log_dir}/collect.log")
    print(f"진행 상황: {progress_file}")
    print("=" * 60)
    
    # API 키 확인
    api_key = os.getenv("ETHERSCAN_API_KEY", "91FZVKNIX7GYPESECU5PHPZIMKD72REX43")
    
    # 리스트 로더
    list_loader = ListLoader()
    sdn_list = list(list_loader.get_sdn_list())
    mixer_list = list(list_loader.get_mixer_list())
    
    print(f"\n제재 주소: {len(sdn_list)}개")
    print(f"믹서 주소: {len(mixer_list)}개")
    
    # 진행 상황 초기화
    progress = {
        "started_at": datetime.now().isoformat(),
        "status": "running",
        "total_addresses": 0,
        "completed_addresses": 0,
        "collected_transactions": 0,
        "errors": []
    }
    
    try:
        # 데이터셋 구축기 생성
        builder = RealDatasetBuilder(api_key=api_key, chain="ethereum")
        
        # 고위험 주소만 수집 (빠른 테스트용)
        high_risk_addresses = sdn_list[:10] + mixer_list[:10]  # 각 10개씩
        
        progress["total_addresses"] = len(high_risk_addresses)
        
        print(f"\n고위험 주소 {len(high_risk_addresses)}개에서 거래 수집 중...")
        print("백그라운드에서 실행 중입니다. 다른 작업을 진행하셔도 됩니다.")
        
        # 진행 상황 저장
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
        
        # 데이터셋 구축
        dataset = builder.build_from_high_risk_addresses(
            addresses=high_risk_addresses,
            max_transactions_per_address=30,
            output_path="data/dataset/real_high_risk.json"
        )
        
        # 완료
        progress["status"] = "completed"
        progress["completed_at"] = datetime.now().isoformat()
        progress["collected_transactions"] = len(dataset)
        
        print(f"\n✅ 수집 완료!")
        print(f"   총 {len(dataset)}개 샘플")
        
    except Exception as e:
        progress["status"] = "error"
        progress["error"] = str(e)
        progress["errors"].append({
            "time": datetime.now().isoformat(),
            "error": str(e)
        })
        print(f"\n❌ 에러 발생: {e}")
    
    finally:
        # 진행 상황 저장
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    print(f"\n진행 상황 저장: {progress_file}")


if __name__ == "__main__":
    main()

