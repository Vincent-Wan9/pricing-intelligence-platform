from typing import Annotated
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.redis import RedisClient, redis_client
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.competitor_price_service import CompetitorPriceService
from app.services.competitor_product_service import CompetitorProductService
from app.services.competitor_service import CompetitorService
from app.services.crawl_job_service import CrawlJobService
from app.services.demand_forecast_service import DemandForecastService
from app.services.inventory_service import InventoryService
from app.services.price_recommendation_service import PriceRecommendationService
from app.services.pricing_rule_service import PricingRuleService
from app.services.product_cache_service import ProductCacheService
from app.services.product_price_service import ProductPriceService
from app.services.product_service import ProductService
from app.services.user_service import UserService
from app.exceptions import AuthenticationError, AuthorizationError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DatabaseSession = Annotated[Session, Depends(get_db)]
BearerToken = Annotated[str | None, Depends(oauth2_scheme)]


def get_redis_client() -> RedisClient:
    return redis_client


def get_auth_service(db: DatabaseSession) -> AuthService:
    return AuthService(db)


def get_user_service(db: DatabaseSession) -> UserService:
    return UserService(db)


def get_category_service(db: DatabaseSession) -> CategoryService:
    return CategoryService(db)


def get_competitor_service(db: DatabaseSession) -> CompetitorService:
    return CompetitorService(db)


def get_competitor_product_service(db: DatabaseSession) -> CompetitorProductService:
    return CompetitorProductService(db)


def get_competitor_price_service(db: DatabaseSession) -> CompetitorPriceService:
    return CompetitorPriceService(db)


def get_inventory_service(db: DatabaseSession) -> InventoryService:
    return InventoryService(db)


def get_pricing_rule_service(db: DatabaseSession) -> PricingRuleService:
    return PricingRuleService(db)


def get_price_recommendation_service(db: DatabaseSession) -> PriceRecommendationService:
    return PriceRecommendationService(db)


def get_crawl_job_service(db: DatabaseSession) -> CrawlJobService:
    return CrawlJobService(db)


def get_demand_forecast_service(db: DatabaseSession) -> DemandForecastService:
    return DemandForecastService(db)


def get_product_cache_service(client: Annotated[RedisClient, Depends(get_redis_client)]) -> ProductCacheService:
    return ProductCacheService(client)


def get_product_service(
    db: DatabaseSession,
    cache: Annotated[ProductCacheService, Depends(get_product_cache_service)],
) -> ProductService:
    return ProductService(db, cache)


def get_product_price_service(
    db: DatabaseSession,
    cache: Annotated[ProductCacheService, Depends(get_product_cache_service)],
) -> ProductPriceService:
    return ProductPriceService(db, cache)


def _token_value(token: str | HTTPAuthorizationCredentials | None) -> str | None:
    return token.credentials if isinstance(token, HTTPAuthorizationCredentials) else token


def _auth_service(value: AuthService | Session) -> AuthService:
    return value if isinstance(value, AuthService) else AuthService(value)


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(service: Annotated[AuthService, Depends(get_auth_service)], token: BearerToken) -> User:
    """Resolve the active user represented by a required JWT access token."""
    raw_token = _token_value(token)
    if not raw_token:
        raise _unauthorized()
    try:
        return _auth_service(service).resolve_token(raw_token)
    except AuthenticationError as exc:
        raise _unauthorized() from exc


def get_optional_user(service: Annotated[AuthService, Depends(get_auth_service)], token: BearerToken) -> User | None:
    """Resolve a user when a valid token is supplied, otherwise return ``None``."""
    raw_token = _token_value(token)
    if not raw_token:
        return None
    try:
        return _auth_service(service).resolve_token(raw_token)
    except AuthenticationError:
        return None


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    try:
        return require_roles("admin")(current_user)
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail="Administrator access is required") from exc


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    allowed = frozenset(allowed_roles)

    def role_dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        role = getattr(current_user.role, "value", current_user.role)
        if role not in allowed:
            raise AuthorizationError("Insufficient permissions")
        return current_user

    return role_dependency


# Convenient route-parameter aliases, e.g. ``service: ProductServiceDep``.
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
DemandForecastServiceDep = Annotated[DemandForecastService, Depends(get_demand_forecast_service)]
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
CompetitorServiceDep = Annotated[CompetitorService, Depends(get_competitor_service)]
CompetitorProductServiceDep = Annotated[CompetitorProductService, Depends(get_competitor_product_service)]
CompetitorPriceServiceDep = Annotated[CompetitorPriceService, Depends(get_competitor_price_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
PricingRuleServiceDep = Annotated[PricingRuleService, Depends(get_pricing_rule_service)]
PriceRecommendationServiceDep = Annotated[PriceRecommendationService, Depends(get_price_recommendation_service)]
CrawlJobServiceDep = Annotated[CrawlJobService, Depends(get_crawl_job_service)]
ProductPriceServiceDep = Annotated[ProductPriceService, Depends(get_product_price_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]
AdminUser = Annotated[User, Depends(require_admin)]
