# 데이터셋: XBlock Ethereum Phishing Transaction Network

## 출처

- **이름**: EPTransNet (Ethereum Phishing Transaction Network)
- **제공**: InPlusLab, Sun Yat-sen University (중산대학교) — 블록체인 데이터 공유 플랫폼 [XBlock](http://xblock.pro/)
- **다운로드**: Kaggle `xblock/ethereum-phishing-transaction-network` (392MB, 압축 해제 시 `MulDiGraph.pkl` 1.2GB)
- **인용**:
  ```bibtex
  @misc{xblockEthereum,
     author = {Chen, Liang and Peng, Jiaying and Liu, Yang and Li, Jintang and Xie, Fenfang and Zheng, Zibin},
     title = {XBLOCK Blockchain Datasets: InPlusLab Ethereum Phishing Detection Datasets},
     howpublished = {\url{http://xblock.pro/ethereum/}},
     year = 2019
  }
  ```

## 라벨 정의

- Etherscan의 `phish-hack` 공개 태그(https://etherscan.io/accounts/label/phish-hack)에서 신고된 주소를 2차 BFS로 확장해 수집한 트랜잭션 네트워크.
- 노드 속성 `isp`: 1 = 피싱 확정 주소, 0 = 그 외.
- **라벨은 지갑(주소) 단위**이며, GOG 데이터와 달리 "토큰/컨트랙트 카테고리"가 아니라 "이 주소가 Etherscan에 피싱으로 신고됐는가"를 직접 라벨링한 것 — TRACE-X가 실제로 풀려는 문제(지갑의 자금세탁/사기 위험)와 정의가 일치함.

## 규모 (원본 그래프, 이번 세션에서 로드 시 실측)

| 항목             | 값                                        |
| ---------------- | ----------------------------------------- |
| 노드 (주소)      | 2,973,489                                 |
| 엣지 (거래)      | 13,551,303                                |
| 라벨된 피싱 주소 | 1,165                                     |
| 평균 degree      | 4.56                                      |
| 그래프 로드 시간 | 약 30초 (M-series Mac, 8.7GB 메모리 피크) |

## 우리가 추출한 서브셋 (이번 세션에서 실행, `data/dataset/` 산출물)

`scripts/extract_features_from_pkl.py` + `scripts/extract_txs_for_rules.py`로 생성:

| 파일                       | 내용                                                                           | 실측 규모                                                            |
| -------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| `xblock_extracted.json`    | 주소별 집계 피처 + `ground_truth_label`                                        | 총 6,165개 (fraud 1,165 전체 + normal 5,000 샘플, seed=42)           |
| `xblock_transactions.json` | 주소별 개별 송/수신 거래 리스트 (`sent`/`received`, 각 `to`/`from`/`usd`/`ts`) | 동일 6,165개 주소, 주소당 최대 500건(`MAX_TXS_PER_ADDRESS`)으로 절단 |

- ETH→USD 환산은 `1500.0` 고정 근사치 사용 (수집 시점인 2017~2019년 평균가 근사). **정확한 달러 금액이 아니라 룰 간 상대적 신호 세기 비교 용도로만 신뢰할 것.**

## 알려진 한계

1. **시기**: 2016~2019년 수집 데이터. 최신 사기 수법(2024~2026년 기준)을 반영하지 못할 수 있음 — 이걸 보완하기 위해 BCCC-DeFiFraudTrans-2025(2017~2024년 데이터) 신청 진행 중 (`DATA_COLLECTION_LOG.md` 참고).
2. **정상 라벨의 성격**: `isp=0`(정상)은 "Etherscan이 피싱으로 신고하지 않음"을 의미할 뿐, "실제로 결백함이 검증됨"은 아님 — 라벨 노이즈 가능성 있음(신고 안 된 실제 위험 주소가 정상으로 섞여있을 수 있음).
3. **클래스 불균형**: 원본 전체 그래프 기준 피싱 비율은 1,165 / 2,973,489 ≈ 0.04%로 극단적으로 불균형. 우리는 정상 5,000개만 샘플링해 테스트 세트 기준 상대 비율(약 19% fraud)을 인위적으로 조정했음 — 이는 실제 운영 환경의 자연 발생 비율과 다르므로, precision/recall을 "실서비스에 그대로 적용될 정확도"로 해석하면 안 되고 "룰/모델의 상대적 판별력 비교"로만 봐야 함.

## 검증 절차 (이번 세션에서 실제로 수행/재현 확인)

1. `kaggle datasets download -d xblock/ethereum-phishing-transaction-network` → `data/xblock/`에 압축 해제
2. `python3 -c "import pickle; G = pickle.load(...)"` 로 그래프 로드 성공 확인 (노드/엣지 수 일치 확인)
3. `scripts/extract_features_from_pkl.py` 실행 → `xblock_extracted.json` 생성, fraud/normal 개수 로그로 확인
4. `scripts/extract_txs_for_rules.py` 실행 → `xblock_transactions.json` 생성
5. 실제 프로덕션 룰 엔진(`AddressAnalyzer`/`RuleEvaluator`)에 이 데이터를 통과시켜 룰 발동 여부·최종 risk_score 확인 — 이 과정에서 이중카운팅 버그(`window.py`)와 주소 오귀속 버그(`evaluator.py`)를 발견/수정함 (자세한 내용은 git log 커밋 `b6c4fc7` 참고)

## 재현 명령어

```bash
cd risk-scoring
kaggle datasets download -d xblock/ethereum-phishing-transaction-network -p data/xblock/
unzip data/xblock/ethereum-phishing-transaction-network.zip -d data/xblock/
python3 scripts/extract_features_from_pkl.py
python3 scripts/extract_txs_for_rules.py \
  --input "data/xblock/Ethereum Phishing Transaction Network/MulDiGraph.pkl" \
  --addresses data/dataset/xblock_extracted.json \
  --output data/dataset/xblock_transactions.json
```
