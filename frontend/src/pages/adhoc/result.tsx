import { useSearchParams, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import * as S from "./style";
import SearchBar from "@/components/SearchBar";
import Graph from "@/components/adhoc/Graph";
import { getFundFlow } from "@/api/getFundFlow";
import type { GraphData } from "@/components/adhoc/Graph";

export default function AdhocResultPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const [value, setValue] = useState(params.get("tx") || "");
  const [graphData, setGraphData] = useState<GraphData | null>(null);

  /* ---------------- 검색 시 URL 갱신 ---------------- */
  const handleSearch = () => {
    if (!value) return;
    navigate(`/adhoc/result?tx=${value}`);
  };

  /* ---------------- URL(tx)이 변경되면 API 호출 ---------------- */
  useEffect(() => {
    const tx = params.get("tx");
    if (!tx) return;

    const fetchData = async () => {
      const data = await getFundFlow(tx); // 실패 시 null 리턴하는 구조 추천
      setGraphData(data); // Graph 안에서 fallbackDummy로 처리됨
    };

    fetchData();
  }, [params]);

  return (
    <S.Root>
      <S.HeaderSection>
        {/* 왼쪽: Title & Intro */}
        <S.TitleWrapper>
          <S.Title>Ad-hoc 분석 결과</S.Title>
          <S.Intro>입력하신 트랜잭션의 흐름을 분석합니다.</S.Intro>
        </S.TitleWrapper>

        {/* 오른쪽: SearchBar */}
        <SearchBar value={value} onChange={setValue} onSearch={handleSearch} />
      </S.HeaderSection>

      {/* 그래프 */}
      {graphData && (
        <Graph
          data={graphData}
          onNodeClick={undefined}
          fitViewOnMount={true}
        />
      )}
    </S.Root>
  );
}
