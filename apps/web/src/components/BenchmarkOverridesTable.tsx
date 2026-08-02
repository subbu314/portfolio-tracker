"use client";

import type { BenchmarkList, Catalogs } from "@/lib/api";

type BenchmarkItem = BenchmarkList["items"][number];

type Props = {
  items: BenchmarkItem[];
  catalogs: Catalogs;
  onCategoryChange: (instrumentId: number, category: string) => void | Promise<void>;
  onBenchmarkChange: (instrumentId: number, benchmark: string) => void | Promise<void>;
  busy: boolean;
};

export function BenchmarkOverridesTable({
  items,
  catalogs,
  onCategoryChange,
  onBenchmarkChange,
  busy,
}: Props) {
  return (
    <section className="panel">
      <h2>Compare each holding to which index?</h2>
      <table>
        <thead>
          <tr>
            <th>Holding</th>
            <th>Kind</th>
            <th>Fund category</th>
            <th>Compare to index</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.instrument_id}
              data-needs-category={item.needs_category || undefined}
              style={
                item.needs_category
                  ? { background: "color-mix(in srgb, var(--warn) 10%, transparent)" }
                  : undefined
              }
            >
              <td>{item.symbol}</td>
              <td>{item.instrument_type}</td>
              <td>
                {item.instrument_type === "mf" ? (
                  <select
                    aria-label={`${item.symbol} fund category`}
                    value={item.mf_category ?? ""}
                    disabled={busy}
                    onChange={(event) =>
                      void onCategoryChange(item.instrument_id, event.target.value)
                    }
                  >
                    {item.needs_category ? (
                      <option value="" disabled>
                        Choose category
                      </option>
                    ) : null}
                    {catalogs.mf_categories.map((category) => (
                      <option key={category} value={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                ) : (
                  "—"
                )}
              </td>
              <td>
                <select
                  aria-label={`${item.symbol} comparison index`}
                  value={item.benchmark_index}
                  disabled={busy}
                  onChange={(event) =>
                    void onBenchmarkChange(item.instrument_id, event.target.value)
                  }
                >
                  {catalogs.benchmark_indexes.map((index) => (
                    <option key={index} value={index}>
                      {index}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
