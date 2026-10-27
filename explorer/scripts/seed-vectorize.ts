import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { recordId, VECTORIZE_INDEX } from "../src/lib/retrieval-config";
import { indexedText, loadCorpus } from "./corpus";
import { embed } from "./workers-ai";

// One vector per skill-level record, embedding "<skill name>: <description>".
// Mirrors embedding-matcher/src/embedding_matcher/ingest.py; no chunking, so a
// record is the atomic retrieval unit on both sides.
const BATCH_SIZE = 50;
const OUT_FILE = resolve(dirname(fileURLToPath(import.meta.url)), "../vectors.ndjson");

const { records, nameOf } = loadCorpus();
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
console.log("Create the index once, then upsert:");
console.log(
  `  bunx wrangler vectorize create ${VECTORIZE_INDEX} --dimensions=${dimensions} --metric=cosine`,
);
console.log(`  bunx wrangler vectorize upsert ${VECTORIZE_INDEX} --file=${OUT_FILE}`);
