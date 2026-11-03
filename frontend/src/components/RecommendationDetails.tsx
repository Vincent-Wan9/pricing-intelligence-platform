import { money } from "../lib/format";
import type {
  CompetitorPrice,
  DemandForecast,
  Inventory,
  PricingRule,
  Product,
  Recommendation,
} from "../types";

export function RecommendationDetails({
  recommendation,
  product,
  forecast,
  competitorPrice,
  inventory,
  rule,
}: {
  recommendation: Recommendation;
  product?: Product;
  forecast?: DemandForecast;
  competitorPrice?: CompetitorPrice;
  inventory?: Inventory;
  rule?: PricingRule;
}) {
  return (
    <dl className="recommendation-details">
      <div>
        <dt>Current price</dt>
        <dd>{money(recommendation.current_price)}</dd>
      </div>
      <div>
        <dt>Recommended</dt>
        <dd>{money(recommendation.recommended_price)}</dd>
      </div>
      <div>
        <dt>Predicted demand</dt>
        <dd>{forecast ? `${forecast.predicted_demand} units` : "—"}</dd>
      </div>
      <div>
        <dt>Competitor price</dt>
        <dd>{money(competitorPrice?.competitor_price)}</dd>
      </div>
      <div>
        <dt>Inventory</dt>
        <dd>{inventory ? `${inventory.on_hand_qty} units` : "—"}</dd>
      </div>
      <div>
        <dt>Pricing rule</dt>
        <dd>{rule?.rule_name || (product ? "Rule unavailable" : "—")}</dd>
      </div>
    </dl>
  );
}
