import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Record_ = {
  code: string;
  level: number;
  text: string;
  source_url: string;
};

type Chart = {
  skills: { code: string; name: string; levels: number[] }[];
};

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../..");
const records = JSON.parse(
  readFileSync(resolve(repoRoot, "data/sfia-skill-level-records.json"), "utf8"),
) as Record_[];
const chart = JSON.parse(
  readFileSync(resolve(repoRoot, "data/sfia-9-summary-chart.json"), "utf8"),
) as Chart;

const names = new Map(chart.skills.map((skill) => [skill.code, skill.name]));
const byCode = new Map<string, Record_[]>();

for (const record of records) {
  const list = byCode.get(record.code) ?? [];
  list.push(record);
  byCode.set(record.code, list);
}

function excerptFor(skillRecords: Record_[], maxChars = 220): string {
  const preferred = [4, 5, 3, 6, 2, 7, 1];
  const record = [...skillRecords].sort(
    (a, b) => preferred.indexOf(a.level) - preferred.indexOf(b.level),
  )[0];
  return trimSentences(record.text, maxChars);
}

function trimSentences(text: string, maxChars: number): string {
  const normalized = text.replace(/\s+/g, " ").trim();
  const sentences = (normalized.match(/[^.!?]+[.!?]+/g) ?? [normalized]).map((sentence) =>
    sentence.trim(),
  );
  let out = "";
  for (const sentence of sentences) {
    const next = `${out} ${sentence}`.trim();
    if (next.length > maxChars) break;
    out = next;
  }
  if (!out) out = `${text.slice(0, maxChars).trim()}…`;
  else if (out.length < text.trim().length) out = `${out}…`;
  return out;
}

const skills = chart.skills
  .map((skill) => {
    const skillRecords = byCode.get(skill.code) ?? [];
    const best = [...skillRecords].sort(
      (a, b) => [4, 5, 3, 6, 2, 7, 1].indexOf(a.level) - [4, 5, 3, 6, 2, 7, 1].indexOf(b.level),
    )[0];
    return {
      code: skill.code,
      name: names.get(skill.code) ?? skill.code,
      levels: skill.levels,
      excerpt: skillRecords.length ? excerptFor(skillRecords) : "",
      sourceUrl: best?.source_url ?? `https://sfia-online.org/en/sfia-9/skills/${skill.code.toLowerCase()}`,
    };
  })
  .sort((a, b) => a.name.localeCompare(b.name));

if (skills.length !== 147) {
  throw new Error(`Expected 147 skills, got ${skills.length}`);
}

const missingExcerpts = skills.filter((skill) => !skill.excerpt);
if (missingExcerpts.length) {
  throw new Error(`Missing excerpts for: ${missingExcerpts.map((s) => s.code).join(", ")}`);
}

const outDir = resolve(here, "../src/data");
mkdirSync(outDir, { recursive: true });
writeFileSync(resolve(outDir, "skills.json"), `${JSON.stringify(skills, null, 2)}\n`);
writeFileSync(
  resolve(outDir, "stats.json"),
  `${JSON.stringify(
    {
      skills: skills.length,
      records: records.length,
      levels: 7,
      generatedAt: new Date().toISOString().slice(0, 10),
    },
    null,
    2,
  )}\n`,
);

console.log(`wrote ${skills.length} skills from ${records.length} records`);
