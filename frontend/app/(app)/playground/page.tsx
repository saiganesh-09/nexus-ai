import { MessageSquareText } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function PlaygroundPage() {
  return (
    <ModulePlaceholder
      title="Playground"
      description="Interactive prompt editor with automatic model routing."
      icon={MessageSquareText}
      phase="Phase 3"
      items={["auto-routing", "manual model selection", "streaming", "token & cost display"]}
    />
  );
}
