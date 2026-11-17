import { expect, test } from "@playwright/test";
import { apiFlyers } from "./helpers";

/**
 * Journey 6 — QR scan: the QR code printed on the flyer encodes the public flyer
 * URL (qr_target_value). Opening that URL as a scanner would lands on the flyer
 * detail page, guest-accessible, with the QR rendered as an SVG data-URL.
 */
test("scanning the flyer QR target opens the public flyer page", async ({ page }) => {
  const list = await apiFlyers(page, "?mode=emergency");
  const flyer = list.results[0];
  expect(flyer).toBeTruthy();
  expect(flyer.qr_target_value).toMatch(new RegExp(`/flyers/${flyer.id}$`));

  // A scanner resolves the encoded absolute URL — here we open the path on the app.
  const { pathname } = new URL(flyer.qr_target_value as string);
  await page.goto(pathname);

  const h1 = page.getByRole("heading", { level: 1 });
  await expect(h1).toContainText(flyer.pet.name);
  await expect(h1).toContainText("Lost pet");

  const qr = page.locator('img[alt^="QR code linking to"]');
  await expect(qr).toBeVisible();
  await expect(qr).toHaveAttribute("src", /^data:image\/svg\+xml/);
});
