import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR || ".next",
  output: "standalone",
  devIndicators: false,
  async rewrites() {
    return [{
      source: "/api/:path*",
      destination: `${process.env.INTERNAL_API_BASE || "http://backend:8000"}/:path*`
    }];
  }
};

export default nextConfig;
