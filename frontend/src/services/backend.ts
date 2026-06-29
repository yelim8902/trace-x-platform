// 백엔드 API 서비스
import type { AddressAnalysisResponse } from "@/types/api";

const BACKEND_API_URL =
  import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8888";

const RISK_SCORING_API_URL =
  import.meta.env.VITE_RISK_SCORING_API_URL || "http://localhost:5001";

function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 30000
): Promise<Response> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() =>
    clearTimeout(id)
  );
}

export interface BackendRiskScoringRequest {
  address: string;
  chain_id: number;
  max_hops?: number; // optional, default: 3
  max_addresses_per_direction?: number; // optional, default: 10
  analysis_type?: "basic" | "advanced"; // optional, default: "basic"
}

/**
 * 백엔드를 통한 리스크 스코어링
 *
 * 백엔드가 Etherscan으로 거래 데이터를 수집하고,
 * 리스크 스코어링 API에 전달하여 결과를 반환합니다.
 *
 * @param request - 분석 요청 데이터
 * @returns 리스크 스코어링 결과
 */
export async function analyzeAddressViaBackend(
  request: BackendRiskScoringRequest
): Promise<AddressAnalysisResponse> {
  // 백엔드 API를 통해 리스크 스코어링 (백엔드가 리스크 스코어링 API를 프록시)
  const response = await fetchWithTimeout(`${BACKEND_API_URL}/api/analysis/risk-scoring`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Unknown error" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const result = await response.json();
  return result.data; // 백엔드는 { data: {...} } 형식으로 반환
}

/**
 * 백엔드를 통한 심층 분석 - 편의 함수
 *
 * analyzeAddressViaBackend(request, {analysis_type: "advanced"})와 동일
 */
export async function analyzeAddressAdvancedViaBackend(
  address: string,
  chain_id: number,
  max_hops: number = 3
): Promise<AddressAnalysisResponse> {
  return analyzeAddressViaBackend({
    address,
    chain_id,
    max_hops,
    analysis_type: "advanced",
  });
}

/**
 * 헬스 체크
 */
export async function backendHealthCheck(): Promise<{
  status: string;
  message: string;
}> {
  const response = await fetchWithTimeout(`${BACKEND_API_URL}/health`, {}, 5000);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  return response.json();
}

/**
 * 주소의 펀드 플로우 가져오기 (그래프 데이터)
 */
export async function getFundFlow(
  address: string,
  chain_id: number,
  max_hops: number = 2,
  max_addresses: number = 5
): Promise<any> {
  const response = await fetchWithTimeout(
    `${BACKEND_API_URL}/api/analysis/fund-flow?address=${address}&chain_id=${chain_id}&max_hops=${max_hops}&max_addresses=${max_addresses}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Unknown error" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Multi-hop 그래프 데이터 가져오기 (리스크 스코어링 없이)
 */
export async function getMultihopGraphData(
  address: string,
  chain_id: number,
  max_hops: number = 3
): Promise<any> {
  const response = await fetchWithTimeout(`${BACKEND_API_URL}/api/analysis/scoring`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      address,
      chain_id,
      max_hops,
    }),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Unknown error" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * 트랜잭션 해시로 펀드 플로우 가져오기 (그래프 데이터)
 */
export async function getFundFlowByTxHash(
  tx_hash: string,
  chain_id: number,
  max_hops: number = 1,
  max_addresses: number = 5
): Promise<any> {
  const response = await fetchWithTimeout(
    `${BACKEND_API_URL}/api/analysis/transaction-flow?tx_hash=${tx_hash}&chain_id=${chain_id}&max_hops=${max_hops}&max_addresses_per_direction=${max_addresses}`,
    { method: "GET" }
  );

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Unknown error" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const result = await response.json();
  return result.data;
}
