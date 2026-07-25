# 피처 엔지니어링

`docs/DOMAIN_RESEARCH.md`에서 나온 6개 후보를 구현·검증한 기록. 검증은 전부 train set(4,315개, `data/dataset/split_manifest_train.txt`)에서만 했고 val/test는 안 건드림.

## 1. `peel_chain_score` (구현·검증 완료)

### 정의

큰 금액이 들어온 뒤 매 홉마다 이전 금액의 일정 비율만 남기고(나머지는 peel) 새 주소로 계속 전달하는 체인. 비트코인 도난 사건의 약 70%에서 나타나는 패턴 (Chainalysis/Merkle Science/AMLTRIX — `docs/DOMAIN_RESEARCH.md` 참고).

**B-201(Layering Chain)과 정반대 조건**: B-201은 각 홉 금액이 ±5% 이내로 비슷해야 발동하는데, peel chain은 매 홉 금액이 줄어들어야 함. 지금 룰북은 이 패턴을 못 잡고 있었음.

### 구현

- `core/aggregation/peel_chain.py` — `find_peel_chains()`(DFS로 금액이 단조 감소하는 경로 탐색), `peel_chain_score()`(ML 피처용 요약)
- `_path_is_decaying()`: 연속 홉의 금액 비율이 `[min_decay_pct, max_decay_pct]` 구간 안에서 계속 줄어드는지 확인
- 합성 데이터 5개 케이스로 로직 검증: 진짜 peel chain(탐지), layering chain(비탐지, B-201과 구분됨 확인), 단일 홉(비탐지), 금액 증가(비탐지), 시작금액 과소(비탐지) — 전부 기대대로 동작

### 데이터 문제와 해결

`xblock_transactions.json`은 타겟 주소의 1홉 거래만 있어서 멀티홉 패턴 검증이 불가능했음. `scripts/extract_peel_chain_features.py`를 새로 작성해서 `MulDiGraph.pkl`(원본 그래프, 이미 로컬에 있음)에서 주소별로 **depth≤5, breadth≤5(가중치 상위), 노드수≤300** 제한된 BFS 서브그래프를 직접 뽑음. train 4,315개 전체 처리에 그래프 로딩 포함 약 30초 소요 (예상보다 훨씬 빠름).

### 임계값 튜닝 (train set 스윕)

| 설정 | fraud 검출률 | normal 오탐률 | lift |
|---|---|---|---|
| min_hops=3, decay 0.5~0.95 (첫 시도) | 2.0% | 0.00% | inf |
| min_hops=2, decay 0.5~0.95 | 20.4% | 1.37% | 14.9 |
| min_hops=3, decay 0.3~0.97 | 4.2% | 0.06% | 73.0 |
| **min_hops=2, decay 0.3~0.97 (채택)** | **26.1%** | **1.74%** | **15.0** |
| min_hops=4, decay 0.5~0.95 | 0.1% | 0.00% | inf |

fan-in/fan-out(B-203/204) 튜닝 때와 같은 패턴 — 처음 정의(min_hops=3)가 너무 엄격해서 recall이 대부분 죽어있었고, min_hops=2로 완화하니 recall이 10배 이상 뛰면서도 lift는 여전히 15.0으로 강한 신호 유지. **min_hops=2, decay 0.3~0.97**을 최종 채택 (`peel_chain.py`의 기본값으로 반영).

### 최종 검증 결과 (train set, 최종 임계값)

- fraud 815개 중 213개(26.1%) 탐지
- normal 3,500개 중 61개(1.74%) 탐지
- lift 15.0

## 2. `sanction_hop_distance` / `mixer_hop_distance` (구현 완료, XBlock으로는 검증 불가 판정)

### 구현

- `core/aggregation/subgraph_utils.py` — peel_chain과 공용으로 쓰는 BFS 서브그래프 빌더를 분리 (`direction="out"|"both"` 지원)
- `core/aggregation/exposure_distance.py` — `hop_distance_to_any()`(양방향 BFS 최단거리), `exposure_score_from_hops()`(감쇠 점수, decay=0.4 기준 hop1=40점/hop2=16점...)
- 합성 데이터로 로직 자체는 검증 완료 (2-hop 거리 정확히 계산됨)

### XBlock으로 검증 시도 → 데이터 부족으로 불가 판정

1. **1차 시도**: 기존 `SDN_LIST`(78개), `MIXER_LIST`(3개)가 XBlock 297만 노드 그래프에 SDN 2개/믹서 0개만 존재 — 애초에 겹칠 게 없음
2. **SDN_LIST를 실제 OFAC 공식 XML(Treasury.gov)에서 947개(ETH 96개)로 갱신** — `scripts/update_sdn_list.py` 실행. 라이브 룰 C-001/E-102가 읽는 파일 포맷이 달라서(레거시 스크립트는 dict로 저장하는데 `ListLoader`는 flat list만 읽음) 스크립트를 수정한 뒤 실행, `AddressAnalyzer`로 C-001 발동 회귀 테스트까지 통과 확인
3. **947개로 늘려도 여전히 그래프 노드로는 3개뿐** — train set 4,315개 주소 전부에 대해 5홉 양방향 BFS로 SDN 도달 가능성을 확인한 결과 **11개(0.25%)만 도달 가능, 그나마 hop 거리가 전부 4~5(가장 먼 축)**. fraud 3개/normal 8개로는 통계적으로 무의미.

**결론**: 리스트 완성도 문제가 아니라 **시기 불일치** — OFAC 암호화폐 제재는 대부분 2020년 이후에 집중되는데 XBlock 그래프는 2016~2019년 데이터라 원천적으로 겹칠 시간대가 아님. `sanction_hop_distance`/`mixer_hop_distance`는 **구현은 완료했지만 이번 데이터셋으로는 검증 보류** — 2017~2024년을 포괄하는 BCCC-DeFiFraudTrans-2025가 도착하면 재시도.

**부수 효과**: SDN_LIST 78→947 갱신은 이 피처와 무관하게 라이브 컴플라이언스 룰(C-001, E-102) 품질 자체를 개선한 실질적 성과.

## 3. `privacy_protocol_involved` (구현 완료, XBlock으로는 0% — 예상된 결과)

### 재정의

FATF의 "AEC/privacy coin 전환" 레드플래그는 이더리움에 그대로 적용 안 됨(별도 privacy coin이 없음) — 가장 가까운 대응은 **Tornado Cash/Railgun/Aztec 같은 프라이버시 프로토콜과의 직접 접촉**으로 재정의. `mixer_hop_distance`와 달리 1-hop 직접 접촉만 보는 단순 이진 피처라 멀티홉 그래프 불필요, 1-hop 거래 목록만으로 계산 가능.

### 구현

- `core/aggregation/privacy_protocol.py` — `privacy_protocol_involved(sent, received, privacy_addresses)`
- **부수 작업**: 기존 `MIXER_LIST`가 3개뿐이라(`sanction_hop_distance` 작업 때 발견) `dawsbot/eth-labels`의 `tornado-cash`(64)/`mixer`(35)/`ethereum-mixer`(1)/`aztec`(1) 라벨에서 67개로 확장, `data/lists/bridge_contracts.json`의 `mixer_services` 갱신. `AddressAnalyzer`로 E-101(믹서 직접 노출) 발동 회귀 테스트 통과.

### XBlock 검증 결과

**fraud 0/815 (0.00%) / normal 0/3500 (0.00%)** — `sanction_hop_distance` 때와 똑같은 시기 불일치. Tornado Cash는 2019년 12월 출시라 XBlock 수집 기간(2016~2019)과 거의 안 겹침. 리스트를 67개로 늘려도 XBlock 자체의 시간대 문제라 해결 안 됨.

### 다음 검증처

`sanction_hop_distance`/`mixer_hop_distance`와 마찬가지로 **ETH-Labels-2026**(2024~2025년 데이터, `docs/DATA_ETH_LABELS_2026.md`)에서 재검증 예정 — Tornado Cash가 그 시기엔 실제로 활발히 쓰였으므로 신호가 나올 가능성 높음.

## 4. `amount_deviation_score` / `frequency_deviation_score` (구현·검증 완료)

### 정의

"이 주소 자신의 과거 패턴 대비 이탈"을 보는 피처 — 절대 임계값이 아니라 **변동계수(coefficient of variation = 표준편차/평균)**로 정규화해서, 스케일과 무관하게 "이 주소 활동이 얼마나 불규칙한가"를 봄.

- `amount_deviation_score`: 거래 금액들의 변동계수
- `frequency_deviation_score`: 거래 간격들의 변동계수

**기존 B-103(`interarrival_std`, `core/aggregation/stats.py`)과 차이**: B-103은 거래 간격의 원시 표준편차(초 단위)를 그대로 써서 스케일에 의존적임(간격이 원래 긴 주소는 그냥 절대값이 커서 걸릴 수 있음). 여긴 평균으로 나눈 상대값이라 스케일 무관.

**도메인 근거는 상대적으로 약함**(`docs/DOMAIN_RESEARCH.md` 발견 4) — 크립토 AML 특화 논문이 아니라 일반 이상탐지 원칙에 기반. 그래도 실제 검증 결과는 이번 세션에서 가장 강한 축에 속함.

### 구현

`core/aggregation/deviation_features.py` — `amount_deviation_score()`, `frequency_deviation_score()`, `deviation_features()`(요약)

### 검증 결과 (train set)

| 피처 | fraud median | normal median |
|---|---|---|
| amount_deviation_score | 1.32 | 0.56 |
| frequency_deviation_score | 2.03 | 1.18 |

임계값 스윕 (일부):

| 피처 | 임계값 | fraud 검출 | normal 오탐 | lift |
|---|---|---|---|---|
| amount | >=0.8 | 72.3% | 6.60% | 10.9 |
| amount | **>=1.0 (채택)** | **62.7%** | **4.20%** | **14.9** |
| amount | >=1.5 | 40.2% | 0.71% | 56.3 |
| frequency | >=0.8 | 82.7% | 6.54% | 12.6 |
| frequency | **>=1.0 (채택)** | **78.2%** | **5.43%** | **14.4** |
| frequency | >=1.5 | 61.1% | 2.31% | 26.4 |

두 피처 모두 균형 잡힌 `>=1.0`을 채택 (`deviation_features.py`의 `AMOUNT_DEVIATION_THRESHOLD`/`FREQUENCY_DEVIATION_THRESHOLD`).

### ⚠️ 결측치 편향 발견 (`build_feature_matrix.py`로 train 전체 매트릭스 만든 뒤 확인)

`amount_deviation_score`는 거래 금액이 2개 이상, `frequency_deviation_score`는 타임스탬프가 3개 이상 있어야 계산됨(`_coefficient_of_variation`). 그런데 이 조건을 만족하는 비율 자체가 fraud/normal 간에 크게 다름:

| | has_data (amount) | has_data (frequency) |
|---|---|---|
| fraud (815) | 785개 (96.3%) | 699개 (85.8%) |
| normal (3,500) | 656개 (18.7%) | 320개 (9.1%) |

즉 위 lift 테이블의 "fraud 62.7% / normal 4.20%" 같은 검출률은 **전체 모집단 기준(결측=미검출로 처리)**이라, 상당 부분이 "이 주소가 애초에 지갑 히스토리가 로그에 충분히 있는가"라는 커버리지 차이에서 나온 것이지 순수하게 변동계수 크기 차이만은 아님. 데이터를 가진 주소로만 좁혀도 fraud 65.1% vs normal 22.4%로 여전히 차이는 있어서 신호 자체가 없는 건 아니지만, "커버리지"와 "크기"가 뒤섞여 있다는 점은 분리해서 봐야 함.

**해석 두 가지**: (1) 피싱 주소는 피해자로부터 자금을 받아 여러 홉으로 릴레이하므로 실제로 거래가 더 많이/불규칙하게 생기는 게 자연스러움 (진짜 행동 신호) — 또는 (2) XBlock의 "normal" 5,000개 샘플에 활동이 거의 없는 지갑이 많이 섞여 있어서 생기는 표본 구성 artifact. 둘 다 배제 불가, 지금 데이터로는 구분 안 됨.

**6단계(모델 학습) 대응**: None을 임의로 0 등으로 임퓨테이션하지 않고, 결측치를 자체 분기 조건으로 학습하는 NaN-native 트리 모델(`sklearn.ensemble.HistGradientBoostingClassifier`)을 쓰기로 함 — "값이 없다"는 사실 자체를 모델이 독립적인 분기 신호로 다루게 해서 커버리지 편향을 감추지 않고 그대로 노출시킴. SHAP(9단계)에서도 이 모델은 `shap.TreeExplainer`로 지원됨.

## 6개 후보 진행 상황 요약

| # | 피처 | 상태 |
|---|---|---|
| 1 | peel_chain_score | ✅ 구현·검증 완료 (lift 15.0) |
| 2 | sanction_hop_distance | ✅ 구현 완료, XBlock 검증 보류 (시기 불일치) |
| 3 | mixer_hop_distance | ✅ 구현 완료, XBlock 검증 보류 (시기 불일치) |
| 4 | privacy_protocol_involved | ✅ 구현 완료, XBlock 검증 보류 (시기 불일치) |
| 5 | amount_deviation_score | ✅ 구현·검증 완료 (lift 14.9) |
| 6 | frequency_deviation_score | ✅ 구현·검증 완료 (lift 14.4) |

**6개 전부 구현 완료.** 2,3,4번은 ETH-Labels-2026(2024~2025년) 데이터로 재검증 예정 — 시기가 맞아서 신호가 나올 가능성 높음.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/extract_peel_chain_features.py --output data/dataset/peel_chain_train.json
```
