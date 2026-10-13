'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { Key, ShieldCheck, CheckCircle2, AlertCircle, Loader2, X, Sparkles, Cpu } from 'lucide-react';
import { API_BASE } from '@/config/api';

interface ApiKeyModalProps {
  isOpen: boolean;
  onClose: () => void;
  apiKey: string;
  setApiKey: (key: string) => void;
  provider: string;
  setProvider: (provider: string) => void;
}

export const ApiKeyModal: React.FC<ApiKeyModalProps> = ({
  isOpen,
  onClose,
  apiKey,
  setApiKey,
  provider,
  setProvider,
}) => {
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string } | null>(null);

  if (!isOpen) return null;

  const handleVerify = async () => {
    setIsVerifying(true);
    setVerifyResult(null);

    try {
      const res = await axios.post(`${API_BASE}/api/verify-key`, {
        api_key: apiKey,
        provider: provider,
      });

      if (res.data) {
        setVerifyResult({
          valid: res.data.valid,
          message: res.data.message,
        });
      }
    } catch (err: any) {
      setVerifyResult({
        valid: false,
        message: err.response?.data?.detail || err.message || 'API key verification error.',
      });
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-[#FFFFFF] rounded-2xl p-6 relative shadow-2xl border border-[#E2E8F0] space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#E2E8F0]">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#ECFDF5] border border-[#10B981]/30 text-[#10B981] flex items-center justify-center shadow-2xs">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-[#0F172A]">AI Engine & Model Provider</h3>
              <p className="text-xs text-[#64748B]">Select LLM or use deterministic offline engine</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg text-[#64748B] hover:text-[#0F172A] hover:bg-[#E2E8F0] flex items-center justify-center transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Engine Selection & Inputs */}
        <div className="space-y-3.5">
          <div>
            <label className="text-xs font-bold text-[#0F172A] block mb-1.5">
              Active LLM Provider:
            </label>
            <div className="grid grid-cols-1 gap-2">
              {[
                { id: 'gemini', label: 'Google Gemini 1.5 Flash', desc: 'Fast, high-token context, recommended', tag: 'Cloud' },
                { id: 'openai', label: 'OpenAI GPT-4o', desc: 'Deep SQL reasoning & complex schemas', tag: 'Cloud' },
                { id: 'fallback', label: 'Deterministic Engine', desc: 'Offline rule-based engine (Zero config / No key needed)', tag: 'Offline' },
              ].map((opt) => (
                <div
                  key={opt.id}
                  onClick={() => {
                    setProvider(opt.id);
                    setVerifyResult(null);
                  }}
                  className={`p-2.5 rounded-xl border text-xs cursor-pointer transition-all flex items-center justify-between ${
                    provider === opt.id
                      ? 'bg-[#ECFDF5] border-[#10B981]/50 text-[#047857] shadow-2xs font-semibold'
                      : 'bg-[#F8FAFC] border-[#E2E8F0] text-[#475569] hover:bg-[#F1F5F9]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${provider === opt.id ? 'bg-[#10B981]' : 'bg-[#CBD5E1]'}`} />
                    <div>
                      <span className="font-bold text-[#0F172A] block">{opt.label}</span>
                      <span className="text-[10px] text-[#64748B] block">{opt.desc}</span>
                    </div>
                  </div>
                  <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                    opt.tag === 'Offline' ? 'bg-[#E2E8F0] text-[#475569]' : 'bg-[#ECFDF5] text-[#047857]'
                  }`}>
                    {opt.tag}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {provider !== 'fallback' && (
            <div>
              <label className="text-xs font-bold text-[#0F172A] block mb-1">
                API Key:
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => {
                  setApiKey(e.target.value);
                  setVerifyResult(null);
                }}
                placeholder={provider === 'gemini' ? 'AIzaSy...' : 'sk-...'}
                className="w-full bg-[#F8FAFC] border border-[#CBD5E1] px-3.5 py-2 rounded-xl text-xs text-[#0F172A] placeholder:text-[#94A3B8] font-mono focus:outline-none focus:border-[#10B981] focus:ring-1 focus:ring-[#10B981]"
              />
              <p className="text-[10px] text-[#64748B] mt-1">
                Stored in client-side memory for the current session. Never persisted to database.
              </p>
            </div>
          )}

          {/* Verification Status */}
          {verifyResult && (
            <div
              className={`p-3 rounded-xl text-xs font-semibold flex items-center space-x-2 border ${
                verifyResult.valid
                  ? 'bg-[#ECFDF5] border-[#10B981]/40 text-[#047857]'
                  : 'bg-rose-50 border-rose-300 text-rose-900'
              }`}
            >
              {verifyResult.valid ? (
                <CheckCircle2 className="w-4 h-4 text-[#10B981] shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{verifyResult.message}</span>
            </div>
          )}

          {/* Action Footer */}
          <div className="flex justify-between items-center pt-2 border-t border-[#E2E8F0]">
            {provider !== 'fallback' ? (
              <button
                onClick={handleVerify}
                disabled={isVerifying || !apiKey.trim()}
                className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-[#F8FAFC] hover:bg-[#F1F5F9] text-[#0F172A] text-xs font-bold border border-[#E2E8F0] transition-colors disabled:opacity-50 cursor-pointer shadow-2xs"
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#10B981]" />
                    <span>Testing Key...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5 text-[#10B981]" />
                    <span>Test Connectivity</span>
                  </>
                )}
              </button>
            ) : (
              <div />
            )}

            <button
              onClick={onClose}
              className="px-5 py-2 rounded-xl bg-[#10B981] hover:bg-[#059669] text-white text-xs font-bold shadow-md shadow-[#10B981]/20 transition-all cursor-pointer"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
