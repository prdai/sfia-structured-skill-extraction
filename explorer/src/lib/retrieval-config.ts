// Mirrors the Python pipeline so the demo and the paper's numbers come from the
// same retrieval behaviour; see embedding-matcher/src/embedding_matcher/__init__.py
// and keyword-matcher/src/keyword_matcher/matcher.py.
export const EMBEDDING_MODEL = "@cf/qwen/qwen3-embedding-0.6b";
export const RERANKER_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";

export const VECTORIZE_INDEX = "sfia-skill-level-records";

// Vector ids are derived, not stored, so re-seeding upserts in place.
export function recordId(code: string, level: number): string {
  return `${code}-${level}`;
}

export const RETRIEVAL_K = 20;
export const RERANK_THRESHOLD = 0.6;
export const KEYWORD_THRESHOLD = 0.7;
export const TOOL_RESULT_LIMIT = 10;

export const BM25_K1 = 1.5;
export const BM25_B = 0.75;
export const BM25_EPSILON = 0.25;

const RERANK_PROMPT = `You are scoring how relevant an SFIA skill description is to a query.

Query (a job/course/role description):
{query}

Candidate skill description:
{candidate}

How relevant is the candidate to the query? Reply with ONLY a number between 0 and 1 (e.g. 0.85), nothing else.`;

// Function replacements: record text containing "$&" must not be expanded.
export function rerankPrompt(query: string, candidate: string): string {
  return RERANK_PROMPT.replace("{query}", () => query).replace("{candidate}", () => candidate);
}
