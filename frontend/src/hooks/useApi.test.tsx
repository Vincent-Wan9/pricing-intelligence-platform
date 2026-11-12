import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useApi } from "./useApi";

describe("useApi polling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("polls active resources at the configured interval", async () => {
    // Arrange
    vi.useFakeTimers({ shouldAdvanceTime: true });

    const mockResponse = [
      { status: "running" },
    ];

    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(mockResponse), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
        },
      })
    );

    // Act
    const { unmount } = renderHook(() => useApi("/crawl-jobs", 20));

    // Wait for the initial API request
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    // Advance time to trigger polling
    await vi.advanceTimersByTimeAsync(25);

    // Assert
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // Cleanup
    unmount();
  });
});