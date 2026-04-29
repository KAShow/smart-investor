import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { smartInvestorApi } from '@/lib/smart-investor/api';
import type { Sector } from '@/lib/smart-investor/types';

type Props = {
  value?: string;
  onChange: (sector: string) => void;
};

export function SectorPicker({ value, onChange }: Props) {
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    smartInvestorApi
      .listSectors()
      .then(setSectors)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {sectors.map(sector => (
        <Card
          key={sector.value}
          onClick={() => onChange(sector.value)}
          className={cn(
            'cursor-pointer transition-all hover:scale-105 hover:border-primary',
            value === sector.value && 'border-primary bg-primary/5 ring-2 ring-primary',
          )}
        >
          <CardContent className="flex flex-col items-center justify-center gap-2 p-4 text-center">
            <span className="text-3xl" aria-hidden="true">
              {sector.icon}
            </span>
            <span className="text-sm font-medium">{sector.name_ar}</span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
