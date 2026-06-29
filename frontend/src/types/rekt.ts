export interface RektToken {
  name?: string;
  addresses?: string[];
}

export interface RektItem {
  id: number;
  projectName: string;
  title?: string;                // De.Fi가 가끔 내려주는 경우 있음
  description?: string;          // HTML 포함
  date?: string;                 // YYYY-mm-dd
  fundsLost?: number | string;   // De.Fi API에서 string으로 오는 경우 많음
  fundsReturned?: number | string;
  chaindIds: number[];           // GraphQL 필드 명 그대로 (주의!)
  category?: string;
  issueType?: string;
  token: RektToken;
  logo?: string;                 // enrichment
}
