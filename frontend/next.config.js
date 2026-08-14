/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const apiHostPort = process.env.API_HOSTPORT;

    // On Render the browser talks to this service, while Next.js forwards API
    // requests over Render's private network to the FastAPI service.
    return apiHostPort
      ? [{ source: '/api/:path*', destination: `http://${apiHostPort}/api/:path*` }]
      : [];
  },
};

module.exports = nextConfig;
