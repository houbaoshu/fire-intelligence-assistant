import { Badge } from "@/components/ui/badge";
import { RECORD_STATUS_LABELS, RECORD_STATUS_TONES } from "@/lib/record-status";
import { cn } from "@/lib/utils";

export function RecordStatusBadge({ status }: { status: string }) {
  return (
    <Badge
      variant="outline"
      className={cn("font-normal", RECORD_STATUS_TONES[status] ?? "bg-muted text-muted-foreground")}
    >
      {RECORD_STATUS_LABELS[status] ?? status}
    </Badge>
  );
}
