import { FlaskConical } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function EvaluationsPage() {
  return (
    <ModulePlaceholder
      title="Evaluations"
      description="Run and review agent evaluation suites."
      icon={FlaskConical}
      phase="Phase 6"
      items={["datasets", "scored runs", "historical comparisons"]}
    />
  );
}
