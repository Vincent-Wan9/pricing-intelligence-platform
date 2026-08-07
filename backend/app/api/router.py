from fastapi import APIRouter
from app.api.routers import auth,categories,competitor_prices,competitor_products,competitors,crawl_jobs,demand_forecasts,inventory,price_recommendations,pricing_rules,product_price_history,products,users

api_router=APIRouter()
for router in (auth.router,users.router,categories.router,products.router,inventory.router,competitors.router,competitor_products.router,competitor_prices.router,crawl_jobs.router,pricing_rules.router,price_recommendations.router,demand_forecasts.router,product_price_history.router):
    api_router.include_router(router)
