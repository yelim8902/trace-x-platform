#!/usr/bin/env python3
"""
AI 모델 학습 스크립트

사용법:
    python scripts/train_ai_model.py
"""
import json
import sys
from pathlib import Path
import pickle

# 프로젝트 루트를 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.scoring.ai_weight_learner import RuleWeightLearner


def main():
    """메인 함수"""
    # 학습 데이터 로드
    train_path = project_root / "data" / "dataset" / "train.json"
    if not train_path.exists():
        print(f"❌ 학습 데이터가 없습니다: {train_path}")
        print("   먼저 데이터셋을 분할하세요: python scripts/split_dataset.py")
        return
    
    print(f"📂 학습 데이터 로드: {train_path.name}")
    
    try:
        with open(train_path, 'r') as f:
            train_data = json.load(f)
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return
    
    if not train_data:
        print("❌ 학습 데이터가 비어있습니다.")
        return
    
    print(f"📊 학습 샘플: {len(train_data)}개")
    
    # 데이터 형식 변환
    print("\n데이터 형식 변환 중...")
    training_data = []
    
    for item in train_data:
        rule_results = item.get("rule_results", [])
        actual_score = item.get("actual_risk_score", 0.0)
        tx_context = item.get("tx_context", {})
        
        training_data.append((rule_results, actual_score, tx_context))
    
    print(f"✅ {len(training_data)}개 샘플 준비 완료")
    
    # 모델 학습
    print("\n🤖 AI 모델 학습 시작...")
    print("   (시간이 걸릴 수 있습니다)")
    
    try:
        learner = RuleWeightLearner(use_ai=True)
        learner.train(training_data)
        
        # 모델 저장
        model_dir = project_root / "models"
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / "rule_weights.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump({
                'model': learner.model,
                'scaler': learner.scaler,
                'rule_features': learner.rule_features,
                'rule_based_weights': learner.rule_based_weights
            }, f)
        
        print(f"\n✅ 학습 완료!")
        print(f"   모델 저장: {model_path}")
        
    except ImportError:
        print("\n⚠️  scikit-learn이 설치되지 않았습니다.")
        print("   규칙 기반 가중치만 사용합니다.")
        print("\n   설치: pip install scikit-learn")
        
        # 규칙 기반 가중치만 저장
        learner = RuleWeightLearner(use_ai=False)
        model_dir = project_root / "models"
        model_dir.mkdir(exist_ok=True)
        
        model_path = model_dir / "rule_weights_rule_based.pkl"
        with open(model_path, 'wb') as f:
            pickle.dump({
                'rule_based_weights': learner.rule_based_weights,
                'use_ai': False
            }, f)
        
        print(f"   규칙 기반 가중치 저장: {model_path}")
    
    except Exception as e:
        print(f"\n❌ 학습 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

