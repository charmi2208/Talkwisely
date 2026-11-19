import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";

/** Change vs the previous period. Direction is shown by icon and sign, not only color. */
export function TrendBadge({ value, unit = "%", digits = 0 }: { value: number | null | undefined; unit?: string; digits?: number }) {
  if (value === null || value === undefined) return null;
  const Icon = value > 0 ? ArrowUpRight : value < 0 ? ArrowDownRight : Minus;
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return (
    <Badge variant="outline" className="tabular-nums" title="Change vs the previous period of the same length">
      <Icon />
      {sign}{Math.abs(value).toFixed(digits)}{unit}
    </Badge>
  );
}
