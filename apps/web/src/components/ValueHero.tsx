import { formatInr, formatPct, formatSignedInr } from "@/lib/format";
import { Card } from "@/components/ui/card";

type Props = {
  totalValue: number;
  investedCost: number;
  gainInr: number;
  gainPct: number | null;
};

export function ValueHero({
  totalValue,
  investedCost,
  gainInr,
  gainPct,
}: Props) {
  return (
    <Card className="value-hero p-5">
      <div>
        <p className="eyebrow">Total portfolio value</p>
        <p className="hero-value font-mono tabular-nums">
          {formatInr(totalValue)}
        </p>
        <p className="muted">Invested cost {formatInr(investedCost)}</p>
      </div>
      <div className="hero-return">
        <p className="eyebrow">Absolute return</p>
        <p className="metric-value font-mono tabular-nums">
          {formatSignedInr(gainInr)}
        </p>
        <p
          className="metric-percent font-mono tabular-nums"
          data-negative={gainPct !== null && gainPct < 0}
        >
          {formatPct(gainPct)}
        </p>
      </div>
    </Card>
  );
}
