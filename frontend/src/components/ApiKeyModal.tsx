'use client';

import React, { useState } from 'react';
import axios from 'axios';
import { Key, ShieldCheck, CheckCircle2, AlertCircle, Loader2, X } from 'lucide-react';
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-white rounded-3xl p-6 relative shadow-2xl border border-slate-200 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-lime-400 text-slate-900 flex items-center justify-center font-bold">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">Configure LLM Provider</h3>
              <p className="text-xs text-slate-500">Select model and configure your API key</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-500 flex items-center justify-center transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3.5">
          <div>
            <label className="text-xs font-bold text-slate-700 block mb-1">
              Select AI Engine / Provider:
            </label>
            <select
              value={provider}
              onChange={(e) => {
                setProvider(e.target.value);
                setVerifyResult(null);
              }}
              className="w-full bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-2xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-lime-400"
            >
              <option value="gemini">Google Gemini 1.5 Flash (Recommended)</option>
              <option value="openai">OpenAI GPT-4o</option>
              <option value="fallback">Deterministic Offline Engine (No Key Needed)</option>
            </select>
          </div>

          {provider !== 'fallback' && (
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
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
                className="w-full bg-slate-50 border border-slate-200 px-3.5 py-2 rounded-2xl text-xs text-slate-900 placeholder:text-slate-400 font-mono focus:outline-none focus:ring-2 focus:ring-lime-400"
              />
              <p className="text-[10px] text-slate-400 mt-1">
                Your API key is kept in browser memory and not permanently stored.
              </p>
            </div>
          )}

          {/* Verification Status */}
          {verifyResult && (
            <div
              className={`p-3 rounded-2xl text-xs font-semibold flex items-center space-x-2 border ${
                verifyResult.valid
                  ? 'bg-lime-50 border-lime-300 text-lime-900'
                  : 'bg-rose-50 border-rose-300 text-rose-900'
              }`}
            >
              {verifyResult.valid ? (
                <CheckCircle2 className="w-4 h-4 text-lime-600 shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
              )}
              <span>{verifyResult.message}</span>
            </div>
          )}

          <div className="flex justify-between items-center pt-2 border-t border-slate-100">
            {provider !== 'fallback' ? (
              <button
                onClick={handleVerify}
                disabled={isVerifying || !apiKey.trim()}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold transition-all disabled:opacity-50"
              >
                {isVerifying ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-900" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-3.5 h-3.5 text-lime-600" />
                    <span>Test API Key</span>
                  </>
                )}
              </button>
            ) : (
              <div></div>
            )}

            <button
              onClick={onClose}
              className="px-5 py-2 rounded-full bg-slate-900 text-white text-xs font-bold hover:bg-slate-800 transition-all shadow-sm"
            >
              Save & Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
