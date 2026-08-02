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
import { api, type Alerts } from "@/lib/api";
import { parseImportError } from "@/lib/api-errors";
import { loadImportReport, saveImportReport } from "@/lib/import-report";
import {
  isSingleImportResult,
  type SingleImportResult,
} from "@/lib/import-types";

export function ImportPage() {
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [report, setReport] = useState<SingleImportResult | null>(null);
  const [alertsError, setAlertsError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<
    ReturnType<typeof parseImportError> | null
  >(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const stored = loadImportReport();
    if (stored && isSingleImportResult(stored)) setReport(stored);
    void api
      .getAlerts()
      .then(setAlerts)
      .catch((loadError: Error) => setAlertsError(loadError.message));
  }, []);

  async function onUpload(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await api.postImportCsv(file);
      if (!isSingleImportResult(result)) {
        throw new Error("Unexpected import response");
      }
      saveImportReport(result);
      setReport(result);
      try {
        const nextAlerts = await api.getAlerts();
        setAlerts(nextAlerts);
        setAlertsError(null);
      } catch (error) {
        setAlertsError(
          error instanceof Error ? error.message : "Failed to refresh alerts",
        );
      }
    } catch (error) {
      setUploadError(parseImportError(error));
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
      {alertsError ? (
        <PageAlert title="Alerts error">{alertsError}</PageAlert>
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
      {uploadError ? (
        <PageAlert title="Import error">
          <p>{uploadError.message}</p>
          {uploadError.rows.length > 0 ? (
            <ul>
              {uploadError.rows.map((row) => (
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
