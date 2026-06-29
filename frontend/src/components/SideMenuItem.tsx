import * as S from "./style/sideMenu";
import { useLocation } from "react-router";

type SideMenuItemProps = {
  title: string;
  icon: string;
  activeIcon: string;
  path: string;
};

export function SideMenuItem({
  title,
  icon,
  activeIcon,
  path,
}: SideMenuItemProps) {
  const location = useLocation();
  const currentPath = location.pathname;

  const isActive =
    path === "/"
      ? currentPath === "/" // 홈은 정확히 "/"일 때만
      : currentPath.startsWith(path);

  return (
    <S.MenuItem to={path}>
      <S.MenuIcon src={isActive ? activeIcon : icon} alt={title} />
      <div>{title}</div>
    </S.MenuItem>
  );
}
