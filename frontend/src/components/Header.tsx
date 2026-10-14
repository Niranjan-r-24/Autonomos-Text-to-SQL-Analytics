'use client';

import React, { useState } from 'react';
import { Database, Settings, UploadCloud, RefreshCw, ChevronDown, Check } from 'lucide-react';

interface HeaderProps {
  apiKey: string;
  provider: string;
  setProvider: (p: string) => void;
  onOpenSchema: () => void;
  onOpenApiKeyModal: () => void;
  onOpenUploadModal: () => void;
  onReSeed?: () => void;
  tableCount?: number;
}

export const Header: React.FC<HeaderProps> = ({
  apiKey,
  provider,
  setProvider,
  onOpenSchema,
  onOpenApiKeyModal,
  onOpenUploadModal,
  onReSeed,
  tableCount = 4,
}) => {
  const [isActionsOpen, setIsActionsOpen] = useState(false);

  const getProviderLabel = () => {
    if (provider === 'gemini') return 'Gemini 1.5 Flash';
    if (provider === 'openai') return 'OpenAI GPT-4o';
    return 'Deterministic Engine';
  };

  return (
    <header className="w-full bg-[#FFFFFF] border-b border-[#E2E8F0] sticky top-0 z-40 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-15 flex items-center justify-between gap-3">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-2.5 shrink-0">
          <div className="w-8 h-8 rounded-xl bg-[#0F172A] text-white flex items-center justify-center shadow-xs">
            <div className="grid grid-cols-2 gap-1 w-3.5 h-3.5">
              <div className="bg-[#10B981] rounded-xs" />
              <div className="bg-white rounded-xs" />
              <div className="bg-white rounded-xs" />
              <div className="bg-[#10B981] rounded-xs" />
            </div>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-base font-black tracking-tight text-[#0F172A]">
              Text-to-SQL
            </span>
            <span className="text-base font-black tracking-tight bg-gradient-to-r from-[#10B981] to-[#047857] bg-clip-text text-transparent">
              Analytics
            </span>
          </div>
        </div>

        {/* Right: Secondary Actions */}
        <div className="flex items-center gap-2">
          {/* Desktop Secondary Actions */}
          <div className="hidden sm:flex items-center gap-2">
            {/* Schema Explorer */}
            <button
              onClick={onOpenSchema}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#334155] hover:text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition-colors cursor-pointer"
              title="Inspect Database Schema"
            >
              <Database className="w-3.5 h-3.5 text-[#10B981]" />
              <span>Schema</span>
            </button>

            {/* Upload Dataset */}
            <button
              onClick={onOpenUploadModal}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#334155] hover:text-[#0F172A] text-xs font-semibold border border-[#E2E8F0] transition-colors cursor-pointer"
              title="Upload dataset (.csv, .xlsx, .json, .sqlite, etc.)"
            >
              <UploadCloud className="w-3.5 h-3.5 text-[#10B981]" />
              <span>Upload Dataset</span>
            </button>

            {/* Provider & API Key Settings */}
            <button
              onClick={onOpenApiKeyModal}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors cursor-pointer ${
                apiKey || provider === 'fallback'
                  ? 'bg-[#ECFDF5] text-[#047857] border-[#10B981]/30 hover:bg-[#D1FAE5]'
                  : 'bg-[#F8FAFC] text-[#334155] border-[#E2E8F0] hover:bg-[#F1F5F9]'
              }`}
              title="LLM Provider & API Key Settings"
            >
              <Settings className="w-3.5 h-3.5 text-[#10B981]" />
              <span>{getProviderLabel()}</span>
            </button>

            {/* Reset / Re-seed */}
            {onReSeed && (
              <button
                onClick={onReSeed}
                className="p-1.5 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#64748B] hover:text-[#0F172A] border border-[#E2E8F0] transition-colors cursor-pointer"
                title="Reset sample enterprise database"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Mobile Secondary Actions Menu */}
          <div className="relative sm:hidden">
            <button
              onClick={() => setIsActionsOpen(!isActionsOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#F8FAFC] text-[#334155] text-xs font-semibold border border-[#E2E8F0] cursor-pointer"
            >
              <span>Actions</span>
              <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isActionsOpen ? 'rotate-180' : ''}`} />
            </button>

            {isActionsOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-white border border-[#E2E8F0] rounded-xl shadow-lg py-1.5 z-50 space-y-0.5">
                <button
                  onClick={() => {
                    setIsActionsOpen(false);
                    onOpenSchema();
                  }}
                  className="w-full px-3 py-2 text-left text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 cursor-pointer"
                >
                  <Database className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Schema Explorer</span>
                </button>
                <button
                  onClick={() => {
                    setIsActionsOpen(false);
                    onOpenUploadModal();
                  }}
                  className="w-full px-3 py-2 text-left text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 cursor-pointer"
                >
                  <UploadCloud className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Upload Dataset</span>
                </button>
                <button
                  onClick={() => {
                    setIsActionsOpen(false);
                    onOpenApiKeyModal();
                  }}
                  className="w-full px-3 py-2 text-left text-xs text-[#334155] hover:bg-[#F8FAFC] flex items-center gap-2 cursor-pointer"
                >
                  <Settings className="w-3.5 h-3.5 text-[#10B981]" />
                  <span>Provider & Key Settings</span>
                </button>
                {onReSeed && (
                  <button
                    onClick={() => {
                      setIsActionsOpen(false);
                      onReSeed();
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-[#64748B] hover:bg-[#F8FAFC] flex items-center gap-2 cursor-pointer border-t border-[#E2E8F0]"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Reset Database</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
