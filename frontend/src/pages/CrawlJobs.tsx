import { AlertTriangle, Bot, CheckCircle2, Clock3, LoaderCircle, Play, RefreshCw, Timer } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CrawlJobTable } from "../components/CrawlJobTable";
import { Card, PageState, SectionHeader, StatusBadge } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../lib/api";
import { dateTime } from "../lib/format";
import type { Competitor, CrawlJob, CrawlSchedule } from "../types";

export function CrawlJobs(){
  const [params] = useSearchParams(); const selected = params.get("competitor") || ""; const { user } = useAuth();
  const [submitting,setSubmitting]=useState(""); const [notice,setNotice]=useState(""); const [actionError,setActionError]=useState("");
  const initialJobs=useApi<CrawlJob[]>("/crawl-jobs?limit=1000"), competitors=useApi<Competitor[]>("/competitors?limit=1000"), schedule=useApi<CrawlSchedule>("/crawl-jobs/schedule/status");
  const active=initialJobs.data?.some(j=>j.status==="pending"||j.status==="running") ?? false;
  const polledJobs=useApi<CrawlJob[]>(active?"/crawl-jobs?limit=1000":null,active?3000:0); const jobs=polledJobs.data || initialJobs.data || [];
  const canTrigger=user?.role==="editor"||user?.role==="admin";
  const filtered=useMemo(()=>selected?jobs.filter(j=>j.competitor_id===selected):jobs,[jobs,selected]);
  async function trigger(competitorId:string){setSubmitting(competitorId);setNotice("");setActionError("");try{const job=await api.post<CrawlJob>(`/crawl-jobs/competitors/${competitorId}`);setNotice(`Crawl submitted. Job ${job.job_id.slice(0,8)} is ${job.status}.`);await initialJobs.refresh()}catch(e){setActionError(e instanceof Error?e.message:"Unable to submit crawl")}finally{setSubmitting("")}}
  if(initialJobs.loading||competitors.loading||schedule.loading)return <PageState loading/>;if(initialJobs.error||competitors.error||schedule.error)return <PageState error={initialJobs.error||competitors.error||schedule.error}/>;
  return <><div className="page-intro"><div><p className="eyebrow">Background collection</p><h2>Competitor crawl jobs</h2><p>Submit collection work and follow its progress without waiting.</p></div><button className="button secondary" onClick={()=>void initialJobs.refresh()}><RefreshCw/> Refresh</button></div>
    {notice&&<div className="form-success">{notice}</div>}{actionError&&<div className="form-error">{actionError}</div>}
    <div className="kpi-grid crawl-kpis"><Mini label="Pending" value={jobs.filter(j=>j.status==="pending").length} icon={<Clock3/>}/><Mini label="Running" value={jobs.filter(j=>j.status==="running").length} icon={<Bot/>}/><Mini label="Completed" value={jobs.filter(j=>j.status==="completed").length} icon={<CheckCircle2/>}/><Mini label="Failed" value={jobs.filter(j=>j.status==="failed").length} icon={<AlertTriangle/>}/></div>
    <div className="dashboard-grid"><Card><SectionHeader title="Automated scraping" subtitle="Read-only scheduler configuration"/><dl className="details"><div><dt>Status</dt><dd><StatusBadge status={schedule.data?.enabled?"Enabled":"Disabled"}/></dd></div><div><dt>Interval</dt><dd>{formatInterval(schedule.data?.interval_seconds)}</dd></div><div><dt>Most recent crawl</dt><dd>{dateTime(schedule.data?.last_crawl_at)}</dd></div><div><dt>Next scheduled crawl</dt><dd>{dateTime(schedule.data?.next_scheduled_crawl)}</dd></div></dl>{!schedule.data?.next_scheduled_crawl&&<p className="permission-note"><Timer/> The worker does not expose its next exact tick.</p>}</Card>
    <Card><SectionHeader title="Start a crawl" subtitle={canTrigger?"Work is submitted to a background worker.":"Editor or admin access is required."}/><div className="crawl-actions">{competitors.data?.filter(c=>c.is_active).map(c=><button key={c.competitor_id} className="button secondary" disabled={!canTrigger||!!submitting||jobs.some(j=>j.competitor_id===c.competitor_id&&(j.status==="pending"||j.status==="running"))} onClick={()=>void trigger(c.competitor_id)}>{submitting===c.competitor_id?<LoaderCircle className="spin"/>:<Play/>}{c.competitor_name}</button>)}</div></Card></div>
    <Card><SectionHeader title={selected?"Filtered crawl history":"Crawl job history"} subtitle={active?"Active jobs refresh every 3 seconds":"Recent competitor data collection runs"}/><CrawlJobTable jobs={filtered} competitors={competitors.data||[]}/></Card></>;
}
function Mini({label,value,icon}:{label:string;value:number;icon:React.ReactNode}){return <Card className="mini-kpi"><span>{icon}{label}</span><strong>{value}</strong></Card>}
function formatInterval(seconds?:number){if(!seconds)return "—";if(seconds%86400===0)return `Every ${seconds/86400} day${seconds===86400?"":"s"}`;if(seconds%3600===0)return `Every ${seconds/3600} hours`;return `Every ${seconds} seconds`}
