// أنواع TypeScript مطابقة لاستجابات Flask API

export type Sector = {
  value: string;
  name_ar: string;
  icon: string;
};

export type AnalysisInput = {
  sector: string;
  budget?: string;
  notes?: string;
  requester_name?: string;
  requester_email?: string;
  requester_company?: string;
};

export type AgentResult = {
  title?: string;
  summary?: string;
  details?: string[];
  score?: number;
  recommendation?: string;
};

export type FinalVerdict = {
  summary?: string;
  consensus?: string[];
  conflicts?: string[];
  verdict?: string;
  overall_score?: number;
  score_justification?: string;
  recommended_model?: string;
  model_justification?: string;
  advice?: string[];
};

export type SwotAnalysis = {
  strengths?: Array<string | { point: string }>;
  weaknesses?: Array<string | { point: string }>;
  opportunities?: Array<string | { point: string }>;
  threats?: Array<string | { point: string }>;
};

export type ActionPlan = {
  executive_summary?: string;
  total_budget?: string;
  phases?: Array<{ name: string; duration?: string; tasks?: string[] }>;
  key_metrics?: string[];
  critical_success_factors?: string[];
  risk_mitigation?: string[];
};

export type StreamStage =
  | 'data_sources_used'
  | 'competitors_found'
  | 'market_analysis'
  | 'financial_analysis'
  | 'competitive_analysis'
  | 'legal_analysis'
  | 'technical_analysis'
  | 'brokerage_models_analysis'
  | 'synthesizing'
  | 'final_verdict'
  | 'generating_extras'
  | 'swot_analysis'
  | 'action_plan'
  | 'done'
  | 'error';

export type StreamEvent = {
  event: StreamStage;
  data: any;
};

export type DoneEvent = {
  status: 'completed';
  analysis_id: number;
  share_token: string;
  report_number: string;
  valid_until: string;
};

export type SavedAnalysis = {
  id: number;
  idea: string;
  sector: string;
  created_at: string;
  report_number: string | null;
  share_token: string | null;
  valid_until: string | null;
};

export type FullAnalysis = SavedAnalysis & {
  market_analysis: string;
  financial_analysis: string;
  competitive_analysis: string;
  legal_analysis: string;
  technical_analysis: string;
  brokerage_models_analysis: string;
  swot_analysis: string;
  action_plan: string;
  final_verdict: string;
};
