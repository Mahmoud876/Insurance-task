import { Info, AlertCircle, TriangleAlert, CircleX } from "lucide-react";
import { Badge } from "@/components/ui/badge";

const severityConfig = {
  LOW: {
    label: "Low",
    icon: Info,
    variant: "secondary",
  },

  MEDIUM: {
    label: "Medium",
    icon: AlertCircle,
    variant: "outline",
  },

  HIGH: {
    label: "High",
    icon: TriangleAlert,
    variant: "destructive",
  },

  CRITICAL: {
    label: "Critical",
    icon: CircleX,
    variant: "destructive",
  },
};

function SeverityBadge({ severity }) {
  const config = severityConfig[severity];

  if (!config) {
    throw new Error(`Unknown severity: ${severity}`);
  }

  const Icon = config.icon;

  return (
    <Badge variant={config.variant}>
      <Icon />
      {config.label}
    </Badge>
  );
}

export { SeverityBadge };