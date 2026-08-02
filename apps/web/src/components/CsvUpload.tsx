"use client";

import { type FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type Props = {
  onUpload: (file: File) => void | Promise<void>;
  uploading?: boolean;
};

export function CsvUpload({ onUpload, uploading = false }: Props) {
  const [file, setFile] = useState<File | null>(null);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (file) void onUpload(file);
  }

  return (
    <Card className="border-dashed border-border bg-surface-elevated">
      <CardContent className="p-5">
        <form className="control-row" onSubmit={onSubmit}>
          <label className="field flex-1">
            <span>Console tradebook CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <Button type="submit" disabled={!file || uploading}>
            {uploading ? "Uploading…" : "Upload"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
