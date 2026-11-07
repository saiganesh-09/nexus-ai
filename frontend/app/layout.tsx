import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "NEXUS AI",
    template: "%s · NEXUS AI",
  },
  description:
    "Intelligent LLM Gateway & AI Operations Platform — route prompts to the right model, track usage and cost, evaluate agents.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
