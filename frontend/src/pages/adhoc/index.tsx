import { useState, useMemo, useEffect, useRef } from "react";
import * as S from "./style";
import SearchBar from "@/components/SearchBar";
import Graph, {
  GraphData,
  GraphNodeData,
  GraphEdgeData,
} from "@/components/adhoc/Graph";
import {
  getFundFlowByTxHash,
  analyzeAddressViaBackend,
} from "@/services/backend";
import { getFundFlow } from "@/api/getFundFlow";
import type { AddressAnalysisResponse } from "@/types/api";

import ArrowUpSmall from "@/assets/icon_arrow_up_2.svg";
import ArrowDownSmall from "@/assets/icon_arrow_down2.svg";

// 체인 정보
const CHAINS = [
  { id: 1, name: "Ethereum" },
  { id: 56, name: "BSC" },
  { id: 137, name: "Polygon" },
];

// 주소 라벨링 데이터
const ADDRESS_LABELS: Record<
  string,
  { name: string; type: string; description: string }
> = {
  // DEX
  "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": {
    name: "Uniswap V2 Router",
    type: "DEX",
    description:
      "Uniswap V2의 라우터 컨트랙트로, 토큰 스왑을 위한 DEX 프로토콜입니다.",
  },
  "0xe592427a0aece92de3edee1f18e0157c05861564": {
    name: "Uniswap V3 Router",
    type: "DEX",
    description:
      "Uniswap V3의 라우터 컨트랙트로, 집중 유동성 풀을 사용하는 DEX 프로토콜입니다.",
  },
  // 브릿지
  "0x3666f603cc164936c1b87e207f36beba4ac5f18a": {
    name: "Hop Protocol",
    type: "Bridge",
    description:
      "Hop Protocol은 크로스체인 자산 전송을 위한 브릿지 프로토콜입니다.",
  },
  "0x6b7a87899490ece95443e979ca9485cbe7e71522": {
    name: "Multichain (Anyswap)",
    type: "Bridge",
    description:
      "Multichain은 크로스체인 브릿지 서비스로, 여러 체인 간 자산 전송을 지원합니다.",
  },
  "0x8731d54e9d02c286767d56ac03e8037c07e01e98": {
    name: "Stargate Finance",
    type: "Bridge",
    description: "Stargate Finance는 네이티브 자산 브릿지 프로토콜입니다.",
  },
  "0x2796317b0ff8538f253012862c06787adfb8ceb6": {
    name: "Synapse Protocol",
    type: "Bridge",
    description: "Synapse Protocol은 크로스체인 브릿지 및 스왑 프로토콜입니다.",
  },
  // CEX
  "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": {
    name: "Binance Hot Wallet",
    type: "CEX",
    description:
      "Binance 거래소의 핫 월렛 주소로, 사용자 입출금을 처리하는 중앙화 거래소 주소입니다.",
  },
  "0x28c6c06298d514db089934071355e5743bf21d60": {
    name: "Binance Hot Wallet",
    type: "CEX",
    description: "Binance 거래소의 핫 월렛 주소입니다.",
  },
  "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": {
    name: "Coinbase",
    type: "CEX",
    description: "Coinbase 거래소의 주소입니다.",
  },
  "0x2910543af39aba0cd09dbb2d50200b3e800a63d2": {
    name: "Kraken",
    type: "CEX",
    description: "Kraken 거래소의 주소입니다.",
  },
  // 믹서
  "0x8589427373d6d84e98730d7795d8f6f8731fda16": {
    name: "Tornado Cash",
    type: "Mixer",
    description:
      "Tornado Cash는 프라이버시를 위한 암호화폐 믹서 서비스입니다. OFAC 제재 대상입니다.",
  },
  "0x910cbd523d972eb0a6f4cae4618ad62622b39dbf": {
    name: "Mixer Service",
    type: "Mixer",
    description:
      "암호화폐 믹서 서비스로, 거래 추적을 어렵게 만드는 프라이버시 도구입니다.",
  },
  "0xa160cdab225685da1d56aa342ad8841c3b53f291": {
    name: "Mixer Service",
    type: "Mixer",
    description: "암호화폐 믹서 서비스입니다.",
  },
};

function getAddressLabel(
  address: string
): { name: string; type: string; description: string } | null {
  return ADDRESS_LABELS[address.toLowerCase()] || null;
}

function getChainName(chainId: number): string {
  return CHAINS.find((c) => c.id === chainId)?.name || "Unknown";
}

function toGraphData(
  fundFlowData: any,
  targetAddress: string,
  chainId: number
): GraphData {
  const searchedAddress = targetAddress.trim().toLowerCase();
  return {
    nodes: (fundFlowData.nodes || [])
      .map((node: any) => {
        if (!node) return null;
        let nodeAddress = node?.address || node?.id || "";
        if (nodeAddress.includes("-")) nodeAddress = nodeAddress.split("-")[1];
        if (!nodeAddress) return null;
        const isTargetNode = nodeAddress.toLowerCase() === searchedAddress;
        const addressLabel = getAddressLabel(nodeAddress);
        return {
          address: nodeAddress,
          label: addressLabel
            ? `${addressLabel.name} (${addressLabel.type})`
            : node?.label || "Unknown",
          chain: getChainName(node?.chain_id || node?.chain || chainId),
          type: addressLabel?.type?.toLowerCase() || node?.type || "unknown",
          isWarning: node?.isWarning || node?.is_warning || false,
          isTarget: isTargetNode,
          canExpand: !isTargetNode,
        };
      })
      .filter(Boolean) as GraphNodeData[],
    edges: (fundFlowData.edges || [])
      .map((edge: any) => {
        if (!edge) return null;
        let fromAddr = edge?.from_address || "";
        let toAddr = edge?.to_address || "";
        if (fromAddr.includes("-")) fromAddr = fromAddr.split("-")[1];
        if (toAddr.includes("-")) toAddr = toAddr.split("-")[1];
        if (!fromAddr || !toAddr) return null;
        return {
          source: fromAddr,
          target: toAddr,
          type: edge?.tx_type || "transfer",
          asset: edge?.token_symbol || "ETH",
          amount: edge?.amount || "0",
          timestamp: edge?.timestamp
            ? new Date(Number(edge.timestamp) * 1000).toISOString()
            : undefined,
        };
      })
      .filter(Boolean) as GraphEdgeData[],
  };
}

export default function AdhocPage() {
  // 페이지 정보 (직접 정의)
  const title = "Ad-hoc 분석";
  const intro = "주소를 분석하여 위험도를 평가합니다.";

  const [address, setAddress] = useState("");
  const [chainId, setChainId] = useState(1);
  const [analysisMode, setAnalysisMode] = useState<"address" | "transaction">(
    "address"
  );

  // 그래프 데이터
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [currentHops, setCurrentHops] = useState(1); // 현재 표시 중인 홉 수
  const [currentMaxAddresses, setCurrentMaxAddresses] = useState(5); // 현재 주소 제한
  const [isInitialLoad, setIsInitialLoad] = useState(true); // 초기 로드 여부
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set()); // 확장된 노드 추적

  // 선택된 노드의 상세 정보
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [nodeDetails, setNodeDetails] =
    useState<AddressAnalysisResponse | null>(null);
  const [isDeepAnalysis, setIsDeepAnalysis] = useState(false); // 심층분석 여부
  const [showTestAddresses, setShowTestAddresses] = useState(false); // 테스트 주소 드롭다운 표시 여부
  const testAddressesRef = useRef<HTMLDivElement>(null); // 테스트 주소 드롭다운 ref

  const [loading, setLoading] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        testAddressesRef.current &&
        !testAddressesRef.current.contains(event.target as Node)
      ) {
        setShowTestAddresses(false);
      }
    };

    if (showTestAddresses) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showTestAddresses]);

  // 1. 주소/트랜잭션 입력 → 그래프 데이터 가져오기
  const handleAnalyze = async () => {
    if (!address.trim()) {
      setError(
        analysisMode === "address"
          ? "주소를 입력해주세요."
          : "트랜잭션 해시를 입력해주세요."
      );
      return;
    }

    setError(null);
    setLoading(true);
    setGraphData(null);
    setSelectedNode(null);
    setNodeDetails(null);

    // 초기 로드 시 홉 수와 주소 제한 리셋
    setCurrentHops(1);
    setCurrentMaxAddresses(5);
    setIsInitialLoad(true); // 초기 로드 상태로 설정
    setExpandedNodes(new Set()); // 확장된 노드 초기화

    try {
      let fundFlowData;

      if (analysisMode === "address") {
        // 주소 기반 분석 (노드 수 제한)
        fundFlowData = await getFundFlow(
          address.trim(),
          chainId,
          1, // max_hops: 1홉만
          5 // max_addresses: 방향당 5개만
        );
      } else {
        // 트랜잭션 해시 기반 분석
        fundFlowData = await getFundFlowByTxHash(
          address.trim(),
          chainId,
          1, // max_hops: 1홉만
          5 // max_addresses: 방향당 5개만
        );
      }

      // 빈 데이터 체크
      if (
        !fundFlowData ||
        !fundFlowData.nodes ||
        fundFlowData.nodes.length === 0
      ) {
        setError(
          "해당 주소에 거래 내역이 없습니다. 다른 주소를 시도해보세요.\n예시: 0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be (Binance Hot Wallet)"
        );
        setGraphData(null);
        return;
      }

      setGraphData(toGraphData(fundFlowData, address, chainId));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "그래프 데이터를 가져오는 중 오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  // 2. 노드 클릭 → 상세 정보 가져오기
  const handleNodeClick = async (nodeAddress: string) => {
    if (selectedNode === nodeAddress) {
      // 같은 노드 다시 클릭하면 닫기
      setSelectedNode(null);
      setNodeDetails(null);
      setIsDeepAnalysis(false); // 심층분석 상태도 리셋
      return;
    }

    setSelectedNode(nodeAddress);
    setLoadingDetails(true);
    setNodeDetails(null);
    setIsDeepAnalysis(false); // 새 노드 선택 시 기본 분석으로 리셋

    try {
      // 해당 노드의 리스크 스코어링 요청
      // 기본: 1-hop, basic 분석
      // 심층분석: 3-hop, advanced 분석
      const result = await analyzeAddressViaBackend({
        address: nodeAddress,
        chain_id: chainId,
        max_hops: isDeepAnalysis ? 3 : 1,
        analysis_type: isDeepAnalysis ? "advanced" : "basic",
      });

      setNodeDetails(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "리스크 분석 중 오류가 발생했습니다."
      );
    } finally {
      setLoadingDetails(false);
    }
  };

  // 3. 노드를 타겟으로 설정하고 1-hop 확장 (기존 그래프에 병합)
  const handleExpandNodeAsTarget = async (nodeAddress: string) => {
    if (!nodeAddress.trim() || !graphData) return;

    const nodeAddressLower = nodeAddress.trim().toLowerCase();

    // 이미 확장된 노드인지 확인
    if (expandedNodes.has(nodeAddressLower)) {
      setError("이미 확장된 노드입니다.");
      return;
    }

    // 현재 타겟 주소와 같으면 확장하지 않음
    if (nodeAddressLower === address.trim().toLowerCase()) {
      setError("이미 타겟 주소입니다.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 새로운 노드의 1-hop 거래 로드
      let fundFlowData;
      if (analysisMode === "address") {
        fundFlowData = await getFundFlow(
          nodeAddress.trim(),
          chainId,
          1, // max_hops: 1홉만
          5 // max_addresses: 방향당 5개만
        );
      } else {
        fundFlowData = await getFundFlowByTxHash(
          nodeAddress.trim(),
          chainId,
          1,
          5
        );
      }

      // 기존 노드와 엣지 주소 Set 생성 (중복 체크용)
      const existingNodeAddresses = new Set(
        graphData.nodes.map((n) => n.address.toLowerCase())
      );
      const existingEdges = new Set(
        graphData.edges.map(
          (e) => `${e.source.toLowerCase()}-${e.target.toLowerCase()}`
        )
      );

      // 새로운 노드 추가 (중복 제외)
      const newNodes: GraphNodeData[] = fundFlowData.nodes
        .map((node: any) => {
          let nodeAddr = node.address || node.id;
          if (nodeAddr && nodeAddr.includes("-")) {
            nodeAddr = nodeAddr.split("-")[1];
          }

          const nodeAddrLower = nodeAddr.toLowerCase();

          // 이미 존재하는 노드는 건너뛰기
          if (existingNodeAddresses.has(nodeAddrLower)) {
            return null;
          }

          // 주소 라벨링 정보 가져오기
          const addressLabel = getAddressLabel(nodeAddr);
          const displayLabel = addressLabel
            ? `${addressLabel.name} (${addressLabel.type})`
            : node.label || "Unknown";

          return {
            address: nodeAddr,
            label: displayLabel,
            chain: getChainName(node.chain_id || node.chain || chainId),
            type: addressLabel?.type.toLowerCase() || node.type || "unknown",
            isWarning: node.isWarning || node.is_warning || false,
            isTarget: false, // 확장된 노드는 타겟이 아님
            canExpand: true, // 확장 가능
          };
        })
        .filter(
          (node: GraphNodeData | null): node is GraphNodeData => node !== null
        );

      // 새로운 엣지 추가 (중복 제외)
      const newEdges: GraphEdgeData[] = (fundFlowData.edges || [])
        .map((edge: any) => {
          if (!edge) return null;

          let fromAddr = edge?.from_address || "";
          let toAddr = edge?.to_address || "";

          if (fromAddr && fromAddr.includes("-")) {
            fromAddr = fromAddr.split("-")[1];
          }
          if (toAddr && toAddr.includes("-")) {
            toAddr = toAddr.split("-")[1];
          }

          if (!fromAddr || !toAddr) return null;

          const edgeKey = `${fromAddr.toLowerCase()}-${toAddr.toLowerCase()}`;

          // 이미 존재하는 엣지는 건너뛰기
          if (existingEdges.has(edgeKey)) {
            return null;
          }

          return {
            source: fromAddr,
            target: toAddr,
            type: edge?.tx_type || "transfer",
            asset: edge?.token_symbol || "ETH",
            amount: edge?.amount || "0",
            timestamp: edge?.timestamp
              ? new Date(Number(edge.timestamp) * 1000).toISOString()
              : undefined,
          };
        })
        .filter(
          (edge: GraphEdgeData | null): edge is GraphEdgeData => edge !== null
        );

      // 기존 노드들에서 타겟 노드 업데이트
      // 1. 기존 타겟 노드를 일반 노드로 변경
      // 2. 확장된 노드를 새로운 타겟으로 설정
      const updatedNodes = graphData.nodes.map((node) => {
        const nodeAddrLower = node.address.toLowerCase();

        // 기존 타겟 노드는 일반 노드로 변경
        if (node.isTarget) {
          return {
            ...node,
            isTarget: false,
            canExpand: true, // 이제 확장 가능
          };
        }

        // 확장된 노드를 새로운 타겟으로 설정
        if (nodeAddrLower === nodeAddressLower) {
          return {
            ...node,
            isTarget: true,
            canExpand: false, // 타겟은 확장 불가
          };
        }

        return node;
      });

      // 기존 그래프 데이터에 새로운 노드와 엣지 병합
      const mergedGraphData: GraphData = {
        nodes: [...updatedNodes, ...newNodes],
        edges: [...graphData.edges, ...newEdges],
      };

      setGraphData(mergedGraphData);

      // 확장된 노드로 표시
      setExpandedNodes((prev) => new Set(prev).add(nodeAddressLower));

      // 타겟 주소 업데이트 (선택적 - UI 표시용)
      setAddress(nodeAddress);

      // 사이드바는 유지 (닫지 않음)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "노드 확장 중 오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  // 4. 그래프 확장 (더 많은 노드 로드)
  const handleExpandGraph = async (level: "more" | "all") => {
    if (!address.trim()) return;

    setLoading(true);
    setError(null);
    setIsInitialLoad(false); // 확장 시에는 초기 로드 상태 아님

    try {
      let newHops = currentHops;
      let newMaxAddresses = currentMaxAddresses;

      if (level === "more") {
        // "더보기" → 1단계 확장
        newHops = Math.min(currentHops + 1, 3); // 최대 3홉
        newMaxAddresses = Math.min(currentMaxAddresses + 5, 15); // 최대 15개
      } else {
        // "전체 보기" → 최대 확장
        newHops = 3;
        newMaxAddresses = 20;
      }

      setCurrentHops(newHops);
      setCurrentMaxAddresses(newMaxAddresses);

      // 그래프 재로드
      let fundFlowData;
      if (analysisMode === "address") {
        fundFlowData = await getFundFlow(
          address.trim(),
          chainId,
          newHops,
          newMaxAddresses
        );
      } else {
        fundFlowData = await getFundFlowByTxHash(
          address.trim(),
          chainId,
          newHops,
          newMaxAddresses
        );
      }

      setGraphData(toGraphData(fundFlowData, address, chainId));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "그래프 확장 중 오류가 발생했습니다."
      );
    } finally {
      setLoading(false);
    }
  };

  // 리스크 레벨 색상
  const getRiskColor = (level: string) => {
    switch (level) {
      case "critical":
        return "#dc2626";
      case "high":
        return "#ea580c";
      case "medium":
        return "#eab308";
      case "low":
        return "#22c55e";
      default:
        return "#6b7280";
    }
  };

  return (
    <S.Root>
      {/* 헤더 */}
      <S.HeaderSection>
        <div style={{display: "flex", flexDirection: "column", gap: 5}}>
          <S.Title>{title}</S.Title>
          <S.Intro>{intro}</S.Intro>
        </div>
      </S.HeaderSection>

      {/* 검색 영역 */}
      <S.SearchSection>
        {/* 분석 모드 선택 */}
        {/* <S.ModeSelector>
          <S.ModeButton
            $active={analysisMode === "address"}
            onClick={() => setAnalysisMode("address")}
          >
            주소 분석
          </S.ModeButton>
          <S.ModeButton
            $active={analysisMode === "transaction"}
            onClick={() => setAnalysisMode("transaction")}
          >
            트랜잭션 분석
          </S.ModeButton>
        </S.ModeSelector> */}

        {/* 체인 선택 + 검색바 + 분석 버튼 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "20px",
            width: "100%",
          }}
        >
          <S.ChainSelect
            value={chainId}
            onChange={(e) => setChainId(Number(e.target.value))}
          >
            {CHAINS.map((chain) => (
              <option key={chain.id} value={chain.id}>
                {chain.name}
              </option>
            ))}
          </S.ChainSelect>

          <SearchBar
            value={address}
            onChange={setAddress}
            onSearch={handleAnalyze}
            placeholder={
              analysisMode === "address"
                ? "주소를 입력하세요 (0x...)"
                : "트랜잭션 해시를 입력하세요 (0x...)"
            }
          />

          <S.AnalyzeButton onClick={handleAnalyze} disabled={loading}>
            {loading ? "분석 중..." : "분석하기"}
          </S.AnalyzeButton>
        </div>

        {/* 테스트 주소 버튼 및 드롭다운 */}
        <div
          ref={testAddressesRef}
          style={{ position: "relative", display: "inline-block" }}
        >
          <button
            onClick={() => setShowTestAddresses(!showTestAddresses)}
            style={{
              background: "rgba(59, 130, 246, 0.1)",
              border: "1px solid rgba(59, 130, 246, 0.3)",
              borderRadius: "6px",
              padding: "6px 12px",
              color: "#93c5fd",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              gap: "6px",
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = "rgba(59, 130, 246, 0.2)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "rgba(59, 130, 246, 0.1)";
            }}
          >
            테스트 주소
            <span >
              <img
                src={showTestAddresses ? ArrowUpSmall : ArrowDownSmall}
                alt="toggle"
                style={{ width: 10, height: 10 }}
              />
            </span>
          </button>

          {/* 드롭다운 메뉴 */}
          {showTestAddresses && (
            <div
              style={{
                position: "absolute",
                top: "100%",
                left: 0,
                marginTop: "8px",
                background: "rgba(30, 41, 59, 0.95)",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                borderRadius: "8px",
                padding: "12px",
                minWidth: "300px",
                zIndex: 1000,
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
              }}
            >
              {/* 기본 테스트 주소 */}
              <div style={{ marginBottom: "12px" }}>
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#94a3b8",
                    marginBottom: "8px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  기본 테스트 주소
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                  }}
                >
                  <button
                    onClick={() => {
                      setAddress("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045");
                      setAnalysisMode("address");
                      setShowTestAddresses(false);
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#60a5fa",
                      cursor: "pointer",
                      textAlign: "left",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      fontSize: "12px",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background =
                        "rgba(59, 130, 246, 0.1)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "none";
                    }}
                  >
                    Vitalik Buterin
                  </button>
                  <button
                    onClick={() => {
                      setAddress("0x28C6c06298d514Db089934071355E5743bf21d60");
                      setAnalysisMode("address");
                      setShowTestAddresses(false);
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#60a5fa",
                      cursor: "pointer",
                      textAlign: "left",
                      padding: "4px 8px",
                      borderRadius: "4px",
                      fontSize: "12px",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background =
                        "rgba(59, 130, 246, 0.1)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "none";
                    }}
                  >
                    Binance Hot Wallet
                  </button>
                </div>
              </div>

              {/* 룰 테스트용 주소 */}
              <div
                style={{
                  borderTop: "1px solid rgba(59, 130, 246, 0.2)",
                  paddingTop: "12px",
                }}
              >
                <div
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#94a3b8",
                    marginBottom: "8px",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                  }}
                >
                  룰 테스트용 주소
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  <div>
                    <span style={{ color: "#9ca3af", fontSize: "11px" }}>
                      믹서:
                    </span>
                    <button
                      onClick={() => {
                        setAddress(
                          "0x8589427373D6D84E98730D7795D8f6f8731FDA16"
                        );
                        setAnalysisMode("address");
                        setShowTestAddresses(false);
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#60a5fa",
                        cursor: "pointer",
                        marginLeft: "8px",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background =
                          "rgba(59, 130, 246, 0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "none";
                      }}
                    >
                      Tornado Cash
                    </button>
                  </div>
                  <div>
                    <span style={{ color: "#9ca3af", fontSize: "11px" }}>
                      브릿지:
                    </span>
                    <button
                      onClick={() => {
                        setAddress(
                          "0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a"
                        );
                        setAnalysisMode("address");
                        setShowTestAddresses(false);
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#60a5fa",
                        cursor: "pointer",
                        marginLeft: "8px",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background =
                          "rgba(59, 130, 246, 0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "none";
                      }}
                    >
                      Hop Protocol
                    </button>
                  </div>
                  <div>
                    <span style={{ color: "#9ca3af", fontSize: "11px" }}>
                      CEX:
                    </span>
                    <button
                      onClick={() => {
                        setAddress(
                          "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE"
                        );
                        setAnalysisMode("address");
                        setShowTestAddresses(false);
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#60a5fa",
                        cursor: "pointer",
                        marginLeft: "8px",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background =
                          "rgba(59, 130, 246, 0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "none";
                      }}
                    >
                      Binance
                    </button>
                  </div>
                  <div>
                    <span style={{ color: "#9ca3af", fontSize: "11px" }}>
                      DEX:
                    </span>
                    <button
                      onClick={() => {
                        setAddress(
                          "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
                        );
                        setAnalysisMode("address");
                        setShowTestAddresses(false);
                      }}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#60a5fa",
                        cursor: "pointer",
                        marginLeft: "8px",
                        padding: "4px 8px",
                        borderRadius: "4px",
                        fontSize: "12px",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background =
                          "rgba(59, 130, 246, 0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = "none";
                      }}
                    >
                      Uniswap V2
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </S.SearchSection>

      {/* 에러 메시지 */}
      {error && <S.ErrorMessage>{error}</S.ErrorMessage>}

      {/* 그래프 + 사이드바 레이아웃 */}
      {graphData && (
        <S.ContentLayout>
          {/* 왼쪽: 그래프 */}
          <S.GraphSection $hasDetails={!!selectedNode}>
            <Graph
              data={graphData}
              onNodeClick={handleNodeClick}
              fitViewOnMount={isInitialLoad}
            />

            {/* 그래프 확장 버튼 */}
            <S.GraphControlBar>
              <S.GraphInfo>
                현재: {currentHops}홉, 방향당 {currentMaxAddresses}개 주소
              </S.GraphInfo>
              <S.GraphButtonGroup>
                <S.ExpandButton
                  onClick={() => handleExpandGraph("more")}
                  disabled={loading || currentHops >= 3}
                >
                  더보기
                  <S.ButtonHint>+1홉씩 점진적 확장</S.ButtonHint>
                </S.ExpandButton>
                <S.ExpandButton
                  onClick={() => handleExpandGraph("all")}
                  disabled={loading || currentHops >= 3}
                  primary
                >
                  전체 보기
                  <S.ButtonHint>3홉 최대 확장</S.ButtonHint>
                </S.ExpandButton>
              </S.GraphButtonGroup>
            </S.GraphControlBar>
          </S.GraphSection>

          {/* 오른쪽: 노드 상세 정보 (선택 시에만 표시) */}
          {selectedNode && (
            <S.DetailsSidebar>
              <S.SidebarHeader>
                <S.SidebarTitle>리스크 분석 결과</S.SidebarTitle>
                <S.CloseButton onClick={() => setSelectedNode(null)}>
                  ✕
                </S.CloseButton>
              </S.SidebarHeader>

              {loadingDetails ? (
                <S.LoadingMessage>분석 중...</S.LoadingMessage>
              ) : nodeDetails ? (
                <>
                  {/* 주소 */}
                  <S.DetailSection>
                    <S.DetailLabel>주소</S.DetailLabel>
                    <S.DetailValue
                      style={{
                        fontFamily: "monospace",
                        fontSize: "13px",
                        wordBreak: "break-all",
                      }}
                    >
                      {nodeDetails.target_address}
                    </S.DetailValue>
                    {/* 주소 라벨링 정보 */}
                    {(() => {
                      const addressLabel = getAddressLabel(
                        nodeDetails.target_address
                      );
                      if (addressLabel) {
                        return (
                          <div
                            style={{
                              marginTop: "12px",
                              padding: "12px",
                              background: "rgba(59, 130, 246, 0.1)",
                              border: "1px solid rgba(59, 130, 246, 0.2)",
                              borderRadius: "8px",
                            }}
                          >
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                marginBottom: "8px",
                              }}
                            >
                              <span
                                style={{
                                  background:
                                    addressLabel.type === "DEX"
                                      ? "rgba(16, 185, 129, 0.3)"
                                      : addressLabel.type === "Bridge"
                                      ? "rgba(139, 92, 246, 0.3)"
                                      : addressLabel.type === "CEX"
                                      ? "rgba(59, 130, 246, 0.3)"
                                      : addressLabel.type === "Mixer"
                                      ? "rgba(239, 68, 68, 0.3)"
                                      : "rgba(59, 130, 246, 0.2)",
                                  color:
                                    addressLabel.type === "DEX"
                                      ? "#6ee7b7"
                                      : addressLabel.type === "Bridge"
                                      ? "#c4b5fd"
                                      : addressLabel.type === "CEX"
                                      ? "#93c5fd"
                                      : addressLabel.type === "Mixer"
                                      ? "#fca5a5"
                                      : "#bfdbfe",
                                  padding: "4px 8px",
                                  borderRadius: "4px",
                                  fontSize: "11px",
                                  fontWeight: 600,
                                  textTransform: "uppercase",
                                }}
                              >
                                {addressLabel.type}
                              </span>
                              <span
                                style={{
                                  fontSize: "14px",
                                  fontWeight: 600,
                                  color: "var(--white, #fff)",
                                }}
                              >
                                {addressLabel.name}
                              </span>
                            </div>
                            <div
                              style={{
                                fontSize: "12px",
                                color: "var(--primary400, #aeb9e1)",
                                lineHeight: 1.5,
                              }}
                            >
                              {addressLabel.description}
                            </div>
                          </div>
                        );
                      }
                      return null;
                    })()}
                  </S.DetailSection>

                  {/* 리스크 점수 */}
                  <S.DetailSection>
                    <S.DetailLabel>리스크 점수</S.DetailLabel>
                    <S.RiskScore
                      style={{
                        color: getRiskColor(nodeDetails.risk_level),
                      }}
                    >
                      {nodeDetails.risk_score.toFixed(2)} / 100
                    </S.RiskScore>
                    <S.RiskLevel
                      style={{
                        background: `${getRiskColor(nodeDetails.risk_level)}20`,
                        color: getRiskColor(nodeDetails.risk_level),
                      }}
                    >
                      {nodeDetails.risk_level.toUpperCase()}
                    </S.RiskLevel>
                  </S.DetailSection>

                  {/* 리스크 태그 */}
                  {nodeDetails.risk_tags &&
                    nodeDetails.risk_tags.length > 0 && (
                      <S.DetailSection>
                        <S.DetailLabel>리스크 태그</S.DetailLabel>
                        <S.TagContainer>
                          {nodeDetails.risk_tags.map((tag, idx) => (
                            <S.RiskTag key={idx}>{tag}</S.RiskTag>
                          ))}
                        </S.TagContainer>
                      </S.DetailSection>
                    )}

                  {/* 발동된 룰 */}
                  {nodeDetails.fired_rules &&
                    nodeDetails.fired_rules.length > 0 && (
                      <S.DetailSection>
                        <S.DetailLabel>발동된 룰</S.DetailLabel>
                        <S.RuleList>
                          {nodeDetails.fired_rules.map((rule, idx) => (
                            <S.RuleItem key={idx}>
                              <span style={{ fontWeight: 600 }}>
                                {rule.rule_id}
                              </span>
                              <span style={{ color: "#9ca3af" }}>
                                +{rule.score.toFixed(1)}점
                              </span>
                            </S.RuleItem>
                          ))}
                        </S.RuleList>
                      </S.DetailSection>
                    )}

                  {/* 거래 시간 정보 */}
                  {(() => {
                    // 해당 노드와 연결된 엣지의 시간 정보 찾기
                    const nodeEdges =
                      graphData?.edges.filter(
                        (edge) =>
                          edge.source.toLowerCase() ===
                            selectedNode?.toLowerCase() ||
                          edge.target.toLowerCase() ===
                            selectedNode?.toLowerCase()
                      ) || [];

                    if (nodeEdges.length > 0) {
                      // 가장 최근 거래 시간 찾기
                      const timestamps = nodeEdges
                        .map((edge) => edge.timestamp)
                        .filter((ts) => ts)
                        .sort()
                        .reverse();

                      if (timestamps.length > 0) {
                        const latestTimestamp = timestamps[0];
                        if (latestTimestamp) {
                          try {
                            const date = new Date(latestTimestamp);
                            if (!isNaN(date.getTime())) {
                              const formattedDate = date.toLocaleString(
                                "ko-KR",
                                {
                                  year: "numeric",
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  hour12: false,
                                }
                              );

                              return (
                                <S.DetailSection>
                                  <S.DetailLabel>최근 거래 시간</S.DetailLabel>
                                  <S.DetailValue
                                    style={{
                                      fontSize: "13px",
                                      color: "#9ca3af",
                                    }}
                                  >
                                    {formattedDate}
                                  </S.DetailValue>
                                </S.DetailSection>
                              );
                            }
                          } catch {
                            // 날짜 파싱 실패 시 무시
                          }
                        }
                      }
                    }
                    return null;
                  })()}

                  {/* 설명 */}
                  {nodeDetails.explanation && (
                    <S.DetailSection>
                      <S.DetailLabel>상세 설명</S.DetailLabel>
                      <S.DetailValue>{nodeDetails.explanation}</S.DetailValue>
                    </S.DetailSection>
                  )}

                  {/* 버튼 영역 (맨 아래) */}
                  <div
                    style={{
                      marginTop: "24px",
                      paddingTop: "24px",
                      borderTop: "1px solid var(--secondary200, #343b4f)",
                      display: "flex",
                      flexDirection: "column",
                      gap: "12px",
                    }}
                  >
                    {/* 심층분석 버튼 */}
                    {!isDeepAnalysis && (
                      <button
                        onClick={async () => {
                          if (!selectedNode) return;
                          setIsDeepAnalysis(true);
                          setLoadingDetails(true);
                          setNodeDetails(null);

                          try {
                            const result = await analyzeAddressViaBackend({
                              address: selectedNode,
                              chain_id: chainId,
                              max_hops: 3,
                              analysis_type: "advanced",
                            });
                            setNodeDetails(result);
                          } catch (err) {
                            setError(
                              err instanceof Error
                                ? err.message
                                : "심층분석 중 오류가 발생했습니다."
                            );
                            setIsDeepAnalysis(false);
                          } finally {
                            setLoadingDetails(false);
                          }
                        }}
                        disabled={loadingDetails}
                        style={{
                          width: "100%",
                          padding: "10px 16px",
                          background: "var(--red300, #ff5a65)",
                          color: "var(--white, #fff)",
                          border: "1px solid var(--red300, #ff5a65)",
                          borderRadius: "8px",
                          fontSize: "13px",
                          fontWeight: 600,
                          cursor: loadingDetails ? "not-allowed" : "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: "8px",
                          transition: "all 0.2s ease",
                          opacity: loadingDetails ? 0.5 : 1,
                          fontFamily: "Mona Sans",
                        }}
                        onMouseEnter={(e) => {
                          if (!loadingDetails) {
                            e.currentTarget.style.background = "#ff6b7f";
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background =
                            "var(--red300, #ff5a65)";
                        }}
                      >
                        <span>
                          {loadingDetails
                            ? "심층분석 중..."
                            : "심층분석 (3-hop, Advanced)"}
                        </span>
                      </button>
                    )}

                    {/* 확장 버튼 (타겟 주소가 아닌 경우에만 표시) */}
                    {selectedNode &&
                      selectedNode.toLowerCase() !==
                        address.trim().toLowerCase() && (
                        <button
                          onClick={() => handleExpandNodeAsTarget(selectedNode)}
                          disabled={loading}
                          style={{
                            width: "100%",
                            padding: "10px 16px",
                            background: "var(--neutral800, #060a1d)",
                            color: "var(--primary400, #aeb9e1)",
                            border: "1px solid var(--secondary200, #343b4f)",
                            borderRadius: "8px",
                            fontSize: "13px",
                            fontWeight: 600,
                            cursor: loading ? "not-allowed" : "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "8px",
                            transition: "all 0.2s ease",
                            opacity: loading ? 0.5 : 1,
                            fontFamily: "Mona Sans",
                          }}
                          onMouseEnter={(e) => {
                            if (!loading) {
                              e.currentTarget.style.background =
                                "var(--secondary200, #343b4f)";
                              e.currentTarget.style.borderColor =
                                "var(--primary500, #7c8dd8)";
                              e.currentTarget.style.color =
                                "var(--white, #fff)";
                            }
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background =
                              "var(--neutral800, #060a1d)";
                            e.currentTarget.style.borderColor =
                              "var(--secondary200, #343b4f)";
                            e.currentTarget.style.color =
                              "var(--primary400, #aeb9e1)";
                          }}
                        >
                          <span style={{ fontSize: "14px" }}>→</span>
                          <span>{loading ? "확장 중..." : "이 노드 확장"}</span>
                        </button>
                      )}
                  </div>
                </>
              ) : (
                <S.ErrorMessage>
                  리스크 분석 결과를 가져올 수 없습니다.
                </S.ErrorMessage>
              )}
            </S.DetailsSidebar>
          )}
        </S.ContentLayout>
      )}

      {/* 데이터가 없을 때 메시지 */}
      {!loading && !graphData && !error && (
        <S.EmptyMessage>
          주소를 입력하고 "분석하기" 버튼을 클릭하세요.
        </S.EmptyMessage>
      )}
    </S.Root>
  );
}
