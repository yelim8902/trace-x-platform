import styled from "styled-components";
import ArrowUp from "@/assets/icon_arrow_up.svg";
import ArrowDown from "@/assets/icon_arrow_down.svg";

type StatCardProps = {
  title: string;
  value: string | number;
  diff: string | number;
  icon: string;
};

export default function StatCard({ title, value, diff, icon }: StatCardProps) {
  // 문자열 → 숫자로 변환 ("-4.5%" → -4.5)
  const diffNumber =
    typeof diff === "string" ? Number(diff.replace("%", "")) : diff;

  const status: "up" | "down" | "neutral" =
    diffNumber > 0 ? "up" : diffNumber < 0 ? "down" : "neutral";

  // 숫자일 경우 3자리 콤마 적용
  const formattedValue =
    typeof value === "number"
      ? value.toLocaleString(undefined, { maximumFractionDigits: 1 })
      : value;

  return (
    <Card>
      <Header>
        <Icon src={icon} alt={title} />
        <Title>{title}</Title>
      </Header>

      <Body>
        <Value>{formattedValue}</Value>

        <Diff $status={status}>
          <div>{diffNumber}%</div>

          {status !== "neutral" && (
            <ArrowIcon
              src={status === "up" ? ArrowUp : ArrowDown}
              alt={status === "up" ? "상승" : "하락"}
            />
          )}
        </Diff>
      </Body>
    </Card>
  );
}


// ---------- styled ----------
const Card = styled.div`
  width: 100%;
  height: 100px;
  border-radius: 8px;
  border: 0.6px solid var(--secondary200, #343b4f);
  background: var(--neutral800, #060a1d);
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
`;

const Header = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  color: #aeb9e1;
`;

const Icon = styled.img`
  width: 14px;
  height: 14px;
`;

const Title = styled.span`
  color: var(--primary400, #aeb9e1);
  font-family: "Mona Sans";
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  line-height: 14px;
`;

const Body = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const Value = styled.div`
  color: var(--white, #fff);
  font-family: "Mona Sans";
  font-size: 24px;
  font-style: normal;
  font-weight: 600;
  line-height: 32px;
`;

const ArrowIcon = styled.img`
  width: 8px;
  height: 8px;
`;

const Diff = styled.div<{ $status: "up" | "down" | "neutral" }>`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 3px;
  padding: 2px 6px;

  font-family: "Mona Sans";
  font-size: 11px;
  line-height: 14px;
  font-weight: 300;

  color: ${({ $status }) =>
    $status === "up"
      ? "var(--red300, #FF5A65)"
      : $status === "down"
      ? "var(--skyblue300, #00D4FF)"
      : "var(--neutral300, #AEB9E1)"};

  background-color: ${({ $status }) =>
    $status === "up"
      ? "rgba(255, 90, 101, 0.20)"
      : $status === "down"
      ? "rgba(0, 212, 255, 0.20)"
      : "rgba(255,255,255,0.08)"};

  border: ${({ $status }) =>
    $status === "up"
      ? "1px solid rgba(255, 90, 101, 0.20)"
      : $status === "down"
      ? "1px solid rgba(0, 212, 255, 0.20)"
      : "1px solid rgba(255,255,255,0.08)"};

  border-radius: 2px;
`;
