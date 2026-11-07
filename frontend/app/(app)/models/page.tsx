import { Boxes } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function ModelsPage() {
  return (
    <ModulePlaceholder
      title="Models"
      description="Catalog of available providers and models."
      icon={Boxes}
      phase="Phase 3"
      items={["provider status", "pricing", "capabilities"]}
    />
  );
}
