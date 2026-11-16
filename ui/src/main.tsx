import React from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  const [state, setState] = React.useState("Checking API…");
  React.useEffect(() => {
    fetch("./api/health").then(r => {
      if (!r.ok) throw Error("API unavailable");
      return r.json();
    }).then(d => setState(d.status)).catch(() => setState("API unavailable"));
  }, []);
  return <main><header><h1>NetworkBridge</h1><p>Local network and server monitoring</p></header><section><h2>Platform status</h2><p>API: {state}</p><p>Router collector: Not enabled (Phase 2)</p><p>Server metrics: Planned (Phase 3)</p></section></main>;
}

createRoot(document.getElementById("root")!).render(<App />);
