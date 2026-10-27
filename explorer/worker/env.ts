export interface Env {
  AI: Ai;
  VECTORIZE: VectorizeIndex;
  MATCH_CACHE: KVNamespace;
  BUDGET: DurableObjectNamespace;
  QUERIES: AnalyticsEngineDataset;
  ASSETS: Fetcher;
  APP_ORIGIN: string;
  MODEL: string;
  MONTHLY_MATCH_BUDGET: string;
  TURNSTILE_SECRET?: string;
}
