'use client';

import { useSearch } from '@/hooks/useSearch';
import { ThinkingProcess } from './ThinkingProcess';
import { FinalAnswer } from './FinalAnswer';
import { AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export function SearchResults() {
  const { currentSearch, isConnected, error } = useSearch();

  if (!currentSearch) {
    return null;
  }

  const isThinking = currentSearch.status === 'thinking';
  const hasError = currentSearch.status === 'error' || !!error;
  const isCompleted = currentSearch.status === 'completed';

  return (
    <div className="w-full space-y-6 animate-fade-in">
      {/* Current Query Display */}
      {currentSearch && (
        <Card className="w-full max-w-4xl mx-auto bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-100">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex-shrink-0">
                <span className="text-sm font-medium">Q</span>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-blue-900 mb-1">Your Question</h3>
                <p className="text-blue-800 leading-relaxed">
                  "{currentSearch.query}"
                </p>
                {isThinking && (
                  <div className="flex items-center gap-2 mt-2 text-sm text-blue-600">
                    <div className="flex gap-1">
                      <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span>Researching your question...</span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Connection status */}
      {!isConnected && (
        <Card className="w-full max-w-4xl mx-auto border-yellow-200 bg-yellow-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-yellow-700">
              <WifiOff className="h-5 w-5" />
              <span className="text-sm font-medium">Connection lost</span>
              <span className="text-sm">- Trying to reconnect...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error display */}
      {hasError && (
        <Card className="w-full max-w-4xl mx-auto border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-start gap-3 text-red-700">
              <AlertCircle className="h-5 w-5 mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-medium text-sm">Search failed</p>
                <p className="text-sm mt-1">
                  {currentSearch.error || error || 'An unexpected error occurred'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Thinking process */}
      <ThinkingProcess
        steps={currentSearch.steps}
        isThinking={isThinking}
        query={currentSearch.query}
      />

      {/* Final answer */}
      {isCompleted && currentSearch.finalAnswer && (
        <FinalAnswer searchResult={currentSearch} />
      )}

      {/* Connection restored indicator */}
      {isConnected && currentSearch.steps.length > 0 && (
        <div className="fixed bottom-4 right-4 z-50">
          <div className="bg-green-500 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 shadow-lg animate-slide-down">
            <Wifi className="h-3 w-3" />
            Connected
          </div>
        </div>
      )}
    </div>
  );
}