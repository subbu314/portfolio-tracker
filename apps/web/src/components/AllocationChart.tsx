"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartEmpty } from "@/components/ChartEmpty";
import type { AllocationSliceUi } from "@/lib/allocation";
import { formatPct } from "@/lib/format";

const COLORS = ["var(--accent)", "var(--positive)", "var(--warn)"];

type Props = {
  slices: AllocationSliceUi[];
  holdingsCount: number;
};

export function AllocationChart({ slices, holdingsCount }: Props) {
  if (slices.length === 0) {
    return (
      <ChartEmpty>
        {holdingsCount > 0
          ? "Allocation unavailable — prices missing"
          : "No holdings yet"}
      </ChartEmpty>
    );
  }

  return (
    <div className="chart-frame" aria-label="Asset allocation chart">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={slices}
            dataKey="weight"
            nameKey="label"
            innerRadius="55%"
            outerRadius="80%"
          >
            {slices.map((slice, index) => (
              <Cell
                key={slice.label}
                fill={COLORS[index % COLORS.length]}
                stroke="var(--border)"
              />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatPct(Number(value))} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
