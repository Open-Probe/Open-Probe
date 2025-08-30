'use client';

import { useState } from 'react';
import { Message } from '@/types/search';
import { User, Bot, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ThinkingProcess } from '@/components/search/ThinkingProcess';
import { cn } from '@/lib/utils';

// Simple markdown renderer for basic formatting
const renderMarkdown = (text: string) => {
  // Handle bold text
  let rendered = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Handle italic text
  rendered = rendered.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Handle code blocks
  rendered = rendered.replace(/`([^`]+)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>');
  
  return rendered;
};

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.type === 'user';
  const isAssistant = message.type === 'assistant';
  const searchResult = message.searchResult;

  const handleCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const formatTime = (timestamp: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(timestamp);
  };

  if (isUser) {
    return (
      <div className="flex items-start gap-3 max-w-[80%] ml-auto message-bubble user-message">
        <div className="flex-1 min-w-0">
          <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-md px-4 py-3 shadow-sm">
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </div>
          <p className="text-xs text-muted-foreground mt-1 text-right">
            {formatTime(message.timestamp)}
          </p>
        </div>
        <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center">
          <User className="h-4 w-4 text-primary-foreground" />
        </div>
      </div>
    );
  }

  if (isAssistant) {
    const isThinking = searchResult?.status === 'thinking';
    const isCompleted = searchResult?.status === 'completed';
    const finalAnswer = searchResult?.finalAnswer;
    const hasSteps = searchResult && searchResult.steps.length > 0;

    return (
      <div className="flex items-start gap-3 max-w-[95%] message-bubble assistant-message">
        <div className="flex-shrink-0 w-8 h-8 bg-muted rounded-full flex items-center justify-center">
          <Bot className="h-4 w-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="bg-muted/50 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm">
            {/* Thinking Process - Make it prominent during execution */}
            {hasSteps && (
              <div className="mb-4">
                <ThinkingProcess 
                  steps={searchResult.steps} 
                  isThinking={isThinking} 
                  query={searchResult.query}
                  className="border border-border/20 shadow-sm bg-muted/20 rounded-lg"
                />
              </div>
            )}

            {/* Final Answer */}
            {isCompleted && finalAnswer && (
              <div className="space-y-4">
                <div className="prose max-w-none">
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100">
                    <div 
                      className="whitespace-pre-wrap break-words text-gray-800 leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: renderMarkdown(finalAnswer) }}
                    />
                  </div>
                </div>
                
                {/* Metadata and Sources */}
                {searchResult && (
                  <div className="space-y-3 pt-2 border-t border-border/30">
                    {/* Performance Stats */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>✅ Completed in {searchResult.endTime ? 
                          Math.round((searchResult.endTime.getTime() - searchResult.startTime.getTime()) / 1000) : '?'}s
                        </span>
                        <span>🔄 {searchResult.steps.filter(s => s.status === 'completed').length} steps</span>
                        <span>🕒 {formatTime(searchResult.endTime || searchResult.startTime)}</span>
                      </div>
                      
                      {/* Copy button - moved to top right */}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(finalAnswer)}
                        className="h-7 px-2 text-xs"
                      >
                        {copied ? (
                          <>
                            <Check className="h-3 w-3 mr-1" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="h-3 w-3 mr-1" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>

                    {/* Sources from steps */}
                    {searchResult.steps.some(step => step.metadata?.sources) && (
                      <div className="mt-3">
                        <details className="group">
                          <summary className="cursor-pointer text-xs font-medium text-muted-foreground hover:text-foreground mb-2">
                            📚 Sources Used ({searchResult.steps
                              .map(step => step.metadata?.sources || [])
                              .flat()
                              .filter(Boolean).length} sources)
                          </summary>
                          <div className="space-y-2 ml-4 max-h-40 overflow-y-auto custom-scrollbar">
                            {searchResult.steps
                              .map(step => step.metadata?.sources || [])
                              .flat()
                              .filter(Boolean)
                              .map((source, index) => (
                                <div key={index} className="text-xs bg-muted/30 rounded p-2">
                                  {typeof source === 'string' ? (
                                    <span className="text-blue-600">{source}</span>
                                  ) : (
                                    <div>
                                      <a 
                                        href={source.link} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:underline font-medium"
                                      >
                                        {source.title}
                                      </a>
                                      {source.snippet && (
                                        <p className="text-muted-foreground mt-1">{source.snippet}</p>
                                      )}
                                    </div>
                                  )}
                                </div>
                              ))}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Smart progress indicator - only show when plan exists */}
            {(() => {
              if (!isThinking || finalAnswer) return null;
              
              // Find the plan step and get total planned steps
              const planStep = searchResult.steps.find(s => s.type === 'plan');
              const totalPlanSteps = planStep?.metadata?.planSteps?.length || 0;
              
              // Only show progress if we have a plan
              if (totalPlanSteps === 0) {
                // Show current step being executed or planning
                const runningStep = searchResult.steps.find(s => s.status === 'running');
                const currentStepTitle = runningStep?.title || 'Planning...';
                
                return (
                  <div className="flex items-center gap-2 p-2 bg-muted/20 rounded-lg border border-border/30">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-sm font-medium">{currentStepTitle}</span>
                  </div>
                );
              }
              
              // Count completed execution steps (excluding the plan step itself)
              const executionSteps = searchResult.steps.filter(s => s.type !== 'plan');
              const completedExecutionSteps = executionSteps.filter(s => s.status === 'completed').length;
              const runningStep = searchResult.steps.find(s => s.status === 'running');
              
              return (
                <div className="flex items-center justify-between p-2 bg-muted/20 rounded-lg border border-border/30">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                      <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                    </div>
                    <span className="text-sm font-medium">
                      {completedExecutionSteps} of {totalPlanSteps} Done
                    </span>
                  </div>
                  <div className="text-xs text-muted-foreground max-w-xs truncate">
                    {runningStep?.title || 'Processing...'}
                  </div>
                </div>
              );
            })()}
          </div>
          
          <p className="text-xs text-muted-foreground mt-1">
            {formatTime(message.timestamp)}
            {isCompleted && searchResult?.endTime && (
              <span className="ml-2">
                • {Math.round((searchResult.endTime.getTime() - searchResult.startTime.getTime()) / 1000)}s
              </span>
            )}
          </p>
        </div>
      </div>
    );
  }

  return null;
}
