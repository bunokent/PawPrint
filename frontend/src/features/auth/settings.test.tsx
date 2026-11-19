import { describe, expect, it, beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettingsPage } from "@/features/auth/pages/SettingsPage";
import { useAuth } from "@/stores/auth";
import { mswServer } from "@/test/setup";
import { renderWithProviders } from "@/test/utils";
import { mockUser } from "@/test/handlers";

beforeEach(() => {
  useAuth.setState({ user: null, checked: true });
});

describe("SettingsPage", () => {
  const renderSettings = () =>
    renderWithProviders(<SettingsPage />, { route: "/settings", routes: [["/auth/login", <div>LOGIN PAGE</div>]] });

  it("redirects guests to login", async () => {
    renderSettings();
    expect(await screen.findByText("LOGIN PAGE")).toBeInTheDocument();
  });

  it("shows the current profile and saves display name + phone", async () => {
    useAuth.setState({ user: mockUser(), checked: true });
    const patchCalls: Array<Record<string, unknown>> = [];
    mswServer.use(
      http.patch("*/api/auth/profile", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchCalls.push(body);
        return HttpResponse.json(mockUser(body as Partial<ReturnType<typeof mockUser>>));
      }),
    );
    const user = userEvent.setup();
    renderSettings();

    const name = await screen.findByLabelText("Display name");
    expect(name).toHaveValue("Mia");
    expect(screen.getByLabelText("Email")).toHaveValue("mia@example.com");
    expect(screen.getByLabelText("Email")).toHaveAttribute("readonly");

    await user.clear(name);
    await user.type(name, "Mia Cruz");
    await user.type(screen.getByLabelText("Phone"), "09171234567");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Profile saved.");
    await waitFor(() => expect(patchCalls).toEqual([{ display_name: "Mia Cruz", phone: "09171234567" }]));
    expect(useAuth.getState().user?.display_name).toBe("Mia Cruz");
    expect(useAuth.getState().user?.phone).toBe("09171234567");
  });

  it("uploads a profile picture and shows it", async () => {
    useAuth.setState({ user: mockUser(), checked: true });
    const avatarCalls = vi.fn();
    mswServer.use(
      http.post("*/api/auth/avatar", () => {
        avatarCalls();
        return HttpResponse.json(
          mockUser({
            avatar_path: "avatars/u/a.jpg",
            avatar_url: "http://localhost:8000/media/avatars/u/a.jpg",
          }),
        );
      }),
    );
    renderSettings();
    fireEvent.change(screen.getByLabelText("Choose a profile picture"), {
      target: { files: [new File(["img"], "me.jpg", { type: "image/jpeg" })] },
    });
    await waitFor(() => expect(avatarCalls).toHaveBeenCalled());
    await waitFor(() => expect(useAuth.getState().user?.avatar_path).toBe("avatars/u/a.jpg"));
    const avatar = screen.getByRole("img", { name: "Mia's profile picture" });
    expect(avatar.tagName).toBe("IMG");
    expect(avatar).toHaveAttribute("src", "http://localhost:8000/media/avatars/u/a.jpg");
  });

  it("shows the initial-letter fallback when there is no picture", async () => {
    useAuth.setState({ user: mockUser({ avatar_path: "", avatar_url: "" }), checked: true });
    renderSettings();
    const fallback = await screen.findByRole("img", { name: "Mia's profile picture" });
    expect(fallback).toHaveTextContent("M");
    expect(screen.getByRole("button", { name: "Choose a photo" })).toBeInTheDocument();
  });

  it("shows an error when the avatar upload fails", async () => {
    useAuth.setState({ user: mockUser(), checked: true });
    mswServer.use(
      http.post("*/api/auth/avatar", () =>
        HttpResponse.json(
          { error: { code: "validation_error", message: "That file is not a readable image. Please choose a JPG or PNG." } },
          { status: 400 },
        ),
      ),
    );
    renderSettings();
    fireEvent.change(screen.getByLabelText("Choose a profile picture"), {
      target: { files: [new File(["x"], "bad.png", { type: "image/png" })] },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("not a readable image");
  });

  it("shows an error when saving the profile fails", async () => {
    useAuth.setState({ user: mockUser(), checked: true });
    mswServer.use(
      http.patch("*/api/auth/profile", () =>
        HttpResponse.json({ error: { code: "error", message: "Could not save." } }, { status: 400 }),
      ),
    );
    const user = userEvent.setup();
    renderSettings();
    await user.click(await screen.findByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not save.");
  });
});
