-- ==========================
-- table users --
-- what: Stores user accounts for authentication and authorization.
-- ==========================
CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role ENUM('viewer', 'admin',  'approver', 'editor') NOT NULL  DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table categories --
-- what: Organizes products into logical groups.
-- ==========================
CREATE TABLE categories (
    category_id UUID PRIMARY KEY,
    category_name VARCHAR(20) UNIQUE NOT NULL,
    slug VARCHAR(20) UNIQUE NOT NULL, 
    description TEXT,
    parent_id UUID REFERENCES categories(category_id) ON DELETE SET NULL,
    CONSTRAINT chk_no_self_reference CHECK (category_id <> parent_id)
);
-- ==========================
-- table products --
-- what: Master catalog of products managed by the pricing platform.
-- ==========================
CREATE TABLE products (
    product_id UUID PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    brand VARCHAR(100),
    category_id UUID REFERENCES categories(category_id),
    safety_stock INTEGER DEFAULT 0,
    image_url TEXT,
    rule_id UUID REFERENCES pricing_rules(rule_id),
    base_price DECIMAL(10,2) NOT NULL,
    current_price DECIMAL(10,2) NOT NULL,
    min_price DECIMAL(10,2),
    max_price DECIMAL(10,2),
    target_margin DECIMAL(5,2),
    auto_pricing_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table inventory --
-- what: Tracks current inventory levels for each combination of product and vendor.
-- ==========================
CREATE TABLE inventories (
    inventory_id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id) ON DELETE CASCADE,
    vendor VARCHAR(255) NOT NULL,
    lead_time INTEGER NOT NULL,
    cost_per_unit DECIMAL(10,2) NOT NULL,
    on_hand_qty INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table competitors --
-- what: Stores competitor retailers monitored by the platform.
-- ==========================
CREATE TABLE competitors (
    competitor_id UUID PRIMARY KEY,
    competitor_name VARCHAR(255) UNIQUE NOT NULL,
    website_url TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table competitor_products --
-- what: Maps internal products to equivalent competitor listings.
-- ==========================
CREATE TABLE competitor_products (
    competitor_product_id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id),
    competitor_id UUID NOT NULL REFERENCES competitors(competitor_id),
    competitor_sku VARCHAR(100) NOT NULL,
    competitor_product_name VARCHAR(255) NOT NULL,
    competitor_product_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, competitor_id)
);
-- ==========================
-- table competitor_prices --
-- what: Stores historical pricing collected from competitor websites.
-- ==========================
CREATE TABLE competitor_prices (
    price_id UUID PRIMARY KEY,
    competitor_product_id UUID NOT NULL REFERENCES competitor_products(competitor_product_id),
    competitor_price DECIMAL(10,2) NOT NULL,
    stock_qty INTEGER,
    in_stock BOOLEAN,
    crawl_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_competitor_prices ON competitor_prices (competitor_product_id, crawl_timestamp DESC);
-- ==========================
-- table product_price_history --
-- what: Maintains historical pricing for internal products.
-- ==========================
CREATE TABLE product_price_histories (
    history_id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id),
    old_price DECIMAL(10,2) NOT NULL,
    new_price DECIMAL(10,2) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table pricing_rules --
-- what: Defines configurable pricing strategies.
-- ==========================
CREATE TABLE pricing_rules (
    rule_id UUID PRIMARY KEY,
    rule_name VARCHAR(255) UNIQUE NOT NULL,
    rule_description TEXT,
    rule_type ENUM('cost_plus', 'competitor_based',  'inventory_based', 'demand_based') DEFAULT 'cost_plus',
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
    updated_by UUID REFERENCES users(user_id) ON DELETE SET NULL,
);
-- ==========================
-- table demand_forecasts --
-- what: Stores demand forecasting results generated by machine learning models.
-- ==========================
CREATE TABLE demand_forecasts (
    forecast_id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id),
    forecast_date DATE NOT NULL,
    predicted_demand INTEGER NOT NULL,
    model_name VARCHAR(100),
    confidence_score DECIMAL(5,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_product_date_model UNIQUE (product_id, forecast_date, model_name)
);
-- ==========================
-- table price_recommendations --
-- what: Stores pricing recommendations generated by the pricing engine.
-- ==========================
CREATE TABLE price_recommendations (
    recommendation_id UUID PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(product_id),
    rule_id UUID NOT NULL REFERENCES pricing_rules(rule_id),
    recommended_price DECIMAL(10,2) NOT NULL,
    recommendation_reason TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- ==========================
-- table crawl_jobs --
-- what: Tracks execution of competitor price crawling jobs.
-- ==========================
CREATE TABLE crawl_jobs (
    job_id UUID PRIMARY KEY,
    competitor_id UUID NOT NULL REFERENCES competitors(competitor_id),
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    records_collected INTEGER DEFAULT 0,
    error_message TEXT
);