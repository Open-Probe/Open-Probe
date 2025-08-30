'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Clock, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ThinkingStep } from '@/types/search';
import { getStepIcon, getStepColor, formatTimestamp } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface StepCardProps {
  step: ThinkingStep;
  isLast?: boolean;
  isActive?: boolean;
}

export function StepCard({ step, isLast = false, isActive = false }: StepCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const getStatusIcon = () => {
    switch (step.status) {
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'pending':
        return <Clock className="h-4 w-4 text-gray-400" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusText = () => {
    switch (step.status) {
      case 'running':
        return 'Running...';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'pending':
        return 'Pending';
      default:
        return 'Unknown';
    }
  };

  const hasContent = step.content && step.content.trim().length > 0;
  const hasMetadata = step.metadata && Object.keys(step.metadata).length > 0;

  return (
    <Card className={cn(
      "transition-all duration-200 border-l-4",
      step.status === 'running' && "border-l-blue-500 bg-blue-50/50 ring-2 ring-blue-200",
      step.status === 'completed' && "border-l-green-500 bg-green-50/50",
      step.status === 'failed' && "border-l-red-500 bg-red-50/50",
      step.status === 'pending' && "border-l-gray-300 bg-gray-50/50",
      isActive && "shadow-md scale-[1.02]",
      isLast && step.status === 'running' && "animate-pulse-thinking"
    )}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn(
              "flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium",
              getStepColor(step.type)
            )}>
              {getStepIcon(step.type)}
            </div>
            
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <h4 className="font-medium text-sm truncate">{step.title}</h4>
                {getStatusIcon()}
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="capitalize">{step.type}</span>
                <span>•</span>
                <span>{getStatusText()}</span>
                <span>•</span>
                <span>{formatTimestamp(step.timestamp)}</span>
              </div>
            </div>
          </div>

          {(hasContent || hasMetadata) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 w-8 p-0"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>

        {/* Expandable content */}
        {isExpanded && (hasContent || hasMetadata) && (
          <div className="mt-4 pt-4 border-t border-border/50 animate-slide-down">
            {hasContent && (
              <div className="mb-3">
                <h5 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                  Details
                </h5>
                <div className="text-sm bg-muted/50 rounded-md p-3 whitespace-pre-wrap">
                  {step.content}
                </div>
              </div>
            )}
            
            {hasMetadata && (
              <div>
                <h5 className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                  Metadata
                </h5>
                <div className="space-y-2">
                  {step.metadata?.searchQuery && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Search Query:</span>
                      <p className="text-sm bg-blue-50 rounded px-2 py-1 mt-1">{step.metadata.searchQuery}</p>
                    </div>
                  )}
                  {step.metadata?.codeResult && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Code Result:</span>
                      <pre className="text-sm bg-green-50 rounded px-2 py-1 mt-1 overflow-auto font-mono">
                        {step.metadata.codeResult}
                      </pre>
                    </div>
                  )}
                  {step.metadata?.planSteps && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Plan Steps:</span>
                      <ul className="text-sm bg-purple-50 rounded px-2 py-1 mt-1 list-disc list-inside">
                        {step.metadata.planSteps.map((planStep, index) => (
                          <li key={index}>{planStep}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {step.metadata?.sources && (
                    <div>
                      <span className="text-xs font-medium text-muted-foreground">Sources:</span>
                      <ul className="text-sm bg-orange-50 rounded px-2 py-1 mt-1 space-y-1">
                        {step.metadata.sources.map((source, index) => (
                          <li key={index} className="break-all">
                            {typeof source === 'object' && 'link' in source && source.link ? (
                              <a 
                                href={source.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 underline transition-colors"
                                title={source.title || source.link}
                              >
                                {source.title || source.link}
                              </a>
                            ) : typeof source === 'string' && source.startsWith('http') ? (
                              <a 
                                href={source}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 underline transition-colors"
                              >
                                {source}
                              </a>
                            ) : (
                              <span className="text-gray-600">{typeof source === 'string' ? source : JSON.stringify(source)}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {step.metadata?.error && (
                    <div>
                      <span className="text-xs font-medium text-destructive">Error:</span>
                      <p className="text-sm bg-red-50 rounded px-2 py-1 mt-1 text-destructive">
                        {step.metadata.error}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
