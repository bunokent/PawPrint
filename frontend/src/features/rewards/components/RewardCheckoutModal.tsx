import { useState } from "react";
import { CreditCard, Smartphone } from "lucide-react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { FieldShell, Input } from "@/components/ui/field";
import { ErrorBox } from "@/components/ui/feedback";
import { useCreateReward, type RewardInit } from "@/features/rewards/api";
import type { Flyer } from "@/features/flyers/api";
import { ApiError } from "@/lib/api/client";
import { GcashQrModal } from "@/features/rewards/components/GcashQrModal";
import { formatMoney } from "@/lib/utils";

type Provider = "stripe" | "gcash";

/**
 * Reward funding dialog: pick an amount and a provider — Stripe test checkout
 * (redirect) or GCash QR (inline modal + status polling).
 */
export function RewardCheckoutModal({ flyer, open, onClose }: { flyer: Flyer; open: boolean; onClose: () => void }) {
  const createReward = useCreateReward();
  const [provider, setProvider] = useState<Provider>("gcash");
  const [pesos, setPesos] = useState(String(((flyer.reward_amount_cents ?? 0) / 100).toFixed(0)));
  const [error, setError] = useState<string | null>(null);
  const [tx, setTx] = useState<RewardInit | null>(null);

  const submit = async () => {
    setError(null);
    const amount_cents = Math.round(Number(pesos) * 100);
    if (!Number.isFinite(amount_cents) || amount_cents <= 0) {
      setError("Enter an amount above zero.");
      return;
    }
    try {
      const init = await createReward.mutateAsync({
        flyer_id: flyer.id,
        provider,
        amount_cents,
        currency: flyer.reward_currency || "PHP",
      });
      if (provider === "stripe" && init.checkout_url) {
        window.location.href = init.checkout_url;
        return;
      }
      setTx(init);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start the payment. Please try again.");
    }
  };

  const close = () => {
    setTx(null);
    setError(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={close} title={tx ? "Pay with GCash" : `Fund the reward for ${flyer.pet.name}`}>
      {tx ? (
        <GcashQrModal init={tx} onDone={close} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p className="t-body" style={{ color: "var(--color-muted)" }}>
            Default reward:{" "}
            <strong>{formatMoney(flyer.reward_amount_cents ?? 0, flyer.reward_currency ?? "PHP")}</strong>. You can
            adjust the amount.
          </p>
          <FieldShell label="Amount (PHP)" htmlFor="reward-amount">
            <Input
              id="reward-amount"
              inputMode="decimal"
              value={pesos}
              onChange={(e) => setPesos(e.target.value)}
              aria-invalid={Boolean(error)}
            />
          </FieldShell>
          <div className="btn-row" role="group" aria-label="Payment provider">
            <Button
              type="button"
              variant={provider === "gcash" ? "sage" : "secondary"}
              aria-pressed={provider === "gcash"}
              onClick={() => setProvider("gcash")}
            >
              <Smartphone size={16} /> GCash QR
            </Button>
            <Button
              type="button"
              variant={provider === "stripe" ? "primary" : "secondary"}
              aria-pressed={provider === "stripe"}
              onClick={() => setProvider("stripe")}
            >
              <CreditCard size={16} /> Card (Stripe test)
            </Button>
          </div>
          {error && <ErrorBox message={error} />}
          <Button onClick={() => void submit()} disabled={createReward.isPending}>
            {createReward.isPending ? "Starting payment…" : provider === "stripe" ? "Continue to card payment" : "Show GCash QR"}
          </Button>
        </div>
      )}
    </Modal>
  );
}
