'use client';

import React, { useState } from 'react';
import { Grid, Sparkles, Key, Share2, Database, ChevronDown, Check } from 'lucide-react';

interface HeaderProps {
  apiKey: string;
  setApiKey: (key: string) => void;
  provider: string;
  setProvider: (p: string) => void;
  onOpenSchema: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  apiKey,
  setApiKey,
  provider,
  setProvider,
  onOpenSchema
}) => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showKeyModal, setShowKeyModal] = useState(false);

  return (
    <header className="w-full px-8 py-4 flex items-center justify-between bg-clay-150/80 backdrop-blur-md sticky top-0 z-40">
      {/* Brand Logo matching Orvion emblem */}
      <div className="flex items-center space-x-3">
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

      {/* Top Center Pill Navigation (Dashboard, Analytics, AI Pulse, Data) */}
      <nav className="flex items-center space-x-1.5 bg-white/90 p-1.5 rounded-full border border-slate-200 shadow-sm">
        <button
          onClick={() => setActiveTab('dashboard')}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
            activeTab === 'dashboard'
              ? 'clay-pill-active'
              : 'text-slate-600 hover:text-slate-900'
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
              : 'text-slate-600 hover:text-slate-900'
          }`}
        >
          <span>Analytics</span>
        </button>

        <button
          onClick={() => setActiveTab('pulse')}
          className={`flex items-center space-x-2 px-4 py-1.5 rounded-full text-xs font-bold transition-all ${
            activeTab === 'pulse'
              ? 'clay-pill-active'
              : 'text-slate-600 hover:text-slate-900'
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

        {/* Floating User Team Avatars */}
        <div className="flex items-center -space-x-2 bg-white px-2 py-1 rounded-full border border-slate-200 shadow-sm">
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

        {/* Share Button Pill */}
        <button className="flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 text-xs font-bold shadow-sm transition-all">
          <Share2 className="w-3.5 h-3.5 text-slate-500" />
          <span>Shared</span>
        </button>

        {/* API Key Modal Button */}
        <button
          onClick={() => setShowKeyModal(true)}
          className={`flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all shadow-sm ${
            apiKey
              ? 'bg-lime-400 text-slate-900 border border-lime-500/50'
              : 'bg-slate-900 text-white hover:bg-slate-800'
          }`}
        >
          <Key className="w-3.5 h-3.5" />
          <span>{apiKey ? 'Key Set' : 'API Key'}</span>
        </button>
      </div>

      {/* API Key Modal */}
      {showKeyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-white rounded-3xl p-6 relative shadow-2xl border border-slate-200">
            <h3 className="text-base font-bold text-slate-900 mb-1 flex items-center gap-2">
              <Key className="w-5 h-5 text-lime-500" />
              Configure LLM API Key
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Enter your Gemini or OpenAI API key. Orvion includes a high-precision deterministic engine when no key is provided.
            </p>

            <div className="space-y-4">
              <div>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="AIzaSy... / sk-..."
                  className="w-full bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-2xl text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-lime-400"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  onClick={() => setShowKeyModal(false)}
                  className="px-5 py-2 rounded-full bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-all shadow-sm"
                >
                  Save & Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};
