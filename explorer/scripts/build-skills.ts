import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { Skill } from "../src/lib/types";
import { loadCorpus, type SkillLevelRecord } from "./corpus";

const EXPECTED_SKILLS = 147;
const EXCERPT_MAX_CHARS = 220;
// Mid-range levels read best as a one-paragraph summary of a whole skill.
const LEVEL_PREFERENCE = [4, 5, 3, 6, 2, 7, 1];
const OUT_DIR = resolve(dirname(fileURLToPath(import.meta.url)), "../src/data");
const OUT_FILE = resolve(OUT_DIR, "skills.json");

function levelRank(level: number): number {
  const rank = LEVEL_PREFERENCE.indexOf(level);
  return rank === -1 ? Number.MAX_SAFE_INTEGER : rank;
}

function preferredRecord(records: SkillLevelRecord[]): SkillLevelRecord {
  return [...records].sort((a, b) => levelRank(a.level) - levelRank(b.level))[0];
}

function excerpt(text: string): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= EXCERPT_MAX_CHARS) return normalized;

  const sentences = normalized.match(/[^.!?]+[.!?]+/g) ?? [];
  let out = "";
  for (const sentence of sentences) {
    const next = `${out} ${sentence.trim()}`.trim();
    if (next.length > EXCERPT_MAX_CHARS) break;
    out = next;
  }

  return `${out || normalized.slice(0, EXCERPT_MAX_CHARS).trim()}…`;
}

const { records, skills, recordsByCode } = loadCorpus();

if (skills.length !== EXPECTED_SKILLS) {
  throw new Error(`Expected ${EXPECTED_SKILLS} skills in the summary chart, got ${skills.length}`);
}

const catalogue: Skill[] = skills
  .map((skill) => {
    const skillRecords = recordsByCode.get(skill.code);
    if (!skillRecords?.length) {
      throw new Error(`No extracted records for ${skill.code}: cannot build an excerpt`);
    }

    const record = preferredRecord(skillRecords);
    return {
      code: skill.code,
      name: skill.name,
      levels: skill.levels,
      excerpt: excerpt(record.text),
      sourceUrl: record.source_url,
    };
  })
  .sort((a, b) => a.name.localeCompare(b.name));

mkdirSync(OUT_DIR, { recursive: true });
writeFileSync(OUT_FILE, `${JSON.stringify(catalogue, null, 2)}\n`);

console.log(`wrote ${catalogue.length} skills from ${records.length} records`);
