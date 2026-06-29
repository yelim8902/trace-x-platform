import styled from "styled-components";

export const Container = styled.div`
  height: 200px;
  display: flex;
  flex-direction: column;
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
  align-items: center;
  justify-content: center;
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
