# 데이터 수집 로그

리스크 스코어링 엔진 재설계(GOG → 재현 가능한 데이터 기반)의 데이터 수집 단계 진행 기록. 결정 사항과 이유를 시간순으로 남긴다.

## 결정 사항

- **GOG(Graph of Graphs) 논문 데이터셋 폐기.** 이유: (1) 팀 저장소에서 원본 삭제, git 히스토리도 스쿼시되어 있어 재현 불가, (2) 라벨이 "지갑의 자금세탁 위험"이 아니라 "토큰/컨트랙트의 피싱·스캠 카테고리"라서 TRACE-X가 실제로 푸는 문제와 라벨 정의 자체가 다름, (3) 주소 단위 라벨을 거래 단위로 그대로 복사한 데이터 구축 방식이라 train/test 분할 시 데이터 누수 가능성이 있음.
- **XBlock을 베이스라인으로 채택.** 이미 다운로드·추출·룰 엔진 검증까지 완료 (`DATA_XBLOCK.md` 참고). 지갑 단위 라벨(Etherscan phish-hack 태그 직접 사용)이라 문제 정의가 일치하고, Kaggle을 통해 언제든 재다운로드 가능해 재현성이 확보됨.
- **BCCC-DeFiFraudTrans-2025 데이터셋 신청 진행.** XBlock(2017~2019년)보다 최신 구간(2017~2024년)을 포함하고, Etherscan 태그 라벨을 이상탐지·일관성 검증·중복제거로 교차검증한 벤치마크라 신뢰도가 더 높을 것으로 기대. York University BCCC가 배포하며 직접 다운로드가 아닌 request form 제출 후 승인 방식.

## BCCC-DeFiFraudTrans-2025 신청 현황

| 항목 | 상태 |
|---|---|
| Request form 제출 | ⬜ 미제출 — 본인이 직접 https://www.yorku.ca/research/bccc/ucs-technical/cybersecurity-datasets-cds/defi-fraud-transactions-bccc-defifraudtrans-2025/ 에서 제출 필요 (학술 소속 정보 등이 필요할 수 있어 대리 제출 불가) |
| 승인 여부 | ⬜ 대기 중 |
| 데이터 수령 후 스키마 비교 | ⬜ 미착수 |

*(제출/승인 시 이 표를 직접 업데이트해주세요 — 날짜와 함께 기록)*

## 보류/추후 결정 사항

- **정상 주소 샘플 크기**: 현재 XBlock에서 정상 5,000개만 샘플링됨. 피처 엔지니어링 단계에서 실제 피처 분포를 보고 늘릴지 결정 예정 (이번 단계에서는 미결정).
- **XBlock ↔ BCCC 병합 여부**: BCCC 데이터 도착 후 라벨 정의·피처 단위 스키마를 비교해서 (a) 두 데이터셋을 합쳐 하나의 학습셋으로 쓸지, (b) XBlock=학습, BCCC=독립 검증셋으로 분리해서 쓸지 결정 (독립 검증셋 분리 쪽이 과적합 여부를 더 엄격하게 볼 수 있어 유력한 후보).

## 별개로 발견된 이슈 (데이터 수집과 무관하지만 이 조사 중 발견)

- **Etherscan API 키(`91FZVKNIX7GYPESECU5PHPZIMKD72REX43`)가 공개 GitHub 저장소(`aml-risk-engine2`)에 하드코딩되어 노출됨** — `core/scoring/real_dataset_builder.py`, `core/data/etherscan_client.py`, `scripts/collect_real_data*.py`, `api/routes/demo_analysis.py`, `demo/index.html` 등 다수 위치. **Etherscan 콘솔에서 폐기(revoke) 후 재발급 필요.**
