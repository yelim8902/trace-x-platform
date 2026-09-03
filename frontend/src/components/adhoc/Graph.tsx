import { useMemo, useEffect, useRef } from "react";
import ReactFlow, {
  Handle,
  MarkerType,
  Position,
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import "reactflow/dist/style.css";
import dagre from "dagre";

// ====== 타입 정의 ======
export type GraphNodeData = {
  address: string;
  label: string;
  chain: string;
  type: string;
  isWarning: boolean;
  isTarget: boolean; // 타겟 주소 여부
  canExpand?: boolean; // 확장 가능 여부
};

export type GraphEdgeData = {
  source: string;
  target: string;
  type: string;
  asset: string;
  amount: string;
  timestamp?: string;
};

export type GraphData = {
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
};

// ====== Custom Node ======
type CustomNodeProps = {
  data: GraphNodeData;
};

const CustomNode = ({ data }: CustomNodeProps) => {
  const shortAddress = data.address
    ? `${data.address.slice(0, 8)}...${data.address.slice(-6)}`
    : "Unknown";
  const isHighRisk = data.isWarning;
  const isTarget = data.isTarget; // 타겟 주소 여부
  const canExpand = data.canExpand && !isTarget; // 확장 가능하고 타겟이 아닌 경우

  // 타겟 주소일 경우 특별한 스타일 적용
  const borderColor = isTarget
    ? "#10b981" // 초록색
    : canExpand
    ? "#667eea" // 보라색 (확장 가능)
    : isHighRisk
    ? "#ef4444" // 빨간색
    : "#3b82f6"; // 파란색

  const bgGradient = isTarget
    ? "linear-gradient(135deg, #065f46 0%, #047857 100%)" // 초록 그라디언트
    : isHighRisk
    ? "linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%)" // 빨간 그라디언트
    : "linear-gradient(135deg, #0c4a6e 0%, #075985 100%)"; // 파란 그라디언트

  const boxShadow = isTarget
    ? "0 6px 24px rgba(16, 185, 129, 0.4)" // 초록 그림자
    : isHighRisk
    ? "0 4px 20px rgba(239, 68, 68, 0.3)"
    : "0 4px 16px rgba(59, 130, 246, 0.3)";

  const hoverShadow = isTarget
    ? "0 10px 36px rgba(16, 185, 129, 0.6)" // 초록 그림자
    : isHighRisk
    ? "0 8px 30px rgba(239, 68, 68, 0.5)"
    : "0 8px 24px rgba(59, 130, 246, 0.5)";

  return (
    <div
      style={{
        padding: isTarget ? "18px 22px" : "14px 18px", // 타겟은 패딩 증가
        borderRadius: 12,
        border: `3px solid ${borderColor}`, // 타겟은 3px 테두리
        background: bgGradient,
        color: "#fff",
        fontSize: isTarget ? 14 : 13, // 타겟은 폰트 크기 증가
        cursor: "pointer",
        minWidth: isTarget ? "260px" : "220px", // 타겟은 더 넓게
        maxWidth: isTarget ? "320px" : "280px",
        boxShadow: boxShadow,
        transition: "all 0.3s ease",
        position: "relative",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-2px) scale(1.02)";
        e.currentTarget.style.boxShadow = hoverShadow;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = boxShadow;
      }}
    >
      {/* TARGET 뱃지 (타겟 주소일 경우만 표시) */}
      {isTarget && (
        <div
          style={{
            position: "absolute",
            top: "-10px",
            right: "-10px",
            background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
            color: "white",
            padding: "4px 10px",
            borderRadius: "12px",
            fontSize: "10px",
            fontWeight: "800",
            boxShadow: "0 4px 12px rgba(16, 185, 129, 0.5)",
            border: "2px solid white",
            letterSpacing: "0.5px",
          }}
        >
          TARGET
        </div>
      )}

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: isTarget ? "#10b981" : isHighRisk ? "#ef4444" : "#3b82f6",
          width: isTarget ? 14 : 12, // 타겟은 핸들 크기 증가
          height: isTarget ? 14 : 12,
          border: "2px solid white",
        }}
      />
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: isTarget ? "#10b981" : isHighRisk ? "#ef4444" : "#3b82f6",
          width: isTarget ? 14 : 12,
          height: isTarget ? 14 : 12,
          border: "2px solid white",
        }}
      />

      {/* 주소 */}
      <div
        style={{
          fontWeight: "700",
          marginBottom: "8px",
          color: isTarget ? "#d1fae5" : isHighRisk ? "#fca5a5" : "#bfdbfe",
          fontFamily: "monospace",
          fontSize: "14px",
          letterSpacing: "0.5px",
        }}
      >
        {shortAddress}
      </div>

      {/* 라벨과 체인 */}
      <div
        style={{
          fontSize: 11,
          color: "#cbd5e1",
          display: "flex",
          gap: "8px",
          flexWrap: "wrap",
          alignItems: "center",
          marginTop: "4px",
        }}
      >
        {/* 라벨 배지 (타입별 색상) - 더 눈에 띄게 */}
        {data.type && data.type !== "unknown" && (
          <span
            style={{
              background:
                data.type === "dex"
                  ? "rgba(16, 185, 129, 0.5)"
                  : data.type === "bridge"
                  ? "rgba(139, 92, 246, 0.5)"
                  : data.type === "cex"
                  ? "rgba(59, 130, 246, 0.5)"
                  : data.type === "mixer"
                  ? "rgba(239, 68, 68, 0.5)"
                  : "rgba(59, 130, 246, 0.3)",
              color:
                data.type === "dex"
                  ? "#10b981"
                  : data.type === "bridge"
                  ? "#a78bfa"
                  : data.type === "cex"
                  ? "#60a5fa"
                  : data.type === "mixer"
                  ? "#f87171"
                  : "#bfdbfe",
              padding: "4px 8px",
              borderRadius: 6,
              fontWeight: 700,
              fontSize: 11,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              border:
                data.type === "dex"
                  ? "1px solid rgba(16, 185, 129, 0.6)"
                  : data.type === "bridge"
                  ? "1px solid rgba(139, 92, 246, 0.6)"
                  : data.type === "cex"
                  ? "1px solid rgba(59, 130, 246, 0.6)"
                  : data.type === "mixer"
                  ? "1px solid rgba(239, 68, 68, 0.6)"
                  : "1px solid rgba(59, 130, 246, 0.4)",
              boxShadow: "0 2px 4px rgba(0, 0, 0, 0.2)",
            }}
          >
            {data.type}
          </span>
        )}
        {/* 주소 라벨 - 더 눈에 띄게 */}
        <span
          style={{
            background: "rgba(59, 130, 246, 0.3)",
            color: "#bfdbfe",
            padding: "4px 8px",
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            border: "1px solid rgba(59, 130, 246, 0.4)",
            boxShadow: "0 2px 4px rgba(0, 0, 0, 0.15)",
          }}
        >
          {data.label}
        </span>
        {/* 체인 정보 */}
        <span
          style={{
            fontSize: 10,
            color: "#94a3b8",
            fontWeight: 600,
            padding: "2px 6px",
            background: "rgba(148, 163, 184, 0.15)",
            borderRadius: 4,
          }}
        >
          {data.chain}
        </span>
        {canExpand && (
          <span
            style={{
              fontSize: 16,
              color: "#667eea",
              fontWeight: "bold",
              marginLeft: "auto",
              textShadow: "0 0 4px rgba(102, 126, 234, 0.5)",
            }}
          >
            →
          </span>
        )}
      </div>
    </div>
  );
};

// ====== DAGRE Layout ======
const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  // 가로 방향 레이아웃 (좌→우) - 중앙 노드 기준으로 펼쳐짐!
  dagreGraph.setGraph({
    rankdir: "LR", // Left to Right (좌→우 방향)
    align: "UL", // 상단 정렬
    nodesep: 150, // 같은 레벨 노드 간 세로 간격
    ranksep: 350, // 레벨 간 가로 간격
    edgesep: 30, // 엣지 간 간격
    marginx: 100, // 좌우 여백
    marginy: 80, // 상하 여백
    ranker: "network-simplex", // 최적화된 레이아웃 알고리즘
  });

  nodes
    .filter((node) => node && node.id)
    .forEach((node) => {
      // 노드 크기
      dagreGraph.setNode(node.id, { width: 240, height: 85 });
    });

  edges
    .filter((edge) => edge && edge.source && edge.target)
    .forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes
    .filter((node) => node && node.id)
    .map((node) => {
      const pos = dagreGraph.node(node.id);
      if (!pos) {
        // pos가 없으면 기본 위치 반환
        return {
          ...node,
          position: { x: 0, y: 0 },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
        };
      }
      return {
        ...node,
        position: { x: pos.x || 0, y: pos.y || 0 },
        // LR 방향에서는 Left/Right 사용
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });

  return { nodes: layoutedNodes, edges };
};

// ====== Main Component ======
export function Graph({
  data,
  onNodeClick,
  fitViewOnMount, // 초기 로드 시에만 fitView
}: {
  data: GraphData;
  onNodeClick?: (address: string) => void;
  fitViewOnMount: boolean;
}) {
  const reactFlowInstance = useReactFlow(); // useReactFlow 훅 사용
  const hasFitView = useRef(false); // fitView가 실행되었는지 추적

  // 데이터 안전 체크
  if (!data || !data.nodes || !data.edges) {
    return (
      <div
        style={{
          width: "100%",
          height: "750px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#fff",
        }}
      >
        데이터를 불러오는 중...
      </div>
    );
  }

  // ----- 노드 변환 -----
  const nodes = useMemo<Node<GraphNodeData>[]>(
    () =>
      (data?.nodes || [])
        .filter((n) => n && n.address)
        .map((n) => ({
          id: n.address,
          type: "customNode",
          data: n,
          position: { x: 0, y: 0 }, // 초기 위치는 0,0으로 설정 (dagre가 업데이트할 것)
        })),
    [data]
  );

  // ----- 엣지 변환 + timestamp 포함 라벨 -----
  const edges = useMemo<Edge[]>(
    () =>
      (data?.edges || [])
        .filter((e) => e && e.source && e.target)
        .map((e, i) => {
        // 타임스탬프 포맷팅 (안전하게)
        let displayTimestamp = "";
        if (e.timestamp) {
          try {
            const date = new Date(e.timestamp);
            // 유효한 날짜인지 확인
            if (!isNaN(date.getTime())) {
              const month = String(date.getMonth() + 1).padStart(2, "0");
              const day = String(date.getDate()).padStart(2, "0");
              const hour = String(date.getHours()).padStart(2, "0");
              const min = String(date.getMinutes()).padStart(2, "0");
              displayTimestamp = `${month}/${day} ${hour}:${min}`;
            }
          } catch {
            // 날짜 파싱 실패 시 빈 문자열
            displayTimestamp = "";
          }
        }

        // 금액 포맷팅 (간결하게)
        let displayAmount = "";
        if (e.amount) {
          const num = Number(e.amount);
          if (!isNaN(num)) {
            if (num === 0) {
              displayAmount = "0";
            } else if (num < 0.0001 && num !== 0) {
              displayAmount = num.toExponential(2);
            } else if (num < 1) {
              displayAmount = num.toFixed(4);
            } else if (num < 1000) {
              displayAmount = num.toFixed(2);
            } else {
              displayAmount = num.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              });
            }
          }
        }

        // 자산 이름 간결화
        let displayAsset = e.asset || "ETH";
        if (displayAsset.length > 10) {
          displayAsset = displayAsset.slice(0, 8) + "..";
        }

        // 라벨 구성 (자산, 금액, 시간 포함)
        let edgeLabel = "";

        // 자산과 금액
        if (displayAmount && displayAmount !== "0") {
          edgeLabel = `${displayAsset} ${displayAmount}`;
        } else {
          edgeLabel = displayAsset;
        }

        // 시간 정보 추가 (간결하게)
        if (displayTimestamp) {
          edgeLabel = `${edgeLabel}\n${displayTimestamp}`;
        }

        return {
          id: `edge-${i}`,
          source: e.source,
          target: e.target,
          type: "default", // smoothstep → default (더 단순하고 명확)
          animated: false,
          style: {
            stroke: "#60a5fa",
            strokeWidth: 3, // 엣지 더 굵게
            strokeOpacity: 0.8,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: "#60a5fa",
            width: 25,
            height: 25,
          },
          label: edgeLabel,
          labelStyle: {
            fill: "#e0f2fe",
            fontSize: 12,
            fontWeight: 700,
          },
          labelBgStyle: {
            fill: "rgba(15, 23, 42, 0.98)", // 불투명도 증가
            color: "#fff",
            borderRadius: 8,
            border: "2px solid rgba(96, 165, 250, 0.6)", // 테두리 두껍게
          },
          labelBgPadding: [12, 8] as [number, number], // 패딩 증가
          labelShowBg: true, // 배경 명시적으로 표시
        };
      }),
    [data]
  );

  // Layout 적용
  const layouted = useMemo(
    () => getLayoutedElements(nodes, edges),
    [nodes, edges]
  );

  // ----- 타겟 노드로 자동 포커스 (레이아웃 적용 후!) -----
  useEffect(() => {
    if (layouted.nodes.length > 0) {
      // 레이아웃 적용된 노드에서 타겟 노드 찾기
      const targetNode = layouted.nodes.find((node) => node.data.isTarget);

      setTimeout(() => {
        if (targetNode && targetNode.position) {
          // 타겟 노드가 있으면 그 노드 중심으로 포커스
          reactFlowInstance.setCenter(
            targetNode.position.x,
            targetNode.position.y,
            {
              zoom: 0.8, // 적당한 줌 레벨
              duration: 800, // 부드러운 애니메이션 (800ms)
            }
          );
          console.log(
            "🎯 타겟 노드로 포커스:",
            targetNode.id,
            targetNode.position
          );
        } else if (fitViewOnMount && !hasFitView.current) {
          // 타겟 노드가 없으면 (또는 초기 로드인데 타겟이 없으면) 전체 fitView
          reactFlowInstance.fitView({
            padding: 0.15,
            maxZoom: 1.2,
          });
          hasFitView.current = true;
        }
      }, 200); // 레이아웃 계산 완료 후
    }
  }, [layouted, fitViewOnMount, reactFlowInstance]);

  // 클릭하면 부모 컴포넌트로 전달
  const handleNodeClick = (event: any, node: Node) => {
    // 부모 컴포넌트의 onNodeClick 호출
    if (onNodeClick) {
      onNodeClick(node.id);
    }
  };

  return (
    <div
      style={{
        width: "100%",
        height: "750px", // 사이드바는 이제 내용 길이만큼 자라고, 그래프는 독립적으로 고정 높이 유지
        marginTop: 20,
        border: "1px solid var(--secondary200, #343b4f)",
        borderRadius: "8px",
        overflow: "hidden",
        background: "var(--neutral800, #060a1d)",
      }}
    >
      <ReactFlow
        nodes={layouted.nodes}
        edges={layouted.edges}
        nodeTypes={{ customNode: CustomNode }}
        fitView={false} // 초기 로드 시에만 fitViewOnMount로 제어
        fitViewOptions={{
          padding: 0.15, // 여백 15%
          maxZoom: 1.2, // 최대 확대 (너무 크게 보이지 않게)
        }}
        minZoom={0.1} // 최소 축소
        maxZoom={1.8} // 최대 확대
        proOptions={{ hideAttribution: true }}
        onNodeClick={handleNodeClick}
        style={{
          background: "var(--neutral800, #060a1d)",
        }}
      >
        {/* 줌/이동 컨트롤 */}
        <Controls
          style={{
            background: "rgba(15, 23, 42, 0.95)",
            border: "2px solid #3b82f6",
            borderRadius: "12px",
            boxShadow: "0 4px 16px rgba(0, 0, 0, 0.5)",
          }}
        />

        {/* 배경 그리드 */}
        <Background
          color="#1e3a8a"
          gap={20}
          size={1}
          style={{ opacity: 0.3 }}
        />

        {/* 미니맵 */}
        <MiniMap
          nodeColor={(node) => {
            const nodeData = node.data as GraphNodeData;
            if (nodeData.isTarget) return "#10b981"; // 타겟 노드는 초록색
            return nodeData.isWarning ? "#ef4444" : "#3b82f6";
          }}
          maskColor="rgba(0, 0, 0, 0.7)"
        />
      </ReactFlow>
    </div>
  );
}

// Wrap with ReactFlowProvider
export default function GraphWithProvider(props: {
  data: GraphData;
  onNodeClick?: (address: string) => void;
  fitViewOnMount: boolean;
}) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}
