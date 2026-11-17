import { describe, expect, it, beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { useAuth } from "@/stores/auth";
import { mswServer } from "@/test/setup";
import { mockUser } from "@/test/handlers";

beforeEach(() => {
  useAuth.setState({ user: null, checked: false });
});

describe("auth store", () => {
  it("fetchMe stores the user on success", async () => {
    mswServer.use(http.get("*/api/auth/me", () => HttpResponse.json(mockUser())));
    const user = await useAuth.getState().fetchMe();
    expect(user?.email).toBe("mia@example.com");
    expect(useAuth.getState().user?.email).toBe("mia@example.com");
    expect(useAuth.getState().checked).toBe(true);
  });

  it("fetchMe clears the user on 401", async () => {
    const user = await useAuth.getState().fetchMe();
    expect(user).toBeNull();
    expect(useAuth.getState().user).toBeNull();
    expect(useAuth.getState().checked).toBe(true);
  });

  it("logout posts and clears the user", async () => {
    const logoutCalls = vi.fn();
    mswServer.use(http.post("*/api/auth/logout", () => {
      logoutCalls();
      return HttpResponse.json({ status: "logged_out" });
    }));
    useAuth.setState({ user: mockUser(), checked: true });
    await useAuth.getState().logout();
    expect(logoutCalls).toHaveBeenCalled();
    expect(useAuth.getState().user).toBeNull();
  });

  it("clears the user when the session-expired event fires", () => {
    useAuth.setState({ user: mockUser(), checked: true });
    window.dispatchEvent(new CustomEvent("pawprint:session-expired"));
    expect(useAuth.getState().user).toBeNull();
  });
});
