#!/usr/bin/env python3
"""
XBlock Ethereum Phishing Transaction Network → 프로젝트 JSON 변환 스크립트

Kaggle 데이터셋 다운로드:
    pip install kaggle
    kaggle datasets download -d xblock/ethereum-phishing-transaction-network
    unzip ethereum-phishing-transaction-network.zip -d data/xblock/

사용법:
    python scripts/build_xblock_dataset.py
    python scripts/build_xblock_dataset.py --input data/xblock/transaction_dataset.csv
    python scripts/build_xblock_dataset.py --input data/xblock/transaction_dataset.csv --limit 5000
"""
import sys
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ETH → USD 근사 환율 (XBlock 데이터 수집 시점인 2017~2022년 평균)
ETH_USD_APPROX = 1500.0

# XBlock 컬럼 → 프로젝트 피처 매핑
COLUMN_MAP = {
    "address":                                       "Address",
    "sent_txn":                                      "Sent tnx",
    "received_txn":                                  "Received Tnx",
    "total_txn":                                     "total transactions (including tnx to create contract)",
    "unique_received_from":                          "Unique Received From Addresses",
    "unique_sent_to":                                "Unique Sent To Addresses",
    "avg_val_sent_eth":                              "avg val sent",
    "avg_val_received_eth":                          "avg val received",
    "max_val_received_eth":                          "max value received",
    "max_val_sent_eth":                              "max val sent",
    "total_ether_sent":                              "total Ether sent",
    "total_ether_received":                          "total ether received",
    "total_ether_balance":                           "total ether balance",
    "time_diff_mins":                                "Time Diff between first and last (Mins)",
    "avg_min_between_sent":                          "Avg min between sent tnx",
    "avg_min_between_received":                      "Avg min between received tnx",
}


def _safe_float(val, default: float = 0.0) -> float:
    try:
        v = float(val)
        return default if (np.isnan(v) or np.isinf(v)) else v
    except (TypeError, ValueError):
        return default


def convert_row(row: pd.Series) -> dict:
    """XBlock 행 1개 → ablation_study.py 가 기대하는 샘플 dict 변환"""

    # ── 기본 집계 ─────────────────────────────────────────────────
    fan_in  = _safe_float(row.get("Unique Received From Addresses", 0))
    fan_out = _safe_float(row.get("Unique Sent To Addresses", 0))
    sent_txn     = _safe_float(row.get("Sent tnx", 0))
    received_txn = _safe_float(row.get("Received Tnx", 0))
    total_txn    = _safe_float(
        row.get("total transactions (including tnx to create contract)", sent_txn + received_txn)
    )

    avg_sent_eth     = _safe_float(row.get("avg val sent", 0))
    avg_received_eth = _safe_float(row.get("avg val received", 0))
    max_received_eth = _safe_float(row.get("max value received", 0))
    max_sent_eth     = _safe_float(row.get("max val sent", 0))

    avg_tx_usd = ((avg_sent_eth + avg_received_eth) / 2) * ETH_USD_APPROX
    max_tx_usd = max(max_received_eth, max_sent_eth) * ETH_USD_APPROX

    total_sent_eth = _safe_float(row.get("total Ether sent", 0))
    total_recv_eth = _safe_float(row.get("total ether received", 0))

    # ── 그래프 파생 피처 (XBlock은 그래프 정보가 없으므로 근사) ────
    # n_omega: 출력 방향 편향 (0=순수 수신, 1=순수 송신)
    denom = fan_in + fan_out
    n_omega = (fan_out / denom) if denom > 0 else 0.5

    # n_theta: 거래 활성도 (1000건 기준 정규화, 최대 1.0)
    n_theta = min(total_txn / 1000.0, 1.0)

    # ppr_score: XBlock에서 도출 불가 → 0.05 (정상 주소 기준 중앙값 근사)
    ppr_score = 0.05

    # pattern_score: fan-in/out 불균형 기반 이상 점수 (0~100)
    imbalance = abs(fan_out - fan_in) / max(denom, 1)
    fan_out_ratio = fan_out / max(total_txn, 1)
    pattern_score = min(100.0, (imbalance * 40) + (fan_out_ratio * 60))

    # graph_nodes / edges: 고유 주소 수 합산으로 근사
    graph_nodes = int(fan_in + fan_out + 1)
    graph_edges = int(total_txn)

    # ── tx_data (룰 평가용, XBlock에서 직접 확인 불가한 필드는 False) ─
    tx_data = {
        "from": str(row.get("Address", "")),
        "to":   str(row.get("Address", "")),
        "usd_value": avg_tx_usd,
        "timestamp": 1700000000,
        "is_sanctioned": False,   # XBlock은 SDN 정보 없음
        "is_mixer": False,        # XBlock은 믹서 태그 없음
    }

    ml_features = {
        "fan_in_count":               int(fan_in),
        "fan_out_count":              int(fan_out),
        "pattern_score":              round(pattern_score, 4),
        "n_omega":                    round(n_omega, 4),
        "n_theta":                    round(n_theta, 4),
        "ppr_score":                  round(ppr_score, 4),
        "graph_nodes":                graph_nodes,
        "tx_primary_fan_in_count":    int(received_txn),
        "tx_primary_fan_out_count":   int(sent_txn),
        "tx_primary_fan_in_value":    round(total_recv_eth * ETH_USD_APPROX, 2),
        "tx_primary_fan_out_value":   round(total_sent_eth * ETH_USD_APPROX, 2),
        "avg_transaction_value":      round(avg_tx_usd, 2),
        "max_transaction_value":      round(max_tx_usd, 2),
    }

    label_raw = row.get("FLAG", 0)
    ground_truth_label = "fraud" if int(_safe_float(label_raw, 0)) == 1 else "normal"

    return {
        "ground_truth_label": ground_truth_label,
        "address": str(row.get("Address", "")),
        "rule_score": 0.0,
        "tx_data": tx_data,
        "ml_features": ml_features,
        "num_transactions": int(total_txn),
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
    }


def main():
    parser = argparse.ArgumentParser(description="XBlock → 프로젝트 JSON 변환")
    parser.add_argument(
        "--input", type=str,
        default="data/xblock/transaction_dataset.csv",
        help="XBlock CSV 파일 경로",
    )
    parser.add_argument(
        "--output", type=str,
        default="data/dataset/xblock_dataset.json",
        help="출력 JSON 파일 경로",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="변환할 최대 샘플 수 (기본: 전체)",
    )
    parser.add_argument(
        "--balance", action="store_true",
        help="fraud/normal 클래스 수를 맞춰 언더샘플링",
    )
    args = parser.parse_args()

    input_path = project_root / args.input
    if not input_path.exists():
        print(f"[오류] 파일 없음: {input_path}")
        print()
        print("  Kaggle에서 XBlock 데이터셋을 먼저 다운로드하세요:")
        print("  1) pip install kaggle")
        print("  2) kaggle datasets download -d xblock/ethereum-phishing-transaction-network")
        print(f"  3) unzip ethereum-phishing-transaction-network.zip -d {project_root / 'data/xblock/'}")
        sys.exit(1)

    print(f"[로드] {input_path}")
    df = pd.read_csv(input_path)
    print(f"  전체 행: {len(df):,}  |  컬럼: {len(df.columns)}")
    print(f"  FLAG 분포: {df['FLAG'].value_counts().to_dict()}")

    # ? 값을 NaN으로 변환 (XBlock은 결측값을 '?'로 표시)
    df.replace("?", np.nan, inplace=True)

    if args.balance:
        fraud_df  = df[df["FLAG"] == 1]
        normal_df = df[df["FLAG"] == 0].sample(n=len(fraud_df), random_state=42)
        df = pd.concat([fraud_df, normal_df]).sample(frac=1, random_state=42).reset_index(drop=True)
        print(f"  균형 샘플링 후: {len(df):,}개 (fraud {len(fraud_df):,} / normal {len(fraud_df):,})")

    if args.limit:
        df = df.head(args.limit)
        print(f"  --limit 적용: {len(df):,}개")

    print("[변환 중...]")
    samples = [convert_row(row) for _, row in df.iterrows()]

    fraud_count  = sum(1 for s in samples if s["ground_truth_label"] == "fraud")
    normal_count = len(samples) - fraud_count
    print(f"  fraud: {fraud_count:,}  |  normal: {normal_count:,}")

    output_path = project_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(samples, f, indent=2, ensure_ascii=False)

    print(f"[저장] {output_path}  ({len(samples):,}개 샘플)")
    print()
    print("다음 단계:")
    print(f"  python scripts/ablation_study.py --data {args.output}")


if __name__ == "__main__":
    main()
