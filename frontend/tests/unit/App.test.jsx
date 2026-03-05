import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

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
});
