import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { Products } from "./Products";

vi.mock("../hooks/useApi", () => ({
  useApi: (path: string) => ({
    data: path.startsWith("/products")
      ? [
          {
            product_id: "p1",
            product_name: "Travel Mug",
            sku: "MUG-001",
            brand: "Acme",
            current_price: "20.00",
            is_active: true,
          },
        ]
      : [],
    loading: false,
    error: "",
    refresh: vi.fn(),
  }),
}));

describe("Products", () => {
  it("matches searches across name, SKU, and brand while respecting status", () => {
    render(
      <MemoryRouter>
        <Products />
      </MemoryRouter>,
    );

    const search = screen.getByPlaceholderText("Search name, SKU, or brand…");
    for (const query of ["travel mug MUG-001", "mug-001 acme", "ACME"]) {
      fireEvent.change(search, { target: { value: query } });
      expect(screen.getByRole("link", { name: /Travel Mug/ })).toBeInTheDocument();
    }

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "false" },
    });
    expect(screen.getByText("No products match these filters.")).toBeInTheDocument();

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "true" },
    });
    expect(screen.getByRole("link", { name: /Travel Mug/ })).toBeInTheDocument();
  });
});
