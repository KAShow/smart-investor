import { useCallback, useRef, useState } from 'react';

import { smartInvestorApi, ApiError } from './api';
import type { AnalysisInput, DoneEvent, StreamStage } from './types';

type StageData = Record<string, any>;

type StreamState = {
  isStreaming: boolean;
  stages: Partial<Record<StreamStage, StageData>>;
  currentStage: StreamStage | null;
  done: DoneEvent | null;
  error: string | null;
};

const initial: StreamState = {
  isStreaming: false,
  stages: {},
  currentStage: null,
  done: null,
  error: null,
};

function parseSseChunk(chunk: string): { event: string; data: any } | null {
  const lines = chunk.split('\n');
  let eventName = 'message';
  let dataLine = '';
  for (const line of lines) {
    if (line.startsWith(':')) continue; // heartbeat / comment
    if (line.startsWith('event:')) eventName = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLine += line.slice(5).trim();
  }
  if (!dataLine) return null;
  try {
    return { event: eventName, data: JSON.parse(dataLine) };
  } catch {
    return { event: eventName, data: dataLine };
  }
}

/**
 * Hook to start a multi-agent analysis and consume the SSE stream.
 *
 * EventSource cannot send `Authorization` headers, so we use
 * fetch + ReadableStream — supported in all evergreen browsers.
 */
export function useAnalysisStream() {
  const [state, setState] = useState<StreamState>(initial);
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (input: AnalysisInput) => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setState({ ...initial, isStreaming: true });

    try {
      const response = await smartInvestorApi.startAnalysis(input);
      if (!response.ok) {
        let msg = 'تعذّر بدء التحليل';
        try {
          const body = await response.json();
          msg = body?.message || body?.error || msg;
        } catch {
          /* ignore */
        }
        throw new ApiError(msg, response.status);
      }
      if (!response.body) throw new ApiError('لا يدعم المتصفح streaming', 0);

      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        const parts = buffer.split('\n\n');
        buffer = parts.pop() ?? '';
        for (const raw of parts) {
          if (!raw.trim()) continue;
          const parsed = parseSseChunk(raw);
          if (!parsed) continue;

          if (parsed.event === 'done') {
            setState(s => ({ ...s, done: parsed.data, isStreaming: false }));
            return parsed.data as DoneEvent;
          }
          if (parsed.event === 'error') {
            const errMsg = parsed.data?.error || parsed.data?.message || 'حدث خطأ';
            setState(s => ({ ...s, error: errMsg, isStreaming: false }));
            return null;
          }
          setState(s => ({
            ...s,
            currentStage: parsed.event as StreamStage,
            stages: { ...s.stages, [parsed.event]: parsed.data },
          }));
        }
      }
      setState(s => ({ ...s, isStreaming: false }));
      return null;
    } catch (e) {
      if ((e as DOMException).name === 'AbortError') return null;
      setState(s => ({
        ...s,
        isStreaming: false,
        error: e instanceof Error ? e.message : 'خطأ غير معروف',
      }));
      return null;
    }
  }, []);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setState(s => ({ ...s, isStreaming: false }));
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(initial);
  }, []);

  return { ...state, start, cancel, reset };
}
