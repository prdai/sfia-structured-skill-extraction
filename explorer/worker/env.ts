export interface Env {
  AI: Ai;
  AI_SEARCH: AiSearchInstance;
  MATCH_CACHE: KVNamespace;
  BUDGET: DurableObjectNamespace;
  QUERIES: AnalyticsEngineDataset;
  ASSETS: Fetcher;
  APP_ORIGIN: string;
  MODEL: string;
  MONTHLY_MATCH_BUDGET: string;
  TURNSTILE_SECRET?: string;
}
