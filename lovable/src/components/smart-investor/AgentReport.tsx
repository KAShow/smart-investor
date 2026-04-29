import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeSanitize from 'rehype-sanitize';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

type Props = {
  title: string;
  content: string; // raw JSON string from API or Markdown
};

function tryParseJson(content: string): any | null {
  if (!content) return null;
  const trimmed = content.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) return null;
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

export function AgentReport({ title, content }: Props) {
  const parsed = useMemo(() => tryParseJson(content), [content]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{title}</CardTitle>
          {parsed?.score != null && (
            <Badge variant={parsed.score >= 7 ? 'default' : parsed.score >= 5 ? 'secondary' : 'destructive'}>
              {parsed.score}/10
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {parsed ? <ParsedView data={parsed} /> : <MarkdownView text={content} />}
      </CardContent>
    </Card>
  );
}

function ParsedView({ data }: { data: any }) {
  return (
    <div className="space-y-3 leading-relaxed">
      {data.title && <h4 className="text-base font-semibold">{data.title}</h4>}
      {data.summary && <p>{data.summary}</p>}
      {Array.isArray(data.details) && data.details.length > 0 && (
        <ul className="list-disc space-y-1 pr-5 text-sm">
          {data.details.map((d: string, i: number) => (
            <li key={i}>{d}</li>
          ))}
        </ul>
      )}
      {data.recommendation && (
        <div className="rounded-md border-r-4 border-primary bg-muted/30 p-3 text-sm">
          <strong>التوصية:</strong> {data.recommendation}
        </div>
      )}
      {Array.isArray(data.models) && data.models.length > 0 && (
        <div className="space-y-2">
          <h5 className="text-sm font-semibold">النماذج المقترحة</h5>
          {data.models.map((m: any, i: number) => (
            <div key={i} className="rounded-md border p-3">
              <div className="flex items-center justify-between">
                <strong>{m.name}</strong>
                {m.score != null && <Badge variant="secondary">{m.score}/10</Badge>}
              </div>
              {m.fit_for_bahrain && (
                <p className="mt-1 text-xs text-muted-foreground">ملاءمة للسوق البحريني: {m.fit_for_bahrain}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MarkdownView({ text }: { text: string }) {
  if (!text) return <p className="text-muted-foreground">لا يوجد محتوى</p>;
  return (
    <div className="prose prose-sm max-w-none rtl:prose-headings:text-right dark:prose-invert">
      <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{text}</ReactMarkdown>
    </div>
  );
}
