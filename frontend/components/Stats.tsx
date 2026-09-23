import { Card } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
export function StatCard({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: React.ReactNode;
  detail?: string;
  icon?: LucideIcon;
}) {
  return (
    <Card className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        {Icon && <Icon size={17} />}
      </div>
      <strong className="stat-value">{value}</strong>
      {detail && <p className="stat-detail">{detail}</p>}
    </Card>
  );
}
