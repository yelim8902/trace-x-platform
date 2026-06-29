#!/usr/bin/env python3
"""
논문용 Ablation Study 스크립트

룰 축(axis)별, 특금법 파생 룰 단독, 전체 Stage 1, Stage 1+2 조합으로
AML 탐지 성능을 비교하는 Table을 생성한다.

논문 Section 5 (Ablation Study) 핵심 Table 출력.

Ablation 구성:
  - C/E/B-axis only    : 룰 축별 단독 기여도
  - Law-Derived only   : 특금법 파생 룰 단독 기여도
  - Rules Only         : 그래프 없이 룰만
  - Graph Only         : 룰 없이 그래프 피처만
  - Stage 1 전체       : 룰 + 그래프 (룰 0.9 + 그래프 0.1 가중 합산)
  - Stage 1 + Stage 2  : 최종 GBM 모델 포함

사용법:
    python scripts/ablation_study.py                              # 합성 데이터
    python scripts/ablation_study.py --data data/dataset/test.json
    python scripts/ablation_study.py --data data/dataset/xblock_with_rules.json
"""
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score,
    precision_score, recall_score, average_precision_score
)

from core.scoring.stage1_scorer import Stage1Scorer


# ── 룰 그룹 정의 ────────────────────────────────────────────────
AXIS_C_RULES = {"C-001", "C-002", "C-003", "C-004"}
AXIS_E_RULES = {"E-101", "E-102", "E-103", "E-104", "E-105"}
AXIS_B_RULES = {
    "B-101", "B-102", "B-103", "B-201", "B-202",
    "B-401", "B-402", "B-403A", "B-403B", "B-501", "B-502",
}
# 특금법/가상자산이용자보호법 직접 매핑 신규 룰
LAW_DERIVED_RULES = {"C-005", "C-006", "B-504", "B-505", "B-506", "E-106"}

ALL_RULES = AXIS_C_RULES | AXIS_E_RULES | AXIS_B_RULES | LAW_DERIVED_RULES


# ── 합성 데이터 (diagnose_rules.py와 동일 패턴) ─────────────────

def build_synthetic_samples(n_each: int = 150) -> List[Dict]:
    samples = []
    for i in range(n_each):
        samples.append({
            "ground_truth_label": "fraud",
            "tx_data": {
                "from": f"0xvictim_{i:04d}",
                "to": f"0xphisher_{i // 10:02d}",
                "usd_value": 120.0 + (i % 15) * 25,
                "timestamp": 1700000000 + i * 1800,
                "is_sanctioned": i % 30 == 0,
                "is_mixer": i % 20 == 0,
            },
            "ml_features": {
                "fan_in_count": 5 + i % 6,
                "fan_out_count": 22 + i % 14,
                "pattern_score": 14.0 + i % 12,
                "n_omega": 0.39 + (i % 6) * 0.01,
                "n_theta": 0.80 + (i % 4) * 0.01,
                "ppr_score": 0.08 + (i % 5) * 0.02,
                "graph_nodes": 105 + i % 55,
                "tx_primary_fan_in_count": 4 + i % 5,
                "tx_primary_fan_out_count": 24 + i % 10,
                "tx_primary_fan_in_value": 800.0 + i * 10,
                "tx_primary_fan_out_value": 750.0 + i * 9,
                "avg_transaction_value": 140.0 + i % 30,
                "max_transaction_value": 500.0 + i % 100,
            },
            "tx_context": {
                "num_transactions": 70 + i % 40,
                "graph_nodes": 105 + i % 55,
                "graph_edges": 120 + i % 60,
            }
        })
    for i in range(n_each):
        samples.append({
            "ground_truth_label": "normal",
            "tx_data": {
                "from": f"0xexchange_{i % 5:02d}",
                "to": f"0xuser_{i:04d}",
                "usd_value": 400.0 + i * 80,
                "timestamp": 1700000000 + i * 7200,
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
                "tx_primary_fan_in_value": 5000.0 + i * 100,
                "tx_primary_fan_out_value": 4800.0 + i * 95,
                "avg_transaction_value": 3500.0 + i % 500,
                "max_transaction_value": 15000.0 + i % 2000,
            },
            "tx_context": {
                "num_transactions": 90 + i % 30,
                "graph_nodes": 72 + i % 35,
                "graph_edges": 85 + i % 40,
            }
        })
    return samples


# ── 핵심 평가 함수 ───────────────────────────────────────────────

def evaluate_with_rule_filter(
    samples: List[Dict],
    allowed_rules: Optional[set],
    use_graph: bool = True,
    threshold: float = 35.0,
) -> Dict[str, float]:
    """
    allowed_rules에 포함된 룰만 사용해 Stage 1 점수를 계산하고 성능을 반환한다.
    allowed_rules=None이면 모든 룰 사용.
    """
    scorer = Stage1Scorer()

    all_rules = scorer.rule_evaluator.rule_loader.get_rules()
    if allowed_rules is not None:
        filtered_rules = [r for r in all_rules if r.get("id") in allowed_rules]
    else:
        filtered_rules = all_rules

    y_true, y_scores = [], []

    loader = scorer.rule_evaluator.rule_loader
    original_ruleset = loader._ruleset

    if allowed_rules is not None:
        loader._ruleset = dict(original_ruleset)
        loader._ruleset["rules"] = filtered_rules

    for sample in samples:
        label = sample["ground_truth_label"]
        tx_data = sample["tx_data"]
        ml_features = sample.get("ml_features", {})
        tx_context = sample.get("tx_context", {})
        y_true.append(1 if label == "fraud" else 0)

        try:
            fired = scorer.rule_evaluator.evaluate_single_transaction(tx_data)
            rule_score = scorer.rule_scorer.calculate_score(fired, tx_context)

            if use_graph:
                graph_score, _ = scorer._calculate_graph_score(ml_features, tx_context)
                final = scorer.rule_weight * rule_score + scorer.graph_weight * graph_score
            else:
                final = rule_score

            y_scores.append(min(100.0, max(0.0, final)))
        except Exception:
            y_scores.append(0.0)

    loader._ruleset = original_ruleset

    y_pred = [1 if s >= threshold else 0 for s in y_scores]
    y_proba = [s / 100.0 for s in y_scores]

    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
    }
    if len(set(y_proba)) > 1 and len(set(y_true)) > 1:
        try:
            metrics["roc_auc"] = roc_auc_score(y_true, y_proba)
            metrics["avg_precision"] = average_precision_score(y_true, y_proba)
        except ValueError:
            metrics["roc_auc"] = 0.5
            metrics["avg_precision"] = 0.0
    else:
        metrics["roc_auc"] = 0.5
        metrics["avg_precision"] = 0.0
    return metrics


def _compute_metrics(y_true, y_scores, threshold=35.0):
    """공통 메트릭 계산 헬퍼"""
    y_pred  = [1 if s >= threshold else 0 for s in y_scores]
    y_proba = [s / 100.0 for s in y_scores]
    m = {
        "accuracy":  accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall":    recall_score(y_true, y_pred, zero_division=0),
        "f1":        f1_score(y_true, y_pred, zero_division=0),
    }
    if len(set(y_proba)) > 1 and len(set(y_true)) > 1:
        try:
            m["roc_auc"]       = roc_auc_score(y_true, y_proba)
            m["avg_precision"] = average_precision_score(y_true, y_proba)
        except ValueError:
            m["roc_auc"] = 0.5
            m["avg_precision"] = 0.0
    else:
        m["roc_auc"] = 0.5
        m["avg_precision"] = 0.0
    return m


def evaluate_graph_only(
    samples: List[Dict],
    threshold: float = 35.0,
) -> Dict[str, float]:
    """그래프 피처만으로 위험 점수 계산 (룰 기여 없음).

    Stage1Scorer의 _calculate_graph_score를 직접 호출해 0-100 점수를 얻는다.
    룰 없이 그래프 구조 피처만의 기여도를 측정한다.
    """
    scorer = Stage1Scorer()
    y_true, y_scores = [], []
    for sample in samples:
        ml = sample.get("ml_features", {})
        ctx = sample.get("tx_context", {})
        y_true.append(1 if sample["ground_truth_label"] == "fraud" else 0)
        try:
            graph_score, _ = scorer._calculate_graph_score(ml, ctx)
            y_scores.append(min(100.0, max(0.0, graph_score)))
        except Exception:
            y_scores.append(0.0)
    return _compute_metrics(y_true, y_scores, threshold)


def run_ablation(samples: List[Dict], stage2_model_path: Optional[Path] = None) -> List[Dict]:
    """
    Ablation 조합 실행 후 결과 리스트 반환.

    각 항목:
        { "configuration": str, "accuracy": float, "f1": float,
          "roc_auc": float, "precision": float, "recall": float }
    """
    configurations = [
        # (이름, 허용 룰셋, use_graph, 특수모드)
        ("C-axis only (Compliance)",          AXIS_C_RULES,      True,  "default"),
        ("E-axis only (Exposure)",            AXIS_E_RULES,      True,  "default"),
        ("B-axis only (Behavior)",            AXIS_B_RULES,      True,  "default"),
        ("법령 파생 룰 only (Law-Derived)",    LAW_DERIVED_RULES, True,  "default"),
        ("룰 전체, graph 없음 (Rules Only)",   ALL_RULES,         False, "default"),
        ("그래프 피처만 (Graph Only)",          None,              True,  "graph_only"),
        ("Stage 1 전체 (Rules + Graph)",      ALL_RULES,         True,  "default"),
    ]

    results = []
    for name, rule_set, use_graph, mode in configurations:
        if mode == "graph_only":
            m = evaluate_graph_only(samples)
        else:
            m = evaluate_with_rule_filter(samples, rule_set, use_graph)

        results.append({
            "configuration": name,
            **{k: round(v, 4) for k, v in m.items()}
        })

    # Stage 2 (ML) 있으면 추가
    if stage2_model_path and stage2_model_path.exists():
        try:
            from core.scoring.stage2_scorer import Stage2Scorer
            scorer2 = Stage2Scorer(model_type="gradient_boosting")
            scorer2.load_model(stage2_model_path)
            y_true, y_scores = [], []
            for sample in samples:
                label = sample["ground_truth_label"]
                tx_data = sample["tx_data"]
                ml_features = sample.get("ml_features", {})
                tx_context = sample.get("tx_context", {})
                y_true.append(1 if label == "fraud" else 0)
                try:
                    final = scorer2.calculate_risk_score(tx_data, ml_features, tx_context)
                    y_scores.append(final.get("risk_score", 0))
                except Exception:
                    y_scores.append(0.0)
            y_pred = [1 if s >= 50 else 0 for s in y_scores]
            y_proba = [s / 100.0 for s in y_scores]
            m = {
                "accuracy": accuracy_score(y_true, y_pred),
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "roc_auc": roc_auc_score(y_true, y_proba) if len(set(y_proba)) > 1 else 0.5,
                "avg_precision": average_precision_score(y_true, y_proba) if len(set(y_proba)) > 1 else 0.0,
            }
            results.append({
                "configuration": "Stage 1 + Stage 2 (최종, ML 포함)",
                **{k: round(v, 4) for k, v in m.items()}
            })
        except Exception as e:
            print(f"  ⚠️  Stage 2 평가 실패: {e}")

    return results


# ── 출력 ─────────────────────────────────────────────────────────

def print_ablation_table(results: List[Dict]) -> None:
    print("\n" + "=" * 90)
    print("📋 Ablation Study — 논문 Table")
    print("=" * 90)
    header = f"{'Configuration':<42} {'Acc':>7} {'Prec':>7} {'Rec':>7} {'F1':>7} {'AUC':>7}"
    print(header)
    print("-" * 90)
    for r in results:
        row = (
            f"{r['configuration']:<42} "
            f"{r['accuracy']:>7.4f} "
            f"{r['precision']:>7.4f} "
            f"{r['recall']:>7.4f} "
            f"{r['f1']:>7.4f} "
            f"{r['roc_auc']:>7.4f}"
        )
        print(row)
    print("=" * 90)
    print("\n💡 법령 파생 룰 단독 성능이 높을수록 특금법 매핑의 논문 기여도 강화.")
    print("   Stage 1 전체 > 단일 axis 이면 룰 다양성의 기여가 입증됨.")
    print()


def save_latex_table(results: List[Dict], output_path: Path) -> None:
    """논문 직접 삽입 가능한 LaTeX 테이블 생성"""
    lines = [
        r"\begin{table}[h]",
        r"\centering",
        r"\caption{Ablation Study: Rule Axis and Stage Contribution}",
        r"\label{tab:ablation}",
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Configuration & Acc. & Prec. & Rec. & F1 & AUC \\",
        r"\midrule",
    ]
    for r in results:
        name = r["configuration"].replace("_", r"\_").replace("&", r"\&")
        lines.append(
            f"{name} & {r['accuracy']:.4f} & {r['precision']:.4f} & "
            f"{r['recall']:.4f} & {r['f1']:.4f} & {r['roc_auc']:.4f} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"📄 LaTeX 테이블 저장: {output_path}")


# ── Main ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="논문용 Ablation Study")
    parser.add_argument("--data", type=str, default=None)
    parser.add_argument("--n-synthetic", type=int, default=150)
    parser.add_argument("--stage2-model", type=str,
                        default="data/dataset/stage2_scorer_gradient_boosting.pkl")
    parser.add_argument("--output-json", type=str,
                        default="data/ablation_results.json")
    parser.add_argument("--output-latex", type=str,
                        default="docs/ablation_table.tex")
    args = parser.parse_args()

    if args.data:
        data_path = Path(args.data)
        if not data_path.exists():
            print(f"❌ 파일 없음: {data_path}")
            sys.exit(1)
        print(f"📂 데이터 로드: {data_path}")
        with open(data_path) as f:
            raw = json.load(f)
        samples = []
        for s in raw:
            tx_raw = s.get("tx_data", {})
            samples.append({
                "ground_truth_label": s.get("ground_truth_label", "normal"),
                "tx_data": {
                    "from": tx_raw.get("from", s.get("address", "")),
                    "to": tx_raw.get("to", s.get("address", "")),
                    "usd_value": tx_raw.get("usd_value", s.get("avg_tx_usd", 0)),
                    "timestamp": tx_raw.get("timestamp", 1700000000),
                    "is_sanctioned": tx_raw.get("is_sanctioned", False),
                    "is_mixer": tx_raw.get("is_mixer", False),
                },
                "ml_features": {
                    "fan_in_count":             s.get("fan_in_count", 0),
                    "fan_out_count":            s.get("fan_out_count", 0),
                    "tx_primary_fan_in_count":  s.get("tx_primary_fan_in_count", 0),
                    "tx_primary_fan_out_count": s.get("tx_primary_fan_out_count", 0),
                    "pattern_score":            s.get("pattern_score", 0),
                    "avg_transaction_value":    s.get("avg_tx_usd", 0),
                    "max_transaction_value":    s.get("max_tx_usd", 0),
                    "graph_nodes":              s.get("graph_nodes", 0),
                    "num_transactions":         s.get("graph_edges", 0),
                    "ppr_score":                s.get("ppr_score", 0),
                    "n_theta":                  s.get("n_theta", 0),
                    "n_omega":                  s.get("n_omega", 0),
                    # 시간 윈도우 룰 플래그 (xblock_with_rules.json에서 제공)
                    "B101_fired":               s.get("B101_fired", 0),
                    "B102_fired":               s.get("B102_fired", 0),
                    "C004_fired":               s.get("C004_fired", 0),
                    "C005_fired":               s.get("C005_fired", 0),
                    "B504_fired":               s.get("B504_fired", 0),
                    "B505_fired":               s.get("B505_fired", 0),
                },
                "tx_context": {
                    "num_transactions": s.get("graph_edges", 0),
                    "graph_nodes":      s.get("graph_nodes", 0),
                    "graph_edges":      s.get("graph_edges", 0),
                },
            })
    else:
        print(f"⚠️  데이터 미지정 → 합성 데이터 {args.n_synthetic}개/클래스 사용")
        samples = build_synthetic_samples(args.n_synthetic)

    print(f"🔄 Ablation 실행 중... ({len(samples)}개 샘플)")

    stage2_path = project_root / args.stage2_model
    results = run_ablation(samples, stage2_path if stage2_path.exists() else None)

    print_ablation_table(results)

    # JSON 저장
    out_json = project_root / args.output_json
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON 저장: {out_json}")

    # LaTeX 저장
    save_latex_table(results, project_root / args.output_latex)


if __name__ == "__main__":
    main()
