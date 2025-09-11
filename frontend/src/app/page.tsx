'use client';

import { useEffect, useState } from 'react';
import { SearchBox } from '@/components/search/SearchBox';
import { ChatView } from '@/components/chat/ChatView';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useSearch } from '@/hooks/useSearch';
import { cn } from '@/lib/utils';

export default function HomePage() {
  const { isConnected } = useWebSocket();
  const { isInChatMode, exitChatMode } = useSearch();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [selectedExample, setSelectedExample] = useState<string>('');

  // Handle chat mode transitions with animation
  const handleBackToHome = () => {
    setIsTransitioning(true);
    setSelectedExample(''); // Clear any selected example
    setTimeout(() => {
      exitChatMode();
      setIsTransitioning(false);
    }, 300);
  };

  const handleExampleClick = (example: string) => {
    setSelectedExample(example);
  };

  // Trigger transition animation when entering chat mode
  useEffect(() => {
    if (isInChatMode) {
      setIsTransitioning(true);
      setTimeout(() => setIsTransitioning(false), 300);
    }
  }, [isInChatMode]);

  // If in chat mode, show chat view
  if (isInChatMode) {
    return (
      <div className={cn(
        "fixed inset-0 bg-background transition-all duration-300 ease-out",
        isTransitioning ? "scale-95 opacity-0" : "scale-100 opacity-100"
      )}>
        <ChatView onBackToHome={handleBackToHome} />
      </div>
    );
  }

  // Homepage view
  return (
    <div className={cn(
      "flex-1 flex flex-col transition-all duration-300 ease-out",
      isTransitioning ? "scale-95 opacity-0" : "scale-100 opacity-100"
    )}>
      {/* Main container with centered layout */}
      <div className="flex-1 flex flex-col justify-center items-center px-4 py-8 min-h-[calc(100vh-8rem)]">
        {/* Hero Section */}
        <div className="text-center mb-12 max-w-3xl">
          <h1 className="text-4xl md:text-6xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-4">
            OpenProbe
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground mb-2">
            AI-powered research assistant
          </p>
          <p className="text-base text-muted-foreground/80">
            Ask complex questions and watch me think through the answer step by step
          </p>
        </div>

        {/* Search interface */}
        <div className="w-full max-w-2xl">
          <SearchBox initialQuery={selectedExample} />
        </div>

        {/* Example queries */}
        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground mb-4">Try asking:</p>
          <div className="flex flex-wrap gap-2 justify-center max-w-2xl">
            {[
              "What is the population of the largest city in the country where the 2024 Olympics were held?",
              "If I multiply the number of moons of Jupiter by the year the Berlin Wall fell, what do I get?",
              "What did Russian President Vladimir Putin say about Western troops in Ukraine on Sept 5, 2025?",
              "Why did Elon Musk face criticism in September 2025 over Starlink?"
            ].map((example, index) => (
              <button
                key={index}
                onClick={() => handleExampleClick(example)}
                className="text-xs bg-muted/50 hover:bg-muted transition-colors px-3 py-2 rounded-full text-muted-foreground hover:text-foreground cursor-pointer"
              >
                "{example.length > 10 ? example: example}"
              </button>
            ))}
          </div>
        </div>

        {/* Connection status */}
        {!isConnected && (
          <div className="mt-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-yellow-50 border border-yellow-200 rounded-full text-yellow-700 text-sm">
              <div className="w-2 h-2 bg-yellow-400 rounded-full animate-pulse"></div>
              Connecting to server...
            </div>
          </div>
        )}
      </div>

      {/* Background decoration */}
      <div className="fixed inset-0 -z-10 pointer-events-none overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-50/30 via-white to-purple-50/30"></div>
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-100/20 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-100/20 rounded-full blur-3xl animate-pulse"></div>
      </div>
    </div>
  );
}