'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useSearch } from '@/hooks/useSearch';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { Button } from '@/components/ui/button';
import { ArrowLeft, RotateCcw } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatViewProps {
  onBackToHome: () => void;
}

export function ChatView({ onBackToHome }: ChatViewProps) {
  const { messages, currentSearch, exitChatMode } = useSearch();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const isAutoScrollEnabled = useRef(true);

  // Improved auto-scroll function
  const scrollToBottom = useCallback((force = false) => {
    if (!messagesEndRef.current || !messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    
    // Auto-scroll if user is near bottom or force scroll
    if (isAutoScrollEnabled.current && (isNearBottom || force)) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ 
          behavior: 'smooth',
          block: 'end'
        });
      }, 100); // Small delay to ensure content is rendered
    }
  }, []);

  // Auto-scroll when new messages arrive or content changes
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-scroll when search status changes (thinking -> completed)
  useEffect(() => {
    if (currentSearch?.status === 'completed') {
      scrollToBottom(true); // Force scroll on completion
    }
  }, [currentSearch?.status, scrollToBottom]);

  // Check if user is scrolling manually to disable auto-scroll
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const isAtBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 50;
    
    isAutoScrollEnabled.current = isAtBottom;
  }, []);

  const handleNewChat = () => {
    exitChatMode();
    onBackToHome();
  };

  const isSearching = currentSearch?.status === 'thinking';

  return (
    <div className="flex flex-col h-screen w-full">
      {/* Chat Header - Fixed at top */}
      <div className="flex-shrink-0 flex items-center justify-between chat-header p-4 border-b border-border/50 bg-background/95 backdrop-blur-sm z-10">
        <div className="flex items-center gap-3 max-w-4xl mx-auto w-full">
          <Button
            variant="ghost"
            size="sm"
            onClick={onBackToHome}
            className="p-2 h-auto"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="font-semibold text-lg">OpenProbe Chat</h1>
            <p className="text-sm text-muted-foreground">
              AI-powered research assistant
            </p>
          </div>
          
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewChat}
            disabled={isSearching}
            className="flex items-center gap-2"
          >
            <RotateCcw className="h-4 w-4" />
            New Chat
          </Button>
        </div>
      </div>

      {/* Messages Container - Scrollable middle area */}
      <div 
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto custom-scrollbar min-h-0 chat-messages-container" 
        onScroll={handleScroll}
      >
        <div className="max-w-4xl mx-auto">
          <div className="space-y-6 message-spacing p-4 pb-32 chat-messages-container">
            {messages.map((message) => (
              <MessageBubble
                key={message.id}
                message={message}
              />
            ))}
            
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </div>

      {/* Chat Input - Fixed at bottom */}
      <div className="flex-shrink-0 border-t border-border/50 bg-background/95 backdrop-blur-sm chat-input-container">
        <div className="max-w-4xl mx-auto chat-input p-4">
          <ChatInput disabled={isSearching} />
          
          {/* Subtle footer in chat mode */}
          <div className="text-center mt-3">
            <p className="text-xs text-muted-foreground/60">
              Powered by{" "}
              <span className="font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                OpenProbe AI
              </span>
              {" "}• Built with Next.js & FastAPI
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
