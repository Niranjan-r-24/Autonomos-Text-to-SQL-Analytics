/**
 * API configuration and base URL resolver.
 * Handles production (Vercel -> Render backend), local development, and fallback proxying.
 */

export function getApiBaseUrl(): string {
  // 1. Explicitly configured public environment variable
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim()) {
    return envUrl.trim().replace(/\/+$/, '');
  }

  // 2. Client-side browser checks
  if (typeof window !== 'undefined') {
    const host = window.location.hostname || 'localhost';
    const isLocal =
      host === 'localhost' ||
      host === '127.0.0.1' ||
      host.startsWith('192.168.') ||
      host.startsWith('10.') ||
      host.startsWith('172.');
    
    // In local development, direct to FastAPI on port 8000
    if (isLocal) {
      return `http://${host}:8000`;
    }

    // In production on Vercel without NEXT_PUBLIC_API_URL, relative path uses Next.js rewrites
    return '';
  }

  // 3. SSR / Node.js server fallback
  return 'http://localhost:8000';
}

export const API_BASE = getApiBaseUrl();
