'use client';

import { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, Brain, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { StepCard } from './StepCard';
import { ThinkingStep } from '@/types/search';
import { cn } from '@/lib/utils';

interface ThinkingProcessProps {
  steps: ThinkingStep[];
  isThinking: boolean;
  query?: string;
  className?: string;
}

export function ThinkingProcess({ steps, isThinking, query, className }: ThinkingProcessProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [shouldAutoExpand, setShouldAutoExpand] = useState(true);

  // Auto-expand when thinking starts or when steps are available
  useEffect(() => {
    if ((isThinking || steps.length > 0) && shouldAutoExpand) {
      setIsOpen(true);
    }
  }, [isThinking, steps.length, shouldAutoExpand]);

  // Reset auto-expand behavior when manually toggled
  const handleToggle = () => {
    setIsOpen(!isOpen);
    setShouldAutoExpand(false);
  };

  const activeSteps = steps.filter(step => step.status !== 'pending');
  const runningSteps = activeSteps.filter(step => step.status === 'running');
  const completedSteps = activeSteps.filter(step => step.status === 'completed');
  const failedSteps = activeSteps.filter(step => step.status === 'failed');

  // Smart progress based on plan steps
  const planStep = steps.find(s => s.type === 'plan');
  const totalPlanSteps = planStep?.metadata?.planSteps?.length || 0;
  const executionSteps = steps.filter(s => s.type !== 'plan');
  const completedExecutionSteps = executionSteps.filter(s => s.status === 'completed').length;

  const getThinkingText = () => {
    if (!isThinking && steps.length === 0) return '';
    if (!isThinking) return `Completed ${completedSteps.length} steps`;
    
    // Show plan-based progress if available
    if (totalPlanSteps > 0) {
      return `${completedExecutionSteps} of ${totalPlanSteps} steps completed`;
    }
    
    if (runningSteps.length > 0) {
      return runningSteps[0].title;
    }
    return 'Starting to think...';
  };

  if (!isThinking && steps.length === 0) {
    return null;
  }

  return (
    <Card className={cn("w-full max-w-4xl mx-auto mb-3", className)}>
      <Collapsible open={isOpen} onOpenChange={handleToggle}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors py-3 px-4">
            <Button variant="ghost" className="w-full justify-between p-0 h-auto">
              <div className="flex items-center gap-2">
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10">
                  {isThinking ? (
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  ) : (
                    <Brain className="h-4 w-4 text-primary" />
                  )}
                </div>
                
                <div className="text-left">
                  <h3 className="font-medium text-sm">
                    {isThinking ? (
                      <span className="thinking-dots">Thinking</span>
                    ) : (
                      'Thinking Process'
                    )}
                    {!isThinking && completedSteps.length > 0 && (
                      <span className="text-xs text-muted-foreground ml-2">
                        ({completedSteps.length} steps)
                      </span>
                    )}
                  </h3>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                {isOpen ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </Button>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent className="pt-0 pb-3 px-4">
            {activeSteps.length > 0 ? (
              <div className="max-h-48 overflow-y-auto custom-scrollbar">
                <div className="space-y-2">
                  {activeSteps.map((step, index) => (
                    <details key={step.id} className="text-xs group">
                      <summary className={cn(
                        "flex items-center gap-2 p-2 rounded-md cursor-pointer hover:bg-muted/50 transition-colors",
                        step.status === 'running' && "bg-primary/10",
                        step.status === 'completed' && "bg-green-50 hover:bg-green-100",
                        step.status === 'failed' && "bg-red-50 hover:bg-red-100"
                      )}>
                        <div className={cn(
                          "w-2 h-2 rounded-full flex-shrink-0",
                          step.status === 'running' && "bg-primary animate-pulse",
                          step.status === 'completed' && "bg-green-500",
                          step.status === 'failed' && "bg-red-500",
                          step.status === 'pending' && "bg-gray-300"
                        )} />
                        <span className="font-medium truncate flex-1">{step.title}</span>
                        {step.status === 'running' && (
                          <Loader2 className="h-3 w-3 animate-spin flex-shrink-0" />
                        )}
                        <ChevronDown className="h-3 w-3 text-muted-foreground group-open:rotate-180 transition-transform flex-shrink-0" />
                      </summary>
                      
                      {/* Step details */}
                      <div className="mt-2 ml-4 p-3 bg-muted/30 rounded-md">
                        {/* Step content */}
                        {step.content && (
                          <div className="mb-3">
                            <p className="text-xs font-medium text-muted-foreground mb-1">Output:</p>
                            <div className="text-xs bg-background/50 rounded p-2 max-h-32 overflow-y-auto custom-scrollbar">
                              <pre className="whitespace-pre-wrap font-mono">{step.content}</pre>
                            </div>
                          </div>
                        )}
                        
                        {/* Metadata */}
                        {step.metadata && (
                          <div className="space-y-2">
                            {step.metadata.searchQuery && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground">Search Query:</p>
                                <p className="text-xs bg-blue-50 rounded p-1">{step.metadata.searchQuery}</p>
                              </div>
                            )}
                            
                            {step.metadata.codeResult && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground">Code Result:</p>
                                <pre className="text-xs bg-green-50 rounded p-2 overflow-x-auto font-mono">{step.metadata.codeResult}</pre>
                              </div>
                            )}
                            
                            {step.metadata.planSteps && step.metadata.planSteps.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground">Plan Steps:</p>
                                <ol className="text-xs bg-yellow-50 rounded p-2 space-y-1">
                                  {step.metadata.planSteps.map((planStep, idx) => (
                                    <li key={idx} className="flex gap-2">
                                      <span className="font-medium">{idx + 1}.</span>
                                      <span>{planStep}</span>
                                    </li>
                                  ))}
                                </ol>
                              </div>
                            )}
                            
                            {step.metadata.error && (
                              <div>
                                <p className="text-xs font-medium text-red-600">Error:</p>
                                <p className="text-xs bg-red-50 text-red-700 rounded p-2">{step.metadata.error}</p>
                              </div>
                            )}
                            
                            {step.metadata.sources && step.metadata.sources.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground">Sources:</p>
                                <div className="text-xs bg-purple-50 rounded p-2 space-y-1 max-h-24 overflow-y-auto">
                                  {step.metadata.sources.map((source, idx) => (
                                    <div key={idx}>
                                      {typeof source === 'string' ? (
                                        <span className="text-purple-700">{source}</span>
                                      ) : (
                                        <a 
                                          href={source.link} 
                                          target="_blank" 
                                          rel="noopener noreferrer"
                                          className="text-purple-600 hover:underline block"
                                        >
                                          {source.title}
                                        </a>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        
                        <div className="mt-2 text-xs text-muted-foreground">
                          {step.timestamp.toLocaleTimeString()}
                        </div>
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <Brain className="h-6 w-6 mx-auto mb-2 opacity-50" />
                <p className="text-xs">Initializing...</p>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
