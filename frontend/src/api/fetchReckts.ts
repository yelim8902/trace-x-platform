import { createClient } from "@de-fi/sdk";

const DEFI_GQL = import.meta.env.VITE_DEFI_GQL;
const API_KEY = import.meta.env.VITE_DEFI_API_KEY;

type Sort = "asc" | "desc";

function parseOrderBy(input?: string | string[]) {
  if (typeof input !== "string" || !input.trim()) return undefined;

  const parts = input.split(",");
  const obj: Record<string, Sort> = {};

  for (const p of parts) {
    const [kRaw, vRaw] = p.split(":").map((s) => s.trim());
    const v = vRaw?.toLowerCase() === "desc" ? "desc" : "asc";

    if (
      ["project", "ticker", "fundsLost", "chain", "issue", "date", "category"].includes(
        kRaw
      )
    ) {
      obj[kRaw] = v as Sort;
    }
  }
  return Object.keys(obj).length ? obj : undefined;
}

const toIntArray = (v?: string | string[]) =>
  typeof v === "string" && v.trim().length
    ? v.split(",").map((s) => parseInt(s.trim(), 10)).filter((n) => !Number.isNaN(n))
    : undefined;

const toStringArray = (v?: string | string[]) =>
  typeof v === "string" && v.trim().length
    ? v.split(",").map((s) => s.trim()).filter(Boolean)
    : undefined;

export async function fetchRekts(params: {
  pageNumber?: number;
  pageSize?: number;
  searchText?: string;
  projectName?: string;
  chainIds?: string;
  orderBy?: string;
  issueTypes?: string;
  projectCategories?: string;
}) {
  try {
    const client = createClient({
      url: DEFI_GQL,
      headers: API_KEY ,
    });

    const {
      pageNumber = 1,
      pageSize = 20,
      searchText,
      projectName,
      chainIds,
      orderBy,
      issueTypes,
      projectCategories,
    } = params;

    const args: any = {
      pageNumber,
      pageSize,
    };

    if (searchText) args.searchText = searchText;
    if (projectName) args.projectName = projectName;

    const chainIdsArr = toIntArray(chainIds);
    if (chainIdsArr) args.chainIds = chainIdsArr;

    const order = parseOrderBy(orderBy);
    if (order) args.orderBy = order;

    const issueArr = toStringArray(issueTypes);
    if (issueArr) args.issueTypes = issueArr;

    const catArr = toStringArray(projectCategories);
    if (catArr) args.projectCategories = catArr;

    // Rekts 호출
    const result = await client.query({
      rekts: [
        args,
        {
          id: true,
          projectName: true,
          description: true,
          date: true,
          fundsLost: true,
          fundsReturned: true,
          chaindIds: true,
          category: true,
          issueType: true,
          token: { name: true, addresses: true },
        },
      ],
    });

    const rawRekts = result.data?.rekts ?? [];

    // logo enrichment
    const addressSet = new Set<string>();
    for (const r of rawRekts) {
      const addr = r.token?.addresses?.[0];
      if (addr) addressSet.add(addr.toLowerCase());
    }

    const addresses = [...addressSet];
    const logoMap: Record<string, string> = {};

    for (const a of addresses) {
      try {
        const single = await client.query({
          scannerProject: [
            {
              where: { address: a, chainId: rawRekts[0]?.chaindIds?.[0] || 1 },
            },
            { logo: true },
          ],
        });

        const logo = (single.data as any)?.scannerProject?.logo;
        if (logo) logoMap[a] = logo;
      } catch {}
    }

    const enriched = rawRekts.map((r: any) => {
      const addr = r.token?.addresses?.[0]?.toLowerCase();
      const logo = addr ? logoMap[addr] : undefined;
      return { ...r, logo };
    });

    return { data: enriched };
  } catch (e: any) {
    return { error: e.message ?? "Unknown error" };
  }
}
