'use client';

import React, { useState, useMemo } from 'react';
import { 
  Brain, 
  Search, 
  Code, 
  CheckCircle2, 
  Clock, 
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  RefreshCw,
  Loader2,
  Target
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ThinkingStep } from '@/types/search';
import { cn } from '@/lib/utils';

interface ThinkingProcessProps {
  steps: ThinkingStep[];
  isThinking: boolean;
  isCompleted: boolean;
  query: string;
}

interface StepTypeConfig {
  icon: React.ComponentType<any>;
  label: string;
  color: string;
  description: string;
}

const STEP_CONFIGS: Record<string, StepTypeConfig> = {
  plan: { icon: Lightbulb, label: '💭 Planning', color: 'text-purple-600', description: 'Creating research strategy' },
  search: { icon: Search, label: '🔍 Searching', color: 'text-blue-600', description: 'Finding relevant information' },
  code: { icon: Code, label: '⚡ Processing', color: 'text-green-600', description: 'Analyzing and processing data' },
  llm: { icon: Brain, label: '🧠 Thinking', color: 'text-indigo-600', description: 'AI processing and analysis' },
  solve: { icon: Target, label: '🎯 Solving', color: 'text-orange-600', description: 'Generating comprehensive answer' },
  replan: { icon: RefreshCw, label: '🔄 Replanning', color: 'text-amber-600', description: 'Adjusting research strategy' }
};

function extractTotalStepsFromPlan(planContent: string): number {
  if (!planContent) return 0;
  const headerPattern = /^\s*(?:\d+\.\s*)?#E\d+\s*(?:=|\-)/gm;
  const matches = planContent.match(headerPattern);
  return matches ? matches.length : 0;
}

export function ThinkingProcess({ steps, isThinking, isCompleted, query }: ThinkingProcessProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  // detect execution step types
  const isExecutionType = (t: ThinkingStep['type']) => t === 'search' || t === 'code' || t === 'llm';

  // total planned steps (from plan metadata or parsing)
  const totalPlannedSteps = useMemo(() => {
    const planStep = steps.find(step => step.type === 'plan');
    if (planStep?.metadata?.planSteps && planStep.metadata.planSteps.length > 0) {
      return planStep.metadata.planSteps.length;
    }
    if (planStep?.content) {
      const parsed = extractTotalStepsFromPlan(planStep.content);
      if (parsed > 0) return parsed;
    }
    return steps.filter(s => isExecutionType(s.type)).length;
  }, [steps]);

  // progress stats (only execution steps)
  const progressStats = useMemo(() => {
    const completed = steps.filter(step => isExecutionType(step.type) && step.status === 'completed').length;
    const running = steps.filter(step => isExecutionType(step.type) && step.status === 'running').length;
    const failed = steps.filter(step => isExecutionType(step.type) && step.status === 'failed').length;
    const observedETotal = steps.filter(step => isExecutionType(step.type)).length;
    const total = totalPlannedSteps > 0 ? totalPlannedSteps : observedETotal;
    const percentage = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 0;
    return { total, completed, running, failed, percentage };
  }, [steps, totalPlannedSteps]);

  // count of running execution steps — used to show spinner even if header text says "In Progress"
  const executionRunningCount = useMemo(() => {
    return steps.filter(s => isExecutionType(s.type) && s.status === 'running').length;
  }, [steps]);

  // current running execution step for small badge
  const currentStep = useMemo(() => {
    if (isCompleted) return null;
    return steps.find(step => step.status === 'running' && isExecutionType(step.type)) || null;
  }, [steps, isCompleted]);

  if (!steps || steps.length === 0) return null;

  // Consider complete ONLY when:
  // - parent sets isCompleted true (final output shown), OR
  // - a 'solve' step exists and is completed.
  // <-- IMPORTANT: we intentionally do NOT treat `completed execution steps >= planned steps` as final completion.
  const consideredComplete = useMemo(() => {
    const solveCompleted = steps.some(s => s.type === 'solve' && s.status === 'completed');
    return Boolean(isCompleted || solveCompleted);
  }, [isCompleted, steps]);

  const getOverallStatus = () => {
    if (consideredComplete) return 'completed';
    // Check for running execution steps first (more reliable than parent isThinking)
    if (executionRunningCount > 0) return 'thinking';
    if (isThinking) return 'thinking';
    if (progressStats.failed > 0 && executionRunningCount === 0) return 'error';
    return 'in-progress';
  };

  const overallStatus = getOverallStatus();
  const displayedPercentage = consideredComplete ? 100 : progressStats.percentage;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-2 animate-fade-in">
      <Card className={cn(
        "transition-all duration-300 border-l-4",
        overallStatus === 'thinking' && "border-l-blue-500 bg-blue-50/30 ring-1 ring-blue-200",
        overallStatus === 'completed' && "border-l-green-500 bg-green-50/30",
        overallStatus === 'error' && "border-l-red-500 bg-red-50/30",
        overallStatus === 'in-progress' && "border-l-blue-500 bg-blue-50/30"
      )}>
        <CardContent className="p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Left icon: if any execution step is running, show spinner here for immediate cue */}
              <div className={cn(
                "flex items-center justify-center w-8 h-8 rounded-full",
                overallStatus === 'thinking' && "bg-blue-100 text-blue-600",
                overallStatus === 'completed' && "bg-green-100 text-green-600",
                overallStatus === 'error' && "bg-red-100 text-red-600",
                overallStatus === 'in-progress' && "bg-blue-100 text-blue-600"
              )}>
                {executionRunningCount > 0 ? (
                  // show spinner while any execution step runs
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  // fallback icon based on overall status
                  overallStatus === 'completed' ? <CheckCircle2 className="w-4 h-4" />
                  : overallStatus === 'error' ? <AlertCircle className="w-4 h-4" />
                  : <Brain className="w-4 h-4" />
                )}
              </div>

              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                   {/* Header text */}
                   <h4 className="text-sm font-medium flex items-center gap-2">
                     {consideredComplete && '✅ Research Complete'}
                     {!consideredComplete && executionRunningCount > 0 && '🔬 Researching'}
                     {!consideredComplete && executionRunningCount === 0 && '🔬 In Progress'}
                     {!consideredComplete && overallStatus === 'error' && '⚠️ Research Issues'}
                   </h4>

                  {/* small spinner + "Thinking..." text when execution steps are running */}
                  {executionRunningCount > 0 && !consideredComplete && (
                    <div className="flex items-center gap-2 ml-2">
                      <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                      <span className="text-xs text-gray-600">Thinking…</span>
                    </div>
                  )}

                  {/* current step badge */}
                  {currentStep && !consideredComplete && (
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                      currentStep.type === 'plan' && "bg-purple-100 text-purple-700",
                      currentStep.type === 'search' && "bg-blue-100 text-blue-700", 
                      currentStep.type === 'code' && "bg-green-100 text-green-700",
                      currentStep.type === 'llm' && "bg-indigo-100 text-indigo-700",
                      currentStep.type === 'solve' && "bg-orange-100 text-orange-700",
                      currentStep.type === 'replan' && "bg-amber-100 text-amber-700"
                    )}>
                      {STEP_CONFIGS[currentStep.type]?.label || currentStep.type}
                    </span>
                  )}
                </div>

                {/* Progress bar */}
                <div className="flex items-center gap-3">
                  <div className="flex-1 min-w-[200px] bg-gray-200 rounded-full h-3">
                    <div 
                      className={cn(
                        "h-full transition-all duration-500 ease-out rounded-full",
                        overallStatus === 'thinking' && "bg-blue-500",
                        overallStatus === 'completed' && "bg-green-500",
                        overallStatus === 'error' && "bg-red-500",
                        overallStatus === 'in-progress' && "bg-blue-500"
                      )}
                      style={{ width: `${displayedPercentage}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-600 min-w-[3rem]">
                    {consideredComplete
                      ? `${Math.max(progressStats.total, progressStats.completed)}/${Math.max(progressStats.total, progressStats.completed)}`
                      : `${progressStats.completed}/${Math.max(1, progressStats.total)}`}
                  </span>
                </div>
              </div>
            </div>

            <Button variant="ghost" size="sm" onClick={() => setIsExpanded(!isExpanded)} className="h-6 w-6 p-0">
              {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isExpanded && (
        <div className="space-y-2 animate-slide-down">
          {steps.map((step) => {
            const config = STEP_CONFIGS[step.type];
            const stepExpanded = expandedSteps[step.id] || false;
            const toggleStepExpanded = () => setExpandedSteps(prev => ({ ...prev, [step.id]: !prev[step.id] }));

            return (
              <Card key={step.id} className={cn(
                "border-l-2 transition-all duration-200",
                step.status === 'running' && "border-l-blue-400 bg-blue-50/20",
                step.status === 'completed' && "border-l-green-400 bg-green-50/20",
                step.status === 'failed' && "border-l-red-50/20",
                step.status === 'pending' && "border-l-gray-300 bg-gray-50/20"
              )}>
                <CardContent className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <div className={cn(
                        "flex items-center justify-center w-6 h-6 rounded-full text-xs",
                        step.status === 'running' && "bg-blue-100 text-blue-600",
                        step.status === 'completed' && "bg-green-100 text-green-600",
                        step.status === 'failed' && "bg-red-100 text-red-600",
                        step.status === 'pending' && "bg-gray-100 text-gray-600"
                      )}>
                        {step.status === 'running' && <Loader2 className="w-3 h-3 animate-spin" />}
                        {step.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                        {step.status === 'failed' && <AlertCircle className="w-3 h-3" />}
                        {step.status === 'pending' && <Clock className="w-3 h-3" />}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium truncate">{step.title}</span>
                          <span className={cn(
                            "text-[10px] px-1.5 py-0.5 rounded-full font-medium border",
                            step.type === 'plan' && "bg-purple-50 text-purple-700 border-purple-200",
                            step.type === 'search' && "bg-blue-50 text-blue-700 border-blue-200",
                            step.type === 'code' && "bg-green-50 text-green-700 border-green-200",
                            step.type === 'llm' && "bg-indigo-50 text-indigo-700 border-indigo-200",
                            step.type === 'solve' && "bg-orange-50 text-orange-700 border-orange-200",
                            step.type === 'replan' && "bg-amber-50 text-amber-700 border-amber-200"
                          )}>
                            {config?.label}
                          </span>
                        </div>
                      </div>
                    </div>

                    {(step.content || step.metadata) && (
                      <Button variant="ghost" size="sm" onClick={toggleStepExpanded} className="h-6 w-6 p-0">
                        {stepExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      </Button>
                    )}
                  </div>

                  {stepExpanded && (step.content || step.metadata) && (
                    <div className="mt-3 pt-3 border-t border-gray-100 text-[11px] space-y-2">
                      {step.content && (
                        <div className="bg-gray-50 rounded p-2">
                          <div className="font-medium text-gray-600 mb-2 text-[11px]">Details:</div>
                          <div className="whitespace-pre-wrap text-gray-700 text-[11px] leading-snug max-h-96 overflow-y-auto">
                            {step.content}
                          </div>
                        </div>
                      )}

                      {step.metadata?.searchQuery && (
                        <div className="bg-blue-50 rounded p-2">
                          <div className="font-medium text-blue-700 mb-2 text-[11px]">Search Query:</div>
                          <div className="text-blue-600 text-[11px]">{step.metadata.searchQuery}</div>
                        </div>
                      )}

                      {step.metadata?.codeResult && (
                        <div className="bg-green-50 rounded p-2">
                          <div className="font-medium text-green-700 mb-2 text-[11px]">Code Result:</div>
                          <pre className="text-green-600 text-[11px] whitespace-pre-wrap max-h-64 overflow-y-auto bg-white rounded p-1 border border-green-200">
                            {step.metadata.codeResult}
                          </pre>
                        </div>
                      )}

                      {step.metadata?.llmResult && (
                        <div className="bg-indigo-50 rounded p-2">
                          <div className="font-medium text-indigo-700 mb-2 text-[11px]">LLM Result:</div>
                          <pre className="text-indigo-600 text-[11px] whitespace-pre-wrap max-h-64 overflow-y-auto bg-white rounded p-1 border border-indigo-200">
                            {step.metadata.llmResult}
                          </pre>
                        </div>
                      )}

                      {step.metadata?.sources && step.metadata.sources.length > 0 && (
                        <div className="bg-orange-50 rounded p-2">
                          <div className="font-medium text-orange-700 mb-2 text-[11px]">Sources ({step.metadata.sources.length}):</div>
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {step.metadata.sources.map((source, idx) => (
                              <div key={idx} className="text-[11px]">
                                {typeof source === 'object' && 'link' in source && source.link ? (
                                  <a href={source.link} target="_blank" rel="noopener noreferrer" className="text-orange-600 hover:text-orange-800 underline break-all" title={source.title || source.link}>
                                    {source.title || source.link}
                                  </a>
                                ) : typeof source === 'string' && source.startsWith('http') ? (
                                  <a href={source} target="_blank" rel="noopener noreferrer" className="text-orange-600 hover:text-orange-800 underline break-all">{source}</a>
                                ) : (
                                  <span className="text-orange-600">{typeof source === 'string' ? source : JSON.stringify(source)}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {step.metadata?.error && (
                        <div className="bg-red-50 rounded p-2">
                          <div className="font-medium text-red-700 mb-2 text-[11px]">Error:</div>
                          <div className="text-red-600 text-[11px] whitespace-pre-wrap">{step.metadata.error}</div>
                        </div>
                      )}

                      {step.metadata?.planSteps && step.metadata.planSteps.length > 0 && (
                        <div className="bg-purple-50 rounded p-2">
                          <div className="font-medium text-purple-700 mb-2 text-[11px]">Plan ({step.metadata.planSteps.length} steps):</div>
                          <div className="space-y-1 max-h-64 overflow-y-auto">
                            {step.metadata.planSteps.map((planStep, idx) => (
                              <div key={idx} className="text-purple-600 text-[11px]">• {planStep}</div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
