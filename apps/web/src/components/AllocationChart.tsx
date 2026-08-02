"use client";

import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { AllocationSliceUi } from "@/lib/allocation";
import { formatPct } from "@/lib/format";

const COLORS = ["#5b9fd4", "#3ecf8e", "#e6a23c"];

type Props = {
  slices: AllocationSliceUi[];
};

export function AllocationChart({ slices }: Props) {
  if (slices.length === 0) return <p className="muted">No holdings yet</p>;

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
