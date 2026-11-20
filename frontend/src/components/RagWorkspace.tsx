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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-stone-900 flex items-center gap-2">
            <FileText className="w-4 h-4 text-forest-700" />
            <span>Independent RAG Document Intelligence</span>
          </h2>
          <p className="text-xs text-stone-500 mt-0.5">
            Semantic document retrieval with source citations. Ingested documents are also available as queryable tables in the Schema Explorer.
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-forest-800 bg-sage-50 border border-sage-200/80 px-2.5 py-1 rounded-md self-start sm:self-auto shrink-0">
          <ShieldCheck className="w-3.5 h-3.5 text-forest-700" />
          <span>Synced to Schema & RAG</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Upload Column */}
        <div className="md:col-span-1 bg-white border border-stone-200/90 rounded-xl p-5 md:p-6 space-y-4 shadow-card">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-600">
            Index Documents
          </h3>
          <form onSubmit={handleFileUpload} className="space-y-3">
            <div className="border-2 border-dashed border-stone-300 hover:border-forest-600/70 rounded-xl p-5 text-center cursor-pointer transition-colors relative bg-stone-50/50 hover:bg-stone-50">
              <input
                type="file"
                accept=".txt,.md,.pdf,.docx,.doc,.json"
                onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <div className="w-10 h-10 rounded-lg bg-sage-50 text-forest-700 flex items-center justify-center mx-auto mb-2 border border-sage-200/80">
                <FileText className="w-5 h-5" />
              </div>
              <p className="text-xs font-semibold text-stone-800">
                {file ? file.name : 'Choose document'}
              </p>
              <p className="text-[10px] text-stone-400 mt-1 font-mono">TXT, MD, PDF, DOCX</p>
            </div>
            <button
              type="submit"
              disabled={!file || uploading}
              className="w-full flex items-center justify-center gap-2 bg-forest-900 hover:bg-forest-850 disabled:opacity-50 text-white text-xs font-medium py-2.5 rounded-lg transition-colors shadow-sm"
            >
              <Upload className="w-3.5 h-3.5 text-emerald-300" />
              <span>{uploading ? 'Ingesting Document...' : 'Index Document'}</span>
            </button>
          </form>

          {uploadSuccess && (
            <div className="p-3.5 bg-sage-50 border border-sage-200 rounded-lg text-xs text-forest-900 space-y-2">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-4 h-4 text-forest-700 shrink-0 mt-0.5" />
                <span className="font-medium">{uploadSuccess}</span>
              </div>
              {createdTableName && onNavigateToSchema && (
                <button
                  type="button"
                  onClick={onNavigateToSchema}
                  className="flex items-center gap-1 text-[11px] font-semibold text-forest-800 hover:text-forest-950 underline pt-1"
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
          <div className="bg-white border border-stone-200/90 rounded-xl p-5 md:p-6 space-y-4 shadow-card">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-stone-600">
              Document Question Answering
            </h3>
            <form onSubmit={handleQuery} className="flex gap-2">
              <input
                type="text"
                value={ragQueryText}
                onChange={(e) => setRagQueryText(e.target.value)}
                placeholder="Ask questions about uploaded enterprise policies, guides, etc."
                className="flex-1 bg-stone-50 border border-stone-300 rounded-lg px-3.5 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600"
              />
              <button
                type="submit"
                disabled={querying || !ragQueryText.trim()}
                className="bg-forest-900 hover:bg-forest-850 disabled:opacity-50 text-white text-xs font-medium px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors shadow-sm shrink-0"
              >
                <Search className="w-3.5 h-3.5 text-emerald-300" />
                <span>{querying ? 'Searching...' : 'Search'}</span>
              </button>
            </form>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex items-center gap-2 shadow-card">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span className="font-mono">{String(error || '')}</span>
            </div>
          )}

          {/* Results & Citations */}
          {result && (
            <div className="bg-white border border-stone-200/90 rounded-xl p-5 md:p-6 space-y-4 shadow-card border-l-4 border-l-forest-700">
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-forest-800">
                  Grounded Synthesis
                </h4>
                <p className="text-sm text-stone-800 mt-1.5 leading-relaxed">
                  {result.answer}
                </p>
              </div>

              {/* Citations List */}
              {result.citations && result.citations.length > 0 && (
                <div className="border-t border-stone-200/80 pt-4 space-y-2.5">
                  <h5 className="text-xs font-semibold uppercase tracking-wider text-stone-600 flex items-center gap-1.5">
                    <BookOpen className="w-3.5 h-3.5 text-stone-500" />
                    <span>Source Citations ({result.citations.length})</span>
                  </h5>
                  <div className="space-y-2.5">
                    {result.citations.map((cite, idx) => (
                      <div
                        key={idx}
                        className="p-3.5 bg-stone-50/70 border border-stone-200/90 rounded-lg text-xs space-y-1.5"
                      >
                        <div className="flex items-center justify-between text-stone-500">
                          <span className="font-semibold text-stone-900 font-mono text-[11px]">
                            {cite.source}
                          </span>
                          <span className="text-[10px] bg-sage-50 text-forest-800 border border-sage-200 px-2 py-0.5 rounded font-mono font-medium">
                            Relevance: {cite.relevance_score}
                          </span>
                        </div>
                        <p className="text-stone-700 italic font-mono text-[11px] leading-relaxed bg-white/70 p-2 rounded border border-stone-100">
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
