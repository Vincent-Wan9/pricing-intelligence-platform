
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Clock3,
  LoaderCircle,
  Play,
  RefreshCw,
  Timer,
} from "lucide-react";

import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { CrawlJobTable } from "../components/CrawlJobTable";
import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { dateTime } from "../lib/format";

import type { Competitor, CrawlJob, CrawlSchedule } from "../types";

export function CrawlJobs() {
  // URL parameters and authentication
  const [params] = useSearchParams();
  const selected = params.get("competitor") || "";
  const { user } = useAuth();

  // Component state
  const [submitting, setSubmitting] = useState("");
  const [notice, setNotice] = useState("");
  const [actionError, setActionError] = useState("");

  // Fetch initial data
  const initialJobs = useApi<CrawlJob[]>("/crawl-jobs?limit=1000");
  const competitors = useApi<Competitor[]>("/competitors?limit=1000");
  const schedule = useApi<CrawlSchedule>("/crawl-jobs/schedule/status");

  // Detect active crawl jobs
  const active =
    initialJobs.data?.some(
      (job) => job.status === "pending" || job.status === "running"
    ) ?? false;

  // Poll active jobs every 3 seconds
  const polledJobs = useApi<CrawlJob[]>(
    active ? "/crawl-jobs?limit=1000" : null,
    active ? 3000 : 0
  );

  const jobs = polledJobs.data || initialJobs.data || [];

  // User permissions
  const canTrigger = user?.role === "editor" || user?.role === "admin";

  // Filter jobs by selected competitor
  const filtered = useMemo(
    () =>
      selected
        ? jobs.filter((job) => job.competitor_id === selected)
        : jobs,
    [jobs, selected]
  );

  // Submit a new crawl job
  async function trigger(competitorId: string) {
    setSubmitting(competitorId);
    setNotice("");
    setActionError("");

    try {
      const job = await api.post<CrawlJob>(
        `/crawl-jobs/competitors/${competitorId}`
      );

      setNotice(
        `Crawl submitted. Job ${job.job_id.slice(0, 8)} is ${job.status}.`
      );

      await initialJobs.refresh();
    } catch (error) {
      setActionError(
        error instanceof Error
          ? error.message
          : "Unable to submit crawl"
      );
    } finally {
      setSubmitting("");
    }
  }

  // Loading state
  if (
    initialJobs.loading ||
    competitors.loading ||
    schedule.loading
  ) {
    return <PageState loading />;
  }

  // Error state
  if (
    initialJobs.error ||
    competitors.error ||
    schedule.error
  ) {
    return (
      <PageState
        error={
          initialJobs.error ||
          competitors.error ||
          schedule.error
        }
      />
    );
  }

  return (
    <>
      {/* Page header */}
      <div className="page-intro">
        <div>
          <p className="eyebrow">Background collection</p>
          <h2>Competitor crawl jobs</h2>
          <p>Submit collection work and follow its progress without waiting.</p>
        </div>

        <button
          className="button secondary"
          onClick={() => void initialJobs.refresh()}
        >
          <RefreshCw />
          Refresh
        </button>
      </div>

      {/* Notifications */}
      {notice && (
        <div className="form-success">
          {notice}
        </div>
      )}

      {actionError && (
        <div className="form-error">
          {actionError}
        </div>
      )}

      {/* Crawl job statistics */}
      <div className="kpi-grid crawl-kpis">
        <Mini
          label="Pending"
          value={jobs.filter((job) => job.status === "pending").length}
          icon={<Clock3 />}
        />

        <Mini
          label="Running"
          value={jobs.filter((job) => job.status === "running").length}
          icon={<Bot />}
        />

        <Mini
          label="Completed"
          value={jobs.filter((job) => job.status === "completed").length}
          icon={<CheckCircle2 />}
        />

        <Mini
          label="Failed"
          value={jobs.filter((job) => job.status === "failed").length}
          icon={<AlertTriangle />}
        />
      </div>

      {/* Dashboard */}
      <div className="dashboard-grid">
        {/* Automated scraping schedule */}
        <Card>
          <SectionHeader
            title="Automated scraping"
            subtitle="Read-only scheduler configuration"
          />

          <dl className="details">
            <div>
              <dt>Status</dt>
              <dd>
                <StatusBadge
                  status={schedule.data?.enabled ? "Enabled" : "Disabled"}
                />
              </dd>
            </div>

            <div>
              <dt>Interval</dt>
              <dd>{formatInterval(schedule.data?.interval_seconds)}</dd>
            </div>

            <div>
              <dt>Most recent crawl</dt>
              <dd>{dateTime(schedule.data?.last_crawl_at)}</dd>
            </div>

            <div>
              <dt>Next scheduled crawl</dt>
              <dd>{dateTime(schedule.data?.next_scheduled_crawl)}</dd>
            </div>
          </dl>

          {!schedule.data?.next_scheduled_crawl && (
            <p className="permission-note">
              <Timer />
              The worker does not expose its next exact tick.
            </p>
          )}
        </Card>

        {/* Manual crawl submission */}
        <Card>
          <SectionHeader
            title="Start a crawl"
            subtitle={
              canTrigger
                ? "Work is submitted to a background worker."
                : "Editor or admin access is required."
            }
          />

          <div className="crawl-actions">
            {competitors.data
              ?.filter((competitor) => competitor.is_active)
              .map((competitor) => (
                <button
                  key={competitor.competitor_id}
                  className="button secondary"
                  disabled={
                    !canTrigger ||
                    !!submitting ||
                    jobs.some(
                      (job) =>
                        job.competitor_id === competitor.competitor_id &&
                        (job.status === "pending" || job.status === "running")
                    )
                  }
                  onClick={() => void trigger(competitor.competitor_id)}
                >
                  {submitting === competitor.competitor_id ? (
                    <LoaderCircle className="spin" />
                  ) : (
                    <Play />
                  )}

                  {competitor.competitor_name}
                </button>
              ))}
          </div>
        </Card>
      </div>

      {/* Crawl job history */}
      <Card>
        <SectionHeader
          title={selected ? "Filtered crawl history" : "Crawl job history"}
          subtitle={
            active
              ? "Active jobs refresh every 3 seconds"
              : "Recent competitor data collection runs"
          }
        />

        <CrawlJobTable
          jobs={filtered}
          competitors={competitors.data || []}
        />
      </Card>
    </>
  );
}

// Reusable KPI card
function Mini({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <Card className="mini-kpi">
      <span>
        {icon}
        {label}
      </span>
      <strong>{value}</strong>
    </Card>
  );
}

// Format crawl schedule interval
function formatInterval(seconds?: number) {
  if (!seconds) {
    return "—";
  }

  if (seconds % 86400 === 0) {
    return `Every ${seconds / 86400} day${seconds === 86400 ? "" : "s"}`;
  }

  if (seconds % 3600 === 0) {
    return `Every ${seconds / 3600} hours`;
  }

  return `Every ${seconds} seconds`;
}
