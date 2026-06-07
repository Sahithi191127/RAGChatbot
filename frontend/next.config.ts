import type { NextConfig } from "next";

/** Used by local `npm run dev` if App Router proxy is bypassed; production uses route handlers. */
const API_URL =
  process.env.API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${API_URL.replace(/\/$/, "")}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
