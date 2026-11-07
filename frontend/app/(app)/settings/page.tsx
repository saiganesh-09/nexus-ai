import { Settings } from "lucide-react";
import { ModulePlaceholder } from "@/components/module-placeholder";

export default function SettingsPage() {
  return (
    <ModulePlaceholder
      title="Settings"
      description="Profile, provider configuration and API key management."
      icon={Settings}
      phase="Phase 9"
      items={["profile", "provider config", "API keys", "usage limits"]}
    />
  );
}
