# 도메인 조사 — 신규 피처 설계 근거

5단계(피처 엔지니어링) 전 단계. FATF 보고서(기존에 읽음) + Chainalysis 실제 보고서 + 관련 논문 조사. 지난번 손그림 설계도에서 나온 5개 후보를 이 조사로 검증/보강한다.

## 참고 자료

1. **FATF (2020)**, *Virtual Assets Red Flag Indicators of Money Laundering and Terrorist Financing* — 이미 룰북에서 인용 중 (`docs/DATA_XBLOCK.md`와 별개로 이미 읽음)
2. **Chainalysis (2026)**, *2026 Crypto Crime Report* — https://www.chainalysis.com/blog/2026-crypto-crime-report-introduction/
3. Elliptic / TRM Labs / Scorechain / Merkle Science 블로그 — 실무 스크리닝 도구들이 hop-distance 기반 노출 점수를 실제로 어떻게 계산하는지
4. **arXiv:2206.04803**, *Detecting Anomalous Cryptocurrency Transactions: an AML/CFT Application of Machine Learning-based Forensics* (2022)
5. **arXiv:2512.02534**, *Detection of Crowdsourcing Cryptocurrency Laundering via Multi-Task Collaboration* (2025)
6. Merkle Science / Crypto Trace Labs / AMLTRIX Framework — Peel Chain 기술 문서

## 발견 1 — 업계 표준: hop-distance 감쇠 점수 (기존 후보 `sanction_hop_distance`, `mixer_hop_distance` 뒷받침)

Elliptic/TRM Labs/Scorechain 등 실제 상용 스크리닝 도구들의 공통 패턴: **1-hop(직접 접촉)은 강한 신호, 2-hop 이상은 훨씬 약한 가중치**로 감쇠시켜 점수화함. 지금 룰북의 `E-102`(간접 제재 노출)는 PPR 기반 이진 판정(임계값 0.05 넘으면 발동)만 있고, "몇 hop인지"에 따라 점수를 grade하는 연속값 피처는 없음 — 손그림에서 제안한 `sanction_hop_distance`/`sanction_exposure_strength`가 실무 관행과 일치하는 방향임을 확인.

## 발견 2 — Peel Chain: 지금 룰북이 놓치고 있는 패턴 (신규, 6번째 후보)

Chainalysis 보고서와 Merkle Science/AMLTRIX 문서에 따르면, **비트코인 도난 사건의 약 70%**에서 나타나는 대표적 자금세탁 기법. 동작 방식:

```
큰 금액 입금 → [소액 peel + 잔액 forward] → 새 주소로 반복 (수백 개 주소까지)
```

**중요한 발견**: 이건 지금 룰북의 `B-201`(Layering Chain)이 잡는 패턴과 **반대**예요. B-201은 `hop_amount_delta_pct_lte: 5`(각 홉 금액이 ±5% 이내로 비슷해야 발동) 조건인데, peel chain은 정의상 **매 홉마다 금액이 계속 줄어듦**(소액을 떼어내고 나머지를 전달) — 그러니 지금 B-201은 peel chain을 아예 못 잡음.

**신규 후보 피처**: `peel_chain_depth` / `peel_chain_score` — 연속된 홉에서 금액이 단조 감소하는 체인의 길이, 각 홉에서 새 주소로 가는지 여부.

## 발견 3 — Privacy Coin / AEC 전환 (기존 후보 `privacy_coin_involved` 뒷받침)

FATF 문서에서 이미 확인한 내용과 일치: "공개 블록체인(비트코인 등)에서 거래소로 옮긴 뒤 즉시 AEC(익명성 강화 코인)나 privacy coin으로 전환"하는 패턴이 명시적 레드플래그. 논문 조사에서도 이 패턴이 별도로 더 다뤄지진 않음 — FATF 문서가 사실상 가장 구체적인 근거.

## 발견 4 — 개인 기준선 대비 이상치 (기존 후보 `amount_deviation_score`/`frequency_deviation_score` 뒷받침, 근거는 약함)

업계 일반론("baseline behavior 확립 후 이탈 탐지")은 여러 자료에서 확인되지만, 크립토 AML에 특화된 구체적 논문 근거는 못 찾음 (arXiv:2206.04803은 개인 기준선이 아니라 그래프 전체 구조 기반 GCN/GAT 접근이 핵심이었음 — 방향이 다름). 이 피처는 "일반적인 이상탐지 원칙"으로는 정당화되지만, "크립토 AML 논문이 이렇게 하라고 한다"는 근거는 약하다는 걸 인지하고 진행해야 함.

## 발견 5 — Crowdsourcing Laundering (참고만, 이번엔 구현 안 함)

2025년 최신 논문(arXiv:2512.02534)은 자금세탁이 소수의 중앙화된 hub가 아니라 **다수의 개별 참가자에게 분산**되는(폴리센트릭) 패턴을 GNN으로 그룹 단위로 탐지하는 접근. 우리 시스템은 지금 "주소 하나"를 스코어링하는 구조라 이런 **다중 주소 그룹 탐지**는 스코프 밖 — 언급만 해두고 이번 5단계엔 안 넣음. 나중에 시스템이 그래프 전체를 보는 구조로 커지면 고려.

## 갱신된 피처 후보 목록 (6개)

| # | 피처 | 근거 | 상태 |
|---|---|---|---|
| 1 | `sanction_hop_distance` | 업계 표준 hop-decay 관행 | 기존 |
| 2 | `mixer_hop_distance` | 업계 표준 hop-decay 관행 | 기존 |
| 3 | `privacy_coin_involved` | FATF Red Flag Indicators (Anonymity 섹션) | 기존 |
| 4 | `amount_deviation_score` | 일반 이상탐지 원칙 (크립토 특화 근거는 약함) | 기존 |
| 5 | `frequency_deviation_score` | 일반 이상탐지 원칙 (크립토 특화 근거는 약함) | 기존 |
| 6 | **`peel_chain_score`** | Chainalysis + Merkle Science + AMLTRIX — 비트코인 도난의 70%에서 나타나는 패턴, 지금 B-201이 놓치는 정반대 패턴 | **신규** |

## Sources

- [Chainalysis 2026 Crypto Crime Report Introduction](https://www.chainalysis.com/blog/2026-crypto-crime-report-introduction/)
- [Chainalysis: Crypto Sanctions 2026](https://www.chainalysis.com/blog/crypto-sanctions-2026/)
- [What Is a Peel Chain in Crypto Money Laundering? — Merkle Science](https://www.merklescience.com/blog/what-is-a-peel-chain-in-crypto-money-laundering)
- [What Are Peel Chains and How Do Investigators Track Them? — Crypto Trace Labs](https://cryptotracelabs.com/blog/what-are-peel-chains-and-how-do-investigators-track-them/)
- [AMLTRIX Framework — Peel Chain (T0070.002)](https://framework.amltrix.com/techniques/T0070.002-peel-chain)
- [arXiv:2206.04803 — Detecting Anomalous Cryptocurrency Transactions](https://arxiv.org/abs/2206.04803)
- [arXiv:2512.02534 — Detection of Crowdsourcing Cryptocurrency Laundering via Multi-Task Collaboration](https://arxiv.org/abs/2512.02534)
