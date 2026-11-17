import { startTransition, useActionState, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { authApi, REDIRECT_URI } from "@/features/auth/api";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/stores/auth";
import { Button } from "@/components/ui/button";
import { FieldShell, Input } from "@/components/ui/field";
import { GoogleButton } from "@/features/auth/components/GoogleButton";

const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password."),
});
type LoginValues = z.infer<typeof loginSchema>;

interface FormState {
  error: string | null;
}

const initialState: FormState = { error: null };

export function LoginPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const setUser = useAuth((s) => s.setUser);
  const user = useAuth((s) => s.user);
  const [callbackError, setCallbackError] = useState<string | null>(null);

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const [state, submit, pending] = useActionState(async (_prev: FormState, values: LoginValues): Promise<FormState> => {
    try {
      const u = await authApi.login(values);
      setUser(u);
      navigate("/");
      return { error: null };
    } catch (e) {
      return { error: e instanceof ApiError ? e.message : "Login failed. Please try again." };
    }
  }, initialState);

  // Google redirects back here with ?code=… — exchange it for a session.
  const code = params.get("code");
  useEffect(() => {
    if (!code) return;
    void (async () => {
      try {
        const { user: u } = await authApi.googleCallback(code, REDIRECT_URI);
        setUser(u);
        setParams({}, { replace: true });
        navigate("/");
      } catch (e) {
        setCallbackError(e instanceof ApiError ? e.message : "Google sign-in failed.");
        setParams({}, { replace: true });
      }
    })();
  }, [code, setParams, setUser, navigate]);

  useEffect(() => {
    if (user) navigate("/");
  }, [user, navigate]);

  return (
    <section style={{ padding: "72px 0" }}>
      <div className="wrap" style={{ maxWidth: 480 }}>
        <h1 className="t-h1" data-enter style={{ fontSize: "clamp(28px, 4vw, 40px)", marginBottom: 8 }}>
          Welcome back
        </h1>
        <p className="t-lead" data-enter="2" style={{ marginBottom: 32 }}>
          Log in to post flyers and fund rewards.
        </p>

        <div className="card" style={{ padding: 28 }} data-enter="3">
          {callbackError && (
            <div className="error-box" role="alert" style={{ marginBottom: 16 }}>
              {callbackError}
            </div>
          )}
          {code && !callbackError && <p className="t-body">Finishing Google sign-in…</p>}

          <form
            onSubmit={form.handleSubmit((values) => startTransition(() => submit(values)))}
            style={{ display: "flex", flexDirection: "column", gap: 16 }}
            noValidate
          >
            <FieldShell label="Email" htmlFor="login-email" error={form.formState.errors.email?.message}>
              <Input
                id="login-email"
                type="email"
                autoComplete="email"
                aria-invalid={Boolean(form.formState.errors.email)}
                {...form.register("email")}
              />
            </FieldShell>
            <FieldShell label="Password" htmlFor="login-password" error={form.formState.errors.password?.message}>
              <Input
                id="login-password"
                type="password"
                autoComplete="current-password"
                aria-invalid={Boolean(form.formState.errors.password)}
                {...form.register("password")}
              />
            </FieldShell>

            {state.error && (
              <div className="error-box" role="alert">
                {state.error}
              </div>
            )}

            <Button type="submit" disabled={pending} style={{ width: "100%" }}>
              {pending ? "Logging in…" : "Log in"}
            </Button>
          </form>

          <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "20px 0" }} aria-hidden="true">
            <span style={{ flex: 1, height: 1, background: "var(--color-line)" }} />
            <span className="t-label">or</span>
            <span style={{ flex: 1, height: 1, background: "var(--color-line)" }} />
          </div>

          <GoogleButton />

          <p className="t-small" style={{ color: "var(--color-muted)", marginTop: 20, textAlign: "center" }}>
            New to PawPrint?{" "}
            <Link to="/auth/register" style={{ fontWeight: 600 }}>
              Register free
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}
