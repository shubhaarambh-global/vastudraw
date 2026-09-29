import assert from "node:assert/strict";
import test from "node:test";

import { demoDocument } from "../editor/demo-document.ts";
import { ApiRequestError, ProjectApiClient } from "./client.ts";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestUrl(input: Parameters<typeof fetch>[0]): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

void test("project API client uses immutable revision endpoints", async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const fetchImpl: typeof fetch = (input, init) => {
    const url = requestUrl(input);
    calls.push({ url, ...(init === undefined ? {} : { init }) });
    if (url.endsWith("/projects/project-1")) {
      return Promise.resolve(
        jsonResponse({
          project_id: "project-1",
          name: "House",
          created_at: "2026-09-15T00:00:00+00:00",
          current_revision_id: "revision-1",
          current_revision_number: 1,
        }),
      );
    }
    return Promise.resolve(
      jsonResponse({
        project_id: "project-1",
        revision_id: "revision-1",
        revision_number: 1,
        parent_revision_id: null,
        created_at: "2026-09-15T00:00:00+00:00",
        document: {},
        plan_document_hash: "a".repeat(64),
        payload_hash: "b".repeat(64),
      }),
    );
  };

  const client = new ProjectApiClient("http://api.example.test/", fetchImpl);
  const revision = await client.loadCurrentRevision("project-1");
  assert.equal(revision?.revision_id, "revision-1");
  assert.deepEqual(
    calls.map((call) => call.url),
    [
      "http://api.example.test/projects/project-1",
      "http://api.example.test/projects/project-1/revisions/revision-1",
    ],
  );
});

void test("append revision sends canonical document and optimistic parent", async () => {
  let body: unknown;
  const fetchImpl: typeof fetch = (_input, init) => {
    const rawBody = init?.body;
    if (typeof rawBody !== "string") {
      throw new TypeError("Expected request body to be a JSON string.");
    }
    body = JSON.parse(rawBody) as unknown;
    return Promise.resolve(jsonResponse({ revision_id: "next" }, 201));
  };
  const client = new ProjectApiClient("http://api.example.test", fetchImpl);
  const document = {
    ...demoDocument,
    revision_id: "99999999-9999-9999-9999-999999999999",
  };

  await client.appendRevision(demoDocument.project_id, {
    document,
    expected_parent_revision_id: "revision-1",
    note: "Saved from Phase 19 authenticated workflow",
  });

  assert.deepEqual(body, {
    document,
    expected_parent_revision_id: "revision-1",
    note: "Saved from Phase 19 authenticated workflow",
  });
});

void test("authenticated requests include bearer access token", async () => {
  let authorization: string | null = null;
  const fetchImpl: typeof fetch = (_input, init) => {
    authorization = new Headers(init?.headers).get("Authorization");
    return Promise.resolve(jsonResponse([]));
  };
  const client = new ProjectApiClient(
    "http://api.example.test",
    fetchImpl,
    () => Promise.resolve("signed-access-token"),
  );

  await client.listProjects();
  assert.equal(authorization, "Bearer signed-access-token");
});

void test("billing checkout binds authentication and idempotency headers", async () => {
  let checkoutRequestUrl = "";
  let requestHeaders = new Headers();
  let requestBody: BodyInit | null | undefined;
  const fetchImpl: typeof fetch = (input, init) => {
    checkoutRequestUrl = requestUrl(input);
    requestHeaders = new Headers(init?.headers);
    requestBody = init?.body;
    return Promise.resolve(
      jsonResponse({
        merchant_order_id: "vd_order_1",
        sku: "project_single",
        provider: "phonepe",
        provider_reference_id: "OMO_1",
        checkout_url: "https://mercury-uat.phonepe.com/pay/token",
        status: "checkout_created",
        amount_paise: 39_900,
        currency: "INR",
      }),
    );
  };
  const client = new ProjectApiClient(
    "http://api.example.test",
    fetchImpl,
    () => Promise.resolve("signed-access-token"),
  );

  await client.createBillingCheckout("project_single", "checkout-attempt-1");

  assert.equal(checkoutRequestUrl, "http://api.example.test/billing/checkout");
  assert.equal(
    requestHeaders.get("Authorization"),
    "Bearer signed-access-token",
  );
  assert.equal(requestHeaders.get("Idempotency-Key"), "checkout-attempt-1");
  if (typeof requestBody !== "string") {
    throw new TypeError("Expected billing checkout body to be a JSON string.");
  }
  assert.deepEqual(JSON.parse(requestBody), { sku: "project_single" });
});

void test("billing order status paths encode the server order identifier", async () => {
  const requests: Array<{ url: string; method: string }> = [];
  const fetchImpl: typeof fetch = (input, init) => {
    requests.push({ url: requestUrl(input), method: init?.method ?? "GET" });
    return Promise.resolve(
      jsonResponse({
        merchant_order_id: "vd/order",
        sku: "project_single",
        provider: "phonepe",
        provider_reference_id: null,
        checkout_url: null,
        status: "checkout_unknown",
        amount_paise: 39_900,
        currency: "INR",
      }),
    );
  };
  const client = new ProjectApiClient("http://api.example.test", fetchImpl);

  await client.getPaymentOrder("vd/order");
  await client.refreshPaymentOrder("vd/order");

  assert.deepEqual(requests, [
    { url: "http://api.example.test/billing/orders/vd%2Forder", method: "GET" },
    {
      url: "http://api.example.test/billing/orders/vd%2Forder/refresh",
      method: "POST",
    },
  ]);
});

void test("API failures preserve HTTP status and server detail", async () => {
  const client = new ProjectApiClient("http://api.example.test", () =>
    Promise.resolve(jsonResponse({ detail: "stale parent" }, 409)),
  );
  await assert.rejects(
    client.getProject("project-1"),
    (error: unknown) =>
      error instanceof ApiRequestError && error.status === 409,
  );
});

void test("generation intake uploads prompt and reference files as multipart form data", async () => {
  let requestBody: BodyInit | null | undefined;
  let requestHeaders: Headers | null = null;
  const fetchImpl: typeof fetch = (_input, init) => {
    requestBody = init?.body;
    requestHeaders = new Headers(init?.headers);
    return Promise.resolve(
      jsonResponse(
        {
          intake_id: "intake-1",
          project_id: "project-1",
          created_at: "2026-09-15T00:00:00+00:00",
          prompt: "Client brief",
          attachments: [],
          authoritative_geometry: false,
          content_hash: "c".repeat(64),
        },
        201,
      ),
    );
  };
  const client = new ProjectApiClient("http://api.example.test", fetchImpl);
  const file = new File(["%PDF-1.7\nreference"], "brief.pdf", {
    type: "application/pdf",
  });

  const result = await client.createGenerationIntake(
    "project-1",
    "Client brief",
    [file],
  );

  assert.equal(result.intake_id, "intake-1");
  assert.ok(requestBody instanceof FormData);
  assert.equal(requestBody.get("prompt"), "Client brief");
  assert.equal((requestBody.get("files") as File).name, "brief.pdf");
  assert.ok(requestHeaders);
  assert.equal(
    (requestHeaders as unknown as Headers).get("Content-Type"),
    null,
  );
});

void test("selected candidate export downloads the exact binary revision artifact", async () => {
  let requestBody: unknown;
  let authorization: string | null = null;
  const fetchImpl: typeof fetch = (_input, init) => {
    authorization = new Headers(init?.headers).get("Authorization");
    const rawBody = init?.body;
    if (typeof rawBody !== "string") {
      throw new TypeError("Expected export request body to be JSON.");
    }
    requestBody = JSON.parse(rawBody) as unknown;
    return Promise.resolve(
      new Response("<svg data-candidate='candidate-a'/>", {
        status: 200,
        headers: {
          "Content-Type": "image/svg+xml",
          "Content-Disposition":
            'attachment; filename="vastudraw-house-ground-floor.svg"',
          "X-Vastudraw-Source-Hash": "a".repeat(64),
          "X-Vastudraw-Artifact-Sha256": "b".repeat(64),
          "X-Vastudraw-Candidate-Id": "candidate-a",
        },
      }),
    );
  };
  const client = new ProjectApiClient(
    "http://api.example.test",
    fetchImpl,
    () => Promise.resolve("signed-access-token"),
  );

  const result = await client.downloadSelectedExport("project-a", {
    revision_id: "revision-a",
    candidate_id: "candidate-a",
    format: "SVG",
    scope: "FLOOR",
    floor_index: 0,
  });

  assert.equal(authorization, "Bearer signed-access-token");
  assert.deepEqual(requestBody, {
    revision_id: "revision-a",
    candidate_id: "candidate-a",
    format: "SVG",
    scope: "FLOOR",
    floor_index: 0,
  });
  assert.equal(result.filename, "vastudraw-house-ground-floor.svg");
  assert.equal(result.mediaType, "image/svg+xml");
  assert.equal(result.sourcePlanHash, "a".repeat(64));
  assert.equal(result.artifactSha256, "b".repeat(64));
  assert.equal(result.candidateId, "candidate-a");
  assert.equal(await result.blob.text(), "<svg data-candidate='candidate-a'/>");
});

void test("export download rejects a response with an unsafe filename", async () => {
  const client = new ProjectApiClient("http://api.example.test", () =>
    Promise.resolve(
      new Response("payload", {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition": 'attachment; filename="../../secret.pdf"',
        },
      }),
    ),
  );

  await assert.rejects(
    client.downloadSelectedExport("project-a", {
      revision_id: "revision-a",
      candidate_id: "candidate-a",
      format: "PDF",
      scope: "FLOOR",
      floor_index: 0,
    }),
    (error: unknown) =>
      error instanceof ApiRequestError && error.status === 502,
  );
});
