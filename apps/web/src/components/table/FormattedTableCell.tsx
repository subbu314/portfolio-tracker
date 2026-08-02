import { TableCell } from "@/components/ui/table";
import { unavailableClassName } from "@/lib/format";

export function FormattedTableCell({ value }: { value: string }) {
  return (
    <TableCell className={unavailableClassName(value, "") || undefined}>
      {value}
    </TableCell>
  );
}
