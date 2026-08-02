import { TableCell } from "@/components/ui/table";
import { isUnavailable } from "@/lib/format";

export function FormattedTableCell({ value }: { value: string }) {
  return (
    <TableCell
      className={
        isUnavailable(value)
          ? "font-mono tabular-nums text-muted-foreground"
          : undefined
      }
    >
      {value}
    </TableCell>
  );
}
