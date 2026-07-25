# 데이터셋: ETH-Labels-2026 (최신 해킹 주소)

XBlock(2016~2019년 피싱)과 별개로, 세션 초반에 논의했던 "최신 해킹 주소로 검증"을 실제로 하기 위해 구축한 두 번째 데이터셋.

## 출처

- **저장소**: [dawsbot/eth-labels](https://github.com/dawsbot/eth-labels) (기본 브랜치 `v1`, `pushed_at: 2026-07-10` — 거의 실시간으로 유지보수됨)
- **원본 데이터**: `data/json/accounts.json` — EVM 체인 전반 144,378개 라벨 주소 (Ethereum만 113,194개)
- **왜 이걸 썼나**: Etherscan의 공식 Metadata API(`getlabelmasterlist`, `exportaddresstags`)로 라벨별 주소를 직접 export하려 했으나 **Pro Plus 티어($899/월) 필요**로 막혀서, 같은 데이터를 무료로 공개 제공하는 이 저장소를 대신 사용.

## 라벨 정의 — XBlock과의 차이

XBlock은 "phish-hack"이라는 뭉뚱그린 카테고리 하나였는데, 이 데이터셋은 **개별 사건 단위**로 라벨링됨:

| 라벨 | 개수 | 실제 사건 |
|---|---|---|
| filament-exploit | 101 | |
| bybit-exploit | 77 | 2025년 Bybit 해킹 (역대 최대 규모 암호화폐 해킹 중 하나) |
| wazirx-exploit | 27 | 2024년 WazirX 거래소 해킹 |
| bingx-exploit | 11 | 2024년 BingX 거래소 해킹 |
| unibtc-exploit | 10 | |
| truebit-exploit | 6 | |
| zkswap-exploit | 6 | |
| fraud-proof | 5 | |
| radiant-capital-exploit | 4 | 2024년 Radiant Capital 해킹 |
| onyxdao-exploit | 2 | |

**총 249개 fraud 주소** — 전부 2024~2025년 실제 확인된 사건.

## 정상 주소 (497개)

같은 데이터셋에서 명확히 합법적인 카테고리만 선택해 샘플링(`seed=42`):
- CEX: bitget, deribit, bilaxy
- DeFi 프로토콜: sushiswap, balancer, bancor, yearn, aave, synthetix, pendle, the-graph
- 비영리: nonprofit, charity, endaoment

**의도적으로 제외한 카테고리**: `mev-bot`(추출적 행위), `airdrop-hunter`(파밍 행위), `sybil-delegate`(기만적 다중 정체성 — 이름부터 적대적), `blocked`(사유 불명), `parity-bug`(자금 동결, 사기 아님) — 라벨 노이즈 위험이 있는 애매한 카테고리라 정상 기준에서 제외.

## 규모

- fraud: 249개
- normal: 497개 (중복 제거 후)
- 총 746개

## 거래내역 수집 결과 (`fetch_eth_labels_transactions.py` 실행, 2026-07-26)

Etherscan v2 API(무료 티어, `txlist`+`tokentx`, 요청당 0.25초 간격)로 746개 주소 전체의 거래내역을 수집. 소요 시간 약 1,591초(26.5분).

| | 라벨 개수 | 실제 온체인 활동 있음 |
|---|---|---|
| fraud | 249 | 220 (88.4%) |
| normal | 497 | 386 (77.7%) |

활동이 없는 나머지(fraud 29개, normal 111개)는 메인넷 트랜잭션이 0건인 주소 — 새로 신고돼 아직 자금 이동이 없거나, 컨트랙트 자체 주소(트랜잭션 발신자가 아님) 등으로 추정. 별도 필터링 없이 원본 그대로 저장(`data/dataset/eth_labels_2026_transactions.json`) — 활동 없는 주소는 하위 피처 계산 단계에서 자연히 신호가 0/None으로 처리됨.

## 알려진 한계

1. **거래 금액이 USD 환산이 아님** — `fetch_eth_labels_transactions.py`가 원시 native/token 단위 값을 그대로 저장함(XBlock처럼 고정 환율 근사조차 안 함). 금액 기반 피처에 이 데이터를 쓰려면 별도 가격 환산이 필요함.
2. **fraud 표본이 10개 사건에 집중** — 249개가 사실상 10개 사건의 관련 주소들이라, "다양한 사기 패턴"이 아니라 "이 10개 사건의 자금 이동 패턴"에 치우칠 수 있음. XBlock(1,165개, Etherscan 커뮤니티 신고 기반, 사건 다양성 높음)과 상호 보완적으로 봐야 함.
3. **정상 샘플이 대형 CEX/프로토콜 위주** — XBlock의 "무작위 미신고 주소"와 성격이 다름. 일반 개인 지갑 대비 훨씬 활동량이 많고 패턴이 규칙적일 수 있음.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/data_collection/build_eth_labels_dataset.py           # 주소 manifest 생성 (API 호출 없음)
python3 scripts/data_collection/fetch_eth_labels_transactions.py      # Etherscan API로 거래내역 수집 (~25-30분)
```
