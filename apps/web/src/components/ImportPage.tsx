"use client";

import { useEffect, useState } from "react";
import { CsvUpload } from "@/components/CsvUpload";
import { GapCallout } from "@/components/GapCallout";
import { ImportReport } from "@/components/ImportReport";
import { PageAlert } from "@/components/PageAlert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Alerts, type ImportResult } from "@/lib/api";
import { loadImportReport, saveImportReport } from "@/lib/import-report";

type SingleImportResult = Extract<
  ImportResult,
  { format: "console_tradebook" }
>;

type ImportError = {
  message: string;
  rows: string[];
};

function isSingleImportResult(
  result: ImportResult,
): result is SingleImportResult {
  return "format" in result;
}

function parseImportError(error: unknown): ImportError {
  const fallback = error instanceof Error ? error.message : "Import failed";
  try {
    const body = JSON.parse(fallback) as {
      detail?: { message?: string; errors?: string[] };
    };
    return {
      message: body.detail?.message ?? fallback,
      rows: body.detail?.errors ?? [],
    };
  } catch {
    return { message: fallback, rows: [] };
  }
}

export function ImportPage() {
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [report, setReport] = useState<SingleImportResult | null>(null);
  const [error, setError] = useState<ImportError | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const stored = loadImportReport();
    if (stored && isSingleImportResult(stored)) setReport(stored);
    void api
      .getAlerts()
      .then(setAlerts)
      .catch((loadError: Error) =>
        setError({ message: loadError.message, rows: [] }),
      );
  }, []);

  async function onUpload(file: File) {
    setUploading(true);
    setError(null);
    try {
      const result = await api.postImportCsv(file);
      if (!isSingleImportResult(result)) {
        throw new Error("Unexpected import response");
      }
      saveImportReport(result);
      setReport(result);
    } catch (uploadError) {
      setError(parseImportError(uploadError));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="stack">
      <h1>Import</h1>
      {alerts?.gap ? (
        <GapCallout
          suggestedFrom={alerts.gap.suggested_from}
          suggestedTo={alerts.gap.suggested_to}
          message={alerts.gap.message}
        />
      ) : null}
      <Card>
        <CardHeader className="p-5 pb-0">
          <CardTitle>Upload Console tradebook</CardTitle>
          <CardDescription>
            Export the Console tradebook for the From–To range and upload the
            CSV here.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-5 pt-4">
          <CsvUpload onUpload={onUpload} uploading={uploading} />
        </CardContent>
      </Card>
      {error ? (
        <PageAlert title="Import error">
          <p>{error.message}</p>
          {error.rows.length > 0 ? (
            <ul>
              {error.rows.map((row) => (
                <li key={row}>{row}</li>
              ))}
            </ul>
          ) : null}
        </PageAlert>
      ) : null}
      {report ? <ImportReport report={report} /> : null}
    </div>
  );
}
