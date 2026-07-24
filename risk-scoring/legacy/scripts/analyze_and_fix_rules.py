#!/usr/bin/env python3
"""
룰 분석 및 수정 스크립트

실험 결과를 바탕으로 룰을 수정
"""
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def analyze_results():
    """실험 결과 분석"""
    results_path = project_root / "data" / "dataset" / "rule_optimization_results.json"
    
    if not results_path.exists():
        print("❌ 실험 결과 파일을 찾을 수 없습니다.")
        return None
    
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    print("=" * 80)
    print("룰 최적화 결과 분석")
    print("=" * 80)
    
    rule_eff = results.get("rule_effectiveness", {})
    axis_eff = results.get("axis_effectiveness", {})
    
    print("\n📊 룰별 효과 분석:")
    sorted_rules = sorted(rule_eff.items(), key=lambda x: x[1].get("effectiveness", 0), reverse=True)
    
    effective_rules = []
    ineffective_rules = []
    
    for rule_id, stats in sorted_rules:
        fired_count = stats.get("fired_count", 0)
        fraud_ratio = stats.get("fraud_ratio", 0)
        effectiveness = stats.get("effectiveness", 0)
        
        print(f"\n   {rule_id}:")
        print(f"      발동: {fired_count}회")
        print(f"      Fraud 비율: {fraud_ratio:.2%}")
        print(f"      효과성: {effectiveness:.2f}")
        
        # 효과성 기준: 발동 10회 이상, Fraud 비율 30% 이상
        if fired_count >= 10 and fraud_ratio >= 0.30:
            effective_rules.append(rule_id)
            print(f"      ✅ 효과적")
        else:
            ineffective_rules.append(rule_id)
            print(f"      ⚠️  효과 낮음")
    
    print("\n📊 축별 효과 분석:")
    for axis, stats in sorted(axis_eff.items(), key=lambda x: x[1].get("fraud_ratio", 0), reverse=True):
        fired_count = stats.get("fired_count", 0)
        fraud_ratio = stats.get("fraud_ratio", 0)
        print(f"   {axis}: 발동 {fired_count}회, Fraud 비율 {fraud_ratio:.2%}")
    
    return {
        "effective_rules": effective_rules,
        "ineffective_rules": ineffective_rules,
        "rule_effectiveness": rule_eff,
        "axis_effectiveness": axis_eff
    }


def modify_rules(analysis: Dict[str, Any]):
    """룰 수정"""
    print("\n" + "=" * 80)
    print("룰 수정")
    print("=" * 80)
    
    rules_path = project_root / "rules" / "tracex_rules.yaml"
    
    with open(rules_path, 'r') as f:
        rules_config = yaml.safe_load(f)
    
    ineffective_rules = analysis.get("ineffective_rules", [])
    rule_eff = analysis.get("rule_effectiveness", {})
    
    modifications = []
    
    print("\n🔧 룰 수정 계획:")
    
    # 1. 효과 없는 룰 제거 또는 수정
    for rule_id in ineffective_rules:
        stats = rule_eff.get(rule_id, {})
        fired_count = stats.get("fired_count", 0)
        fraud_ratio = stats.get("fraud_ratio", 0)
        
        # 룰 찾기
        rule = None
        for r in rules_config["rules"]:
            if r["id"] == rule_id:
                rule = r
                break
        
        if not rule:
            continue
        
        print(f"\n   {rule_id} ({rule.get('name', '')}):")
        print(f"      발동: {fired_count}회, Fraud 비율: {fraud_ratio:.2%}")
        
        # E-105: Scam Direct Exposure - Fraud 비율이 너무 낮음 (3.23%)
        if rule_id == "E-105":
            print(f"      → 제거 또는 임계값 강화")
            # 임계값 강화: usd_value 1 -> 100으로 증가
            if "conditions" in rule and "all" in rule["conditions"]:
                for cond in rule["conditions"]["all"]:
                    if "gte" in cond and cond["gte"].get("field") == "usd_value":
                        old_value = cond["gte"]["value"]
                        cond["gte"]["value"] = 100  # 1 -> 100
                        modifications.append(f"{rule_id}: usd_value 임계값 {old_value} -> 100")
                        print(f"      ✅ 수정: usd_value 임계값 {old_value} -> 100")
        
        # 발동 횟수가 너무 적은 룰 (10회 미만)
        elif fired_count < 10:
            print(f"      → 발동 횟수 부족, 임계값 완화 고려")
            # 임계값 완화하여 발동 횟수 증가
            if "conditions" in rule and "all" in rule["conditions"]:
                for cond in rule["conditions"]["all"]:
                    if "gte" in cond and cond["gte"].get("field") == "usd_value":
                        old_value = cond["gte"]["value"]
                        new_value = max(1, old_value // 2)  # 절반으로 감소
                        cond["gte"]["value"] = new_value
                        modifications.append(f"{rule_id}: usd_value 임계값 {old_value} -> {new_value}")
                        print(f"      ✅ 수정: usd_value 임계값 {old_value} -> {new_value}")
    
    # 2. 효과적인 룰의 임계값 최적화
    effective_rules = analysis.get("effective_rules", [])
    
    print("\n   효과적인 룰 임계값 최적화:")
    
    # B-501: 가장 효과적이지만 Fraud 비율이 34.92%로 낮음
    if "B-501" in effective_rules:
        rule = None
        for r in rules_config["rules"]:
            if r["id"] == "B-501":
                rule = r
                break
        
        if rule and "buckets" in rule:
            print(f"\n   B-501: High-Value Buckets")
            print(f"      현재: 동적 점수 (buckets 기반)")
            print(f"      → Fraud 비율이 34.92%로 낮음, 점수 증가 고려")
            # 점수 증가
            if "buckets" in rule and "ranges" in rule["buckets"]:
                for range_spec in rule["buckets"]["ranges"]:
                    old_score = range_spec.get("score", 0)
                    # 점수 20% 증가
                    new_score = int(old_score * 1.2)
                    range_spec["score"] = new_score
                    modifications.append(f"B-501: bucket 점수 {old_score} -> {new_score}")
                print(f"      ✅ 수정: 모든 bucket 점수 20% 증가")
    
    # C-003: 효과적이지만 Fraud 비율이 33.75%로 낮음
    if "C-003" in effective_rules:
        rule = None
        for r in rules_config["rules"]:
            if r["id"] == "C-003":
                rule = r
                break
        
        if rule:
            print(f"\n   C-003: High-Value Single Transfer")
            print(f"      현재: usd_value >= 3000")
            print(f"      → Fraud 비율이 33.75%로 낮음, 점수 증가 고려")
            old_score = rule.get("score", 20)
            new_score = int(old_score * 1.25)  # 25% 증가
            rule["score"] = new_score
            modifications.append(f"C-003: 점수 {old_score} -> {new_score}")
            print(f"      ✅ 수정: 점수 {old_score} -> {new_score}")
    
    # 3. E 축 룰들 전체적으로 임계값 조정
    print("\n   E 축 룰 전체 조정:")
    e_axis_rules = [r for r in rules_config["rules"] if r.get("axis") == "E"]
    
    for rule in e_axis_rules:
        rule_id = rule["id"]
        stats = rule_eff.get(rule_id, {})
        fraud_ratio = stats.get("fraud_ratio", 0)
        
        if fraud_ratio < 0.20:  # Fraud 비율이 20% 미만
            print(f"\n   {rule_id}: Fraud 비율 {fraud_ratio:.2%}")
            # 점수 증가 또는 임계값 강화
            if "conditions" in rule and "all" in rule["conditions"]:
                for cond in rule["conditions"]["all"]:
                    if "gte" in cond and cond["gte"].get("field") == "usd_value":
                        old_value = cond["gte"]["value"]
                        new_value = max(10, old_value * 2)  # 2배로 증가
                        cond["gte"]["value"] = new_value
                        modifications.append(f"{rule_id}: usd_value 임계값 {old_value} -> {new_value}")
                        print(f"      ✅ 수정: usd_value 임계값 {old_value} -> {new_value}")
            
            # 점수도 증가
            old_score = rule.get("score", 0)
            if old_score > 0:
                new_score = int(old_score * 1.3)  # 30% 증가
                rule["score"] = new_score
                modifications.append(f"{rule_id}: 점수 {old_score} -> {new_score}")
                print(f"      ✅ 수정: 점수 {old_score} -> {new_score}")
    
    # 수정된 룰 저장
    if modifications:
        backup_path = project_root / "rules" / "tracex_rules_backup.yaml"
        print(f"\n💾 원본 룰 백업: {backup_path}")
        with open(backup_path, 'w') as f:
            yaml.dump(rules_config, f)
        
        # 수정된 룰 저장
        modified_rules_path = project_root / "rules" / "tracex_rules_optimized.yaml"
        with open(modified_rules_path, 'w') as f:
            yaml.dump(rules_config, f, default_flow_style=False, sort_keys=False)
        
        print(f"💾 수정된 룰 저장: {modified_rules_path}")
        print(f"\n📝 수정 사항:")
        for mod in modifications:
            print(f"   - {mod}")
        
        return modified_rules_path
    else:
        print("\n⚠️  수정할 룰이 없습니다.")
        return None


def main():
    """메인 함수"""
    # 1. 결과 분석
    analysis = analyze_results()
    if not analysis:
        return
    
    # 2. 룰 수정
    modified_rules_path = modify_rules(analysis)
    
    if modified_rules_path:
        print("\n" + "=" * 80)
        print("✅ 룰 수정 완료!")
        print("=" * 80)
        print(f"\n수정된 룰 파일: {modified_rules_path}")
        print("\n다음 단계:")
        print("1. 수정된 룰을 검토하세요")
        print("2. 원본 룰을 백업에서 복원하려면:")
        print("   cp rules/tracex_rules_backup.yaml rules/tracex_rules.yaml")
        print("3. 수정된 룰을 적용하려면:")
        print("   cp rules/tracex_rules_optimized.yaml rules/tracex_rules.yaml")
        print("4. 성능 테스트:")
        print("   python scripts/optimize_rules.py")


if __name__ == "__main__":
    main()

