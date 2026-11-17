import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Sample = { sampled_at: string; connected: string | null; download_bps: number | null; upload_bps: number | null };
type History = { samples: Sample[]; count: number };
type Status = { router_collection: string };
type ServerHealth = { uptime_seconds: number; memory: { total_bytes: number; used_bytes: number }; disk: { total_bytes: number; available_bytes: number }; cpu: { total_ticks: number; idle_ticks: number } };
const pages = ["Overview", "WAN Traffic", "Devices", "Server Health", "Services & Apps", "Environment Report", "Alerts", "Topology", "Settings"] as const;
type Page = typeof pages[number];
const api = (path: string) => new URL("api/" + path, document.baseURI).toString();
const speed = (bps: number | null | undefined) => bps == null ? "—" : (bps / 1_000_000).toFixed(2) + " Mbps";

function Trend({ samples }: { samples: Sample[] }) {
  const valid = samples.filter(s => s.download_bps != null && s.upload_bps != null);
  if (valid.length < 2) return <div className="empty">Waiting for at least two valid traffic measurements.</div>;
  const max = Math.max(1, ...valid.flatMap(s => [s.download_bps ?? 0, s.upload_bps ?? 0]));
  const points = (field: "download_bps" | "upload_bps") => valid.map((s, i) =>
    `${(i / (valid.length - 1)) * 100},${100 - ((s[field] ?? 0) / max) * 92}`).join(" ");
  return <div><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="trend" role="img" aria-label="Download and upload traffic over time">
    <polyline points={points("download_bps")} fill="none" stroke="#60a5fa" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
    <polyline points={points("upload_bps")} fill="none" stroke="#34d399" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
  </svg><p className="legend">● Download &nbsp; <span>● Upload</span> &nbsp; Peak {speed(max)}</p></div>;
}

function App() {
  const [page, setPage] = React.useState<Page>("Overview");
  const [health, setHealth] = React.useState("Checking…");
  const [status, setStatus] = React.useState("Unknown");
  const [history, setHistory] = React.useState<Sample[]>([]);
  const [server, setServer] = React.useState<ServerHealth | null>(null);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [h, s, w, host] = await Promise.all([
          fetch(api("health")).then(r => { if (!r.ok) throw Error("Health API unavailable"); return r.json(); }),
          fetch(api("status")).then(r => { if (!r.ok) throw Error("Status API unavailable"); return r.json() as Promise<Status>; }),
          fetch(api("wan/history?limit=300")).then(r => { if (!r.ok) throw Error("WAN history unavailable"); return r.json() as Promise<History>; }),
          fetch(api("server/health")).then(r => r.ok ? r.json() as Promise<ServerHealth> : null).catch(() => null),
        ]);
        if (active) { setHealth(h.status); setStatus(s.router_collection); setHistory(w.samples); setServer(host); setError(""); }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "API unavailable"); }
      finally { if (active) setLoading(false); }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  const latest = history.at(-1);
  const pct = (part: number, total: number) => total > 0 ? (part / total * 100).toFixed(1) + "%" : "—";
  const metric = (label: string, value: string) => <div className="metric" key={label}><span>{label}</span><strong>{value}</strong></div>;
  return <div className="shell">
    <aside><div className="brand">NETWORKBRIDGE</div><p className="aside-note">Local monitoring</p><nav aria-label="Main navigation">{pages.map(name =>
      <button key={name} className={page === name ? "selected" : ""} onClick={() => setPage(name)}>{name}</button>
    )}</nav></aside>
    <main><header><div><h1>{page}</h1><p>Read-only network and server monitoring</p></div><div className="status">API: {health}</div></header>
      {error && <div className="error" role="alert">{error}. Check the local service and authentication.</div>}
      {(page === "Overview" || page === "WAN Traffic") && <>
        <div className="metrics">
          {metric("Router collector", status)}
          {metric("Download", speed(latest?.download_bps))}
          {metric("Upload", speed(latest?.upload_bps))}
          {metric("WAN link", latest?.connected ?? "Unknown")}
        </div>
        <section><h2>WAN throughput</h2><p>Aggregate traffic measured by the router; not per-device bandwidth.</p>
          {loading ? <p>Loading history…</p> : <Trend samples={history} />}</section>
        {page === "WAN Traffic" && <section><h2>Recent measurements</h2><div className="table-wrap"><table><thead><tr><th>Time (UTC)</th><th>Download</th><th>Upload</th><th>Link</th></tr></thead><tbody>
          {history.slice(-50).reverse().map((s,i) => <tr key={s.sampled_at+i}><td>{s.sampled_at}</td><td>{speed(s.download_bps)}</td><td>{speed(s.upload_bps)}</td><td>{s.connected ?? "Unknown"}</td></tr>)}
          {!history.length && <tr><td colSpan={4}>No WAN measurements recorded yet.</td></tr>}
        </tbody></table></div></section>}
      </>}
      {page === "Server Health" && <><div className="metrics">
        {metric("Memory used", server ? pct(server.memory.used_bytes, server.memory.total_bytes) : "Unavailable")}
        {metric("Disk used", server ? pct(server.disk.total_bytes - server.disk.available_bytes, server.disk.total_bytes) : "Unavailable")}
        {metric("Uptime", server ? (server.uptime_seconds / 86400).toFixed(1) + " days" : "Unavailable")}
        {metric("CPU usage", "Sampling pending")}
      </div><section><h2>Host resources</h2><p>Read-only Linux /proc and filesystem snapshot. CPU utilisation requires two samples; no process names or identifiers are collected.</p></section></>}
      {page !== "Overview" && page !== "WAN Traffic" && page !== "Server Health" && <section><h2>{page}</h2><div className="empty">This screen is planned. No live integration is configured yet.</div>
        {page === "Settings" && <p>Router collection is opt-in and requires verified TLS trust. Configuration is managed server-side.</p>}
        {page === "Devices" && <p>Remembered devices are not evidence of active bandwidth usage.</p>}
      </section>}
    </main>
  </div>;
}
createRoot(document.getElementById("root")!).render(<App />);
