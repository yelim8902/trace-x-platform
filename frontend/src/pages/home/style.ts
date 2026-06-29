import styled from "styled-components";

export const Root = styled.div`
  padding: 18px 50px;
  width: 100%;
  overflow-y: scroll;
`;

export const HeaderSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
`;

export const Title = styled.div`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 24px;
  font-style: normal;
  font-weight: 600;
  line-height: 32px;
`;

export const Intro = styled.div`
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 14px;
`;

export const ContentSection = styled.div`
  padding-top: 30px;
  padding-bottom: 40px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 17px;
`;

export const StatCardContainer = styled.div`
  display: flex;
  gap: 16px;
`;

export const MainContainer = styled.div`
  width: 100%;
  height: 550px;
  display: grid;
  grid-template-columns: 2fr 1fr;
  border-radius: 8px;
  border: 1px solid var(--secondary200, #343b4f);
  background: var(--neutral800, #060a1d);
`;

/* -------------------- 오른쪽 섹션 -------------------- */
export const RightPanel = styled.div`
  display: flex;
  flex-direction: column;
`;

export const RightTop = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
  border-bottom: 1px solid var(--secondary200, #343b4f);
`;

export const RightBottom = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 30px;
`;

export const RightHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

export const RiskValueRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  margin-left: 4px;
`;

export const RiskDiff = styled.div<{ $isUp: boolean }>`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;

  font-family: "Mona Sans";
  font-size: 11px;
  font-style: normal;
  font-weight: 300;
  line-height: 14px;
  color: ${({ $isUp }) =>
    $isUp ? "var(--red300, #FF5A65)" : "var(--skyblue300, #00D4FF)"};
  background-color: ${({ $isUp }) =>
    $isUp
      ? "var(--red20, rgba(255, 90, 101, 0.20))"
      : " var(--skyblue20, rgba(0, 212, 255, 0.20))"};
  border: ${({ $isUp }) =>
    $isUp
      ? "1px solid var(--red20, rgba(255, 90, 101, 0.20))"
      : "1px solid var(--skyblue20, rgba(0, 212, 255, 0.20))"};
  border-radius: 2px;
`;

export const ArrowIcon = styled.img`
  width: 8px;
  height: 8px;
`;

export const RightTitle = styled.div`
  color: var(--primary400, #aeb9e1);
  font-size: 14px;
  font-weight: 500;
`;

export const RiskValue = styled.div`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 24px;
  font-style: normal;
  font-weight: 600;
  line-height: 32px;
`;

export const ChartPlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  margin-top: 10px;
  border-radius: 8px;
  /* background: rgba(0, 0, 0, 0.15); */
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aeb9e1;
  font-size: 13px;
`;

export const LeftValue = styled.div`
  color: var(--white, #fff);
  font-size: 24px;
  font-weight: 600;
  margin-top: 4px;
`;

export const LegendWrapper = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
`;

export const LeftTitle = styled.div`
  color: var(--primary400, #aeb9e1);
  font-size: 13px;
  font-weight: 500;
`;

export const ChainLegendWrapper = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
`;

export const LegendDot = styled.div<{ color: string }>`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: ${({ color }) => color};
`;

export const LegendText = styled.span`
  color: var(--primary400, #aeb9e1);
  font-size: 12px;
`;

/* ===== 이상 패턴 섹션 ===== */
export const AnomalySection = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 24px;
  align-items: stretch;
`;

export const AnomalyLeft = styled.div``;
export const AnomalyRight = styled.div``;

export const AnomalyCard = styled.div`
  height: 100%;
  border-radius: 8px;
  border: 1px solid var(--secondary200, #343b4f);
  background: var(--neutral800, #060a1d);
  padding: 30px 32px;
  display: flex;
  flex-direction: column;
  gap: 16px;
`;

export const AnomalyHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

export const FilterButton = styled.div`
  background: #0a1330;
  color: #aeb9e1;
  font-size: 12px;
  border-radius: 4px;
  padding: 4px 10px;
  cursor: pointer;
`;

export const GaugePlaceholder = styled.div`
  height: 200px;
  /* background: rgba(0, 0, 0, 0.15); */
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aeb9e1;
  font-size: 13px;
`;

export const PatternList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
`;

export const PatternItem = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

export const PatternText = styled.span`
  color: var(--primary400, #aeb9e1);
  font-size: 13px;
  flex: 1;
  margin-left: 6px;
`;

export const PatternValue = styled.span`
  color: var(--white, #fff);
  font-size: 13px;
  font-weight: 500;
`;

/* ===== 테이블 ===== */
export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  color: #fff;
  font-size: 13px;
  text-align: left;
  margin-top: 8px;

  thead {
    color: #aeb9e1;
    font-weight: 400;
  }

  th,
  td {
    padding: 10px 8px;
  }
`;

// export const TableRow = styled.tr<{ $risk: string }>`
//   background: ${({ $risk }) =>
//     $risk === "위험"
//       ? "var(--point500, #7E2739)" // 위험일 때 붉은 배경
//       : "rgba(255, 255, 255, 0.03)"};
//   transition: background 0.2s ease;
//   cursor: pointer;

//   &:hover {
//     background: ${({ $risk }) =>
//       $risk === "위험"
//         ? "rgba(126, 39, 57, 0.85)"
//         : "rgba(255, 255, 255, 0.08)"};
//   }
// `;

export const TableRow = styled.tr`
  background: rgba(255, 255, 255, 0.03);
  transition: background 0.2s ease;
  cursor: pointer;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }
`;

export const RiskTag = styled.div<{ $level: "high" | "mid" | "low" }>`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;

  width: fit-content;
  min-width: 48px;
  height: 22px;
  padding: 2px 5px;

  border-radius: 6px;

  font-family: "Mona Sans";
  font-size: 10px;
  font-style: normal;
  font-weight: 500;
  line-height: 14px;

  /* 색상 공통 처리 */
  ${({ $level }) => {
    switch ($level) {
      case "high":
        return `
          color: #FF6B7F;
          background: rgba(212, 38, 73, 0.12);
          border: 1px solid rgba(212, 38, 73, 0.4);
        `;
      case "mid":
        return `
          color: #E8B54C;
          background: rgba(232, 181, 76, 0.12);
          border: 1px solid rgba(232, 181, 76, 0.4);
        `;
      case "low":
        return `
          color: #52FFA0;
          background: rgba(82, 255, 160, 0.12);
          border: 1px solid rgba(82, 255, 160, 0.4);
        `;
      default:
        return "";
    }
  }}

  /* 텍스트 앞의 ● 점 */
  &::before {
    content: "•";
    font-size: 14px;
    line-height: 1;
  }
`;

// export const GaugeWrapper = styled.div`
//   position: relative;
//   width: 200px;
//   height: 100px;
//   border-radius: 100px 100px 0 0;
//   overflow: hidden;
//   background: conic-gradient(
//     #7e2739 0deg 100deg,     /* 위험 */
//     #3c3ff2 100deg 210deg,   /* 경고 */
//     #5cc8f8 210deg 270deg,   /* 안전 */
//     #1a2238 270deg 360deg    /* 남은 영역 */
//   );

//   mask: radial-gradient(circle at 50% 100%, transparent 60%, black 61%);
//   -webkit-mask: radial-gradient(circle at 50% 100%, transparent 60%, black 61%);
// `;

export const GaugeContainer = styled.div`
  position: relative;
  width: 260px;
  height: 130px;
  display: flex;
  justify-content: center;
  align-items: flex-end;
  /* overflow: hidden; */
  border-radius: 260px 260px 0 0;
  /* background: #1a1f38; */
`;

// 반원 게이지
export const GaugeArc = styled.div<{
  $fanin: number;
  $peel: number;
  $scatter: number;
}>`
  position: absolute;
  z-index: 9999;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: ${({ $fanin, $peel, $scatter }) => {
    const total = $fanin + $peel + $scatter;
    const faninDeg = ($fanin / total) * 180;
    const peelDeg = ($peel / total) * 180;
    const scatterDeg = ($scatter / total) * 180;

    return `conic-gradient(
      from 270deg,
      #7e2739 0deg ${faninDeg}deg,
      #3c3ff2 ${faninDeg}deg ${faninDeg + peelDeg}deg,
      #5cc8f8 ${faninDeg + peelDeg}deg ${faninDeg + peelDeg + scatterDeg}deg,
      transparent ${faninDeg + peelDeg + scatterDeg}deg 360deg
    )`;
  }};

  /* 반원만 표시 */
  clip-path: inset(0 0 50% 0);

  mask: radial-gradient(circle at 50% 50%, black 60%, transparent 61%);
  -webkit-mask: radial-gradient(circle at 50% 50%, black 60%, transparent 61%);
`;

export const GaugeValue = styled.div`
  position: absolute;
  bottom: 32px;
  color: white;
  font-weight: 700;
  font-size: 32px;
`;

export const GaugeLabel = styled.div`
  position: absolute;
  bottom: 8px;
  color: #aeb9e1;
  font-size: 13px;
`;
