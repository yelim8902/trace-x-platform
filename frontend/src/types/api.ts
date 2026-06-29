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
