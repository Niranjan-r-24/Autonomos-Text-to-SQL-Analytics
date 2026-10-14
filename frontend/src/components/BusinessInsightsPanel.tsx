'use client';

import React, { useState } from 'react';
import {
  Sparkles, Lightbulb, CheckCircle2, Target, TrendingUp, AlertTriangle,
  Info, Copy, Check, Briefcase, Scale, Compass, HelpCircle, Layers, ArrowRight
} from 'lucide-react';

export interface BusinessInsightsData {
  direct_answer?: string;
  summary?: string;
  key_findings?: string[];
  comparisons?: string[];
  caveats?: string[];
  business_takeaway?: string;
  generated_by?: string;
  grounded?: boolean;
  status?: 'success' | 'empty' | 'error';
}

interface BusinessInsightsPanelProps {
  insights?: BusinessInsightsData | null;
  question?: string;
  rowCount?: number;
  isLoading?: boolean;
  error?: string | null;
}

export const BusinessInsightsPanel: React.FC<BusinessInsightsPanelProps> = ({
  insights,
  question,
  rowCount = 0,
  isLoading = false,
  error = null,
}) => {
  const [copied, setCopied] = useState(false);

  // Copy full insights to clipboard
  const handleCopy = () => {
    if (!insights) return;
    const lines: string[] = [];
    if (question) lines.push(`Query: ${question}\n`);
    if (insights.direct_answer) lines.push(`Direct Answer: ${insights.direct_answer}\n`);
    if (insights.key_findings && insights.key_findings.length > 0) {
      lines.push('Key Findings:');
      insights.key_findings.forEach((kf) => lines.push(`- ${kf}`));
      lines.push('');
    }
    if (insights.comparisons && insights.comparisons.length > 0) {
      lines.push('Comparisons & Benchmarks:');
      insights.comparisons.forEach((c) => lines.push(`- ${c}`));
      lines.push('');
    }
    if (insights.caveats && insights.caveats.length > 0) {
      lines.push('Caveats & Constraints:');
      insights.caveats.forEach((c) => lines.push(`- ${c}`));
      lines.push('');
    }
    if (insights.business_takeaway) {
      lines.push(`Business Takeaway: ${insights.business_takeaway}\n`);
    }

    navigator.clipboard.writeText(lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="w-full bg-[#FFFFFF] border border-[#E2E8F0] rounded-2xl p-5 space-y-4 shadow-2xs animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-5 w-48 bg-slate-200 rounded-md" />
          <div className="h-5 w-32 bg-slate-200 rounded-md" />
        </div>
        <div className="h-16 w-full bg-emerald-50/50 border border-emerald-100 rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="h-20 bg-slate-100 rounded-xl" />
          <div className="h-20 bg-slate-100 rounded-xl" />
        </div>
      </div>
    );
  }

  // 2. Error State
  if (error || (insights && insights.status === 'error')) {
    const errorMsg = error || insights?.summary || 'Execution error encountered.';
    return (
      <div className="w-full bg-rose-50 border border-rose-200 rounded-2xl p-5 space-y-3 shadow-2xs">
        <div className="flex items-center space-x-2.5 text-rose-800">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0" />
          <h3 className="text-xs font-bold uppercase tracking-wider">Business Insights Unavailable</h3>
        </div>
        <p className="text-xs text-rose-700 leading-relaxed font-medium">
          {errorMsg}
        </p>
        {insights?.caveats && insights.caveats.length > 0 && (
          <ul className="text-[11px] text-rose-600 space-y-1 list-disc pl-5">
            {insights.caveats.map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  // 3. Empty Results State (Requirement 7)
  if (rowCount === 0 || (insights && insights.status === 'empty')) {
    const directAns = insights?.direct_answer || `No matching records found for "${question}".`;
    const caveats = insights?.caveats || [
      'The query executed safely against the database but returned zero rows.',
      'Check if active records exist matching your search filters.'
    ];

    return (
      <div className="w-full bg-[#FFFFFF] border border-amber-200/80 rounded-2xl p-5 space-y-4 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-100 pb-3">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-amber-50 border border-amber-200 text-amber-600 flex items-center justify-center font-bold">
              <Info className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-[#0F172A] flex items-center gap-1.5">
                Result Interpretation: Zero Records Found
              </h3>
              <p className="text-[11px] text-[#64748B]">Query executed successfully with 0 matching rows</p>
            </div>
          </div>
          <span className="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-0.5 rounded-full font-semibold">
            Zero Matches
          </span>
        </div>

        {/* Direct explanation */}
        <div className="p-3.5 bg-amber-50/60 border border-amber-200/60 rounded-xl space-y-1">
          <span className="text-[10px] uppercase font-bold text-amber-800 tracking-wider block">
            FINDING
          </span>
          <p className="text-xs text-amber-900 font-medium leading-relaxed">
            {directAns}
          </p>
        </div>

        {/* Caveats / Guidance */}
        <div className="space-y-1.5 pt-1">
          <span className="text-[10px] uppercase font-bold text-[#64748B] tracking-wider block">
            WHY THIS HAPPENED & RECOMMENDED NEXT STEPS:
          </span>
          <ul className="text-xs text-[#475569] space-y-1 pl-4 list-disc">
            {caveats.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      </div>
    );
  }

  // 4. If no insights object provided yet
  if (!insights) {
    return null;
  }

  const generatedByLabel = insights.generated_by || 'Deterministic Insights Engine';
  const hasKeyFindings = insights.key_findings && insights.key_findings.length > 0;
  const hasComparisons = insights.comparisons && insights.comparisons.length > 0;
  const hasCaveats = insights.caveats && insights.caveats.length > 0;
  const hasTakeaway = Boolean(insights.business_takeaway);

  return (
    <div className="w-full bg-[#FFFFFF] border border-[#10B981]/30 hover:border-[#10B981]/50 rounded-2xl p-4 sm:p-5 shadow-2xs space-y-4 transition-all">
      {/* 1. Panel Header & Metadata */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-[#E2E8F0] pb-3">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center font-bold shrink-0">
            <Lightbulb className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="min-w-0">
            <h3 className="text-xs sm:text-sm font-bold text-[#0F172A] flex items-center gap-2">
              Executive Business Insights
              <span className="px-2 py-0.5 rounded-md bg-[#ECFDF5] text-[#047857] text-[10px] font-bold border border-[#10B981]/30 hidden sm:inline-flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3 text-[#10B981]" /> Grounded in Data
              </span>
            </h3>
            <p className="text-[11px] text-[#64748B] truncate">
              Plain-English explanation of actual query results
            </p>
          </div>
        </div>

        {/* Action & Provider Badges */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] text-[#047857] bg-[#F8FAFC] border border-[#E2E8F0] px-2.5 py-1 rounded-lg font-semibold">
            Interpreted via <strong className="text-[#064E3B]">{generatedByLabel}</strong>
          </span>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] px-2.5 py-1 rounded-lg border border-[#E2E8F0] transition-colors cursor-pointer font-medium"
            title="Copy Insights to Clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[#10B981]" />
                <span className="text-[#047857]">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-[#64748B]" />
                <span className="hidden sm:inline">Copy Insights</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 2. Direct Answer Highlight Card (Requirement 3) */}
      {insights.direct_answer && (
        <div className="p-3.5 bg-linear-to-r from-[#ECFDF5] to-[#F0FDF4] border border-[#10B981]/30 rounded-xl space-y-1">
          <div className="flex items-center gap-1.5 text-[#047857] font-bold text-[10px] uppercase tracking-wider">
            <Target className="w-3.5 h-3.5 text-[#10B981]" />
            <span>Direct Answer</span>
          </div>
          <p className="text-xs sm:text-[13px] font-semibold text-[#064E3B] leading-relaxed pl-0.5">
            {insights.direct_answer}
          </p>
        </div>
      )}

      {/* 3. Findings & Comparisons Grid */}
      {(hasKeyFindings || hasComparisons) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-0.5">
          {/* Key Findings List */}
          {hasKeyFindings && (
            <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#0F172A]">
                <TrendingUp className="w-3.5 h-3.5 text-[#10B981]" />
                <span>Key Findings & Rankings</span>
              </div>
              <ul className="space-y-1.5 text-xs text-[#334155]">
                {insights.key_findings!.map((finding, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 leading-snug">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] mt-1.5 shrink-0" />
                    <span className="flex-1 font-medium">{finding}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Comparisons & Distribution List */}
          {hasComparisons && (
            <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-[#0F172A]">
                <Scale className="w-3.5 h-3.5 text-[#0284C7]" />
                <span>Comparisons & Benchmarks</span>
              </div>
              <ul className="space-y-1.5 text-xs text-[#334155]">
                {insights.comparisons!.map((comp, idx) => (
                  <li key={idx} className="flex items-start gap-1.5 leading-snug">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#0284C7] mt-1.5 shrink-0" />
                    <span className="flex-1 font-medium">{comp}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 4. Caveats & Limitations Box (Requirement 3 & 7) */}
      {hasCaveats && (
        <div className="p-3 bg-[#FFFBEB] border border-amber-200/70 rounded-xl space-y-1.5 text-xs">
          <div className="flex items-center gap-1.5 text-amber-800 font-bold text-[11px]">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="uppercase tracking-wider">Data Caveats & Constraints</span>
          </div>
          <ul className="space-y-1 text-[11px] text-amber-900/90 pl-4 list-disc">
            {insights.caveats!.map((caveat, idx) => (
              <li key={idx} className="leading-relaxed">
                {caveat}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 5. Strategic Business Takeaway (Requirement 3) */}
      {hasTakeaway && (
        <div className="p-3.5 bg-[#F0FDF4] border border-[#10B981]/40 rounded-xl flex items-start gap-2.5 text-xs">
          <div className="p-1 bg-[#10B981]/10 rounded-md text-[#10B981] shrink-0 mt-0.5">
            <Compass className="w-4 h-4 text-[#10B981]" />
          </div>
          <div className="space-y-0.5 flex-1">
            <span className="text-[10px] uppercase font-bold text-[#047857] tracking-wider block">
              Strategic Business Takeaway
            </span>
            <p className="text-xs text-[#064E3B] font-medium leading-relaxed">
              {insights.business_takeaway}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
