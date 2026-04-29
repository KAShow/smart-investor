import type { StreamStage } from './types';

export const API_BASE_URL =
  import.meta.env.VITE_SMART_INVESTOR_API || 'http://localhost:5000';

// مراحل التحليل بالترتيب الذي يتوقعه المستخدم رؤيتها
export const ANALYSIS_STAGES: Array<{ key: StreamStage; label: string; group: 'data' | 'agents' | 'synthesis' | 'extras' }> = [
  { key: 'data_sources_used', label: 'جلب بيانات السوق البحريني', group: 'data' },
  { key: 'competitors_found', label: 'كشف المنافسين من السجل التجاري', group: 'data' },
  { key: 'market_analysis', label: 'تحليل الطلب والسوق', group: 'agents' },
  { key: 'financial_analysis', label: 'التحليل المالي', group: 'agents' },
  { key: 'competitive_analysis', label: 'تحليل المنافسة', group: 'agents' },
  { key: 'legal_analysis', label: 'التحليل القانوني', group: 'agents' },
  { key: 'technical_analysis', label: 'التحليل التقني', group: 'agents' },
  { key: 'brokerage_models_analysis', label: 'نماذج الوساطة', group: 'agents' },
  { key: 'final_verdict', label: 'الحكم النهائي', group: 'synthesis' },
  { key: 'swot_analysis', label: 'تحليل SWOT', group: 'extras' },
  { key: 'action_plan', label: 'خطة العمل', group: 'extras' },
];

export const AGENT_KEYS = ANALYSIS_STAGES
  .filter(s => s.group === 'agents')
  .map(s => s.key);

export const STAGE_GROUPS = [
  { id: 'data', title: 'جمع البيانات' },
  { id: 'agents', title: '٦ وكلاء يحلّلون بالتوازي' },
  { id: 'synthesis', title: 'التجميع والحكم' },
  { id: 'extras', title: 'SWOT وخطة العمل' },
] as const;
