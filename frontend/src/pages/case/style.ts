import styled from "styled-components";

export const Root = styled.div`
  padding: 18px 50px;
  width: 100%;
  height: 100%;              /* 부모(MainLayout Content)가 주는 높이 꽉 채움 */
  display: flex;             /* flex 컨테이너 */
  flex-direction: column;
  gap: 16px;
  overflow: hidden;          /* 전체는 숨기고, 아래 ListSection만 스크롤 */
`;

export const HeaderSection = styled.div`
  flex-shrink: 0; 
  display: flex;
  flex-direction: column;
  gap: 5px;
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

export const ListSection = styled.div`
  flex: 1;                  
  overflow-y: auto;          
  padding-right: 6px;
  
  display: flex;
  flex-direction: column;
  gap: 18px;

  /* 스크롤바 스타일 */
  &::-webkit-scrollbar {
    width: 4px;
  }
  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.2);
    border-radius: 6px;
  }
`;
