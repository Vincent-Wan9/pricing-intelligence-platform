import { ExternalLink, Link2, LoaderCircle, Play, Scale } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { dateTime } from "../lib/format";

import type {
  Competitor,
  CompetitorMapping,
  CrawlJob,
  Product,
} from "../types";

export function Competitors() {
  // Fetch data
  const competitors = useApi<Competitor[]>("/competitors?limit=1000");
  const mappings = useApi<CompetitorMapping[]>(
    "/competitor-products?limit=1000",
  );
  const products = useApi<Product[]>("/products?limit=1000");
  const jobs = useApi<CrawlJob[]>("/crawl-jobs?limit=1000");

  // Authentication
  const { user } = useAuth();

  const canTrigger = user?.role === "editor" || user?.role === "admin";

  // Component state
  const [acting, setActing] = useState("");
  const [notice, setNotice] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // Submit a crawl job
  async function crawl(competitorId: string) {
    setActing(competitorId);
    setNotice("");
    setErrorMessage("");

    try {
      await api.post(`/crawl-jobs/competitors/${competitorId}`);

      setNotice("Crawl submitted to the background worker.");

      await jobs.refresh();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Unable to submit crawl",
      );
    } finally {
      setActing("");
    }
  }

  // Loading and error states
  const loading =
    competitors.loading || mappings.loading || products.loading || jobs.loading;

  const error =
    competitors.error || mappings.error || products.error || jobs.error;

  if (loading || error) {
    return <PageState loading={loading} error={error} />;
  }

  return (
    <>
      {/* Page header */}
      <div className="page-intro">
        <div>
          <p className="eyebrow">Market coverage</p>
          <h2>Competitors & product mappings</h2>
          <p>See who you track and which catalog items are connected.</p>
        </div>
      </div>

      {/* Notifications */}
      {notice && <div className="form-success">{notice}</div>}
      {errorMessage && <div className="form-error">{errorMessage}</div>}

      {/* Competitor cards */}
      <div className="competitor-cards">
        {competitors.data?.map((competitor) => {
          const active = jobs.data?.some(
            (job) =>
              job.competitor_id === competitor.competitor_id &&
              (job.status === "pending" || job.status === "running"),
          );

          return (
            <Card key={competitor.competitor_id} className="competitor-card">
              <div className="competitor-icon">
                <Scale />
              </div>

              <div>
                <div className="title-line">
                  <h3>{competitor.competitor_name}</h3>
                  <StatusBadge status={competitor.is_active} />
                </div>

                <a
                  href={competitor.website_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Visit website <ExternalLink />
                </a>

                <p>
                  {mappings.data?.filter(
                    (mapping) =>
                      mapping.competitor_id === competitor.competitor_id,
                  ).length || 0}{" "}
                  mapped products
                </p>

                <div className="card-actions">
                  <button
                    className="button secondary compact"
                    disabled={!canTrigger || !!acting || active}
                    onClick={() => void crawl(competitor.competitor_id)}
                  >
                    {acting === competitor.competitor_id ? (
                      <LoaderCircle className="spin" />
                    ) : (
                      <Play />
                    )}

                    {active ? "Crawl active" : "Run crawl"}
                  </button>

                  <Link
                    className="text-link"
                    to={`/crawl-jobs?competitor=${competitor.competitor_id}`}
                  >
                    View jobs
                  </Link>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Competitor-product mappings */}
      <Card>
        <SectionHeader
          title="Competitor-product mappings"
          subtitle={`${mappings.data?.length || 0} catalog connections`}
        />

        {!mappings.data?.length ? (
          <PageState empty="No competitor products are mapped yet." />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Our product</th>
                  <th>Competitor</th>
                  <th>Competitor product</th>
                  <th>SKU</th>
                  <th>Last collected</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {mappings.data.map((mapping) => {
                  const product = products.data?.find(
                    (p) => p.product_id === mapping.product_id,
                  );

                  const competitor = competitors.data?.find(
                    (c) => c.competitor_id === mapping.competitor_id,
                  );

                  return (
                    <tr key={mapping.competitor_product_id}>
                      <td>
                        <Link to={`/products/${mapping.product_id}`}>
                          <strong>
                            {product?.product_name || "Unknown product"}
                          </strong>
                        </Link>
                      </td>

                      <td>{competitor?.competitor_name || "Unknown"}</td>

                      <td>
                        <a
                          href={mapping.competitor_product_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <Link2 />
                          {mapping.competitor_product_name}
                        </a>
                      </td>

                      <td>
                        <code>{mapping.competitor_sku}</code>
                      </td>

                      <td>{dateTime(mapping.last_crawled_at)}</td>

                      <td>
                        <StatusBadge
                          status={
                            mapping.last_crawl_error
                              ? "Failed"
                              : mapping.is_active
                          }
                        />

                        {mapping.last_crawl_error && (
                          <small className="table-sub error-message">
                            {mapping.last_crawl_error}
                          </small>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}
