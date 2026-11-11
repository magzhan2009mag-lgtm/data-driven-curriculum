import type { NextConfig } from "next";

// Сборка для Docker (живая ссылка): интерфейс и API в одном контейнере, наружу открыт только порт
// интерфейса. Поэтому сервер Next собирается в standalone, а API и Swagger доступны через /api/…
// Обычный локальный запуск (next dev / next start) это не затрагивает.
const docker = process.env.NEXT_OUTPUT === "standalone";
const apiUrl = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  ...(docker ? { output: "standalone" as const } : {}),
  devIndicators: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return docker ? [{ source: "/api/:path*", destination: `${apiUrl}/:path*` }] : [];
  },
};

export default nextConfig;
