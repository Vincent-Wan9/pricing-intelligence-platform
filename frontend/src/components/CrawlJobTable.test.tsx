import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { CrawlJobTable } from "./CrawlJobTable";

const competitors = [
  {
    competitor_id: "c1",
    competitor_name: "Market Co",
    website_url: "https://example.com",
    is_active: true,
    created_at: "2026-01-01",
  },
];
describe("CrawlJobTable", () => {
  it("renders crawl status, records, and failures", () => {
    render(
      <MemoryRouter>
        <CrawlJobTable
          competitors={competitors}
          jobs={[
            {
              job_id: "j1",
              competitor_id: "c1",
              status: "failed",
              started_at: "2026-01-01T00:00:00Z",
              completed_at: "2026-01-01T00:01:00Z",
              records_collected: 0,
              error_message: "Selector missing",
            },
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText("Market Co")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getByText("Selector missing")).toBeInTheDocument();
  });
  it("renders an empty state", () => {
    render(
      <MemoryRouter>
        <CrawlJobTable competitors={competitors} jobs={[]} />
      </MemoryRouter>,
    );
    expect(screen.getByText("No crawl jobs have run yet.")).toBeInTheDocument();
  });
});
