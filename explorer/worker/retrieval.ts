import { create, insertMultiple, search } from "@orama/orama";
import { stopwords } from "@orama/stopwords/english";

import rawRecords from "../src/data/records.json";
import {
  EMBEDDING_MODEL,
  KEYWORD_THRESHOLD,
  recordId,
  rerankPrompt,
  RERANK_THRESHOLD,
  RERANKER_MODEL,
  RETRIEVAL_K,
  TOOL_RESULT_LIMIT,
} from "../src/lib/retrieval-config";
import type { CorpusRecord } from "../src/lib/types";
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

const RECORDS = rawRecords as CorpusRecord[];
const byId = new Map(RECORDS.map((record) => [recordId(record.code, record.level), record]));
const keywordIndex = create({
  schema: { text: "string" },
  components: { tokenizer: { stopWords: stopwords, allowDuplicates: true } },
});
insertMultiple(keywordIndex, RECORDS.map((record) => ({
  id: recordId(record.code, record.level),
  text: record.text,
})));
const SCORE_RE = /[01](?:\.\d+)?/;

function toHit(record: CorpusRecord, score: number): RetrievalHit | undefined {
  const skill = resolveSkill(record.code);
  if (!skill || !skill.levels.includes(record.level)) return undefined;

  return {
    code: skill.code,
    skill: skill.name,
    level: record.level,
    text: record.text,
    sourceUrl: record.sourceUrl,
    score,
  };
}

async function rerankScore(env: Env, query: string, candidate: string): Promise<number> {
  const response = await env.AI.run(
    RERANKER_MODEL,
    {
      messages: [{ role: "user", content: rerankPrompt(query, candidate) }],
      temperature: 0,
      max_tokens: 8,
    },
    { gateway: { id: env.AI_GATEWAY_ID } },
  );

  const match = SCORE_RE.exec(String((response as { response?: unknown }).response ?? ""));
  return match ? Number(match[0]) : 0;
}

async function semanticSearch(env: Env, query: string): Promise<RetrievalHit[]> {
  const embedding = await env.AI.run(
    EMBEDDING_MODEL,
    { text: [query] },
    { gateway: { id: env.AI_GATEWAY_ID } },
  );
  const vector = (embedding as { data: number[][] }).data[0];
  const { matches } = await env.VECTORIZE.query(vector, { topK: RETRIEVAL_K });

  const candidates = matches
    .map((match) => byId.get(match.id))
    .filter((record): record is CorpusRecord => record !== undefined);
  const scored = await Promise.all(
    candidates.map(async (record) => ({ record, score: await rerankScore(env, query, record.text) })),
  );

  return scored
    .filter(({ score }) => score >= RERANK_THRESHOLD)
    .map(({ record, score }) => toHit(record, score))
    .filter((hit): hit is RetrievalHit => hit !== undefined)
    .sort((a, b) => b.score - a.score);
}

async function keywordSearch(query: string): Promise<RetrievalHit[]> {
  const { hits } = await search(keywordIndex, {
    term: query,
    threshold: 1,
    limit: TOOL_RESULT_LIMIT,
  });
  const top = hits[0]?.score ?? 0;
  if (top <= 0) return [];

  return hits.map((hit) => {
    const record = byId.get(hit.id);
    const score = hit.score / top;
    return record && score >= KEYWORD_THRESHOLD ? toHit(record, score) : undefined;
  })
    .filter((hit): hit is RetrievalHit => hit !== undefined)
    .sort((a, b) => b.score - a.score);
}

export async function searchSkills(
  env: Env,
  query: string,
  retrievalType: "vector" | "keyword",
): Promise<RetrievalHit[]> {
  const hits = retrievalType === "vector" ? await semanticSearch(env, query) : await keywordSearch(query);
  return hits.slice(0, TOOL_RESULT_LIMIT);
}
