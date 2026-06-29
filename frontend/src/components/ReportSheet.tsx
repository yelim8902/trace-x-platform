import * as S from "./reportSheet.style";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  risk: S.Risk; // "danger" | "warning" | "safe"
  network: string;
  address: string;
  time: string; // 포맷된 문자열
  evidences: string[]; // 근거 리스트
  onMouseDown: () => void;
  DownloadIcon?: React.ComponentType | string; // svg 컴포넌트 or 이미지 경로
};

export default function ReportSheet({
  isOpen,
  onClose,
  risk,
  onMouseDown,
  DownloadIcon,
}: Props) {
  const Icon = DownloadIcon as any;

  // 오버레이 클릭으로 닫기
  const handleOverlay = () => onClose();

  return (
    <>
      <S.Overlay
        $isOpen={isOpen}
        onClick={handleOverlay}
        onMouseDown={onMouseDown}
      />
      <S.Sheet
        $isOpen={isOpen}
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
      >
        <S.Title>검사 결과 리포트</S.Title>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <S.ReasonTitle>BRIDGE_TO_MIXER</S.ReasonTitle>
          <S.RiskPill risk={risk}>
            {risk === "danger" ? "위험" : risk === "warning" ? "주의" : "정상"}
          </S.RiskPill>
        </div>

        <S.Table>
          <S.ItemWrapper>
            <S.Key>bridge_out</S.Key>
            <S.ValueContainer>
              <S.Val>0x....a1</S.Val>
              <S.Val>USDT</S.Val>
              <S.Val>9,980</S.Val>
              <S.Val>23:10</S.Val>
            </S.ValueContainer>
          </S.ItemWrapper>
          <S.ItemWrapper>
            <S.Key>mixer_deposit</S.Key>
            <S.ValueContainer>
              <S.Val>0x....b2</S.Val>
              <S.Val>USDT</S.Val>
              <S.Val>9,962</S.Val>
              <S.Val>23:45</S.Val>
            </S.ValueContainer>
          </S.ItemWrapper>
          <div style={{ paddingTop: "40px" }} />
          <S.ItemWrapper>
            <S.Key>홉 수</S.Key>
            <S.Val>
              <span style={{ color: "#ffb535" }}>2 ≤ 2</span>
            </S.Val>
          </S.ItemWrapper>
          <S.ItemWrapper>
            <S.Key>시간 간격</S.Key>
            <S.Val>
              <span style={{ color: "#21B400" }}>35m ≤ 45m</span>
            </S.Val>
          </S.ItemWrapper>

          <S.ItemWrapper>
            <S.Key>금액 차이율</S.Key>
            <S.Val>
              <span style={{ color: "#21B400" }}>0.18 ≤ 1.00</span>
            </S.Val>
          </S.ItemWrapper>

          <div style={{ paddingTop: "40px" }} />
          <S.ItemWrapper>
            <S.Key>시간</S.Key>
            <S.Val>2025-09-08 14:30</S.Val>
          </S.ItemWrapper>
          <S.ItemWrapper>
            <S.Key>정책</S.Key>
            <S.Val>v1.0.0</S.Val>
          </S.ItemWrapper>
        </S.Table>

        <S.Footer>
          <S.DownloadBtn>
            {DownloadIcon &&
              (typeof DownloadIcon === "string" ? (
                <img src={DownloadIcon} alt="다운로드" />
              ) : (
                <Icon />
              ))}
            다운로드
          </S.DownloadBtn>
        </S.Footer>
      </S.Sheet>
    </>
  );
}
