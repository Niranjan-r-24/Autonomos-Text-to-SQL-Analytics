'use client';

import React, { useState, useRef } from 'react';
import axios from 'axios';
import {
  UploadCloud, FileText, Database, CheckCircle2, AlertCircle, X, Loader2, Sparkles, Table, ArrowRight
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

interface FileUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (tableName: string, schema: Record<string, any>) => void;
}

export const FileUploadModal: React.FC<FileUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const supportedFormats = [
    { label: '.CSV', desc: 'Comma Separated' },
    { label: '.XLSX / .XLS', desc: 'Excel Sheets' },
    { label: '.JSON', desc: 'JSON Records' },
    { label: '.DB / .SQLITE', desc: 'SQLite DB File' },
    { label: '.SQL', desc: 'SQL Dump Script' },
    { label: '.TSV / .TXT', desc: 'Tab Separated' },
    { label: '.PARQUET', desc: 'Parquet File' },
  ];

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
      setErrorMessage(null);
      setUploadResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setErrorMessage(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await axios.post(`${API_BASE}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      if (res.data && res.data.success) {
        setUploadResult(res.data);
        if (onUploadSuccess) {
          onUploadSuccess(res.data.table_name, res.data.schema);
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'File upload failed.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-md p-4">
      <div className="w-full max-w-xl bg-white rounded-3xl overflow-hidden shadow-2xl border border-slate-200 flex flex-col">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-slate-900 text-lime-400 flex items-center justify-center shadow-sm">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                Import Data File
                <span className="px-2 py-0.5 rounded-full bg-lime-400 text-slate-900 text-[10px] font-extrabold uppercase">
                  All Formats
                </span>
              </h2>
              <p className="text-xs text-slate-500">
                Upload custom datasets to instantly query with Text-to-SQL AI
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white text-slate-400 hover:text-slate-700 flex items-center justify-center border border-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5">
          {/* Supported Format Pills */}
          <div>
            <span className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block mb-2">
              Supported Data Formats:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {supportedFormats.map((fmt) => (
                <span
                  key={fmt.label}
                  className="px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-[11px] font-extrabold text-slate-700"
                >
                  {fmt.label}
                </span>
              ))}
            </div>
          </div>

          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`p-8 rounded-3xl border-2 border-dashed transition-all cursor-pointer text-center flex flex-col items-center justify-center space-y-3 ${
              isDragOver
                ? 'border-lime-500 bg-lime-50/50'
                : selectedFile
                ? 'border-slate-400 bg-slate-50/60'
                : 'border-slate-200 bg-slate-50 hover:border-slate-300'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileChange}
              accept=".csv,.xlsx,.xls,.json,.db,.sqlite,.sqlite3,.sql,.tsv,.txt,.parquet"
              className="hidden"
            />

            <div className="w-12 h-12 rounded-2xl bg-white shadow-sm border border-slate-200 flex items-center justify-center text-slate-700">
              <FileText className="w-6 h-6 text-lime-500" />
            </div>

            {selectedFile ? (
              <div>
                <span className="text-xs font-extrabold text-slate-900 block truncate max-w-md">
                  {selectedFile.name}
                </span>
                <span className="text-[10px] text-slate-500 font-semibold">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Click or drag to replace file
                </span>
              </div>
            ) : (
              <div>
                <p className="text-xs font-extrabold text-slate-900 mb-0.5">
                  Drag and drop your file here, or <span className="text-lime-600 underline">browse</span>
                </p>
                <p className="text-[10px] text-slate-400 font-medium">
                  Supports CSV, Excel (.xlsx), JSON, SQLite (.db), SQL dumps, TSV, Parquet
                </p>
              </div>
            )}
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs font-bold flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Success Summary Card */}
          {uploadResult && (
            <div className="p-4 rounded-2xl bg-lime-50 border border-lime-200 text-slate-900 space-y-2">
              <div className="flex items-center space-x-2 text-lime-800 text-xs font-extrabold">
                <CheckCircle2 className="w-4 h-4 text-lime-600 shrink-0" />
                <span>{uploadResult.message}</span>
              </div>

              {uploadResult.columns && (
                <div className="text-[11px] text-slate-600 font-semibold pt-1 border-t border-lime-200/60">
                  Imported Table: <span className="font-mono font-bold text-slate-900">{uploadResult.table_name}</span> ({uploadResult.row_count} rows)
                  <div className="flex flex-wrap gap-1 mt-1 font-mono text-[10px]">
                    {uploadResult.columns.map((c: string) => (
                      <span key={c} className="px-2 py-0.5 rounded bg-white text-slate-800 border border-lime-300">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end space-x-3 pt-2">
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all"
            >
              Cancel
            </button>

            {uploadResult ? (
              <button
                onClick={onClose}
                className="flex items-center space-x-2 px-6 py-2.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 text-xs font-extrabold shadow-sm transition-all"
              >
                <span>Query New Dataset</span>
                <ArrowRight className="w-4 h-4 text-lime-400" />
              </button>
            ) : (
              <button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="flex items-center space-x-2 px-6 py-2.5 rounded-full bg-lime-400 text-slate-900 hover:bg-lime-300 disabled:opacity-50 text-xs font-extrabold shadow-sm transition-all"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-slate-900" />
                    <span>Parsing & Importing...</span>
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-4 h-4" />
                    <span>Upload & Process Dataset</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
