import styled from "styled-components";

export const SideBar = styled.div`
  width: 18%;
  background: var(--primary800);
  box-shadow: 0 8px 28px 0 rgba(1, 5, 17, 0.3);
  padding: 0 28px;

  @media (max-width: 1000px) {
    display: none;
  }
`;

export const LogoContainer = styled.div`
  display: flex;
  gap: 5px;
  align-items: center;
  margin-top: 38px;
  margin-bottom: 56px;
  padding-left: 20px;

  color: var(--white, #fff);
  font-feature-settings: "liga" off, "clig" off;
  font-family: "Mona Sans";
  font-size: 20px;
  font-style: normal;
  font-weight: 600;
  line-height: 22px; /* 110% */
`;

export const SideMenuContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;
