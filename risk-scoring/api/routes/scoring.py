"""
스코어링 API 라우트
"""
from flask import Blueprint, request, jsonify
from core.scoring.engine import TransactionScorer, TransactionInput, ScoringResult

scoring_bp = Blueprint("scoring", __name__)


def _convert_chain_id_to_chain(chain_id: int) -> str:
    """체인 ID(숫자)를 체인 이름으로 변환"""
    chain_id_map = {
        1: "ethereum",                    # Ethereum Mainnet
        11155111: "ethereum",            # Sepolia Testnet
        17000: "ethereum",               # Holesky Testnet
        42161: "arbitrum",              # Arbitrum One Mainnet
        42170: "arbitrum",              # Arbitrum Nova Mainnet
        421614: "arbitrum",             # Arbitrum Sepolia Testnet
        43114: "avalanche",             # Avalanche C-Chain
        43113: "avalanche",             # Avalanche Fuji Testnet
        8453: "base",                   # Base Mainnet
        84532: "base",                  # Base Sepolia Testnet
        137: "polygon",                 # Polygon Mainnet
        80001: "polygon",               # Polygon Mumbai Testnet
        56: "bsc",                      # BSC Mainnet
        97: "bsc",                      # BSC Testnet
        250: "fantom",                  # Fantom Opera
        10: "optimism",                 # Optimism Mainnet
        420: "optimism",                # Optimism Goerli Testnet
        81457: "blast",                 # Blast Mainnet
    }
    return chain_id_map.get(chain_id, "ethereum")  # 기본값: ethereum


@scoring_bp.route("/transaction", methods=["POST"])
def score_transaction():
    """
    트랜잭션을 스코어링합니다
    단일 트랜잭션의 리스크 분석
    ---
    tags:
      - Transaction Scoring
    summary: 트랜잭션을 스코어링합니다
    description: 단일 트랜잭션의 리스크 분석
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - tx_hash
            - chain_id
            - timestamp
            - block_height
            - target_address
            - counterparty_address
            - label
            - is_sanctioned
            - is_known_scam
            - is_mixer
            - is_bridge
            - amount_usd
            - asset_contract
          properties:
            tx_hash:
              type: string
              example: "0x123..."
            chain_id:
              type: integer
              description: "체인 ID (예: 1=Ethereum, 42161=Arbitrum, 43114=Avalanche)"
              example: 1
            timestamp:
              type: string
              format: date-time
              description: UTC 타임스탬프
              example: "2025-11-17T12:34:56Z"
            block_height:
              type: integer
              description: 정렬용
              example: 21039493
            target_address:
              type: string
              description: 점수를 매기려는 기준 주소(스코어링 대상)
              example: "0xabc123..."
            counterparty_address:
              type: string
              description: 타겟주소와 거래한 상대방 주소
              example: "0xdef456..."
            label:
              type: string
              enum: [mixer, bridge, cex, dex, defi, unknown]
              description: 엔티티 라벨 (백엔드에서 라벨링)
              example: "mixer"
            is_sanctioned:
              type: boolean
              description: OFAC/제재 리스트 매핑 결과(팩트) 스코어링은 이걸 이용해 risk 계산
              example: true
            is_known_scam:
              type: boolean
              description: Scam/phishing 블랙리스트 매핑(팩트)
              example: false
            is_mixer:
              type: boolean
              description: label에서 파생되는 사실 정보
              example: true
            is_bridge:
              type: boolean
              description: label에서 파생되는 사실 정보
              example: false
            amount_usd:
              type: number
              description: 시세 기반 환산 금액(지금은 시세 기반 아님)
              example: 123.45
            asset_contract:
              type: string
              description: 자산 종류(Ethereum native, ERC-20 등) 구분 라벨링
              example: "0x..."
    responses:
      200:
        description: 스코어링 성공
        schema:
          type: object
          properties:
            target_address:
              type: string
              example: "0xabc123..."
            risk_score:
              type: integer
              description: 0~100 점수 (연속값)
              example: 78
            risk_level:
              type: string
              enum: [low, medium, high, critical]
              example: "high"
            risk_tags:
              type: array
              description: 이 거래가 왜 위험한지 한눈에 보이는 태그들
              items:
                type: string
              example: ["mixer_inflow", "sanction_exposure", "high_value_transfer"]
            fired_rules:
              type: array
              description: 어떤 룰이 얼마만큼 점수에 기여했는지
              items:
                type: object
                properties:
                  rule_id:
                    type: string
                    example: "E-101"
                  score:
                    type: integer
                    example: 25
              example:
                - rule_id: "E-101"
                  score: 25
                - rule_id: "C-001"
                  score: 30
            explanation:
              type: string
              example: "1-hop sanctioned mixer에서 1,000USD 이상 유입된 거래로, 세탁 자금 유입 패턴에 해당하여 high로 분류됨."
            completed_at:
              type: string
              format: date-time
              description: 스코어링 완료 시각 (ISO8601 UTC)
              example: "2025-11-17T12:34:56Z"
            timestamp:
              type: string
              format: date-time
              description: 트랜잭션 타임스탬프 (ISO8601 UTC)
              example: "2025-11-19T10:00:00Z"
            chain_id:
              type: string
              description: "체인 ID (예: ETH, BNB)"
              example: "ETH"
            value:
              type: number
              description: 거래 금액 (USD, amount_usd와 동일)
              example: 500000.00
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Missing required field: tx_hash"
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Scoring failed: ..."
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # 입력 데이터 검증 및 변환
        try:
            # chain_id를 chain으로 변환
            chain_id = data.get("chain_id")
            if chain_id is None:
                # 하위 호환성: chain 문자열도 지원
                chain_str = data.get("chain", "")
                if chain_str:
                    # 문자열을 숫자로 변환 시도
                    chain_id_map_str = {
                        "ethereum": 1,
                        "arbitrum": 42161,
                        "avalanche": 43114,
                        "base": 8453,
                        "polygon": 137,
                        "bsc": 56,
                        "fantom": 250,
                        "optimism": 10,
                        "blast": 81457
                    }
                    chain_id = chain_id_map_str.get(chain_str.lower())
            
            if chain_id is None:
                return jsonify({"error": "Missing required field: chain_id"}), 400
            
            # chain_id를 정수로 변환
            try:
                chain_id = int(chain_id)
            except (ValueError, TypeError):
                return jsonify({"error": "chain_id must be an integer"}), 400
            
            chain = _convert_chain_id_to_chain(chain_id)
            
            tx_input = TransactionInput(
                tx_hash=data["tx_hash"],
                chain=chain,
                timestamp=data["timestamp"],
                block_height=data["block_height"],
                target_address=data["target_address"],
                counterparty_address=data["counterparty_address"],
                label=data.get("label", data.get("entity_type", "unknown")),  # label로 변경, 하위 호환성 유지
                is_sanctioned=data["is_sanctioned"],
                is_known_scam=data["is_known_scam"],
                is_mixer=data["is_mixer"],
                is_bridge=data["is_bridge"],
                amount_usd=float(data["amount_usd"]),
                asset_contract=data["asset_contract"]
            )
        except KeyError as e:
            return jsonify({"error": f"Missing required field: {e}"}), 400
        
        # 스코어링 수행
        scorer = TransactionScorer()
        result = scorer.score_transaction(tx_input)
        
        # JSON 응답 생성 (입출력 포맷에 맞춤)
        return jsonify({
            "target_address": result.target_address,
            "risk_score": int(result.risk_score),  # 정수로 변환
            "risk_level": result.risk_level,
            "risk_tags": result.risk_tags,
            "fired_rules": [
                {"rule_id": rule.rule_id, "score": int(rule.score)}  # 정수로 변환
                for rule in result.fired_rules
            ],
            "explanation": result.explanation,
            "completed_at": result.completed_at,
            # 백엔드 요구 필드
            "timestamp": result.timestamp,
            "chain_id": result.chain_id,
            "value": float(result.value)
        }), 200
    
    except Exception as e:
        return jsonify({"error": f"Scoring failed: {str(e)}"}), 500

