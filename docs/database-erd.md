# Pricing Intelligence Platform — Database ERD

This diagram reflects the SQLAlchemy models in `backend/app/models` as of August 8, 2026.

Rendered reference files: [SVG](database-erd.svg) · [high-resolution PNG](database-erd.png) · [Graphviz source](database-erd.dot)

```mermaid
erDiagram
    USERS {
        UUID user_id PK
        varchar email UK
        varchar username UK
        varchar hashed_password
        varchar first_name "nullable"
        varchar last_name "nullable"
        user_roles role "admin, approver, editor, viewer"
        boolean is_active
        datetime last_login "nullable"
        datetime created_at
        datetime updated_at
    }

    CATEGORIES {
        UUID category_id PK
        varchar category_name UK
        varchar slug UK
        text description "nullable"
        UUID parent_id FK "nullable; self-reference"
    }

    PRICING_RULES {
        UUID rule_id PK
        varchar rule_name UK
        text rule_description
        rule_type_enum rule_type "COST_PLUS, COMPETITOR_BASED, INVENTORY_BASED, DEMAND_BASED"
        integer priority
        boolean is_active
        datetime created_at "nullable"
        datetime updated_at "nullable"
        UUID created_by FK "nullable"
        UUID updated_by FK "nullable"
    }

    PRODUCTS {
        UUID product_id PK
        varchar sku UK
        varchar product_name
        varchar slug
        text description "nullable"
        varchar brand "nullable"
        UUID category_id FK
        integer safety_stock
        text image_url "nullable"
        UUID rule_id FK
        decimal base_price
        decimal current_price
        decimal min_price "nullable"
        decimal max_price "nullable"
        decimal target_margin "nullable"
        boolean auto_pricing_enabled
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    INVENTORIES {
        UUID inventory_id PK
        UUID product_id FK
        varchar vendor
        integer lead_time
        decimal cost_per_unit
        integer on_hand_qty
        datetime updated_at
    }

    DEMAND_FORECASTS {
        UUID forecast_id PK
        UUID product_id FK
        datetime forecast_date
        integer predicted_demand
        varchar model_name "nullable"
        decimal confidence_score "nullable"
        datetime created_at
    }

    COMPETITORS {
        UUID competitor_id PK
        varchar competitor_name UK
        varchar website_url UK
        boolean is_active
        datetime created_at
    }

    COMPETITOR_PRODUCTS {
        UUID competitor_product_id PK
        UUID product_id FK
        UUID competitor_id FK
        varchar competitor_sku
        varchar competitor_product_name
        text competitor_product_url
        datetime created_at
    }

    COMPETITOR_PRICES {
        UUID price_id PK
        UUID competitor_product_id FK
        decimal competitor_price
        integer stock_qty
        boolean in_stock
        datetime crawl_timestamp
    }

    CRAWL_JOBS {
        UUID job_id PK
        UUID competitor_id FK
        varchar status
        datetime started_at
        datetime completed_at "nullable"
        integer records_collected
        text error_message "nullable"
    }

    PRICE_RECOMMENDATIONS {
        UUID recommendation_id PK
        UUID product_id FK
        UUID rule_id FK
        decimal current_price
        decimal recommended_price
        text recommendation_reason
        datetime generated_at
        varchar status "pending, approved, rejected, applied"
        UUID reviewed_by FK "nullable"
        datetime reviewed_at "nullable"
        text review_reason "nullable"
        UUID applied_by FK "nullable"
        datetime applied_at "nullable"
    }

    PRODUCT_PRICE_HISTORIES {
        UUID history_id PK
        UUID product_id FK
        decimal old_price
        decimal new_price
        text change_reason
        UUID recommendation_id FK "nullable"
        UUID changed_by FK "nullable"
        datetime changed_at
    }

    CATEGORIES o|--o{ CATEGORIES : "parent of"
    CATEGORIES ||--o{ PRODUCTS : classifies
    PRICING_RULES ||--o{ PRODUCTS : configures
    USERS o|--o{ PRICING_RULES : creates
    USERS o|--o{ PRICING_RULES : updates

    PRODUCTS ||--o{ INVENTORIES : stocks
    PRODUCTS ||--o{ DEMAND_FORECASTS : forecasts
    PRODUCTS ||--o{ COMPETITOR_PRODUCTS : maps
    COMPETITORS ||--o{ COMPETITOR_PRODUCTS : lists
    COMPETITOR_PRODUCTS ||--o{ COMPETITOR_PRICES : records
    COMPETITORS ||--o{ CRAWL_JOBS : crawled_by

    PRODUCTS ||--o{ PRICE_RECOMMENDATIONS : receives
    PRICING_RULES ||--o{ PRICE_RECOMMENDATIONS : generates
    USERS o|--o{ PRICE_RECOMMENDATIONS : reviews
    USERS o|--o{ PRICE_RECOMMENDATIONS : applies

    PRODUCTS ||--o{ PRODUCT_PRICE_HISTORIES : audits
    PRICE_RECOMMENDATIONS o|--o{ PRODUCT_PRICE_HISTORIES : produces
    USERS o|--o{ PRODUCT_PRICE_HISTORIES : changes
```

## Pricing workflow

```mermaid
flowchart LR
    P[Product] --> I[Inventory / unit cost]
    P --> D[Latest demand forecast]
    P --> CP[Competitor product mappings]
    CP --> CPrice[Latest competitor prices]
    P --> R[Assigned active pricing rule]

    I --> E[Deterministic rule evaluation]
    D --> E
    CPrice --> E
    R --> E
    P --> E

    E --> PR[Price recommendation: PENDING]
    PR -->|approve| A[APPROVED]
    PR -->|reject| X[REJECTED]
    A -->|atomic apply transaction| AP[APPLIED]
    AP --> PU[Update product.current_price]
    AP --> H[Insert immutable price history]
```

## Constraints and implementation notes

- `competitor_products` is unique on `(product_id, competitor_id)`.
- `demand_forecasts` is unique on `(product_id, forecast_date, model_name)`.
- Categories cannot reference themselves directly (`category_id <> parent_id`).
- Product price history has no update or delete API and serves as immutable audit data.
- The application creates one history row when applying a recommendation, but `recommendation_id` is not unique in the physical schema, so the database itself permits multiple history rows for one recommendation.
- Recommendation review/application and their associated user relationships are nullable because deleting a user uses `ON DELETE SET NULL`.
- The application treats inventory as one record per product, but the database currently lacks a unique constraint on `inventories.product_id`; therefore the physical ERD shows one-to-many.
- Mermaid repeats the user-to-rule and user-to-recommendation relationship because each table contains separate actor columns (`created_by`/`updated_by` and `reviewed_by`/`applied_by`).

## Legend

- `PK`: primary key
- `FK`: foreign key
- `UK`: unique key
- `||`: exactly one
- `o|`: zero or one
- `o{`: zero or many
