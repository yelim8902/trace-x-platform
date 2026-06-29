import styled from "styled-components";

export const Root = styled.div`
  padding: 18px 50px;
  width: 100%;
  overflow-y: scroll;
`;

export const HeaderSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 30px;
`;

export const Title = styled.div`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 24px;
  font-style: normal;
  font-weight: 600;
  line-height: 32px;
`;

export const Intro = styled.div`
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 12px;
  font-style: normal;
  font-weight: 400;
  line-height: 14px;
`;

// 검색 영역
export const SearchSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-bottom: 40px;
`;

export const ModeSelector = styled.div`
  display: flex;
  gap: 16px;
`;

export const ModeButton = styled.button<{ $active: boolean }>`
  padding: 10px 20px;
  background: ${(props) =>
    props.$active ? "var(--red300, #1e1e1e)" : "var(--neutral800, #060a1d)"};
  color: var(--white, #fff);
  border: 1px solid
    ${(props) =>
      props.$active
        ? "var(--red300, #1e1e1e)"
        : "var(--secondary200, #343b4f)"};
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: "Mona Sans";

  &:hover {
    background: ${(props) =>
      props.$active ? "#1e1e1e" : "var(--secondary200, #343b4f)"};
    border-color: ${(props) =>
      props.$active
        ? "var(--red300, #1e1e1e)"
        : "var(--secondary200, #343b4f)"};
  }
`;

export const ChainSelect = styled.select`
  padding: 14px 18px;
  background: #1e1e1e;
  color: var(--white, #fff);
  border: 1px solid #444;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  min-width: 140px;
  transition: all 0.2s ease;
  font-family: "Mona Sans";

  &:focus {
    outline: none;
    border-color: var(--primary500, #7c8dd8);
  }

  option {
    background: var(--neutral800, #060a1d);
    color: var(--white, #fff);
  }
`;

export const AnalyzeButton = styled.button`
  padding: 14px 32px;
  background: var(--point, #ff5a65);
  color: var(--white, #fff);
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  font-family: "Mona Sans";

  &:hover:not(:disabled) {
    background: #ff6b7f;
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const TestAddressHint = styled.div`
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 13px;
  color: var(--primary400, #aeb9e1);
  margin-top: 12px;
`;

export const ErrorMessage = styled.div`
  padding: 16px 20px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 14px;
  margin-bottom: 24px;
`;

export const EmptyMessage = styled.div`
  text-align: center;
  padding: 80px 20px;
  color: var(--primary400, #aeb9e1);
  font-size: 16px;
`;

export const LoadingMessage = styled.div`
  text-align: center;
  padding: 40px 20px;
  color: var(--primary400, #aeb9e1);
  font-size: 14px;
`;

// 그래프 + 사이드바 레이아웃
export const ContentLayout = styled.div`
  display: flex;
  gap: 24px;
  align-items: flex-start;
`;

export const GraphSection = styled.div<{ $hasDetails: boolean }>`
  flex: ${(props) => (props.$hasDetails ? "1" : "1")};
  transition: flex 0.3s ease;
`;

// 그래프 컨트롤 바
export const GraphControlBar = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding: 16px 20px;
  background: var(--neutral800, #060a1d);
  border: 1px solid var(--secondary200, #343b4f);
  border-radius: 8px;
`;

export const GraphInfo = styled.div`
  color: var(--primary400, #aeb9e1);
  font-size: 14px;
  font-weight: 600;
`;

export const GraphButtonGroup = styled.div`
  display: flex;
  gap: 12px;
`;

export const ExpandButton = styled.button<{ primary?: boolean }>`
  position: relative;
  padding: 10px 24px;
  background: ${(props) =>
    props.primary ? "var(--red300, #FF5A65)" : "var(--neutral800, #060a1d)"};
  color: var(--white, #fff);
  border: 1px solid
    ${(props) =>
      props.primary
        ? "var(--red300, #FF5A65)"
        : "var(--secondary200, #343b4f)"};
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-family: "Mona Sans";

  &:hover:not(:disabled) {
    background: ${(props) =>
      props.primary ? "#FF6B7F" : "var(--secondary200, #343b4f)"};
    border-color: ${(props) =>
      props.primary
        ? "var(--red300, #FF5A65)"
        : "var(--secondary200, #343b4f)"};
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`;

export const ButtonHint = styled.span`
  font-size: 10px;
  font-weight: 400;
  color: var(--primary400, #aeb9e1);
  opacity: 0.8;
`;

// 사이드바 (노드 상세 정보)
export const DetailsSidebar = styled.div`
  width: 400px;
  min-width: 400px;
  height: 700px; /* 그래프와 동일한 높이 */
  overflow-y: auto;
  background: var(--neutral800, #060a1d);
  border: 1px solid var(--secondary200, #343b4f);
  border-radius: 8px;
  padding: 24px;

  /* 스크롤바 스타일 */
  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(31, 41, 55, 0.5);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.5);
    border-radius: 4px;

    &:hover {
      background: rgba(59, 130, 246, 0.7);
    }
  }
`;

export const SidebarHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--secondary200, #343b4f);
`;

export const SidebarTitle = styled.h3`
  color: var(--white, #fff);
  font-size: 18px;
  font-weight: 600;
  margin: 0;
  font-family: "Mona Sans";
`;

export const CloseButton = styled.button`
  background: rgba(239, 68, 68, 0.2);
  color: #fca5a5;
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
  font-weight: 700;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(239, 68, 68, 0.3);
    border-color: #ef4444;
  }
`;

export const DetailSection = styled.div`
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
`;

export const DetailLabel = styled.div`
  color: var(--primary400, #aeb9e1);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  font-family: "Mona Sans";
`;

export const DetailValue = styled.div`
  color: var(--white, #fff);
  font-size: 14px;
  line-height: 1.6;
  font-family: "Mona Sans";
`;

export const RiskScore = styled.div`
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 8px;
`;

export const RiskLevel = styled.div`
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.5px;
`;

export const TagContainer = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
`;

export const RiskTag = styled.span`
  padding: 6px 12px;
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
`;

export const RuleList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

export const RuleItem = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--secondary200, #343b4f);
  border-radius: 8px;
  color: var(--white, #fff);
  font-size: 13px;
  font-family: "Mona Sans";

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }
`;

// 기존 컴포넌트 (호환성 유지)
export const CenterBox = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
`;

export const TitleWrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
`;
