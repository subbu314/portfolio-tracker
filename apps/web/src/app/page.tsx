import { api } from "@/lib/api";

export default async function HomePage() {
  void api;

  return (
    <main>
      <h1>Portfolio Tracker</h1>
      <p>API client ready. Run Sync / Import from Settings once UI lands.</p>
      <p>Base: {process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000"}</p>
    </main>
  );
}
