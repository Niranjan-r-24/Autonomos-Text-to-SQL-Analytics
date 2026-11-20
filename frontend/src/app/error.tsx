'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, RotateCcw, RefreshCw } from 'lucide-react';

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Application Error caught by error.tsx:', error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[#F8F9F8] text-[#18221D] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white border border-stone-200/90 rounded-2xl p-6 md:p-8 text-center space-y-4 shadow-popover">
        <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center mx-auto border border-red-200">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-stone-900">Something went wrong</h2>
          <p className="text-xs text-stone-500 mt-1">
            An unexpected error occurred during rendering.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-50/60 border border-red-200 rounded-lg text-xs font-mono text-red-800 text-left overflow-x-auto max-h-32">
            {String(error.message || error)}
          </div>
        )}

        <div className="flex gap-2.5 justify-center pt-2">
          <button
            onClick={() => {
              if (typeof window !== 'undefined') {
                localStorage.clear();
              }
              reset();
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-white hover:bg-stone-50 text-stone-700 text-xs font-medium rounded-lg border border-stone-200 transition-colors shadow-subtle"
          >
            <RotateCcw className="w-3.5 h-3.5 text-stone-500" />
            <span>Reset & Retry</span>
          </button>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-1.5 px-4 py-2 bg-forest-900 hover:bg-forest-850 text-white text-xs font-medium rounded-lg transition-colors shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5 text-emerald-300" />
            <span>Reload Page</span>
          </button>
        </div>
      </div>
    </div>
  );
}
