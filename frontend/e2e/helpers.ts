import path from "node:path";
import type { Page } from "@playwright/test";

/** Django API origin (the webServer in playwright.config.ts runs it on :8010). */
export const API = "http://127.0.0.1:8010/api";

/** Photo fixtures verified against the real YOLO-World gatekeeper. */
export const fixture = (name: string) => path.join(process.cwd(), "e2e", "fixtures", name);

export const DEMO = { email: "mia@example.com", password: "demo1234" };

/** Log in through the real UI and wait until the shell shows the logged-in nav. */
export async function login(page: Page, email = DEMO.email, password = DEMO.password) {
  await page.goto("/auth/login");
  await page.locator("#login-email").fill(email);
  await page.locator("#login-password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
  await page.waitForURL((url) => url.pathname === "/");
  await page.getByRole("button", { name: "Log out" }).waitFor({ state: "visible" });
}

/** Fetch the public flyer list straight from the API (guest, no session needed). */
export async function apiFlyers(page: Page, query = "") {
  const resp = await page.request.get(`${API}/flyers${query}`);
  if (resp.status() !== 200) throw new Error(`GET /api/flyers${query} -> ${resp.status()}`);
  return (await resp.json()) as { results: Array<Record<string, any>> };
}
