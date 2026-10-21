import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { indexedText, loadCorpus, type SkillLevelRecord } from "./corpus";

const DEFAULT_BUCKET = "sfia-corpus";
const INSTANCE = "sfia-corpus";
const KEY_PREFIX = "records/";
// Must stay in step with the instance's chunk_size so no record is ever split.
const CHUNK_SIZE = 1024;
const CONCURRENCY = 8;
const PROGRESS_EVERY = 50;

const accountId = process.env.R2_ACCOUNT_ID;
const accessKeyId = process.env.R2_ACCESS_KEY_ID;
const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
const bucket = process.env.R2_BUCKET ?? DEFAULT_BUCKET;

if (!accountId || !accessKeyId || !secretAccessKey) {
  console.error(
    "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY before running this script.",
  );
  process.exit(1);
}

const { records, nameOf } = loadCorpus();

type IndexedRecord = SkillLevelRecord & { skill: string };

const indexed: IndexedRecord[] = records.map((record) => {
  const skill = nameOf(record.code);
  const text = indexedText(skill, record);
  // UTF-8 byte length bounds the token count conservatively.
  const bytes = Buffer.byteLength(text, "utf8");
  if (bytes > CHUNK_SIZE) {
    throw new Error(
      `${record.code}-${record.level} is ${bytes} bytes, over the ${CHUNK_SIZE}-byte indexing guard. ` +
        `Raise the instance chunk_size and CHUNK_SIZE together before seeding.`,
    );
  }
  return { ...record, text, skill };
});

const client = new S3Client({
  region: "auto",
  endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId, secretAccessKey },
});

let uploaded = 0;

async function upload(record: IndexedRecord): Promise<void> {
  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: `${KEY_PREFIX}${record.code}-${record.level}.txt`,
      Body: record.text,
      ContentType: "text/plain; charset=utf-8",
      Metadata: {
        code: record.code,
        skill: record.skill,
        level: String(record.level),
        source_url: record.source_url,
      },
    }),
  );

  uploaded += 1;
  if (uploaded % PROGRESS_EVERY === 0 || uploaded === indexed.length) {
    console.error(`uploaded ${uploaded}/${indexed.length}`);
  }
}

let cursor = 0;

await Promise.all(
  Array.from({ length: CONCURRENCY }, async () => {
    while (cursor < indexed.length) {
      await upload(indexed[cursor++]);
    }
  }),
);

console.log(`\nDone. ${indexed.length} objects in r2://${bucket}/${KEY_PREFIX}`);
console.log("Trigger indexing with:");
console.log(`  bunx wrangler ai-search jobs create ${INSTANCE}`);
