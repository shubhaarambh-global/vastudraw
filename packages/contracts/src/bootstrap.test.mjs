import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const schemaUrl = new URL(
  "../schema/plan-document.schema.json",
  import.meta.url,
);

test("phase 1 contract schema version is explicit and required", async () => {
  const schema = JSON.parse(await readFile(schemaUrl, "utf8"));
  assert.equal(schema.properties.schema_version.const, "1.0.0");
  assert.ok(schema.required.includes("schema_version"));
  assert.ok(schema.required.includes("canonical_units"));
});
