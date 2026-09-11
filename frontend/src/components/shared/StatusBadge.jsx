import { Badge } from "@/components/ui/badge";

const statusConfig = {
  DRAFT: {
    label: "Draft",
    variant: "secondary",
  },

  SUBMITTED: {
    label: "Submitted",
    variant: "outline",
  },

  ACCEPTED: {
    label: "Accepted",
    variant: "default",
  },

  REJECTED: {
    label: "Rejected",
    variant: "destructive",
  },

  PAID: {
    label: "Paid",
    variant: "default",
  },
};

function StatusBadge({ status }) {
  status = typeof status === "object" ? status?.value : status;
  const config = statusConfig[status];
  const safeConfig = config || { label: status || "Unknown", variant: "outline" };

  return (
    <Badge variant={config.variant}>
      {safeConfig.label}
    </Badge>
  );
}

//make StatusBadge available outside this file.
export { StatusBadge };
