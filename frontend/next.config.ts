import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  },
  images: {
    domains: ["localhost"],
  },
  webpack: (config) => {
    config.cache = false;
    return config;
  },
};

export default nextConfig;
