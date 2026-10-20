import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

type Record_ = {
  code: string;
  level: number;
  text: string;
  source_url: string;
};

type Chart = {
  skills: { code: string; name: string }[];
};

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../..");

const accountId = process.env.R2_ACCOUNT_ID;
const accessKeyId = process.env.R2_ACCESS_KEY_ID;
const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY;
const bucket = process.env.R2_BUCKET ?? "sfia-corpus";

if (!accountId || !accessKeyId || !secretAccessKey) {
  console.error(
    "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY before running this script.",
  );
  process.exit(1);
}

const records = JSON.parse(
  readFileSync(resolve(repoRoot, "data/sfia-skill-level-records.json"), "utf8"),
) as Record_[];
const chart = JSON.parse(
  readFileSync(resolve(repoRoot, "data/sfia-9-summary-chart.json"), "utf8"),
) as Chart;
const names = new Map(chart.skills.map((skill) => [skill.code, skill.name]));

const client = new S3Client({
  region: "auto",
  endpoint: `https://${accountId}.r2.cloudflarestorage.com`,
  credentials: { accessKeyId, secretAccessKey },
});

let uploaded = 0;

async function upload(record: Record_) {
  const skill = names.get(record.code);
  if (!skill) throw new Error(`Unknown skill code ${record.code}`);

  await client.send(
    new PutObjectCommand({
      Bucket: bucket,
      Key: `records/${record.code}-${record.level}.txt`,
      Body: record.text,
      ContentType: "text/plain; charset=utf-8",
      Metadata: {
        code: record.code,
        skill,
        level: String(record.level),
        source_url: record.source_url,
      },
    }),
  );

  uploaded += 1;
  if (uploaded % 50 === 0 || uploaded === records.length) {
    console.log(`uploaded ${uploaded}/${records.length}`);
  }
}

const concurrency = 8;
let cursor = 0;

await Promise.all(
  Array.from({ length: concurrency }, async () => {
    while (cursor < records.length) {
      const record = records[cursor++];
      await upload(record);
    }
  }),
);

console.log(`\nDone. ${records.length} objects in r2://${bucket}/records/`);
console.log("Trigger indexing with:");
console.log("  npx wrangler ai-search jobs create sfia-corpus");
