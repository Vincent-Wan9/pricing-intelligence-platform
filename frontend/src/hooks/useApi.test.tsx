import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useApi } from "./useApi";

describe("useApi polling", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("polls active resources at the configured interval", async () => {
    // Arrange
    vi.useFakeTimers();

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
    const { result, unmount } = renderHook(() => useApi("/crawl-jobs", 20));

    // Wait for the initial API request
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(mockResponse);

    // Advance time to trigger polling
    await act(async () => {
      await vi.advanceTimersByTimeAsync(19);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });

    // Assert
    expect(fetchMock).toHaveBeenCalledTimes(2);

    // Cleanup
    unmount();
    await vi.advanceTimersByTimeAsync(40);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
