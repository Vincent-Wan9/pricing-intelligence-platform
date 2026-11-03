import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecommendationDetails } from "./RecommendationDetails";

describe("RecommendationDetails", () => {
  it("shows backend-supported pricing factors without inventing missing values", () => {
    render(
      <RecommendationDetails
        recommendation={{
          recommendation_id: "r1",
          product_id: "p1",
          rule_id: "rule1",
          current_price: "10",
          recommended_price: "12",
          recommendation_reason: "Demand increased",
          generated_at: "2026-01-01",
          status: "pending",
        }}
        forecast={{
          forecast_id: "f1",
          product_id: "p1",
          forecast_date: "2026-01-02",
          predicted_demand: 21,
          created_at: "2026-01-01",
        }}
      />,
    );
    expect(screen.getByText("21 units")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByText("$12.00")).toBeInTheDocument();
  });
});
