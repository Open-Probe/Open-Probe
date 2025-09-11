export interface SourceInfo {
  title: string;
  link: string;
  snippet?: string;
}

export interface ThinkingStep {
  id: string;
  type: 'plan' | 'search' | 'code' | 'llm' | 'solve' | 'replan';
  status: 'pending' | 'running' | 'completed' | 'failed';
  title: string;
  content: string;
  timestamp: Date;
  metadata?: {
    searchQuery?: string;
    codeResult?: string;
    llmResult?: string;
    planSteps?: string[];
    sources?: (string | SourceInfo)[];
    error?: string;
  };
}

export interface SearchResult {
  id: string;
  query: string;
  status: 'idle' | 'thinking' | 'completed' | 'error';
  steps: ThinkingStep[];
  finalAnswer?: string;
  sources?: SourceInfo[];
  startTime: Date;
  endTime?: Date;
  error?: string;
}

export interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  searchResult?: SearchResult; // For assistant messages with search data
}

export interface ChatState {
  messages: Message[];
  currentSearch: SearchResult | null;
  isInChatMode: boolean;
  isConnected: boolean;
  error: string | null;
}

export interface SearchState extends ChatState {
  startSearch: (query: string) => void;
  clearSearch: () => void;
  cancelSearch: () => void;
  updateStep: (step: ThinkingStep) => void;
  completeRunningSteps: () => void;
  setFinalAnswer: (answer: string) => void;
  setError: (error: string | null) => void;
  setConnected: (connected: boolean) => void;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  clearMessages: () => void;
  enterChatMode: () => void;
  exitChatMode: () => void;
}
