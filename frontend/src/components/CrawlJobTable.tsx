import { Link } from "react-router-dom";
import { Database } from "lucide-react";
import { PageState, StatusBadge } from "./ui";
import { dateTime } from "../lib/format";
import type { Competitor, CrawlJob } from "../types";

export function CrawlJobTable({ jobs, competitors, competitorId }: { jobs: CrawlJob[]; competitors: Competitor[]; competitorId?: string }) {
  const rows = jobs.filter(job => !competitorId || job.competitor_id === competitorId)
    .sort((a,b)=>(b.started_at || b.completed_at || "").localeCompare(a.started_at || a.completed_at || ""));
  if (!rows.length) return <PageState empty="No crawl jobs have run yet."/>;
  return <div className="table-wrap"><table><thead><tr><th>Competitor</th><th>Status</th><th>Started</th><th>Completed</th><th>Records</th><th>Result</th></tr></thead><tbody>{rows.map(job => <tr key={job.job_id}>
    <td><Link to={`/crawl-jobs?competitor=${job.competitor_id}`}><strong>{competitors.find(c=>c.competitor_id===job.competitor_id)?.competitor_name || "Unknown competitor"}</strong></Link></td>
    <td><StatusBadge status={job.status}/></td><td>{dateTime(job.started_at)}</td><td>{dateTime(job.completed_at)}</td>
    <td><span className="records"><Database/>{job.records_collected}</span></td>
    <td className={job.error_message ? "error-message" : ""}>{job.error_message || (job.status === "completed" ? "Completed successfully" : "—")}</td>
  </tr>)}</tbody></table></div>;
}
