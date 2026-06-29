import { api as axiosInstance } from "./axiosInstance";

export interface SuspiciousReport {
  id?: number;
  title: string;
  address: string;
  chain_id: number;
  risk_score: number;
  risk_level: string;
  description: string;
  analysis_data?: any;
  transaction_hashes?: string[];
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CreateReportRequest {
  title: string;
  address: string;
  chain_id: number;
  risk_score: number;
  risk_level: string;
  description: string;
  analysis_data?: any;
  transaction_hashes?: string[];
}

/**
 * 의심거래 보고서 작성
 */
export async function createSuspiciousReport(
  data: CreateReportRequest
): Promise<SuspiciousReport> {
  const response = await axiosInstance.post("/api/reports/suspicious", data);
  return response.data.data;
}

/**
 * 의심거래 보고서 목록 조회
 */
export async function getSuspiciousReports(params?: {
  status?: string;
  chain_id?: number;
  limit?: number;
}): Promise<SuspiciousReport[]> {
  const response = await axiosInstance.get("/api/reports/suspicious", {
    params,
  });
  return response.data.data;
}

/**
 * 특정 보고서 상세 조회
 */
export async function getSuspiciousReportDetail(
  reportId: number
): Promise<SuspiciousReport> {
  const response = await axiosInstance.get(
    `/api/reports/suspicious/${reportId}`
  );
  return response.data.data;
}

/**
 * 보고서 상태 업데이트
 */
export async function updateReportStatus(
  reportId: number,
  status: "pending" | "reviewed" | "resolved"
): Promise<SuspiciousReport> {
  const response = await axiosInstance.put(
    `/api/reports/suspicious/${reportId}/status`,
    { status }
  );
  return response.data.data;
}
