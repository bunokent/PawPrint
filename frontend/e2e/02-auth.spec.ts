import { expect, test } from "@playwright/test";
import { DEMO, login } from "./helpers";

/**
 * Journey 2 — unified account: register a fresh user, log out, log back in
 * with the seeded demo account, and see a wrong-password error.
 */
test("register → logout → login (seeded demo account)", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // Register a brand-new account through the UI.
  await page.goto("/auth/register");
  await page.locator("#reg-name").fill("E2E Tester");
  await page.locator("#reg-email").fill(email);
  await page.locator("#reg-password").fill("e2e-pass-1234");
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
  // The nav greets by display name when set.
  await expect(page.locator("nav")).toContainText("E2E Tester");

  // Log out → back to guest nav.
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();

  // Wrong password surfaces a friendly error, not a crash.
  await page.goto("/auth/login");
  await page.locator("#login-email").fill(DEMO.email);
  await page.locator("#login-password").fill("definitely-wrong");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.locator(".error-box[role='alert']")).toBeVisible();

  // Correct credentials log in and the shell greets the user.
  await page.locator("#login-password").fill(DEMO.password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await expect(page.locator("nav")).toContainText("Mia Santos");
  await expect(page.getByRole("link", { name: "My flyers" })).toBeVisible();
  await expect(page.getByRole("link", { name: "New flyer" })).toBeVisible();
});

test("login helper lands on home as the demo user", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();
});
