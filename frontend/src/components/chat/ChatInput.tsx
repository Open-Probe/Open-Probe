'use client';

import { useState } from 'react';
import { useSearch } from '@/hooks/useSearch';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send, Square } from 'lucide-react';
import { apiClient } from '@/lib/api';

interface ChatInputProps {
  disabled?: boolean;
}

export function ChatInput({ disabled = false }: ChatInputProps) {
  const [query, setQuery] = useState('');
  const { startSearch, cancelSearch, currentSearch } = useSearch();
  const { ensureConnection } = useWebSocket();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isSearching = currentSearch?.status === 'thinking';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || disabled || isSearching) return;

    setIsSubmitting(true);
    try {
      // Ensure WebSocket connection before starting search
      await ensureConnection();
      
      // Start the search in the store first (this will add messages to chat)
      startSearch(query.trim());
      
      // Then make the API call to initiate the search
      await apiClient.startSearch(query.trim());
      
      // Clear the input after successful submission
      setQuery('');
    } catch (error) {
      console.error('Failed to start search:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!currentSearch || !isSearching) return;

    try {
      await apiClient.cancelSearch(currentSearch.id);
      cancelSearch();
    } catch (error) {
      console.error('Failed to cancel search:', error);
      cancelSearch(); // Still update frontend state
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full">
      <div className="flex items-center gap-2 w-full">
        <div className="relative flex-1 min-w-0">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask me anything..."
            className="w-full h-12 pr-4 text-base border-2 focus:border-primary transition-colors rounded-xl resize-none"
            disabled={disabled || isSubmitting}
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
          />
        </div>
        
        {isSearching ? (
          <Button
            type="button"
            variant="destructive"
            size="sm"
            onClick={handleCancel}
            className="h-12 px-4 rounded-xl flex-shrink-0"
            title="Stop generation"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            type="submit"
            disabled={!query.trim() || disabled || isSubmitting}
            size="sm"
            className="h-12 px-4 rounded-xl flex-shrink-0"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </form>
  );
}
