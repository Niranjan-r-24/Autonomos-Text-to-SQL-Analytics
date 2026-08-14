'use client';

import React, { useRef, useState } from 'react';
import axios from 'axios';
import { FileText, Loader2, UploadCloud, X } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '');

export function KnowledgeBaseModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  if (!isOpen) return null;
  const upload = async () => {
    if (!file) return;
    setLoading(true); setStatus('');
    const form = new FormData(); form.append('file', file);
    try {
      const { data } = await axios.post(`${API_BASE}/api/knowledge/upload`, form);
      setStatus(`${data.filename} is ready: ${data.chunks} indexed chunks.`);
    } catch (e: any) { setStatus(e.response?.data?.detail || 'Document ingestion failed.'); }
    finally { setLoading(false); }
  };
  return <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-sm p-4 flex items-center justify-center">
    <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl border border-slate-200">
      <div className="flex justify-between items-start mb-5"><div><h2 className="font-extrabold text-slate-900">Knowledge Base</h2><p className="text-xs text-slate-500 mt-1">Upload PDFs for hybrid retrieval, citations, and executive summaries.</p></div><button onClick={onClose}><X className="w-5 h-5 text-slate-400" /></button></div>
      <button onClick={() => fileRef.current?.click()} className="w-full p-7 border-2 border-dashed border-slate-200 rounded-2xl hover:border-lime-400 text-center transition-colors"><UploadCloud className="w-7 h-7 mx-auto text-lime-600 mb-2" /><span className="text-xs font-bold text-slate-700">{file ? file.name : 'Choose a PDF'}</span></button>
      <input ref={fileRef} type="file" accept="application/pdf" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      {status && <p className="mt-3 text-xs font-medium text-slate-600">{status}</p>}
      <button disabled={!file || loading} onClick={upload} className="mt-5 w-full rounded-full bg-slate-900 text-white py-2.5 text-xs font-bold disabled:opacity-50 flex justify-center gap-2">{loading && <Loader2 className="w-4 h-4 animate-spin" />} {loading ? 'Indexing document…' : 'Ingest PDF'}</button>
    </div>
  </div>;
}
