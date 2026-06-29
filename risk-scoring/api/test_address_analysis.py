"""
주소 분석 API 테스트

시연용 테스트 데이터로 주소 분석 API 테스트
"""
import json
from core.scoring.address_analyzer import AddressAnalyzer


def test_address_analysis():
    """주소 분석 테스트"""
    
    # 시연용 테스트 데이터
    test_address = "0xabc1234567890abcdef1234567890abcdef12345"
    test_chain = "ethereum"
    
    test_transactions = [
        {
            "tx_hash": "0xtx1",
            "timestamp": "2024-01-01T10:00:00Z",
            "block_height": 1000,
            "from": "0xmixer123",
            "to": test_address,
            "amount_usd": 5000.0,
            "label": "mixer",
            "is_sanctioned": False,
            "is_known_scam": False,
            "is_mixer": True,
            "is_bridge": False,
            "asset_contract": "0xETH"
        },
        {
            "tx_hash": "0xtx2",
            "timestamp": "2024-01-01T10:30:00Z",
            "block_height": 1001,
            "from": "0xsanctioned",
            "to": test_address,
            "amount_usd": 3000.0,
            "label": "unknown",
            "is_sanctioned": True,
            "is_known_scam": False,
            "is_mixer": False,
            "is_bridge": False,
            "asset_contract": "0xETH"
        },
        {
            "tx_hash": "0xtx3",
            "timestamp": "2024-01-01T11:00:00Z",
            "block_height": 1002,
            "from": "0xnormal",
            "to": test_address,
            "amount_usd": 4000.0,
            "label": "unknown",
            "is_sanctioned": False,
            "is_known_scam": False,
            "is_mixer": False,
            "is_bridge": False,
            "asset_contract": "0xETH"
        }
    ]
    
    # 주소 분석 수행
    analyzer = AddressAnalyzer()
    result = analyzer.analyze_address(
        address=test_address,
        chain=test_chain,
        transactions=test_transactions
    )
    
    # 결과 출력
    print("=" * 70)
    print("주소 분석 결과")
    print("=" * 70)
    print()
    print(f"주소: {result.address}")
    print(f"체인: {result.chain}")
    print(f"리스크 스코어: {result.risk_score}")
    print(f"리스크 레벨: {result.risk_level}")
    print()
    print("발동된 룰:")
    for rule in result.fired_rules:
        print(f"  - {rule['rule_id']}: {rule['name']} (점수: {rule['score']}, 발동: {rule['count']}회)")
    print()
    print("리스크 태그:")
    for tag in result.risk_tags:
        print(f"  - {tag}")
    print()
    print("거래 패턴:")
    for key, value in result.transaction_patterns.items():
        print(f"  - {key}: {value}")
    print()
    print("분석 요약:")
    print(f"  - 총 거래 수: {result.analysis_summary['total_transactions']}")
    print(f"  - 총 거래액: ${result.analysis_summary['total_volume_usd']:,.2f}")
    print()
    
    # JSON 출력
    result_dict = {
        "address": result.address,
        "chain": result.chain,
        "risk_score": result.risk_score,
        "risk_level": result.risk_level,
        "fired_rules": result.fired_rules,
        "risk_tags": result.risk_tags,
        "transaction_patterns": result.transaction_patterns,
        "analysis_summary": result.analysis_summary
    }
    
    print("JSON 결과:")
    print(json.dumps(result_dict, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_address_analysis()

