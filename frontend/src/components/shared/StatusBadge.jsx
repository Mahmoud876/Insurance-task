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
  const config = statusConfig[status];
   if (!config) {
    throw new Error(`Unknown claim status: ${status}`);
  }

  return (
    <Badge variant={config.variant}>
      {config.label}
    </Badge>
  );
}

//make StatusBadge available outside this file.
export { StatusBadge };
