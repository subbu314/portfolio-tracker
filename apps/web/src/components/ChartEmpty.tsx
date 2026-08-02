export function ChartEmpty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border bg-surface-elevated p-4 text-muted-foreground">
      {children}
    </div>
  );
}
