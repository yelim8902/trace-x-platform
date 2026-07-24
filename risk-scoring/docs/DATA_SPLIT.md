# 데이터 분할 (Train / Val / Test)

## 왜 주소 단위로 나눴는가

GOG 데이터셋의 핵심 결함 중 하나가 "주소 단위 라벨을 거래 단위로 복사해서 데이터셋을 만들고, 그 거래들을 랜덤하게 train/test에 나눠 담은 것"이었음 — 같은 주소의 거래가 양쪽에 섞이면, 그 주소의 그래프 통계(fan_in_count 등은 주소 단위로 계산되는 값이라 같은 주소의 모든 행이 똑같은 피처값을 가짐)가 그대로 test로 새어 들어가 평가 점수가 부풀려짐. Stage2 ML 제거 시 정확도가 38.70%로 폭락한 ablation 결과가 이 누수와 무관하지 않을 것으로 추정됨 (`docs/DATA_COLLECTION_LOG.md` 참고).

이번엔 이 문제를 원천 차단하기 위해 **주소 단위로만** 분할하고, 분할 직후 세 집합 간 교집합이 정말 0인지 스크립트로 직접 검증했다.

## 방법

- `ground_truth_label`(fraud/normal) 기준 **stratified**: 각 라벨 내에서 랜덤 셔플 후 70/15/15로 자름
- `seed=42` 고정 (재현 가능)
- `xblock_extracted.json`(주소별 집계 피처)과 `xblock_transactions.json`(주소별 개별 거래)을 **동일한 주소 파티션**으로 함께 분할 — 두 파일이 서로 다른 기준으로 나뉘면 나중에 join할 때 다시 섞일 위험이 있어서

## 결과 (2026-07-07 실행)

| split | 전체 | fraud | normal | fraud 비율 |
|---|---|---|---|---|
| train | 4,315 | 815 | 3,500 | 18.9% |
| val | 924 | 174 | 750 | 18.8% |
| test | 926 | 176 | 750 | 19.0% |

전체 비율(18.9%)이 세 split 모두에 잘 유지됨.

## 검증 (실제로 실행해서 확인)

1. 스크립트 내부 `assert`로 분할 직후 3중 교집합 0 확인
2. **디스크에 저장된 매니페스트 파일을 다시 읽어서 독립적으로 재검증** — `split_manifest_{train,val,test}.txt`에서 주소만 뽑아 집합 연산으로 교집합 확인 → `train∩val: 0, train∩test: 0, val∩test: 0`, 합집합 6,165개(원본과 일치)

## 파일

- `data/dataset/xblock_split_{train,val,test}_extracted.json` — 전체 데이터(용량 커서 `.gitignore`에 의해 미커밋, 재현 명령어로 재생성)
- `data/dataset/xblock_split_{train,val,test}_transactions.json` — 동일
- `data/dataset/split_manifest_{train,val,test}.txt` — **주소+라벨만 담은 경량 매니페스트, 커밋 대상** (어떤 주소가 어느 split에 들어갔는지 그 자체를 재현성 근거로 남기기 위함)

## ⚠️ 규칙

**test set(926개)은 8~9단계(최종 평가, SHAP 해석)가 끝나기 전까지 절대 열어보지 않는다.** 5~7단계(피처 엔지니어링, 모델 학습/튜닝)는 train/val만 사용.

## 재현 명령어

```bash
cd risk-scoring
python3 scripts/split_dataset.py
```
