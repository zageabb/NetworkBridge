// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { App } from "./App";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function mockApi(historyStatus: () => number) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const path = new URL(url).pathname;
    if (path.endsWith("/health") && !path.includes("/server/")) {
      return new Response(JSON.stringify({ status: "ok" }));
    }
    if (path.endsWith("/status")) {
      return new Response(JSON.stringify({ router_collection: "disabled", database: historyStatus() === 503 ? "unavailable" : "initialized", wan_history: historyStatus() === 503 ? "unavailable" : "no_measurements" }));
    }
    if (path.endsWith("/wan/history")) {
      return new Response(JSON.stringify({ samples: [], count: 0 }), { status: historyStatus() });
    }
    return new Response("{}", { status: 503 });
  }));
}

test("fresh installation shows healthy empty WAN history with polling disabled", async () => {
  mockApi(() => 200);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "WAN Traffic" }));
  await screen.findByText("API: ok");
  expect(screen.getByText("Router polling disabled")).toBeTruthy();
  expect(screen.getByText("No measurements")).toBeTruthy();
  expect(screen.getByText("No WAN measurements recorded yet.")).toBeTruthy();
  expect(screen.getByText(/Waiting for measurements/)).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});

test("database errors are distinct from empty history and clear on recovery", async () => {
  let status = 503;
  let refresh: (() => void) | undefined;
  const interval = vi.spyOn(window, "setInterval").mockImplementation((callback, delay) => {
    if (delay === 10000) refresh = callback as () => void;
    return 1;
  });
  try {
    mockApi(() => status);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "WAN Traffic" }));
    expect((await screen.findByRole("alert")).textContent).toContain("Database unavailable");
    expect(screen.getByText("API: ok")).toBeTruthy();
    expect(screen.getByText("Router polling disabled")).toBeTruthy();
    expect(screen.queryByText(/No WAN measurements recorded yet/)).toBeNull();
    status = 200;
    refresh!();
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(screen.getByText("No WAN measurements recorded yet.")).toBeTruthy();
  } finally {
    interval.mockRestore();
  }
});


test("device history selector requests server-side IP filter and limit", async () => {
  const urls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    urls.push(url);
    const path = new URL(url).pathname;
    if (path.endsWith("/health")) return new Response(JSON.stringify({ status: "ok" }));
    if (path.endsWith("/status")) return new Response(JSON.stringify({ router_collection: "disabled", database: "initialized", wan_history: "no_measurements" }));
    if (path.endsWith("/wan/history")) return new Response(JSON.stringify({ samples: [], count: 0 }));
    if (path.endsWith("/devices/observations")) return new Response(JSON.stringify({
      collection: "positive_tcp_observations",
      devices: [{ address: "192.0.2.5", first_seen: "2026-11-17T12:00:00Z",
        last_seen: "2026-11-17T12:00:00Z", positive_scans: 1,
        recency: "previously_observed", minutes_since_seen: 60 }],
    }));
    if (path.endsWith("/devices/observation-events")) return new Response(JSON.stringify({ events: [], collection: "positive_tcp_events" }));
    return new Response("{}", { status: 503 });
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Devices" }));
  await screen.findByRole("option", { name: "192.0.2.5" });
  fireEvent.change(screen.getByLabelText("Filter by discovered IP address"), { target: { value: "192.0.2.5" } });
  fireEvent.change(screen.getByLabelText("Maximum events"), { target: { value: "25" } });
  await waitFor(() => expect(urls.some(url => {
    const parsed = new URL(url);
    return parsed.pathname.endsWith("/devices/observation-events")
      && parsed.searchParams.get("address") === "192.0.2.5"
      && parsed.searchParams.get("limit") === "25";
  })).toBe(true));
});

test("Devices screen distinguishes inconclusive TCP checks from offline status", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const path = new URL(url).pathname;
    if (path.endsWith("/health") && !path.includes("/server/")) {
      return new Response(JSON.stringify({ status: "ok" }));
    }
    if (path.endsWith("/status")) {
      return new Response(JSON.stringify({ router_collection: "disabled", database: "initialized", wan_history: "no_measurements" }));
    }
    if (path.endsWith("/wan/history")) {
      return new Response(JSON.stringify({ samples: [], count: 0 }));
    }
    if (path.endsWith("/devices/monitoring-history")) {
      return new Response(JSON.stringify({ collection: "opt_in_tcp_checks", checks: [
        { address: "192.168.1.10", checked_at: "2026-11-18T05:00:00+00:00", result: "no_tcp_response", availability_verdict: "not_evaluated" }
      ] }));
    }
    return new Response("{}", { status: 503 });
  }));
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Devices" }));
  expect(await screen.findByText("No TCP response (inconclusive)")).toBeTruthy();
  expect(screen.getByText("Not evaluated")).toBeTruthy();
  expect(screen.getByText("192.168.1.10")).toBeTruthy();
});
