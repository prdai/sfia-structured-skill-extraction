#!/usr/bin/env bun
import { $ } from "bun";
import { recordId, VECTORIZE_INDEX } from "../src/lib/retrieval-config";
import { indexedText, loadCorpus } from "./corpus";
import { embed } from "./workers-ai";

// One vector per skill-level record, embedding "<skill name>: <description>".
// Mirrors embedding-matcher/src/embedding_matcher/ingest.py; no chunking, so a
// record is the atomic retrieval unit on both sides.
const BATCH_SIZE = 50;
const PROJECT_DIR = `${import.meta.dir}/..`;
const OUT_FILE = `${PROJECT_DIR}/vectors.ndjson`;

type VectorizeIndex = {
  name: string;
  config: { dimensions: number; metric: string };
};

const indexes: VectorizeIndex[] = await $`bunx wrangler vectorize list --json`.cwd(PROJECT_DIR).json();
const existing = indexes.find((index) => index.name === VECTORIZE_INDEX);
const { records, nameOf } = await loadCorpus();
const texts = records.map((record) => indexedText(nameOf(record.code), record));

const vectors: number[][] = [];
for (let start = 0; start < texts.length; start += BATCH_SIZE) {
  vectors.push(...(await embed(texts.slice(start, start + BATCH_SIZE))));
  console.error(`embedded ${Math.min(start + BATCH_SIZE, texts.length)}/${texts.length}`);
}

const dimensions = vectors[0].length;
const ragged = vectors.findIndex((vector) => vector.length !== dimensions);
if (ragged !== -1) {
  throw new Error(
    `${records[ragged].code}-${records[ragged].level} embedded to ${vectors[ragged].length} dimensions, expected ${dimensions}`,
  );
}

const lines = records.map((record, index) =>
  JSON.stringify({
    id: recordId(record.code, record.level),
    values: vectors[index],
    metadata: { code: record.code, level: record.level },
  }),
);
await Bun.write(OUT_FILE, `${lines.join("\n")}\n`);

console.log(`\nWrote ${lines.length} vectors (${dimensions} dimensions) to ${OUT_FILE}`);
if (existing && (existing.config.dimensions !== dimensions || existing.config.metric !== "cosine")) {
  throw new Error(
    `${VECTORIZE_INDEX} must use ${dimensions} dimensions and cosine distance. Use a compatible index before seeding.`,
  );
}

if (!existing) {
  await $`bunx wrangler vectorize create ${VECTORIZE_INDEX} --dimensions=${dimensions} --metric=cosine`
    .cwd(PROJECT_DIR);
}
await $`bunx wrangler vectorize upsert ${VECTORIZE_INDEX} --file=${OUT_FILE}`.cwd(PROJECT_DIR);
