import rawSkills from "../src/data/skills.json";
import type { Match, Skill } from "../src/lib/types";

export const SKILLS = rawSkills as Skill[];

const byCode = new Map(SKILLS.map((skill) => [skill.code.toUpperCase(), skill]));
const byName = new Map(SKILLS.map((skill) => [skill.name.toLowerCase(), skill]));

export function resolveSkill(code: string, name?: string): Skill | undefined {
  return byCode.get(code.trim().toUpperCase()) ?? (name ? byName.get(name.trim().toLowerCase()) : undefined);
}

export function toMatch(skill: Skill, level: number, score?: number): Match {
  return {
    code: skill.code,
    skill: skill.name,
    level,
    excerpt: skill.excerpt,
    sourceUrl: skill.sourceUrl,
    ...(score === undefined ? {} : { score }),
  };
}

export function normalizeMatches(
  input: { code?: string; skill?: string; level: number }[],
): Match[] {
  const seen = new Set<string>();
  const matches: Match[] = [];

  for (const candidate of input) {
    const skill = resolveSkill(candidate.code ?? "", candidate.skill);
    if (!skill) continue;
    if (!Number.isInteger(candidate.level)) continue;
    if (!skill.levels.includes(candidate.level)) continue;

    const key = `${skill.code}:${candidate.level}`;
    if (seen.has(key)) continue;
    seen.add(key);
    matches.push(toMatch(skill, candidate.level));
  }

  return matches.slice(0, 20);
}
