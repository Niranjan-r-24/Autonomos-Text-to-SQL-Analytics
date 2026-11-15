/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    let backendUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.BACKEND_URL ||
      (process.env.API_HOSTPORT ? `http://${process.env.API_HOSTPORT}` : 'http://127.0.0.1:8000');

    if (backendUrl) {
      backendUrl = backendUrl.replace(/\/+$/, '');
      return [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
      ];
    }

    return [];
  },
};

module.exports = nextConfig;
