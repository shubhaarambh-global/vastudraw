import assert from "node:assert/strict";
import test from "node:test";

import { activeNavigationKey } from "./navigation.ts";

void test("SaaS navigation marks the current product area active", () => {
  assert.equal(activeNavigationKey("/"), "dashboard");
  assert.equal(activeNavigationKey("/projects"), "projects");
  assert.equal(activeNavigationKey("/projects/abc"), "projects");
  assert.equal(activeNavigationKey("/editor?project=abc"), "editor");
  assert.equal(activeNavigationKey("/generation"), "generation");
  assert.equal(activeNavigationKey("/reviews"), "reviews");
  assert.equal(activeNavigationKey("/exports"), "exports");
  assert.equal(activeNavigationKey("/settings"), "settings");
});
