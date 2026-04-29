import { supabase } from '@/integrations/supabase/client';

import { API_BASE_URL } from './constants';
import type { AnalysisInput, FullAnalysis, SavedAnalysis, Sector } from './types';

async function authHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError('يجب تسجيل الدخول', 401);
  return { Authorization: `Bearer ${token}` };
}

export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly code?: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set('Content-Type', 'application/json');
  for (const [k, v] of Object.entries(await authHeaders())) headers.set(k, v as string);

  const res = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    let body: any = null;
    try {
      body = await res.json();
    } catch {
      /* not json */
    }
    throw new ApiError(
      body?.message || body?.error || `HTTP ${res.status}`,
      res.status,
      body?.error,
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const smartInvestorApi = {
  // قائمة القطاعات (مفتوح بدون auth)
  listSectors: async (): Promise<Sector[]> => {
    const res = await fetch(`${API_BASE_URL}/api/sectors`);
    if (!res.ok) throw new ApiError('تعذّر تحميل القطاعات', res.status);
    return res.json();
  },

  // قائمة تحليلاتي
  listMyAnalyses: () => request<SavedAnalysis[]>('/api/analyses'),

  // تحليل واحد
  getAnalysis: (id: number) => request<FullAnalysis>(`/api/analyses/${id}`),

  // حذف
  deleteAnalysis: (id: number) =>
    request<{ success: boolean }>(`/api/analyses/${id}`, { method: 'DELETE' }),

  // تقييم
  rate: (id: number, rating: number, feedback?: string) =>
    request<{ success: boolean }>(`/api/analyses/${id}/rate`, {
      method: 'POST',
      body: JSON.stringify({ rating, feedback }),
    }),

  // متابعة (سؤال إضافي)
  followup: (id: number, question: string, opts?: {
    conversation_history?: { role: 'user' | 'assistant'; content: string }[];
    web_search?: boolean;
  }) =>
    request<{ answer: string; web_search_used: boolean }>(
      `/api/analyses/${id}/followup`,
      {
        method: 'POST',
        body: JSON.stringify({
          question,
          conversation_history: opts?.conversation_history || [],
          web_search: opts?.web_search || false,
        }),
      },
    ),

  // تنزيل PDF
  exportPdfUrl: (id: number) =>
    `${API_BASE_URL}/api/analyses/${id}/export-pdf`,

  // مشاركة عامة (بدون auth)
  getShared: async (token: string): Promise<FullAnalysis> => {
    const res = await fetch(`${API_BASE_URL}/api/share/${token}`);
    if (!res.ok) throw new ApiError('الرابط غير موجود أو منتهي الصلاحية', res.status);
    return res.json();
  },

  // تشغيل التحليل (يفتح SSE stream — انظر use-analysis-stream)
  startAnalysis: async (input: AnalysisInput): Promise<Response> => {
    const headers = new Headers({ 'Content-Type': 'application/json' });
    for (const [k, v] of Object.entries(await authHeaders())) headers.set(k, v as string);
    return fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers,
      body: JSON.stringify(input),
    });
  },
};
