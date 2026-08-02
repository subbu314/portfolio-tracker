import { TableCell, TableRow } from "@/components/ui/table";

export function EmptyTableRow({ colSpan }: { colSpan: number }) {
  return (
    <TableRow>
      <TableCell
        className="py-8 text-center text-muted-foreground"
        colSpan={colSpan}
      >
        No rows
      </TableCell>
    </TableRow>
  );
}
