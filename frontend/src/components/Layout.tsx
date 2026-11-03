import {
  BarChart3,
  Bot,
  Boxes,
  Lightbulb,
  LogOut,
  Menu,
  Scale,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const links = [
  ["/", "Dashboard", BarChart3],
  ["/products", "Products", Boxes],
  ["/competitors", "Competitors", Scale],
  ["/recommendations", "Recommendations", Lightbulb],
  ["/crawl-jobs", "Crawl Jobs", Bot],
] as const;
const titles: Record<string, string> = {
  "/": "Dashboard",
  "/products": "Products",
  "/competitors": "Competitors",
  "/recommendations": "Recommendations",
  "/crawl-jobs": "Crawl Jobs",
};
export function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const title = location.pathname.startsWith("/products/")
    ? "Product Detail"
    : titles[location.pathname] || "PricePilot";
  return (
    <div className="app-shell">
      {open && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">P</span>
          <span>PricePilot</span>
          <button
            className="icon-button mobile-only"
            onClick={() => setOpen(false)}
          >
            <X />
          </button>
        </div>
        <p className="nav-label">Workspace</p>
        <nav>
          {links.map(([to, label, Icon]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setOpen(false)}
            >
              <Icon />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="live-dot" /> API connected
        </div>
      </aside>
      <main>
        <header className="topbar">
          <div>
            <button
              className="icon-button menu-button"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <h1>{title}</h1>
          </div>
          <div className="user-menu">
            <div className="avatar">
              {(user?.first_name || user?.username || "U")[0].toUpperCase()}
            </div>
            <div>
              <strong>
                {user?.first_name
                  ? `${user.first_name} ${user.last_name || ""}`
                  : user?.username}
              </strong>
              <span>{user?.role}</span>
            </div>
            <button className="icon-button" title="Log out" onClick={logout}>
              <LogOut />
            </button>
          </div>
        </header>
        <div className="page">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
