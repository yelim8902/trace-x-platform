import styled from "styled-components";

export default function RektCard({ item }: any) {
  return (
    <Card>
      {/* HEADER */}
      <TopRow>
        <Left>
          {item.logo && <Logo src={item.logo} alt={item.projectName} />}
          <Title>{item.projectName}</Title>
        </Left>

        <Right>
          <MetaBlock>
            <MetaLabel>Funds Lost</MetaLabel>
            <MetaValue isNegative>
              ${Number(item.fundsLost || 0).toLocaleString()}
            </MetaValue>
          </MetaBlock>

          <MetaBlock>
            <MetaLabel>Date</MetaLabel>
            <MetaValue>{item.date || "-"}</MetaValue>
          </MetaBlock>
        </Right>
      </TopRow>

      <Divider />

      {/* DETAILS GRID */}
      <DetailsGrid>
        <DetailItem>
          <DetailLabel>Category</DetailLabel>
          <DetailValue>{item.category ?? "-"}</DetailValue>
        </DetailItem>

        <DetailItem>
          <DetailLabel>Issue Type</DetailLabel>
          <DetailValue>{item.issueType ?? "-"}</DetailValue>
        </DetailItem>

        <DetailItem>
          <DetailLabel>Chain IDs</DetailLabel>
          <DetailValue>
            {Array.isArray(item.chaindIds)
              ? item.chaindIds.join(", ")
              : "-"}
          </DetailValue>
        </DetailItem>

        <DetailItem>
          <DetailLabel>Token</DetailLabel>
          <DetailValue>{item.token?.name ?? "-"}</DetailValue>
        </DetailItem>

        <DetailItem>
          <DetailLabel>Token Address</DetailLabel>
          <DetailValue>{item.token?.addresses?.[0] ?? "-"}</DetailValue>
        </DetailItem>

        <DetailItem>
          <DetailLabel>Funds Returned</DetailLabel>
          <DetailValue>
            {item.fundsReturned
              ? `$${Number(item.fundsReturned).toLocaleString()}`
              : "-"}
          </DetailValue>
        </DetailItem>
      </DetailsGrid>

      <Divider />

      {/* DESCRIPTION */}
      <Description>{item.description}</Description>
    </Card>
  );
}

/* ---------------- STYLES ---------------- */

const Card = styled.div`
  margin-top: 20px;
  background: rgba(255, 255, 255, 0.07); /* almost see-through glass */
  backdrop-filter: blur(12px);
  border-radius: 18px;
  padding: 24px 28px;

  border: 1px solid rgba(255, 255, 255, 0.12);
  display: flex;
  flex-direction: column;
  gap: 18px;

  box-shadow: 
    0px 6px 18px rgba(0, 0, 0, 0.35),
    inset 0 0 0 0.5px rgba(255,255,255,0.15);

  transition: 0.25s ease;

  &:hover {
    transform: translateY(-3px);
    box-shadow:
      0px 8px 22px rgba(0, 0, 0, 0.45),
      inset 0 0 0 0.7px rgba(255,255,255,0.18);
  }
`;

const Divider = styled.div`
  width: 100%;
  height: 1px;
  background: rgba(255, 255, 255, 0.15);
`;

const TopRow = styled.div`
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  align-items: center;
`;

const Left = styled.div`
  display: flex;
  align-items: center;
  gap: 14px;
`;

const Logo = styled.img`
  width: 42px;
  height: 42px;
  border-radius: 10px;
  object-fit: cover;
  border: 1px solid rgba(255,255,255,0.2);
`;

const Title = styled.h3`
  font-size: 20px;
  font-weight: 700;
  color: #f8fafc;
`;

const Right = styled.div`
  display: flex;
  align-items: flex-end;
  gap: 26px;
`;

const MetaBlock = styled.div`
  display: flex;
  flex-direction: column;
  align-items: flex-end;
`;

const MetaLabel = styled.span`
  color: #cbd5e1;
  font-size: 13px;
  font-weight: 500;
`;

const MetaValue = styled.span<{ isNegative?: boolean }>`
  font-size: 16px;
  font-weight: 700;
  color: ${({ isNegative }) => (isNegative ? "var(--point)" : "#f1f5f9")};
`;

/* -------- GRID -------- */

const DetailsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
`;

const DetailItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;
`;

const DetailLabel = styled.span`
  font-size: 13px;
  color: #94a3b8;
`;

const DetailValue = styled.span`
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  word-break: break-all;
`;

const Description = styled.div`
  color: #cbd5e1;
  font-size: 15px;
  line-height: 1.55;
`;
