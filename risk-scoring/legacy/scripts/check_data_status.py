#!/usr/bin/env python3
"""
데이터 저장 상태 확인 스크립트

사용법:
    python scripts/check_data_status.py
"""
import json
from pathlib import Path
import sys

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def check_data_status():
    """데이터 상태 확인"""
    dataset_dir = project_root / "data" / "dataset"
    logs_dir = project_root / "logs"
    
    print("=" * 60)
    print("📊 데이터 저장 상태")
    print("=" * 60)
    
    # 데이터셋 파일 확인
    dataset_files = list(dataset_dir.glob("*.json")) if dataset_dir.exists() else []
    
    if not dataset_files:
        print("\n❌ 데이터셋 파일이 없습니다.")
        print(f"   경로: {dataset_dir}")
    else:
        for file in sorted(dataset_files):
            size = file.stat().st_size
            print(f"\n📄 {file.name}")
            print(f"   경로: {file}")
            print(f"   크기: {size:,} bytes ({size/1024:.2f} KB)")
            
            if size > 10:  # 최소한의 데이터가 있는지
                try:
                    with open(file, 'r') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        print(f"   샘플 수: {len(data)}개")
                        
                        if data:
                            # 라벨 분포
                            labels = [d.get("ground_truth_label", "unknown") for d in data]
                            label_counts = {}
                            for label in labels:
                                label_counts[label] = label_counts.get(label, 0) + 1
                            
                            print(f"   라벨 분포:")
                            for label, count in sorted(label_counts.items()):
                                print(f"     {label}: {count}개 ({count/len(data)*100:.1f}%)")
                            
                            # 점수 분포
                            scores = [d.get("actual_risk_score", 0) for d in data if d.get("actual_risk_score")]
                            if scores:
                                print(f"   점수 통계:")
                                print(f"     평균: {sum(scores)/len(scores):.1f}")
                                print(f"     최소: {min(scores):.1f}")
                                print(f"     최대: {max(scores):.1f}")
                    else:
                        print(f"   형식: {type(data).__name__}")
                except json.JSONDecodeError:
                    print("   ⚠️  JSON 파싱 실패")
                except Exception as e:
                    print(f"   ⚠️  로드 실패: {e}")
            else:
                print("   ⚠️  파일이 비어있거나 데이터가 없습니다.")
    
    # 진행 상황 확인
    progress_file = logs_dir / "collection_progress.json"
    if progress_file.exists():
        print("\n" + "=" * 60)
        print("🔄 수집 진행 상황")
        print("=" * 60)
        
        try:
            with open(progress_file, 'r') as f:
                progress = json.load(f)
            
            status = progress.get('status', 'unknown')
            status_emoji = "✅" if status == "completed" else "🔄" if status == "running" else "❌"
            
            print(f"{status_emoji} 상태: {status}")
            print(f"   시작: {progress.get('started_at', 'unknown')}")
            
            if progress.get('total_addresses'):
                completed = progress.get('completed_addresses', 0)
                total = progress.get('total_addresses', 0)
                print(f"   진행: {completed}/{total} 주소 ({completed/total*100:.1f}%)" if total > 0 else f"   진행: {completed}/{total} 주소")
            
            print(f"   수집된 거래: {progress.get('collected_transactions', 0)}개")
            
            if progress.get('errors'):
                print(f"   ⚠️  에러: {len(progress['errors'])}개")
        except Exception as e:
            print(f"   ⚠️  진행 상황 로드 실패: {e}")
    else:
        print("\n" + "=" * 60)
        print("🔄 수집 진행 상황")
        print("=" * 60)
        print("   진행 상황 파일이 없습니다.")
        print("   (데이터 수집이 시작되지 않았거나 완료되었을 수 있습니다)")
    
    # 저장 위치 요약
    print("\n" + "=" * 60)
    print("📂 저장 위치 요약")
    print("=" * 60)
    print(f"데이터셋: {dataset_dir}")
    print(f"로그: {logs_dir}")
    print(f"모델: {project_root / 'models'}")


if __name__ == "__main__":
    check_data_status()

