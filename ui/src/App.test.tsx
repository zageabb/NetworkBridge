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
