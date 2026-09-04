import { LineChart } from "./LineChart";
import { Badge, Card, PageState, SectionHeader } from "./ui";
import { dateTime } from "../lib/format";
import type { DemandForecast, DemandHistory } from "../types";

export function DemandForecastChart({ history, forecasts }: { history: DemandHistory[]; forecasts: DemandForecast[] }) {
  return <LineChart valueLabel="units" ariaLabel="Historical and forecasted demand line chart" series={[
    { name: "Historical Demand", color: "#2563eb", points: history.map(x=>({date:x.demand_date,value:x.quantity})) },
    { name: "Forecasted Demand", color: "#d97706", points: forecasts.slice().sort((a,b)=>a.forecast_date.localeCompare(b.forecast_date)).map(x=>({date:x.forecast_date,value:x.predicted_demand})) },
  ]}/>;
}

export function ForecastSummary({ forecasts }: { forecasts: DemandForecast[] }) {
  if (!forecasts.length) return <PageState empty="No demand forecast has been generated yet."/>;
  const ordered = forecasts.slice().sort((a,b)=>a.forecast_date.localeCompare(b.forecast_date));
  const latest = ordered[0]; const total = ordered.reduce((sum,x)=>sum+x.predicted_demand,0);
  return <Card className="forecast-summary"><SectionHeader title="Forecast summary"/><dl className="details">
    <div><dt>Forecast horizon</dt><dd>{ordered.length} days</dd></div><div><dt>Predicted demand</dt><dd>{total.toLocaleString()} units</dd></div>
    <div><dt>Generated</dt><dd>{dateTime(latest.created_at)}</dd></div><div><dt>Model</dt><dd><Badge tone="info">{latest.model_name || "Not provided"}</Badge></dd></div>
    <div><dt>Confidence</dt><dd>{latest.confidence_score ? `${latest.confidence_score}%` : "—"}</dd></div>
  </dl></Card>;
}
