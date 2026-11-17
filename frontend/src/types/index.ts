export interface ColumnInfo {
  name: string;
  type: string;
  primary_key: boolean;
  nullable: boolean;
}

export interface TableInfo {
  name: string;
  columns: ColumnInfo[];
  row_count: number;
  sample_rows: Record<string, any>[];
  foreign_keys: any[];
}

export interface SchemaInfo {
  status: string;
  tables: Record<string, TableInfo>;
  table_names: string[];
  relationships: Array<{
    from_table: string;
    from_column: string;
    to_table: string;
    to_column: string;
  }>;
}

export interface ChartConfig {
  recommended: boolean;
  chart_type: 'bar' | 'line' | 'pie';
  x_axis_key: string;
  y_axis_keys: string[];
  title: string;
}

export interface QueryResult {
  status: 'success' | 'error' | 'blocked' | 'execution_error';
  question: string;
  sql: string;
  columns?: string[];
  rows?: Record<string, any>[];
  row_count?: number;
  execution_time_ms?: number;
  database_time_ms?: number;
  answer?: string;
  chart?: ChartConfig | null;
  provider?: string;
  error?: string;
}

export interface HistoryItem {
  id: number;
  question: string;
  sql: string;
  status: string;
  duration_ms: number;
  row_count: number;
  provider: string;
  error?: string;
  timestamp: string;
}

export interface RagCitation {
  source: string;
  chunk_id: string;
  relevance_score: number;
  excerpt: string;
}

export interface RagResult {
  status: string;
  query: string;
  answer: string;
  citations: RagCitation[];
  retrieved_count: number;
}
