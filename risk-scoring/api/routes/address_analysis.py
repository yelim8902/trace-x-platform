"""
주소 기반 분석 API 라우트

수동 탐지용: 주소의 거래 히스토리를 분석하여 리스크 스코어 계산
"""
from flask import Blueprint, request, jsonify
from core.scoring.address_analyzer import AddressAnalyzer, AddressAnalysisResult
from core.scoring.ml_scorer import MLScorer

address_analysis_bp = Blueprint("address_analysis", __name__)

# 이 룰이 발동하면 ML 점수와 무관하게 강제로 critical 처리(게이팅) —
# 전부 "직접 제재/믹서 노출"류 컴플라이언스 룰(axis C/E, severity HIGH).
# docs/FEATURE_ENGINEERING.md에서 sanction/mixer 노출 피처를 ML 학습
# 피처가 아니라 게이팅 룰로 다루기로 확정한 것과 같은 결정.
GATING_RULE_IDS = {"C-001", "E-101", "E-102"}

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _recommend_action(rule_level: str, ml_result: dict, gating: dict) -> str:
    """룰/ML 등급 조합에 따른 결정론적 권장 조치 — LLM 미사용, 고정 규칙표.
    이 프로젝트 전체가 '설명 가능한 결정론적 시스템'이라는 게 핵심이라,
    여기서 LLM으로 문장을 생성하면 그 자체로 다시 설명이 필요해지는 모순이 생김."""
    if gating.get("triggered"):
        rule_ids = ", ".join(gating["rule_ids"])
        return f"컴플라이언스 룰({rule_ids})이 발동되어 두 점수와 무관하게 즉시 최우선 검토가 필요합니다."

    ml_level = ml_result.get("ml_risk_level")
    if ml_level is None:
        return "ML 판단이 계산되지 않아 룰 판단만으로 검토가 필요합니다."

    r = _SEVERITY_RANK.get(rule_level, 0)
    m = _SEVERITY_RANK.get(ml_level, 0)

    if r <= 1 and m >= 2:
        return "룰 기준으로는 두드러지지 않지만 ML이 이례적 행동 패턴을 감지했으므로 추가 검토를 권장합니다."
    if r >= 2 and m <= 1:
        return "행동 패턴상 특이사항은 적으나 규정 위반 소지가 있어 컴플라이언스 관점에서 검토를 권장합니다."
    if r >= 2 and m >= 2:
        return "룰과 ML 모두 높은 위험을 시사하므로 우선 검토를 권장합니다."
    return "룰/ML 모두 낮은 위험으로 판단되어 특별한 조치가 필요하지 않습니다."


def _build_combined_explanation(result, ml_result: dict, gating: dict) -> str:
    """룰 판단 + ML 판단 + 종합 권장을 하나의 서술로 합침.
    룰 트랙과 ML 트랙의 결과를 각각 그대로 보여주고 마지막에만 합치는 것으로,
    두 점수 자체를 섞는(blending) 게 아님 — 게이팅+병렬 표시 아키텍처의 연장."""
    parts = []

    if result.fired_rules:
        top_rules = sorted(result.fired_rules, key=lambda r: r.get("score", 0), reverse=True)[:3]
        rule_desc = ", ".join(f"{r.get('name', r['rule_id'])}({r['rule_id']})" for r in top_rules)
        parts.append(f"[룰 판단] {rule_desc} 발동 — {result.risk_level} 등급({int(result.risk_score)}점).")
    else:
        parts.append(f"[룰 판단] 발동된 룰 없음 — {result.risk_level} 등급.")

    if ml_result.get("ml_score") is not None:
        top_features = ml_result.get("ml_top_features", [])
        if top_features:
            reasons = ", ".join(f.get("explanation", f["feature"]) for f in top_features[:2])
            parts.append(f"[ML 판단] {reasons} — {ml_result['ml_risk_level']} 등급({ml_result['ml_score']}점).")
        else:
            parts.append(f"[ML 판단] {ml_result['ml_risk_level']} 등급({ml_result['ml_score']}점), 거래 데이터 부족으로 세부 근거 없음.")
    else:
        parts.append("[ML 판단] 계산 실패 (룰 판단은 ML과 무관하게 유효함).")

    parts.append(f"[종합] {_recommend_action(result.risk_level, ml_result, gating)}")
    return " ".join(parts)


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


@address_analysis_bp.route("/address", methods=["POST"])
def analyze_address():
    """
    주소를 분석합니다
    주소의 거래 히스토리를 분석하여 리스크 스코어 계산
    ---
    tags:
      - Manual Analysis
    summary: 주소를 분석합니다
    description: 주소의 거래 히스토리를 분석하여 리스크 스코어 계산
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
            - address
            - chain_id
            - transactions
          properties:
            address:
              type: string
              description: 분석 대상 주소
              example: "0xabc123..."
            chain_id:
              type: integer
              description: "체인 ID (예: 1=Ethereum, 42161=Arbitrum, 43114=Avalanche)"
              example: 1
            transactions:
              type: array
              description: 거래 히스토리
              items:
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
                    description: "체인 ID (예: 1=Ethereum, 42161=Arbitrum)"
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
                    description: 스코어링 대상 주소
                    example: "0xabc123..."
                  counterparty_address:
                    type: string
                    description: 상대방 주소
                    example: "0xdef456..."
                  label:
                    type: string
                    enum: [mixer, bridge, cex, dex, defi, unknown]
                    description: 엔티티 라벨 (백엔드에서 라벨링, 이전 entity_type)
                    example: "mixer"
                  is_sanctioned:
                    type: boolean
                    description: OFAC/제재 리스트 매핑 결과
                    example: true
                  is_known_scam:
                    type: boolean
                    description: Scam/phishing 블랙리스트 매핑
                    example: false
                  is_mixer:
                    type: boolean
                    description: label에서 파생
                    example: true
                  is_bridge:
                    type: boolean
                    description: label에서 파생
                    example: false
                  amount_usd:
                    type: number
                    description: 시세 기반 환산 금액
                    example: 123.45
                  asset_contract:
                    type: string
                    description: 자산 종류
                    example: "0x..."
            time_range:
              type: object
              description: 선택 필드 - 시간 범위
              properties:
                start:
                  type: string
                  format: date-time
                  example: "2024-01-01T00:00:00Z"
                end:
                  type: string
                  format: date-time
                  example: "2024-12-31T23:59:59Z"
            analysis_type:
              type: string
              enum: [basic, advanced]
              description: "분석 타입 - basic: 기본 룰만 평가 (빠름, 1-2초), advanced: 모든 룰 평가 (느림, 5-30초, 그래프 구조 분석 포함)"
              example: "basic"
    responses:
      200:
        description: 분석 성공
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
              type: integer
              description: "체인 ID (예: 1=Ethereum, 42161=Arbitrum)"
              example: 1
            value:
              type: number
              description: 거래 금액 (USD, amount_usd와 동일)
              example: 500000.0
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Missing required field: address"
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Analysis failed: ..."
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # 필수 필드 검증
        # address 또는 target_address 모두 허용
        address = data.get("address") or data.get("target_address")
        chain_id = data.get("chain_id")
        transactions = data.get("transactions", [])
        
        if not address:
            return jsonify({"error": "Missing required field: address or target_address"}), 400
        if chain_id is None:
            # 하위 호환성: chain 문자열도 지원
            chain_str = data.get("chain", "")
            if chain_str:
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
        
        # chain_id를 chain으로 변환
        chain = _convert_chain_id_to_chain(chain_id)
        
        # transactions 배열 내부의 chain_id를 chain으로 변환
        processed_transactions = []
        for tx in transactions:
            tx_chain_id = tx.get("chain_id") or tx.get("chain")  # 하위 호환성
            if tx_chain_id is not None:
                # chain_id를 정수로 변환
                try:
                    if isinstance(tx_chain_id, str):
                        # 문자열인 경우 체인 이름으로 간주하고 chain_id로 변환
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
                        tx_chain_id = chain_id_map_str.get(tx_chain_id.lower())
                    else:
                        tx_chain_id = int(tx_chain_id)
                except (ValueError, TypeError):
                    tx_chain_id = None
                
                if tx_chain_id is not None:
                    tx["chain"] = _convert_chain_id_to_chain(tx_chain_id)
            processed_transactions.append(tx)
        
        # 선택 필드
        time_range = data.get("time_range")
        analysis_type = data.get("analysis_type", "basic")  # 기본값: "basic"
        
        # 주소 분석 수행
        analyzer = AddressAnalyzer()
        result = analyzer.analyze_address(
            address=address,
            chain=chain,
            transactions=processed_transactions,
            time_range=time_range,
            analysis_type=analysis_type
        )
        
        # chain을 chain_id(숫자)로 변환
        chain_to_id_map = {
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
        chain_id = chain_to_id_map.get(chain.lower(), 1)  # 기본값: Ethereum (1)
        
        # 최신 트랜잭션의 timestamp와 총 value 계산
        latest_timestamp = ""
        total_value = 0.0
        if transactions:
            # 시간순 정렬된 마지막 트랜잭션
            sorted_txs = sorted(
                transactions,
                key=lambda tx: tx.get("timestamp", ""),
                reverse=True
            )
            if sorted_txs:
                latest_tx = sorted_txs[0]
                latest_timestamp = latest_tx.get("timestamp", "")
                # 모든 트랜잭션의 총 value 계산
                total_value = sum(float(tx.get("amount_usd", 0)) for tx in transactions)
        
        # ML 트랙 (룰 트랙과 완전히 독립 — 10단계, 게이팅+병렬 표시 아키텍처)
        try:
            ml_result = MLScorer.get_instance().score(address, processed_transactions)
            ml_error = None
        except Exception as e:
            # ML 실패는 룰 기반 결과 반환을 막지 않음 — 컴플라이언스 룰은 ML 없이도 항상 동작해야 함
            ml_result = {"ml_score": None, "ml_risk_level": None, "ml_top_features": []}
            ml_error = str(e)

        # 게이팅: 컴플라이언스 룰이 발동하면 ML 점수와 무관하게 critical 강제
        fired_rule_ids = {r["rule_id"] for r in result.fired_rules}
        gating_hit = fired_rule_ids & GATING_RULE_IDS
        gating = {
            "triggered": bool(gating_hit),
            "rule_ids": sorted(gating_hit),
        }

        # 기존 JSON 포맷에 맞춰 응답 생성 (룰 필드는 그대로, ML/게이팅은 신규 추가 필드)
        response = {
            "target_address": result.address,  # 기존 포맷에 맞춤
            "risk_score": int(result.risk_score),  # 정수로 변환
            "risk_level": result.risk_level,
            "risk_tags": result.risk_tags,
            "fired_rules": result.fired_rules,  # {rule_id, score, name, axis, severity, description, legal_basis, count}
            "explanation": result.explanation,  # 룰 단독 설명 (하위 호환용, 그대로 유지)
            "completed_at": result.completed_at,
            # 백엔드 요구 필드
            "timestamp": latest_timestamp,
            "chain_id": chain_id,
            "value": float(total_value),
            # 10단계 신규 필드 — ML 트랙 (룰과 별도 병렬 표시, 하나의 숫자로 블렌딩하지 않음)
            "ml": ml_result,
            # 10단계 신규 필드 — 게이팅 (컴플라이언스 룰 발동 시 ML과 무관하게 강제 override 신호)
            "gating": gating,
            # 룰 판단 + ML 판단 + 종합 권장을 하나로 서술 (점수 자체는 안 섞음, 텍스트만 병기)
            "combined_explanation": _build_combined_explanation(result, ml_result, gating),
        }
        if ml_error:
            response["ml"]["error"] = ml_error
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

