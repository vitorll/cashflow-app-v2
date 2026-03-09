import { describe, it, expect } from "vitest";
import client from "../../src/api/client";

describe("api/client", () => {
  it("exports an axios instance with the default baseURL", () => {
    // When VITE_API_URL is not set, the fallback should be used.
    expect(client.defaults.baseURL).toBe("http://localhost:8000");
  });

  it("sets Content-Type to application/json", () => {
    expect(client.defaults.headers["Content-Type"]).toBe("application/json");
  });
});
