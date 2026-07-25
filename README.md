# Trace-X Platform

Trace-X는 블록체인 주소의 거래 흐름을 수집해 자금세탁(AML) 위험도를 분석하는 통합 플랫폼입니다. **룰 기반 컴플라이언스 엔진**과 **학습된 ML 모델**을 하나의 점수로 섞지 않고 별도 트랙으로 병렬 반환하며, 특정 컴플라이언스 룰이 발동하면 두 점수와 무관하게 최우선 검토가 필요하다는 신호(게이팅)를 추가로 얹습니다.

```text
Python 3.12 · Flask · scikit-learn (HistGradientBoosting) · SHAP · React · TypeScript · Docker Compose
```

## 왜 이렇게 설계했는가

규제 산업에서는 정확도만큼이나 "왜 이렇게 판단했는가"가 중요합니다. 룰 신호를 ML 피처로 섞어 하나의 점수로 만드는 설계는 "이 점수가 왜 나왔는지" 역추적이 불가능하다는 근본적 한계가 있습니다. 그래서 이 프로젝트는:

- **룰 트랙**: OFAC SDN 리스트 직접 접촉, 고액 거래 임계값 등 법적으로 이진 판단이 가능한 사실을 특금법·FATF 조항을 직접 인용해 탐지 (`risk-scoring/rules/tracex_rules.yaml`, 3개 축 총 28개 룰)
- **ML 트랙**: 자금 집중/분산, 그래프 구조, 거래 패턴의 개인 기준선 대비 이상치 등 룰의 고정 임계값으로 표현하기 어려운 비선형 조합을 학습된 가중치로 판단 (15개 피처, `HistGradientBoostingClassifier`)
- **게이팅**: 두 트랙이 각자 독립적으로 판단한 뒤, 제재·믹서 직접 노출 같은 컴플라이언스 룰이 발동하면 두 점수와 무관하게 최우선 검토 신호를 추가

를 처음부터 분리된 아키텍처로 설계했습니다. 데이터 수집부터 라벨 정의, 피처 엔지니어링, 모델 학습/평가, SHAP 기반 해석까지 표준 9단계 ML 라이프사이클로 진행한 전체 기록은 [`risk-scoring/docs/README.md`](risk-scoring/docs/README.md)에 각 단계별 실제 실행 명령어와 검증 수치로 남겨뒀습니다.

## 핵심 결과

| 지표 | 값 |
| --- | ---: |
| Accuracy | 97.0% |
| Precision | 93.0% |
| Recall | 90.9% |
| ROC-AUC | 99.3% |
| PR-AUC | 97.3% |

held-out 평가 세트(926개 주소, 최초·유일 1회 평가) 기준. 학습에 전혀 포함되지 않은 이후 시점의 실제 사고 관련 주소로도 재확인했습니다 — 특정 사건을 암기한 게 아니라 자금세탁의 행동적 패턴을 일반화해서 학습했다는 근거로 보고 있습니다. 상세 검증 과정과 한계는 [`risk-scoring/docs/README.md`](risk-scoring/docs/README.md) 참고.

## 구성

```text
frontend      React + TypeScript UI
backend       Flask API, Etherscan 데이터 수집, 그래프 변환
risk-scoring  Flask API, TRACE-X 룰북 기반 리스크 스코어링
scripts       로컬 실행, 중지, 헬스체크 스크립트
docs          구조, API, 배포, 문제 해결 문서
```

## 기본 포트

| Service | Port | Health |
| --- | ---: | --- |
| Frontend | 5173 | http://localhost:5173 |
| Backend | 8888 | http://localhost:8888/health |
| Risk Scoring | 5001 | http://localhost:5001/health |

## 로컬 실행 전제조건

- Python 3.12 권장
- Node.js/npm
- Backend는 `eth-abi`가 런타임에 `pkg_resources`를 사용하므로 `setuptools>=61,<81`이 필요합니다.

`./scripts/start-all.sh`는 각 Python 서비스의 `venv`를 만들고 의존성을 설치합니다. 기존 `backend/venv`에서 `ModuleNotFoundError: No module named 'pkg_resources'`가 나면 아래처럼 backend 의존성을 다시 설치합니다.

```bash
cd backend
source venv/bin/activate
pip install -e .
cd ..
```

## 빠른 시작

```bash
cp .env.example .env
# .env에 ETHERSCAN_API_KEY 입력

./scripts/start-all.sh
./scripts/health-check.sh
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

## Docker 실행

```bash
cp .env.example .env
# .env에 ETHERSCAN_API_KEY 입력

docker compose up --build
```

## 핵심 분석 흐름

```text
사용자 주소 입력
  -> Frontend
  -> Backend /api/analysis/risk-scoring
  -> Etherscan V2 거래 수집 (속도 제한 대응 + 홉당 연결 수 제한)
  -> Backend 그래프/거래 포맷 변환
  -> Risk Scoring /api/analyze/address
       ├─ 룰 엔진: TRACE-X 룰북(28개) 평가 -> risk_score / fired_rules
       ├─ ML 스코어러: 15개 피처 -> HistGradientBoosting -> ml_score / SHAP 근거
       └─ 게이팅: 컴플라이언스 룰(제재·믹서 직접 노출) 발동 시 두 점수와 무관하게 최우선 검토 신호
  -> Frontend 결과 표시 (룰/ML 병렬 표시 + 종합 판단)
```

## 문서

**프로젝트 구조/운영**

- [Architecture](docs/ARCHITECTURE.md)
- [API](docs/API.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

**리스크 스코어링 엔진 설계 — 문제 정의부터 SHAP 해석까지 9단계 전체 기록**

- [`risk-scoring/docs/README.md`](risk-scoring/docs/README.md) — 데이터 수집·라벨 정의, EDA, 피처 엔지니어링(도메인 리서치 포함), 모델 학습/튜닝, 평가/임계값, 룰-ML 역할 분리, SHAP 해석까지 각 단계별 실행 명령어와 검증 수치
- [`risk-scoring/docs/GATING_INTEGRATION.md`](risk-scoring/docs/GATING_INTEGRATION.md) — 게이팅+병렬 표시 아키텍처를 라이브 API에 통합한 기록, 실제 curl 검증 사례

## 정리 기준

이 레포는 실행 가능한 최종본을 기준으로 정리했습니다. 원본 연구 자료, PDF, 대용량 XML/ZIP, 로컬 DB, venv, cache, 모델 pickle 파일은 Git에 올리지 않습니다.
