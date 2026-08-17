import { StatusBadge } from "@/components/shared/StatusBadge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { ScorePill } from "@/components/shared/ScorePill";

function App() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6">
      <h1 className="text-4xl font-bold">
        Dental Claim Scrubber
      </h1>

      <div className="flex gap-2">
        <StatusBadge status="DRAFT" />
        <StatusBadge status="SUBMITTED" />
        <StatusBadge status="ACCEPTED" />
        <StatusBadge status="REJECTED" />
        <StatusBadge status="PAID" />
      </div>

      <div className="flex gap-2">
        <SeverityBadge severity="LOW" />
        <SeverityBadge severity="MEDIUM" />
        <SeverityBadge severity="HIGH" />
        <SeverityBadge severity="CRITICAL" />
      </div>

      <div className="flex gap-2">
        <ScorePill score={95} />
        <ScorePill score={68} />
        <ScorePill score={32} />
      </div>
    </div>
  );
}

export default App;