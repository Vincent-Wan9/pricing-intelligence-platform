export type ID = string;
export interface User { user_id: ID; email: string; username: string; first_name?: string; last_name?: string; role: "admin" | "approver" | "editor" | "viewer"; is_active: boolean }
export interface Product { product_id: ID; sku: string; product_name: string; description?: string; brand?: string; category_id: ID; rule_id: ID; safety_stock: number; image_url?: string; base_price: string; current_price: string; min_price?: string; max_price?: string; target_margin?: string; auto_pricing_enabled: boolean; is_active: boolean; created_at: string; updated_at: string }
export interface Inventory { inventory_id: ID; product_id: ID; vendor: string; lead_time: number; cost_per_unit: string; on_hand_qty: number; updated_at: string }
export interface PricingRule { rule_id: ID; rule_name: string; rule_description: string; rule_type: string; priority: number; is_active: boolean }
export interface Competitor { competitor_id: ID; competitor_name: string; website_url: string; is_active: boolean; created_at: string }
export interface CompetitorMapping { competitor_product_id: ID; product_id: ID; competitor_id: ID; competitor_sku: string; competitor_product_name: string; competitor_product_url: string; price_selector?: string; is_active: boolean; created_at: string; last_crawled_at?: string; last_crawl_error?: string }
export interface CompetitorPrice { price_id: ID; competitor_product_id: ID; competitor_price: string; stock_qty?: number; in_stock?: boolean; crawl_timestamp: string; crawl_job_id?: ID }
export interface Recommendation { recommendation_id: ID; product_id: ID; rule_id: ID; current_price?: string; recommended_price: string; recommendation_reason: string; generated_at: string; status: "pending" | "approved" | "rejected" | "applied"; review_reason?: string }
export interface PriceHistory { history_id: ID; product_id: ID; old_price: string; new_price: string; change_reason: string; changed_at: string }
export interface CrawlJob { job_id: ID; competitor_id: ID; status: "pending" | "running" | "completed" | "failed"; started_at?: string; completed_at?: string; records_collected: number; error_message?: string }
export interface CrawlSchedule { enabled: boolean; interval_seconds: number; last_crawl_at?: string; next_scheduled_crawl?: string }
export interface DemandHistory { demand_history_id: ID; product_id: ID; demand_date: string; quantity: number; created_at: string }
export interface DemandForecast { forecast_id: ID; product_id: ID; forecast_date: string; predicted_demand: number; model_name?: string; confidence_score?: string; created_at: string }
export interface ForecastGenerationResult { product_id: ID; horizon_days: number; model_name: string; baseline_mae: number; ml_mae: number; forecasts: DemandForecast[] }
