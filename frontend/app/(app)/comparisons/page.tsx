import { GitCompareArrows } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function ComparisonsPage() {
  return (
    <ModulePlaceholder
      title="Comparisons"
      description="Send one prompt to multiple models and compare results."
      icon={GitCompareArrows}
      phase="Phase 5"
      items={["side-by-side responses", "cost & latency", "quality evaluation"]}
    />
  );
}
