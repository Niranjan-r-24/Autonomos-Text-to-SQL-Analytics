'use client';

import React from 'react';
import { Sparkles, HelpCircle } from 'lucide-react';

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
    <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] hover:border-[#10B981]/40 rounded-2xl p-5 space-y-2.5 shadow-2xs transition-all">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center font-bold">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-[#0F172A] flex items-center gap-2">
              Query Logic Breakdown
              <span className="px-2 py-0.5 rounded-md bg-[#ECFDF5] text-[#047857] text-[10px] font-bold border border-[#10B981]/30">
                Plain English
              </span>
            </h3>
            <p className="text-[11px] text-[#64748B]">What this SQL query accomplishes</p>
          </div>
        </div>

        {generatedBy && (
          <span className="text-[11px] font-semibold text-[#047857] bg-[#F8FAFC] border border-[#E2E8F0] px-3 py-1 rounded-lg">
            Generated via <strong className="text-[#064E3B]">{generatedBy}</strong>
          </span>
        )}
      </div>

      <div className="p-3.5 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#047857] text-xs leading-relaxed font-medium">
        {explanation}
      </div>
    </div>
  );
};
