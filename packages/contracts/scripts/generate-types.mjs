import { writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { compileFromFile } from "json-schema-to-typescript";
import { format } from "prettier";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..");
const schemaPath = path.join(root, "schema", "plan-document.schema.json");
const outputPath = path.join(root, "src", "generated", "plan-document.ts");

const compiled = await compileFromFile(schemaPath, {
  bannerComment: "/* AUTO-GENERATED FROM PYDANTIC JSON SCHEMA. DO NOT EDIT. */",
  style: {
    singleQuote: false,
    semi: true,
    tabWidth: 2,
    trailingComma: "all",
  },
});

const output = await format(compiled, {
  parser: "typescript",
});

await writeFile(outputPath, output, "utf8");

console.log(`Wrote ${path.relative(root, outputPath)}`);
