// src/apis/dashboard/getMonitoring.ts
import axios from "axios";

export type MonitoringItem = {
  chain: string;
  txHash: string;
  timestamp: string;
  value: string;
};

export type MonitoringResponse = {
  RecentHighValueTransfers: MonitoringItem[];
  cache_age_seconds?: number; // 프론트는 무시해도 됨
};

export async function getMonitoring() {
  try {
    const backendUrl =
      import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8888";
    const res = await axios.get<MonitoringResponse>(
      `${backendUrl}/api/dashboard/monitoring`,
      { timeout: 5000 }
    );

    return res.data;
  } catch (err) {
    console.error("❌ getMonitoring API Error:", err);
    throw err;
  }
}
