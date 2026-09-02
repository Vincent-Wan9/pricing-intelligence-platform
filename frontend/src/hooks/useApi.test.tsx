import { renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useApi } from "./useApi";

afterEach(()=>vi.restoreAllMocks());
describe("useApi polling",()=>{it("polls active resources at the configured interval",async()=>{vi.useFakeTimers({shouldAdvanceTime:true});const fetchMock=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify([{status:"running"}]),{status:200,headers:{"Content-Type":"application/json"}}));const {unmount}=renderHook(()=>useApi("/crawl-jobs",20));await waitFor(()=>expect(fetchMock).toHaveBeenCalled());await vi.advanceTimersByTimeAsync(25);expect(fetchMock.mock.calls.length).toBeGreaterThanOrEqual(2);unmount();vi.useRealTimers();});});
