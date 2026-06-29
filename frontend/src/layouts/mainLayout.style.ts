import styled from "styled-components";

export const Root = styled.div`
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--primary800, #081028);
`;

export const Content = styled.div`
  display: flex;
  flex: 1;
  overflow: hidden; /* 전체는 스크롤 금지 */
`;

export const SidebarWrapper = styled.div`
  width: 240px;
  height: 100vh;
  flex-shrink: 0;
  background: #0a1330;
  position: sticky;
  top: 0;
  overflow: hidden;
`;

export const MainArea = styled.div`
  flex: 1;
  height: 100vh;
  overflow-y: auto;
  padding: 0;
`;
