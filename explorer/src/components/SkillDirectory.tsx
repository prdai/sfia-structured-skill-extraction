import * as React from "react";
import { Search } from "lucide-react";

import { Input } from "@/components/ui/input";
import type { Skill } from "@/lib/types";

export function SkillDirectory({ skills }: { skills: Skill[] }) {
  const [query, setQuery] = React.useState("");
  const [level, setLevel] = React.useState<number | null>(null);

  const filtered = React.useMemo(() => {
    const term = query.trim().toLowerCase();
    return skills.filter((skill) => {
      if (level !== null && !skill.levels.includes(level)) return false;
      if (!term) return true;
      return (
        skill.name.toLowerCase().includes(term) ||
        skill.code.toLowerCase().includes(term) ||
        skill.excerpt.toLowerCase().includes(term)
      );
    });
  }, [skills, query, level]);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search 147 skills by name, code, or description…"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setLevel(null)}
            className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
              level === null ? "bg-foreground text-background" : "text-muted-foreground hover:bg-muted"
            }`}
          >
            All
          </button>
          {[1, 2, 3, 4, 5, 6, 7].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setLevel(level === value ? null : value)}
              className={`rounded-full border px-2.5 py-1 text-xs tabular-nums transition-colors ${
                level === value
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-muted"
              }`}
            >
              L{value}
            </button>
          ))}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        {filtered.length} {filtered.length === 1 ? "skill" : "skills"}
      </p>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((skill) => (
          <a
            key={skill.code}
            href={`/skills/${skill.code.toLowerCase()}/`}
            className="group flex flex-col gap-2 rounded-2xl border bg-card p-4 transition-colors hover:bg-muted/30"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] tracking-wide text-muted-foreground">
                {skill.code}
              </span>
              <span className="text-[11px] tabular-nums text-muted-foreground">
                L{skill.levels[0]}–L{skill.levels.at(-1)}
              </span>
            </div>
            <h2 className="text-sm font-medium leading-snug group-hover:underline group-hover:underline-offset-4">
              {skill.name}
            </h2>
            <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
              {skill.excerpt}
            </p>
          </a>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="rounded-2xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          No skills match that search.
        </div>
      )}
    </div>
  );
}
