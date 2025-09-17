export interface SearchRequest {
  query: string;
}

export interface SearchResponse {
  search_id: string;
  status: 'started';
}

export interface SearchStatusResponse {
  search_id: string;
  status: 'running' | 'completed' | 'failed';
  current_step: string;
}

export interface NewChatResponse {
  status: 'reset';
  message: string;
}

export interface HealthResponse {
  status: 'healthy';
  version: string;
}

export interface ApiError {
  detail: string;
  status_code: number;
}
