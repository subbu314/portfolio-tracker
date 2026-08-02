"use client";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { mocksEnabled } from "@/lib/mocks-enabled";
import {
  getActiveScenario,
  SCENARIO_IDS,
  SCENARIO_LABELS,
  setActiveScenario,
  type ScenarioId,
} from "@/mocks/scenarios";

const useMocks = mocksEnabled();

export function ScenarioSwitcher() {
  if (!useMocks) return null;

  const activeScenario = getActiveScenario();

  async function onPickScenario(id: ScenarioId) {
    setActiveScenario(id);
    if (id === "import_errors") {
      const { loadFixture } = await import("@/mocks/load-fixture");
      const report = loadFixture(id, "import-report");
      sessionStorage.setItem(
        "portfolio-tracker:last-import",
        JSON.stringify(report),
      );
    } else {
      sessionStorage.removeItem("portfolio-tracker:last-import");
    }
    window.location.reload();
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="secondary"
            size="sm"
            aria-label={`Mock: ${SCENARIO_LABELS[activeScenario]}`}
          >
            Mock: {SCENARIO_LABELS[activeScenario]} ▾
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {SCENARIO_IDS.map((id) => (
            <DropdownMenuItem key={id} onSelect={() => onPickScenario(id)}>
              {SCENARIO_LABELS[id]}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
