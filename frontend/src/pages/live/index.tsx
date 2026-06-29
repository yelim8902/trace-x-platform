import { useOutletContext } from "react-router";
import * as S from "./style";
import { useEffect, useState } from "react";

/* -------------------- Layout Context -------------------- */
type LayoutContext = {
  title: string;
  intro: string;
};

/* -------------------- 실제 UI에서 사용할 TxData 타입 -------------------- */
type TxData = {
  id: string;
  from: string;
  to: string;
  amount: string;
  token: string;
  timestamp: string;
  risk: string;
  score: number;
};

/* -------------------- 백엔드 타입 정의 -------------------- */
type BackendTx = {
  txHash: string;
  from_address: string;
  to_address: string;
  token: string;
  amount: string;
  timestamp: number;
  risk: {
    score: number;
    level: "High" | "Medium" | "Low";
  };
};

/* -------------------- shorten 함수 -------------------- */
const shorten = (value: string, left = 6, right = 4) => {
  if (!value) return "";
  if (value.length <= left + right) return value;
  return `${value.slice(0, left)}...${value.slice(-right)}`;
};

/* -------------------- 매핑 함수 -------------------- */
const mapBackendToTxData = (raw: BackendTx): TxData => {
  const riskMap: Record<string, string> = {
    High: "위험",
    Medium: "경고",
    Low: "안전",
  };

  const date = new Date(raw.timestamp * 1000);

  const formattedDate = date.toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  return {
    id: raw.txHash,
    from: raw.from_address,
    to: raw.to_address,
    amount: raw.amount,
    token: raw.token,
    timestamp: formattedDate,
    risk: riskMap[raw.risk?.level ?? "Low"],
    score: raw.risk?.score ?? 0,
  };
};

/* -------------------- LivePage Component -------------------- */
export default function LivePage() {
  const { title, intro } = useOutletContext<LayoutContext>();

  const [data, setData] = useState<TxData[]>([]);
  const [loading, setLoading] = useState(true);

  const [page, setPage] = useState(1);

  // 입력값 (API 호출 X)
  const [searchInput, setSearchInput] = useState("");

  // 실제 검색에 사용되는 토큰 (API 호출 O)
  const [searchToken, setSearchToken] = useState("");

  /* -------------------- API 요청 -------------------- */
  useEffect(() => {
    let isMounted = true;
    setLoading(true);

    async function fetchData() {
      try {
        const params = new URLSearchParams();

        if (searchToken.trim() !== "") {
          params.append("tokenFilter", searchToken.trim());
        }

        params.append("pageNo", String(page));

        const backendUrl =
          import.meta.env.VITE_BACKEND_API_URL || "http://localhost:8888";
        const url = `${backendUrl}/api/live-detection/summary?${params.toString()}`;

        const res = await fetch(url);
        const json = await res.json();

        const mapped =
          json.data?.map((item: BackendTx) => mapBackendToTxData(item)) ?? [];

        if (isMounted) setData(mapped);
      } catch (error) {
        if (isMounted) setData([]);
        console.log("Error fetching live data:", error);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchData();
    return () => {
      isMounted = false;
    };
  }, [searchToken, page]);

  /* -------------------- 렌더링 -------------------- */
  return (
    <S.Root>
      <S.HeaderSection>
        <S.Title>{title}</S.Title>
        <S.Intro>{intro}</S.Intro>
      </S.HeaderSection>

      {/* 검색 바 */}
      <S.FilterBar>
        <S.FilterGroup>
          <S.Divider />

          <S.SearchWrapper>
            <input
              type="text"
              placeholder="토큰 검색 (예: ETH, USDT...)"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setSearchToken(searchInput.trim());
                  setPage(1);
                }
              }}
            />

            <button
              onClick={() => {
                setSearchToken(searchInput.trim());
                setPage(1);
              }}
            >
              검색
            </button>
          </S.SearchWrapper>
        </S.FilterGroup>
      </S.FilterBar>

      {/* 테이블 */}
      {loading ? (
        <div style={{ color: "white", marginTop: "20px" }}>Loading...</div>
      ) : (
        <S.Table>
          <thead>
            <tr>
              <th>TxHash</th>
              <th>From</th>
              <th>To</th>
              <th>Amount</th>
              <th>Token</th>
              <th>TimeStamp</th>
              <th>Risk</th>
            </tr>
          </thead>

          <tbody>
            {data.map((tx) => (
              <S.TableRow
                key={tx.id}
                $risk={tx.risk}
                onClick={() =>
                  window.open(`https://etherscan.io/tx/${tx.id}`, "_blank")
                }
              >
                <td title={tx.id}>{shorten(tx.id)}</td>
                <td title={tx.from}>{shorten(tx.from)}</td>
                <td title={tx.to}>{shorten(tx.to)}</td>
                <td>{tx.amount}</td>
                <td>{tx.token}</td>
                <td>{tx.timestamp}</td>
                <td>
                  <S.RiskTag
                    $level={
                      tx.risk === "위험"
                        ? "high"
                        : tx.risk === "경고"
                        ? "mid"
                        : "low"
                    }
                  >
                    {tx.risk} <span>{tx.score.toFixed(2)}</span>
                  </S.RiskTag>
                </td>
              </S.TableRow>
            ))}
          </tbody>
        </S.Table>
      )}

      {/* 페이지네이션 */}
      <S.Pagination>
        {Array.from({ length: 10 }).map((_, i) => (
          <S.PageButton
            key={i}
            $active={page === i + 1}
            onClick={() => setPage(i + 1)}
          >
            {i + 1}
          </S.PageButton>
        ))}
      </S.Pagination>
    </S.Root>
  );
}
