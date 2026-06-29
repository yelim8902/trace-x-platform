import Header from "@/components/layout/DemoHeader";
import * as S from "./styles";
import SendIcon from "@/assets/icon_send.svg";
import { useState } from "react";
import ReportSheet from "@/components/ReportSheet";
import DownloadIcon from "@/assets/icon_download.svg";

export default function DemoPage() {
  // state
  const [isCardOpened, setIsCardOpened] = useState(false);
  const [isChecked, setIsChecked] = useState(false);
  const [isDetailOpened, setIsDetailOpened] = useState(false);

  //handler
  function handleCheck() {
    setIsCardOpened((prev) => !prev);
    setIsChecked(true);
  }

  function handleDetailBtn() {
    setIsDetailOpened(true);
    setIsCardOpened(false);
  }

  return (
    <>
      <S.Home>
        <Header />
        <S.FormSection>
          <S.Body>
            <S.ToWrapper>
              <img src={SendIcon} alt="보내기아이콘" />
              <S.To>TO</S.To>
            </S.ToWrapper>
            <S.FormSection>
              <S.FormItem>
                <S.Label>네트워크</S.Label>
                <S.Input placeholder="선택" />
              </S.FormItem>
              <S.FormItem>
                <S.Label>주소</S.Label>
                <S.Input placeholder="주소를 입력해주세요." />
              </S.FormItem>
              <S.FormItem>
                <S.Label>금액</S.Label>
                <S.Input placeholder="금액을 입력해주세요." />
              </S.FormItem>
            </S.FormSection>
            <S.CheckButton $isChecked={isChecked} onClick={handleCheck}>
              {isChecked ? "검사 완료" : "검사"}
            </S.CheckButton>
            <S.SendButton $isChecked={isChecked}>송금하기</S.SendButton>
          </S.Body>
        </S.FormSection>
        {/* 오버레이 및 카드 */}
        <S.Overlay
          $isOpen={isCardOpened}
          onMouseDown={() => setIsCardOpened(false)} // 바깥 클릭 닫기
        />
        <S.Card $isOpen={isCardOpened} role="dialog" aria-modal="true">
          <S.CardHeader>검사 결과</S.CardHeader>
          <S.CardRow>
            <S.RedDot />
            <span>위험</span>
          </S.CardRow>
          <div
            style={{ display: "flex", gap: "10px", flexDirection: "column" }}
          >
            <S.CardBody>BRIDGE_TO_MIXER</S.CardBody>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                flexDirection: "column",
              }}
            >
              <S.CardBody>
                <div style={{ color: "black", fontSize: "15px" }}>홉 수</div>{" "}
                <div>2</div>
              </S.CardBody>
              <S.CardBody>
                <span style={{ color: "black", fontSize: "15px" }}>
                  시간 간격
                </span>{" "}
                <div>35m</div>
              </S.CardBody>
              <S.CardBody>
                <span style={{ color: "black", fontSize: "15px" }}>
                  금액 차이율
                </span>{" "}
                <div>0.18</div>
              </S.CardBody>
            </div>
            <div style={{ alignSelf: "flex-end" }}>
              <S.CardBody>v1.0.0 · 2025-09-08 14:30</S.CardBody>
            </div>
          </div>
          <S.CardActions>
            <S.DetailBtn onClick={handleDetailBtn}>자세히</S.DetailBtn>
          </S.CardActions>
        </S.Card>
        <ReportSheet
          isOpen={isDetailOpened}
          onClose={() => setIsCardOpened(false)}
          risk="danger"
          network="네트워크"
          address="주소주소주소주소"
          time="2025-09-08 14:30"
          evidences={["첫 번째 근거", "두 번째 근거", "세 번째 근거"]}
          onMouseDown={() => setIsDetailOpened(false)}
          DownloadIcon={DownloadIcon} // 또는 "/icons/download.svg"
        />
      </S.Home>
    </>
  );
}
