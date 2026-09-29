import assert from "node:assert/strict";
import test from "node:test";

import { billingProductBySku } from "./catalog.ts";

void test("one-time plans remain purchasable while subscriptions stay coming soon", () => {
  assert.equal(billingProductBySku("project_single")?.checkoutMode, "one_time");
  assert.equal(
    billingProductBySku("project_pack_10")?.checkoutMode,
    "one_time",
  );
  assert.equal(billingProductBySku("pro_monthly")?.checkoutMode, "coming_soon");
  assert.equal(billingProductBySku("pro_yearly")?.checkoutMode, "coming_soon");
});

void test("published launch prices remain unchanged", () => {
  assert.equal(billingProductBySku("project_single")?.price, "₹399");
  assert.equal(billingProductBySku("project_pack_10")?.price, "₹3,399");
  assert.equal(billingProductBySku("pro_monthly")?.price, "₹2,499");
  assert.equal(billingProductBySku("pro_yearly")?.price, "₹24,999");
});
