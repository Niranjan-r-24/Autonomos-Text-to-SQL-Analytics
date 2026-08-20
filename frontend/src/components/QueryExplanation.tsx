'use client';

import React from 'react';
import { HelpCircle, Sparkles, BookOpen } from 'lucide-react';

interface QueryExplanationProps {
  explanation: string;
  generatedBy?: string;
}

export const QueryExplanation: React.FC<QueryExplanationProps> = ({
  explanation,
  generatedBy = 'Deterministic Analytics Engine',
}) => {
  if (!explanation) return null;

  return (
    <div className="w-full clay-card p-5 space-y-2.5 bg-white border border-slate-200 shadow-sm transition-all">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-xl bg-lime-400 text-slate-900 flex items-center justify-center font-bold">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-extrabold text-slate-900 flex items-center gap-2">
              Query Explanation
              <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold">
                Plain English Summary
              </span>
            </h3>
            <p className="text-[11px] text-slate-500">What this SQL query accomplishes</p>
          </div>
        </div>

        {generatedBy && (
          <span className="text-[11px] font-semibold text-slate-600 bg-slate-50 border border-slate-200 px-3 py-1 rounded-full">
            Generated via <strong className="text-slate-900">{generatedBy}</strong>
          </span>
        )}
      </div>

      <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-100 text-slate-800 text-xs leading-relaxed font-medium">
        {explanation}
      </div>
    </div>
  );
};
