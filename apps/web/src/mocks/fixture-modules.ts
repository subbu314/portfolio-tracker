const loaded = import.meta.glob("./fixtures/**/*.json", {
  eager: true,
  import: "default",
}) as Record<string, unknown>;

export const fixtureModules: Record<string, unknown> = loaded;
