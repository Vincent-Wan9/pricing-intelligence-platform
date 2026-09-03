import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { BarChart3, LoaderCircle, LockKeyhole } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export function Login() {
  const { user, login } = useAuth(); const navigate = useNavigate(); const location = useLocation();
  const [identifier, setIdentifier] = useState(""); const [password, setPassword] = useState(""); const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => { document.title = "Sign in · PricePilot"; }, []);
  if (user) return <Navigate to="/" replace />;
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setError(""); try { await login(identifier, password); navigate((location.state as { from?: string })?.from || "/", { replace: true }); } catch (e) { setError(e instanceof Error ? e.message : "Invalid credentials"); } finally { setBusy(false); } }
  return <div className="login-page"><div className="login-panel"><div className="login-brand"><span className="brand-mark">P</span><span>PricePilot</span></div><div className="login-copy"><BadgeIcon /><h1>See the market.<br/>Price with confidence.</h1><p>Monitor competitors, understand price position, and turn recommendations into action.</p><div className="login-feature"><BarChart3 /><span><strong>Pricing intelligence at a glance</strong><small>One workspace for products, competitors, and pricing decisions.</small></span></div></div></div><div className="login-form-wrap"><form className="login-form" onSubmit={submit}><div className="mobile-login-brand">PricePilot</div><h2>Welcome back</h2><p>Sign in to your pricing workspace</p>{error && <div className="form-error">{error}</div>}<label>Email or username<input autoFocus autoComplete="username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} placeholder="you@company.com" required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" minLength={8} required /></label><button className="button primary full" disabled={busy}>{busy ? <><LoaderCircle className="spin"/> Signing in…</> : "Sign in"}</button><p className="secure-note"><LockKeyhole /> Your session is stored only in this browser tab.</p></form></div></div>;
}
function BadgeIcon() { return <div className="hero-orbit"><span>$</span></div>; }
