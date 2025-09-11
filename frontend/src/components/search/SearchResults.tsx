'use client';

import { useSearch } from '@/hooks/useSearch';
import { ThinkingProcess } from './ThinkingProcess';
import { FinalAnswer } from './FinalAnswer';
import { AlertCircle, CheckCircle, Wifi, WifiOff } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

export function SearchResults() {
  const { currentSearch, isConnected, error } = useSearch();

  if (!currentSearch) {
    return null;
  }

  // Thinking when any non-finalization step is running
  const isThinking = currentSearch.status === 'thinking' ||
    currentSearch.steps.some(s => s.status === 'running' && s.type !== 'solve');
  
  const hasError = currentSearch.status === 'error' || !!error;
  
  // Enhanced completion detection: prioritize final answer presence
  const isCompleted = Boolean(
    currentSearch.status === 'completed' ||
    (currentSearch.finalAnswer && currentSearch.finalAnswer.trim().length > 0)
  );

  return (
    <div className="w-full space-y-6 animate-fade-in">
      {/* Current Query Display with Enhanced Loading States */}
      {currentSearch && (
        <Card className={`w-full max-w-4xl mx-auto transition-all duration-300 ${
          isThinking 
            ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200 ring-2 ring-blue-100' 
            : hasError 
              ? 'bg-gradient-to-r from-red-50 to-pink-50 border-red-200'
              : 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-200'
        }`}>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <div className={`flex items-center justify-center w-8 h-8 rounded-full flex-shrink-0 ${
                isThinking 
                  ? 'bg-blue-100 text-blue-600' 
                  : hasError
                    ? 'bg-red-100 text-red-600'
                    : 'bg-green-100 text-green-600'
              }`}>
                <span className="text-sm font-medium">Q</span>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className={`font-medium mb-1 ${
                  isThinking 
                    ? 'text-blue-900' 
                    : hasError
                      ? 'text-red-900'
                      : 'text-green-900'
                }`}>Your Question</h3>
                <p className={`leading-relaxed ${
                  isThinking 
                    ? 'text-blue-800' 
                    : hasError
                      ? 'text-red-800'
                      : 'text-green-800'
                }`}>
                  "{currentSearch.query}"
                </p>
                {isThinking && (
                  <div className="flex items-center gap-2 mt-3 text-sm text-blue-600 bg-blue-100/50 rounded-md px-3 py-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="font-medium">Researching your question...</span>
                  </div>
                )}
                {isCompleted && (
                  <div className="flex items-center gap-2 mt-3 text-sm text-green-600 bg-green-100/50 rounded-md px-3 py-2">
                    <CheckCircle className="w-4 h-4" />
                    <span className="font-medium">Research completed!</span>
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

      {/* Enhanced Error Display */}
      {hasError && (
        <Card className="w-full max-w-4xl mx-auto border-red-200 bg-red-50 shadow-md animate-shake">
          <CardContent className="p-5">
            <div className="flex items-start gap-4 text-red-700">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-red-100 flex-shrink-0">
                <AlertCircle className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-base text-red-800 mb-1">Search Failed</h4>
                <p className="text-sm mb-3 text-red-700">
                  {currentSearch.error || error || 'An unexpected error occurred while processing your request.'}
                </p>
                <div className="text-xs text-red-600 bg-red-100/50 rounded p-2">
                  <strong>What you can try:</strong>
                  <ul className="list-disc list-inside mt-1 space-y-1">
                    <li>Check your internet connection</li>
                    <li>Try rephrasing your question</li>
                    <li>Wait a moment and try again</li>
                  </ul>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Thinking process */}
      <ThinkingProcess
        steps={currentSearch.steps}
        isThinking={isThinking}
        isCompleted={isCompleted}
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