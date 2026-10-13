'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';

export const SkeletonLoader: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      className="w-full bg-[#FFFFFF] border border-[#E2E8F0] rounded-2xl p-5 sm:p-6 shadow-sm space-y-4"
    >
      {/* Header bar skeleton */}
      <div className="flex flex-wrap items-center justify-between border-b border-[#E2E8F0] pb-3 gap-2">
        <div className="flex items-center space-x-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-[#ECFDF5] border border-[#10B981]/30 flex items-center justify-center shrink-0">
            <RefreshCw className="w-4 h-4 text-[#10B981] animate-spin" />
          </div>
          <div className="space-y-1">
            <div className="h-3 w-28 bg-[#CBD5E1] rounded animate-pulse" />
            <div className="h-4 w-48 sm:w-64 bg-[#E2E8F0] rounded animate-pulse" />
          </div>
        </div>
        <div className="flex items-center space-x-2 shrink-0">
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#047857] bg-[#ECFDF5] px-2.5 py-1 rounded-lg border border-[#10B981]/30">
            <ShieldCheck className="w-3.5 h-3.5 text-[#10B981]" />
            <span>AST Guard Validating</span>
          </span>
          <div className="h-6 w-20 bg-[#F1F5F9] rounded-lg animate-pulse" />
        </div>
      </div>

      {/* SQL code block skeleton */}
      <div className="space-y-2 bg-[#F8FAFC] p-3.5 rounded-xl border border-[#E2E8F0]">
        <div className="flex items-center justify-between pb-1">
          <div className="h-3 w-24 bg-[#E2E8F0] rounded animate-pulse" />
          <div className="h-3 w-16 bg-[#E2E8F0] rounded animate-pulse" />
        </div>
        <div className="h-3.5 w-3/5 bg-[#CBD5E1] rounded animate-pulse" />
        <div className="h-3.5 w-4/5 bg-[#CBD5E1] rounded animate-pulse" />
        <div className="h-3.5 w-2/5 bg-[#CBD5E1] rounded animate-pulse" />
      </div>

      {/* Insight explanation skeleton */}
      <div className="h-10 bg-[#ECFDF5] border border-[#10B981]/30 rounded-xl p-3 flex items-center space-x-3">
        <Sparkles className="w-4 h-4 text-[#10B981] animate-pulse shrink-0" />
        <div className="h-3.5 w-full bg-[#A7F3D0]/60 rounded animate-pulse" />
      </div>

      {/* Visual / Table skeleton grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
        <div className="h-24 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 flex flex-col justify-between">
          <div className="h-3 w-1/2 bg-[#E2E8F0] rounded animate-pulse" />
          <div className="h-6 w-3/4 bg-[#CBD5E1] rounded animate-pulse" />
        </div>
        <div className="h-24 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 flex flex-col justify-between hidden sm:flex">
          <div className="h-3 w-1/2 bg-[#E2E8F0] rounded animate-pulse" />
          <div className="h-6 w-2/3 bg-[#CBD5E1] rounded animate-pulse" />
        </div>
        <div className="h-24 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl p-3 flex flex-col items-center justify-center text-center space-y-1">
          <RefreshCw className="w-5 h-5 text-[#10B981] animate-spin" />
          <span className="text-xs font-semibold text-[#0F172A]">Translating & Running</span>
          <span className="text-[10px] text-[#64748B]">Parsing schema grounding...</span>
        </div>
      </div>
    </motion.div>
  );
};
