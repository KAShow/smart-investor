import { CheckCircle2, Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';
import { ANALYSIS_STAGES, STAGE_GROUPS } from '@/lib/smart-investor/constants';
import type { StreamStage } from '@/lib/smart-investor/types';

type Props = {
  stages: Partial<Record<StreamStage, any>>;
  currentStage: StreamStage | null;
  isStreaming: boolean;
};

export function AnalysisStream({ stages, currentStage, isStreaming }: Props) {
  return (
    <div className="space-y-6">
      {STAGE_GROUPS.map(group => {
        const groupStages = ANALYSIS_STAGES.filter(s => s.group === group.id);
        return (
          <div key={group.id}>
            <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
              {group.title}
            </h3>
            <div className="space-y-2">
              {groupStages.map(stage => {
                const completed = stage.key in stages;
                const inFlight = isStreaming && currentStage === stage.key && !completed;
                return (
                  <div
                    key={stage.key}
                    className={cn(
                      'flex items-center gap-3 rounded-lg border p-3 transition-colors',
                      completed && 'border-primary/50 bg-primary/5',
                      inFlight && 'border-amber-500/50 bg-amber-50 dark:bg-amber-950/20',
                    )}
                  >
                    {completed ? (
                      <CheckCircle2 className="h-5 w-5 shrink-0 text-primary" />
                    ) : inFlight ? (
                      <Loader2 className="h-5 w-5 shrink-0 animate-spin text-amber-500" />
                    ) : (
                      <div className="h-5 w-5 shrink-0 rounded-full border-2 border-muted" />
                    )}
                    <span className="flex-1 text-sm">{stage.label}</span>
                    {completed && stage.group === 'data' && stages[stage.key]?.count != null && (
                      <span className="text-xs text-muted-foreground">
                        {stages[stage.key].count} عنصر
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
