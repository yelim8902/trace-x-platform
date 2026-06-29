import styled, { keyframes } from "styled-components";

export type Risk = "danger" | "warning" | "safe";

export const Overlay = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  border-radius: 12px;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  opacity: ${({ $isOpen }) => ($isOpen ? 1 : 0)};
  pointer-events: ${({ $isOpen }) => ($isOpen ? "auto" : "none")};
  transition: opacity 0.18s ease;
  z-index: 10;
`;

const pop = keyframes`
  from { opacity: 0; transform: translateX(-50%) translateY(8px) scale(.98); }
  to   { opacity: 1; transform: translateX(-50%) translateY(0)   scale(1); }
`;

export const Sheet = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  width: calc(100% - 32px);
  left: 50%;
  bottom: -12px;
  height: 430px;
  background: #fff;
  border-radius: 18px;
  padding: 20px 16px 16px;
  z-index: 11;
  display: ${({ $isOpen }) => ($isOpen ? "flex" : "none")};
  flex-direction: ${({ $isOpen }) => ($isOpen ? "column" : "")};
  gap: ${({ $isOpen }) => ($isOpen ? "15px" : "")};
  animation: ${pop} 0.18s ease both;
`;

export const Header = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
`;

export const Title = styled.h3`
  font-size: 16px;
  font-weight: 800;
`;
export const ReasonTitle = styled.div`
  color: #40454a;
  font-size: 18px;
  font-weight: 600;
  line-height: 150%;
  letter-spacing: 0.072px;
`;

export const RiskPill = styled.span<{ risk: Risk }>`
  border-radius: 62.5px;
  border: 2px solid #f53e55;
  align-self: flex-end;
  width: 65px;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #ffe9eb;

  color: #f53e55;
  text-align: center;
  font-size: 15px;
  font-weight: 500;
  line-height: 125px;
`;

export const Table = styled.dl`
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
  font-size: 14px;
  margin: 12px 0 16px;
  width: 100%;
`;

export const ItemWrapper = styled.div`
  display: flex;
  justify-content: space-between;
  width: 100%;
`;

export const Key = styled.div`
  color: #15181c;
  font-weight: 700;
`;

export const ValueContainer = styled.div`
  display: flex;
  gap: 10px;
`;

export const Val = styled.div`
  color: #60656b;
  margin: 0;
`;

export const Evidence = styled.ul`
  list-style: none;
  padding: 0;
  margin: 6px 0 0;
  color: #60656b;
  font-size: 14px;

  li + li {
    margin-top: 6px;
  }
`;

export const Footer = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
  margin-bottom: 10px;
`;

export const DownloadBtn = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 40px;
  padding: 0 10px;
  border-radius: 12px;
  border: 1.5px solid #1f2329;
  background: #fff;
  font-weight: 700;
  cursor: pointer;

  svg,
  img {
    width: 18px;
    height: 18px;
  }
`;
