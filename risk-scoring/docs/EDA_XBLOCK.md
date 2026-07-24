# EDA: XBlock 데이터 품질 점검

`data/dataset/xblock_extracted.json`(6,165개, fraud 1,165 / normal 5,000)과 `xblock_transactions.json`을 대상으로 실행한 EDA 결과. 스크립트는 이 문서 하단 "재현 명령어" 참고.

## 1. 클래스 균형

| 클래스 | 개수 | 비율 |
|---|---|---|
| fraud | 1,165 | 18.9% |
| normal | 5,000 | 81.1% |

## 2. 정합성 체크 — 이상 없음

- 주소 중복: 0건
- fraud/normal 라벨 충돌(같은 주소가 양쪽에 존재): 0건
- `xblock_extracted.json` ↔ `xblock_transactions.json` 주소 집합 완전 일치 (양방향 누락 0건)

## 3. 데이터 품질 이슈 — 실제로 발견된 것

### 3-1. "정상" 라벨 주소의 43.7%가 거래 이력이 0건

`sent`+`received`가 모두 0건인 주소가 **2,194개**(fraud 11개, normal **2,183개** — 전체 normal의 43.7%). 즉 정상 샘플의 절반 가까이가 사실상 **활동 이력이 없는 빈 계정**이라, fan-in/out·pattern_score·시간 패턴 등 거래 기반 피처에서 아무 정보도 주지 못하고 전부 0으로 깔림.

**영향**: 지금 상태로 모델을 학습하면 "거래가 0건이면 무조건 normal"이라는 당연한 규칙만 과도하게 학습할 위험이 있음 — 진짜 어려운 케이스(활동은 있지만 미묘하게 정상인 주소 vs fraud)를 구분하는 능력은 검증되지 않음.

**권장 조치**: 4단계(데이터 분할) 전에 (a) 거래 0건 주소를 제외하고 "실제 활동이 있는 주소"만으로 재평가하거나, (b) 최소 거래 건수(예: 3건 이상) 필터를 두는 것을 검토. 이번 단계에서는 필터링하지 않고 이슈만 기록 — 5단계 피처 엔지니어링에서 실제로 어떤 피처가 이 영향을 받는지 보고 결정.

### 3-2. 금액 극단치

`total_sent_usd` 상위 5개:

| 금액(USD) | 주소 | 라벨 |
|---|---|---|
| 897,869,836.98 | 0x6f93...cf698 | fraud |
| 112,435,881.55 | 0x33ed...bd735a | fraud |
| 98,066,238.99 | 0x21f7...351aed | fraud |
| 75,354,150.00 | 0xce11...358c01 | **normal** |
| 63,361,500.00 | 0xdf91...94115b6 | fraud |

1위 주소(`0x6f93...cf698`)를 직접 열어보니 500건 캡에 걸릴 만큼 활동이 많고, $240,000 단위 송금이 반복됨(라운드 넘버 반복 패턴) — 데이터 추출 버그로 보이진 않지만, ETH→USD를 고정 $1,500로 환산한 근사치라 정확한 금액은 아님. normal 라벨인 4위 주소($75M)도 확인 필요 — 이 정도 규모면 거래소/브리지성 주소일 가능성이 있고, "정상"이라기보다는 "Etherscan이 아직 피싱 태그를 안 붙였을 뿐"일 수 있음 (`DATA_XBLOCK.md`에 이미 기록한 한계: 정상 라벨은 결백 증명이 아니라 미신고를 의미).

**권장 조치**: `avg_tx_usd`/`max_tx_usd`/`total_sent_usd`/`total_recv_usd`처럼 금액 기반 피처는 5~6단계에서 반드시 `log1p` 변환 후 사용 (원본 스케일 그대로 넣으면 이 몇 개 극단치가 모델을 왜곡함 — 예전 `stage2_scorer.py`도 이 값들에 `log1p`를 쓴 이유가 이것).

### 3-3. 500건 캡에 걸린 주소 49개

`extract_txs_for_rules.py`의 `MAX_TXS_PER_ADDRESS=500` 제한에 정확히 걸린 주소가 49개(fraud 40, normal 9) — 이 주소들은 실제 활동량이 더 많은데 앞쪽(시간순 정렬) 500건만 보고 있어서, `graph_edges`/`total_sent_usd` 등이 실제보다 과소측정됐을 수 있음. fraud 쪽에 압도적으로 몰려있는 것(40/49)도 자연스러움 — fraud 주소가 원래 더 활동적이라는 신호와 일치.

## 4. fraud vs normal 분포 비교 (median / mean / max)

| 피처 | fraud | normal | 방향성 |
|---|---|---|---|
| `fan_in_count` | median 7 | median 0 | fraud가 훨씬 높음 — 자금 집중 신호 |
| `fan_out_count` | median 1 | median 1 | 비슷함 (median 기준으론 구분 안 됨, mean은 fraud가 높음) |
| `graph_nodes` | median 11 | median 2 | fraud가 훨씬 높음 — 네트워크가 더 복잡 |
| `graph_edges` | median 15 | median 1 | fraud가 훨씬 높음 |
| `pattern_score` | median 35 | median 100 | **역방향** — fraud가 오히려 낮음 (예전 코드 주석 "Fraud는 pattern_score가 낮음"과 일치) |
| `n_omega` | median 0.25 | median 1.00 | fraud가 낮음 (송금 편향) |
| `실제 거래 건수` | median 15 | median 1 | fraud가 압도적으로 활동적 |
| `활동 기간(일)` | median 12.57 | median 0 | normal의 중위값이 0일 — 정상 주소 절반 이상이 거래가 하루 안에 끝나거나 1건뿐 (3-1과 연결됨) |

**결론**: fan-in/graph_nodes/pattern_score/n_omega 모두 방향성이 뚜렷하고 논리적으로 설명 가능한 차이를 보임 — 5단계에서 만들 신규 피처들도 이 정도의 명확한 분리력이 있는지가 채택 기준이 돼야 함.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/eda_xblock.py
```

(`data/dataset/xblock_extracted.json`, `xblock_transactions.json`이 먼저 있어야 함 — `DATA_XBLOCK.md`의 재현 명령어로 생성)
