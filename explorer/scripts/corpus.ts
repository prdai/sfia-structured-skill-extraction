import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export type SkillLevelRecord = {
  code: string;
  level: number;
  text: string;
  source_url: string;
};

export type ChartSkill = {
  code: string;
  name: string;
  levels: number[];
};

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const RECORDS_PATH = "data/sfia-skill-level-records.json";
const CHART_PATH = "data/sfia-9-summary-chart.json";

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(resolve(repoRoot, relativePath), "utf8")) as T;
}

export type Corpus = {
  records: SkillLevelRecord[];
  skills: ChartSkill[];
  recordsByCode: Map<string, SkillLevelRecord[]>;
  nameOf: (code: string) => string;
};

export function loadCorpus(): Corpus {
  const records = readJson<SkillLevelRecord[]>(RECORDS_PATH);
  const { skills } = readJson<{ skills: ChartSkill[] }>(CHART_PATH);
  const names = new Map(skills.map((skill) => [skill.code, skill.name]));
  const recordsByCode = new Map<string, SkillLevelRecord[]>();

  for (const record of records) {
    const existing = recordsByCode.get(record.code);
    if (existing) existing.push(record);
    else recordsByCode.set(record.code, [record]);
  }

  return {
    records,
    skills,
    recordsByCode,
    nameOf: (code) => {
      const name = names.get(code);
      if (!name) {
        throw new Error(`Unknown skill code ${code}: not in ${CHART_PATH}`);
      }
      return name;
    },
  };
}

// The matching pipelines embed "<skill name>: <level description>", so anything
// that indexes the corpus must build its text the same way.
export function indexedText(skillName: string, record: SkillLevelRecord): string {
  return `${skillName}: ${record.text}`;
}
