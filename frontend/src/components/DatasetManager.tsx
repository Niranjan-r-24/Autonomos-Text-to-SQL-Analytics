'use client';

import React, { useState } from 'react';
import { UploadCloud, CheckCircle2, AlertTriangle, FileSpreadsheet, ArrowRight, FileText } from 'lucide-react';
import { uploadDatasetCsv, formatErrorMessage } from '@/lib/api';

interface DatasetManagerProps {
  onDatasetUploaded: () => void;
  onNavigateToQuery: (query: string) => void;
}

export function DatasetManager({ onDatasetUploaded, onNavigateToQuery }: DatasetManagerProps) {
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
      onDatasetUploaded();
    } catch (err: any) {
      setErrorMessage(formatErrorMessage(err, 'Dataset upload failed.'));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h2 className="text-base font-semibold text-slate-100 flex items-center gap-2">
          <UploadCloud className="w-4 h-4 text-emerald-400" />
          Dataset & Document Ingestion
        </h2>
        <p className="text-xs text-slate-400">
          Upload CSV datasets for SQL analytics or text documents for semantic RAG intelligence.
        </p>
      </div>

      {/* Upload Box Form */}
      <form onSubmit={handleUpload} className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-5">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-2">Select Dataset or Document</label>
          <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500/50 rounded-lg p-6 text-center cursor-pointer transition-colors relative bg-slate-950/40">
            <input
              type="file"
              accept=".csv,.tsv,.txt,.json,.md,.docx,.pdf"
              onChange={handleFileChange}
              className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
            />
            <FileSpreadsheet className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-200">
              {file ? file.name : 'Click or drag a file to upload'}
            </p>
            <p className="text-xs text-slate-500 mt-1">.CSV, .TSV, .TXT, .MD, .JSON, .DOCX, .PDF supported</p>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Target Database Table Name (Optional, for tabular data)
          </label>
          <input
            type="text"
            value={tableName}
            onChange={(e) => setTableName(e.target.value)}
            placeholder="e.g. quarterly_sales (auto-derived from filename if left blank)"
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3.5 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          className="flex items-center justify-center gap-2 w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm py-2.5 rounded-lg transition-colors"
        >
          <UploadCloud className={`w-4 h-4 ${uploading ? 'animate-bounce' : ''}`} />
          <span>{uploading ? 'Ingesting File & Processing Schema...' : 'Upload & Ingest'}</span>
        </button>
      </form>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 bg-red-950/40 border border-red-500/40 rounded-xl text-red-200 text-sm flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-300">Upload Rejected</p>
            <p className="text-xs text-red-300/80 mt-1">{String(errorMessage)}</p>
          </div>
        </div>
      )}

      {/* Success Notification & Table Preview */}
      {successInfo && (
        <div className="p-5 bg-slate-900 border border-emerald-500/30 rounded-xl space-y-4">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-300">{successInfo.message}</p>
              {successInfo.dataset?.row_count !== undefined && (
                <p className="text-xs text-slate-400 mt-0.5">
                  Total Rows Ingested: <span className="font-mono text-slate-200">{successInfo.dataset.row_count}</span>
                </p>
              )}
              {successInfo.data?.total_chunks !== undefined && (
                <p className="text-xs text-slate-400 mt-0.5">
                  Total Passages Indexed: <span className="font-mono text-slate-200">{successInfo.data.total_chunks}</span>
                </p>
              )}
            </div>
          </div>

          {/* Inferred Columns for Datasets */}
          {successInfo.dataset?.columns && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-400 mb-2">Inferred Table Schema</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {successInfo.dataset.columns.map((col: any) => (
                  <div
                    key={col.name}
                    className="p-2 bg-slate-950 border border-slate-800 rounded font-mono text-xs flex justify-between items-center"
                  >
                    <span className="text-slate-300">{col.name}</span>
                    <span className="text-[10px] text-emerald-400 uppercase">{col.type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {successInfo.dataset?.table_name && (
            <button
              onClick={() => onNavigateToQuery(`Show all ${successInfo.dataset.table_name}`)}
              className="flex items-center gap-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 px-3 py-1.5 rounded-lg border border-emerald-500/20 transition-colors"
            >
              <span>Query New Dataset in Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
