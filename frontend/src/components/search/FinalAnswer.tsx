'use client';

import { useState } from 'react';
import { Copy, Check, Share2, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import { SearchResult } from '@/types/search';
import { formatDuration } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface FinalAnswerProps {
  searchResult: SearchResult;
  className?: string;
}

export function FinalAnswer({ searchResult, className }: FinalAnswerProps) {
  const [copied, setCopied] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (!searchResult.finalAnswer) {
    return null;
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(searchResult.finalAnswer!);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'OpenProbe Result',
          text: `Q: ${searchResult.query}\n\nA: ${searchResult.finalAnswer}`,
        });
      } catch (error) {
        console.error('Failed to share:', error);
      }
    } else {
      // Fallback: copy to clipboard
      handleCopy();
    }
  };

  const duration = searchResult.endTime 
    ? formatDuration(searchResult.startTime, searchResult.endTime)
    : formatDuration(searchResult.startTime);

  const completedSteps = searchResult.steps.filter(step => step.status === 'completed').length;

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-xl mb-2">Answer</CardTitle>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>✅ Completed in {duration}</span>
              <span>🔄 {completedSteps} steps</span>
              <span>🕒 {new Intl.DateTimeFormat('en-US', {
                hour: '2-digit',
                minute: '2-digit',
              }).format(searchResult.startTime)}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2 ml-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="h-8"
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Copied!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-1" />
                  Copy
                </>
              )}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              className="h-8"
            >
              <Share2 className="h-4 w-4 mr-1" />
              Share
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div className="prose max-w-none">
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border border-blue-100">
            <div className="whitespace-pre-wrap text-gray-800 leading-relaxed">
              {searchResult.finalAnswer}
            </div>
          </div>
        </div>
        
        {/* Query reminder */}
        <div className="mt-6 pt-4 border-t border-border/50">
          <h4 className="text-sm font-medium text-muted-foreground mb-2">Original Question:</h4>
          <p className="text-sm bg-muted/30 rounded-md p-3 italic">
            "{searchResult.query}"
          </p>
        </div>
        
        {/* Comprehensive Sources Section */}
        {(searchResult.sources?.length || searchResult.steps.some(step => step.type === 'search')) && (
          <div className="mt-6 pt-4 border-t border-border/50">
            <Collapsible open={sourcesOpen} onOpenChange={setSourcesOpen}>
              <CollapsibleTrigger asChild>
                <Button 
                  variant="ghost" 
                  className="w-full justify-between p-0 h-auto hover:bg-transparent"
                >
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-muted-foreground">
                      Sources Used
                    </h4>
                    {searchResult.sources?.length && (
                      <span className="bg-blue-100 text-blue-600 text-xs px-2 py-1 rounded-full">
                        {searchResult.sources.length} sources
                      </span>
                    )}
                  </div>
                  {sourcesOpen ? (
                    <ChevronUp className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              </CollapsibleTrigger>

              <CollapsibleContent className="mt-3">
                {searchResult.sources?.length ? (
                  <ScrollArea className="h-[200px] pr-4">
                    <div className="space-y-3">
                      {searchResult.sources.map((source, index) => (
                        <div 
                          key={index}
                          className="bg-gray-50 rounded-lg p-3 border border-gray-200 hover:border-blue-300 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <a
                                href={source.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm font-medium text-blue-600 hover:text-blue-800 underline line-clamp-2"
                                title={source.title}
                              >
                                {source.title}
                              </a>
                              {source.snippet && (
                                <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                                  {source.snippet}
                                </p>
                              )}
                              <p className="text-xs text-gray-500 mt-1 truncate">
                                {new URL(source.link).hostname}
                              </p>
                            </div>
                            <ExternalLink className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                ) : (
                  <div className="text-xs text-muted-foreground flex items-center gap-1 bg-gray-50 rounded p-3">
                    <ExternalLink className="h-3 w-3" />
                    Information gathered from web search - detailed sources will appear here
                  </div>
                )}
              </CollapsibleContent>
            </Collapsible>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
