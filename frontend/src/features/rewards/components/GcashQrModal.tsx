import { useQuery } from "@tanstack/react-query";
import { rewardStatusQuery, type RewardInit } from "@/features/rewards/api";
import { Button } from "@/components/ui/button";
import { QrImage } from "@/components/QrImage";
import { formatMoney } from "@/lib/utils";

/**
 * GCash / QR Ph payment: renders the provider QR payload and polls the
 * transaction status until it leaves `pending`.
 */
export function GcashQrModal({ init, onDone }: { init: RewardInit; onDone: () => void }) {
  const status = useQuery(rewardStatusQuery(init.transaction_id));
  const payload = init.qr_payload || init.checkout_url;

  const current = status.data?.status ?? "pending";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "center", textAlign: "center" }}>
      <p className="t-body">
        Scan with <strong>GCash</strong> to pay{" "}
        <strong>{formatMoney(init.amount_cents, init.currency)}</strong> toward the reward.
      </p>
      {payload ? (
        <div data-testid="gcash-qr">
          <QrImage value={payload} size={220} alt="GCash QR code for the reward payment" />
        </div>
      ) : (
        <p className="error-box" role="alert">
          The provider did not return a QR code.
        </p>
      )}
      {current === "pending" && (
        <p className="t-small" style={{ color: "var(--color-muted)" }} role="status">
          Waiting for payment… this page updates automatically.
        </p>
      )}
      {current === "succeeded" && (
        <div className="badge badge--outreach" role="status" style={{ height: 32, fontSize: 14 }} data-testid="gcash-success">
          Payment received — thank you!
        </div>
      )}
      {current === "failed" && (
        <div className="error-box" role="alert" data-testid="gcash-failed">
          Payment failed. You can close this dialog and try again.
        </div>
      )}
      <Button variant="secondary" onClick={onDone}>
        {current === "succeeded" ? "Done" : "Close"}
      </Button>
    </div>
  );
}
