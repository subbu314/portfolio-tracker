"use client";

import { type FormEvent, useState } from "react";

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
    <form className="control-row" onSubmit={onSubmit}>
      <label className="field">
        <span>Console tradebook CSV</span>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <button type="submit" disabled={!file || uploading}>
        {uploading ? "Uploading…" : "Upload"}
      </button>
    </form>
  );
}
