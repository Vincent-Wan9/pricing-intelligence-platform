
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { BarChart3, LoaderCircle, LockKeyhole } from "lucide-react";

import { useAuth } from "../context/AuthContext";

export function Login() {
  // Authentication and navigation
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Form state
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Set page title
  useEffect(() => {
    document.title = "Sign in · PricePilot";
  }, []);

  // Redirect authenticated users
  if (user) {
    return <Navigate to="/" replace />;
  }

  // Handle login submission
  async function submit(e: FormEvent) {
    e.preventDefault();

    setBusy(true);
    setError("");

    try {
      await login(identifier, password);

      const destination =
        (location.state as { from?: string })?.from || "/";

      navigate(destination, { replace: true });
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Invalid credentials"
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      {/* Left panel: Branding */}
      <div className="login-panel">
        <div className="login-brand">
          <span className="brand-mark">P</span>
          <span>PricePilot</span>
        </div>

        <div className="login-copy">
          <BadgeIcon />

          <h1>
            See the market.
            <br />
            Price with confidence.
          </h1>

          <p>
            Monitor competitors, understand price position,
            and turn recommendations into action.
          </p>

          <div className="login-feature">
            <BarChart3 />

            <span>
              <strong>Pricing intelligence at a glance</strong>

              <small>
                One workspace for products, competitors,
                and pricing decisions.
              </small>
            </span>
          </div>
        </div>
      </div>

      {/* Right panel: Login form */}
      <div className="login-form-wrap">
        <form className="login-form" onSubmit={submit}>
          <div className="mobile-login-brand">
            PricePilot
          </div>

          <h2>Welcome back</h2>
          <p>Sign in to your pricing workspace</p>

          {/* Error message */}
          {error && (
            <div className="form-error">
              {error}
            </div>
          )}

          {/* Username / Email */}
          <label>
            Email or username

            <input
              autoFocus
              autoComplete="username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="you@company.com"
              required
            />
          </label>

          {/* Password */}
          <label>
            Password

            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              minLength={8}
              required
            />
          </label>

          {/* Submit button */}
          <button
            className="button primary full"
            disabled={busy}
          >
            {busy ? (
              <>
                <LoaderCircle className="spin" />
                Signing in…
              </>
            ) : (
              "Sign in"
            )}
          </button>

          {/* Security note */}
          <p className="secure-note">
            <LockKeyhole />
            Your session is stored only in this browser tab.
          </p>
        </form>
      </div>
    </div>
  );
}

// Decorative icon for the branding panel
function BadgeIcon() {
  return (
    <div className="hero-orbit">
      <span>$</span>
    </div>
  );
}
