export async function getFundFlow(
  address: string,
  chainId: number = 1,
  maxHops: number = 1,
  maxAddresses: number = 5
) {
  try {
    const backendUrl =
      import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8888";
    const url = `${backendUrl}/api/analysis/fund-flow?chain_id=${chainId}&address=${address}&max_hops=${maxHops}&max_addresses=${maxAddresses}`;

    const res = await fetch(url, {
      cache: "no-cache", // 캐시 방지
      headers: {
        "Cache-Control": "no-cache",
        // Pragma 헤더 제거 - CORS 문제 해결
      },
    });

    if (!res.ok) {
      throw new Error(`HTTP Error: ${res.status}`);
    }

    const json = await res.json();

    // 디버깅: 응답 구조 확인
    console.log("getFundFlow 응답:", {
      hasData: !!json.data,
      hasNodes: !!(json.data && json.data.nodes),
      nodesCount: json.data?.nodes?.length || 0,
      edgesCount: json.data?.edges?.length || 0,
    });

    // 정상 데이터면 반환
    if (json.data) {
      // nodes가 있으면 반환
      if (json.data.nodes && json.data.nodes.length > 0) {
        return json.data;
      }
      // nodes가 없어도 edges가 있으면 데이터가 있다고 판단
      if (json.data.edges && json.data.edges.length > 0) {
        console.warn(
          "getFundFlow: nodes가 없지만 edges가 있습니다. nodes를 생성합니다."
        );
        // edges에서 nodes 추출
        const nodeSet = new Set<string>();
        json.data.edges.forEach((edge: any) => {
          if (edge.from_address) nodeSet.add(edge.from_address.toLowerCase());
          if (edge.to_address) nodeSet.add(edge.to_address.toLowerCase());
        });

        // nodes 생성
        json.data.nodes = Array.from(nodeSet).map((addr) => ({
          id: `${chainId}-${addr}`,
          address: addr,
          chain_id: chainId,
          label: addr.slice(0, 6) + "..." + addr.slice(-4),
        }));
        return json.data;
      }
    }

    // API 응답이 비어 있으면 null
    console.warn("getFundFlow: 데이터가 없습니다.", json);
    return null;
  } catch (error) {
    console.error("getFundFlow Error:", error);
    return null;
  }
}
