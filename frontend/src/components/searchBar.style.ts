import styled from "styled-components";

export const Container = styled.div`
  flex: 1; // 부모 컨테이너에 맞춰서 확장
  width: 100%; // 전체 너비 사용
`;

export const InputWrapper = styled.div`
  display: flex;
  align-items: center;
  background: #1e1e1e;
  border: 1px solid #444;
  border-radius: 12px;
  padding: 6px;
  gap: 6px;
  transition: border-color 0.2s ease;

  &:focus-within {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
  }
`;

export const Input = styled.input`
  flex: 1;
  height: 40px;
  padding: 0 14px;
  background: transparent;
  border: none;
  outline: none;
  color: #e5e7eb;
  font-size: 14px;
  font-family: monospace, Pretendard; // 주소/해시를 위한 monospace 폰트
  letter-spacing: 0.3px;
  width: 100%; // 전체 너비 사용

  &::placeholder {
    color: #6b7280;
    font-family: Pretendard; // placeholder는 일반 폰트
  }
`;

export const SearchButton = styled.button`
  background: #343b4f;
  color: white;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 18px;
  border-radius: 10px;
  border: none;
  cursor: pointer;

  &:hover {
    background: #1e3a8a;
  }
`;
