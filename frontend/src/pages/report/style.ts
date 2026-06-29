import styled from "styled-components";

export const Root = styled.div`
  padding: 18px 50px;
  width: 100%;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
`;

export const HeaderSection = styled.div`
  flex-shrink: 0;
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

export const ContentSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 30px;
  flex: 1;
  min-height: 0;           /* 중요: 내부에서 overflow 잘 동작하게 */
  overflow-y: auto;  
`;

export const FormCard = styled.div`
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

export const FormTitle = styled.h2`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 10px 0;
`;

export const FormRow = styled.div`
  display: flex;
  gap: 15px;
  align-items: flex-end;
`;

export const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
`;

export const Label = styled.label`
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 14px;
  font-weight: 500;
`;

export const Input = styled.input`
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 14px;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
  }
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }
`;

export const Select = styled.select`
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 14px;
  cursor: pointer;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
  }
  
  option {
    background: #1a1a2e;
    color: #fff;
  }
`;

export const TextArea = styled.textarea`
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 12px 16px;
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 14px;
  resize: vertical;
  min-height: 150px;
  
  &:focus {
    outline: none;
    border-color: #3b82f6;
  }
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }
`;

export const AnalyzeButton = styled.button`
  background: #3b82f6;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  color: #fff;
  font-family: "Mona Sans";
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  height: fit-content;
  
  &:hover:not(:disabled) {
    background: #2563eb;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const SubmitButton = styled.button`
  background: #ef4444;
  border: none;
  border-radius: 8px;
  padding: 14px 32px;
  color: #fff;
  font-family: "Mona Sans";
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  width: fit-content;
  margin-top: 10px;
  
  &:hover:not(:disabled) {
    background: #dc2626;
  }
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

export const AnalysisResultCard = styled.div`
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.3);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
`;

export const AnalysisTitle = styled.h3`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 16px;
  font-weight: 600;
  margin: 0;
`;

export const AnalysisRow = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
`;

export const AnalysisLabel = styled.span`
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 14px;
  font-weight: 500;
  min-width: 100px;
`;

export const AnalysisValue = styled.span`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 16px;
  font-weight: 600;
`;

export const RiskBadge = styled.span`
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  color: #fff;
  font-family: "Mona Sans";
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
`;

export const StatusBadge = styled.span<{ status: string }>`
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  color: #fff;
  font-family: "Mona Sans";
  font-size: 12px;
  font-weight: 600;
  background: ${(props) => {
    switch (props.status) {
      case "pending":
        return "#f59e0b";
      case "reviewed":
        return "#3b82f6";
      case "resolved":
        return "#10b981";
      default:
        return "#6b7280";
    }
  }};
`;

export const ErrorMessage = styled.div`
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  color: #fca5a5;
  font-family: "Mona Sans";
  font-size: 14px;
`;

export const SuccessMessage = styled.div`
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 8px;
  padding: 12px 16px;
  color: #6ee7b7;
  font-family: "Mona Sans";
  font-size: 14px;
`;

export const ReportsListCard = styled.div`
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 30px;
`;

export const ReportsListTitle = styled.h2`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px 0;
`;

export const ReportsTable = styled.table`
  width: 100%;
  border-collapse: collapse;
  
  thead {
    background: rgba(255, 255, 255, 0.05);
  }
  
  th {
    padding: 12px 16px;
    text-align: left;
    color: var(--primary400, #aeb9e1);
    font-family: "Mona Sans";
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  }
  
  tbody tr {
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    
    &:hover {
      background: rgba(255, 255, 255, 0.03);
    }
  }
  
  td {
    padding: 16px;
    color: var(--white, #fff);
    font-family: "Mona Sans";
    font-size: 14px;
  }
`;

export const LoadingMessage = styled.div`
  padding: 40px;
  text-align: center;
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 14px;
`;

export const EmptyMessage = styled.div`
  padding: 40px;
  text-align: center;
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 14px;
`;
