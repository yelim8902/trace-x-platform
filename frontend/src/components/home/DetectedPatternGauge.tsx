import { ResponsivePie } from "@nivo/pie";

export default function DetectedPatternGauge() {
  // 📊 더미 데이터 (게이지 섹션별 값)
  const data = [
    { id: "high", label: "High Risk", value: 60, color: "#D42649" },
    { id: "medium", label: "Medium", value: 25, color: "#3845F7" },
    { id: "low", label: "Low", value: 15, color: "#5CC8F8" },
  ];

  return (
    <div
      style={{
        width: "100%",
        height: "200px",
        position: "relative",
        transform: "translateY(20%)",
      }}
    >
      <ResponsivePie
        data={data}
        startAngle={-90}
        endAngle={90}
        sortByValue
        padAngle={2}
        innerRadius={0.9}
        cornerRadius={0}
        activeOuterRadiusOffset={0}
        enableArcLinkLabels={false}
        enableArcLabels={false}
        colors={({ data }) => data.color}
        borderWidth={0}
        animate
        motionConfig="gentle"
        theme={{
          background: "transparent",
        }}
      />

      {/* 가운데 텍스트 */}
      <div
        style={{
          position: "absolute",
          top: "60%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          textAlign: "center",
          color: "#FFFFFF",
          fontFamily: "Pretendard",
        }}
      >
        <div style={{ fontSize: "28px", fontWeight: 600 }}>23,648</div>
        <div style={{ fontSize: "13px", color: "#AEB9E1", marginTop: "4px" }}>
          탐지된 이상 패턴 수
        </div>
      </div>
    </div>
  );
}
