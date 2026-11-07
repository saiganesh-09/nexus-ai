import { BarChart3 } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function AnalyticsPage() {
  return (
    <ModulePlaceholder
      title="Analytics"
      description="Cost, token, latency and provider usage analytics."
      icon={BarChart3}
      phase="Phase 5"
      items={["cost trends", "token usage", "provider performance", "error rates"]}
    />
  );
}
