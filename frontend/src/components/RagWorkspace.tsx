'use client';

import React, { useState } from 'react';
import { FileText, Upload, Search, BookOpen, AlertCircle, CheckCircle2, ShieldCheck, ArrowRight } from 'lucide-react';
import { uploadRagDocument, queryRag, formatErrorMessage } from '@/lib/api';
import { RagResult } from '@/types';

interface RagWorkspaceProps {
  onDocumentUploaded?: (schema?: any) => void;
  onNavigateToSchema?: () => void;
}

export function RagWorkspace({ onDocumentUploaded, onNavigateToSchema }: RagWorkspaceProps) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [createdTableName, setCreatedTableName] = useState<string | null>(null);

  const [ragQueryText, setRagQueryText] = useState('');
  const [querying, setQuerying] = useState(false);
  const [result, setResult] = useState<RagResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    setUploadSuccess(null);
    setCreatedTableName(null);

    try {
      const res = await uploadRagDocument(file);
      setUploadSuccess(res.message);
      if (res.table_name || res.data?.table_name) {
        setCreatedTableName(res.table_name || res.data?.table_name);
      }
      setFile(null);
      if (onDocumentUploaded) {
        onDocumentUploaded(res.schema);
      }
    } catch (err: any) {
      setError(formatErrorMessage(err, 'RAG document upload failed.'));
    } finally {
      setUploading(false);
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ragQueryText.trim()) return;

    setQuerying(true);
    setError(null);

    try {
      const res = await queryRag(ragQueryText.trim());
      setResult(res);
    } catch (err: any) {
      setError(formatErrorMessage(err, 'RAG query failed.'));
    } finally {
      setQuerying(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header & Isolation Notice */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            <FileText className="w-4 h-4 text-emerald-400" />
            Independent RAG Document Intelligence
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Semantic document retrieval with source citations. Ingested documents are also available as queryable tables in the Schema Explorer.
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Synced to Schema & RAG</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Upload Column */}
        <div className="md:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Index Documents
          </h3>
          <form onSubmit={handleFileUpload} className="space-y-3">
            <div className="border border-dashed border-slate-700 hover:border-emerald-500/50 rounded-lg p-4 text-center cursor-pointer transition-colors relative bg-slate-950/40">
              <input
                type="file"
                accept=".txt,.md,.pdf,.docx,.doc,.json"
                onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <FileText className="w-6 h-6 text-emerald-400 mx-auto mb-1.5" />
              <p className="text-xs font-medium text-slate-300">
                {file ? file.name : 'Choose document'}
              </p>
              <p className="text-[10px] text-slate-500 mt-1">TXT, MD, PDF, DOCX</p>
            </div>
            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium py-2 rounded-lg transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>{uploading ? 'Ingesting Document...' : 'Index Document'}</span>
            </button>
          </form>

          {uploadSuccess && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-xs text-emerald-300 space-y-2">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{uploadSuccess}</span>
              </div>
              {createdTableName && onNavigateToSchema && (
                <button
                  type="button"
                  onClick={onNavigateToSchema}
                  className="flex items-center gap-1 text-[11px] font-semibold text-emerald-300 hover:text-white underline pt-1"
                >
                  <span>View &quot;{createdTableName}&quot; in Schema Explorer</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Query & Citations Column */}
        <div className="md:col-span-2 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Document Question Answering
            </h3>
            <form onSubmit={handleQuery} className="flex gap-2">
              <input
                type="text"
                value={ragQueryText}
                onChange={(e) => setRagQueryText(e.target.value)}
                placeholder="Ask questions about uploaded enterprise policies, guides, etc."
                className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <button
                type="submit"
                disabled={querying || !ragQueryText.trim()}
                className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
              >
                <Search className="w-3.5 h-3.5" />
                <span>{querying ? 'Searching...' : 'Search'}</span>
              </button>
            </form>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-950/40 border border-red-500/40 rounded-lg text-xs text-red-200 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{String(error || '')}</span>
            </div>
          )}

          {/* Results & Citations */}
          {result && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                  Grounded Synthesis
                </h4>
                <p className="text-sm text-slate-200 mt-1 leading-relaxed">
                  {result.answer}
                </p>
              </div>

              {/* Citations List */}
              {result.citations && result.citations.length > 0 && (
                <div className="border-t border-slate-800 pt-3 space-y-2">
                  <h5 className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5" />
                    <span>Source Citations ({result.citations.length})</span>
                  </h5>
                  <div className="space-y-2">
                    {result.citations.map((cite, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-slate-400">
                          <span className="font-semibold text-slate-300 font-mono">
                            {cite.source}
                          </span>
                          <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-emerald-400">
                            Relevance: {cite.relevance_score}
                          </span>
                        </div>
                        <p className="text-slate-300 italic font-mono text-[11px] leading-relaxed">
                          &quot;{cite.excerpt}&quot;
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
