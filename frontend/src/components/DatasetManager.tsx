'use client';

import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, FileSpreadsheet, ArrowRight, FileText } from 'lucide-react';
import { uploadDatasetCsv, formatErrorMessage } from '@/lib/api';

interface DatasetManagerProps {
  onDatasetUploaded: (schema?: any) => void;
  onNavigateToQuery: (query: string) => void;
  onNavigateToSchema?: () => void;
}

export function DatasetManager({ onDatasetUploaded, onNavigateToQuery, onNavigateToSchema }: DatasetManagerProps) {
  const [file, setFile] = useState<File | null>(null);
  const [tableName, setTableName] = useState('');
  const [uploading, setUploading] = useState(false);
  const [successInfo, setSuccessInfo] = useState<any | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!tableName) {
        setTableName(selected.name.replace(/\.[^/.]+$/, '').toLowerCase().replace(/[^a-z0-9_]/g, '_'));
      }
      setSuccessInfo(null);
      setErrorMessage(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setErrorMessage(null);
    setSuccessInfo(null);

    try {
      const res = await uploadDatasetCsv(file, tableName.trim() || undefined);
      setSuccessInfo(res);
      setFile(null);
      setTableName('');
      onDatasetUploaded(res);
    } catch (err: any) {
      setErrorMessage(formatErrorMessage(err, 'Dataset upload failed.'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h2 className="text-base font-semibold text-stone-900 flex items-center gap-2">
          <UploadCloud className="w-4 h-4 text-forest-700" />
          <span>Dataset & Document Ingestion</span>
        </h2>
        <p className="text-xs text-stone-500 mt-0.5">
          Upload CSV datasets for SQL analytics or text documents for semantic RAG intelligence.
        </p>
      </div>

      {/* Upload Box Form */}
      <form onSubmit={handleUpload} className="bg-white border border-stone-200/90 rounded-xl p-6 md:p-7 space-y-5 shadow-card">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-2">
            Select Dataset or Document
          </label>
          <div className="border-2 border-dashed border-stone-300 hover:border-forest-600/70 rounded-xl p-7 text-center cursor-pointer transition-colors relative bg-stone-50/50 hover:bg-stone-50">
            <input
              type="file"
              accept=".csv,.tsv,.txt,.json,.md,.docx,.pdf"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
            <div className="w-12 h-12 rounded-xl bg-sage-50 text-forest-700 flex items-center justify-center mx-auto mb-3 border border-sage-200/80">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <p className="text-sm font-semibold text-stone-800">
              {file ? file.name : 'Click or drag a file to upload'}
            </p>
            <p className="text-xs text-stone-400 mt-1 font-mono">
              .CSV, .TSV, .TXT, .MD, .JSON, .DOCX, .PDF supported
            </p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5">
            Target Database Table Name (Optional, for tabular data)
          </label>
          <input
            type="text"
            value={tableName}
            onChange={(e) => setTableName(e.target.value)}
            placeholder="e.g. quarterly_sales (auto-derived from filename if left blank)"
            className="w-full bg-white border border-stone-300 rounded-lg px-3.5 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 focus:outline-none focus:border-forest-600 focus:ring-1 focus:ring-forest-600 shadow-subtle"
          />
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          className="flex items-center justify-center gap-2 w-full bg-forest-900 hover:bg-forest-850 disabled:opacity-50 text-white font-medium text-sm py-2.5 rounded-lg transition-colors shadow-sm"
        >
          <UploadCloud className={`w-4 h-4 text-emerald-300 ${uploading ? 'animate-bounce' : ''}`} />
          <span>{uploading ? 'Ingesting File & Processing Schema...' : 'Upload & Ingest'}</span>
        </button>
      </form>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-900 text-sm flex items-start gap-3 shadow-card">
          <AlertTriangle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-900">Upload Rejected</p>
            <p className="text-xs text-red-700 mt-1 font-mono">{String(errorMessage)}</p>
          </div>
        </div>
      )}

      {/* Success Notification & Table Preview */}
      {successInfo && (
        <div className="p-6 bg-white border border-sage-300 rounded-xl space-y-4 shadow-card border-l-4 border-l-forest-700">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-forest-700 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-stone-900">{successInfo.message}</p>
              {(successInfo.row_count !== undefined || successInfo.dataset?.row_count !== undefined) && (
                <p className="text-xs text-stone-500 mt-0.5">
                  Total Rows Ingested:{' '}
                  <span className="font-mono text-stone-800 font-semibold">
                    {successInfo.row_count ?? successInfo.dataset?.row_count}
                  </span>
                </p>
              )}
              {successInfo.data?.total_chunks !== undefined && (
                <p className="text-xs text-stone-500 mt-0.5">
                  Total Passages Indexed: <span className="font-mono text-stone-800 font-semibold">{successInfo.data.total_chunks}</span>
                </p>
              )}
            </div>
          </div>

          {/* Inferred Columns for Datasets */}
          {(successInfo.columns || successInfo.dataset?.columns) && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-600 mb-2">Inferred Table Schema</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {(successInfo.columns || successInfo.dataset?.columns).map((col: any) => (
                  <div
                    key={col.name}
                    className="p-2.5 bg-stone-50 border border-stone-200 rounded-lg font-mono text-xs flex justify-between items-center shadow-subtle"
                  >
                    <span className="text-stone-800 font-medium truncate">{col.name}</span>
                    <span className="text-[10px] text-forest-800 bg-sage-100 px-1.5 py-0.2 rounded uppercase shrink-0">{col.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(successInfo.table_name || successInfo.dataset?.table_name) && (
            <div className="flex flex-wrap items-center gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => {
                  if (onNavigateToSchema) {
                    onNavigateToSchema();
                  } else {
                    onNavigateToQuery(`Show all ${successInfo.table_name || successInfo.dataset?.table_name}`);
                  }
                }}
                className="flex items-center gap-1.5 text-xs font-medium text-white bg-forest-900 hover:bg-forest-850 px-3.5 py-2 rounded-lg transition-colors shadow-sm"
              >
                <span>View Table in Schema Explorer</span>
                <ArrowRight className="w-3.5 h-3.5 text-emerald-300" />
              </button>
              <button
                type="button"
                onClick={() => onNavigateToQuery(`Show all ${successInfo.table_name || successInfo.dataset?.table_name}`)}
                className="flex items-center gap-1.5 text-xs font-medium text-stone-700 hover:text-stone-900 bg-white hover:bg-stone-50 px-3.5 py-2 rounded-lg border border-stone-200 transition-colors shadow-subtle"
              >
                <span>Query New Dataset in Workspace</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
