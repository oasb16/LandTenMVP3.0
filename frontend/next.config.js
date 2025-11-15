/** @type {import('next').NextConfig} */
const backendUrl = process.env.HEROKU_BACKEND_URL || process.env.BACKEND_INTERNAL_URL || process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_BACKEND_URL: backendUrl,
  },
  experimental: {
    runtime: 'edge',
  },
  turbopack: {
    root: __dirname,
  },
};

module.exports = nextConfig;
