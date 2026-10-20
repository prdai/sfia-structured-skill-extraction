import { Check, Copy } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/button";

export function CopyButton({ text, label = "Copy BibTeX" }: { text: string; label?: string }) {
  const [copied, setCopied] = React.useState(false);

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 2000);
        } catch {
          setCopied(false);
        }
      }}
    >
      {copied ? <Check /> : <Copy />}
      {copied ? "Copied" : label}
    </Button>
  );
}
