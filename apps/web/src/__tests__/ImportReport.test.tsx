import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImportReport } from "@/components/ImportReport";
import { GapCallout } from "@/components/GapCallout";
import { ImportPage } from "@/components/ImportPage";
import { loadImportReport, saveImportReport } from "@/lib/import-report";

const mocks = vi.hoisted(() => ({
  getAlerts: vi.fn(),
  postImportCsv: vi.fn(),
}));

vi.mock("@/lib/api", () => ({ api: mocks }));

const report = {
  format: "console_tradebook" as const,
  new: 3,
  existing: 1,
  segment_counts: { equity: 2, mf: 2 },
  flagged_rows: ["row 4: missing price"],
  date_min: "2024-01-01",
  date_max: "2024-06-01",
  financial_years: ["2023-24"],
};

describe("ImportReport", () => {
  it("shows imported and existing counts as badges", () => {
    render(<ImportReport report={report} />);

    expect(screen.getByText("3 new")).toHaveClass("bg-primary");
    expect(screen.getByText("1 existing")).toHaveClass("bg-secondary");
  });

  it("emphasizes flagged rows", () => {
    render(<ImportReport report={report} />);

    expect(screen.getByText(/row 4: missing price/)).toBeInTheDocument();
    expect(screen.getByText(/row 4: missing price/)).toHaveClass(
      "text-destructive",
    );
  });
});

describe("GapCallout", () => {
  it("exposes adjustable from/to defaults from alerts", () => {
    render(
      <GapCallout
        suggestedFrom="2024-01-01"
        suggestedTo="2024-06-01"
        message="Missing history"
      />,
    );

    expect(screen.getByDisplayValue("2024-01-01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2024-06-01")).toBeInTheDocument();
    expect(screen.getByText(/export that range/i)).toBeInTheDocument();
  });
});

describe("import report storage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("saves and loads the last successful report", () => {
    saveImportReport(report);

    expect(loadImportReport()).toEqual(report);
  });

  it("returns null for malformed stored JSON", () => {
    sessionStorage.setItem("portfolio-tracker:last-import", "{");

    expect(loadImportReport()).toBeNull();
  });

  it("returns null for batch-shaped stored JSON", () => {
    sessionStorage.setItem(
      "portfolio-tracker:last-import",
      JSON.stringify({ results: [{ format: "console_tradebook" }] }),
    );

    expect(loadImportReport()).toBeNull();
  });
});

describe("ImportPage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
    mocks.getAlerts.mockResolvedValue({ gap: null });
  });

  it("shows the gap dates returned by alerts", async () => {
    mocks.getAlerts.mockResolvedValue({
      gap: {
        suggested_from: "2024-01-01",
        suggested_to: "2024-06-01",
        message: "Missing history",
      },
    });

    render(<ImportPage />);

    expect(await screen.findByDisplayValue("2024-01-01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2024-06-01")).toBeInTheDocument();
  });

  it("uploads one CSV and persists its successful report", async () => {
    const user = userEvent.setup();
    mocks.postImportCsv.mockResolvedValue(report);
    render(<ImportPage />);

    const file = new File(["symbol,trade_date\n"], "tradebook.csv", {
      type: "text/csv",
    });
    await user.upload(screen.getByLabelText(/console tradebook csv/i), file);
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(mocks.postImportCsv).toHaveBeenCalledWith(file);
    expect(await screen.findByText(/row 4: missing price/)).toBeInTheDocument();
    expect(loadImportReport()).toEqual(report);
  });

  it("refetches alerts after successful import", async () => {
    const user = userEvent.setup();
    mocks.getAlerts
      .mockResolvedValueOnce({
        gap: {
          suggested_from: "2026-01-01",
          suggested_to: "2026-08-01",
          message: "Missing history",
        },
      })
      .mockResolvedValueOnce({ gap: null });
    mocks.postImportCsv.mockResolvedValue(report);
    render(<ImportPage />);
    expect(await screen.findByDisplayValue("2026-01-01")).toBeInTheDocument();

    await user.upload(
      screen.getByLabelText(/console tradebook csv/i),
      new File(["ok"], "ok.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload" }));

    await screen.findByText(/3 new/i);
    expect(screen.queryByDisplayValue("2026-01-01")).not.toBeInTheDocument();
    expect(mocks.getAlerts).toHaveBeenCalledTimes(2);
  });

  it("keeps the import report when the post-import alerts refresh fails", async () => {
    const user = userEvent.setup();
    mocks.getAlerts
      .mockResolvedValueOnce({ gap: null })
      .mockRejectedValueOnce(new Error("alerts refresh failed"));
    mocks.postImportCsv.mockResolvedValue(report);
    render(<ImportPage />);

    await user.upload(
      screen.getByLabelText(/console tradebook csv/i),
      new File(["ok"], "ok.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(await screen.findByText("Alerts error")).toBeInTheDocument();
    expect(screen.getByText("alerts refresh failed")).toBeInTheDocument();
    expect(screen.getByText(/3 new/i)).toBeInTheDocument();
    expect(screen.queryByText("Import error")).not.toBeInTheDocument();
  });

  it("titles alerts load failures separately from import errors", async () => {
    mocks.getAlerts.mockRejectedValue(new Error("alerts down"));
    render(<ImportPage />);

    expect(await screen.findByText("Alerts error")).toBeInTheDocument();
    expect(screen.queryByText("Import error")).not.toBeInTheDocument();
  });

  it("shows API error details", async () => {
    const user = userEvent.setup();
    mocks.postImportCsv.mockRejectedValue(
      new Error(
        JSON.stringify({
          detail: {
            message: "Console tradebook parse failed",
            errors: ["row 2: missing symbol"],
          },
        }),
      ),
    );
    render(<ImportPage />);

    await user.upload(
      screen.getByLabelText(/console tradebook csv/i),
      new File(["bad"], "bad.csv", { type: "text/csv" }),
    );
    await user.click(screen.getByRole("button", { name: "Upload" }));

    expect(
      await screen.findByText("Console tradebook parse failed"),
    ).toBeInTheDocument();
    expect(screen.getByText("row 2: missing symbol")).toBeInTheDocument();
  });
});
