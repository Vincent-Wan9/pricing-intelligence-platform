import decimal
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.category import Category
from app.models.pricing_rule import PricingRule, RuleType
from app.models.product import Product


engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

session = Session()

print("Generating mock products...")

try:
    # add category 
    category = Category(
        category_id=uuid.uuid4(),
        category_name="Electronics",
        slug="electronics",
        description="Electronic devices and accessories",
    )

    session.add(category)
    session.commit()

    print("Category inserted!")

    # add pricing rule
    rule = PricingRule(
        rule_id=uuid.uuid4(),
        rule_name="Default Cost Plus Pricing",
        rule_description="Calculate price based on product cost plus target margin.",
        rule_type=RuleType.COST_PLUS,
        priority=1,
        is_active=True,
        created_by=None,
        updated_by=None,
    )

    session.add(rule)
    session.commit()

    print("Pricing rule inserted successfully!")

    # add product
    mock_products = [
        Product(
            product_id=uuid.uuid4(),
            sku="ELEC-SND-901",
            product_name="Noise Cancelling Wireless Headphones",
            slug="noise-cancelling-wireless-headphones",
            description="Premium over-ear headphones with active noise cancellation.",
            brand="AudioMax",

            category_id=category.category_id,
            rule_id=rule.rule_id,

            safety_stock=20,

            image_url="https://example.com/headphones.jpg",

            base_price=decimal.Decimal("129.99"),
            current_price=decimal.Decimal("129.99"),
            min_price=decimal.Decimal("89.99"),
            max_price=decimal.Decimal("149.99"),
            target_margin=decimal.Decimal("35.00"),

            auto_pricing_enabled=True,
            is_active=True,
        ),

        Product(
            product_id=uuid.uuid4(),
            sku="HOME-KTC-042",
            product_name="Stainless Steel Electric Kettle",
            slug="stainless-steel-electric-kettle",
            description="1.7L rapid-boil kettle with auto shut-off.",
            brand="KitchenPro",

            category_id=category.category_id,
            rule_id=rule.rule_id,

            safety_stock=15,

            image_url="https://example.com/kettle.jpg",

            base_price=decimal.Decimal("34.95"),
            current_price=decimal.Decimal("34.95"),
            min_price=decimal.Decimal("24.99"),
            max_price=decimal.Decimal("39.99"),
            target_margin=decimal.Decimal("30.00"),

            auto_pricing_enabled=False,
            is_active=True,
        ),
    ]

    session.add_all(mock_products)
    session.commit()

    print(f"Successfully inserted {len(mock_products)} products.")

    print("\nInserted Products:")
    for product in session.query(Product).all():
        print(
            f"{product.product_name} | "
            f"SKU={product.sku} | "
            f"Price=${product.current_price}"
        )

except Exception as e:
    session.rollback()
    print(f"Error while seeding: {e}")

finally:
    session.close()