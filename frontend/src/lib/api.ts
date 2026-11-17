import axios from 'axios';
import { SchemaInfo, QueryResult, HistoryItem, RagResult } from '@/types';

const getApiBase = () => {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  // Connect directly to the live production API so all features work reliably
  return 'https://autonomos-text2sql-api.onrender.com';
};

const client = axios.create({
  baseURL: getApiBase(),
  timeout: 45000,
});

export function formatErrorMessage(err: any, fallback: string = 'An unexpected error occurred.'): string {
  if (!err) return fallback;
  if (typeof err === 'string') return err;

  // Extract FastAPI or Axios detail or error
  const detail =
    err?.response?.data?.detail ??
    err?.response?.data?.error ??
    err?.detail ??
    err?.error;

  if (detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (typeof d === 'string' ? d : d?.msg ? `${d.msg} (${d.loc?.join('.') || ''})` : JSON.stringify(d)))
        .join(', ');
    }
    if (typeof detail === 'object') {
      return detail.msg || detail.message || JSON.stringify(detail);
    }
  }

  if (err?.response?.status) {
    return `Server responded with HTTP ${err.response.status} (${err.response.statusText || 'Error'}).`;
  }

  if (err?.message && typeof err.message === 'string') {
    return err.message;
  }

  try {
    return JSON.stringify(err);
  } catch {
    return fallback;
  }
}

export async function fetchSchema(refresh: boolean = false): Promise<SchemaInfo> {
  try {
    const timestamp = Date.now();
    const res = await client.get<SchemaInfo>(`/api/schema?refresh=${refresh}&_t=${timestamp}`, {
      headers: {
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        Pragma: 'no-cache',
      },
    });
    if (res.data && typeof res.data === 'object' && res.data.tables) {
      return res.data;
    }
    return {
      status: 'ok',
      tables: {},
      table_names: [],
      relationships: [],
      uploaded_files: [],
      indexed_documents: [],
    };
  } catch (err) {
    console.warn('API fetchSchema failed, using fallback empty schema:', err);
    return {
      status: 'offline',
      tables: {},
      table_names: [],
      relationships: [],
      uploaded_files: [],
      indexed_documents: [],
    };
  }
}

export async function executeQuery(
  question: string,
  provider?: string,
  apiKey?: string
): Promise<QueryResult> {
  const res = await client.post<QueryResult>('/api/query', {
    question,
    query: question,
    provider: provider || undefined,
    api_key: apiKey || undefined,
  });
  return res.data;
}

export async function executeManualSql(sql: string): Promise<QueryResult> {
  const res = await client.post<QueryResult>('/api/execute-sql', {
    sql,
    query: sql,
  });
  return res.data;
}

export async function uploadDatasetCsv(file: File, tableName?: string) {
  const formData = new FormData();
  formData.append('file', file);
  if (tableName) {
    formData.append('table_name', tableName);
  }
  
  // Try /api/upload first (universal), fallback to /api/upload-csv
  try {
    const res = await client.post('/api/upload', formData);
    return res.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const resFallback = await client.post('/api/upload-csv', formData);
      return resFallback.data;
    }
    throw err;
  }
}

export async function fetchQueryHistory(limit: number = 50): Promise<HistoryItem[]> {
  try {
    const res = await client.get<{ status: string; history: HistoryItem[] }>(`/api/history?limit=${limit}`);
    return Array.isArray(res.data?.history) ? res.data.history : [];
  } catch (err) {
    console.warn('Failed to fetch query history:', err);
    return [];
  }
}

export async function clearQueryHistory(): Promise<void> {
  try {
    await client.delete('/api/history');
  } catch (err) {
    console.warn('Failed to clear history:', err);
  }
}

export async function uploadRagDocument(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  // Try /api/rag/upload first, fallback to /api/upload
  try {
    const res = await client.post('/api/rag/upload', formData);
    return res.data;
  } catch (err: any) {
    if (err?.response?.status === 404) {
      const resFallback = await client.post('/api/upload', formData);
      return resFallback.data;
    }
    throw err;
  }
}

export async function queryRag(query: string): Promise<RagResult> {
  const res = await client.post<RagResult>('/api/rag/query', {
    query,
    question: query,
  });
  return res.data;
}

export async function seedDatabase(force: boolean = true) {
  const res = await client.post(`/api/db/seed?force=${force}`);
  return res.data;
}
