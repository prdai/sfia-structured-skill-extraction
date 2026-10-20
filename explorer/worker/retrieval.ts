import type { Env } from "./env";
import { resolveSkill } from "./skills";

export type RetrievalHit = {
  code: string;
  skill: string;
  level: number;
  text: string;
  sourceUrl: string;
  score: number;
};

type Metadata = Record<string, unknown>;

function pick(metadata: Metadata, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === "string" && value.trim()) return value.trim();
    if (typeof value === "number") return String(value);
  }
  return undefined;
}

function fromKey(key: string): { code: string; level: number } | undefined {
  const match = key.match(/([A-Z]{3,5})-(\d)\.(?:txt|md|json)$/i);
  if (!match) return undefined;
  return { code: match[1].toUpperCase(), level: Number(match[2]) };
}

export async function searchSkills(
  env: Env,
  query: string,
  retrievalType: "vector" | "keyword",
): Promise<RetrievalHit[]> {
  const response = await env.AI_SEARCH.search({
    query,
    ai_search_options: {
      retrieval: {
        retrieval_type: retrievalType,
        max_num_results: 12,
        match_threshold: retrievalType === "vector" ? 0.35 : 0.05,
        keyword_match_mode: "or",
      },
      reranking: { enabled: false },
    },
  });

  const best = new Map<string, RetrievalHit>();

  for (const chunk of response.chunks) {
    const metadata = (chunk.item.metadata ?? {}) as Metadata;
    const keyParts = fromKey(chunk.item.key);
    const code = pick(metadata, ["code", "x-amz-meta-code"]) ?? keyParts?.code;
    const level = Number(pick(metadata, ["level", "x-amz-meta-level"]) ?? keyParts?.level);
    const skillName = pick(metadata, ["skill", "x-amz-meta-skill"]);
    const sourceUrl = pick(metadata, ["source_url", "source-url", "x-amz-meta-source_url"]);

    if (!code || !Number.isInteger(level) || level < 1 || level > 7) continue;

    const skill = resolveSkill(code, skillName);
    if (!skill) continue;
    if (!skill.levels.includes(level)) continue;

    const hit: RetrievalHit = {
      code: skill.code,
      skill: skill.name,
      level,
      text: chunk.text,
      sourceUrl: sourceUrl ?? skill.sourceUrl,
      score: chunk.score,
    };

    const dedupeKey = `${hit.code}:${hit.level}`;
    const existing = best.get(dedupeKey);
    if (!existing || existing.score < hit.score) best.set(dedupeKey, hit);
  }

  return [...best.values()].sort((a, b) => b.score - a.score).slice(0, 10);
}
