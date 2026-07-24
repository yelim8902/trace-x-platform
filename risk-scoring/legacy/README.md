# Legacy (GOG 시대 코드)

이 폴더는 GOG(Graph of Graphs) 논문 데이터 기반으로 시도했던 "1단계 룰+그래프 휴리스틱 / 2단계 ML" 하이브리드 아키텍처의 잔재예요. GOG 데이터가 팀 저장소에서 삭제되어 재현 불가능하고, 실제로 라이브 API(`api/app.py`에 등록된 블루프린트)에서 사용되지 않는다는 게 확인돼서 이쪽으로 옮겼어요. 자세한 배경은 `../docs/DATA_COLLECTION_LOG.md` 참고.

**여기 있는 코드는 유지보수되지 않고, import 경로도 이동 후 그대로 깨져 있을 수 있어요.** 참고용으로만 보고, 재사용하려면 현재 구조(`core/`, `api/`)에 맞게 다시 확인해야 해요.

## 구성

- `core/scoring/` — `stage1_scorer.py`(룰+그래프 통계 휴리스틱, ML 아님), `stage2_scorer.py`(진짜 ML, LR/RF/GB), `hybrid_address_analyzer.py`, `ai_weight_learner.py`, `improved_rule_scorer.py`, `dataset_builder.py`, `real_dataset_builder.py`
- `core/aggregation/` — `mpocryptml_scorer.py`, `mpocryptml_normalizer.py`, `temporal_features.py`, `neighborhood_features.py` (Stage1 전용, 라이브 룰 엔진은 안 씀)
- `core/data/etherscan_client.py` — GOG 시절 실데이터 수집기. **하드코딩된 API 키가 있었음** (`91FZVKNIX7GYPESECU5PHPZIMKD72REX43`, 이미 폐기 대상으로 별도 기록됨 — `docs/DATA_COLLECTION_LOG.md`)
- `api/routes/demo_analysis.py` — `/api/analyze/address/demo` 데모 엔드포인트. `app.py`에서 등록 해제함(프론트엔드가 호출한 적 없고, 필요로 하는 Stage2 모델 `.pkl` 파일도 저장소에 없어서 실제로는 Stage1만 degraded 모드로 돌던 상태였음)
- `api/routes/hybrid_address_analysis.py` — 애초에 `app.py`에 등록된 적 없는 라우트
- `scripts/` — GOG 데이터 수집·학습·평가·튜닝 스크립트 전부 (기존 `scripts/archive/`와 최상위의 GOG 전용 스크립트를 여기로 통합)

## 왜 옮겼는가

1. GOG 원본 데이터가 삭제돼서 이 코드들이 실제로 만든다고 주장하는 결과(Accuracy 99.20% 등)를 재현할 방법이 없음
2. `stage2_scorer.py`가 학습하는 라벨(`ground_truth_label`)이 "지갑의 자금세탁 위험"이 아니라 GOG 데이터셋 자체의 "토큰이 피싱/스캠 카테고리인가"였음 — 지금 TRACE-X가 풀려는 문제와 라벨 정의가 다름
3. `demo_analysis.py`를 제외하면 나머지는 애초에 라이브 API에 연결된 적이 없음
4. 이동 전 전체 의존성을 grep으로 확인해서, 라이브 코드(`core/rules/`, `core/scoring/address_analyzer.py`, `core/scoring/engine.py`, `api/routes/address_analysis.py`, `api/routes/scoring.py`)는 이 폴더의 어떤 것도 import하지 않음을 검증함 (`core/scoring/engine.py`가 `ai_weight_learner`를 optional import하지만 `try/except ImportError`로 감싸져 있어 실패해도 기본 sum 방식으로 안전하게 폴백됨)

## 지금 진행 중인 재구축과의 관계

새 파이프라인(`docs/` 아래 `DATA_XBLOCK.md`부터 시작하는 문서들, XBlock 데이터 기반)은 이 폴더의 아이디어(PPR, fan-in/fan-out, 그래프 통계 기반 피처, 룰+ML 하이브리드) 중 유효한 부분은 재사용하되, 데이터·검증 방식·룰과 ML의 결합 구조(게이팅+병렬 표시)는 처음부터 다시 설계함.
