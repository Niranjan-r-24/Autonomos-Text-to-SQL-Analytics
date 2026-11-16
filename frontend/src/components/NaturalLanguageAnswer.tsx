'use client';

import React, { useState } from 'react';
import { Sparkles, Check, Copy, AlertCircle, BookOpen, ChevronDown, ChevronUp, Bot, FileText, Database, TrendingUp } from 'lucide-react';

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
  rows?: any[];
  columns?: string[];
}

/**
 * Dynamically synthesizes a clean, human-readable business answer
 * directly from SQL results when no pre-generated answer is provided.
 */
function synthesizeDynamicAnswer(
  question?: string,
  rows?: any[],
  columns?: string[],
  answer?: string | null,
  summary?: string | null,
  status?: string
): string {
  // 1. If backend already provided a direct answer, use it
  if (answer && answer.trim()) {
    return answer.trim();
  }

  // 2. If status is empty or no rows
  if (status === 'empty' || !rows || rows.length === 0) {
    if (question && question.trim()) {
      return `No matching records were found in the database for "${question.trim()}".`;
    }
    return 'No matching records were found in the database for this query.';
  }

  const q = (question || '').toLowerCase();

  // Check for browse query ("Show first 10 rows from <tbl>", "browse <tbl>", "Give me all products", "All products")
  const isBrowse =
    q.includes('show first') ||
    q.includes('browse') ||
    q.includes('sample rows') ||
    q.includes('show rows') ||
    q.includes('all rows') ||
    q.includes('give me all') ||
    q.includes('show all') ||
    q.includes('list all') ||
    q.includes('get all') ||
    q.startsWith('first 10') ||
    q.startsWith('first 5') ||
    q.startsWith('all ') ||
    q.endsWith(' table') ||
    q === 'all products' ||
    q === 'products' ||
    q === 'customers' ||
    q === 'orders';

  if (isBrowse && rows.length > 0) {
    const tblMatch = q.match(/(?:from|in|table)\s+[\"']?([a-zA-Z0-9_]+)[\"']?/);
    let tblName = tblMatch ? tblMatch[1] : '';
    if (!tblName) {
      for (const t of ['products', 'customers', 'orders', 'order_items', 'payments', 'support_tickets', 'sales', 'employees']) {
        if (q.includes(t) || q.includes(t.slice(0, -1))) {
          tblName = t;
          break;
        }
      }
    }
    const finalTbl = tblName || 'dataset';
    return `Retrieved ${rows.length} records from the '${finalTbl}' table.`;
  }
  const sampleRow = rows[0] || {};
  const cols = columns && columns.length > 0 ? columns : Object.keys(sampleRow);

  // Helper to format currency or numbers
  const formatVal = (val: any, colName: string = ''): string => {
    if (val === null || val === undefined) return '0';
    const num = Number(val);
    if (isNaN(num)) return String(val);
    const colLower = colName.toLowerCase();
    if (
      colLower.includes('revenue') ||
      colLower.includes('price') ||
      colLower.includes('spent') ||
      colLower.includes('amount') ||
      colLower.includes('cost') ||
      colLower.includes('total_price') ||
      colLower.includes('line_total') ||
      colLower.includes('salary')
    ) {
      return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return Number.isInteger(num) ? num.toLocaleString('en-US') : num.toFixed(2);
  };

  // 3. Single Row Result (e.g. COUNT(*), single scalar aggregate, or top KPI)
  if (rows.length === 1) {
    const countCol = cols.find((c) => {
      const cl = c.toLowerCase();
      return (
        cl.includes('count') ||
        cl === 'cnt' ||
        cl.includes('total_rows') ||
        cl.includes('total_records') ||
        cl.includes('total_orders') ||
        cl.includes('total_customers')
      );
    });

    if (countCol || cols.length === 1) {
      const targetCol = countCol || cols[0];
      const countVal = formatVal(sampleRow[targetCol], targetCol);

      if (q.includes('customer') || q.includes('client') || q.includes('user') || targetCol.toLowerCase().includes('customer')) {
        return `There are ${countVal} customers in the database.`;
      }
      if (q.includes('order') || targetCol.toLowerCase().includes('order')) {
        return `There are ${countVal} orders in the database.`;
      }
      if (q.includes('product') || q.includes('item') || targetCol.toLowerCase().includes('product')) {
        return `There are ${countVal} products in the database.`;
      }
      if (q.includes('ticket') || q.includes('support') || targetCol.toLowerCase().includes('ticket')) {
        return `There are ${countVal} support tickets in the database.`;
      }
      if (q.includes('payment') || targetCol.toLowerCase().includes('payment')) {
        return `There are ${countVal} payments in the database.`;
      }
      if (q.includes('employee') || q.includes('staff') || targetCol.toLowerCase().includes('employee')) {
        return `There are ${countVal} employees in the database.`;
      }
      if (q.includes('sale') || q.includes('transaction') || targetCol.toLowerCase().includes('sale')) {
        return `There are ${countVal} sales transactions in the database.`;
      }
      if (/\b(audit|audit_log|audit_logs)\b/i.test(q) || targetCol.toLowerCase().includes('audit')) {
        return `There are ${countVal} audit log records in the database.`;
      }
      return `There are ${countVal} records in the database for this query.`;
    }

    // Single row with multiple columns (e.g. single top item)
    const preferredNames = ['product_name', 'name', 'customer_name', 'title', 'category', 'item_name', 'car_model', 'action'];
    const nameCol = cols.find((c) => preferredNames.includes(c.toLowerCase()));
    const metricCol = cols.find(
      (c) => typeof sampleRow[c] === 'number' && !c.toLowerCase().endsWith('_id') && c.toLowerCase() !== 'id'
    );

    if (nameCol && metricCol) {
      const nameVal = sampleRow[nameCol];
      const mVal = formatVal(sampleRow[metricCol], metricCol);
      const mLabel = metricCol.replace(/_/g, ' ');
      return `${nameVal} is the top-performing record with ${mVal} in ${mLabel}.`;
    }
  }

  // 4. Multi-Row Ranked / Breakdown Results (e.g. "top 5 revenue products", "Soap is the top-performing product")
  const preferredNameCols = [
    'product_name', 'product', 'name', 'customer_name', 'title', 'item_name',
    'car_model', 'brand', 'category', 'action', 'department', 'city', 'country'
  ];
  const nameCol =
    cols.find((c) => preferredNameCols.includes(c.toLowerCase())) ||
    cols.find((c) => typeof sampleRow[c] === 'string' && !c.toLowerCase().endsWith('_id'));

  const metricCol = cols.find((c) => {
    const cl = c.toLowerCase();
    return typeof sampleRow[c] === 'number' && !cl.endsWith('_id') && cl !== 'id';
  });

  if (nameCol && metricCol) {
    const topItem = rows[0];
    const topName = topItem[nameCol];
    const topVal = formatVal(topItem[metricCol], metricCol);
    const mLabel = metricCol.replace(/_/g, ' ');

    const isBreakdown =
      nameCol.toLowerCase() === 'status' ||
      nameCol.toLowerCase() === 'category' ||
      nameCol.toLowerCase() === 'stage' ||
      q.includes('by status') ||
      q.includes('by category');

    if (isBreakdown) {
      const topName = topItem[nameCol];
      const topVal = formatVal(topItem[metricCol], metricCol);
      const mLabel = metricCol.replace(/_/g, ' ');
      if (rows.length > 1 && rows.length <= 6) {
        const breakdown = rows.map((r) => `${r[nameCol]}: ${formatVal(r[metricCol], metricCol)}`).join(', ');
        return `Breakdown by ${nameCol}: ${breakdown}. (Highest is ${topName} with ${topVal} ${mLabel}).`;
      }
      return `Breakdown by ${nameCol}: '${topName}' leads with ${topVal} ${mLabel}. Total ${rows.length} groups represented.`;
    }

    let entity = 'item';
    if (q.includes('product') || nameCol.toLowerCase().includes('product')) entity = 'product';
    else if (q.includes('customer') || nameCol.toLowerCase().includes('customer')) entity = 'customer';
    else if (q.includes('employee') || nameCol.toLowerCase().includes('employee') || q.includes('salary')) entity = 'employee';
    else if (q.includes('department') || nameCol.toLowerCase().includes('department')) entity = 'department';
    else if (q.includes('car') || nameCol.toLowerCase().includes('car')) entity = 'car model';

    const isLowest = q.includes('lowest') || q.includes('bottom') || q.includes('least') || q.includes('cheapest');
    const rankAdjective = isLowest ? 'lowest-performing' : 'top-performing';

    if (rows.length > 1 && rows.length <= 5) {
      const otherNames = rows.slice(0, Math.min(rows.length, 5)).map((r) => r[nameCol]).filter(Boolean);
      return `${topName} is the ${rankAdjective} ${entity} with ${topVal} in ${mLabel}. The ${rows.length} ${entity}s are: ${otherNames.join(', ')}.`;
    }

    return `${topName} is the ${rankAdjective} ${entity} with ${topVal} in ${mLabel}.`;
  }

  // 5. If summary is available from backend
  if (summary && summary.trim()) {
    return summary.trim();
  }

  // 6. Generic tabular fallback
  if (question && question.trim()) {
    return `Retrieved ${rows.length} records answering "${question.trim()}".`;
  }
  return `Retrieved ${rows.length} matching records from the database.`;
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
  rows = [],
  columns = [],
}) => {
  const [copied, setCopied] = useState(false);
  const [showCitations, setShowCitations] = useState(false);

  // Compute dynamic business answer guaranteed never to be null when rows exist
  const displayAnswer = synthesizeDynamicAnswer(question, rows, columns, answer, summary, status);

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

  const isZero = status === 'empty' || (!isLoading && rows.length === 0 && route !== 'rag');
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
            <span
              className={`text-xs font-black uppercase tracking-wider ${
                isZero ? 'text-amber-800' : isErr ? 'text-rose-800' : 'text-[#047857]'
              }`}
            >
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
        {isLoading ? (
          <div className="space-y-1.5 animate-pulse">
            <div className="h-5 bg-emerald-200/50 rounded-md w-3/4" />
            <div className="h-4 bg-emerald-100/50 rounded-md w-1/2" />
          </div>
        ) : (
          <p className={`text-base sm:text-lg font-bold ${textColor} leading-snug tracking-tight`}>
            {displayAnswer}
          </p>
        )}
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
