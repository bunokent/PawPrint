import { Link, NavLink, Outlet } from "react-router";
import { useAuth } from "@/stores/auth";
import { Button } from "@/components/ui/button";

function PawMark() {
  return (
    <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="10" cy="11" r="4" fill="currentColor" />
      <circle cx="22" cy="11" r="4" fill="currentColor" />
      <circle cx="16" cy="21" r="7" fill="currentColor" />
    </svg>
  );
}

export function AppShell() {
  const { user, logout } = useAuth();
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="nav no-print">
        <div className="wrap nav-inner">
          <Link to="/" style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--color-ink)", textDecoration: "none" }}>
            <PawMark />
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 900, fontSize: 22 }}>PawPrint</span>
          </Link>
          <nav className="nav-links" aria-label="Main">
            <NavLink className="nav-link" to="/flyers">Flyers</NavLink>
            {user && <NavLink className="nav-link" to="/my-flyers">My flyers</NavLink>}
            {user ? (
              <>
                <NavLink className="nav-link" to="/builder">New flyer</NavLink>
                <span className="t-small" style={{ color: "var(--color-muted)" }}>{user.display_name || user.email}</span>
                <Button variant="secondary" style={{ height: 36, padding: "0 16px" }} onClick={() => void logout()}>
                  Log out
                </Button>
              </>
            ) : (
              <>
                <NavLink className="nav-link" to="/auth/login">Log in</NavLink>
                <Button style={{ height: 36, padding: "0 16px" }} asChild>
                  <Link to="/auth/register">Register free</Link>
                </Button>
              </>
            )}
          </nav>
        </div>
      </header>
      <main id="top" style={{ flex: 1 }}>
        <Outlet />
      </main>
      <footer className="no-print" style={{ borderTop: "1px solid var(--color-line)", marginTop: 64, padding: "32px 0" }}>
        <div className="wrap t-small" style={{ color: "var(--color-muted)", display: "flex", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
          <span>PawPrint — bring them home. Lost-pet alerts and adoption flyers, print-ready in one click.</span>
          <span>Contacts: hello@pawprint.example</span>
        </div>
      </footer>
    </div>
  );
}
