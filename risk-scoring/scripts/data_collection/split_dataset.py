"""
XBlock 데이터셋을 주소 단위로 train/val/test 분할

GOG 시절 split_dataset.py(legacy/scripts/)는 거래 단위로 분할해서
같은 주소의 거래가 train/test에 동시에 섞이는 누수 위험이 있었음.
이 스크립트는 반드시 "주소" 단위로만 나눠서 같은 주소가 두 split에
걸치지 않도록 한다 (ground_truth_label 기준 stratified, seed 고정).

실행:
    python3 scripts/split_dataset.py
"""
import json
import random
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
SEED = 42
RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


def stratified_split(addresses_by_label: dict, ratios: dict, seed: int) -> dict:
    rng = random.Random(seed)
    split = {"train": [], "val": [], "test": []}
    for label, addrs in addresses_by_label.items():
        addrs = list(addrs)
        rng.shuffle(addrs)
        n = len(addrs)
        n_train = int(n * ratios["train"])
        n_val = int(n * ratios["val"])
        split["train"].extend(addrs[:n_train])
        split["val"].extend(addrs[n_train:n_train + n_val])
        split["test"].extend(addrs[n_train + n_val:])
    return split


def main():
    extracted = json.load(open(project_root / "data/dataset/xblock_extracted.json"))
    tx_data = json.load(open(project_root / "data/dataset/xblock_transactions.json"))

    label_by_addr = {r["address"]: r["ground_truth_label"] for r in extracted}
    addresses_by_label = {"fraud": [], "normal": []}
    for addr, label in label_by_addr.items():
        addresses_by_label[label].append(addr)

    split = stratified_split(addresses_by_label, RATIOS, SEED)

    # 겹치는 주소가 없는지 검증 (핵심 — GOG 누수 재발 방지)
    train_set, val_set, test_set = set(split["train"]), set(split["val"]), set(split["test"])
    assert not (train_set & val_set), "train/val overlap!"
    assert not (train_set & test_set), "train/test overlap!"
    assert not (val_set & test_set), "val/test overlap!"
    assert len(train_set) + len(val_set) + len(test_set) == len(label_by_addr), "주소 개수 불일치!"
    print("✅ 주소 단위 분할 검증 통과 — train/val/test 교집합 없음")

    extracted_by_addr = {r["address"]: r for r in extracted}
    tx_by_addr = {r["address"]: r for r in tx_data}

    for split_name, addrs in split.items():
        extracted_subset = [extracted_by_addr[a] for a in addrs]
        tx_subset = [tx_by_addr[a] for a in addrs]

        out_extracted = project_root / f"data/dataset/xblock_split_{split_name}_extracted.json"
        out_tx = project_root / f"data/dataset/xblock_split_{split_name}_transactions.json"
        json.dump(extracted_subset, open(out_extracted, "w"))
        json.dump(tx_subset, open(out_tx, "w"))

        # 경량 매니페스트(주소+라벨만) — 재현성 확보용으로 커밋 대상
        manifest_path = project_root / f"data/dataset/split_manifest_{split_name}.txt"
        with open(manifest_path, "w") as f:
            for a in sorted(addrs):
                f.write(f"{a},{label_by_addr[a]}\n")

        fraud_n = sum(1 for a in addrs if label_by_addr[a] == "fraud")
        normal_n = len(addrs) - fraud_n
        print(f"{split_name:<6} 총 {len(addrs):>5}개  (fraud {fraud_n:>4} / normal {normal_n:>5})  "
              f"fraud 비율 {fraud_n/len(addrs)*100:.1f}%")


if __name__ == "__main__":
    main()
