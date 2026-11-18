import React from "react";
import "./style.css";

type Sample = { sampled_at: string; connected: string | null; download_bps: number | null; upload_bps: number | null };
type History = { samples: Sample[]; count: number };
type CollectorHealth = { state: string; last_sample_at: string | null; age_seconds: number | null; stale_after_seconds: number };
type Usage = { day_received_bytes: number; day_transmitted_bytes: number; month_received_bytes: number; month_transmitted_bytes: number; accepted_intervals: number; skipped_intervals: number; coverage: string };
type Status = { router_collection: string; database: "initialized" | "not_initialized" | "unavailable"; wan_history: "available" | "no_measurements" | "unavailable" };
type ResourceAlert = { metric: string; percent: number; threshold: number; severity: string };
type AlertsResponse = { alerts: ResourceAlert[]; count: number; mode: string };
type DiscoveryResult = { devices: { address: string; state: string }[]; probed_hosts: number; note: string };
type IdentifiedDevice = { label: string | null; address: string; mac: string | null; interface: string | null; last_positive_tcp: string | null; positive_scans: number; evidence: string[]; status: string };
type IdentifiedResponse = { devices: IdentifiedDevice[]; collection: string };
type Observation = { address: string; first_seen: string; last_seen: string; positive_scans: number; source: string; recency: string; minutes_since_seen: number | null };
type ObservationEvent = { address: string; observed_at: string; source: string };
type ObservationEventsResponse = { events: ObservationEvent[]; collection: string };
type MonitorCheck = { address: string; checked_at: string; result: "tcp_responded" | "no_tcp_response"; availability_verdict: string };
type MonitorHistory = { checks: MonitorCheck[]; collection: string; note?: string };
type MonitoringReadiness = { state: string; observed_addresses: number; recent_positive?: number; previously_observed?: number; unknown_timestamp?: number; availability_verdict: string; alerts_enabled: boolean };
type ObservationResponse = { devices: Observation[]; collection: string; recency_window_minutes?: number };
type Neighbour = { name: string; address: string; mac: string; interface: string; source: string; state: string };
type NeighboursResponse = { devices: Neighbour[]; collection: string; source: string };
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
  if (!samples.length) return <div className="empty">No WAN measurements recorded yet. Waiting for measurements.</div>;
  const valid = samples.filter(s => s.download_bps != null && s.upload_bps != null);
  if (valid.length < 2) return <div className="empty">Waiting for at least two valid traffic measurements.</div>;
  const max = Math.max(1, ...valid.flatMap(s => [s.download_bps ?? 0, s.upload_bps ?? 0]));
  const width = 100 / valid.length;
  const barWidth = width * 0.38;
  const bars = valid.flatMap((sample, i) => {
    const x = i * width;
    return (["download_bps", "upload_bps"] as const).map((field, j) => {
      const height = Math.max(0, ((sample[field] ?? 0) / max) * 92);
      return <rect key={i + "-" + field} x={x + (j === 0 ? width * 0.1 : width * 0.52)}
        y={100 - height} width={barWidth} height={height}
        fill={j === 0 ? "#60a5fa" : "#34d399"} />;
    });
  });
  return <div><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="trend"
    role="img" aria-label="Grouped bars showing download and upload traffic over time">
    {bars}
  </svg><p className="legend">● Download &nbsp; <span>● Upload</span> &nbsp; Peak {speed(max)}</p></div>;
}

export function App() {
  const [page, setPage] = React.useState<Page>("Overview");
  const [health, setHealth] = React.useState("Checking…");
  const [status, setStatus] = React.useState("Unknown");
  const [wanError, setWanError] = React.useState("");
  const [history, setHistory] = React.useState<Sample[]>([]);
  const [usage, setUsage] = React.useState<Usage | null>(null);
  const [collectorHealth, setCollectorHealth] = React.useState<CollectorHealth | null>(null);
  const [chartMinutes, setChartMinutes] = React.useState(5);
  const [aggregateHistory, setAggregateHistory] = React.useState<Sample[]>([]);
  const [aggregateError, setAggregateError] = React.useState("");
  const [server, setServer] = React.useState<ServerHealth | null>(null);
  const [services, setServices] = React.useState<Service[] | null>(null);
  const [environment, setEnvironment] = React.useState<Environment | null>(null);
  const [devices, setDevices] = React.useState<DeviceInventory | null>(null);
  const [neighbours, setNeighbours] = React.useState<NeighboursResponse | null>(null);
  const [discovered, setDiscovered] = React.useState<DiscoveryResult | null>(null);
  const [observations, setObservations] = React.useState<ObservationResponse | null>(null);
  const [monitoringReadiness, setMonitoringReadiness] = React.useState<MonitoringReadiness | null>(null);
  const [observationEvents, setObservationEvents] = React.useState<ObservationEventsResponse | null>(null);
  const [monitorHistory, setMonitorHistory] = React.useState<MonitorHistory | null>(null);
  const [monitorHistoryError, setMonitorHistoryError] = React.useState("");
  const [monitorAddress, setMonitorAddress] = React.useState("");
  const [monitorLimit, setMonitorLimit] = React.useState(100);
  React.useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ limit: String(monitorLimit) });
    if (monitorAddress.trim()) params.set("address", monitorAddress.trim());
    async function load() {
      try {
        const response = await fetch(api("devices/monitoring-history?" + params.toString()));
        if (!response.ok) throw new Error("Monitoring history unavailable");
        const data = await response.json() as MonitorHistory;
        if (active) { setMonitorHistory(data); setMonitorHistoryError(""); }
      } catch {
        if (active) { setMonitorHistory(null); setMonitorHistoryError("Could not load monitoring history."); }
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 30000);
    return () => { active = false; window.clearInterval(timer); };
  }, [monitorAddress, monitorLimit]);
  const [eventAddress, setEventAddress] = React.useState("");
  const [eventLimit, setEventLimit] = React.useState(100);
  const [eventHistoryError, setEventHistoryError] = React.useState("");
  const [identified, setIdentified] = React.useState<IdentifiedResponse | null>(null);
  React.useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ limit: String(eventLimit) });
    if (eventAddress) params.set("address", eventAddress);
    fetch(api("devices/observation-events?" + params.toString()))
      .then(r => { if (!r.ok) throw new Error("Event history unavailable"); return r.json() as Promise<ObservationEventsResponse>; })
      .then(data => { if (active) { setObservationEvents(data); setEventHistoryError(""); } })
      .catch(() => { if (active) { setObservationEvents(null); setEventHistoryError("Could not load discovery event history."); } });
    return () => { active = false; };
  }, [eventAddress, eventLimit]);

  const [discovering, setDiscovering] = React.useState(false);
  const [discoveryMessage, setDiscoveryMessage] = React.useState("");
  const [alerts, setAlerts] = React.useState<AlertsResponse | null>(null);
  const [deviceSearch, setDeviceSearch] = React.useState("");
  const [editingMac, setEditingMac] = React.useState<string | null>(null);
  const [aliasText, setAliasText] = React.useState("");
  const [aliasMessage, setAliasMessage] = React.useState("");
  const [cpuUsage, setCpuUsage] = React.useState<number | null>(null);
  const previousCpu = React.useRef<{ total_ticks: number; idle_ticks: number } | null>(null);
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(true);
  React.useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const [h, s, w, host, checks, inventory, deviceInventory, resourceAlerts, observed, savedObservations, identifiedDevices, usageTotals, collectorState, monitoringState] = await Promise.all([
          fetch(api("health")).then(r => { if (!r.ok) throw Error("Health API unavailable"); return r.json(); }),
          fetch(api("status")).then(r => { if (!r.ok) throw Error("Status API unavailable"); return r.json() as Promise<Status>; }),
          fetch(api("wan/history?limit=300")).then(async r => {
            if (!r.ok) throw Error(r.status === 503 ? "Database unavailable" : "WAN history unavailable");
            return { history: await r.json() as History, error: "" };
          }).catch((e: unknown) => ({ history: null, error: e instanceof Error ? e.message : "WAN history unavailable" })),
          fetch(api("server/health")).then(r => r.ok ? r.json() as Promise<ServerHealth> : null).catch(() => null),
          fetch(api("services")).then(r => r.ok ? r.json() as Promise<{ services: Service[] }> : null).catch(() => null),
          fetch(api("environment")).then(r => r.ok ? r.json() as Promise<Environment> : null).catch(() => null),
          fetch(api("devices")).then(r => r.ok ? r.json() as Promise<DeviceInventory> : null).catch(() => null),
          fetch(api("alerts")).then(r => r.ok ? r.json() as Promise<AlertsResponse> : null).catch(() => null),
          fetch(api("devices/neighbours")).then(r => r.ok ? r.json() as Promise<NeighboursResponse> : null).catch(() => null),
          fetch(api("devices/observations")).then(r => r.ok ? r.json() as Promise<ObservationResponse> : null).catch(() => null),
          fetch(api("devices/identified")).then(r => r.ok ? r.json() as Promise<IdentifiedResponse> : null).catch(() => null),
          fetch(api("wan/usage")).then(r => r.ok ? r.json() as Promise<Usage> : null).catch(() => null),
          fetch(api("wan/collector-health")).then(r => r.ok ? r.json() as Promise<CollectorHealth> : null).catch(() => null),
          fetch(api("devices/monitoring-readiness")).then(r => r.ok ? r.json() as Promise<MonitoringReadiness> : null).catch(() => null),

        ]);
        if (active) { setHealth(h.status); setStatus(s.router_collection); setHistory(w.history?.samples ?? []); setWanError(w.error); setServer(host); setServices(checks?.services ?? null); setEnvironment(inventory); setDevices(deviceInventory); setAlerts(resourceAlerts); setNeighbours(observed); setObservations(savedObservations); setMonitoringReadiness(monitoringState); setIdentified(identifiedDevices); setUsage(usageTotals); setCollectorHealth(collectorState); setError("");
          if (host) { const old = previousCpu.current; const dt = host.cpu.total_ticks - (old?.total_ticks ?? host.cpu.total_ticks); const di = host.cpu.idle_ticks - (old?.idle_ticks ?? host.cpu.idle_ticks); setCpuUsage(old && dt > 0 && di >= 0 && di <= dt ? 100 * (1 - di / dt) : null); previousCpu.current = host.cpu; } else { previousCpu.current = null; setCpuUsage(null); } }
      } catch (e) { if (active) setError(e instanceof Error ? e.message : "API unavailable"); }
      finally { if (active) setLoading(false); }
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 10000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);
  React.useEffect(() => {
    if (chartMinutes <= 25) return;
    let active = true;
    const hours = chartMinutes / 60;
    async function refreshAggregates() {
      try {
        const response = await fetch(api("wan/aggregated?hours=" + hours));
        if (!response.ok) throw Error("Long-term WAN history unavailable");
        const payload = await response.json() as History;
        if (active) { setAggregateHistory(payload.samples); setAggregateError(""); }
      } catch {
        if (active) { setAggregateHistory([]); setAggregateError("Long-term WAN history unavailable"); }
      }
    }
    void refreshAggregates();
    const timer = window.setInterval(() => void refreshAggregates(), 60_000);
    return () => { active = false; window.clearInterval(timer); };
  }, [chartMinutes]);
  async function discover() {
    setDiscovering(true); setDiscoveryMessage("");
    try {
      const response = await fetch(api("devices/discover"), {method: "POST", headers: {"X-NetworkBridge-Action": "discover"}});
      if (!response.ok) throw new Error(response.status === 403 ? "Active discovery is disabled on the server." : response.status === 429 ? "Please wait one minute between scans." : "Discovery failed.");
      const result = await response.json() as DiscoveryResult;
      setDiscovered(result);
      const saved = await fetch(api("devices/observations"));
      if (saved.ok) setObservations(await saved.json() as ObservationResponse);
      const joined = await fetch(api("devices/identified"));
      if (joined.ok) setIdentified(await joined.json() as IdentifiedResponse);
      setDiscoveryMessage("Checked " + result.probed_hosts + " addresses; " + result.devices.length + " hosts accepted TCP connections.");
    } catch (e) { setDiscoveryMessage(e instanceof Error ? e.message : "Discovery unavailable"); }
    finally { setDiscovering(false); }
  }
  async function saveDeviceAlias() {
    if (!editingMac) return;
    setAliasMessage("");
    try {
      const response = await fetch(api("devices/alias"), {
        method: "PUT", headers: {"Content-Type": "application/json", "X-NetworkBridge-Action": "save-device-alias"},
        body: JSON.stringify({mac: editingMac, label: aliasText})
      });
      if (!response.ok) throw new Error(response.status === 403 ? "Device label editing is disabled on the server." : "Could not save device label.");
      const result = await fetch(api("devices/identified"));
      if (result.ok) setIdentified(await result.json() as IdentifiedResponse);
      setEditingMac(null); setAliasMessage("Device label saved.");
    } catch (e) { setAliasMessage(e instanceof Error ? e.message : "Save failed"); }
  }
  const latest = history.at(-1);
  const chartHistory = React.useMemo(() => {
    if (chartMinutes > 25) return aggregateHistory;
    const end = Date.parse(latest?.sampled_at ?? "");
    if (!Number.isFinite(end)) return [];
    const cutoff = end - chartMinutes * 60_000;
    return history.filter(s => {
      const timestamp = Date.parse(s.sampled_at);
      return Number.isFinite(timestamp) && timestamp >= cutoff && timestamp <= end;
    });
  }, [history, latest?.sampled_at, chartMinutes, aggregateHistory]);
  const gigabytes = (bytes: number | undefined) => bytes === undefined ? "—" : (bytes / 1_000_000_000).toFixed(3) + " GB";
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
          {metric("Router collector", status === "disabled" ? "Router polling disabled" : status === "enabled" ? "Router polling enabled" : status)}
          {metric("Collector health", collectorHealth ? collectorHealth.state === "fresh" ? "Receiving data" : collectorHealth.state === "stale" ? "Stale measurements" : collectorHealth.state.replaceAll("_", " ") : "Unavailable")}
          {metric("WAN history", loading ? "Checking…" : wanError || (history.length ? "Measurements available" : "No measurements"))}
          {metric("Download", speed(latest?.download_bps))}
          {metric("Upload", speed(latest?.upload_bps))}
          {metric("WAN link", latest?.connected ?? "Unknown")}
        </div>
        {page === "WAN Traffic" && <section><h2>WAN usage (UTC)</h2><p>Observed counter changes only. Missing polls, counter resets and retention can make these totals lower than actual usage.</p>
          <div className="metrics">
            {metric("Today downloaded", gigabytes(usage?.day_received_bytes))}
            {metric("Today uploaded", gigabytes(usage?.day_transmitted_bytes))}
            {metric("Month downloaded", gigabytes(usage?.month_received_bytes))}
            {metric("Month uploaded", gigabytes(usage?.month_transmitted_bytes))}
          </div><p>Valid intervals: {usage?.accepted_intervals ?? "—"} · Skipped intervals: {usage?.skipped_intervals ?? "—"}</p>
        </section>}
        {page === "WAN Traffic" && <section><h2>Collector diagnostics</h2><p>Measurement freshness indicates whether the database has received a recent WAN sample. It does not identify the underlying cause of a polling failure.</p>
          <p>State: <strong>{collectorHealth?.state ?? "Unavailable"}</strong> · Last sample: {collectorHealth?.last_sample_at ? new Date(collectorHealth.last_sample_at).toLocaleString() : "None"} · Age: {collectorHealth?.age_seconds == null ? "—" : collectorHealth.age_seconds.toFixed(1) + " seconds"}</p>
          {collectorHealth?.state === "stale" && <div className="error" role="alert">WAN measurements are stale. Check the collector worker and router connectivity.</div>}
        </section>}
        <section><h2>WAN throughput</h2><p>Aggregate traffic measured by the router; not per-device bandwidth.</p>
          <div className="chart-controls"><label htmlFor="wan-period">History window</label><select id="wan-period" value={chartMinutes} onChange={e => setChartMinutes(Number(e.target.value))}>
            <option value={5}>Last 5 minutes</option><option value={15}>Last 15 minutes</option><option value={25}>Last 25 minutes</option><option value={60}>Last hour</option><option value={1440}>Last 24 hours</option><option value={10080}>Last 7 days</option>
          </select><span>Times shown in your local timezone</span></div>
          {loading ? <p>Loading history…</p> : wanError ? <div className="error" role="alert">{wanError}. WAN history could not be loaded.</div> : chartMinutes > 25 && aggregateError ? <div className="error" role="alert">{aggregateError}</div> : <><Trend samples={chartHistory} />{chartHistory.length > 0 && <p className="chart-range">{new Date(chartHistory[0].sampled_at).toLocaleTimeString()} – {new Date(chartHistory[chartHistory.length - 1].sampled_at).toLocaleTimeString()} · {chartHistory.length} samples</p>}</>}</section>
        {page === "WAN Traffic" && <section><h2>Recent measurements</h2><div className="table-wrap"><table><thead><tr><th>Time (UTC)</th><th>Download</th><th>Upload</th><th>Link</th></tr></thead><tbody>
          {history.slice(-50).reverse().map((s,i) => <tr key={s.sampled_at+i}><td>{s.sampled_at}</td><td>{speed(s.download_bps)}</td><td>{speed(s.upload_bps)}</td><td>{s.connected ?? "Unknown"}</td></tr>)}
          {!history.length && <tr><td colSpan={4}>{loading ? "Loading history…" : wanError || "No WAN measurements recorded yet."}</td></tr>}
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
      {page === "Devices" && <><section><h2>Device monitoring readiness</h2>
        <p>Observation evidence only. Availability checks and device alerts are not enabled; an old observation does not mean a device is offline.</p>
        <p>State: {monitoringReadiness?.state ?? "unavailable"} · Observed addresses: {monitoringReadiness?.observed_addresses ?? "—"} · Recent positive: {monitoringReadiness?.recent_positive ?? "—"} · Historical: {monitoringReadiness?.previously_observed ?? "—"}</p>
        <p>Availability verdict: {monitoringReadiness?.availability_verdict ?? "not evaluated"} · Alerts: {monitoringReadiness?.alerts_enabled ? "enabled" : "disabled"}</p>
        </section><section><h2>Device TCP monitoring history</h2>
        <p>Checks are recorded only when the separate opt-in monitoring worker is running. No TCP response is inconclusive and does not establish that a device is offline. No device alerts are enabled.</p>
        <p>Collection: {monitorHistory?.collection ?? "unavailable"}</p>
        <label htmlFor="monitor-address">Filter by monitored IP address</label>
        <input id="monitor-address" className="search" value={monitorAddress} onChange={e => setMonitorAddress(e.target.value)} placeholder="All monitored IP addresses" />
        <label htmlFor="monitor-limit">Maximum checks</label>
        <select id="monitor-limit" value={monitorLimit} onChange={e => setMonitorLimit(Number(e.target.value))}>
          <option value={25}>25</option><option value={100}>100</option><option value={250}>250</option><option value={500}>500</option>
        </select>
        {monitorHistoryError && <p role="status">{monitorHistoryError}</p>}
        <div className="table-wrap"><table><thead><tr><th>IP address</th><th>Checked at</th><th>TCP check</th><th>Availability</th></tr></thead><tbody>
          {monitorHistory?.checks.map((check, i) => <tr key={check.address + check.checked_at + i}>
            <td>{check.address}</td><td>{new Date(check.checked_at).toLocaleString()}</td>
            <td>{check.result === "tcp_responded" ? "TCP response received" : "No TCP response (inconclusive)"}</td>
            <td>Not evaluated</td>
          </tr>)}
          {!monitorHistory?.checks.length && <tr><td colSpan={4}>No monitoring checks stored yet. Monitoring is disabled unless the separate worker is explicitly started.</td></tr>}
        </tbody></table></div>
        </section><section><h2>Combined device evidence</h2><p>Current ARP MAC/interface data joined to historical positive TCP responses by IP address. IP addresses may be reassigned; this is not permanent identity or proof of online status.</p>
        <label htmlFor="device-search">Search devices</label>
        <input id="device-search" className="search" value={deviceSearch} onChange={e => setDeviceSearch(e.target.value)} placeholder="IP address, MAC or interface" />
        <div className="table-wrap"><table><thead><tr><th>Label</th><th>IP address</th><th>MAC</th><th>Interface</th><th>Evidence</th><th>Last TCP response</th></tr></thead><tbody>
        {identified?.devices.filter(d => [d.address, d.mac, d.interface, d.label].some(v => (v ?? "").toLowerCase().includes(deviceSearch.toLowerCase()))).map(d => <tr key={d.address}><td>{d.label ?? "Unnamed"} {d.mac && <button onClick={() => { setEditingMac(d.mac); setAliasText(d.label ?? ""); setAliasMessage(""); }}>Rename</button>}</td><td>{d.address}</td><td>{d.mac ?? "—"}</td><td>{d.interface ?? "—"}</td><td>{d.evidence.join(", ")}</td><td>{d.last_positive_tcp ?? "—"}</td></tr>)}
        {!identified?.devices.length && <tr><td colSpan={6}>No combined evidence yet. Enable discovery on the server.</td></tr>}
        </tbody></table></div>
        {editingMac && <div><p>Set label for {editingMac}</p><label htmlFor="alias-label">Device label</label><input id="alias-label" value={aliasText} maxLength={80} onChange={e => setAliasText(e.target.value)} /><button onClick={() => void saveDeviceAlias()}>Save label</button><button onClick={() => setEditingMac(null)}>Cancel</button></div>}
        {aliasMessage && <p role="status">{aliasMessage}</p>}
        </section><section><h2>Active LAN discovery</h2><p>Optional, server-configured private-subnet TCP checks. This is an active network operation; only use it on networks you administer. Hosts with closed ports may be absent.</p>
        <button disabled={discovering} onClick={() => void discover()}>{discovering ? "Checking LAN…" : "Discover LAN devices"}</button>
        {discoveryMessage && <p role="status">{discoveryMessage}</p>}
        {discovered && <div className="table-wrap"><table><thead><tr><th>IP address</th><th>Result</th></tr></thead><tbody>
          {discovered.devices.map(d => <tr key={d.address}><td>{d.address}</td><td>{d.state}</td></tr>)}
          {!discovered.devices.length && <tr><td colSpan={2}>No hosts accepted TCP connections on the checked ports.</td></tr>}
        </tbody></table></div>}</section><section><h2>Previously discovered devices</h2><p>Positive TCP responses retained between scans. A last-seen timestamp is not proof that the device is online now.</p>
        <p>Collection: {observations?.collection ?? "unavailable"}</p>
        <div className="table-wrap"><table><thead><tr><th>IP address</th><th>First seen</th><th>Last positive response</th><th>Positive scans</th><th>Observation recency</th></tr></thead><tbody>
        {observations?.devices.filter(d => d.address.includes(deviceSearch)).map(d => <tr key={d.address}><td>{d.address}</td><td>{d.first_seen}</td><td>{d.last_seen}</td><td>{d.positive_scans}</td><td>{d.recency === "recent_positive" ? `Seen in last ${observations?.recency_window_minutes ?? 15} min` : d.recency === "previously_observed" ? "Previously observed" : "Unknown"}{d.minutes_since_seen == null ? "" : ` (${d.minutes_since_seen} min ago)`}</td></tr>)}
        {!observations?.devices.length && <tr><td colSpan={5}>No successful active discovery observations stored yet.</td></tr>}
        </tbody></table></div></section><section><h2>Discovery event history</h2><p>Each row records a successful TCP probe during an explicitly requested scan. No automatic scans or offline events are generated.</p>
        <label htmlFor="event-address">Filter by discovered IP address</label>
        <select id="event-address" value={eventAddress} onChange={e => setEventAddress(e.target.value)}>
          <option value="">All discovered devices</option>
          {observations?.devices.map(d => <option key={d.address} value={d.address}>{d.address}</option>)}
        </select>
        <label htmlFor="event-limit">Maximum events</label>
        <select id="event-limit" value={eventLimit} onChange={e => setEventLimit(Number(e.target.value))}>
          <option value={25}>25</option><option value={100}>100</option><option value={250}>250</option><option value={500}>500</option>
        </select>
        {eventHistoryError && <p role="status">{eventHistoryError}</p>}
        <div className="table-wrap"><table><thead><tr><th>IP address</th><th>Observed at</th><th>Source</th></tr></thead><tbody>
          {observationEvents?.events.filter(d => d.address.includes(deviceSearch)).map((d, i) => <tr key={d.address + d.observed_at + i}><td>{d.address}</td><td>{d.observed_at}</td><td>{d.source}</td></tr>)}
          {!observationEvents?.events.length && <tr><td colSpan={3}>No positive discovery events stored yet.</td></tr>}
        </tbody></table></div></section><section><h2>Recently observed LAN neighbours</h2><p>Passive Linux ARP cache only. Recently observed does not mean currently online. Other VLANs and uncontacted devices may be absent.</p>
        <p>Discovery: {neighbours?.collection ?? "unavailable"} · {neighbours?.devices.length ?? 0} observed</p>
        <div className="table-wrap"><table><thead><tr><th>IP address</th><th>MAC address</th><th>Interface</th><th>Observation</th></tr></thead><tbody>
          {neighbours?.devices.filter(d => [d.address,d.mac,d.interface].some(v => v.toLowerCase().includes(deviceSearch.toLowerCase()))).map(d => <tr key={d.address}><td>{d.address}</td><td>{d.mac}</td><td>{d.interface}</td><td>Recently observed</td></tr>)}
          {!neighbours?.devices.length && <tr><td colSpan={4}>No neighbours found. Enable NETWORKBRIDGE_NEIGHBOUR_DISCOVERY_ENABLED=true on the server to collect passive ARP entries.</td></tr>}
        </tbody></table></div></section><section><h2>Remembered devices</h2><p>Stored router inventory; BT Smart Hub device parsing is not yet connected.</p>
        <p>Collection: {devices?.collection ?? "unavailable"}</p>
        <div className="table-wrap"><table><thead><tr><th>Name</th><th>Address</th><th>Connection</th><th>Last seen</th></tr></thead><tbody>
          {devices?.devices.filter(d => [d.name, d.address, d.connection_type].some(v => (v ?? "").toLowerCase().includes(deviceSearch.toLowerCase()))).map((d, i) => <tr key={d.name+i}><td>{d.name}</td><td>{d.address ?? "—"}</td><td>{d.connection_type ?? "Unknown"}</td><td>{d.last_seen ?? "Unknown"}</td></tr>)}
          {!devices?.devices.length && <tr><td colSpan={4}>No devices recorded. Discovery is not yet connected.</td></tr>}
        </tbody></table></div></section></>}
      {page === "Alerts" && <section><h2>Resource threshold alerts</h2><p>Live snapshot evaluation for memory and disk usage. Thresholds are configured on the server. No alert history, acknowledgement or notifications yet.</p>
        {!alerts ? <div className="empty">Resource alert status unavailable.</div> : alerts.count === 0 ? <div className="empty">No memory or disk thresholds exceeded in the latest sample.</div> :
          <div className="table-wrap"><table><thead><tr><th>Resource</th><th>Usage</th><th>Threshold</th><th>Severity</th></tr></thead><tbody>
            {alerts.alerts.map(a => <tr key={a.metric}><td>{a.metric}</td><td>{a.percent}%</td><td>{a.threshold}%</td><td>{a.severity}</td></tr>)}
          </tbody></table></div>}</section>}
      {page !== "Overview" && page !== "WAN Traffic" && page !== "Devices" && page !== "Server Health" && page !== "Services & Apps" && page !== "Environment Report" && page !== "Alerts" && <section><h2>{page}</h2><div className="empty">This screen is planned. No live integration is configured yet.</div>
        {page === "Settings" && <p>Router collection is opt-in and requires verified TLS trust. Configuration is managed server-side.</p>}

      </section>}
    </main>
  </div>;
}
