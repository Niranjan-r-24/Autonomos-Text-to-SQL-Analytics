'use client';

import React, { useEffect } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

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
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-4 shadow-2xl">
        <div className="w-12 h-12 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mx-auto border border-red-500/20">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">Something went wrong</h2>
          <p className="text-xs text-slate-400 mt-1">
            An unexpected error occurred during rendering.
          </p>
        </div>

        {error && (
          <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-red-300 text-left overflow-x-auto max-h-32">
            {String(error.message || error)}
          </div>
        )}

        <div className="flex gap-2 justify-center pt-2">
          <button
            onClick={() => {
              if (typeof window !== 'undefined') {
                localStorage.clear();
              }
              reset();
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset & Retry</span>
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition-colors"
          >
            Reload Page
          </button>
        </div>
      </div>
    </div>
  );
}
