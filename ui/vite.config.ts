import { defineConfig } from "vite";
export default defineConfig({ base: "/apps/networkbridge/", server: { proxy: { "/api": "http://127.0.0.1:8765" } } });
