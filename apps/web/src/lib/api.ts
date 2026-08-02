import type { paths } from "./api-types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

type AppJson<P extends keyof paths, M extends keyof paths[P]> =
  paths[P][M] extends { responses: { 200: { content: { "application/json": infer R } } } }
    ? R
    : never;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, { ...init, cache: "no-store" });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type Overview = AppJson<"/portfolio/overview", "get">;
export type HoldingsResponse = AppJson<"/portfolio/holdings", "get">;
export type Holding = HoldingsResponse["holdings"][number];
export type Performance = AppJson<"/portfolio/performance", "get">;
export type Alerts = AppJson<"/portfolio/alerts", "get">;
export type AuthStatus = AppJson<"/auth/status", "get">;
export type SyncResult = AppJson<"/sync", "post">;
export type ImportResult = AppJson<"/import/csv", "post">;
export type BenchmarkList = AppJson<"/settings/benchmarks", "get">;

export const api = {
  getHealth: () => request<AppJson<"/health", "get">>("/health"),
  getOverview: () => request<Overview>("/portfolio/overview"),
  getHoldings: async () => {
    const data = await request<HoldingsResponse>("/portfolio/holdings");
    return data.holdings;
  },
  getPerformance: () => request<Performance>("/portfolio/performance"),
  getAlerts: () => request<Alerts>("/portfolio/alerts"),
  getAuthStatus: () => request<AuthStatus>("/auth/status"),
  getLoginUrl: () => request<AppJson<"/auth/login-url", "get">>("/auth/login-url"),
  postCallback: (request_token: string) =>
    request<AppJson<"/auth/callback", "post">>("/auth/callback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_token }),
    }),
  postLogout: () =>
    request<AppJson<"/auth/logout", "post">>("/auth/logout", { method: "POST" }),
  postSync: () => request<SyncResult>("/sync", { method: "POST" }),
  postImportCsv: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<ImportResult>("/import/csv", { method: "POST", body });
  },
  postImportCsvBatch: async (files: File[]) => {
    const body = new FormData();
    for (const file of files) body.append("files", file);
    return request<ImportResult>("/import/csv", { method: "POST", body });
  },
  getBenchmarkSettings: () => request<BenchmarkList>("/settings/benchmarks"),
  putBenchmark: (instrumentId: number, benchmark_index: string) =>
    request<AppJson<"/settings/benchmarks/{instrument_id}", "put">>(
      `/settings/benchmarks/${instrumentId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ benchmark_index }),
      },
    ),
  putCategory: (instrumentId: number, category: string) =>
    request<AppJson<"/settings/categories/{instrument_id}", "put">>(
      `/settings/categories/${instrumentId}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category }),
      },
    ),
};
