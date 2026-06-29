import { menu } from "@/data/menu";
import { SideMenuItem } from "../SideMenuItem";
import * as S from "./sideBar.style";

export default function SideBar() {
  return (
    <S.SideBar>
      <S.LogoContainer>Trace - X</S.LogoContainer>

      <S.SideMenuContainer>
        {menu.map((m) => (
          <SideMenuItem
            key={m.title}
            title={m.title}
            icon={m.svgPath}
            activeIcon={m.activeSvgPath}
            path={m.path}
          />
        ))}
      </S.SideMenuContainer>
    </S.SideBar>
  );
}
