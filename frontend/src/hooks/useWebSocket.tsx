import { useEffect, useCallback } from 'react';
import { wsClient } from '@/lib/websocket';
import { useSearch } from './useSearch';
import { 
  WebSocketMessage, 
  StepUpdateMessage, 
  SearchCompleteMessage, 
  SearchCancelledMessage,
  ErrorMessage 
} from '@/types/websocket';
import { ThinkingStep } from '@/types/search';
import { generateId } from '@/lib/utils';

export const useWebSocket = () => {
  const { 
    setConnected, 
    updateStep, 
    setFinalAnswer, 
    setError, 
    clearSearch,
    cancelSearch,
    completeRunningSteps
  } = useSearch();

  const handleMessage = useCallback((message: WebSocketMessage) => {
    console.log('WebSocket message received:', message);

    switch (message.type) {
      case 'step_update': {
        const stepMessage = message as StepUpdateMessage;
        const step: ThinkingStep = {
          id: stepMessage.data.step_id,
          type: stepMessage.data.step_type,
          status: stepMessage.data.status === 'started' ? 'running' : 
                  stepMessage.data.status === 'completed' ? 'completed' :
                  stepMessage.data.status === 'failed' ? 'failed' : 'pending',
          title: stepMessage.data.title,
          content: stepMessage.data.content || '',
          timestamp: new Date(message.timestamp),
          metadata: stepMessage.data.metadata,
        };
        
        updateStep(step);
        break;
      }

      case 'search_complete': {
        const completeMessage = message as SearchCompleteMessage;
        // Ensure any running steps are marked completed so the UI reaches 100%
        completeRunningSteps();
        setFinalAnswer(completeMessage.data.result);
        break;
      }

      case 'search_cancelled': {
        const cancelMessage = message as SearchCancelledMessage;
        cancelSearch();
        console.log('Search was cancelled:', cancelMessage.data.message);
        break;
      }

      case 'error': {
        const errorMessage = message as ErrorMessage;
        setError(errorMessage.data.error);
        break;
      }

      case 'session_reset': {
        clearSearch();
        break;
      }

      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }, [updateStep, setFinalAnswer, setError, clearSearch, cancelSearch]);

  const connect = useCallback(async (showError = false) => {
    try {
      await wsClient.connect();
      setConnected(true);
      setError(null); // Clear any previous errors on successful connection
      wsClient.onMessage(handleMessage);
      console.log('WebSocket connected successfully');
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error);
      setConnected(false);
      
      // Only show error if explicitly requested (e.g., user initiated action)
      if (showError) {
        setError('Failed to connect to server. Please refresh the page.');
      }
    }
  }, [setConnected, setError, handleMessage]);

  const disconnect = useCallback(() => {
    wsClient.disconnect();
    setConnected(false);
  }, [setConnected]);

  const ensureConnection = useCallback(async () => {
    if (!wsClient.isConnected()) {
      await connect(true); // Show error if connection fails when user needs it
    }
  }, [connect]);

  useEffect(() => {
    // Try to connect silently on mount, don't show error immediately
    connect(false);

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected: wsClient.isConnected(),
    connect,
    disconnect,
    ensureConnection,
  };
};
