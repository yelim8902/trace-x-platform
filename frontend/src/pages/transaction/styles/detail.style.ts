import styled from "styled-components";

export const Root = styled.div`
  flex: 1;
  background: linear-gradient(180deg, #393b54 52.86%, #292a3b 100%);
  padding: 20px;
  padding-top: 0;
  display: flex;
  flex-direction: column;
`;

export const HeaderSection = styled.div`
  display: flex;
  justify-content: space-between;
  padding: 15px 0;
`;

export const HeaderTitleContainer = styled.div`
  display: flex;
  gap: 9px;
  justify-content: center;
  align-items: center;

  color: white;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.4px;
`;

export const TxHashBox = styled.div`
  border-radius: 20px;
  padding: 15px 22px;
  background: #161831;

  color: #373a5e;
  font-size: 12px;
  font-weight: 700;
`;

export const MainSection = styled.div`
  margin-top: 20px;
  flex: 1;
  border-radius: 4px;
  background: #161831;
  box-shadow: 4px 4px 8px 2px #1f213b;
`;
