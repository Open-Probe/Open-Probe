import { create } from 'zustand';
import { SearchState, SearchResult, ThinkingStep, Message } from '@/types/search';
import { generateId } from '@/lib/utils';

export const useSearch = create<SearchState>((set, get) => ({
  messages: [],
  currentSearch: null,
  isInChatMode: false,
  isConnected: false,
  error: null,

  startSearch: (query: string) => {
    const newSearch: SearchResult = {
      id: generateId(),
      query,
      status: 'thinking',
      steps: [],
      startTime: new Date(),
    };

    // Add user message to chat
    const userMessage: Message = {
      id: generateId(),
      type: 'user',
      content: query,
      timestamp: new Date(),
    };

    // Add initial assistant message with search result
    const assistantMessage: Message = {
      id: generateId(),
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      searchResult: newSearch,
    };

    set({
      currentSearch: newSearch,
      messages: [...get().messages, userMessage, assistantMessage],
      isInChatMode: true,
      error: null,
    });
  },

  clearSearch: () => {
    set({
      currentSearch: null,
      error: null,
    });
  },

  cancelSearch: () => {
    const { currentSearch } = get();
    if (!currentSearch || currentSearch.status !== 'thinking') return;

    set({
      currentSearch: {
        ...currentSearch,
        status: 'idle',
        endTime: new Date(),
      },
      error: null,
    });
  },

  updateStep: (step: ThinkingStep) => {
    const { currentSearch, messages } = get();
    if (!currentSearch) return;

    // Don't add completely new steps if search is completed, but allow updates to existing steps
    if (currentSearch.status === 'completed' && !currentSearch.steps.some(s => s.id === step.id)) {
      return;
    }

    const updatedSearch = {
      ...currentSearch,
      steps: currentSearch.steps.some(s => s.id === step.id)
        ? currentSearch.steps.map(s => s.id === step.id ? step : s)
        : [...currentSearch.steps, step],
    };

    // Update the assistant message with the updated search result
    const updatedMessages = messages.map(msg => 
      msg.type === 'assistant' && msg.searchResult?.id === currentSearch.id
        ? { ...msg, searchResult: updatedSearch }
        : msg
    );

    set({
      currentSearch: updatedSearch,
      messages: updatedMessages,
    });
  },

  // Mark any running steps as completed (useful when we receive a final completion event)
  completeRunningSteps: () => {
    const { currentSearch, messages } = get();
    if (!currentSearch) return;

    const updatedSteps = currentSearch.steps.map((s) =>
      s.status === 'running' ? { ...s, status: 'completed' as const } : s
    );

    const updatedSearch = { ...currentSearch, steps: updatedSteps };

    const updatedMessages = messages.map((msg) =>
      msg.type === 'assistant' && msg.searchResult?.id === currentSearch.id
        ? { ...msg, searchResult: updatedSearch }
        : msg
    );

    set({ currentSearch: updatedSearch, messages: updatedMessages });
  },

  setFinalAnswer: (answer: string) => {
    const { currentSearch, messages } = get();
    if (!currentSearch) return;

    // Complete all running steps, especially solve steps that might still be running
    const completedSteps = currentSearch.steps.map(step => 
      step.status === 'running' || (step.type === 'solve' && step.status !== 'completed') 
        ? { ...step, status: 'completed' as const } 
        : step
    );

    const updatedSearch: SearchResult = {
      ...currentSearch,
      steps: completedSteps,
      status: 'completed' as const,
      finalAnswer: answer.trim(), // Trim whitespace here
      endTime: new Date(),
    };

    // Update the assistant message with the final answer
    const updatedMessages = messages.map(msg => 
      msg.type === 'assistant' && msg.searchResult?.id === currentSearch.id
        ? { ...msg, content: answer.trim(), searchResult: updatedSearch }
        : msg
    );
    
    set({
      currentSearch: updatedSearch,
      messages: updatedMessages,
    });
  },

  setError: (error: string | null) => {
    const { currentSearch } = get();
    
    set({
      error,
      currentSearch: currentSearch ? {
        ...currentSearch,
        status: 'error' as const,
        error: error || undefined,
        endTime: new Date(),
      } : null,
    });
  },

  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: generateId(),
      timestamp: new Date(),
    };

    set({
      messages: [...get().messages, newMessage],
    });
  },

  clearMessages: () => {
    set({
      messages: [],
      currentSearch: null,
      isInChatMode: false,
      error: null,
    });
  },

  enterChatMode: () => {
    set({ isInChatMode: true });
  },

  exitChatMode: () => {
    set({
      isInChatMode: false,
      messages: [],
      currentSearch: null,
      error: null,
    });
  },
}));
