import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

describe("crawl submission", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("submits a crawl without waiting for completion", async () => {
    // Arrange
    const mockResponse = {
      job_id: "j1",
      competitor_id: "c1",
      status: "pending",
      records_collected: 0,
    };

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), {
        status: 202,
        headers: {
          "Content-Type": "application/json",
        },
      }),
    );

    // Act
    const result = await api.post("/crawl-jobs/competitors/c1");

    // Assert
    expect(result).toEqual(mockResponse);

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/crawl-jobs/competitors/c1"),
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});
