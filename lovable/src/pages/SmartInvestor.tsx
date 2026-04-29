import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, RefreshCw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { useSession } from '@/hooks/use-session'; // عدّل المسار حسب مشروعك

import { AgentReport } from '@/components/smart-investor/AgentReport';
import { AnalysesList } from '@/components/smart-investor/AnalysesList';
import { AnalysisStream } from '@/components/smart-investor/AnalysisStream';
import { IdeaForm, type IdeaFormValues } from '@/components/smart-investor/IdeaForm';
import { SectorPicker } from '@/components/smart-investor/SectorPicker';
import { smartInvestorApi } from '@/lib/smart-investor/api';
import { ANALYSIS_STAGES } from '@/lib/smart-investor/constants';
import { useAnalysisStream } from '@/lib/smart-investor/use-analysis-stream';

const AGENT_LABELS: Record<string, string> = Object.fromEntries(
  ANALYSIS_STAGES.filter(s => s.group === 'agents' || s.key === 'final_verdict').map(s => [s.key, s.label]),
);

export default function SmartInvestor() {
  const session = useSession();
  const navigate = useNavigate();
  const { toast } = useToast();
  const stream = useAnalysisStream();
  const [sector, setSector] = useState<string>();
  const [refreshList, setRefreshList] = useState(0);
  const [activeTab, setActiveTab] = useState('new');

  useEffect(() => {
    if (session === null) navigate('/auth?redirect=/tools/smart-investor');
  }, [session, navigate]);

  useEffect(() => {
    if (stream.done) {
      toast({ title: 'اكتمل التحليل', description: `رقم التقرير: ${stream.done.report_number}` });
      setRefreshList(k => k + 1);
    }
  }, [stream.done, toast]);

  useEffect(() => {
    if (stream.error) {
      toast({ title: 'فشل التحليل', description: stream.error, variant: 'destructive' });
    }
  }, [stream.error, toast]);

  const handleSubmit = (values: IdeaFormValues) => {
    if (!sector) return;
    stream.start({ sector, ...values });
  };

  if (session === undefined) {
    return <div className="container py-12 text-center">جاري التحميل...</div>;
  }

  return (
    <div dir="rtl" className="container max-w-6xl space-y-8 py-8">
      <header>
        <h1 className="text-3xl font-bold">المستثمر الذكي البحريني</h1>
        <p className="mt-2 text-muted-foreground">
          دراسة جدوى احترافية لمشاريع الوساطة التجارية في البحرين، مدعومة بـ ٦ وكلاء ذكاء اصطناعي وبيانات حقيقية من المصادر الرسمية.
        </p>
      </header>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="new">تحليل جديد</TabsTrigger>
          <TabsTrigger value="history">تحليلاتي</TabsTrigger>
          {(stream.isStreaming || stream.done || Object.keys(stream.stages).length > 0) && (
            <TabsTrigger value="run">جاري التحليل</TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="new" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>١. اختر القطاع</CardTitle>
              <CardDescription>القطاع الذي ترغب بدراسة فرص الوساطة فيه.</CardDescription>
            </CardHeader>
            <CardContent>
              <SectorPicker value={sector} onChange={s => { setSector(s); }} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>٢. تفاصيل الفكرة</CardTitle>
              <CardDescription>الميزانية والملاحظات تساعد المحللين في تخصيص النتيجة.</CardDescription>
            </CardHeader>
            <CardContent>
              <IdeaForm
                sectorSelected={!!sector}
                isSubmitting={stream.isStreaming}
                onSubmit={values => {
                  handleSubmit(values);
                  setActiveTab('run');
                }}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="run" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{stream.done ? 'اكتمل التحليل' : 'جاري التحليل...'}</CardTitle>
              <CardDescription>
                {stream.done
                  ? `رقم التقرير: ${stream.done.report_number}`
                  : 'سترى المراحل تتقدم بشكل مباشر — قد تستغرق العملية حتى ٣ دقائق.'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <AnalysisStream
                stages={stream.stages}
                currentStage={stream.currentStage}
                isStreaming={stream.isStreaming}
              />
            </CardContent>
          </Card>

          {stream.done && (
            <div className="flex flex-wrap gap-3">
              <Button asChild>
                <a href={smartInvestorApi.exportPdfUrl(stream.done.analysis_id)} target="_blank" rel="noopener">
                  <Download className="ms-2 h-4 w-4" /> تنزيل PDF
                </a>
              </Button>
              <Button variant="outline" onClick={stream.reset}>
                <RefreshCw className="ms-2 h-4 w-4" /> تحليل جديد
              </Button>
            </div>
          )}

          {Object.entries(stream.stages)
            .filter(([key]) => key in AGENT_LABELS)
            .map(([key, value]) => (
              <AgentReport key={key} title={AGENT_LABELS[key]} content={value?.content || ''} />
            ))}
        </TabsContent>

        <TabsContent value="history">
          <AnalysesList
            refreshKey={refreshList}
            onSelect={id => navigate(`/tools/smart-investor/analyses/${id}`)}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
