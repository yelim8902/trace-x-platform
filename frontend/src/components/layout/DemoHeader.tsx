import * as S from "./demoHeader.style";
import BackIcon from "@/assets/icon_next_lg.svg";
import AddIcon from "@/assets/icon_add.svg";

export default function Header() {
  return (
    <>
      <S.Header>
        <S.IconContainer>
          <S.Icon>
            <img src={BackIcon} alt="뒤로가기아이콘" />
          </S.Icon>
          <S.Icon>
            <img src={AddIcon} alt="뒤로가기아이콘" />
          </S.Icon>
        </S.IconContainer>
        <S.Title>송금</S.Title>
      </S.Header>
    </>
  );
}
