import { Search, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { money } from "../lib/format";
import type { Inventory, PricingRule, Product } from "../types";

export function Products() {
  const products = useApi<Product[]>("/products?limit=1000"), inventory = useApi<Inventory[]>("/inventory?limit=1000"), rules = useApi<PricingRule[]>("/pricing-rules?limit=1000");
  const [search, setSearch] = useState(""); const [status, setStatus] = useState("all");
  const filtered = useMemo(() => (products.data || []).filter(p => (status === "all" || String(p.is_active) === status) && `${p.product_name} ${p.sku} ${p.brand || ""}`.toLowerCase().includes(search.toLowerCase())), [products.data, search, status]);
  if (products.loading || inventory.loading || rules.loading) return <PageState loading/>; const error=products.error||inventory.error||rules.error; if(error)return <PageState error={error} onRetry={()=>{void products.refresh();void inventory.refresh();void rules.refresh()}}/>;
  return <Card><SectionHeader title="Product catalog" subtitle={`${filtered.length} of ${(products.data || []).length} products`} /><div className="toolbar"><label className="search"><Search/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search name, SKU, or brand…"/></label><label className="select-wrap"><SlidersHorizontal/><select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">All statuses</option><option value="true">Active</option><option value="false">Inactive</option></select></label></div>{!filtered.length ? <PageState empty={products.data?.length ? "No products match these filters." : "No products have been added yet."}/> : <div className="table-wrap"><table><thead><tr><th>Product</th><th>SKU</th><th>Current price</th><th>Price range</th><th>Inventory</th><th>Pricing rule</th><th>Status</th></tr></thead><tbody>{filtered.map(p=>{const stock=inventory.data?.find(i=>i.product_id===p.product_id);const rule=rules.data?.find(r=>r.rule_id===p.rule_id);return <tr key={p.product_id}><td><Link className="product-cell" to={`/products/${p.product_id}`}><span className="product-thumb">{p.product_name[0]}</span><span><strong>{p.product_name}</strong><small>{p.brand || "Unbranded"}</small></span></Link></td><td><code>{p.sku}</code></td><td><strong>{money(p.current_price)}</strong></td><td>{money(p.min_price)} – {money(p.max_price)}</td><td><span className={stock && stock.on_hand_qty <= p.safety_stock ? "stock-low":""}>{stock ? `${stock.on_hand_qty} units` : "Not tracked"}</span></td><td>{rule?.rule_name || "—"}</td><td><StatusBadge status={p.is_active}/></td></tr>})}</tbody></table></div>}</Card>;
}
