import { readFileSync } from "node:fs";
import path from "node:path";

const css = readFileSync(
  path.resolve(__dirname, "../app/globals.css"),
  "utf8",
);

it("defines polish design tokens from the spec", () => {
  expect(css).toContain("#0b1220");
  expect(css).toContain("#121a27");
  expect(css).toContain("#2a3545");
  expect(css).toContain("#e7eef8");
  expect(css).toContain("#8fa0b7");
  expect(css).toContain("#3d9cf0");
});

it("maps shadcn semantic colors into the Tailwind theme", () => {
  expect(css).toContain("--color-primary: var(--primary)");
  expect(css).toContain("--color-card: var(--card)");
});
