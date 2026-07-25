# 문서 가이드

리스크 스코어링 엔진을 표준 10단계 ML 라이프사이클(문제 정의 → 데이터 수집 → EDA → 분할 → 피처 엔지니어링 → 학습 → 평가 → 선정 → 해석 → 통합)로 재구축한 기록. **읽는 순서대로 정렬**돼 있고, 각 문서에 실제 실행한 명령어와 검증된 수치만 남겼다(사후 추정 없음).

과거 GOG(Graph of Graphs) 논문 데이터 기반 실험은 재현 불가능해서 폐기했다 — 관련 코드는 `../legacy/`에 보관돼 있다(`../legacy/README.md` 참고).

## 1~2. 데이터 수집

| 문서 | 내용 |
|---|---|
| [DATA_COLLECTION_OVERVIEW.md](DATA_COLLECTION_OVERVIEW.md) | **먼저 읽을 것** — GOG를 왜 버렸는지, XBlock/ETH-Labels-2026/BCCC-2025 세 데이터셋이 서로 어떤 역할을 하는지 한 번에 설명 |
| [DATA_XBLOCK.md](DATA_XBLOCK.md) | 베이스라인 데이터셋(2016~2019년, 6,165개 주소) 출처·라벨 정의·한계 |
| [DATA_ETH_LABELS_2026.md](DATA_ETH_LABELS_2026.md) | 시기 민감 피처 재검증용 최신 데이터셋(2024~2025년, 746개 주소) |
| [DATA_COLLECTION_LOG.md](DATA_COLLECTION_LOG.md) | 결정 로그 — BCCC-2025 신청 현황, SDN_LIST 갱신, API 키 노출 이슈 등 시간순 기록 |

## 3. EDA

| 문서 | 내용 |
|---|---|
| [EDA_XBLOCK.md](EDA_XBLOCK.md) | XBlock 데이터 품질 점검 — 정상 라벨 43.7%가 활동 0건 등 |
| [EDA_ETH_LABELS_2026.md](EDA_ETH_LABELS_2026.md) | ETH-Labels-2026 데이터 품질 점검 — fraud 표본이 사건 2개에 쏠림 등 |

## 4. 데이터 분할

| 문서 | 내용 |
|---|---|
| [DATA_SPLIT.md](DATA_SPLIT.md) | 주소 단위 train/val/test 분할(누수 방지) — GOG의 핵심 결함이었던 거래 단위 분할 문제 교정 |

## 5. 피처 엔지니어링

| 문서 | 내용 |
|---|---|
| [DOMAIN_RESEARCH.md](DOMAIN_RESEARCH.md) | FATF/Chainalysis 등 근거로 도출한 6개 피처 후보 |
| [FEATURE_ENGINEERING.md](FEATURE_ENGINEERING.md) | 6개 후보 구현·검증 결과 — 3개는 XBlock에서 lift 확인, 3개는 게이팅 룰로 재분류 |

## 6~8. 모델 학습·평가·선정

| 문서 | 내용 |
|---|---|
| [MODEL_TRAINING.md](MODEL_TRAINING.md) | 5-fold CV 모델 비교, 어블레이션, 하이퍼파라미터 튜닝 |
| [TEST_EVALUATION.md](TEST_EVALUATION.md) | held-out test set 최초/유일 평가 + 등급 임계값 설정 |
| [FINAL_MODEL_SELECTION.md](FINAL_MODEL_SELECTION.md) | 최종 모델 확정 + 프로덕션 아티팩트(`../models/`) |

## 9~10. 해석·통합

| 문서 | 내용 |
|---|---|
| [MODEL_INTERPRETATION.md](MODEL_INTERPRETATION.md) | SHAP 기반 모델 해석 — permutation importance와 교차 검증, 정탐/미탐/오탐 사례 분석 |
| [GATING_INTEGRATION.md](GATING_INTEGRATION.md) | 게이팅+병렬 표시 아키텍처를 라이브 API에 통합 (백엔드), 실제 서버로 curl 검증 |

## 재현 명령어 규칙

모든 문서의 "재현 명령어"는 `risk-scoring/`을 cwd로 가정한다:

```bash
cd risk-scoring
python3 scripts/<단계별 폴더>/<스크립트>.py
```

스크립트는 파이프라인 단계별로 `scripts/` 아래 정리돼 있다: `data_collection/`, `eda/`, `features/`, `model/`. 룰 엔진 자체(라이브 컴플라이언스 룰 유지보수) 관련 스크립트는 `scripts/` 최상위에 그대로 있다(`update_sdn_list.py`, `evaluate_time_window_rules.py`, `generate_rulebook_report.py`).
