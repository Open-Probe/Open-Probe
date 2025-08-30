'use client';

import { useState, useEffect } from 'react';
import { Search, RotateCcw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useSearch } from '@/hooks/useSearch';
import { useWebSocket } from '@/hooks/useWebSocket';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SearchBoxProps {
  className?: string;
  initialQuery?: string;
}

export function SearchBox({ className, initialQuery }: SearchBoxProps) {
  const [query, setQuery] = useState(initialQuery || '');
  const { startSearch, isInChatMode } = useSearch();
  const { isConnected, ensureConnection } = useWebSocket();
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Update query when initialQuery changes
  useEffect(() => {
    if (initialQuery) {
      setQuery(initialQuery);
    }
  }, [initialQuery]);

  // Don't render if we're in chat mode (chat has its own input)
  if (isInChatMode) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      // Ensure WebSocket connection before starting search
      await ensureConnection();
      
      // Start the search in the store first (this will switch to chat mode)
      startSearch(query.trim());
      
      // Then make the API call to initiate the search
      await apiClient.startSearch(query.trim());
      
      // Clear the input after successful submission
      setQuery('');
    } catch (error) {
      console.error('Failed to start search:', error);
      // The error will be handled by the WebSocket error message or ensureConnection
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExampleClick = (example: string) => {
    setQuery(example);
  };

  return (
    <div className={cn("w-full", className)}>
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-muted-foreground h-5 w-5" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask me anything..."
              className="pl-12 pr-4 h-14 text-lg border-2 focus:border-primary transition-colors rounded-xl shadow-sm"
              disabled={isSubmitting}
              autoFocus
            />
          </div>
          
          <Button
            type="submit"
            disabled={!query.trim() || isSubmitting}
            size="lg"
            className="h-14 px-6 rounded-xl shadow-sm"
          >
            {isSubmitting ? (
              <>
                <RotateCcw className="h-5 w-5 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Search className="h-5 w-5 mr-2" />
                Search
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Connection status indicator */}
      {!isConnected && (
        <div className="mt-3 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-yellow-50 border border-yellow-200 rounded-full text-yellow-700 text-xs">
            <div className="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></div>
            Connecting...
          </div>
        </div>
      )}
    </div>
  );
}