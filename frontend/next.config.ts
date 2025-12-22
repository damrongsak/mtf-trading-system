import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname, ".."),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:80/api/:path*",
      },
      {
        source: "/static/:path*",
        destination: "http://127.0.0.1:80/static/:path*",
      },
    ];
  },
};

export default nextConfig;
