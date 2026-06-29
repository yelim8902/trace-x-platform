import styled, { css } from "styled-components";

export const Home = styled.div`
  position: relative;
  width: 320px;
  height: 680px;
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
  padding: 0 20px;
`;

export const Body = styled.div`
  padding: 0 20px;
  height: 520px;
  display: flex;
  flex-direction: column;
`;

export const ToWrapper = styled.div`
  display: flex;
  gap: 5px;
  margin: 45px 0;
`;

export const To = styled.div`
  color: #0e0f15;
  font-size: 18px;
  font-weight: 700;
  line-height: 150%;
  letter-spacing: 0.84px;
`;

export const FormSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 40px;
`;

export const FormItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 5px;
`;

export const Label = styled.div`
  color: #000;
  font-size: 14px;
  font-weight: 700;
  line-height: 150%;
  letter-spacing: 0.84px;
`;

export const Select = styled.select`
  width: 100%;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background-color: #f9f9ff;
  font-size: 14px;
`;

export const Input = styled.input`
  padding: 12px 16px;
  border-radius: 4px;
  background: #f0f4fe;

  font-size: 14px;
  font-weight: 400;
  letter-spacing: 0.7px;

  &::placeholder {
    color: #939da7;
  }
`;

export const CheckButton = styled.div<{ $isChecked: boolean }>`
  width: 80px;
  height: 20px;
  padding: 10px 0;
  border-radius: 16px;

  display: flex;
  justify-content: center;
  align-items: center;
  align-self: flex-end;

  ${({ $isChecked }) =>
    $isChecked
      ? css`
          border: 2px solid #939da7;
          background: transparent;
          color: #939da7;
        `
      : css`
          background: #527cf2;
          border: none;
          color: white;
          cursor: pointer;
        `}

  font-size: 14px;
  font-weight: 600;
  line-height: 100%;

  &:hover {
  }
`;

export const SendButton = styled.div<{ $isChecked: boolean }>`
  width: 100%;
  border-radius: 8px;
  border: 2px solid #939da7;
  margin-top: auto;
  padding: 12px 0;

  ${({ $isChecked }) =>
    $isChecked
      ? css`
          background: #527cf2;
          color: white;
          cursor: pointer;
          border: none;
        `
      : css`
          border: 2px solid #939da7;
          color: #939da7;
        `}

  font-size: 14px;
  font-weight: 600;
  line-height: 150%;
  letter-spacing: 0.96px;

  text-align: center;

  &:hover {
  }
`;

/* ===== 오버레이 & 카드 ===== */
export const Overlay = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.35);
  opacity: ${({ $isOpen }) => ($isOpen ? 1 : 0)};
  pointer-events: ${({ $isOpen }) => ($isOpen ? "auto" : "none")};
  transition: opacity 0.18s ease;
  z-index: 999;
`;

export const Card = styled.div<{ $isOpen: boolean }>`
  position: absolute;
  bottom: 60px;
  width: 300px;
  height: 270px;
  left: 50%;
  transform: translateX(-50%);
  border-radius: 20px;
  background: #fcf3f3;
  flex-direction: column;

  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
  padding: 20px;
  z-index: 1000;
  display: ${({ $isOpen }) => ($isOpen ? "flex" : "none")};
`;

export const CardHeader = styled.div`
  font-weight: 700;
  margin-bottom: 8px;
`;

export const CardRow = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  padding: 8px 0;

  color: #ca3b40;
  font-size: 18px;
  font-weight: 700;
  line-height: 150%;
`;

export const RedDot = styled.span`
  width: 18px;
  height: 18px;
  background: #db4b53;
  border-radius: 50%;
  display: inline-block;
`;

export const CardBody = styled.p`
  color: #40454a;
  font-size: 14px;
  font-weight: 600;
  line-height: 150%;
  letter-spacing: 0.06px;
  display: flex;
  justify-content: space-between;
`;

export const ReasonTitle = styled.div`
  color: #40454a;
  font-size: 18px;
  font-weight: 600;
  line-height: 150%;
  letter-spacing: 0.072px;
`;

export const CardActions = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
`;

export const DetailBtn = styled.div`
  width: 100px;
  height: 40px;
  border-radius: 16px;
  border: 2px solid #000;
  background: #000;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;

  color: white;
  font-size: 14px;
  font-weight: 600;
  line-height: 100%;
`;
