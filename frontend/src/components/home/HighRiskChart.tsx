import { ResponsiveLine } from "@nivo/line";
import * as S from "./style/highRiskChart";

type TrendMap = Record<string, number>;

interface HighRiskChartProps {
  data?: TrendMap;
}

export default function HighRiskChart({ data }: HighRiskChartProps) {
  // 월 → "Jan" 변환
  const monthMap = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];

  /** 더미 12개월 데이터 */
  const fallbackDummy = [
    { x: "Jan", y: 5 },
    { x: "Feb", y: 12 },
    { x: "Mar", y: 18 },
    { x: "Apr", y: 22 },
    { x: "May", y: 31 },
    { x: "Jun", y: 27 },
    { x: "Jul", y: 35 },
    { x: "Aug", y: 49 },
    { x: "Sep", y: 40 },
    { x: "Oct", y: 33 },
    { x: "Nov", y: 22 },
    { x: "Dec", y: 15 },
  ];

  /** 데이터가 유효한지 검사 */
  const isValidData =
    data && typeof data === "object" && Object.keys(data).length > 0;

  /** 백엔드 데이터를 nivo 형식으로 변환 */
  let trendData: { x: string; y: number }[] = [];

  if (isValidData) {
      trendData = Object.entries(data)
        .map(([ym, value]) => {
          const parts = ym.split("-");
          const month = Number(parts[1]);

          // value가 0이어도 유효 → 삭제하면 안 됨!!
          if (!month || typeof value !== "number") return null;

          return {
            x: monthMap[month - 1],
            y: value,
          };
        })
        .filter(Boolean) as { x: string; y: number }[];


    // 월 순서대로 정렬
    trendData.sort((a, b) => monthMap.indexOf(a.x) - monthMap.indexOf(b.x));
  }

  /** trendData가 비어있으면 더미 사용 */
  const finalTrendData = trendData.length > 0 ? trendData : fallbackDummy;

  /** nivo data 구조 */
  const chartData = [
    {
      id: "고위험",
      color: "#D42649",
      data: finalTrendData,
    },
  ];

  return (
    <S.LeftChartSection>
      <S.LeftHeader>
        <div>
          <S.LeftTitle>고위험거래 추이</S.LeftTitle>
        </div>

        <S.LegendWrapper>
          <S.LegendDot color="#D42649" />
          <S.LegendText>고위험</S.LegendText>
        </S.LegendWrapper>
      </S.LeftHeader>

      <div style={{ height: "360px", marginTop: "20px" }}>
        <ResponsiveLine
          data={chartData}
          colors={(d) => d.color}
          margin={{ top: 30, right: 40, bottom: 50, left: 70 }}
          xScale={{ type: "point" }}
          yScale={{ type: "linear", min: 0, max: "auto" }}
          curve="monotoneX"
          enablePoints={false}
          enableArea
          areaOpacity={0.1}
          lineWidth={3}
          enableGridX={false}
          enableGridY
          axisBottom={{
            tickSize: 0,
            tickPadding: 10,
          }}
          axisLeft={{
            tickSize: 0,
            tickPadding: 10,
          }}
          useMesh
          enableSlices="x"
          sliceTooltip={({ slice }) => {
            const high = slice.points[0];

            return (
              <div
                style={{
                  background: "rgba(10, 15, 35, 0.9)",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  border: "1px solid #2a3042",
                  color: "#fff",
                  fontFamily: "Pretendard",
                  fontSize: "13px",
                }}
              >
                <div style={{ marginBottom: 6, fontWeight: 500 }}>
                  {high.data.x}
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: "#D42649",
                      flexShrink: 0,
                    }}
                  />
                  <strong style={{ color: "#D42649" }}>{high.data.y}</strong>
                </div>
              </div>
            );
          }}
          theme={{
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
              line: { stroke: "#2a3042", strokeWidth: 0.5 },
            },
          }}
        />
      </div>
    </S.LeftChartSection>
  );
}
