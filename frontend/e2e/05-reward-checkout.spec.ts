import { createHmac } from "node:crypto";
import { expect, test } from "@playwright/test";
import { API, apiFlyers, login } from "./helpers";

/**
 * Journey 5 — fund a reward over GCash (PayMongo stub): open the checkout modal,
 * show the QR, then deliver a correctly HMAC-signed PayMongo webhook and watch
 * the UI flip to "Payment received" via status polling.
 */
test("GCash reward checkout + signed PayMongo webhook flips status to succeeded", async ({ page }) => {
  await login(page);

  // Find the seeded emergency flyer (Bruno, ₱5,000 reward) via the public API.
  const list = await apiFlyers(page, "?mode=emergency&q=Bruno");
  const bruno = list.results.find((f) => f.pet?.name === "Bruno" && f.reward_amount_cents > 0);
  expect(bruno, "seeded Bruno flyer with a reward should exist").toBeTruthy();

  await page.goto(`/flyers/${bruno.id}`);
  await expect(page.getByRole("heading", { name: "Lost pet: Bruno" })).toBeVisible();

  // Open the reward checkout modal.
  await page.getByRole("button", { name: "Fund reward" }).click();
  const dialog = page.getByRole("dialog", { name: /Fund the reward for Bruno/ });
  await expect(dialog).toBeVisible();

  // Start a GCash payment (hits the stubbed PayMongo checkout-sessions endpoint).
  const createPromise = page.waitForResponse(
    (r) => r.url().endsWith("/api/rewards") && r.request().method() === "POST",
  );
  await page.locator("#reward-amount").fill("250");
  await dialog.getByRole("button", { name: /Show GCash QR/ }).click();
  const createResp = await createPromise;
  expect(createResp.status()).toBe(201);
  const init = (await createResp.json()) as { transaction_id: string; checkout_url: string };
  expect(init.checkout_url).toContain("checkout.paymongo.test");

  // QR + waiting state render; the app polls the status endpoint.
  await expect(page.locator('[data-testid="gcash-qr"] img')).toBeVisible();
  await expect(page.getByText("Waiting for payment…")).toBeVisible();

  // Read the pending transaction (page.request shares the session cookie).
  const statusResp = await page.request.get(`${API}/rewards/${init.transaction_id}/status`);
  expect(statusResp.status()).toBe(200);
  const status0 = (await statusResp.json()) as { status: string; provider_reference: string };
  expect(status0.status).toBe("pending");
  expect(status0.provider_reference).toMatch(/^cs_test_/);

  // Deliver a correctly signed PayMongo webhook (HMAC-SHA256 of "{ts}.{payload}").
  const ts = String(Math.floor(Date.now() / 1000));
  const payload = JSON.stringify({
    id: `evt_e2e_${ts}`,
    data: {
      id: `evt_e2e_${ts}`,
      type: "payment_intent.succeeded",
      attributes: { id: status0.provider_reference },
    },
  });
  const sig = createHmac("sha256", "whsec_dev").update(`${ts}.${payload}`, "utf8").digest("hex");
  const wh = await page.request.post(`${API}/webhooks/paymongo`, {
    data: payload,
    headers: { "Content-Type": "application/json", "Paymongo-Signature": `t=${ts},te=${sig}` },
  });
  expect(wh.status()).toBe(200);

  // An unsigned/forged webhook is rejected.
  const forged = await page.request.post(`${API}/webhooks/paymongo`, {
    data: payload,
    headers: { "Content-Type": "application/json", "Paymongo-Signature": `t=${ts},te=deadbeef` },
  });
  expect(forged.status()).toBe(400);

  // Eager Celery applied the event: status endpoint reports succeeded.
  const after = (await (await page.request.get(`${API}/rewards/${init.transaction_id}/status`)).json()) as {
    status: string;
  };
  expect(after.status).toBe("succeeded");

  // The modal's 2s polling picks it up.
  await expect(page.locator('[data-testid="gcash-success"]')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('[data-testid="gcash-success"]')).toContainText("Payment received");
});
