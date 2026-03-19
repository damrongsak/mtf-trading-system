import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname, ".."),
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://api-gateway:8000/api/:path*",
      },
      {
        source: "/static/:path*",
        destination: "http://nginx:80/static/:path*",
      },
    ];
  },
};

export default nextConfig;
