import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../static/react",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/react.js",
        chunkFileNames: "assets/react-[name].js",
        assetFileNames: "assets/react.[ext]",
      },
    },
  },
});
