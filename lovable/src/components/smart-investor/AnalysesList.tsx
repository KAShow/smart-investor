import { useEffect, useState } from 'react';
import { FileText, Trash2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useToast } from '@/hooks/use-toast';
import { smartInvestorApi } from '@/lib/smart-investor/api';
import type { SavedAnalysis } from '@/lib/smart-investor/types';

type Props = {
  onSelect: (id: number) => void;
  refreshKey?: number;
};

export function AnalysesList({ onSelect, refreshKey = 0 }: Props) {
  const [items, setItems] = useState<SavedAnalysis[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    setLoading(true);
    smartInvestorApi
      .listMyAnalyses()
      .then(setItems)
      .catch(e => toast({ title: 'تعذّر تحميل التحليلات', description: e.message, variant: 'destructive' }))
      .finally(() => setLoading(false));
  }, [refreshKey, toast]);

  const remove = async (id: number) => {
    if (!confirm('هل أنت متأكد من حذف هذا التحليل؟')) return;
    try {
      await smartInvestorApi.deleteAnalysis(id);
      setItems(items.filter(i => i.id !== id));
      toast({ title: 'تم الحذف' });
    } catch (e: any) {
      toast({ title: 'فشل الحذف', description: e.message, variant: 'destructive' });
    }
  };

  if (loading) return <div className="text-center text-muted-foreground">جاري التحميل...</div>;

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          لم تنشئ أي تحليل بعد. ابدأ بأول دراسة جدوى لك.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {items.map(item => (
        <Card key={item.id} className="cursor-pointer transition-colors hover:bg-muted/50">
          <CardContent
            className="flex items-center gap-3 p-4"
            onClick={() => onSelect(item.id)}
          >
            <FileText className="h-5 w-5 shrink-0 text-primary" />
            <div className="flex-1 min-w-0">
              <p className="truncate font-medium">{item.idea}</p>
              <p className="text-xs text-muted-foreground">
                {item.report_number} · {new Date(item.created_at).toLocaleDateString('ar-BH')}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={e => {
                e.stopPropagation();
                remove(item.id);
              }}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
