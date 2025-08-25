import path from "path";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");

  return {
    define: {
      "process.env.API_KEY": JSON.stringify(env.GEMINI_API_KEY),
    },
    server: {
      proxy: {
        "/api": {
          target: "http://localhost:7901",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "."),
        "@gradio/client": path.resolve(
          __dirname,
          "./node_modules/@gradio/client/dist/index.js"
        ),
      },
      dedupe: ["@gradio/client"],
    },
  };
});
