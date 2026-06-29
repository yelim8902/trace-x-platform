export type NodeType = {
  address: string;
  label: string;
  chain: string;
  type: "EOA" | "CA" | string;
  isWarning: boolean;
  displayName?: string;
  description?: string;
};

export type EdgeType = {
  source: string;
  target: string;
  type: string;
  asset: string;
  amount: string;
  txHash: string;
  timeStamp: string;
  uiLabel?: string;
};

export type GraphData = {
  nodes: NodeType[];
  edges: EdgeType[];
};

export const dummyGraphData: GraphData = {
  nodes: [
    // 왼쪽 (유입 지갑들)
    {
      address: "0xLeftA",
      label: "transfer",
      chain: "ETH",
      type: "EOA",
      isWarning: false,
      displayName: "0xLeftA...",
    },
    {
      address: "0xLeftB",
      label: "transfer",
      chain: "ETH",
      type: "EOA",
      isWarning: false,
      displayName: "0xLeftB...",
    },
    {
      address: "0xLeftC",
      label: "swap",
      chain: "ETH",
      type: "CA",
      isWarning: true,
      displayName: "DEX",
      description: "Suspicious swap",
    },
    {
      address: "0xLeftD",
      label: "bridge",
      chain: "BSC",
      type: "CA",
      isWarning: false,
      displayName: "Bridge-BSC",
    },
    {
      address: "0xLeftE",
      label: "transfer",
      chain: "ETH",
      type: "EOA",
      isWarning: false,
      displayName: "0xLeftE...",
    },

    // 중앙 노드 이름 변경
    {
      address: "0xMAIN",
      label: "collector",
      chain: "ETH",
      type: "EOA",
      isWarning: true,
      displayName: "0xMAIN",
      description: "Central wallet",
    },

    // 오른쪽
    {
      address: "0xRight1",
      label: "transfer",
      chain: "ETH",
      type: "EOA",
      isWarning: false,
      displayName: "0xRight1...",
    },
    {
      address: "0xRight2",
      label: "transfer",
      chain: "ETH",
      type: "EOA",
      isWarning: false,
      displayName: "0xRight2...",
    },
    {
      address: "0xRight3",
      label: "bridge",
      chain: "ETH",
      type: "CA",
      isWarning: false,
      displayName: "Bridge-Out",
    },
    {
      address: "0xRight4",
      label: "swap",
      chain: "TRON",
      type: "CA",
      isWarning: true,
      displayName: "TRON-DEX",
    },
    {
      address: "0xRight5",
      label: "escrow",
      chain: "ETH",
      type: "CA",
      isWarning: false,
      displayName: "Escrow",
    },
    {
      address: "0xRight6",
      label: "withdraw",
      chain: "BTC",
      type: "External",
      isWarning: true,
      displayName: "Exit-BTC",
    },
  ],

  edges: [
    // Left -> 0xMAIN
    {
      source: "0xLeftA",
      target: "0xMAIN",
      type: "transfer",
      asset: "ETH",
      amount: "0.1157",
      timeStamp: "2025-03-03T04:24:47Z",
      txHash: "0xhash01",
      uiLabel: "[1] 03/03 04:24 · 0.1157 ETH",
    },
    {
      source: "0xLeftB",
      target: "0xMAIN",
      type: "transfer",
      asset: "USDT",
      amount: "104.33",
      timeStamp: "2025-04-27T08:22:35Z",
      txHash: "0xhash02",
      uiLabel: "[2] 04/27 08:22 · 104.33 USDT",
    },
    {
      source: "0xLeftC",
      target: "0xMAIN",
      type: "swap",
      asset: "ETH",
      amount: "0.0212",
      timeStamp: "2025-05-24T07:27:59Z",
      txHash: "0xhash03",
      uiLabel: "[3] 05/24 07:27 · 0.0212 ETH",
    },
    {
      source: "0xLeftD",
      target: "0xMAIN",
      type: "bridge",
      asset: "BSC-ETH",
      amount: "1",
      timeStamp: "2025-10-13T07:00:35Z",
      txHash: "0xhash04",
      uiLabel: "[4] 10/13 07:00 · Bridge",
    },
    {
      source: "0xLeftE",
      target: "0xMAIN",
      type: "transfer",
      asset: "ETH",
      amount: "0.0045",
      timeStamp: "2025-05-02T10:11:20Z",
      txHash: "0xhash05",
      uiLabel: "[5] 05/02 10:11 · 0.0045 ETH",
    },

    // 0xMAIN -> Right
    {
      source: "0xMAIN",
      target: "0xRight1",
      type: "transfer",
      asset: "USDC",
      amount: "1665.74",
      timeStamp: "2025-06-11T10:28:47Z",
      txHash: "0xhash11",
      uiLabel: "[21] 06/11 10:28 · 1665.74 USDC",
    },
    {
      source: "0xMAIN",
      target: "0xRight2",
      type: "transfer",
      asset: "USDT",
      amount: "12.34",
      timeStamp: "2025-06-02T07:00:59Z",
      txHash: "0xhash12",
      uiLabel: "[22] 06/02 07:00 · 12.34 USDT",
    },
    {
      source: "0xMAIN",
      target: "0xRight3",
      type: "bridge",
      asset: "ETH",
      amount: "0.0118",
      timeStamp: "2025-06-11T10:28:47Z",
      txHash: "0xhash13",
      uiLabel: "[23] 06/11 10:28 · Bridge ETH",
    },
    {
      source: "0xMAIN",
      target: "0xRight4",
      type: "swap",
      asset: "USDT",
      amount: "61",
      timeStamp: "2025-06-15T13:39:47Z",
      txHash: "0xhash14",
      uiLabel: "[24] 06/15 13:39 · 61 USDT",
    },
    {
      source: "0xMAIN",
      target: "0xRight5",
      type: "transfer",
      asset: "USDT",
      amount: "10",
      timeStamp: "2025-06-04T13:25:23Z",
      txHash: "0xhash15",
      uiLabel: "[25] 06/04 13:25 · 10 USDT",
    },
    {
      source: "0xMAIN",
      target: "0xRight6",
      type: "withdraw",
      asset: "NEWT",
      amount: "276",
      timeStamp: "2025-06-25T11:46:11Z",
      txHash: "0xhash16",
      uiLabel: "[26] 06/25 11:46 · 276 NEWT",
    },
  ],
};
