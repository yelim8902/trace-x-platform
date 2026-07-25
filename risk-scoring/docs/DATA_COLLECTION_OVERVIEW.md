# 데이터 수집 전체 개요

이번 리스크 스코어링 엔진 재설계에서 "데이터를 어떻게 모았는가"를 한눈에 보기 위한 요약 문서. 각 데이터셋의 세부 사항은 개별 문서(`DATA_XBLOCK.md`, `DATA_SPLIT.md`, `DATA_ETH_LABELS_2026.md`, `DATA_COLLECTION_LOG.md`)에 있고, 여기서는 **왜 이 순서로 이 데이터들을 모았는지, 서로 어떤 역할을 하는지**를 설명한다.

## 1. 왜 처음부터 다시 모았는가

기존에는 GOG(Graph of Graphs) 논문 데이터셋으로 실험했었다. 이걸 버린 이유 3가지:

1. **재현 불가** — 원본 데이터가 팀 저장소에서 삭제됐고 git 히스토리도 스쿼시돼 있어서 어떻게 만들어졌는지 되짚을 수 없었음.
2. **라벨 정의 불일치** — GOG 라벨은 "지갑의 자금세탁 위험"이 아니라 "토큰/컨트랙트의 피싱·스캠 카테고리"였음. TRACE-X가 실제로 풀려는 문제(지갑 주소 단위 위험 스코어링)와 라벨이 가리키는 대상 자체가 달랐음.
3. **누수 의심** — 주소 단위 라벨을 거래 단위로 그대로 복사해 데이터셋을 만든 방식이라, train/test를 무작위로 나누면 같은 주소의 거래가 양쪽에 섞였을 가능성이 높음. Stage2(ML) 제거 시 정확도가 38.70%로 폭락했던 ablation 결과가 이 의심과 맞아떨어짐.

그래서 **"어떤 주소가 왜 fraud로 라벨링됐는지 출처를 직접 추적할 수 있는" 데이터**로 처음부터 다시 모으기로 했다.

## 2. 데이터셋 A — XBlock (베이스라인, 2016~2019년)

- **어디서**: Sun Yat-sen University InPlusLab이 배포하는 XBlock 플랫폼, Kaggle 경유로 다운로드.
- **왜 이걸 골랐나**: 라벨이 Etherscan의 `phish-hack` 공개 태그를 그대로 쓴 **지갑 주소 단위** 라벨이라, GOG와 달리 우리가 풀려는 문제와 라벨 정의가 일치함. Kaggle을 통해 누구나 재다운로드 가능해서 재현성도 확보됨.
- **규모**: 원본 그래프 297만 노드/1,355만 엣지 중, 확정 피싱 1,165개 전체 + 정상 5,000개 샘플(seed=42)을 뽑아 6,165개 주소로 작업 세트를 만듦.
- **한계**: 2016~2019년 수집이라 최신 사기 수법(믹서, 제재 대상 등)을 반영 못 함 — 이게 데이터셋 B를 따로 모은 직접적인 이유.
- 상세: `DATA_XBLOCK.md`

## 3. 데이터 분할 — 주소 단위로 누수 차단

XBlock 6,165개를 `ground_truth_label` 기준 stratified 70/15/15로 train(4,315)/val(924)/test(926) 분할. **거래 단위가 아니라 주소 단위로 통째로 나눠서**, GOG 때처럼 같은 주소가 train과 test에 걸쳐 있는 상황을 원천 차단. 분할 직후 스크립트로 세 집합 간 교집합이 정말 0인지 두 번(내부 assert + 디스크에서 다시 읽어 재검증) 확인함.

**test set(926개)은 8~9단계(최종 평가, SHAP 해석) 전까지 열어보지 않는다** — 지금까지 나온 모든 lift/recall 수치는 전부 train(또는 train+val)에서 나온 것.

상세: `DATA_SPLIT.md`

## 4. 데이터셋 B — ETH-Labels-2026 (신선도 검증용, 2024~2025년)

XBlock만으로는 "최근 해킹 주소로도 검증해야 하지 않냐"는 요구를 채울 수 없어서 두 번째 데이터셋을 새로 구축했다.

### 시도했다가 막힌 경로

Etherscan 공식 라벨 API(`getlabelmasterlist`, `exportaddresstags`)로 직접 최신 라벨을 받으려 했으나 **Pro Plus 티어($899/월)가 필요**해서 막힘. 라벨 페이지를 직접 스크래핑하는 것도 Etherscan ToS 위반 소지가 있어 시도하지 않음.

### 실제로 쓴 경로

- **라벨 출처**: `dawsbot/eth-labels` (GitHub, 무료, `pushed_at: 2026-07-10`로 거의 실시간 유지보수) — Etherscan 라벨과 같은 성격의 데이터를 공개 저장소로 미러링해주는 프로젝트.
- **`scripts/build_eth_labels_dataset.py`**: 이 저장소의 `accounts.json`(EVM 전체 144,378개 라벨)을 스크립트가 직접 다운로드(`urlretrieve`, 캐싱)해서, fraud 키워드가 붙은 라벨 249개(bybit-exploit, wazirx-exploit 등 2024~2025년 실제 사건 10개) + 명확히 합법적인 카테고리(CEX/DeFi/비영리)에서 정상 497개를 샘플링(seed=42) → `eth_labels_2026_manifest.json`.
- **`scripts/fetch_eth_labels_transactions.py`**: 이 746개 주소 각각에 대해 **Etherscan 무료 티어 API**(`txlist`+`tokentx`)로 실제 거래내역을 가져옴. 요청 간 0.25초 간격(무료 티어 초당 5회 제한 안전마진), 746개 처리에 약 26.5분 소요.
- **결과**: fraud 249개 중 220개(88.4%), normal 497개 중 386개(77.7%)에서 실제 온체인 활동 확인.

### 알려진 API 키 노출과 처리

이 작업 도중 Etherscan API 키(`91FZVKNIX7GYPESECU5PHPZIMKD72REX43`)가 **공개 GitHub 저장소에 하드코딩되어 노출**돼 있는 걸 발견함(`aml-risk-engine2` 저장소 여러 파일). 폐기 후 재발급이 원칙이지만, 이번 세션에서는 사용자 판단으로 기존 키를 그대로 재사용하기로 결정 — 코드에는 하드코딩하지 않고 `.env`에서만 읽도록 함(`load_api_key()`).

### 이 데이터셋의 역할

XBlock과 다른 목적: **모델 학습용이 아니라, 시기에 민감한 피처(제재 대상 근접도, 믹서 근접도, 프라이버시 프로토콜 접촉)를 재검증하기 위한 데이터셋**. XBlock(2016~2019)은 OFAC 암호화폐 제재와 Tornado Cash(2019년 말 출시) 둘 다와 시간대가 안 겹쳐서 이 피처들의 신호를 검증할 수 없었음 — 2024~2025년 데이터인 이 데이터셋에서 재시도 예정.

상세: `DATA_ETH_LABELS_2026.md`

## 5. 데이터셋 C — BCCC-DeFiFraudTrans-2025 (신청 완료, 승인 대기)

York University BCCC가 배포하는 2017~2024년 벤치마크(1,026,867건 트랜잭션, 79개 피처, Etherscan 태그 기반 라벨을 이상탐지·중복제거로 교차검증). Request form을 제출했고(승인 성공 화면 확인), 아직 승인 메일은 도착하지 않음. 승인되면 XBlock/ETH-Labels-2026과 스키마를 비교해 병합할지 독립 검증셋으로 쓸지 결정 예정.

상세: `DATA_COLLECTION_LOG.md`

## 6. 세 데이터셋의 역할 정리

| 데이터셋 | 시기 | 역할 | 상태 |
|---|---|---|---|
| XBlock | 2016~2019 | 모델 학습/검증/테스트 (train/val/test 분할) | ✅ 확보, 분할 완료 |
| ETH-Labels-2026 | 2024~2025 | 시기 민감 피처(제재/믹서/프라이버시) 재검증 | ✅ 확보, EDA/재검증 예정 |
| BCCC-2025 | 2017~2024 | 향후 병합 또는 독립 검증셋 | ⬜ 승인 대기 |

## 7. 재현성 원칙

이번 데이터 수집은 전부 **스크립트 + 고정 seed**로 재현 가능하게 만들었다 (GOG 때처럼 "한 번 만들고 사라지는" 데이터 없음):

```bash
cd risk-scoring
# XBlock
kaggle datasets download -d xblock/ethereum-phishing-transaction-network -p data/xblock/
python3 scripts/extract_features_from_pkl.py
python3 scripts/extract_txs_for_rules.py --input "data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl" --addresses data/dataset/xblock_extracted.json --output data/dataset/xblock_transactions.json
python3 scripts/split_dataset.py

# ETH-Labels-2026
python3 scripts/build_eth_labels_dataset.py
python3 scripts/fetch_eth_labels_transactions.py
```

큰 산출물(`data/dataset/*.json`)은 용량 때문에 `.gitignore`로 커밋 대상에서 뺐고, 대신 재현 명령어와 (XBlock의 경우) 주소 목록만 담은 경량 매니페스트(`split_manifest_*.txt`)를 커밋해서 "어떤 주소가 어디에 쓰였는지"는 항상 git에 남도록 했다.
