import { describe, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { api, ApiError, multipartConfig } from "@/lib/api/client";
import { mswServer } from "@/test/setup";

describe("ApiError normalization", () => {
  it("parses a 422 no_pet_detected body with detected labels", async () => {
    mswServer.use(
      http.post("*/api/pets/photos", () =>
        HttpResponse.json(
          { error: { code: "no_pet_detected", message: "No pet detected in the photo.", detected_labels: ["person", "car"] } },
          { status: 422 },
        ),
      ),
    );
    const error = await api.post("/pets/photos", {}).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.code).toBe("no_pet_detected");
    expect(apiError.detectedLabels).toEqual(["person", "car"]);
    expect(apiError.sessionExpired).toBe(false);
  });

  it("flags 401 responses as session-expired and emits the window event", async () => {
    const listener = vi.fn();
    window.addEventListener("pawprint:session-expired", listener);
    mswServer.use(
      http.get("*/api/auth/me", () =>
        HttpResponse.json({ error: { code: "authentication_required", message: "Authentication required.", session_expired: true } }, { status: 401 }),
      ),
    );
    const error = await api.get("/auth/me").catch((e: unknown) => e);
    expect((error as ApiError).sessionExpired).toBe(true);
    expect(listener).toHaveBeenCalled();
    window.removeEventListener("pawprint:session-expired", listener);
  });

  it("falls back to a network error without a response", async () => {
    mswServer.use(http.get("*/api/flyers", () => HttpResponse.error()));
    const error = await api.get("/flyers").catch((e: unknown) => e);
    expect((error as ApiError).code).toBe("network_error");
    expect((error as ApiError).status).toBe(0);
  });
});

describe("multipartConfig", () => {
  it("sets the multipart content type", () => {
    expect(multipartConfig().headers).toMatchObject({ "Content-Type": "multipart/form-data" });
  });
});
