import { ResponsiveBar } from "@nivo/bar";
import * as S from "./style/highRiskByEachChain";

interface HighRiskByEachChainProps {
  data?: Record<string, Record<string, number>>;
  // ex) { "1~2월": { "Ethereum": 5, ... } }
}

export default function HighRiskByEachChain({
  data,
}: HighRiskByEachChainProps) {
  // 백엔드 → 차트 데이터 변환
  function transformChainData(raw: Record<string, Record<string, number>>) {
    const monthMap: Record<string, string> = {
      "1~2월": "1–2",
      "3~4월": "3–4",
      "5~6월": "5–6",
      "7~8월": "7–8",
      "9~10월": "9–10",
      "11~12월": "11–12",
    };

    return Object.entries(raw).map(([period, chains]) => ({
      month: monthMap[period] ?? period,
      ...chains,
    }));
  }
  // data가 비어있거나 잘못된 구조면 더미데이터 사용
  const isEmptyData = !data || Object.keys(data).length === 0;

  // 데이터가 없으면 더미 데이터 사용
  const chartData = !isEmptyData
    ? transformChainData(data)
    : [
        {
          month: "1-2",
          Ethereum: 80,
          "Arbitrum One": 70,
          Base: 65,
          Solana: 55,
        },
        {
          month: "3-4",
          Ethereum: 60,
          "Arbitrum One": 50,
          Base: 45,
          Solana: 35,
        },
        {
          month: "5-6",
          Ethereum: 90,
          "Arbitrum One": 75,
          Base: 70,
          Solana: 60,
        },
        {
          month: "7-8",
          Ethereum: 70,
          "Arbitrum One": 85,
          Base: 50,
          Solana: 40,
        },
        {
          month: "9-10",
          Ethereum: 100,
          "Arbitrum One": 95,
          Base: 80,
          Solana: 75,
        },
        {
          month: "11-12",
          Ethereum: 85,
          "Arbitrum One": 60,
          Base: 55,
          Solana: 50,
        },
      ];

  // keys: 백엔드 체인명 자동 추출
  const keys = Object.keys(chartData[0]).filter((key) => key !== "month");

  const colors = ["#D64A4A", "#5CC8F8", "#ffe641", "#d5a2ff"];

  return (
    <>
      <S.Container>
        <ResponsiveBar
          data={chartData}
          keys={keys}
          indexBy="month"
          margin={{ top: 20, right: 30, bottom: 70, left: 50 }}
          padding={0.3}
          groupMode="grouped"
          colors={colors}
          enableLabel={false}
          borderRadius={2}
          axisLeft={null}
          axisBottom={{
            tickSize: 0,
            tickPadding: 10,
            tickRotation: 0,
          }}
          tooltip={({ id, value }) => (
            <div
              style={{
                padding: "8px 12px",
                background: "rgba(10,15,35,0.9)",
                borderRadius: "8px",
                border: "1px solid #2a3042",
                color: "#fff",
                fontFamily: "Pretendard",
                fontSize: 12,
              }}
            >
              <strong>{id}</strong>
              <div style={{ marginTop: 4, color: "#AEB9E1" }}>{value}</div>
            </div>
          )}
          theme={{
            background: "transparent",
            axis: {
              ticks: {
                text: {
                  fill: "#AEB9E1",
                  fontSize: 12,
                  fontFamily: "Pretendard",
                },
              },
            },
            grid: {
              line: {
                stroke: "#2a3042",
                strokeWidth: 0.5,
              },
            },
          }}
        />
      </S.Container>

      {/* 범례 */}
      <S.ChainLegendWrapper>
        {keys.map((chain, i) => (
          <S.LegendWrapper key={chain}>
            <S.LegendDot color={colors[i]} />
            <S.LegendText>{chain}</S.LegendText>
          </S.LegendWrapper>
        ))}
      </S.ChainLegendWrapper>
    </>
  );
}
