import { Link, useSearchParams } from "react-router";
import { useRewardStatus } from "@/features/rewards/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/feedback";
import { formatMoney } from "@/lib/utils";

export function RewardSuccessPage() {
  const [params] = useSearchParams();
  const tx = params.get("tx");
  const status = useRewardStatus(tx ?? undefined);
  const current = status.data?.status ?? "pending";

  const heading = current === "succeeded" ? "Reward payment received" : "Finishing your payment";
  let body: string;
  if (current === "succeeded" && status.data) {
    body = `Thank you — ${formatMoney(status.data.amount_cents, status.data.currency ?? "PHP")} is on its way to the finder. The pet's family will be in touch.`;
  } else if (current === "failed") {
    body = "The payment did not go through. No money was taken — you can try again from the flyer.";
  } else {
    body = "We're confirming the payment with the provider. This page updates automatically.";
  }

  return (
    <section style={{ padding: "72px 0" }}>
      <div className="wrap" style={{ maxWidth: 520 }}>
        <h1 className="t-h1" data-enter style={{ fontSize: "clamp(28px, 4vw, 40px)", marginBottom: 12 }}>
          {heading}
        </h1>
        {status.isLoading && <Skeleton style={{ height: 24, width: "60%", marginBottom: 16 }} />}
        <p className="t-lead" data-enter="2" style={{ marginBottom: 24 }}>
          {body}
        </p>
        <div className="btn-row" data-enter="3">
          <Button asChild>
            <Link to="/flyers">Browse flyers</Link>
          </Button>
          <Button variant="secondary" asChild>
            <Link to="/">Back home</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
