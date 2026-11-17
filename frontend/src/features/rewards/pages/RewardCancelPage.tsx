import { Link, useSearchParams } from "react-router";
import { useRewardStatus } from "@/features/rewards/api";
import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/utils";

export function RewardCancelPage() {
  const [params] = useSearchParams();
  const tx = params.get("tx");
  const status = useRewardStatus(tx ?? undefined);

  const body = status.data
    ? `No charge was made (${formatMoney(status.data.amount_cents, status.data.currency ?? "PHP")} was only pending). You can fund the reward again any time from the flyer page.`
    : "No charge was made. You can fund the reward again any time from the flyer page.";

  return (
    <section style={{ padding: "72px 0" }}>
      <div className="wrap" style={{ maxWidth: 520 }}>
        <h1 className="t-h1" data-enter style={{ fontSize: "clamp(28px, 4vw, 40px)", marginBottom: 12 }}>
          Payment cancelled
        </h1>
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
