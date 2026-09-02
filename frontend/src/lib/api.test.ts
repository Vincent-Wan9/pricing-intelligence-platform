import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

afterEach(()=>vi.restoreAllMocks());
describe("crawl submission",()=>{it("submits a crawl without waiting for completion",async()=>{const response={job_id:"j1",competitor_id:"c1",status:"pending",records_collected:0};const fetchMock=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify(response),{status:202,headers:{"Content-Type":"application/json"}}));await expect(api.post("/crawl-jobs/competitors/c1")).resolves.toEqual(response);expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/crawl-jobs/competitors/c1"),expect.objectContaining({method:"POST"}));});});
