import { HttpResponse, http } from "msw";
import { loadFixture } from "./load-fixture";
import { getActiveScenario } from "./scenarios";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

function scenario() {
  return getActiveScenario();
}

function requestedWindow(request: Request): string {
  return new URL(request.url).searchParams.get("window") ?? "ITD";
}

export const handlers = [
  http.get(`${API}/health`, () =>
    HttpResponse.json(loadFixture(scenario(), "health")),
  ),
  http.get(`${API}/portfolio/overview`, () =>
    HttpResponse.json(loadFixture(scenario(), "overview")),
  ),
  http.get(`${API}/portfolio/holdings`, () =>
    HttpResponse.json(loadFixture(scenario(), "holdings")),
  ),
  http.get(`${API}/portfolio/holdings/:id`, ({ params }) =>
    HttpResponse.json(loadFixture(scenario(), `holding-${params.id}`)),
  ),
  http.get(`${API}/portfolio/holdings/:id/transactions`, ({ params }) =>
    HttpResponse.json(
      loadFixture(scenario(), `holding-${params.id}-transactions`),
    ),
  ),
  http.get(`${API}/portfolio/holdings/:id/series`, ({ params, request }) =>
    HttpResponse.json(
      loadFixture(
        scenario(),
        `holding-${params.id}-series-${requestedWindow(request)}`,
      ),
    ),
  ),
  http.get(`${API}/portfolio/series`, ({ request }) =>
    HttpResponse.json(
      loadFixture(scenario(), `series-${requestedWindow(request)}`),
    ),
  ),
  http.get(`${API}/portfolio/performance`, () =>
    HttpResponse.json(loadFixture(scenario(), "performance")),
  ),
  http.get(`${API}/portfolio/alerts`, () =>
    HttpResponse.json(loadFixture(scenario(), "alerts")),
  ),
  http.get(`${API}/auth/status`, () =>
    HttpResponse.json(loadFixture(scenario(), "auth-status")),
  ),
  http.get(`${API}/auth/login-url`, () =>
    HttpResponse.json(loadFixture(scenario(), "login-url")),
  ),
  http.post(`${API}/auth/callback`, () =>
    HttpResponse.json({ connected: true }),
  ),
  http.post(`${API}/auth/logout`, () =>
    HttpResponse.json({ connected: false }),
  ),
  http.post(`${API}/sync`, () =>
    HttpResponse.json(loadFixture(scenario(), "sync-result")),
  ),
  http.post(`${API}/import/csv`, () =>
    HttpResponse.json(loadFixture(scenario(), "import-result")),
  ),
  http.get(`${API}/settings/benchmarks`, () =>
    HttpResponse.json(loadFixture(scenario(), "benchmarks")),
  ),
  http.get(`${API}/settings/catalogs`, () =>
    HttpResponse.json(loadFixture(scenario(), "catalogs")),
  ),
  http.put(`${API}/settings/benchmarks/:id`, async ({ params, request }) => {
    const body = (await request.json()) as { benchmark_index: string };
    return HttpResponse.json({
      instrument_id: Number(params.id),
      benchmark_index: body.benchmark_index,
      source: "user",
    });
  }),
  http.put(`${API}/settings/categories/:id`, async ({ params, request }) => {
    const body = (await request.json()) as { category: string };
    return HttpResponse.json({
      instrument_id: Number(params.id),
      mf_category: body.category,
    });
  }),
];
