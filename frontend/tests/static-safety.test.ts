import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

const sourceRoot = join(process.cwd(), "src");

const collectSourceFiles = (directory: string): string[] =>
  readdirSync(directory).flatMap((entry) => {
    const fullPath = join(directory, entry);
    return statSync(fullPath).isDirectory() ? collectSourceFiles(fullPath) : [fullPath];
  });

describe("frontend architecture safety", () => {
  it("does not import Python backend or database modules", () => {
    const forbidden = [
      "app.database",
      "app.repositories",
      "app.services",
      "DATABASE_URL",
      "psycopg",
      "sqlalchemy",
    ];
    const contents = collectSourceFiles(sourceRoot)
      .map((file) => readFileSync(file, "utf8"))
      .join("\n");

    for (const token of forbidden) {
      expect(contents).not.toContain(token);
    }
  });

  it("does not hardcode operational site IDs in frontend source", () => {
    const contents = collectSourceFiles(sourceRoot)
      .map((file) => readFileSync(file, "utf8"))
      .join("\n");

    expect(contents).not.toMatch(/MH-\d{3}/);
  });

  it("keeps status colours centralized in design tokens", () => {
    const tokenFile = readFileSync(join(sourceRoot, "app", "theme.ts"), "utf8");

    expect(tokenFile).toContain("colorRemote");
    expect(tokenFile).toContain("colorField");
    expect(tokenFile).toContain("priorityCritical");
  });
});
