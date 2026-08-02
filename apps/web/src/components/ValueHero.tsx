import { formatInr, formatPct, formatSignedInr } from "@/lib/format";

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
    <section className="value-hero">
      <div>
        <p className="eyebrow">Total portfolio value</p>
        <p className="hero-value">{formatInr(totalValue)}</p>
        <p className="muted">Invested cost {formatInr(investedCost)}</p>
      </div>
      <div className="hero-return">
        <p className="eyebrow">Absolute return</p>
        <p className="metric-value">{formatSignedInr(gainInr)}</p>
        <p
          className="metric-percent"
          data-negative={gainPct !== null && gainPct < 0}
        >
          {formatPct(gainPct)}
        </p>
      </div>
    </section>
  );
}
