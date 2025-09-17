export interface WebSocketMessage {
  type: 'step_update' | 'search_complete' | 'search_cancelled' | 'error' | 'session_reset';
  search_id?: string;
  data: any;
  timestamp: string;
}

export interface StepUpdateMessage extends WebSocketMessage {
  type: 'step_update';
  data: {
    step_id: string;
    step_type: 'plan' | 'search' | 'code' | 'solve' | 'replan';
    status: 'started' | 'running' | 'completed' | 'failed';
    title: string;
    content?: string;
    metadata?: {
      searchQuery?: string;
      codeResult?: string;
      planSteps?: string[];
      error?: string;
    };
  };
}

export interface SearchCompleteMessage extends WebSocketMessage {
  type: 'search_complete';
  data: {
    search_id: string;
    result: string;
    total_steps: number;
    duration: number;
  };
}

export interface ErrorMessage extends WebSocketMessage {
  type: 'error';
  data: {
    error: string;
    step_id?: string;
    recoverable: boolean;
  };
}

export interface SearchCancelledMessage extends WebSocketMessage {
  type: 'search_cancelled';
  data: {
    search_id: string;
    message: string;
  };
}

export interface SessionResetMessage extends WebSocketMessage {
  type: 'session_reset';
  data: {
    message: string;
  };
}
