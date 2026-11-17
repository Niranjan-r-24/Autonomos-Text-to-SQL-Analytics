/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    let backendUrl =
      process.env.NEXT_PUBLIC_API_URL ||
      process.env.BACKEND_URL ||
      (process.env.API_HOSTPORT ? `http://${process.env.API_HOSTPORT}` : 'https://autonomos-text2sql-api.onrender.com');

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
