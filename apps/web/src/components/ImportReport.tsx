import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { SingleImportResult } from "@/lib/import-types";

type Props = {
  report: SingleImportResult;
};

export function ImportReport({ report }: Props) {
  return (
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>Last import</CardTitle>
      </CardHeader>
      <CardContent className="stack p-5 pt-4">
        <div className="flex flex-wrap gap-2">
          <Badge>{report.new} new</Badge>
          <Badge variant="secondary">{report.existing} existing</Badge>
        </div>
        {report.date_min && report.date_max ? (
          <p className="text-muted-foreground">
            Date range: {report.date_min} to {report.date_max}
          </p>
        ) : null}
        {Object.keys(report.segment_counts).length > 0 ? (
          <section>
            <h3>Segments</h3>
            <ul>
              {Object.entries(report.segment_counts).map(([segment, count]) => (
                <li key={segment}>
                  {segment}: {count}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {report.flagged_rows.length > 0 ? (
          <section>
            <h3>Flagged rows</h3>
            <ul>
              {report.flagged_rows.map((row) => (
                <li key={row} className="text-destructive">
                  {row}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </CardContent>
    </Card>
  );
}
