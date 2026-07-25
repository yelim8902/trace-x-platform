#!/usr/bin/env python3
"""
2단계 스코어러 학습 스크립트
"""
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.stage2_scorer import Stage2Scorer


def preprocess_xblock_sample(sample: dict) -> dict:
    """xblock_extracted.json의 flat 구조를 Stage2Scorer가 기대하는 형식으로 변환"""
    tx_raw = sample.get("tx_data", {})
    return {
        "ground_truth_label": sample.get("ground_truth_label", "normal"),
        "from": tx_raw.get("from", sample.get("address", "")),
        "to": tx_raw.get("to", ""),
        "usd_value": tx_raw.get("usd_value", sample.get("avg_tx_usd", 0)),
        "timestamp": tx_raw.get("timestamp", 0),
        "is_sanctioned": tx_raw.get("is_sanctioned", False),
        "is_mixer": tx_raw.get("is_mixer", False),
        "ml_features": {
            "fan_in_count":              sample.get("fan_in_count", 0),
            "fan_out_count":             sample.get("fan_out_count", 0),
            "tx_primary_fan_in_count":   sample.get("tx_primary_fan_in_count", 0),
            "tx_primary_fan_out_count":  sample.get("tx_primary_fan_out_count", 0),
            "pattern_score":             sample.get("pattern_score", 0),
            "avg_transaction_value":     sample.get("avg_tx_usd", 0),
            "max_transaction_value":     sample.get("max_tx_usd", 0),
            "graph_nodes":               sample.get("graph_nodes", 0),
            "num_transactions":          sample.get("graph_edges", 0),
            "ppr_score":                 sample.get("ppr_score", 0),
            "n_theta":                   sample.get("n_theta", 0),
            "n_omega":                   sample.get("n_omega", 0),
            # 시간 윈도우 룰 이진 플래그 (B-203/B-204 제거됨 - rulebook v2.1)
            "B101_fired":                sample.get("B101_fired", 0),
            "B102_fired":                sample.get("B102_fired", 0),
            "C004_fired":                sample.get("C004_fired", 0),
            "C005_fired":                sample.get("C005_fired", 0),
            "B504_fired":                sample.get("B504_fired", 0),
            "B505_fired":                sample.get("B505_fired", 0),
        },
        "tx_context": {
            "is_sanctioned":    tx_raw.get("is_sanctioned", False),
            "is_mixer":         tx_raw.get("is_mixer", False),
            "graph_nodes":      sample.get("graph_nodes", 0),
            "num_transactions": sample.get("graph_edges", 0),
        },
    }


def main():
    """메인 함수"""
    dataset_dir = project_root / "data" / "dataset"
    train_path = dataset_dir / "train.json"
    val_path = dataset_dir / "val.json"
    
    if not train_path.exists():
        print("❌ 학습 데이터셋 파일을 찾을 수 없습니다.")
        return
    
    print("📂 데이터 로드 중...")
    with open(train_path, 'r') as f:
        train_data = [preprocess_xblock_sample(s) for s in json.load(f)]

    val_data = None
    if val_path.exists():
        with open(val_path, 'r') as f:
            val_data = [preprocess_xblock_sample(s) for s in json.load(f)]
    
    print(f"   Train: {len(train_data)}개")
    if val_data:
        print(f"   Val: {len(val_data)}개")
    
    # 여러 모델 타입으로 학습
    model_types = ["logistic", "random_forest", "gradient_boosting"]
    results = {}
    
    for model_type in model_types:
        print(f"\n{'=' * 80}")
        print(f"{model_type.upper()} 모델 학습")
        print(f"{'=' * 80}")
        
        scorer = Stage2Scorer(model_type=model_type, use_ppr_features=True)
        train_results = scorer.train(train_data, val_data)
        
        results[model_type] = train_results
        
        # 모델 저장
        model_path = dataset_dir / f"stage2_scorer_{model_type}.pkl"
        scorer.save_model(model_path)
        print(f"\n💾 모델 저장: {model_path}")
    
    # 결과 저장
    output_path = dataset_dir / "stage2_scorer_training_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 80}")
    print("✅ 학습 완료")
    print(f"{'=' * 80}")
    print("\n📊 학습 결과 요약:")
    for model_type, result in results.items():
        print(f"\n  {model_type.upper()}:")
        print(f"    학습 Accuracy: {result.get('train_accuracy', 0):.4f}")
        if 'val_accuracy' in result:
            print(f"    검증 Accuracy: {result.get('val_accuracy', 0):.4f}")
            print(f"    검증 F1-Score: {result.get('val_f1', 0):.4f}")


if __name__ == "__main__":
    main()

