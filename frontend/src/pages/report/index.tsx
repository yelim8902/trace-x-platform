import { useOutletContext, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import * as S from "./style";
import {
  createSuspiciousReport,
  getSuspiciousReports,
  SuspiciousReport,
} from "@/api/reports";
import { analyzeAddressViaBackend } from "@/services/backend";

type LayoutContext = {
  title: string;
  intro: string;
};

const CHAINS = [
  { id: 1, name: "Ethereum" },
  { id: 56, name: "BSC" },
  { id: 137, name: "Polygon" },
];

export default function ReportPage() {
  const { title, intro } = useOutletContext<LayoutContext>();
  const navigate = useNavigate();

  // 폼 상태
  const [reportTitle, setReportTitle] = useState("");
  const [address, setAddress] = useState("");
  const [chainId, setChainId] = useState(1);
  const [description, setDescription] = useState("");

  // 분석 상태
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // 제출 상태
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // 보고서 목록
  const [reports, setReports] = useState<SuspiciousReport[]>([]);
  const [isLoadingReports, setIsLoadingReports] = useState(false);

  // 보고서 목록 로드
  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setIsLoadingReports(true);
    try {
      const data = await getSuspiciousReports({ limit: 10 });
      setReports(data);
    } catch (error: any) {
      console.error("Failed to load reports:", error);
    } finally {
      setIsLoadingReports(false);
    }
  };

  // 주소 분석
  const handleAnalyze = async () => {
    if (!address.trim()) {
      setAnalysisError("주소를 입력해주세요.");
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null);
    setAnalysisResult(null);

    try {
      const result = await analyzeAddressViaBackend({
        address: address.trim(),
        chain_id: chainId,
        max_hops: 2,
        analysis_type: "basic",
      });

      setAnalysisResult(result);
      setAnalysisError(null);
    } catch (error: any) {
      console.error("Analysis failed:", error);
      setAnalysisError(
        error?.response?.data?.error || "주소 분석에 실패했습니다."
      );
      setAnalysisResult(null);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 보고서 제출
  const handleSubmit = async () => {
    if (!reportTitle.trim()) {
      setSubmitError("보고서 제목을 입력해주세요.");
      return;
    }

    if (!address.trim()) {
      setSubmitError("주소를 입력해주세요.");
      return;
    }

    if (!description.trim()) {
      setSubmitError("보고서 내용을 입력해주세요.");
      return;
    }

    if (!analysisResult) {
      setSubmitError("먼저 주소를 분석해주세요.");
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(false);

    try {
      const riskScore =
        analysisResult.final_score ||
        analysisResult.risk_score ||
        analysisResult.stage2_score ||
        0;
      const riskLevel =
        analysisResult.risk_level ||
        (riskScore >= 70 ? "high" : riskScore >= 40 ? "medium" : "low");

      await createSuspiciousReport({
        title: reportTitle.trim(),
        address: address.trim(),
        chain_id: chainId,
        risk_score: riskScore,
        risk_level: riskLevel,
        description: description.trim(),
        analysis_data: analysisResult,
        transaction_hashes: analysisResult.transaction_hashes || [],
      });

      setSubmitSuccess(true);
      setReportTitle("");
      setAddress("");
      setDescription("");
      setAnalysisResult(null);
      loadReports(); // 목록 새로고침

      // 2초 후 성공 메시지 숨기기
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 3000);
    } catch (error: any) {
      console.error("Submit failed:", error);
      setSubmitError(
        error?.response?.data?.error || "보고서 제출에 실패했습니다."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const getRiskLevelColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case "high":
      case "danger":
        return "#ef4444";
      case "medium":
      case "warning":
        return "#f59e0b";
      case "low":
      case "normal":
        return "#10b981";
      default:
        return "#6b7280";
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "-";
    try {
      const date = new Date(dateString);
      return date.toLocaleString("ko-KR");
    } catch {
      return dateString;
    }
  };

  return (
    <S.Root>
      <S.HeaderSection>
        <S.Title>{title}</S.Title>
        <S.Intro>{intro}</S.Intro>
      </S.HeaderSection>

      <S.ContentSection>
        {/* 보고서 작성 폼 */}
        <S.FormCard>
          <S.FormTitle>새 의심거래 보고서 작성</S.FormTitle>

          {/* 제목 */}
          <S.FormGroup>
            <S.Label>보고서 제목 *</S.Label>
            <S.Input
              type="text"
              placeholder="예: Tornado Cash 연관 의심거래"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
            />
          </S.FormGroup>

          {/* 주소 및 체인 */}
          <S.FormRow>
            <S.FormGroup style={{ flex: 2 }}>
              <S.Label>의심 주소 *</S.Label>
              <S.Input
                type="text"
                placeholder="0x..."
                value={address}
                onChange={(e) => setAddress(e.target.value)}
              />
            </S.FormGroup>
            <S.FormGroup style={{ flex: 1 }}>
              <S.Label>체인</S.Label>
              <S.Select
                value={chainId}
                onChange={(e) => setChainId(Number(e.target.value))}
              >
                {CHAINS.map((chain) => (
                  <option key={chain.id} value={chain.id}>
                    {chain.name}
                  </option>
                ))}
              </S.Select>
            </S.FormGroup>
            <S.AnalyzeButton onClick={handleAnalyze} disabled={isAnalyzing}>
              {isAnalyzing ? "분석 중..." : "주소 분석"}
            </S.AnalyzeButton>
          </S.FormRow>

          {/* 분석 결과 */}
          {analysisError && <S.ErrorMessage>{analysisError}</S.ErrorMessage>}

          {analysisResult && (
            <S.AnalysisResultCard>
              <S.AnalysisTitle>분석 결과</S.AnalysisTitle>
              <S.AnalysisRow>
                <S.AnalysisLabel>리스크 점수:</S.AnalysisLabel>
                <S.AnalysisValue>
                  {analysisResult.final_score ||
                    analysisResult.risk_score ||
                    analysisResult.stage2_score ||
                    "-"}
                </S.AnalysisValue>
              </S.AnalysisRow>
              <S.AnalysisRow>
                <S.AnalysisLabel>리스크 레벨:</S.AnalysisLabel>
                <S.RiskBadge
                  style={{
                    backgroundColor: getRiskLevelColor(
                      analysisResult.risk_level || "low"
                    ),
                  }}
                >
                  {analysisResult.risk_level || "low"}
                </S.RiskBadge>
              </S.AnalysisRow>
            </S.AnalysisResultCard>
          )}

          {/* 보고서 내용 */}
          <S.FormGroup>
            <S.Label>보고서 내용 *</S.Label>
            <S.TextArea
              placeholder="의심거래에 대한 상세 설명을 작성해주세요..."
              rows={8}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </S.FormGroup>

          {/* 제출 버튼 */}
          <S.SubmitButton
            onClick={handleSubmit}
            disabled={isSubmitting || !analysisResult}
          >
            {isSubmitting ? "제출 중..." : "보고서 제출"}
          </S.SubmitButton>

          {submitError && <S.ErrorMessage>{submitError}</S.ErrorMessage>}
          {submitSuccess && (
            <S.SuccessMessage>
              보고서가 성공적으로 제출되었습니다!
            </S.SuccessMessage>
          )}
        </S.FormCard>

        {/* 보고서 목록 */}
        <S.ReportsListCard>
          <S.ReportsListTitle>최근 보고서</S.ReportsListTitle>
          {isLoadingReports ? (
            <S.LoadingMessage>로딩 중...</S.LoadingMessage>
          ) : reports.length === 0 ? (
            <S.EmptyMessage>제출된 보고서가 없습니다.</S.EmptyMessage>
          ) : (
            <S.ReportsTable>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>제목</th>
                  <th>주소</th>
                  <th>리스크</th>
                  <th>상태</th>
                  <th>작성일</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr
                    key={report.id}
                    onClick={() => {
                      // 상세 페이지로 이동 (추후 구현)
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <td>#{report.id}</td>
                    <td>{report.title}</td>
                    <td>
                      {report.address.slice(0, 6)}...{report.address.slice(-4)}
                    </td>
                    <td>
                      <S.RiskBadge
                        style={{
                          backgroundColor: getRiskLevelColor(
                            report.risk_level || "low"
                          ),
                        }}
                      >
                        {report.risk_level}
                      </S.RiskBadge>
                    </td>
                    <td>
                      <S.StatusBadge status={report.status || "pending"}>
                        {report.status || "pending"}
                      </S.StatusBadge>
                    </td>
                    <td>{formatDate(report.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </S.ReportsTable>
          )}
        </S.ReportsListCard>
      </S.ContentSection>
    </S.Root>
  );
}
