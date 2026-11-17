import { describe, expect, it, beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "@/features/auth/pages/LoginPage";
import { RegisterPage } from "@/features/auth/pages/RegisterPage";
import { GoogleButton } from "@/features/auth/components/GoogleButton";
import { useAuth } from "@/stores/auth";
import { mswServer } from "@/test/setup";
import { renderWithProviders } from "@/test/utils";
import { mockUser } from "@/test/handlers";

const HOME = <div>HOME PAGE</div>;

beforeEach(() => {
  useAuth.setState({ user: null, checked: true });
});

describe("LoginPage", () => {
  const renderLogin = (route = "/auth/login") =>
    renderWithProviders(<LoginPage />, { route, routes: [["/", HOME]] });

  it("logs in with valid credentials and navigates home", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "mia@example.com");
    await user.type(screen.getByLabelText("Password"), "demo1234");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("HOME PAGE")).toBeInTheDocument();
    expect(useAuth.getState().user?.email).toBe("mia@example.com");
  });

  it("shows the API error on bad credentials", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.type(screen.getByLabelText("Email"), "mia@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password.");
  });

  it("validates required fields client-side", async () => {
    const user = userEvent.setup();
    renderLogin();
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findAllByRole("alert")).not.toHaveLength(0);
    expect(screen.queryByText("HOME PAGE")).not.toBeInTheDocument();
  });

  it("exchanges a Google ?code= callback for a session", async () => {
    const callbackCalls = vi.fn();
    mswServer.use(
      http.post("*/api/auth/google/callback", async ({ request }) => {
        callbackCalls(await request.json());
        return HttpResponse.json({ user: mockUser({ google_id: "g-9" }), created: true });
      }),
    );
    renderLogin("/auth/login?code=google-code-123");
    expect(await screen.findByText("HOME PAGE")).toBeInTheDocument();
    expect(callbackCalls).toHaveBeenCalledWith(expect.objectContaining({ code: "google-code-123" }));
    expect(useAuth.getState().user?.google_id).toBe("g-9");
  });

  it("shows an error when the Google callback fails", async () => {
    mswServer.use(
      http.post("*/api/auth/google/callback", () =>
        HttpResponse.json({ error: { code: "oauth_error", message: "Google sign-in failed." } }, { status: 400 }),
      ),
    );
    renderLogin("/auth/login?code=bad-code");
    expect(await screen.findByRole("alert")).toHaveTextContent("Google sign-in failed.");
  });
});

describe("RegisterPage", () => {
  const renderRegister = () =>
    renderWithProviders(<RegisterPage />, { route: "/auth/register", routes: [["/", HOME]] });

  it("registers and navigates home", async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByLabelText(/Display name/), "Kai");
    await user.type(screen.getByLabelText("Email"), "kai@example.com");
    await user.type(screen.getByLabelText(/Password/), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("HOME PAGE")).toBeInTheDocument();
    expect(useAuth.getState().user?.email).toBe("kai@example.com");
  });

  it("shows a field error when the email is taken", async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByLabelText("Email"), "taken@example.com");
    await user.type(screen.getByLabelText(/Password/), "supersecret1");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
  });

  it("rejects short passwords client-side", async () => {
    const user = userEvent.setup();
    renderRegister();
    await user.type(screen.getByLabelText("Email"), "kai@example.com");
    await user.type(screen.getByLabelText(/Password/), "short");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByText("Use at least 8 characters.")).toBeInTheDocument();
  });
});

describe("GoogleButton", () => {
  it("requests the authorize URL and redirects", async () => {
    const urlCalls = vi.fn();
    mswServer.use(
      http.post("*/api/auth/google/url", async ({ request }) => {
        urlCalls(await request.json());
        return HttpResponse.json({ url: "https://accounts.google.com/o/oauth2/v2/auth?client_id=dev" });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<GoogleButton />);
    await user.click(screen.getByRole("button", { name: /Continue with Google/ }));
    await waitFor(() => expect(urlCalls).toHaveBeenCalledWith(expect.objectContaining({ redirect_uri: expect.stringContaining("/auth/login") })));
  });

  it("shows an error when the URL request fails", async () => {
    mswServer.use(http.post("*/api/auth/google/url", () => HttpResponse.error()));
    const user = userEvent.setup();
    renderWithProviders(<GoogleButton />);
    await user.click(screen.getByRole("button", { name: /Continue with Google/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not reach Google sign-in");
  });
});
