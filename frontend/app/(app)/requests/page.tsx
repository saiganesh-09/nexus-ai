import { History } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function RequestsPage() {
  return (
    <ModulePlaceholder
      title="Requests"
      description="Full history of AI requests with search, filters and details."
      icon={History}
      phase="Phase 4"
      items={["search & filter", "pagination", "request details"]}
    />
  );
}
