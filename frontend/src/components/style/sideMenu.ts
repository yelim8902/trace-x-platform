import { NavLink } from "react-router";
import styled from "styled-components";

export const SideMenuContainer = styled.div`
  width: 100%;
`;

export const MenuItem = styled(NavLink)`
  border-radius: 4px;
  color: var(--primary400, #aeb9e1);

  display: flex;
  gap: 6px;

  font-feature-settings: "liga" off, "clig" off;
  font-family: "Mona Sans";
  font-size: 14px;
  font-style: normal;
  font-weight: 500;
  line-height: 14px;
  width: 100%;
  padding: 14px 0;
  border-radius: 4px;
  text-decoration: none;

  &.active {
    background: var(--primary700);
    padding: 14px 18.5px;
    color: var(--point600, #d42649);
    border-left: 3px solid var(--point600, #d42649);
  }
`;

export const MenuIcon = styled.img`
  width: 18px;
  height: 18px;
`;
