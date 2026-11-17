import { expect, test } from "@playwright/test";
import { apiFlyers } from "./helpers";

/**
 * Journey 1 — guest browsing (2-mode access: guests browse without an account).
 * Home → gallery → mode filter → full-text search → flyer detail with QR.
 */
test("guest can browse, filter, search and open a flyer", async ({ page }) => {
  // Seeded demo data: an emergency flyer for "Bruno" exists (see seed_demo).
  const list = await apiFlyers(page, "?mode=emergency");
  const bruno = list.results.find((f) => f.pet?.name === "Bruno");
  expect(bruno, "seeded emergency flyer 'Bruno' should exist").toBeTruthy();

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /bring them home/i })).toBeVisible();
  // Emergency rail on the home page renders the seeded flyer as a guest.
  await expect(page.getByRole("heading", { name: "Lost right now" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Bruno/ }).first()).toBeVisible();

  // Gallery.
  await page.getByRole("link", { name: "Flyers" }).click();
  await page.waitForURL(/\/flyers$/);
  await expect(page.getByRole("heading", { name: "All flyers" })).toBeVisible();

  // Mode filter.
  await page.getByRole("button", { name: "Lost — urgent" }).click();
  await expect(page.getByRole("heading", { name: "Lost pet alerts" })).toBeVisible();
  await expect(page).toHaveURL(/mode=emergency/);

  // Full-text search.
  await page.getByRole("textbox", { name: /search pets/i }).fill("Bruno");
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page).toHaveURL(/q=Bruno/);
  await expect(page.getByRole("link", { name: /Bruno/ }).first()).toBeVisible();

  // Open the detail page.
  await page.getByRole("link", { name: /Bruno/ }).first().click();
  await page.waitForURL(/\/flyers\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Lost pet: Bruno" })).toBeVisible();
  await expect(page.getByText(/Reward for safe return/)).toBeVisible();
  // Print-ready actions + scannable QR are on the public page.
  await expect(page.getByRole("button", { name: /Print A4 flyer/ })).toBeVisible();
  await expect(page.locator('img[alt^="QR code linking to"]')).toBeVisible();
  // Guests are invited to log in to fund the reward (no paywall on browsing).
  await expect(page.getByRole("link", { name: "Log in to fund reward" })).toBeVisible();
});
