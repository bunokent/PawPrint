import { useState } from "react";
import { authApi, REDIRECT_URI } from "@/features/auth/api";
import { Button } from "@/components/ui/button";

/** Starts the Google OAuth 2.0 flow by fetching the authorize URL, then redirecting. */
export function GoogleButton() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = async () => {
    setPending(true);
    setError(null);
    try {
      const { url } = await authApi.googleUrl(REDIRECT_URI);
      window.location.href = url;
    } catch {
      setError("Could not reach Google sign-in. Please try again.");
      setPending(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <Button type="button" variant="secondary" style={{ width: "100%" }} onClick={() => void start()} disabled={pending}>
        {pending ? "Redirecting to Google…" : "Continue with Google"}
      </Button>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
