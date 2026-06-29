/* ============================================
   📌 응답 타입 정의
============================================ */

import { api } from "./axiosInstance";

export type DashboardSummaryResponse = {
  data: {
    totalVolume: {
      value: number;
      changeRate: string;
    };
    totalTransactions: {
      value: number;
      changeRate: string;
    };
    highRiskTransactions: {
      value: number;
      changeRate: string;
    };
    warningTransactions: {
      value: number;
      changeRate: string;
    };

    highRiskTransactionTrend: {
      trend: Record<string, number>;
      value: number;
    };

    highRiskTransactionsByChain: Record<string, Record<string, number>>;

    averageRiskScore: Record<string, number>;
  };
};

/* ============================================
   📌 getDashboardSummary  
============================================ */

export const getDashboardSummary = async (chainId?: string) => {
  try {
    const res = await api.get<DashboardSummaryResponse>("/data/dashboard", {
      params: chainId ? { chain_id: chainId } : undefined,
    });

    if (!res.data?.data) {
      return {
        totalVolume: { value: 0, changeRate: "0" },
        totalTransactions: { value: 0, changeRate: "0" },
        highRiskTransactions: { value: 0, changeRate: "0" },
        warningTransactions: { value: 0, changeRate: "0" },
        highRiskTransactionTrend: {},
        highRiskTransactionsByChain: {},
        averageRiskScore: {},
      };
    }

    const data = res.data.data;

    console.log("[Dashboard API] fetched data:", data);

    return {
      totalVolume: data?.totalVolume ?? { value: 0, changeRate: "0" },
      totalTransactions: data?.totalTransactions ?? { value: 0, changeRate: "0" },
      highRiskTransactions:
        data?.highRiskTransactions ?? { value: 0, changeRate: "0" },
      warningTransactions:
        data?.warningTransactions ?? { value: 0, changeRate: "0" },

  
      highRiskTransactionTrend: data?.highRiskTransactionTrend?.trend ?? {},

      highRiskTransactionsByChain: data?.highRiskTransactionsByChain ?? {},
      averageRiskScore: data?.averageRiskScore ?? {},
    };
  } catch (error: any) {
    console.error("[Dashboard API Error]:", error);
    return {
      totalVolume: { value: 0, changeRate: "0" },
      totalTransactions: { value: 0, changeRate: "0" },
      highRiskTransactions: { value: 0, changeRate: "0" },
      warningTransactions: { value: 0, changeRate: "0" },
      highRiskTransactionTrend: {},
      highRiskTransactionsByChain: {},
      averageRiskScore: {},
    };
  }
};
