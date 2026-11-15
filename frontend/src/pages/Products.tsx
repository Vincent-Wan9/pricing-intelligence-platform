import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { money } from "../lib/format";

import type { Inventory, PricingRule, Product } from "../types";

export function Products() {
  // Fetch data
  const products = useApi<Product[]>("/products?limit=1000");
  const inventory = useApi<Inventory[]>("/inventory?limit=1000");
  const rules = useApi<PricingRule[]>("/pricing-rules?limit=1000");

  // Filter state
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");

  // Filter products by search query and status
  const filtered = useMemo(
    () =>
      (products.data || []).filter((product) => {
        const matchesStatus =
          status === "all" || String(product.is_active) === status;

        const searchableText =
          `${product.product_name} ${product.sku} ${product.brand || ""}`.toLowerCase();

        const matchesSearch = searchableText.includes(search.toLowerCase());

        return matchesStatus && matchesSearch;
      }),
    [products.data, search, status],
  );

  // Loading state
  if (products.loading || inventory.loading || rules.loading) {
    return <PageState loading />;
  }

  // Error state
  const error = products.error || inventory.error || rules.error;

  if (error) {
    return (
      <PageState
        error={error}
        onRetry={() => {
          void products.refresh();
          void inventory.refresh();
          void rules.refresh();
        }}
      />
    );
  }

  return (
    <Card>
      {/* Section header */}
      <SectionHeader
        title="Product catalog"
        subtitle={`${filtered.length} of ${(products.data || []).length} products`}
      />

      {/* Search and filters */}
      <div className="toolbar">
        <label className="search">
          <Search />

          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, SKU, or brand…"
          />
        </label>

        <label className="select-wrap">
          <SlidersHorizontal />

          <select
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </label>
      </div>

      {/* Product table */}
      {!filtered.length ? (
        <PageState
          empty={
            products.data?.length
              ? "No products match these filters."
              : "No products have been added yet."
          }
        />
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Product</th>
                <th>SKU</th>
                <th>Current price</th>
                <th>Price range</th>
                <th>Inventory</th>
                <th>Pricing rule</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              {filtered.map((product) => {
                const stock = inventory.data?.find(
                  (item) => item.product_id === product.product_id,
                );

                const rule = rules.data?.find(
                  (item) => item.rule_id === product.rule_id,
                );

                return (
                  <tr key={product.product_id}>
                    {/* Product name and brand */}
                    <td>
                      <Link
                        className="product-cell"
                        to={`/products/${product.product_id}`}
                      >
                        <span className="product-thumb">
                          {product.product_name[0]}
                        </span>

                        <span>
                          <strong>{product.product_name}</strong>
                          <small>{product.brand || "Unbranded"}</small>
                        </span>
                      </Link>
                    </td>

                    {/* SKU */}
                    <td>
                      <code>{product.sku}</code>
                    </td>

                    {/* Current price */}
                    <td>
                      <strong>{money(product.current_price)}</strong>
                    </td>

                    {/* Price range */}
                    <td>
                      {money(product.min_price)} – {money(product.max_price)}
                    </td>

                    {/* Inventory */}
                    <td>
                      <span
                        className={
                          stock && stock.on_hand_qty <= product.safety_stock
                            ? "stock-low"
                            : ""
                        }
                      >
                        {stock ? `${stock.on_hand_qty} units` : "Not tracked"}
                      </span>
                    </td>

                    {/* Pricing rule */}
                    <td>{rule?.rule_name || "—"}</td>

                    {/* Product status */}
                    <td>
                      <StatusBadge status={product.is_active} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
