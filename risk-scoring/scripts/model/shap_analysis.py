"""
9단계: SHAP 기반 모델 해석 — 이 코드베이스 최초의 SHAP 구현.

목적:
1. 전역 피처 중요도를 SHAP로 다시 산출해서 6단계 permutation importance와 방향이
   일치하는지 교차 확인 (일치하면 "우연히 한 방법에서만 나온 신호"가 아니라는 근거가 됨)
2. SHAP 피처 이름 -> 사람이 읽는 설명 문구로 매핑하는 테이블 구축 (룰북의 "법적 근거"
   문구와 나란히 놓을 ML 쪽 "왜 이 점수가 나왔는가" 근거)
3. 개별 주소 몇 개(정탐/오탐/미탐)에 대해 실제 설명 문구가 어떻게 나오는지 예시 생성
"""
import json
from pathlib import Path

import joblib
import numpy as np
import shap

from train_model import FEATURE_COLUMNS, load_split, to_xy

project_root = Path(__file__).parent.parent.parent

# SHAP 피처 -> 사람이 읽는 설명 문구 매핑 (룰북 설명과 나란히 표시할 ML 근거)
FEATURE_EXPLANATIONS = {
    "fan_in_count": "여러 주소로부터 자금이 한 곳으로 집중 유입됨 (자금 분산 후 합류 패턴)",
    "fan_out_count": "한 주소에서 여러 주소로 자금이 분산 유출됨",
    "pattern_score": "그래프 구조상 정상 거래 패턴과의 유사도가 낮음",
    "n_omega": "수신 편향 — 보내는 것보다 받는 거래가 두드러짐",
    "n_theta": "다단계 자금 이동 구조 지표",
    "graph_nodes": "이 주소와 연결된 거래 네트워크가 큼 (관련 주소 수 많음)",
    "graph_edges": "이 주소를 둘러싼 거래(엣지) 수가 많음",
    "avg_tx_usd": "평균 거래 금액이 큼",
    "max_tx_usd": "단일 거래 중 최대 금액이 큼",
    "total_sent_usd": "누적 송금액이 큼",
    "total_recv_usd": "누적 수신액이 큼",
    "peel_chain_max_length": "금액이 매 홉마다 줄어드는 자금 세탁 체인(peel chain) 패턴 감지",
    "peel_chain_count": "peel chain 패턴이 여러 건 감지됨",
    "amount_deviation_score": "거래 금액이 이 주소의 평소 패턴 대비 불규칙함",
    "frequency_deviation_score": "거래 발생 간격이 이 주소의 평소 패턴 대비 불규칙함",
}


def explain_row(shap_row, X_row, top_k=3):
    order = np.argsort(-np.abs(shap_row))[:top_k]
    lines = []
    for i in order:
        col = FEATURE_COLUMNS[i]
        direction = "위험도 상승" if shap_row[i] > 0 else "위험도 하강"
        lines.append(f"    - {col} (값={X_row[i]:.2f}, SHAP={shap_row[i]:+.3f}, {direction}): {FEATURE_EXPLANATIONS[col]}")
    return lines


def main():
    model = joblib.load(project_root / "models" / "ml_risk_model.joblib")
    clf = model.named_steps["clf"]

    all_rows = load_split("train") + load_split("val") + load_split("test")
    X, y = to_xy(all_rows)
    addrs = [r["address"] for r in all_rows]

    print(f"SHAP 계산 대상: {len(all_rows)}개 (전체 XBlock 데이터셋)")
    explainer = shap.TreeExplainer(clf)
    shap_values = explainer.shap_values(X)
    # HistGradientBoostingClassifier 이진분류 -> shap_values가 (n, features) 1개 배열로 나옴(양성=fraud 클래스 기준)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    print("\n" + "=" * 70)
    print("전역 피처 중요도 (mean |SHAP value|)")
    print("=" * 70)
    mean_abs = np.abs(shap_values).mean(axis=0)
    order = np.argsort(-mean_abs)
    for i in order:
        print(f"  {FEATURE_COLUMNS[i]:<28} {mean_abs[i]:.4f}")

    print("\n" + "=" * 70)
    print("6단계 Permutation Importance와 순위 비교")
    print("=" * 70)
    perm_rank = [
        "fan_in_count", "total_sent_usd", "graph_nodes", "n_omega", "amount_deviation_score",
        "total_recv_usd", "avg_tx_usd", "frequency_deviation_score", "max_tx_usd", "n_theta",
        "peel_chain_count", "pattern_score", "peel_chain_max_length", "graph_edges", "fan_out_count",
    ]
    shap_rank = [FEATURE_COLUMNS[i] for i in order]
    print(f"  {'순위':<4} {'permutation importance (6단계)':<28} {'SHAP (9단계)':<28}")
    for rank in range(len(FEATURE_COLUMNS)):
        print(f"  {rank+1:<4} {perm_rank[rank]:<28} {shap_rank[rank]:<28}")

    # 개별 주소 예시: (a) critical로 정탐된 fraud, (b) low인데 실제 fraud(미탐), (c) critical로 오탐된 normal
    proba = clf.predict_proba(X)[:, 1]
    score = proba * 100
    is_fraud = y == 1

    print("\n" + "=" * 70)
    print("개별 주소 설명 예시")
    print("=" * 70)

    tp_idx = np.where(is_fraud & (score >= 80))[0]
    if len(tp_idx) > 0:
        i = tp_idx[np.argmax(score[tp_idx])]
        print(f"\n[정탐 예시] {addrs[i]} (fraud, score={score[i]:.1f}, critical)")
        for line in explain_row(shap_values[i], X[i]):
            print(line)

    fn_idx = np.where(is_fraud & (score < 20))[0]
    if len(fn_idx) > 0:
        i = fn_idx[np.argmin(score[fn_idx])]
        print(f"\n[미탐 예시] {addrs[i]} (실제 fraud인데 score={score[i]:.1f}, low로 분류됨)")
        for line in explain_row(shap_values[i], X[i]):
            print(line)

    fp_idx = np.where(~is_fraud & (score >= 80))[0]
    if len(fp_idx) > 0:
        i = fp_idx[np.argmax(score[fp_idx])]
        print(f"\n[오탐 예시] {addrs[i]} (실제 normal인데 score={score[i]:.1f}, critical로 분류됨)")
        for line in explain_row(shap_values[i], X[i]):
            print(line)
    else:
        print("\n[오탐 예시] critical로 잘못 분류된 normal 없음")


if __name__ == "__main__":
    main()
