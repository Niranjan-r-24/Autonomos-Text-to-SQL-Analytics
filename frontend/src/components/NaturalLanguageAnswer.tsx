'use client';

import React, { useState } from 'react';
import { Sparkles, Check, Copy, AlertCircle, BookOpen, ChevronDown, ChevronUp, Bot, FileText } from 'lucide-react';

export interface CitationItem {
  source: string;
  chunk: number;
  excerpt: string;
  score?: number;
}

export interface NaturalLanguageAnswerProps {
  answer?: string | null;
  summary?: string | null;
  status?: 'success' | 'empty' | 'error' | string;
  question?: string;
  generatedBy?: string;
  isLoading?: boolean;
  route?: 'sql' | 'rag' | string;
  citations?: CitationItem[];
}

export const NaturalLanguageAnswer: React.FC<NaturalLanguageAnswerProps> = ({
  answer,
  summary,
  status = 'success',
  question,
  generatedBy = 'Autonomous AI Engine',
  isLoading = false,
  route = 'sql',
  citations = [],
}) => {
  const [copied, setCopied] = useState(false);
  const [showCitations, setShowCitations] = useState(false);

  // Fallback answer if answer is empty
  const displayAnswer = answer || summary || (status === 'empty' ? 'No matching records were found in the database.' : null);

  if (!displayAnswer && !isLoading) {
    return null;
  }

  const handleCopy = () => {
    if (displayAnswer) {
      navigator.clipboard.writeText(displayAnswer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isZero = status === 'empty';
  const isErr = status === 'error';
  const isRag = route === 'rag' || (citations && citations.length > 0);

  // Border & background themes
  let cardBg = 'bg-gradient-to-r from-[#ECFDF5] via-[#F0FDF4] to-[#FFFFFF] border-[#10B981]/50';
  let iconBg = 'bg-[#10B981] text-white';
  let badgeStyle = 'text-[#047857] bg-[#ECFDF5] border-[#10B981]/30';
  let textColor = 'text-[#064E3B]';
  let badgeLabel = isRag ? 'Knowledge Base Answer' : 'Live Business Answer';

  if (isZero) {
    cardBg = 'bg-amber-50/70 border-amber-300/80';
    iconBg = 'bg-amber-500 text-white';
    badgeStyle = 'text-amber-800 bg-amber-100/70 border-amber-300';
    textColor = 'text-amber-900';
    badgeLabel = 'Zero Matches';
  } else if (isErr) {
    cardBg = 'bg-rose-50/70 border-rose-300/80';
    iconBg = 'bg-rose-500 text-white';
    badgeStyle = 'text-rose-800 bg-rose-100/70 border-rose-300';
    textColor = 'text-rose-900';
    badgeLabel = 'Execution Alert';
  }

  return (
    <div
      className={`w-full ${cardBg} border-2 rounded-2xl p-4 sm:p-5 shadow-xs space-y-3 transition-all duration-200`}
      data-testid="natural-language-answer-card"
    >
      {/* Top Banner Row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={`w-7 h-7 rounded-lg ${iconBg} flex items-center justify-center shadow-xs`}>
            {isRag ? <BookOpen className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-black uppercase tracking-wider ${isZero ? 'text-amber-800' : isErr ? 'text-rose-800' : 'text-[#047857]'}`}>
              Natural Language Answer
            </span>
            <span className="hidden sm:inline-block text-[10px] text-[#64748B] font-medium">
              • {generatedBy}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border ${badgeStyle}`}>
            {badgeLabel}
          </span>

          {displayAnswer && (
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 text-[11px] font-medium text-[#475569] hover:text-[#0F172A] bg-white/80 hover:bg-white px-2 py-1 rounded-lg border border-[#E2E8F0] shadow-2xs transition-colors cursor-pointer"
              title="Copy answer to clipboard"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-[#10B981]" />
                  <span className="text-[#10B981] font-semibold text-[10px]">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Main Dynamic Business Answer Text */}
      <div className="pt-0.5">
        <p className={`text-base sm:text-lg font-bold ${textColor} leading-snug tracking-tight`}>
          {displayAnswer}
        </p>
      </div>

      {/* RAG Citations Section (if document knowledge retrieval) */}
      {citations && citations.length > 0 && (
        <div className="pt-2 border-t border-[#10B981]/20">
          <button
            onClick={() => setShowCitations(!showCitations)}
            className="flex items-center justify-between w-full text-left text-xs font-semibold text-[#047857] hover:text-[#065F46] py-1 cursor-pointer transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-[#10B981]" />
              <span>Verified Document Citations ({citations.length} sources)</span>
            </span>
            {showCitations ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showCitations && (
            <div className="mt-2 space-y-2">
              {citations.map((c, idx) => (
                <div
                  key={`${c.source}-${c.chunk}-${idx}`}
                  className="p-2.5 bg-white/90 border border-[#E2E8F0] rounded-xl text-xs space-y-1 shadow-2xs"
                >
                  <div className="flex items-center justify-between font-mono text-[10px] text-[#047857]">
                    <span className="font-bold flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]" />
                      {c.source} (Chunk {c.chunk})
                    </span>
                    {c.score !== undefined && (
                      <span className="text-[#64748B]">Score: {c.score}</span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#334155] leading-relaxed italic">
                    "{c.excerpt}"
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
