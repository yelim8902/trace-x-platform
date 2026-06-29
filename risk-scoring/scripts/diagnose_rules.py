#!/usr/bin/env python3
"""
룰별 fraud lift 분석 — Stage 1 성능 진단 도구

각 룰이 fraud vs normal 주소에서 얼마나 발동하는지 측정하고
Lift(fraud_rate / normal_rate)를 계산한다.

Lift < 1.0  → 역방향 신호 (정상에서 더 많이 발동, Stage 1 성능 저해 주범)
Lift = 1.0  → 무의미 (구분력 없음)
Lift > 2.0  → 유효 신호

사용법:
    python scripts/diagnose_rules.py                        # 합성 데이터로 테스트
    python scripts/diagnose_rules.py --data data/dataset/test.json
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.rules.evaluator import RuleEvaluator
from core.scoring.stage1_scorer import Stage1Scorer


# ────────────────────────────────────────────────────────────
# 합성 샘플 생성 (실제 데이터가 없을 때 빠른 진단용)
# ────────────────────────────────────────────────────────────

def _make_fraud_sample(i: int) -> Dict:
    """피싱/해킹 주소 패턴: 다수 피해자로부터 소액 수취 후 빠르게 분산"""
    return {
        "ground_truth_label": "fraud",
        "tx_data": {
            "from": f"0xvictim_{i:04d}",
            "to": f"0xphisher_{i // 10:02d}",
            "usd_value": 120.0 + (i % 15) * 25,
            "timestamp": 1700000000 + i * 1800,  # 30분 간격
            "is_sanctioned": False,
            "is_mixer": i % 20 == 0,   # 5%만 믹서 관련
        },
        "ml_features": {
            "fan_in_count": 5 + i % 6,         # 낮은 fan-in (fraud 특성)
            "fan_out_count": 22 + i % 14,       # 높은 fan-out (fraud 특성)
            "pattern_score": 14.0 + i % 12,     # 낮은 패턴 점수
            "n_omega": 0.39 + (i % 6) * 0.01,  # 낮은 n_omega (fraud 특성)
            "n_theta": 0.80 + (i % 4) * 0.01,
            "ppr_score": 0.08 + (i % 5) * 0.02,
            "graph_nodes": 105 + i % 55,
            "tx_primary_fan_in_count": 4 + i % 5,
            "tx_primary_fan_out_count": 24 + i % 10,
            "tx_primary_fan_in_value": 800.0 + i * 10,
            "tx_primary_fan_out_value": 750.0 + i * 9,
            "avg_transaction_value": 140.0 + i % 30,
            "max_transaction_value": 500.0 + i % 100,
            "total_transaction_value": 8000.0 + i * 50,
        },
        "tx_context": {
            "num_transactions": 70 + i % 40,
            "graph_nodes": 105 + i % 55,
            "graph_edges": 120 + i % 60,
        }
    }


def _make_normal_sample(i: int) -> Dict:
    """정상 거래소 사용자: 균형잡힌 입출금, 대형 거래소와 거래"""
    return {
        "ground_truth_label": "normal",
        "tx_data": {
            "from": f"0xexchange_{i % 5:02d}",
            "to": f"0xuser_{i:04d}",
            "usd_value": 400.0 + i * 80,   # 정상 사용자는 고액 거래도 많음
            "timestamp": 1700000000 + i * 7200,  # 2시간 간격
            "is_sanctioned": False,
            "is_mixer": False,
        },
        "ml_features": {
            "fan_in_count": 12 + i % 7,
            "fan_out_count": 17 + i % 6,
            "pattern_score": 34.0 + i % 12,
            "n_omega": 0.55 + (i % 5) * 0.01,
            "n_theta": 0.85 + (i % 3) * 0.01,
            "ppr_score": 0.04,
            "graph_nodes": 72 + i % 35,
            "tx_primary_fan_in_count": 11 + i % 6,
            "tx_primary_fan_out_count": 16 + i % 5,
            "tx_primary_fan_in_value": 5000.0 + i * 100,  # 정상은 고액
            "tx_primary_fan_out_value": 4800.0 + i * 95,
            "avg_transaction_value": 3500.0 + i % 500,    # 평균값 높음
            "max_transaction_value": 15000.0 + i % 2000,
            "total_transaction_value": 80000.0 + i * 200,
        },
        "tx_context": {
            "num_transactions": 90 + i % 30,
            "graph_nodes": 72 + i % 35,
            "graph_edges": 85 + i % 40,
        }
    }


def build_synthetic_samples(n_each: int = 100) -> List[Dict]:
    fraud = [_make_fraud_sample(i) for i in range(n_each)]
    normal = [_make_normal_sample(i) for i in range(n_each)]
    return fraud + normal


# ────────────────────────────────────────────────────────────
# 진단 로직
# ────────────────────────────────────────────────────────────

def diagnose(samples: List[Dict]) -> Dict[str, Any]:
    """
    각 룰의 fraud/normal 발동률과 Lift를 계산한다.

    Returns:
        {
          "rule_stats": { rule_id: { fraud_rate, normal_rate, lift, ... } },
          "graph_feature_stats": { feature: { fraud_mean, normal_mean } },
          "score_distribution": { fraud: [...], normal: [...] }
        }
    """
    evaluator = RuleEvaluator()
    scorer = Stage1Scorer()

    rule_fired_fraud: Dict[str, int] = defaultdict(int)
    rule_fired_normal: Dict[str, int] = defaultdict(int)

    fraud_scores: List[float] = []
    normal_scores: List[float] = []
    fraud_rule_scores: List[float] = []
    normal_rule_scores: List[float] = []
    fraud_graph_scores: List[float] = []
    normal_graph_scores: List[float] = []

    graph_feat_fraud: Dict[str, List[float]] = defaultdict(list)
    graph_feat_normal: Dict[str, List[float]] = defaultdict(list)

    n_fraud = sum(1 for s in samples if s["ground_truth_label"] == "fraud")
    n_normal = sum(1 for s in samples if s["ground_truth_label"] == "normal")

    print(f"  샘플: fraud={n_fraud}, normal={n_normal}")

    for sample in samples:
        label = sample["ground_truth_label"]
        tx_data = sample["tx_data"]
        ml_features = sample.get("ml_features", {})
        tx_context = sample.get("tx_context", {})

        # 룰 발동 체크
        try:
            fired = evaluator.evaluate_single_transaction(tx_data)
            for r in fired:
                rid = r["rule_id"]
                if label == "fraud":
                    rule_fired_fraud[rid] += 1
                else:
                    rule_fired_normal[rid] += 1
        except Exception:
            pass

        # Stage1 점수 계산
        try:
            result = scorer.calculate_risk_score(tx_data, ml_features, tx_context)
            score = result["risk_score"]
            if label == "fraud":
                fraud_scores.append(score)
                fraud_rule_scores.append(result["rule_score"])
                fraud_graph_scores.append(result["graph_score"])
            else:
                normal_scores.append(score)
                normal_rule_scores.append(result["rule_score"])
                normal_graph_scores.append(result["graph_score"])
        except Exception:
            pass

        # 그래프 피처 분포
        for feat in ["fan_in_count", "fan_out_count", "pattern_score", "n_omega", "ppr_score", "graph_nodes"]:
            val = ml_features.get(feat)
            if val is not None:
                if label == "fraud":
                    graph_feat_fraud[feat].append(float(val))
                else:
                    graph_feat_normal[feat].append(float(val))

    # ── 룰 통계 계산
    all_rule_ids = set(rule_fired_fraud.keys()) | set(rule_fired_normal.keys())
    rule_stats = {}
    for rid in sorted(all_rule_ids):
        fd = rule_fired_fraud.get(rid, 0)
        nd = rule_fired_normal.get(rid, 0)
        fraud_rate = fd / n_fraud if n_fraud > 0 else 0.0
        normal_rate = nd / n_normal if n_normal > 0 else 0.0
        lift = fraud_rate / normal_rate if normal_rate > 0 else float("inf")
        rule_stats[rid] = {
            "fraud_fired": fd,
            "normal_fired": nd,
            "fraud_rate": round(fraud_rate, 4),
            "normal_rate": round(normal_rate, 4),
            "lift": round(lift, 3),
            "signal": "✅ 유효" if lift >= 2.0 else ("⚠️  약함" if lift >= 1.0 else "❌ 역방향"),
        }

    # ── 그래프 피처 통계
    def _mean(lst):
        return round(sum(lst) / len(lst), 4) if lst else 0.0

    graph_stats = {
        feat: {
            "fraud_mean": _mean(graph_feat_fraud[feat]),
            "normal_mean": _mean(graph_feat_normal[feat]),
            "discriminative": abs(_mean(graph_feat_fraud[feat]) - _mean(graph_feat_normal[feat])) > 2.0
        }
        for feat in sorted(graph_feat_fraud.keys() | graph_feat_normal.keys())
    }

    return {
        "n_fraud": n_fraud,
        "n_normal": n_normal,
        "rule_stats": rule_stats,
        "graph_feature_stats": graph_stats,
        "score_distribution": {
            "fraud_mean": _mean(fraud_scores),
            "normal_mean": _mean(normal_scores),
            "fraud_rule_mean": _mean(fraud_rule_scores),
            "normal_rule_mean": _mean(normal_rule_scores),
            "fraud_graph_mean": _mean(fraud_graph_scores),
            "normal_graph_mean": _mean(normal_graph_scores),
        }
    }


# ────────────────────────────────────────────────────────────
# 출력 포맷
# ────────────────────────────────────────────────────────────

def print_report(result: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print("📊 룰별 Fraud Lift 분석 결과")
    print("=" * 70)
    print(f"  샘플: fraud={result['n_fraud']}, normal={result['n_normal']}\n")

    # ── 룰 테이블 (lift 기준 정렬)
    rule_stats = result["rule_stats"]
    sorted_rules = sorted(rule_stats.items(), key=lambda x: x[1]["lift"], reverse=True)

    print(f"{'Rule':<8} {'Fraud율':>8} {'Normal율':>9} {'Lift':>7}  Signal")
    print("-" * 55)
    for rid, s in sorted_rules:
        bar = "▓" * min(20, int(s["lift"] * 4)) if s["lift"] != float("inf") else "▓" * 20
        print(f"{rid:<8} {s['fraud_rate']:>8.3f} {s['normal_rate']:>9.3f} {s['lift']:>7.2f}  {s['signal']}")

    # ── 역방향 룰 요약 (논문에서 제거/조정 필요)
    inverted = [(rid, s) for rid, s in sorted_rules if s["lift"] < 1.0]
    print(f"\n❌ 역방향 신호 룰 ({len(inverted)}개) — 점수 인하 또는 예외 조건 강화 필요:")
    for rid, s in inverted:
        print(f"  {rid}: lift={s['lift']:.2f} (fraud {s['fraud_rate']:.1%} vs normal {s['normal_rate']:.1%})")

    # ── 점수 분포
    sd = result["score_distribution"]
    print(f"\n📈 Stage 1 점수 분포:")
    print(f"  {'':20} {'Fraud':>10} {'Normal':>10}")
    print(f"  {'최종 risk_score':20} {sd['fraud_mean']:>10.2f} {sd['normal_mean']:>10.2f}")
    print(f"  {'rule_score':20} {sd['fraud_rule_mean']:>10.2f} {sd['normal_rule_mean']:>10.2f}")
    print(f"  {'graph_score':20} {sd['fraud_graph_mean']:>10.2f} {sd['normal_graph_mean']:>10.2f}")
    note = "✅ 정상 분리" if sd["fraud_mean"] > sd["normal_mean"] else "❌ 점수 역전 — 임계값 이하로 fraud가 분류됨"
    print(f"\n  → {note}")

    # ── 그래프 피처 구분력
    print(f"\n🔍 그래프 피처 구분력 (fraud_mean vs normal_mean):")
    for feat, s in sorted(result["graph_feature_stats"].items()):
        flag = "✅" if s["discriminative"] else "  "
        print(f"  {flag} {feat:<30} fraud={s['fraud_mean']:<10.4f} normal={s['normal_mean']:.4f}")

    print()


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="룰별 Fraud Lift 진단")
    parser.add_argument("--data", type=str, default=None,
                        help="테스트 데이터 JSON 경로 (없으면 합성 데이터 사용)")
    parser.add_argument("--n-synthetic", type=int, default=100,
                        help="합성 샘플 수 (클래스별, 기본 100)")
    parser.add_argument("--output", type=str, default=None,
                        help="결과 JSON 저장 경로")
    args = parser.parse_args()

    if args.data:
        data_path = Path(args.data)
        if not data_path.exists():
            print(f"❌ 파일 없음: {data_path}")
            sys.exit(1)
        print(f"📂 데이터 로드: {data_path}")
        with open(data_path, "r") as f:
            samples = json.load(f)
        # 기존 데이터셋 포맷 변환 (build_mpocryptml_dataset 출력 형식)
        converted = []
        for s in samples:
            converted.append({
                "ground_truth_label": s.get("ground_truth_label", "normal"),
                "tx_data": {
                    "from": s.get("address", ""),
                    "to": s.get("address", ""),
                    "usd_value": s.get("rule_score", 0),
                    "timestamp": 1700000000,
                    "is_sanctioned": False,
                    "is_mixer": False,
                },
                "ml_features": s.get("ml_features", {}),
                "tx_context": {
                    "num_transactions": s.get("num_transactions", 0),
                    "graph_nodes": s.get("graph_nodes", 0),
                    "graph_edges": s.get("graph_edges", 0),
                }
            })
        samples = converted
    else:
        print(f"⚠️  데이터 파일 미지정 → 합성 데이터 {args.n_synthetic}개/클래스 사용")
        samples = build_synthetic_samples(args.n_synthetic)

    print(f"\n🔄 분석 중... (총 {len(samples)}개 샘플)")
    result = diagnose(samples)
    print_report(result)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 결과 저장: {out_path}")


if __name__ == "__main__":
    main()
