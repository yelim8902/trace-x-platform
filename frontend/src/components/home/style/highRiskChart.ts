import styled from "styled-components";

export const LeftChartSection = styled.div`
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px;
  border-right: 1px solid var(--secondary200, #343b4f);
`;

export const LeftHeader = styled.div`
  display: flex;
  flex-direction: column;
  gap: 20px;
  justify-content: space-between;
  align-items: flex-start;
`;

export const LeftTitle = styled.div`
  color: var(--primary400, #aeb9e1);
  font-size: 14px;
  font-weight: 500;
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

export const DateRange = styled.div`
  background: #0a1330;
  color: #aeb9e1;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 11px;
  margin-left: 8px;
`;

export const ChartPlaceholder = styled.div`
  display: flex;
  flex-direction: column;
  flex: 1;
  margin-top: 10px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #aeb9e1;
  font-size: 13px;
`;

export const YearSelect = styled.select`
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;

  background: #0a1330;
  color: #aeb9e1;
  border: 1px solid #2a3042;
  border-radius: 6px;
  padding: 6px 28px 6px 10px;
  font-size: 12px;
  font-weight: 500;
  margin-left: 8px;
  font-family: Pretendard, sans-serif;
  transition: all 0.2s ease;
  cursor: pointer !important;

  position: relative;
  z-index: 2;

  &:hover {
    background: #101a3d;
    border-color: #385de0;
  }

  &:focus {
    outline: none;
    border-color: #5cc8f8;
    box-shadow: 0 0 0 2px rgba(92, 200, 248, 0.2);
  }

  /* 커스텀 화살표 */
  background-image: url("data:image/svg+xml;charset=UTF-8,<svg width='10' height='7' viewBox='0 0 10 7' xmlns='http://www.w3.org/2000/svg'><path fill='%23AEB9E1' d='M1 1l4 4 4-4'/></svg>");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 10px 7px;

  /* 드롭다운 옵션 스타일 */
  option {
    background: #0a1330;
    color: #aeb9e1;
    padding: 6px 10px;
    font-size: 12px;
    font-weight: 500;
    border: none;
    cursor: pointer !important;

    &:hover {
      background: #121c4a;
      color: #fff;
    }

    &:checked {
      background: #385de0;
      color: #fff;
    }
  }
`;
