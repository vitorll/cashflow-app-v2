import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "../../src/App";

describe("App", () => {
  it("renders without crashing", () => {
    // A smoke test — if the component throws during render, this fails.
    expect(() => render(<App />)).not.toThrow();
  });

  it("renders a top-level heading or identifiable element", () => {
    render(<App />);
    // The App must render at least one heading element.
    // Acceptable: h1, h2, or an element with role="heading".
    const headings = screen.getAllByRole("heading");
    expect(headings.length).toBeGreaterThan(0);
  });

  it("shows the Dashboard tab content by default", () => {
    render(<App />);
    expect(screen.getByText("No data loaded yet.")).toBeInTheDocument();
  });

  it("switches to the Forecast tab when clicked", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Forecast" }));
    expect(screen.getByText("No forecast data available.")).toBeInTheDocument();
  });

  it("switches to the Phase Comparison tab when clicked", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Phase Comparison" }));
    expect(screen.getByText("No phase data available.")).toBeInTheDocument();
  });

  it("switches to the P&L tab when clicked", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "P&L" }));
    expect(screen.getByText("No P&L data available.")).toBeInTheDocument();
  });

  it("switches to the Data Entry tab when clicked", async () => {
    render(<App />);
    await userEvent.click(screen.getByRole("button", { name: "Data Entry" }));
    expect(screen.getByText("No entries yet.")).toBeInTheDocument();
  });

  it("marks the active tab with aria-current=page", async () => {
    render(<App />);
    const forecastBtn = screen.getByRole("button", { name: "Forecast" });
    await userEvent.click(forecastBtn);
    expect(forecastBtn).toHaveAttribute("aria-current", "page");
  });
});
