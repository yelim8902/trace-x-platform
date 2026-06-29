// MainLayout.tsx
import { Outlet, useLocation } from "react-router";
import * as S from "./mainLayout.style";
import SideBar from "@/components/layout/SideBar";
import { menu } from "@/data/menu";

export default function MainLayout() {
  const location = useLocation();
  const currentPath = location.pathname;

  // 현재 경로와 일치하는 메뉴 객체 찾기
  // 1. 먼저 path 완전 일치하는 메뉴 찾기
  let currentMenu =
    menu.find((m) => m.path === currentPath) ??
    // 2. 없으면 "/" 제외하고 startsWith 로 찾기
    menu.find((m) => m.path !== "/" && currentPath.startsWith(m.path)) ??
    // 3. 그래도 없으면 기본값: 대시보드
    menu[0];
  const contextValue = {
    title: currentMenu?.engTitle ?? "",
    intro: currentMenu?.intro ?? "",
  };

  return (
    <S.Root>
      <S.Content>
        <SideBar />
        <Outlet context={contextValue} />
      </S.Content>
    </S.Root>
  );
}
