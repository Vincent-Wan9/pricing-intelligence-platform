
import {
  ArrowLeft,
  ExternalLink,
  LoaderCircle,
  Package,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { LineChart, type ChartSeries } from "../components/LineChart";
import {
  DemandForecastChart,
  ForecastSummary,
} from "../components/DemandForecast";
import { RecommendationDetails } from "../components/RecommendationDetails";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { dateTime, money, percent } from "../lib/format";

import type {
  Competitor,
  CompetitorMapping,
  CompetitorPrice,
  DemandForecast,
  DemandHistory,
  ForecastGenerationResult,
  Inventory,
  PriceHistory,
  PricingRule,
  Product,
  Recommendation,
} from "../types";

export function ProductDetail() {
  // Route parameters and authentication
  const { id } = useParams();
  const { user } = useAuth();

  // Forecast state
  const [horizon, setHorizon] = useState(7);
  const [generating, setGenerating] = useState(false);
  const [forecastError, setForecastError] = useState("");
  const [forecastNotice, setForecastNotice] = useState("");

  // Fetch product data
  const product = useApi<Product>(
    id ? `/products/${id}` : null
  );

  const inventory = useApi<Inventory>(
    id ? `/inventory/product/${id}` : null
  );

  const rules = useApi<PricingRule[]>(
    "/pricing-rules?limit=1000"
  );

  const mappings = useApi<CompetitorMapping[]>(
    id ? `/products/${id}/competitor-mappings` : null
  );

  const prices = useApi<CompetitorPrice[]>(
    id ? `/products/${id}/competitor-prices?limit=500` : null
  );

  const history = useApi<PriceHistory[]>(
    id ? `/products/${id}/price-history?limit=100` : null
  );

  const recs = useApi<Recommendation[]>(
    id ? `/price-recommendations/product/${id}/history` : null
  );

  const competitors = useApi<Competitor[]>(
    "/competitors?limit=1000"
  );

  const demand = useApi<DemandHistory[]>(
    id ? `/demand-forecasts/history/product/${id}?limit=365` : null
  );

  const forecasts = useApi<DemandForecast[]>(
    id ? `/demand-forecasts/product/${id}/history` : null
  );

  // Product loading and error states
  if (product.loading) {
    return <PageState loading />;
  }

  if (product.error || !product.data) {
    return (
      <PageState error={product.error || "Product not found"} />
    );
  }

  const p = product.data;

  // Latest competitor prices
  const latest = latestPrices(prices.data || []);

  const values = latest.map((price) =>
    Number(price.competitor_price)
  );

  const low = values.length
    ? Math.min(...values)
    : null;

  const avg = values.length
    ? values.reduce((sum, value) => sum + value, 0) / values.length
    : null;

  const position =
    avg == null
      ? null
      : ((Number(p.current_price) - avg) / avg) * 100;

  // Product price history chart
  const productSeries = [...(history.data || [])]
    .reverse()
    .map((item) => ({
      date: item.changed_at,
      value: Number(item.new_price),
    }));

  // Competitor price history chart
  const compSeries: ChartSeries[] = (mappings.data || [])
    .map((mapping, index) => ({
      name:
        competitors.data?.find(
          (competitor) =>
            competitor.competitor_id === mapping.competitor_id
        )?.competitor_name || mapping.competitor_product_name,

      color: ["#f59e0b", "#8b5cf6", "#06b6d4"][index % 3],

      points: (prices.data || [])
        .filter(
          (price) =>
            price.competitor_product_id ===
            mapping.competitor_product_id
        )
        .sort((a, b) =>
          a.crawl_timestamp.localeCompare(b.crawl_timestamp)
        )
        .map((price) => ({
          date: price.crawl_timestamp,
          value: Number(price.competitor_price),
        })),
    }))
    .filter((series) => series.points.length);

  // Forecast permissions
  const canGenerate =
    user?.role === "editor" || user?.role === "admin";

  // Upcoming forecasts
  const forecastRows = (forecasts.data || [])
    .filter(
      (forecast) =>
        new Date(forecast.forecast_date) >=
        new Date(new Date().toDateString())
    )
    .sort((a, b) =>
      a.forecast_date.localeCompare(b.forecast_date)
    );

  // Generate demand forecast
  async function generateForecast() {
    if (!id) return;

    setGenerating(true);
    setForecastError("");
    setForecastNotice("");

    try {
      const result = await api.post<ForecastGenerationResult>(
        `/demand-forecasts/generate/${id}?horizon_days=${horizon}`
      );

      setForecastNotice(
        `${result.horizon_days}-day forecast generated with ${result.model_name}.`
      );

      await forecasts.refresh();
    } catch (error) {
      setForecastError(
        error instanceof Error
          ? error.message
          : "Unable to generate forecast"
      );
    } finally {
      setGenerating(false);
    }
  }

  return (
    <>
      {/* Back navigation */}
      <Link to="/products" className="back-link">
        <ArrowLeft />
        Back to products
      </Link>

      {/* Product header */}
      <div className="detail-title">
        <div className="product-thumb large">
          {p.product_name[0]}
        </div>

        <div>
          <div className="title-line">
            <h2>{p.product_name}</h2>
            <StatusBadge status={p.is_active} />
          </div>

          <p>
            {p.brand || "Unbranded"} · <code>{p.sku}</code>
          </p>
        </div>
      </div>

      {/* Product KPIs */}
      <div className="detail-kpis">
        <Card>
          <span>Our price</span>
          <strong>{money(p.current_price)}</strong>
          <small>
            Range {money(p.min_price)} – {money(p.max_price)}
          </small>
        </Card>

        <Card>
          <span>Lowest competitor</span>
          <strong>{money(low)}</strong>
          <small>
            {low == null
              ? "No observations"
              : `${money(Number(p.current_price) - low)} difference`}
          </small>
        </Card>

        <Card>
          <span>Market position</span>
          <strong>
            {position == null ? "—" : percent(position)}
          </strong>
          <small>Compared with market average</small>
        </Card>

        <Card>
          <span>On hand</span>
          <strong>{inventory.data?.on_hand_qty ?? "—"}</strong>
          <small>Safety stock: {p.safety_stock}</small>
        </Card>
      </div>

      {/* Product details */}
      <div className="detail-grid">
        {/* Price history chart */}
        <Card className="wide">
          <SectionHeader
            title="Price history"
            subtitle="Our price and observed competitor prices"
          />

          {history.loading || prices.loading ? (
            <PageState loading />
          ) : (
            <LineChart
              series={[
                {
                  name: "Our price",
                  color: "#2563eb",
                  points: productSeries,
                },
                ...compSeries,
              ]}
            />
          )}
        </Card>

        {/* Product information */}
        <Card>
          <SectionHeader title="Product information" />

          <dl className="details">
            <div>
              <dt>Base price</dt>
              <dd>{money(p.base_price)}</dd>
            </div>

            <div>
              <dt>Target margin</dt>
              <dd>
                {p.target_margin
                  ? `${p.target_margin}%`
                  : "—"}
              </dd>
            </div>

            <div>
              <dt>Auto pricing</dt>
              <dd>
                <StatusBadge
                  status={
                    p.auto_pricing_enabled
                      ? "Enabled"
                      : "Disabled"
                  }
                />
              </dd>
            </div>

            <div>
              <dt>Last updated</dt>
              <dd>{dateTime(p.updated_at)}</dd>
            </div>
          </dl>
        </Card>

        {/* Demand forecast */}
        <Card className="wide">
          <SectionHeader
            title="Demand forecast"
            subtitle="Historical Demand → Forecasted Demand"
            action={
              canGenerate ? (
                <div className="forecast-actions">
                  <select
                    aria-label="Forecast horizon"
                    value={horizon}
                    onChange={(event) =>
                      setHorizon(Number(event.target.value))
                    }
                  >
                    {[7, 14, 30, 60, 90].map((value) => (
                      <option key={value} value={value}>
                        {value} days
                      </option>
                    ))}
                  </select>

                  <button
                    className="button primary"
                    disabled={generating}
                    onClick={() => void generateForecast()}
                  >
                    {generating ? (
                      <LoaderCircle className="spin" />
                    ) : (
                      <Sparkles />
                    )}
                    Generate
                  </button>
                </div>
              ) : undefined
            }
          />

          {forecastNotice && (
            <div className="form-success">
              {forecastNotice}
            </div>
          )}

          {forecastError && (
            <div className="form-error">
              {forecastError}
            </div>
          )}

          {demand.loading || forecasts.loading ? (
            <PageState loading />
          ) : (
            <DemandForecastChart
              history={demand.data || []}
              forecasts={forecastRows}
            />
          )}
        </Card>

        {/* Forecast summary */}
        <ForecastSummary forecasts={forecastRows} />

        {/* Competitor comparison */}
        <Card className="wide">
          <SectionHeader
            title="Competitor comparison"
            subtitle={`${latest.length} current observations`}
          />

          {!latest.length ? (
            <PageState
              empty="No competitor prices have been collected for this product."
            />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Competitor</th>
                    <th>Product</th>
                    <th>Price</th>
                    <th>Difference</th>
                    <th>Availability</th>
                    <th>Observed</th>
                  </tr>
                </thead>

                <tbody>
                  {latest.map((price) => {
                    const mapping = mappings.data?.find(
                      (item) =>
                        item.competitor_product_id ===
                        price.competitor_product_id
                    );

                    const competitor = competitors.data?.find(
                      (item) =>
                        item.competitor_id === mapping?.competitor_id
                    );

                    const diff =
                      ((Number(p.current_price) -
                        Number(price.competitor_price)) /
                        Number(price.competitor_price)) *
                      100;

                    return (
                      <tr key={price.price_id}>
                        <td>
                          <strong>
                            {competitor?.competitor_name ||
                              "Competitor"}
                          </strong>
                        </td>

                        <td>
                          {mapping ? (
                            <a
                              href={mapping.competitor_product_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {mapping.competitor_product_name}
                              <ExternalLink />
                            </a>
                          ) : (
                            "—"
                          )}
                        </td>

                        <td>
                          <strong>
                            {money(price.competitor_price)}
                          </strong>
                        </td>

                        <td>
                          <span
                            className={
                              diff > 0 ? "negative" : "positive"
                            }
                          >
                            {diff > 0 ? (
                              <TrendingUp />
                            ) : (
                              <TrendingDown />
                            )}
                            {percent(diff)}
                          </span>
                        </td>

                        <td>
                          <StatusBadge
                            status={
                              price.in_stock === false
                                ? "Out of stock"
                                : "In stock"
                            }
                          />
                        </td>

                        <td>{dateTime(price.crawl_timestamp)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Inventory and pricing rule */}
        <Card>
          <SectionHeader title="Inventory" />

          <Info
            icon={<Package />}
            title={inventory.data?.vendor || "Not tracked"}
            body={
              inventory.data
                ? `${inventory.data.on_hand_qty} units · ${inventory.data.lead_time} day lead time`
                : "No inventory record"
            }
          />

          <SectionHeader title="Pricing rule" />

          <Info
            icon={<ShieldCheck />}
            title={
              rules.data?.find(
                (rule) => rule.rule_id === p.rule_id
              )?.rule_name || "Unknown rule"
            }
            body={
              rules.data?.find(
                (rule) => rule.rule_id === p.rule_id
              )?.rule_description || "Rule details unavailable"
            }
          />
        </Card>

        {/* Recent recommendations */}
        <Card className="wide">
          <SectionHeader title="Recent recommendations" />

          {recs.loading ? (
            <PageState loading />
          ) : !recs.data?.length ? (
            <PageState
              empty="No recommendations for this product."
            />
          ) : (
            <div className="recommendation-list">
              {recs.data.slice(0, 5).map((rec) => (
                <div
                  className="recommendation-item"
                  key={rec.recommendation_id}
                >
                  <div className="recommendation-head">
                    <strong>
                      {money(rec.recommended_price)}
                    </strong>

                    <StatusBadge status={rec.status} />

                    <small>
                      {dateTime(rec.generated_at)}
                    </small>
                  </div>

                  <p>{rec.recommendation_reason}</p>

                  <RecommendationDetails
                    recommendation={rec}
                    product={p}
                    forecast={forecastRows[0]}
                    competitorPrice={latest[0]}
                    inventory={inventory.data || undefined}
                    rule={rules.data?.find(
                      (rule) => rule.rule_id === rec.rule_id
                    )}
                  />
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}

// Get the latest observed price for each competitor product
function latestPrices(prices: CompetitorPrice[]) {
  return Object.values(
    prices.reduce<Record<string, CompetitorPrice>>(
      (accumulator, price) => {
        const previous =
          accumulator[price.competitor_product_id];

        if (
          !previous ||
          price.crawl_timestamp > previous.crawl_timestamp
        ) {
          accumulator[price.competitor_product_id] = price;
        }

        return accumulator;
      },
      {}
    )
  );
}

// Reusable information block
function Info({
  icon,
  title,
  body,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
}) {
  return (
    <div className="info-block">
      <span>{icon}</span>

      <div>
        <strong>{title}</strong>
        <p>{body}</p>
      </div>
    </div>
  );
}
