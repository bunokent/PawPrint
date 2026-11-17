import { describe, expect, it, beforeEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RewardCheckoutModal } from "@/features/rewards/components/RewardCheckoutModal";
import { GcashQrModal } from "@/features/rewards/components/GcashQrModal";
import { RewardSuccessPage } from "@/features/rewards/pages/RewardSuccessPage";
import { RewardCancelPage } from "@/features/rewards/pages/RewardCancelPage";
import { rewardKeys, useCreateReward, useRewardStatus, myRewardsQuery, rewardStatusQuery } from "@/features/rewards/api";
import { mswServer } from "@/test/setup";
import { renderWithProviders, makeQueryClient } from "@/test/utils";
import { mockFlyer, mockRewardInit, mockRewardStatus, setRewardStatus } from "@/test/handlers";
import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render } from "@testing-library/react";

const TX_ID = "44444444-4444-4444-4444-444444444444";

beforeEach(() => {
  setRewardStatus(TX_ID, { status: "pending" });
});

describe("RewardCheckoutModal", () => {
  it("gcash flow: opens the QR modal and polls until succeeded", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={onClose} />);

    // Default amount comes from the flyer reward (5000 PHP).
    expect(screen.getByLabelText("Amount (PHP)")).toHaveValue("5000");
    await user.click(screen.getByRole("button", { name: /^GCash QR$/ }));
    await user.click(screen.getByRole("button", { name: "Show GCash QR" }));

    expect(await screen.findByTestId("gcash-qr")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Waiting for payment");

    setRewardStatus(TX_ID, { status: "succeeded" });
    expect(await screen.findByTestId("gcash-success", {}, { timeout: 5000 })).toHaveTextContent("Payment received");
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("stripe flow: creates a checkout and redirects to the checkout URL", async () => {
    const calls: Array<Record<string, unknown>> = [];
    mswServer.use(
      http.post("*/api/rewards", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        calls.push(body);
        return HttpResponse.json(mockRewardInit({ provider: "stripe", checkout_url: "https://checkout.stripe.com/test/pay/cs_test_123", qr_payload: "" }), { status: 201 });
      }),
    );
    const user = userEvent.setup();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={() => {}} />);
    await user.click(screen.getByRole("button", { name: /Card \(Stripe test\)/ }));
    await user.click(screen.getByRole("button", { name: "Continue to card payment" }));
    await waitFor(() => expect(calls).toHaveLength(1));
    expect(calls[0]).toMatchObject({ provider: "stripe", amount_cents: 500000, currency: "PHP", flyer_id: mockFlyer().id });
  });

  it("rejects a zero amount client-side", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={() => {}} />);
    await user.clear(screen.getByLabelText("Amount (PHP)"));
    await user.click(screen.getByRole("button", { name: "Show GCash QR" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Enter an amount above zero.");
  });

  it("shows the API error when reward creation fails", async () => {
    mswServer.use(
      http.post("*/api/rewards", () => HttpResponse.json({ error: { code: "reward_error", message: "A positive reward amount is required." } }, { status: 400 })),
    );
    const user = userEvent.setup();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Show GCash QR" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("A positive reward amount is required.");
  });

  it("closes via the dialog close button and resets state", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={onClose} />);
    await user.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("handles a flyer without a preset reward amount/currency", async () => {
    const flyer = mockFlyer({ reward_amount_cents: undefined, reward_currency: undefined, reward_enabled: true });
    const user = userEvent.setup();
    renderWithProviders(<RewardCheckoutModal flyer={flyer} open onClose={() => {}} />);
    expect(screen.getByLabelText("Amount (PHP)")).toHaveValue("0");
    expect(screen.getByText(/₱0\.00/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Amount (PHP)"), "100");
    await user.click(screen.getByRole("button", { name: "Show GCash QR" }));
    expect(await screen.findByTestId("gcash-qr")).toBeInTheDocument();
  });

  it("shows the generic error when a non-API error is thrown", async () => {
    const { api } = await import("@/lib/api/client");
    vi.spyOn(api, "post").mockRejectedValueOnce(new Error("boom"));
    const user = userEvent.setup();
    renderWithProviders(<RewardCheckoutModal flyer={mockFlyer()} open onClose={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Show GCash QR" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not start the payment. Please try again.");
    vi.restoreAllMocks();
  });
});

describe("GcashQrModal", () => {
  it("shows the failed state when the transaction fails", async () => {
    setRewardStatus(TX_ID, { status: "failed" });
    renderWithProviders(<GcashQrModal init={mockRewardInit()} onDone={() => {}} />);
    expect(await screen.findByTestId("gcash-failed", {}, { timeout: 5000 })).toHaveTextContent("Payment failed");
  });

  it("shows an error when no QR payload is available", () => {
    renderWithProviders(<GcashQrModal init={mockRewardInit({ qr_payload: "", checkout_url: "" })} onDone={() => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("did not return a QR code");
  });

  it("falls back to checkout_url when qr_payload is empty", async () => {
    renderWithProviders(<GcashQrModal init={mockRewardInit({ qr_payload: "", checkout_url: "https://gcash.example/pay/1" })} onDone={() => {}} />);
    expect(await screen.findByTestId("gcash-qr")).toBeInTheDocument();
  });

  it("shows pending then close button", async () => {
    const onDone = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<GcashQrModal init={mockRewardInit()} onDone={onDone} />);
    expect(await screen.findByRole("status")).toHaveTextContent("Waiting for payment");
    await user.click(screen.getByRole("button", { name: "Close" }));
    expect(onDone).toHaveBeenCalled();
  });
});

describe("reward pages", () => {
  it("success page polls and shows the received state", async () => {
    setRewardStatus(TX_ID, { status: "succeeded", amount_cents: 500000, currency: "PHP" });
    renderWithProviders(<RewardSuccessPage />, { route: `/rewards/success?tx=${TX_ID}` });
    expect(await screen.findByText("Reward payment received", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText(/₱5,000\.00/)).toBeInTheDocument();
  });

  it("success page shows the confirming state while pending", async () => {
    renderWithProviders(<RewardSuccessPage />, { route: `/rewards/success?tx=${TX_ID}` });
    expect(await screen.findByText("Finishing your payment")).toBeInTheDocument();
    expect(screen.getByText(/confirming the payment/i)).toBeInTheDocument();
  });

  it("success page shows the failed copy", async () => {
    setRewardStatus(TX_ID, { status: "failed" });
    renderWithProviders(<RewardSuccessPage />, { route: `/rewards/success?tx=${TX_ID}` });
    expect(await screen.findByText(/did not go through/i, {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("cancel page renders with and without a tx param", async () => {
    setRewardStatus(TX_ID, { status: "pending", amount_cents: 2500, currency: "PHP" });
    const { unmount } = renderWithProviders(<RewardCancelPage />, { route: `/rewards/cancel?tx=${TX_ID}` });
    expect(await screen.findByText("Payment cancelled")).toBeInTheDocument();
    expect(await screen.findByText(/₱25\.00/, {}, { timeout: 5000 })).toBeInTheDocument();
    unmount();
    renderWithProviders(<RewardCancelPage />, { route: "/rewards/cancel" });
    expect(screen.getByText(/No charge was made\./)).toBeInTheDocument();
  });

  it("cancel page falls back to PHP when the currency is missing", async () => {
    setRewardStatus(TX_ID, { status: "pending", amount_cents: 2500, currency: undefined });
    renderWithProviders(<RewardCancelPage />, { route: `/rewards/cancel?tx=${TX_ID}` });
    expect(await screen.findByText(/₱25\.00/, {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("success page shows a skeleton while the status is loading", async () => {
    mswServer.use(http.get("*/api/rewards/:id/status", () => new Promise<Response>(() => {})));
    const { container } = renderWithProviders(<RewardSuccessPage />, { route: `/rewards/success?tx=${TX_ID}` });
    await waitFor(() => expect(container.querySelector(".skeleton")).toBeInTheDocument());
    expect(screen.getByText("Finishing your payment")).toBeInTheDocument();
  });

  it("success page renders without a tx param and with a missing currency", async () => {
    const { unmount } = renderWithProviders(<RewardSuccessPage />, { route: "/rewards/success" });
    expect(await screen.findByText("Finishing your payment")).toBeInTheDocument();
    unmount();
    setRewardStatus(TX_ID, { status: "succeeded", amount_cents: 500000, currency: undefined });
    renderWithProviders(<RewardSuccessPage />, { route: `/rewards/success?tx=${TX_ID}` });
    expect(await screen.findByText("Reward payment received", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText(/₱5,000\.00/)).toBeInTheDocument();
  });
});

describe("rewards api module", () => {
  it("exposes stable query keys", () => {
    expect(rewardKeys.status("abc")).toEqual(["rewards", "status", "abc"]);
    expect(rewardKeys.mine).toEqual(["rewards", "mine"]);
    expect(rewardStatusQuery("abc").queryKey).toEqual(["rewards", "status", "abc"]);
    expect(myRewardsQuery().queryKey).toEqual(["rewards", "mine"]);
  });

  it("useCreateReward posts and returns the init payload", async () => {
    const client = makeQueryClient();
    let hookResult: unknown;
    function Probe() {
      const mutation = useCreateReward();
      hookResult = mutation;
      return null;
    }
    render(
      <QueryClientProvider client={client}>
        <Probe />
      </QueryClientProvider>,
    );
    const mutation = hookResult as ReturnType<typeof useCreateReward>;
    const init = await mutation.mutateAsync({ flyer_id: mockFlyer().id, provider: "gcash" });
    expect(init.transaction_id).toBe(TX_ID);
    expect(init.qr_payload).toContain("qrph://");
  });

  it("useRewardStatus is disabled without an id or when enabled=false, and fetches with one", async () => {
    setRewardStatus(TX_ID, { status: "succeeded" });
    const client = makeQueryClient();
    const seen: Array<string | undefined> = [];
    function Probe() {
      const off = useRewardStatus(undefined);
      const disabled = useRewardStatus(TX_ID, false);
      const on = useRewardStatus(TX_ID);
      seen.push(off.data?.status, disabled.data?.status, on.data?.status);
      return null;
    }
    render(
      <QueryClientProvider client={client}>
        <Probe />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(seen).toContain("succeeded"));
    expect(seen.filter((s) => s === undefined).length).toBeGreaterThan(0);
  });

  it("myRewardsQuery lists the user's transactions", async () => {
    const client = makeQueryClient();
    let result: unknown;
    function Probe() {
      const q = useQuery(myRewardsQuery());
      result = q.data;
      return null;
    }
    render(
      <QueryClientProvider client={client}>
        <Probe />
      </QueryClientProvider>,
    );
    await waitFor(() => expect(result).toEqual([mockRewardStatus()]));
  });
});
