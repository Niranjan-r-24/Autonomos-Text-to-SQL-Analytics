'use client';

import React, { useState } from 'react';
import { Grid, Sparkles, Key, Share2, Database, UploadCloud, Users, Check, BookOpen } from 'lucide-react';

interface HeaderProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  provider: string;
  setProvider: (p: string) => void;
  onOpenSchema: () => void;
  onOpenApiKeyModal: () => void;
  onOpenUploadModal: () => void;
  onOpenKnowledgeModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  apiKey,
  setApiKey,
  provider,
  setProvider,
  onOpenSchema,
  onOpenApiKeyModal,
  onOpenUploadModal,
  onOpenKnowledgeModal,
}) => {
  const [copiedNotice, setCopiedNotice] = useState(false);
  const [showTeamInfo, setShowTeamInfo] = useState(false);

  const handleCopyLink = () => {
    if (typeof window !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopiedNotice(true);
      setTimeout(() => setCopiedNotice(false), 2500);
    }
  };

  return (
    <header className="w-full px-8 py-4 flex items-center justify-between bg-clay-150/80 backdrop-blur-md sticky top-0 z-40">
      {/* Brand Logo matching Orvion emblem */}
      <div
        className="flex items-center space-x-3 cursor-pointer"
        onClick={() => setActiveTab('dashboard')}
      >
        <div className="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-md">
          {/* Orvion grid icon */}
          <div className="grid grid-cols-2 gap-0.5 w-4 h-4">
            <div className="bg-lime-400 rounded-xs"></div>
            <div className="bg-white rounded-xs"></div>
            <div className="bg-white rounded-xs"></div>
            <div className="bg-lime-400 rounded-xs"></div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xl font-extrabold tracking-tight text-slate-900">
            Orvion
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-lime-400 text-slate-900">
            Text-to-SQL AI
          </span>
        </div>
      </div>

      {/* Top Center Pill Navigation (Dashboard, Analytics, AI Pulse, Data Schema) */}
      <nav className="flex items-center space-x-1.5 bg-white/90 p-1.5 rounded-full border border-slate-200 shadow-sm">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
            activeTab === 'dashboard'
              ? 'clay-pill-active'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Grid className="w-3.5 h-3.5" />
          <span>Dashboard</span>
        </button>

        <button
          onClick={() => setActiveTab('analytics')}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
            activeTab === 'analytics'
              ? 'clay-pill-active'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <span>Analytics</span>
        </button>

        <button
          onClick={() => setActiveTab('pulse')}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
            activeTab === 'pulse'
              ? 'clay-pill-active'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-lime-500" />
          <span>AI Pulse</span>
        </button>

        <button
          onClick={onOpenSchema}
          className="flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-all"
        >
          <Database className="w-3.5 h-3.5 text-slate-500" />
          <span>Data Schema</span>
        </button>
      </nav>

      {/* Top Right User Team Avatars & Action Pills */}
      <div className="flex items-center space-x-3">
        <button onClick={onOpenKnowledgeModal} className="flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-800 text-xs font-bold shadow-sm hover:bg-slate-50">
          <BookOpen className="w-3.5 h-3.5 text-lime-600" /><span>Knowledge Base</span>
        </button>
        {/* Upload Dataset Button Pill */}
        <button
          onClick={onOpenUploadModal}
          className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-lime-400 hover:bg-lime-300 text-slate-900 text-xs font-extrabold shadow-sm transition-all hover:scale-105"
        >
          <UploadCloud className="w-3.5 h-3.5" />
          <span>Upload Dataset</span>
        </button>

        {/* LLM Engine Dropdown */}
        <div className="relative">
          <select
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            className="bg-white border border-slate-200 text-slate-800 font-semibold px-3 py-1.5 pr-7 rounded-full text-xs cursor-pointer focus:outline-none shadow-sm hover:border-slate-300"
          >
            <option value="gemini">Gemini 1.5 Flash</option>
            <option value="openai">OpenAI GPT-4o</option>
            <option value="fallback">Deterministic AI Engine</option>
          </select>
        </div>

        {/* Floating User Team Avatars with Interactive Info Drawer */}
        <div className="relative">
          <div
            onClick={() => setShowTeamInfo(!showTeamInfo)}
            title="View Workspace Members"
            className="flex items-center -space-x-2 bg-white px-2 py-1 rounded-full border border-slate-200 shadow-sm cursor-pointer hover:border-slate-300 transition-all"
          >
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-amber-400 to-rose-400 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
              JD
            </div>
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
              AK
            </div>
            <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-emerald-400 to-teal-600 text-white text-[10px] font-bold flex items-center justify-center ring-2 ring-white">
              SL
            </div>
            <div className="w-6 h-6 rounded-full bg-slate-900 text-white text-[9px] font-bold flex items-center justify-center ring-2 ring-white">
              +3
            </div>
          </div>

          {showTeamInfo && (
            <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl p-4 shadow-xl border border-slate-200 z-50 space-y-2">
              <div className="flex items-center justify-between border-b pb-2 border-slate-100">
                <span className="text-xs font-extrabold text-slate-900 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-lime-500" />
                  Workspace Team (6)
                </span>
                <button
                  onClick={() => setShowTeamInfo(false)}
                  className="text-slate-400 hover:text-slate-600 text-xs font-bold"
                >
                  ✕
                </button>
              </div>
              <div className="space-y-1.5 text-xs text-slate-700 font-medium">
                <div className="flex items-center justify-between">
                  <span>John Doe (Data Architect)</span>
                  <span className="w-2 h-2 rounded-full bg-lime-400"></span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Alice Kim (AI Engineer)</span>
                  <span className="w-2 h-2 rounded-full bg-lime-400"></span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Sarah Lee (SQL Admin)</span>
                  <span className="w-2 h-2 rounded-full bg-lime-400"></span>
                </div>
                <div className="text-[10px] text-slate-400 font-semibold pt-1">
                  +3 Analytics Analysts active
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Share Button Pill */}
        <button
          onClick={handleCopyLink}
          className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold shadow-sm transition-all relative"
        >
          {copiedNotice ? (
            <>
              <Check className="w-3.5 h-3.5 text-lime-600" />
              <span className="text-lime-600 font-extrabold">Link Copied!</span>
            </>
          ) : (
            <>
              <Share2 className="w-3.5 h-3.5 text-slate-500" />
              <span>Shared</span>
            </>
          )}
        </button>

        {/* API Key Modal Button */}
        <button
          onClick={onOpenApiKeyModal}
          className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all shadow-sm ${
            apiKey
              ? 'bg-lime-400 text-slate-900 border border-lime-500/50'
              : 'bg-slate-900 text-white hover:bg-slate-800'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>{apiKey ? 'Key Set' : 'Check API Key'}</span>
        </button>
      </div>
    </header>
  );
};
