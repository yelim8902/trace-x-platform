import icon_dashboard from "@/assets/icon_dashboard.svg";
import icon_active_dashboard from "@/assets/icon_active_dashboard.svg";
import icon_live_detection from "@/assets/icon_live_detection.svg";
import icon_active_live_detection from "@/assets/icon_active_live_detection.svg";
import icon_adhoc from "@/assets/icon_adhoc.svg";
import icon_active_adhoc from "@/assets/icon_active_adhoc.svg";
import icon_report from "@/assets/icon_report.svg";
import icon_active_report from "@/assets/icon_active_report.svg";
import icon_case from "@/assets/icon_case.svg";
import icon_active_case from "@/assets/icon_active_case.svg";

export const menu = [
  {
    title: "대시보드",
    engTitle: "Dashboard",
    intro: "블록체인 인텔리전스 및 리스크 분석 플랫폼",
    svgPath: icon_dashboard,
    activeSvgPath: icon_active_dashboard,
    path: "/",
  },
  {
    title: "실시간 탐지",
    engTitle: "Live Detection",
    intro: "실시간 탐지",
    svgPath: icon_live_detection,
    activeSvgPath: icon_active_live_detection,
    path: "/live-detection",
  },
  {
    title: "수동 탐지",
    engTitle: "Ad-hoc Detection",
    intro: "수동 탐지",
    svgPath: icon_adhoc,
    activeSvgPath: icon_active_adhoc,
    path: "/adhoc",
  },
  {
    title: "의심거래 보고서",
    engTitle: "SRT Reports",
    intro: "의심거래 보고서",
    svgPath: icon_report,
    activeSvgPath: icon_active_report,
    path: "/report",
  },
  {
    title: "사건 관리",
    engTitle: "Watchlist",
    intro: "사건 관리",
    svgPath: icon_case,
    activeSvgPath: icon_active_case,
    path: "/case",
  },
];
