import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import {
  Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

const schema = z.object({
  budget: z
    .string()
    .optional()
    .refine(v => !v || /^\d+$/.test(v), { message: 'أدخل رقماً صحيحاً' }),
  notes: z.string().max(1500, 'الملاحظات يجب أن لا تتجاوز ١٥٠٠ حرف').optional(),
  requester_name: z.string().max(100).optional(),
  requester_email: z.string().email('بريد غير صالح').optional().or(z.literal('')),
  requester_company: z.string().max(200).optional(),
});

export type IdeaFormValues = z.infer<typeof schema>;

type Props = {
  sectorSelected: boolean;
  isSubmitting: boolean;
  onSubmit: (values: IdeaFormValues) => void;
};

export function IdeaForm({ sectorSelected, isSubmitting, onSubmit }: Props) {
  const form = useForm<IdeaFormValues>({
    resolver: zodResolver(schema),
    defaultValues: { budget: '', notes: '', requester_name: '', requester_email: '', requester_company: '' },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        <FormField
          control={form.control}
          name="budget"
          render={({ field }) => (
            <FormItem>
              <FormLabel>رأس المال المتوفر (دينار بحريني)</FormLabel>
              <FormControl>
                <Input type="text" inputMode="numeric" placeholder="مثلاً: 25000" {...field} />
              </FormControl>
              <FormDescription>اختياري — يقيّد التحليل المالي بهذه الميزانية.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>ملاحظات إضافية</FormLabel>
              <FormControl>
                <Textarea
                  rows={4}
                  placeholder="اذكر أي تفاصيل تساعد المحللين على فهم فكرتك..."
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="requester_name"
            render={({ field }) => (
              <FormItem>
                <FormLabel>الاسم</FormLabel>
                <FormControl>
                  <Input {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="requester_email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>البريد الإلكتروني</FormLabel>
                <FormControl>
                  <Input type="email" dir="ltr" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="requester_company"
          render={({ field }) => (
            <FormItem>
              <FormLabel>اسم الشركة (اختياري)</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Button type="submit" disabled={!sectorSelected || isSubmitting} className="w-full" size="lg">
          {isSubmitting ? 'جاري التحليل...' : 'ابدأ التحليل بالذكاء الاصطناعي'}
        </Button>
      </form>
    </Form>
  );
}
