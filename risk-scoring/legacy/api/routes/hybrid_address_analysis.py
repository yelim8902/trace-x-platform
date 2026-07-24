"""
하이브리드 주소 분석 API 라우트

Rule-based + MPOCryptoML 통합 분석
"""

from flask import Blueprint, request, jsonify
from core.scoring.hybrid_address_analyzer import HybridAddressAnalyzer

hybrid_address_analysis_bp = Blueprint("hybrid_address_analysis", __name__)


@hybrid_address_analysis_bp.route("/address/hybrid", methods=["POST"])
def analyze_address_hybrid():
    """
    하이브리드 방식으로 주소를 분석합니다
    Rule-based (70%) + MPOCryptoML (30%) 통합 스코어링
    
    ---
    tags:
      - Hybrid Analysis
    summary: 하이브리드 방식으로 주소를 분석합니다
    description: |
      Rule-based 스코어링과 MPOCryptoML 방법론을 결합하여 
      더 정확한 리스크 스코어를 계산합니다.
      
      - Rule-based: TRACE-X 룰 기반 점수 (70%)
      - MPOCryptoML: 그래프 패턴 분석 점수 (30%)
      
      **3-hop 데이터가 제공되면 MPOCryptoML 분석이 활성화됩니다.**
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
            - chain
            - transactions
          properties:
            address:
              type: string
              description: 분석 대상 주소
              example: "0xabc123..."
            chain:
              type: string
              description: 체인 이름
              example: "ethereum"
            transactions:
              type: array
              description: 주소의 직접 거래 히스토리
              items:
                type: object
            transactions_3hop:
              type: array
              description: 3-hop까지의 거래 데이터 (MPOCryptoML용, 선택사항)
              items:
                type: object
            analysis_type:
              type: string
              enum: [basic, rule_only, hybrid]
              description: |
                분석 타입
                - basic: Rule-based만 사용 (빠름)
                - rule_only: Rule-based만 사용
                - hybrid: Rule-based + MPOCryptoML (기본값)
              example: "hybrid"
    responses:
      200:
        description: 분석 성공
        schema:
          type: object
          properties:
            target_address:
              type: string
            risk_score:
              type: number
              description: 최종 리스크 점수 (0~100)
            risk_level:
              type: string
              enum: [low, medium, high, critical]
            rule_score:
              type: number
              description: Rule-based 점수
            ml_score:
              type: number
              description: MPOCryptoML 점수
            ml_details:
              type: object
              description: MPOCryptoML 상세 정보
            risk_tags:
              type: array
            fired_rules:
              type: array
            explanation:
              type: string
            completed_at:
              type: string
      400:
        description: 잘못된 요청
      500:
        description: 서버 오류
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        address = data.get("address") or data.get("target_address")
        if not address:
            return jsonify({"error": "Missing required field: address"}), 400
        
        chain = data.get("chain", "ethereum")
        transactions = data.get("transactions", [])
        transactions_3hop = data.get("transactions_3hop", None)
        analysis_type = data.get("analysis_type", "hybrid")
        
        if not transactions:
            return jsonify({
                "error": "Missing required field: transactions",
                "target_address": address,
                "risk_score": 0,
                "risk_level": "low",
                "rule_score": 0,
                "ml_score": 0,
                "explanation": "No transactions provided"
            }), 200
        
        # 하이브리드 분석기 초기화
        analyzer = HybridAddressAnalyzer(use_ml=(analysis_type == "hybrid"))
        
        # 분석 수행
        result = analyzer.analyze_address(
            address=address,
            chain=chain,
            transactions=transactions,
            transactions_3hop=transactions_3hop,
            analysis_type=analysis_type
        )
        
        # 결과 반환
        return jsonify({
            "target_address": result.address,
            "chain": result.chain,
            "risk_score": round(result.risk_score, 2),
            "risk_level": result.risk_level,
            "rule_score": round(result.rule_score, 2),
            "ml_score": round(result.ml_score, 2),
            "ml_details": result.ml_details,
            "risk_tags": result.risk_tags,
            "fired_rules": [
                {
                    "rule_id": rule.get("rule_id", ""),
                    "score": rule.get("score", 0)
                }
                for rule in result.fired_rules
            ],
            "explanation": result.explanation,
            "completed_at": result.completed_at,
            "analysis_summary": result.analysis_summary
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            "error": f"Analysis failed: {str(e)}",
            "traceback": traceback.format_exc()
        }), 500

