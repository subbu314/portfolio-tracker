import type { ImportResult } from "@/lib/api";

type SingleImportResult = Extract<
  ImportResult,
  { format: "console_tradebook" }
>;

type Props = {
  report: SingleImportResult;
};

export function ImportReport({ report }: Props) {
  return (
    <section className="panel">
      <h2>Last import</h2>
      <p>{report.new} new rows imported</p>
      <p>{report.existing} existing rows (duplicates skipped)</p>
      {report.date_min && report.date_max ? (
        <p>
          Date range: {report.date_min} to {report.date_max}
        </p>
      ) : null}
      {Object.keys(report.segment_counts).length > 0 ? (
        <>
          <h3>Segments</h3>
          <ul>
            {Object.entries(report.segment_counts).map(([segment, count]) => (
              <li key={segment}>
                {segment}: {count}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      {report.flagged_rows.length > 0 ? (
        <>
          <h3>Flagged rows</h3>
          <ul>
            {report.flagged_rows.map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
