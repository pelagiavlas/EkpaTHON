import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["icon.svg", "pictos/*.svg"],
      manifest: {
        name: "Study Buddy: μελέτη με βοήθεια που μειώνεται",
        short_name: "Study Buddy",
        description: "Εργαλείο μελέτης και αυτονομίας για φοιτητές.",
        lang: "el",
        start_url: "/",
        display: "standalone",
        background_color: "#ffffff",
        theme_color: "#0a3d8f",
        icons: [{ src: "icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any maskable" }],
      },
      workbox: { navigateFallbackDenylist: [/^\/api/, /^\/docs/] },
    }),
  ],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  preview: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
