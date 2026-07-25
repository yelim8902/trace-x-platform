# EDA: ETH-Labels-2026 데이터 품질 점검

`data/dataset/eth_labels_2026_transactions.json`(746개, fraud 249 / normal 497)을 대상으로 실행한 EDA 결과. XBlock과 스키마가 달라(그래프 통계 없음, 개별 사건 라벨 있음) `EDA_XBLOCK.md`와 항목 구성이 조금 다르다.

## 1. 클래스 균형

| 클래스 | 개수 | 비율 |
|---|---|---|
| fraud | 249 | 33.4% |
| normal | 497 | 66.6% |

XBlock(fraud 18.9%)보다 fraud 비율이 훨씬 높음 — XBlock은 정상 5,000개를 임의로 크게 샘플링했지만, 이 데이터셋은 애초에 소규모(fraud 249개 확정 + normal 497개 의도적 샘플)라 균형이 다르게 잡혔음. 모델 학습에 같이 쓸 경우 이 비율 차이를 감안해야 함(class_weight 등).

## 2. 정합성 체크 — 이상 없음

- 주소 중복: 0건
- fraud/normal 라벨 충돌(같은 주소가 양쪽에 존재): 0건

## 3. source_label 분포 — fraud 표본이 10개 사건에 집중

| 사건 | 주소 수 |
|---|---|
| filament-exploit | 101 |
| bybit-exploit | 77 |
| wazirx-exploit | 27 |
| bingx-exploit | 11 |
| unibtc-exploit | 10 |
| truebit-exploit | 6 |
| zkswap-exploit | 6 |
| fraud-proof | 5 |
| radiant-capital-exploit | 4 |
| onyxdao-exploit | 2 |

`DATA_ETH_LABELS_2026.md`에 이미 적어둔 한계가 실측으로 확인됨: 249개 중 178개(filament+bybit)가 사건 2개에 쏠려있음. 이 데이터셋에서 나오는 어떤 피처 신호도 "일반적인 사기 패턴"이 아니라 "이 10개 사건, 특히 filament/bybit 두 사건의 특징"일 수 있다는 점을 감안해야 함 — XBlock(1,165개, 다수의 개별 신고 기반)과 상호보완적으로 봐야 하는 이유.

## 4. 거래 활동 없는 주소

| | 활동 0건 | 비율 |
|---|---|---|
| fraud | 29 / 249 | 11.6% |
| normal | 111 / 497 | 22.3% |

XBlock(정상의 43.7%가 활동 0건)보다 훨씬 낮음 — 이 데이터셋의 normal은 CEX/대형 DeFi 프로토콜 주소 위주라 원래도 활동량이 많기 때문(`DATA_ETH_LABELS_2026.md` 한계 3 참고). fraud/normal 모두 활동 없는 주소가 존재하므로, XBlock과 마찬가지로 거래 기반 피처 계산 시 결측 처리가 필요.

## 5. fraud vs normal 분포 비교 (활동 있는 주소만)

| 항목 | fraud | normal |
|---|---|---|
| 거래 건수 (median) | 26 | 8 |
| 거래 건수 (mean) | 124.98 | 62.27 |
| 활동 기간 (median, 일) | 400.37 | 419.28 |
| 활동 기간 (mean, 일) | 351.42 | 529.84 |

거래 건수는 XBlock과 같은 방향(fraud가 더 활동적)이지만, 활동 기간은 median 기준 거의 비슷함(fraud 400일 vs normal 419일) — XBlock에서 normal의 활동 기간 median이 0이었던 것과 대조적. 이 데이터셋의 normal이 오래 운영된 CEX/프로토콜 주소라 활동 기간 자체는 fraud와 큰 차이가 안 남. **XBlock 검증 결과(활동 기간이 fraud를 가르는 축)를 이 데이터셋에 그대로 일반화하면 안 된다**는 걸 보여주는 사례.

## 6. 500건 캡 도달 및 데이터 잘림

`fetch_eth_labels_transactions.py`의 `MAX_TXS_PER_ADDRESS=500` 캡에 걸린 주소: 4개(fraud 3, normal 1) — XBlock(49개)보다 훨씬 적음. 이 데이터셋 규모(746개)에서는 캡으로 인한 정보 손실이 크지 않음.

## 7. 타임스탬프 범위 — "최신 데이터"라는 전제 재확인

| | 값 |
|---|---|
| 최소 | 2017-06-11 |
| 최대 | 2026-07-25 |
| 중앙값 | 2025-02-23 |

최소값이 2017년까지 내려가는 건 버그가 아니라, normal 라벨 중 오래 전부터 운영된 DeFi 프로토콜/CEX 주소(예: aave, sushiswap 등)의 과거 거래까지 전부 딸려온 것. 중앙값(2025-02-23)은 애초에 의도한 "최신 데이터" 범위와 일치함 — **중앙값 기준으로는 신선도가 확인되지만, 이 데이터셋 전체가 2024~2025년으로만 좁혀진 건 아니라는 점**은 sanction/mixer 노출 피처를 재검증할 때 감안해야 함(비교적 오래된 정상 활동도 섞여 있음).

## 결론 — 다음 단계(피처 재검증)에 대한 시사점

- fraud 표본이 사건 2개(filament, bybit)에 쏠려있어 신호 해석에 주의 필요
- 활동량(거래 건수) 차이는 XBlock과 같은 방향으로 재확인됨 — 이 데이터셋에서도 `amount_deviation_score`/`frequency_deviation_score` 재검증 가치가 있음
- 활동 기간은 XBlock과 다른 양상 — 데이터셋 간 일반화에 주의
- 시기가 중앙값 기준 2025년 초로, sanction_hop_distance/mixer_hop_distance/privacy_protocol_involved 재검증(다음 단계)에 적합한 시간대 확보됨

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/eda_eth_labels_2026.py
```

(`data/dataset/eth_labels_2026_transactions.json`이 먼저 있어야 함 — `DATA_ETH_LABELS_2026.md`의 재현 명령어로 생성)
