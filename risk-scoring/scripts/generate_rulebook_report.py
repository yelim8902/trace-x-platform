"""
TRACE-X 룰북 팀 공유용 리포트 생성기

생성 내용:
  1. 룰북 전체 (법적 근거 포함)
  2. AWS가 필요한 이유 및 위치
  3. XBlock 데이터셋 소개

실행:
  python scripts/generate_rulebook_report.py
  → docs/RULEBOOK_REPORT.md 생성
"""

import yaml
from pathlib import Path
from datetime import date

RULES_PATH = Path(__file__).parent.parent / "rules" / "tracex_rules.yaml"
OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "RULEBOOK_REPORT.md"

AXIS_DESC = {
    "C": "Compliance (법령 준수 위반 의심)",
    "E": "Exposure (위험 주소·서비스 노출)",
    "B": "Behavior (행동 패턴 이상)",
}

SEVERITY_KR = {
    "HIGH":   "🔴 높음",
    "MEDIUM": "🟡 중간",
    "LOW":    "🟢 낮음",
}


def load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def rules_by_axis(rules):
    grouped = {"C": [], "E": [], "B": []}
    for r in rules:
        grouped[r["axis"]].append(r)
    return grouped


def fmt_legal_basis(text: str) -> str:
    # 멀티라인 텍스트를 들여쓰기 없이 한 줄로
    return " ".join(text.split())


def build_report(data: dict) -> str:
    meta = data["meta"]
    rules = data["rules"]
    grouped = rules_by_axis(rules)

    lines = []

    # ── 헤더 ──────────────────────────────────────────────────────────
    lines += [
        f"# TRACE-X 룰북 v{meta['version']} — 팀 공유 보고서",
        f"",
        f"> 생성일: {date.today()}  ",
        f"> 룰 총 수: {len(rules)}개 (C-axis {len(grouped['C'])}개 / "
        f"E-axis {len(grouped['E'])}개 / B-axis {len(grouped['B'])}개)  ",
        f"> 법적 근거: 특금법, 가상자산이용자보호법, FATF (2020/2021)",
        f"",
        f"---",
        f"",
    ]

    # ── 참고문헌 ──────────────────────────────────────────────────────
    lines += [
        "## 참고 법령 및 문헌",
        "",
    ]
    for ref in meta.get("references", []):
        lines.append(f"- {ref}")
    lines += ["", "---", ""]

    # ── 룰북 섹션 ─────────────────────────────────────────────────────
    lines += [
        "## 룰북 전체 목록",
        "",
        "각 룰에는 **법적 근거(legal_basis)** 가 명시되어 있습니다.  ",
        "근거 출처: 특금법 조문, FATF Red Flag Indicators (2020), FATF VA-VASP Guidance (2021)",
        "",
    ]

    for axis in ["C", "E", "B"]:
        lines += [
            f"### {axis}-axis: {AXIS_DESC[axis]}",
            "",
            "| ID | 룰 이름 | 심각도 | 점수 | 법적 근거 요약 |",
            "|-----|---------|--------|------|--------------|",
        ]
        for r in grouped[axis]:
            severity = SEVERITY_KR.get(r.get("severity", ""), r.get("severity", ""))
            score = r.get("score", "-")
            basis = fmt_legal_basis(r.get("legal_basis", ""))
            # 근거를 너무 길면 앞부분만
            if len(basis) > 120:
                basis = basis[:117] + "..."
            lines.append(f"| {r['id']} | {r['name']} | {severity} | {score} | {basis} |")
        lines += [""]

    # 룰별 상세
    lines += [
        "---",
        "",
        "## 룰 상세 (법적 근거 전문)",
        "",
    ]
    for axis in ["C", "E", "B"]:
        lines += [f"### {axis}-axis: {AXIS_DESC[axis]}", ""]
        for r in grouped[axis]:
            severity = SEVERITY_KR.get(r.get("severity", ""), r.get("severity", ""))
            score = r.get("score", "-")
            lines += [
                f"#### {r['id']} — {r['name']}",
                f"",
                f"- **심각도**: {severity}  ",
                f"- **점수**: {score}  ",
            ]
            if r.get("description"):
                desc = " ".join(r["description"].split())
                lines.append(f"- **설명**: {desc}  ")
            basis = fmt_legal_basis(r.get("legal_basis", ""))
            lines += [
                f"- **법적 근거**:",
                f"  ```",
                f"  {basis}",
                f"  ```",
                f"",
            ]

    # ── AWS 섹션 ──────────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## AWS가 필요한 이유",
        "",
        "### 문제: XBlock 데이터셋 로컬 처리 불가",
        "",
        "| 항목 | 내용 |",
        "|------|------|",
        "| 데이터 파일 | `data/xblock/MulDiGraph.pkl` (1.0 GB) |",
        "| 메모리 필요량 | pickle 로드 시 RAM 8~15 GB 팽창 |",
        "| 로컬 환경 | MacBook 16 GB RAM → **크래시 발생** |",
        "| 해결책 | AWS r5.xlarge (32 GB RAM) 스팟 인스턴스 |",
        "",
        "### 무엇을 하는가",
        "",
        "```",
        "XBlock 피클 로드 (15 GB)          scripts/build_xblock_dataset.py",
        "  → 2,973,489 노드 순회",
        "  → 피싱 레이블 1,165개 추출",
        "  → fan-in/fan-out/PPR 피처 계산",
        "  → data/dataset/xblock_features.csv 저장 (수십 MB)",
        "                                             ↓",
        "                              이후 로컬에서 ML 학습 가능",
        "```",
        "",
        "### 비용 추정",
        "",
        "| 인스턴스 | vCPU | RAM | 스팟 시간당 | 예상 처리 시간 | 예상 총비용 |",
        "|---------|------|-----|-----------|-------------|-----------|",
        "| r5.xlarge | 4 | 32 GB | ~$0.07 | 3~5 시간 | **$0.21~0.35** |",
        "",
        "> 버퍼 포함 $50 예산 신청 예정 (Stage 2 재학습, Ablation 실험 포함)",
        "",
        "### 처리 완료 후 가능한 작업",
        "",
        "1. `python scripts/train_stage2_scorer.py` — Stage 2 모델 재학습",
        "2. `python scripts/ablation_study.py` — 논문 Table 생성",
        "3. `python scripts/test_stage1_scorer.py` — 성능 재검증",
        "",
    ]

    # ── XBlock 섹션 ───────────────────────────────────────────────────
    lines += [
        "---",
        "",
        "## XBlock 데이터셋이란?",
        "",
        "### 출처",
        "",
        "| 항목 | 내용 |",
        "|------|------|",
        "| 이름 | EPTransNet (Ethereum Phishing Transaction Network) |",
        "| 제공 | InPlusLab, 중산대학교 (SYSU), 2019 |",
        "| 데이터 수집 | Etherscan `phish-hack` 레이블 공식 신고 주소 + 2차 BFS 크롤링 |",
        "| 라이선스 | 학술 연구용 공개 데이터셋 |",
        "",
        "### 규모",
        "",
        "| 항목 | 수치 |",
        "|------|------|",
        "| 노드 (이더리움 주소) | 2,973,489개 |",
        "| 엣지 (거래) | 13,551,303개 |",
        "| 레이블된 피싱 주소 | **1,165개** |",
        "| 평균 degree | 4.56 |",
        "| 형식 | networkx MultiDiGraph (pickle) |",
        "",
        "### 왜 이 데이터를 쓰는가",
        "",
        "1. **실제 신고된 피싱 주소** — Etherscan에 공개 신고된 주소 기반 → 레이블 신뢰도 높음",
        "2. **이더리움 네이티브** — 우리 시스템이 이더리움 트랜잭션 분석 대상",
        "3. **공개 학술 데이터셋** — 논문 재현 가능성 보장",
        "4. **그래프 구조 포함** — fan-in/fan-out, PPR 등 그래프 피처 추출 가능",
        "",
        "### 기존 학습 데이터(GOG)와의 차이",
        "",
        "| 항목 | GOG (기존, 삭제됨) | XBlock (현재) |",
        "|------|------------------|--------------|",
        "| 출처 | NeurIPS 2024 논문 부속 데이터 | Etherscan 공식 신고 |",
        "| 레이블 | 다양한 사기 유형 | 피싱/해킹 특화 |",
        "| 접근성 | 팀 저장소 삭제 | 공개 다운로드 가능 |",
        "| 재현성 | 낮음 | 높음 (논문 인용 가능) |",
        "",
        "### 인용",
        "",
        "```bibtex",
        "@misc{xblockEthereum,",
        "  author = {Chen, Liang and Peng, Jiaying and Liu, Yang and",
        "            Li, Jintang and Xie, Fenfang and Zheng, Zibin},",
        "  title  = {XBLOCK Blockchain Datasets: InPlusLab Ethereum",
        "            Phishing Detection Datasets},",
        "  year   = {2019},",
        "  url    = {http://xblock.pro/ethereum/}",
        "}",
        "```",
        "",
        "---",
        "",
        f"*이 보고서는 `scripts/generate_rulebook_report.py`로 자동 생성됩니다.*  ",
        f"*룰북 수정 후 재실행하면 최신 내용으로 갱신됩니다.*",
    ]

    return "\n".join(lines)


def main():
    print("📋 룰북 리포트 생성 중...")
    data = load_rules()
    report = build_report(data)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(report, encoding="utf-8")

    rules = data["rules"]
    grouped = rules_by_axis(rules)
    print(f"✅ 완료: {OUTPUT_PATH}")
    print(f"   총 {len(rules)}개 룰 "
          f"(C:{len(grouped['C'])} / E:{len(grouped['E'])} / B:{len(grouped['B'])})")
    print(f"   → 팀원에게 docs/RULEBOOK_REPORT.md 파일을 공유하세요.")


if __name__ == "__main__":
    main()
