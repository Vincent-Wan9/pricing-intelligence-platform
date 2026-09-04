import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DemandForecastChart, ForecastSummary } from "./DemandForecast";

const forecasts=[{forecast_id:"f1",product_id:"p1",forecast_date:"2026-09-01T00:00:00Z",predicted_demand:42,model_name:"ridge-lag-v1",confidence_score:"91.2",created_at:"2026-08-29T00:00:00Z"}];
describe("demand forecast components",()=>{
  it("distinguishes historical and forecasted demand",()=>{render(<DemandForecastChart history={[{demand_history_id:"h1",product_id:"p1",demand_date:"2026-08-28",quantity:35,created_at:"2026-08-28"}]} forecasts={forecasts}/>);expect(screen.getByText("Historical Demand")).toBeInTheDocument();expect(screen.getByText("Forecasted Demand")).toBeInTheDocument();expect(screen.getByRole("img",{name:/historical and forecasted/i})).toBeInTheDocument();});
  it("renders forecast metadata",()=>{render(<ForecastSummary forecasts={forecasts}/>);expect(screen.getByText("42 units")).toBeInTheDocument();expect(screen.getByText("ridge-lag-v1")).toBeInTheDocument();expect(screen.getByText("91.2%")).toBeInTheDocument();});
});
