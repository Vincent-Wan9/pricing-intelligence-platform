import logging
import re

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    DomainError,
    ResourceNotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _code_from_exception(exc: Exception) -> str:
    if isinstance(exc, DomainError):
        return exc.code
    name = exc.__class__.__name__
    for suffix in ("NotFoundError", "ConflictError", "ValidationError", "AuthorizationError", "ServiceError", "Error"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    resource = re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper() or "RESOURCE"
    if exc.__class__.__name__.endswith("NotFoundError"):
        return f"{resource}_NOT_FOUND"
    if exc.__class__.__name__.endswith("ConflictError"):
        return f"{resource}_CONFLICT"
    if exc.__class__.__name__.endswith("AuthorizationError"):
        return "INSUFFICIENT_PERMISSIONS"
    return f"{resource}_INVALID"


def _response(exc: Exception, status_code: int) -> JSONResponse:
    message = "Could not validate credentials" if isinstance(exc, AuthenticationError) else str(exc)
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": _code_from_exception(exc), "message": message}},
        headers={"WWW-Authenticate": "Bearer"} if status_code == 401 else None,
    )


def register_exception_handlers(app: FastAPI) -> None:
    from app.services import ProductAuthorizationError, ProductConflictError, ProductNotFoundError, ProductValidationError
    from app.services.category_service import CategoryConflictError, CategoryNotFoundError, CategoryValidationError
    from app.services.competitor_price_service import CompetitorPriceConflictError, CompetitorPriceNotFoundError, CompetitorPriceValidationError
    from app.services.competitor_product_service import CompetitorProductConflictError, CompetitorProductNotFoundError, CompetitorProductValidationError
    from app.services.competitor_service import CompetitorConflictError, CompetitorNotFoundError, CompetitorValidationError
    from app.services.crawl_job_service import CrawlJobConflictError, CrawlJobEnqueueError, CrawlJobNotFoundError, CrawlJobValidationError
    from app.services.demand_forecast_service import DemandForecastConflictError, DemandForecastNotFoundError, DemandForecastValidationError
    from app.services.inventory_service import InventoryConflictError, InventoryNotFoundError, InventoryValidationError
    from app.services.price_recommendation_service import PriceRecommendationConflictError, PriceRecommendationNotFoundError, PriceRecommendationValidationError
    from app.services.pricing_rule_service import PricingRuleConflictError, PricingRuleNotFoundError, PricingRuleValidationError
    from app.services.user_service import UserAuthorizationError, UserConflictError, UserNotFoundError, UserValidationError

    mappings = {
        status.HTTP_400_BAD_REQUEST: (ValidationError, ProductValidationError, CategoryValidationError, CompetitorValidationError, CompetitorProductValidationError, CompetitorPriceValidationError, CrawlJobValidationError, DemandForecastValidationError, InventoryValidationError, PriceRecommendationValidationError, PricingRuleValidationError, UserValidationError),
        status.HTTP_401_UNAUTHORIZED: (AuthenticationError,),
        status.HTTP_403_FORBIDDEN: (AuthorizationError, ProductAuthorizationError, UserAuthorizationError),
        status.HTTP_404_NOT_FOUND: (ResourceNotFoundError, ProductNotFoundError, CategoryNotFoundError, CompetitorNotFoundError, CompetitorProductNotFoundError, CompetitorPriceNotFoundError, CrawlJobNotFoundError, DemandForecastNotFoundError, InventoryNotFoundError, PriceRecommendationNotFoundError, PricingRuleNotFoundError, UserNotFoundError),
        status.HTTP_409_CONFLICT: (ConflictError, ProductConflictError, CategoryConflictError, CompetitorConflictError, CompetitorProductConflictError, CompetitorPriceConflictError, CrawlJobConflictError, DemandForecastConflictError, InventoryConflictError, PriceRecommendationConflictError, PricingRuleConflictError, UserConflictError),
        status.HTTP_503_SERVICE_UNAVAILABLE: (CrawlJobEnqueueError,),
    }
    for status_code, exception_types in mappings.items():
        async def handler(request: Request, exc: Exception, code: int = status_code) -> JSONResponse:
            return _response(exc, code)
        for exception_type in exception_types:
            app.add_exception_handler(exception_type, handler)

    async def http_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = "INVALID_REQUEST"
        if exc.status_code == 401:
            code = "INVALID_CREDENTIALS"
        elif exc.status_code == 403:
            code = "INSUFFICIENT_PERMISSIONS"
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": str(exc.detail)}},
            headers=exc.headers,
        )

    app.add_exception_handler(HTTPException, http_handler)

    async def unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled API error", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"}})

    app.add_exception_handler(Exception, unexpected_handler)
