import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000",
  timeout: 15000,
});

export type Overview = {
  total_trades: number;
  trades_with_21d_return: number;
  buys: {
    count: number;
    mean_excess_return_21d: number | null;
  };
  sells: {
    count: number;
    mean_excess_return_21d: number | null;
  };
  buy_vs_sell_ttest: {
    t_stat: number | null;
    p_value: number | null;
  };
  nlp_coverage: {
    top_retrieved_count: number;
    top_retrieved_pct: number;
    sentiment_30d_count: number;
    sentiment_30d_pct: number;
  };
};

export type SenatorRow = {
  senator: string;
  n: number;
  mean_excess_return_21d: number | null;
  ci_low: number | null;
  ci_high: number | null;
};

export type SentimentBucket = {
  sentiment_bucket: string;
  n: number;
  mean_sentiment_score_30d: number | null;
  mean_excess_return_21d: number | null;
  ci_low: number | null;
  ci_high: number | null;
};

export type NlpRouting = {
  mode: string;
  total_scored_news: number;
  checked_news: number;
  total_processed_news: number;
  retrieval_rows: number;
  weights: Record<string, number>;
  llm: Record<string, number | string | null>;
  llm_elapsed_seconds: number;
  counts: Record<string, number>;
  percentages: Record<string, number>;
};

export type EquityPoint = {
  date: string;
  equity: number;
  cash?: number;
  open_positions?: number;
};

export type BacktestMetrics = {
  total_return: number;
  annualized_return: number;
  volatility: number;
  sharpe: number | null;
  max_drawdown: number;
  hit_rate: number | null;
  trade_count: number;
};

export type BacktestSeries = {
  equity_curve: EquityPoint[];
  metrics: BacktestMetrics;
  trades?: unknown[];
};

export type Backtest = {
  baseline: BacktestSeries;
  nlp_filtered: BacktestSeries;
  spy: BacktestSeries;
};

export type RecentTrade = {
  trade_id: number;
  senator: string;
  ticker: string;
  type: string;
  disclosure_date: string;
  signal_date: string | null;
  entry_price: number | null;
  fwd_return_21d: number | null;
  excess_return_21d: number | null;
  news_count_30d: number;
  sentiment_score_30d: number | null;
  top_news_similarity: number | null;
  top_news_sentiment: number | null;
  top_news_headline: string | null;
  top_news_published_at: string | null;
  top_news_publisher: string | null;
};

export type RerunStatus = {
  running: boolean;
  step: string;
  message: string;
  started_at: string | null;
  finished_at: string | null;
  success: boolean | null;
};

async function get<T>(path: string): Promise<T> {
  const response = await api.get<T>(path);
  return response.data;
}

export const fetchOverview = () => get<Overview>("/api/overview");
export const fetchSenators = () => get<SenatorRow[]>("/api/senators");
export const fetchSentimentBuckets = () => get<SentimentBucket[]>("/api/sentiment-buckets");
export const fetchNlpRouting = () => get<NlpRouting>("/api/nlp-routing");
export const fetchBacktest = () => get<Backtest>("/api/backtest");
export const fetchRecentTrades = (n = 50) => get<RecentTrade[]>(`/api/trades/recent?n=${n}`);
export const startRerun = async () => {
  const response = await api.post<RerunStatus>("/api/rerun");
  return response.data;
};
export const fetchRerunStatus = () => get<RerunStatus>("/api/rerun/status");
