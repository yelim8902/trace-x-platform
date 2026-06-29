#!/usr/bin/env python3
"""
데이터셋을 학습/검증/테스트로 분할

사용법:
    python scripts/split_dataset.py
"""
import json
import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.dataset_builder import DatasetBuilder


def main():
    """메인 함수"""
    builder = DatasetBuilder()
    
    # 데이터셋 파일 찾기
    dataset_dir = project_root / "data" / "dataset"
    
    # diverse_rules_enhanced_sampled.json 우선 선택 (그래프 통계 Feature 강화 버전)
    dataset_file = None
    if (dataset_dir / "diverse_rules_enhanced_sampled.json").exists():
        dataset_file = dataset_dir / "diverse_rules_enhanced_sampled.json"
    elif (dataset_dir / "diverse_rules_fixed_sampled.json").exists():
        dataset_file = dataset_dir / "diverse_rules_fixed_sampled.json"
    elif (dataset_dir / "diverse_rules_optimized_sampled.json").exists():
        dataset_file = dataset_dir / "diverse_rules_optimized_sampled.json"
    elif (dataset_dir / "diverse_rules_sampled.json").exists():
        dataset_file = dataset_dir / "diverse_rules_sampled.json"
    
    if dataset_file is None:
        dataset_files = list(dataset_dir.glob("*.json"))
    if not dataset_files:
        print("❌ 데이터셋 파일을 찾을 수 없습니다.")
        print(f"   경로: {dataset_dir}")
        return
    # 가장 최근 파일 선택
    dataset_file = max(dataset_files, key=lambda p: p.stat().st_mtime)
    
    print(f"📂 데이터셋 파일: {dataset_file.name}")
    
    # 데이터셋 로드
    try:
        with open(dataset_file, 'r') as f:
            dataset = json.load(f)
    except Exception as e:
        print(f"❌ 데이터셋 로드 실패: {e}")
        return
    
    if not dataset:
        print("❌ 데이터셋이 비어있습니다.")
        return
    
    print(f"📊 총 {len(dataset)}개 샘플")
    
    # 라벨 분포 확인
    labels = [item.get("ground_truth_label", "unknown") for item in dataset]
    label_counts = {}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1
    
    print("\n라벨 분포:")
    for label, count in label_counts.items():
        print(f"  {label}: {count}개 ({count/len(dataset)*100:.1f}%)")
    
    # 분할
    print("\n데이터셋 분할 중...")
    train, val, test = builder.split_dataset(
        dataset,
        train_ratio=0.7,
        val_ratio=0.15,
        test_ratio=0.15,
        stratify=True  # 라벨별 비율 유지
    )
    
    # 저장
    output_dir = dataset_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    with open(output_dir / "train.json", 'w') as f:
        json.dump(train, f, indent=2, ensure_ascii=False)
    with open(output_dir / "val.json", 'w') as f:
        json.dump(val, f, indent=2, ensure_ascii=False)
    with open(output_dir / "test.json", 'w') as f:
        json.dump(test, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ 분할 완료!")
    print(f"   학습: {len(train)}개 ({len(train)/len(dataset)*100:.1f}%)")
    print(f"   검증: {len(val)}개 ({len(val)/len(dataset)*100:.1f}%)")
    print(f"   테스트: {len(test)}개 ({len(test)/len(dataset)*100:.1f}%)")
    print(f"\n저장 위치: {output_dir}")
    print("  - train.json")
    print("  - val.json")
    print("  - test.json")


if __name__ == "__main__":
    main()

