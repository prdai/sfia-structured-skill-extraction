import { ArrowUpRight } from "lucide-react";

import type { Match } from "@/lib/types";
import { safeHttpUrl } from "@/lib/utils";

export function MatchCard({ match }: { match: Match }) {
  const href = safeHttpUrl(match.sourceUrl);

  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] tracking-wide text-muted-foreground">
              {match.code}
            </span>
            <span className="rounded-full bg-muted px-2 py-0.5 text-[11px] font-medium tabular-nums text-muted-foreground">
              L{match.level}
            </span>
          </div>
          <h3 className="mt-1 text-sm font-medium leading-snug">{match.skill}</h3>
        </div>
        {href && (
          <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-muted-foreground transition-colors group-hover:text-foreground" />
        )}
      </div>

      <p className="line-clamp-3 text-sm leading-relaxed text-muted-foreground">{match.excerpt}</p>

      <div className="flex items-center gap-1" aria-label={`SFIA level ${match.level} of 7`}>
        {Array.from({ length: 7 }, (_, index) => (
          <span
            key={index}
            className={`h-1 w-4 rounded-full ${index < match.level ? "bg-foreground/70" : "bg-border"}`}
          />
        ))}
      </div>
    </>
  );

  const className =
    "group flex flex-col gap-3 rounded-2xl border bg-card p-4 text-left transition-colors hover:bg-muted/30";

  if (!href) return <div className={className}>{content}</div>;

  return (
    <a className={className} href={href} target="_blank" rel="noreferrer">
      {content}
    </a>
  );
}
