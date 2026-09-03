import type { ReactNode } from "react";
import { AlertCircle, Inbox, LoaderCircle } from "lucide-react";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "success" | "warning" | "danger" | "info" | "neutral" }) { return <span className={`badge badge-${tone}`}>{children}</span>; }
export function StatusBadge({ status }: { status: string | boolean }) {
  const label = typeof status === "boolean" ? (status ? "Active" : "Inactive") : status;
  const tone = ["active", "approved", "applied", "completed"].includes(label.toLowerCase()) ? "success" : ["pending", "running"].includes(label.toLowerCase()) ? "warning" : ["failed", "rejected", "inactive"].includes(label.toLowerCase()) ? "danger" : "neutral";
  return <Badge tone={tone}>{label}</Badge>;
}
export function Card({ children, className = "" }: { children: ReactNode; className?: string }) { return <section className={`card ${className}`}>{children}</section>; }
export function PageState({ loading, error, empty, onRetry }: { loading?: boolean; error?: string; empty?: string; onRetry?: () => void }) {
  if (loading) return <div className="page-state"><LoaderCircle className="spin" /><p>Loading data…</p></div>;
  if (error) return <div className="page-state error"><AlertCircle /><p>{error}</p>{onRetry && <button className="button secondary" onClick={onRetry}>Try again</button>}</div>;
  if (empty) return <div className="page-state"><Inbox /><p>{empty}</p></div>;
  return null;
}
export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: ReactNode }) { return <div className="section-header"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>; }
