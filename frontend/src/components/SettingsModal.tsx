'use client';

import React, { useState } from 'react';
import { X, Key, Sparkles, Shield, Check } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentProvider: string;
  onSaveProvider: (provider: string, apiKey: string) => void;
}

export function SettingsModal({
  isOpen,
  onClose,
  currentProvider,
  onSaveProvider,
}: SettingsModalProps) {
  const [provider, setProvider] = useState(currentProvider || 'gemini');
  const [apiKey, setApiKey] = useState('');
  const [saved, setSaved] = useState(false);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onSaveProvider(provider, apiKey);
    setSaved(true);
    setTimeout(() => {
      setSaved(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-900/40 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white border border-stone-200/90 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-popover relative">
        <button
          onClick={onClose}
          className="absolute right-4 top-4 text-stone-400 hover:text-stone-700 p-1 rounded-md transition-colors"
          aria-label="Close settings"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-sage-50 text-forest-700 flex items-center justify-center border border-sage-200/80 shadow-subtle">
            <Key className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-stone-900">AI Provider & API Configuration</h3>
            <p className="text-xs text-stone-500">Configure your LLM backend or use the built-in engine</p>
          </div>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-2">
              Select AI Model Provider
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'gemini', label: 'Google Gemini' },
                { id: 'openai', label: 'OpenAI GPT' },
                { id: 'schema_fallback', label: 'Schema Engine' },
              ].map((p) => (
                <button
                  type="button"
                  key={p.id}
                  onClick={() => setProvider(p.id)}
                  className={`p-2.5 rounded-lg text-xs font-medium border text-center transition-all ${
                    provider === p.id
                      ? 'bg-sage-100 border-forest-600 text-forest-900 font-bold shadow-xs'
                      : 'bg-stone-50 border-stone-200 text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {provider !== 'schema_fallback' && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
                API Key for {provider === 'gemini' ? 'Google Gemini' : 'OpenAI'}
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Paste your API key (leave blank to use backend .env)"
                className="w-full bg-stone-50 border border-stone-300 rounded-lg px-3 py-2 text-xs text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600 font-mono shadow-subtle"
              />
              <p className="text-[11px] text-stone-500 mt-1">
                Keys remain in your browser session and are never persisted to disk.
              </p>
            </div>
          )}

          <div className="p-3.5 bg-sage-50/80 border border-sage-200 rounded-lg flex items-start gap-2.5 text-xs text-stone-600">
            <Shield className="w-4 h-4 text-forest-700 shrink-0 mt-0.5" />
            <span className="leading-relaxed">
              If no API key is provided, Autonomos uses the zero-cost schema-grounded deterministic engine, ensuring 100% offline accuracy.
            </span>
          </div>

          <div className="flex justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-stone-600 hover:text-stone-900 hover:bg-stone-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-forest-900 hover:bg-forest-850 text-white transition-colors shadow-sm"
            >
              {saved ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-300" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>Save Configuration</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
