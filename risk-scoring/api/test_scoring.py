"""
트랜잭션 스코어링 API 테스트 예시
"""
from score_transaction import score_transaction_api

# 테스트 케이스 1: Mixer + Sanctioned + High Amount
test_case_1 = {
    "tx_hash": "0x1234567890abcdef",
    "chain": "ethereum",
    "timestamp": "2025-11-17T12:34:56Z",
    "block_height": 21039493,
    "target_address": "0xabc123",
    "counterparty_address": "0xdef456",
    "label": "mixer",
    "is_sanctioned": True,
    "is_known_scam": False,
    "is_mixer": True,
    "is_bridge": False,
    "amount_usd": 1234.56,
    "asset_contract": "0x..."
}

# 테스트 케이스 2: 일반 거래
test_case_2 = {
    "tx_hash": "0xabcdef1234567890",
    "chain": "ethereum",
    "timestamp": "2025-11-17T12:34:56Z",
    "block_height": 21039494,
    "target_address": "0xabc123",
    "counterparty_address": "0xdef456",
    "label": "unknown",
    "is_sanctioned": False,
    "is_known_scam": False,
    "is_mixer": False,
    "is_bridge": False,
    "amount_usd": 50.0,
    "asset_contract": "0x..."
}

if __name__ == "__main__":
    print("=" * 70)
    print("테스트 케이스 1: Mixer + Sanctioned + High Amount")
    print("=" * 70)
    result1 = score_transaction_api(test_case_1)
    import json
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 70)
    print("테스트 케이스 2: 일반 거래")
    print("=" * 70)
    result2 = score_transaction_api(test_case_2)
    print(json.dumps(result2, indent=2, ensure_ascii=False))

