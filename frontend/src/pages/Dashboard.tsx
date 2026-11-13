
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  Bot,
  Boxes,
  Lightbulb,
  Scale,
} from "lucide-react";

import { useMemo } from "react";

import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { dateTime, money, percent } from "../lib/format";

import type {
  Competitor,
  CrawlJob,
  DemandForecast,
  PriceHistory,
  Product,
  Recommendation,
} from "../types";

export function Dashboard() {
  // Fetch dashboard data
  const products = useApi<Product[]>("/products?limit=1000");
  const recommendations = useApi<Recommendation[]>(
    "/price-recommendations?limit=1000"
  );
  const competitors = useApi<Competitor[]>("/competitors?limit=1000");
  const jobs = useApi<CrawlJob[]>("/crawl-jobs?limit=1000");

  // Loading and error states
  const loading =
    products.loading ||
    recommendations.loading ||
    competitors.loading ||
    jobs.loading;

  const error =
    products.error ||
    recommendations.error ||
    competitors.error ||
    jobs.error;

  // Product ID to product name lookup
  const names = useMemo(
    () =>
      Object.fromEntries(
        (products.data || []).map((product) => [
          product.product_id,
          product.product_name,
        ])
      ),
    [products.data]
  );

  if (loading || error) {
    return (
      <PageState
        loading={loading}
        error={error}
        onRetry={() => {
          void products.refresh();
          void recommendations.refresh();
          void competitors.refresh();
          void jobs.refresh();
        }}
      />
    );
  }

  // Sort recommendations and crawl jobs by date
  const recs = [...(recommendations.data || [])].sort((a, b) =>
    b.generated_at.localeCompare(a.generated_at)
  );

  const recentJobs = [...(jobs.data || [])].sort((a, b) =>
    (b.started_at || "").localeCompare(a.started_at || "")
  );

  return (
    <>
      {/* Page header */}
      <div className="page-intro">
        <div>
          <p className="eyebrow">Pricing overview</p>
          <h2>Good morning. Here’s what’s moving.</h2>
          <p>Monitor your catalog and act on pricing opportunities.</p>
        </div>

        <span className="last-updated">
          <span className="live-dot" />
          Live data
        </span>
      </div>

      {/* Dashboard KPIs */}
      <div className="kpi-grid">
        <Kpi
          label="Total products"
          value={(products.data || []).length}
          icon={<Boxes />}
        />

        <Kpi
          label="Active / failed crawls"
          value={
            recentJobs.filter(
              (job) =>
                job.status === "pending" ||
                job.status === "running" ||
                job.status === "failed"
            ).length
          }
          icon={<Activity />}
        />

        <Kpi
          label="Pending recommendations"
          value={recs.filter((rec) => rec.status === "pending").length}
          icon={<Lightbulb />}
          accent
        />

        <Kpi
          label="Tracked competitors"
          value={
            (competitors.data || []).filter(
              (competitor) => competitor.is_active
            ).length
          }
          icon={<Scale />}
        />
      </div>

      {/* Recent activity */}
      <div className="dashboard-grid">
        {/* Recommendations */}
        <Card>
          <SectionHeader
            title="Recent recommendations"
            subtitle="Latest pricing opportunities"
          />

          <div className="activity-list">
            {recs.slice(0, 5).map((rec) => {
              const change =
                ((Number(rec.recommended_price) -
                  Number(rec.current_price || 0)) /
                  Number(rec.current_price || 1)) *
                100;

              return (
                <div
                  className="activity-row"
                  key={rec.recommendation_id}
                >
                  <div className={`trend ${change >= 0 ? "up" : "down"}`}>
                    {change >= 0 ? <ArrowUpRight /> : <ArrowDownRight />}
                  </div>

                  <div>
                    <strong>{names[rec.product_id] || "Product"}</strong>

                    <span>
                      {money(rec.current_price)} →{" "}
                      {money(rec.recommended_price)}
                    </span>
                  </div>

                  <div className="row-end">
                    <StatusBadge status={rec.status} />
                    <small>{percent(change)}</small>
                  </div>
                </div>
              );
            })}

            {!recs.length && (
              <PageState empty="No recommendations yet." />
            )}
          </div>
        </Card>

        {/* Crawl jobs */}
        <Card>
          <SectionHeader
            title="Recent crawl jobs"
            subtitle="Competitor data collection"
          />

          <div className="activity-list">
            {recentJobs.slice(0, 5).map((job) => (
              <div className="activity-row" key={job.job_id}>
                <div className="trend neutral">
                  <Bot />
                </div>

                <div>
                  <strong>
                    {competitors.data?.find(
                      (competitor) =>
                        competitor.competitor_id === job.competitor_id
                    )?.competitor_name || "Competitor crawl"}
                  </strong>

                  <span>
                    {job.records_collected} records ·{" "}
                    {dateTime(job.started_at)}
                  </span>
                </div>

                <div className="row-end">
                  <StatusBadge status={job.status} />
                </div>
              </div>
            ))}

            {!recentJobs.length && (
              <PageState empty="No crawl jobs yet." />
            )}
          </div>
        </Card>
      </div>

      {/* Demand forecast */}
      <LatestForecast product={products.data?.[0]} />

      {/* Price history */}
      <RecentChanges products={products.data || []} />
    </>
  );
}

// Reusable KPI card
function Kpi({
  label,
  value,
  icon,
  accent,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <Card className={accent ? "kpi accent" : "kpi"}>
      <div className="kpi-icon">{icon}</div>
      <span>{label}</span>
      <strong>{value.toLocaleString()}</strong>
      <small>Current workspace</small>
    </Card>
  );
}

// Recent price changes
function RecentChanges({ products }: { products: Product[] }) {
  const first = products[0];

  const history = useApi<PriceHistory[]>(
    first
      ? `/products/${first.product_id}/price-history?limit=5`
      : null
  );

  return (
    <Card>
      <SectionHeader
        title="Recent price changes"
        subtitle={
          first
            ? `Latest changes for ${first.product_name}`
            : "Catalog activity"
        }
      />

      {history.loading ? (
        <PageState loading />
      ) : history.error ? (
        <PageState error={history.error} />
      ) : !history.data?.length ? (
        <PageState empty="No price changes have been recorded." />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>Previous price</th>
                <th>New price</th>
                <th>Reason</th>
                <th>Changed</th>
              </tr>
            </thead>

            <tbody>
              {history.data.map((item) => (
                <tr key={item.history_id}>
                  <td>
                    <strong>{first.product_name}</strong>
                  </td>

                  <td>{money(item.old_price)}</td>

                  <td>
                    <strong>{money(item.new_price)}</strong>
                  </td>

                  <td>{item.change_reason}</td>

                  <td>{dateTime(item.changed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// Latest demand forecast
function LatestForecast({ product }: { product?: Product }) {
  const forecasts = useApi<DemandForecast[]>(
    product
      ? `/demand-forecasts/product/${product.product_id}/history`
      : null
  );

  const latest = forecasts.data
    ?.slice()
    .sort((a, b) => b.created_at.localeCompare(a.created_at))[0];

  return (
    <Card>
      <SectionHeader
        title="Latest demand forecast"
        subtitle={
          product
            ? `Forecast activity for ${product.product_name}`
            : "Catalog forecast activity"
        }
      />

      {forecasts.loading ? (
        <PageState loading />
      ) : forecasts.error ? (
        <PageState error={forecasts.error} />
      ) : !latest ? (
        <PageState empty="No forecasts have been generated yet." />
      ) : (
        <div className="forecast-highlight">
          <div>
            <span>Predicted demand</span>
            <strong>
              {latest.predicted_demand.toLocaleString()} units
            </strong>
          </div>

          <div>
            <span>Model</span>
            <strong>{latest.model_name || "Not provided"}</strong>
          </div>

          <div>
            <span>Generated</span>
            <strong>{dateTime(latest.created_at)}</strong>
          </div>
        </div>
      )}
    </Card>
  );
}
