// API 요청/응답 타입 정의

export interface Transaction {
  tx_hash: string;
  chain: string;
  timestamp: string; // ISO 8601 format
  block_height: number;
  target_address: string;
  counterparty_address: string;
  entity_type: "mixer" | "bridge" | "cex" | "dex" | "defi" | "unknown";
  is_sanctioned: boolean;
  is_known_scam: boolean;
  is_mixer: boolean;
  is_bridge: boolean;
  amount_usd: number;
  asset_contract: string;
}

export interface FiredRule {
  rule_id: string;
  score: number;
}

// ML 트랙 (룰 트랙과 별도 병렬 표시 — 하나의 숫자로 블렌딩하지 않음, docs/GATING_INTEGRATION.md)
export interface MLTopFeature {
  feature: string;
  value: number | null;
  shap_value: number;
  direction: "increases_risk" | "decreases_risk";
  explanation: string;
}

export interface MLScoreResult {
  ml_score: number | null;
  ml_risk_level: "low" | "medium" | "high" | "critical" | null;
  ml_top_features: MLTopFeature[];
  error?: string;
}

// 컴플라이언스 룰(제재/믹서 직접 노출) 발동 시 룰/ML 점수와 무관하게 최우선 처리 신호
export interface GatingResult {
  triggered: boolean;
  rule_ids: string[];
}

export interface AddressAnalysisRequest {
  address?: string;
  target_address?: string;
  chain: string;
  transactions: Transaction[];
  time_range?: {
    start: string;
    end: string;
  };
  analysis_type?: "basic" | "advanced";
}

export interface AddressAnalysisResponse {
  target_address: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_tags: string[];
  fired_rules: FiredRule[];
  explanation: string;
  analysis_type?: "basic" | "advanced";
  ml?: MLScoreResult;
  gating?: GatingResult;
}

export interface TransactionScoringRequest {
  tx_hash: string;
  chain: string;
  timestamp: string;
  block_height: number;
  target_address: string;
  counterparty_address: string;
  entity_type: "mixer" | "bridge" | "cex" | "dex" | "defi" | "unknown";
  is_sanctioned: boolean;
  is_known_scam: boolean;
  is_mixer: boolean;
  is_bridge: boolean;
  amount_usd: number;
  asset_contract: string;
}

export interface TransactionScoringResponse {
  target_address: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_tags: string[];
  fired_rules: FiredRule[];
  explanation: string;
}

// 그래프 데이터 타입 (우리가 추가)
export interface GraphNodeData {
  address: string;
  label: string;
  chain: string;
  type: string;
  isWarning: boolean;
  isTarget: boolean;
}

export interface GraphEdgeData {
  source: string;
  target: string;
  type: string;
  asset: string;
  amount: string;
  timestamp?: string;
}

export interface GraphData {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
}
