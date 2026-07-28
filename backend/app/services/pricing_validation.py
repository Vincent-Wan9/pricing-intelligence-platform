from decimal import Decimal

from app.services import ProductValidationError


def validate_prices(
 *, 
 base_price: Decimal, 
 current_price: Decimal, 
 min_price: Decimal | None,
 max_price: Decimal | None,
) -> None:

    required_prices = {"base_price": base_price, "current_price": current_price}
    optional_prices = {"min_price": min_price, "max_price": max_price}

    for field_name, value in required_prices.items():
        if value <= Decimal("0"):
            raise ProductValidationError(
                f"{field_name} must be greater than zero"
            )

    for field_name, value in optional_prices.items():
        if value is not None and value <= Decimal("0"):
            raise ProductValidationError(
                f"{field_name} must be greater than zero"
            )

    if min_price is not None and max_price is not None and min_price > max_price:
        raise ProductValidationError(
            "min_price cannot be greater than max_price"
        )
    if min_price is not None and current_price < min_price:
        raise ProductValidationError(
            "current_price cannot be lower than min_price"
        )
    if max_price is not None and current_price > max_price:
        raise ProductValidationError(
            "current_price cannot be greater than max_price"
        )
