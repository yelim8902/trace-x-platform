import { Outlet } from "react-router";
import styled from "styled-components";

const Wrapper = styled.div`
  width: 100%;
  height: 100%;
  padding: 40px 60px;
  background: #0b1120;
`;

export default function AdhocLayout() {
  return (
    <Wrapper>
      <Outlet />
    </Wrapper>
  );
}
