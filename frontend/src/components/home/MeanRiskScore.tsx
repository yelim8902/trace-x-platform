import { ResponsiveLine } from "@nivo/line";

interface MeanRiskScoreProps {
  data?: Record<string, number>;
}

export default function MeanRiskScore({ data }: MeanRiskScoreProps) {
  // HH → "2PM" 변환
  function formatHour(hh: number) {
    const hour = hh % 24;
    const isPM = hour >= 12;
    const display =
      hour === 0 ? 12 : hour === 12 ? 12 : hour > 12 ? hour - 12 : hour;

    return `${display}${isPM ? "PM" : "AM"}`;
  }

  // -------------------------------
  // fallback dummy
  // -------------------------------
  const fallback = [
    { x: 0, y: 2.1, xFormatted: "12AM", yFormatted: "2.1" },
    { x: 2, y: 2.5, xFormatted: "2AM", yFormatted: "2.5" },
    { x: 4, y: 1.8, xFormatted: "4AM", yFormatted: "1.8" },
    { x: 6, y: 2.2, xFormatted: "6AM", yFormatted: "2.2" },
    { x: 8, y: 1.9, xFormatted: "8AM", yFormatted: "1.9" },
    { x: 10, y: 2.3, xFormatted: "10AM", yFormatted: "2.3" },
    { x: 12, y: 3.4, xFormatted: "12PM", yFormatted: "3.4" },
    { x: 14, y: 2.8, xFormatted: "2PM", yFormatted: "2.8" },
    { x: 16, y: 3.9, xFormatted: "4PM", yFormatted: "3.9" },
    { x: 18, y: 2.7, xFormatted: "6PM", yFormatted: "2.7" },
    { x: 20, y: 3.2, xFormatted: "8PM", yFormatted: "3.2" },
    { x: 22, y: 2.4, xFormatted: "10PM", yFormatted: "2.4" },
  ];

  // -------------------------------
  // 타입 가드 선언
  // -------------------------------
  const isValidItem = (
    item: any
  ): item is { x: number; y: number; xFormatted: string; yFormatted: string } =>
    item &&
    typeof item === "object" &&
    typeof item.x === "number" &&
    typeof item.y === "number" &&
    typeof item.xFormatted === "string" &&
    typeof item.yFormatted === "string";

  // -------------------------------
  // data 유효성 검사 + 변환
  // -------------------------------
  const isValid =
    data &&
    Object.keys(data).length > 0 &&
    Object.values(data).some((v) => typeof v === "number");

  let converted: {
    x: number;
    y: number;
    xFormatted: string;
    yFormatted: string;
  }[] = [];

  if (isValid) {
    converted = Object.entries(data!)
      .map(([hourStr, score]) => {
        const hour = Number(hourStr);
        if (isNaN(hour)) return null;
        if (typeof score !== "number") return null;

        return {
          x: hour,
          y: score,
          xFormatted: formatHour(hour),
          yFormatted: String(score),
        };
      })
      .filter(isValidItem); // << 타입 가드로 null 제거 완전 인정됨

    // 정렬
    converted.sort((a, b) => a.x - b.x);
  }

  // -------------------------------
  // 최종 데이터 선택
  // -------------------------------
  const finalData = converted.length > 0 ? converted : fallback;

  const chartData = [
    {
      id: "Mean Risk Score",
      color: "#D42649",
      data: finalData,
    },
  ];

  return (
    <div style={{ width: "100%", height: "120px" }}>
      <ResponsiveLine
        data={chartData}
        useMesh={true}
        margin={{ top: 10, right: 20, bottom: 30, left: 20 }}
        xScale={{ type: "linear" }}
        yScale={{ type: "linear", min: "auto", max: "auto" }}
        axisLeft={null}
        axisTop={null}
        axisRight={null}
        axisBottom={{
          tickSize: 0,
          tickPadding: 8,
          tickRotation: 0,
          format: (v) => formatHour(v as number),
          tickValues: [0, 8, 16, 22],
        }}
        enablePoints={false}
        enableGridX={false}
        enableGridY={false}
        colors={["#D42649"]}
        lineWidth={2}
        curve="monotoneX"
        theme={{
          axis: {
            ticks: {
              text: {
                fill: "#AEB9E1",
                fontSize: 11,
                fontFamily: "Pretendard",
              },
            },
          },
          tooltip: {
            container: {
              background: "rgba(10,15,35,0.9)",
              border: "1px solid #2a3042",
              padding: "8px 12px",
              borderRadius: "8px",
              color: "#fff",
              fontFamily: "Pretendard",
              fontSize: 12,
            },
          },
        }}
        tooltip={({ point }) => (
          <div>
            <strong>{formatHour(point.data.x as number)}</strong>
            <div style={{ color: "#D42649", marginTop: 4 }}>{point.data.y}</div>
          </div>
        )}
      />
    </div>
  );
}
