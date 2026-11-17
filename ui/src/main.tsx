import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Sample = { sampled_at: string; connected: string | null; download_bps: number | null; upload_bps: number | null };
type History = { samples: Sample[]; count: number };
type Status = { router_collection: string };
type Device = { name: string; address: string | null; connection_type: string | null; last_seen: string | null; observed_at: string };
type DeviceInventory = { devices: Device[]; collection: string };
type Environment = { operating_system: string; kernel: string; architecture: string; python_version: string; monitoring_mode: string };
type Service = { name: string; port: number; state: string; probe: string };
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
  const [services, setServices] = React.useState<Service[] | null>(null);
  const [environment, setEnvironment] = React.useState<Environment | null>(null);
  const [devices, setDevices] = React.useState<DeviceInventory | null>(null);
  const [deviceSearch, setDeviceSearch] = React.useState("");
  const [cpuUsage, setCpuUsage] = React.useState<number | null>(null);
  const previousCpu = React.useRef<{ total_ticks: number; idle_ticks: number } | null>(null);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [h, s, w, host, checks, inventory, deviceInventory] = await Promise.all([
          fetch(api("health")).then(r => { if (!r.ok) throw Error("Health API unavailable"); return r.json(); }),
          fetch(api("status")).then(r => { if (!r.ok) throw Error("Status API unavailable"); return r.json() as Promise<Status>; }),
          fetch(api("wan/history?limit=300")).then(r => { if (!r.ok) throw Error("WAN history unavailable"); return r.json() as Promise<History>; }),
          fetch(api("server/health")).then(r => r.ok ? r.json() as Promise<ServerHealth> : null).catch(() => null),
          fetch(api("services")).then(r => r.ok ? r.json() as Promise<{ services: Service[] }> : null).catch(() => null),
          fetch(api("environment")).then(r => r.ok ? r.json() as Promise<Environment> : null).catch(() => null),
          fetch(api("devices")).then(r => r.ok ? r.json() as Promise<DeviceInventory> : null).catch(() => null),
        ]);
        if (active) { setHealth(h.status); setStatus(s.router_collection); setHistory(w.samples); setServer(host); setServices(checks?.services ?? null); setEnvironment(inventory); setDevices(deviceInventory); setError("");
          if (host) { const old = previousCpu.current; const dt = host.cpu.total_ticks - (old?.total_ticks ?? host.cpu.total_ticks); const di = host.cpu.idle_ticks - (old?.idle_ticks ?? host.cpu.idle_ticks); setCpuUsage(old && dt > 0 && di >= 0 && di <= dt ? 100 * (1 - di / dt) : null); previousCpu.current = host.cpu; } else { previousCpu.current = null; setCpuUsage(null); } }
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
        {metric("CPU usage", cpuUsage === null ? "Sampling pending" : cpuUsage.toFixed(1) + "%")}
      </div><section><h2>Host resources</h2><p>Read-only Linux /proc and filesystem snapshot. CPU utilisation is calculated from consecutive /proc samples; no process names or identifiers are collected.</p></section></>}
      {page === "Services & Apps" && <section><h2>Local service reachability</h2><p>Fixed loopback TCP probes only. Reachable does not guarantee the application is healthy; reverse-proxied applications are not individually tested.</p>
        <div className="table-wrap"><table><thead><tr><th>Service</th><th>Local port</th><th>Reachability</th></tr></thead><tbody>
          {services?.map(service => <tr key={service.name}><td>{service.name}</td><td>{service.port}</td><td>{service.state}</td></tr>)}
          {!services && <tr><td colSpan={3}>Service probes unavailable.</td></tr>}
        </tbody></table></div></section>}
      {page === "Environment Report" && <section><h2>Runtime inventory</h2><p>Minimal read-only host information. No environment variables, addresses, usernames or credentials are collected.</p>
        {environment ? <div className="table-wrap"><table><tbody>{([
          ["Operating system", environment.operating_system], ["Kernel", environment.kernel],
          ["Architecture", environment.architecture], ["Python", environment.python_version],
          ["Monitoring", environment.monitoring_mode],
        ] as [string,string][]).map(([name,value]) => <tr key={name}><th scope="row">{name}</th><td>{value}</td></tr>)}</tbody></table></div>
        : <div className="empty">Environment inventory unavailable.</div>}</section>}
      {page === "Devices" && <section><h2>Remembered devices</h2><p>Stored inventory only; discovery requires a validated router parser. These records do not indicate live connectivity or per-device traffic.</p>
        <p>Collection: {devices?.collection ?? "unavailable"}</p>
        <label htmlFor="device-search">Search devices</label>
        <input id="device-search" className="search" value={deviceSearch} onChange={e => setDeviceSearch(e.target.value)} placeholder="Search by name, address or connection" />
        <div className="table-wrap"><table><thead><tr><th>Name</th><th>Address</th><th>Connection</th><th>Last seen</th></tr></thead><tbody>
          {devices?.devices.filter(d => [d.name, d.address, d.connection_type].some(v => (v ?? "").toLowerCase().includes(deviceSearch.toLowerCase()))).map((d, i) => <tr key={d.name+i}><td>{d.name}</td><td>{d.address ?? "—"}</td><td>{d.connection_type ?? "Unknown"}</td><td>{d.last_seen ?? "Unknown"}</td></tr>)}
          {!devices?.devices.length && <tr><td colSpan={4}>No devices recorded. Discovery is not yet connected.</td></tr>}
        </tbody></table></div></section>}
      {page !== "Overview" && page !== "WAN Traffic" && page !== "Devices" && page !== "Server Health" && page !== "Services & Apps" && page !== "Environment Report" && <section><h2>{page}</h2><div className="empty">This screen is planned. No live integration is configured yet.</div>
        {page === "Settings" && <p>Router collection is opt-in and requires verified TLS trust. Configuration is managed server-side.</p>}
        {page === "Devices" && <p>Remembered devices are not evidence of active bandwidth usage.</p>}
      </section>}
    </main>
  </div>;
}
createRoot(document.getElementById("root")!).render(<App />);
