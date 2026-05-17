# Congressional Trading Signal Analyzer — Build Spec (v3: NLP-enhanced, fully local)

## How to use this file

You are an AI coding agent (Codex) helping me build this project in **VS Code**. This file is your single source of truth.

**Rules of engagement:**
1. Work through the **PHASES** in order. Do **one phase at a time**. Stop after each phase and wait for me to confirm before moving on.
2. Inside each phase, complete tasks sequentially. After each task, briefly state what you did and what file you changed.
3. If a decision is ambiguous, **ask me a single clarifying question** instead of guessing.
4. You may `pip install` additional packages as needed, BUT every addition must be added to `pyproject.toml` AND called out in the commit message under a `Dependencies added:` footer. Do not silently add deps.
5. Prefer **simple, readable code** over clever code. This is a portfolio project — recruiters will read it.
6. Every Python module gets a docstring. Every non-obvious function gets a comment.
7. **Do not skip the methodology guardrails** (no lookahead bias, transaction costs, proper train/test split). These are non-negotiable.
8. Commit after every phase with a clear commit message.

---

## Project overview

**Name:** `congressional-alpha`
**One-liner:** A data + NLP pipeline and research dashboard that analyzes whether US senators' stock trades — combined with financial news sentiment — generate alpha, with a tradeable backtested signal.

**Why this exists:** Portfolio project demonstrating data engineering, NLP/LLM engineering, classical ML, quantitative research methodology, and full-stack delivery. Target audience: quant developer / quant SWE hiring managers who want to see an ML-strong candidate who understands market data.

**Hard timeline:** 3 days, ~8-10 focused hours per day.

**Cost:** $0. Fully local stack. No paid APIs, no subscriptions.

---

## The thesis (one paragraph — this drives every design decision)

> Senator trade disclosures are a noisy alpha signal: most trades carry no information, but a subset (driven by committee access, timing, or context) outperforms. Pure trade-based strategies suffer from low signal-to-noise. By layering NLP-derived news sentiment around each trade — using cosine similarity to retrieve relevant news, Naive Bayes for fast bulk classification, FinBERT for finance-specific scoring, and a local LLM (Ollama) for ambiguous cases — we can filter the trade signal to a higher-conviction subset. The backtest evaluates whether the NLP-filtered signal beats the raw trade signal and SPY.

---

## Tech stack (locked — log any additions per Rule 4)

### Backend / pipeline
- **Language:** Python 3.11+
- **Storage:** Parquet (raw), DuckDB (processed/features), JSON (results)
- **Orchestration:** Plain Python scripts + Makefile
- **Classical ML / stats:** pandas, numpy, scikit-learn (Naive Bayes, TF-IDF, cosine), statsmodels
- **NLP / embeddings:** sentence-transformers (`all-MiniLM-L6-v2` for cosine), FinBERT (`ProsusAI/finbert`) for finance-specific classification
- **LLM:** Ollama running `llama3.1:8b` or `mistral:7b` (whatever is already pulled locally). **No API fallback.** If the local LLM fails to parse a response, log it and assign `label="neutral", confidence=0.5, source="fallback_neutral"`.
- **Trade data:** Senate Stock Watcher public dataset (free JSON, no key)
- **News data:** yfinance news (free, no key)
- **Prices:** yfinance daily OHLCV (free, no key)
- **API:** FastAPI + uvicorn
- **Backtest:** Pure pandas/numpy

### Frontend
- **Framework:** React + Vite + TypeScript
- **Charts:** Recharts
- **Styling:** Tailwind
- **HTTP:** axios

### Package managers
- `uv` for Python, `pnpm` for frontend

---

## Repo structure (create exactly this)

```
congressional-alpha/
├── README.md
├── Makefile
├── pyproject.toml
├── .gitignore
├── .env.example
├── data/
│   ├── raw/                  # immutable raw pulls
│   │   ├── senate_trades/
│   │   ├── prices/
│   │   └── news/
│   ├── processed/            # DuckDB lives here
│   ├── embeddings/           # cached sentence embeddings
│   └── results/              # backtest + EDA JSON outputs
├── src/
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── congress.py       # Senate Stock Watcher
│   │   ├── prices.py         # yfinance OHLCV
│   │   └── news.py           # yfinance news
│   ├── clean/
│   │   ├── __init__.py
│   │   └── transform.py
│   ├── nlp/
│   │   ├── __init__.py
│   │   ├── embeddings.py     # sentence-transformer wrapper, cosine retrieval
│   │   ├── classify_nb.py    # Naive Bayes sentiment classifier
│   │   ├── classify_finbert.py
│   │   ├── llm_local.py      # Ollama client
│   │   └── router.py         # picks NB → FinBERT → Ollama (3-tier cascade)
│   ├── features/
│   │   ├── __init__.py
│   │   └── build.py
│   ├── research/
│   │   ├── __init__.py
│   │   ├── eda.py
│   │   └── backtest.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py
│   └── config.py
├── notebooks/
│   └── exploration.ipynb
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── components/
        └── lib/api.ts
```

---

## Methodology guardrails (READ BEFORE WRITING ANY CODE)

These separate a real quant project from a toy. **Implement these correctly or the project is worthless.**

1. **No lookahead bias on trades.** The signal date is the **disclosure date**, NOT the transaction date. Entry price = open on disclosure_date + 1 business day.

2. **No lookahead bias on news/NLP.** A news article published at time T can only contribute to signals from time T+1 (next trading session open) onward. When joining news sentiment to trades, every news timestamp must be **strictly before** the trade's signal_date — and the join must be enforced in SQL, not just hoped for.

3. **No lookahead in NLP training.** The Naive Bayes classifier must be trained ONLY on the static labeled corpus (Financial PhraseBank), never on the news we're scoring. FinBERT is used as-is (no fine-tuning).

4. **Out-of-sample testing.** Train/explore on data before `2023-01-01`. Evaluate on `2023-01-01` onward.

5. **Transaction costs.** 5 basis points per side (10 bps round trip) on every simulated trade.

6. **Survivorship awareness.** Note delisted exclusions in README.

7. **Benchmark.** Always report vs SPY buy-and-hold.

8. **Statistical honesty.** Null results are fine and impressive when methodology is right.

---

## PHASE 1: Project scaffolding

**Goal:** Empty repo to a working dev environment.

**Tasks:**
1. `git init`. Add `.gitignore` for Python + Node + macOS + VS Code + `.env` + `data/raw/*` + `data/embeddings/*` + `data/processed/*.duckdb`.
2. Create the full directory structure above. Use `.gitkeep` files in empty data dirs.
3. `uv init`. Add base deps: `pandas`, `numpy`, `pyarrow`, `duckdb`, `yfinance`, `requests`, `scikit-learn`, `statsmodels`, `fastapi`, `uvicorn`, `python-dotenv`, `sentence-transformers`, `transformers`, `torch`, `ollama`, `joblib`. Dev: `ruff`, `pytest`, `jupyter`.
4. Frontend: `pnpm create vite frontend -- --template react-ts`, then add `tailwindcss`, `recharts`, `axios`.
5. `src/config.py`: path constants (RAW_DIR, PROCESSED_DIR, RESULTS_DIR, EMBEDDINGS_DIR, DUCKDB_PATH), plus model name constants (EMBED_MODEL, FINBERT_MODEL, OLLAMA_MODEL). All paths derived from a `PROJECT_ROOT` resolved relative to this file.
6. Makefile with stubs: `ingest`, `clean`, `nlp`, `features`, `research`, `backtest`, `api`, `frontend`, `all`. Each stub prints what it will do.
7. `.env.example` with: `OLLAMA_HOST=http://localhost:11434` and `OLLAMA_MODEL=llama3.1:8b`.
8. `README.md` with title, one-line description, "Status: In progress" badge.
9. Commit: `chore: initial scaffolding with local NLP stack`.

**Stop. Show tree. Wait for go.**

---

## PHASE 2a: Senate trade ingestion

**Goal:** Pull congressional trades from Senate Stock Watcher to `data/raw/senate_trades/`.

**Source:** Senate Stock Watcher public dataset. Try in order:
1. `https://senatestockwatcher.com/aggregate/all_transactions.json`
2. GitHub mirror: `https://raw.githubusercontent.com/jeremiak/senate-stock-watcher-data/master/aggregate/all_transactions.json`

Both free, no API key.

**Tasks:**
1. `src/ingest/congress.py`:
   - `fetch_senate_trades() -> pd.DataFrame` downloads JSON, parses, saves `data/raw/senate_trades/trades.parquet`
   - Required cols: `senator`, `ticker`, `transaction_date`, `disclosure_date`, `type` (buy/sell), `amount_range_low`, `amount_range_high`, `asset_type`
   - Filter to stocks only (skip bonds/options/crypto/funds — keep only rows where `asset_type` looks like a stock)
   - Print row count, date range, unique senators, unique tickers
2. CLI entry: `python -m src.ingest.congress`
3. Commit: `feat: ingest senate trade disclosures from senate stock watcher`

**Stop. Show counts. Wait for go.**

---

## PHASE 2b: Price ingestion

**Goal:** Pull daily OHLCV for every ticker the senators traded + SPY benchmark.

**Tasks:**
1. `src/ingest/prices.py`:
   - `fetch_prices(tickers: list[str], start: str, end: str)` pulls daily OHLCV via `yfinance.download()` in batches of 50
   - Always include SPY
   - One parquet per ticker at `data/raw/prices/{ticker}.parquet`
   - Handle delisted tickers gracefully (log and continue)
2. Load ticker universe from the trades parquet (Phase 2a) — don't hardcode
3. CLI entry: `python -m src.ingest.prices`
4. Commit: `feat: ingest daily prices via yfinance`

**Stop. Show count of successful vs failed tickers. Wait for go.**

---

## PHASE 2c: News ingestion

**Goal:** Pull a news headline corpus for the tickers in our universe.

**Source:** `yfinance.Ticker(symbol).news` — free, no key. Coverage is limited to recent news per ticker, so expect thinner coverage on older trades. Document this honestly.

**Tasks:**
1. `src/ingest/news.py`:
   - `fetch_news_for_tickers(tickers: list[str]) -> None` iterates universe, pulls available headlines per ticker via yfinance.
   - For each headline capture: `ticker`, `headline`, `summary` (if available), `publisher`, `published_at` (UTC ISO), `url`, `source`
   - Save to `data/raw/news/{ticker}.parquet`
   - Handle rate limits with a small `time.sleep(0.5)` between tickers
2. Print: total headlines, unique tickers covered, date range
3. CLI entry: `python -m src.ingest.news`
4. Commit: `feat: news ingestion via yfinance`

**Stop. Show stats. We'll adapt in features phase if coverage is thin.**

---

## PHASE 3: Clean + load (processed layer)

**Goal:** Raw parquet → unified DuckDB tables.

**Tasks:**
1. `src/clean/transform.py`:
   - Senate trades: uppercase tickers, parse dates, drop nulls on required fields, dedupe, validate `disclosure_date >= transaction_date` (drop violations and log count)
   - Prices: concat per-ticker parquets → long-format `(date, ticker, open, high, low, close, adj_close, volume)`
   - News: concat per-ticker parquets → long-format with proper UTC timestamps
   - Write all three to `data/processed/db.duckdb` as tables `trades`, `prices`, `news`
2. Create `senator_trade_universe` view: trades inner-joined to prices on ticker (surfaces trades we can actually analyze)
3. Sanity prints: row counts, date coverage, % of trades with at least one news headline before disclosure
4. Update Makefile `make clean`
5. Commit: `feat: clean and load to duckdb`

**Stop. Show sanity output. Wait for go.**

---

## PHASE 4: NLP layer — embeddings + cosine retrieval

**Goal:** For each trade, find the K most semantically similar news headlines published BEFORE its signal_date.

**Tasks:**
1. `src/nlp/embeddings.py`:
   - Load `sentence-transformers/all-MiniLM-L6-v2`
   - `embed_texts(texts: list[str]) -> np.ndarray` — batch encode, cache to disk under `data/embeddings/`
   - `find_similar_news(trade_row, news_df, k=5) -> pd.DataFrame`:
     - Filter news to: same ticker AND `published_at < trade.signal_date - 1 business day` (LOOKAHEAD GUARDRAIL)
     - Compute cosine similarity between trade context string and candidate headlines
     - Return top-k with similarity scores
   - Build "trade context string" from: `"{senator} {type}s {ticker} disclosed {disclosure_date}"`
2. Persist all embeddings (news + trade contexts) to parquet for reuse
3. Print: avg # of pre-disclosure news headlines available per trade, avg top-1 similarity
4. Update Makefile `make nlp` (Phase 4 portion)
5. Commit: `feat: sentence-transformer embeddings + cosine news retrieval`

  Dependencies added: `sentence-transformers`

**Stop. Show similarity stats. Wait for go.**

---

## PHASE 5: NLP layer — 3-tier classification cascade

**Goal:** Score every retrieved news headline with bullish/bearish/neutral sentiment using a cascade: Naive Bayes (fast bulk) → FinBERT (finance-tuned) → local LLM via Ollama (nuanced cases). **Fully local — no API calls.**

**Why a cascade:** Most headlines are obvious. Spend cheap compute on those, expensive compute only on ambiguous ones. This is a real engineering pattern that demonstrates cost-aware ML system design — a quant-shop value.

**Tasks:**
1. `src/nlp/classify_nb.py`:
   - Train a Multinomial Naive Bayes on Financial PhraseBank (`takala/financial_phrasebank` on HF, or download the CSV directly).
   - TF-IDF vectorizer + MultinomialNB pipeline (sklearn)
   - `classify_nb(texts: list[str]) -> list[{label, confidence}]`
   - Persist trained model to `data/processed/nb_model.joblib`
2. `src/nlp/classify_finbert.py`:
   - Load `ProsusAI/finbert` from HuggingFace
   - `classify_finbert(texts: list[str]) -> list[{label, confidence}]`
   - Batch inference (batch size 32 is fine)
3. `src/nlp/llm_local.py`:
   - Ollama client (use the `ollama` python package or raw HTTP to `OLLAMA_HOST`)
   - `classify_local(text: str) -> {label, confidence, reasoning}` — short prompt asking for bullish/bearish/neutral + 1-sentence reasoning. Parse JSON response.
   - If parse fails or Ollama is unreachable: return `{label: "neutral", confidence: 0.5, reasoning: "fallback"}` and log the failure.
4. `src/nlp/router.py`:
   - `classify_headline(text: str) -> {label, confidence, source}`:
     - Run NB. If `confidence > 0.85`, return NB result, source=`"nb"`
     - Else run FinBERT. If `confidence > 0.80`, return FinBERT, source=`"finbert"`
     - Else run local LLM (Ollama). Return its result, source=`"ollama"` (or `"fallback_neutral"` if Ollama failed)
   - Log which tier handled each call → save tier-usage stats to `data/results/nlp_routing.json`
5. Apply router across all news in the universe. Persist `data/processed/news_sentiment.parquet` with `(news_id, headline, label, confidence, source)`.
6. Update Makefile: `make nlp` runs embeddings AND classification
7. Commit: `feat: 3-tier nlp cascade (NB → FinBERT → Ollama)`

  Dependencies added: `transformers`, `torch`, `ollama`, `joblib`

**Stop. Show: tier distribution (% NB / FinBERT / Ollama / fallback), 10 sample classifications. Wait for go.**

---

## PHASE 6: Feature engineering

**Goal:** Build the feature table combining trade signals + NLP sentiment, with strict lookahead enforcement.

**Tasks:**
1. `src/features/build.py`:
   - For each trade compute:
     - `signal_date` = disclosure_date shifted to next business day
     - `entry_price` = open on signal_date
     - `fwd_return_5d`, `fwd_return_21d`, `fwd_return_63d` (close-to-close from signal_date)
     - `spy_fwd_return_*` same windows
     - `excess_return_*` = trade return minus SPY return
     - `disclosure_lag_days` = disclosure_date - transaction_date
     - `is_buy` boolean
   - NLP features per trade (using cosine + classified sentiment from Phase 4/5):
     - `news_count_30d`: # of news for this ticker in the 30 days BEFORE signal_date
     - `sentiment_score_30d`: mean signed sentiment of those news (bullish=+1, neutral=0, bearish=-1, weighted by confidence)
     - `top_news_similarity`: cosine sim of the top retrieved headline to the trade context
     - `top_news_sentiment`: sentiment label of the top retrieved headline
   - **CRITICAL:** every news feature must filter `news.published_at < trade.signal_date - 1 BDay`. Write this as an explicit SQL guard.
2. Save as DuckDB table `features` + export `data/processed/features.parquet`
3. Print: feature coverage (% of trades with non-null NLP features), summary stats
4. Update Makefile `make features`
5. Commit: `feat: feature engineering with lookahead-safe trade + nlp features`

**Stop. Show coverage + summary. Wait for go.**

---

## PHASE 7: Exploratory research

**Goal:** Answer the thesis with stats.

**Tasks:**
1. `src/research/eda.py` produces JSON to `data/results/eda/`:
   - `overview.json`: total trades, buys vs sells, mean excess return for each, t-stat, p-value
   - `by_senator.json`: top 20 senators by mean excess return on buys (n ≥ 10), with confidence intervals
   - `by_lag.json`: mean excess return bucketed by disclosure lag
   - `by_sentiment.json`: **the key chart** — mean 21d excess return on senator buys, bucketed by `sentiment_score_30d` quintile. This is what shows whether NLP adds info.
   - `nlp_routing.json` (from Phase 5): tier usage distribution
2. Use statsmodels for tests
3. Update Makefile `make research`
4. Commit: `feat: eda including nlp-conditional return analysis`

**Stop. Show overview and by_sentiment outputs. Wait for go.**

---

## PHASE 8: Backtest

**Goal:** Simulate two strategies and compare:
- **Baseline:** all senator buys, 21-day hold
- **NLP-filtered:** senator buys WHERE `sentiment_score_30d > 0` (positive news flow leading into the disclosure)

**Strategy rules:**
- Universe: senate buys with available NLP features
- Entry: open on signal_date
- Exit: close 21 trading days later
- Position sizing: equal-weight, max 20 concurrent positions; tie-break by lowest disclosure_lag
- Transaction cost: 5 bps per side (10 bps round trip)
- Capital: $100,000 starting, equal-weight across open positions
- Train/test split: train ≤ 2022-12-31, test ≥ 2023-01-01

**Tasks:**
1. `src/research/backtest.py`:
   - Run baseline AND NLP-filtered backtests on the test period
   - Equity curves vs SPY
   - Metrics: total return, annualized return, vol, Sharpe, max drawdown, hit rate, # trades
   - Output `data/results/backtest.json`:
     ```
     {
       baseline: {equity_curve, metrics, trades},
       nlp_filtered: {equity_curve, metrics, trades},
       spy: {equity_curve, metrics}
     }
     ```
2. Print metrics table comparing baseline vs NLP-filtered vs SPY
3. Update Makefile `make backtest`
4. Commit: `feat: backtest with nlp-filtered comparison vs baseline and spy`

**Stop. Show metrics. Wait for go.**

---

## PHASE 9: API

**Tasks:**
1. `src/api/main.py` endpoints:
   - `GET /api/overview` → eda/overview.json
   - `GET /api/senators` → eda/by_senator.json
   - `GET /api/sentiment-buckets` → eda/by_sentiment.json
   - `GET /api/nlp-routing` → results/nlp_routing.json
   - `GET /api/backtest` → backtest.json
   - `GET /api/trades/recent?n=50` → most recent 50 trades w/ NLP features
   - `GET /health` → `{status: "ok"}`
2. Enable CORS for `http://localhost:5173`
3. Update Makefile `make api`
4. Test each endpoint with curl, paste outputs
5. Commit: `feat: fastapi serving research + nlp results`

**Stop. Show curl outputs. Wait for go.**

---

## PHASE 10: Frontend

**Design rules (non-negotiable):**
- White/near-white bg, one accent color (sober blue or green)
- One font family (Inter), 2 weights max
- Generous whitespace
- Charts: minimal axes, clear titles, tooltips, no junk
- Show the NLP machinery — that's the differentiator

**Sections (single-page app):**
1. **Header:** title, one-line thesis, GitHub link
2. **Overview cards:** total trades, mean buy excess return, mean sell excess return, p-value
3. **NLP routing card:** stacked bar showing % of headlines handled by NB / FinBERT / Ollama (the "look how I engineered this" flex)
4. **Sentiment-bucket bar chart:** mean 21d excess return by sentiment quintile (this is the *finding*)
5. **Equity curve:** baseline strategy vs NLP-filtered vs SPY over test period
6. **Backtest metrics table:** side-by-side comparison
7. **Top senators table:** sortable
8. **Recent trades feed:** w/ top headline + sentiment for each
9. **Methodology section:** the lookahead handling (trades AND news), train/test split, transaction costs, NLP cascade rationale, limitations

**Tasks:**
1. `lib/api.ts`: typed axios fetchers
2. Components: `OverviewCards`, `NlpRoutingCard`, `SentimentBuckets`, `EquityCurveChart`, `MetricsTable`, `SenatorTable`, `RecentTrades`, `MethodologyNotes`
3. Wire into `App.tsx`
4. Tailwind only, no component library
5. Loading + error states on every fetch
6. Update Makefile `make frontend`
7. Commit: `feat: react dashboard with nlp visualizations`

**Stop. I'll run it locally.**

---

## PHASE 11: README + polish

**README order:**
1. One-line + GIF of dashboard
2. Thesis question
3. Key findings (3-5 brutally honest bullets — including null results if any)
4. **Architecture diagram** (ASCII or Mermaid) showing data flow through the NLP cascade
5. Methodology section (lookahead, train/test, costs, NLP cascade design)
6. Tech stack — emphasize "fully local, $0 to run"
7. How to run locally (numbered, `make ingest && make clean && make nlp && ...`)
8. Repo structure
9. Limitations + "what I'd do with more time"
10. Author + contact

**Tasks:**
1. Write README
2. Record 30-60s screen capture → GIF → add to README
3. Add `LICENSE` (MIT)
4. `ruff check --fix` + `ruff format` across `src/`
5. Final commit: `docs: complete readme and final polish`

**Done.**

---

## Anti-patterns to avoid

- Do not skip the lookahead enforcement on news features. Easy to get wrong, fatal if you do.
- Do not add an Anthropic/OpenAI API fallback. This project is fully local — that is a feature.
- Do not over-engineer the NLP cascade thresholds in v1. Hard-coded thresholds (0.85, 0.80) are fine. Document that they're heuristic.
- Do not train FinBERT from scratch or fine-tune it. Use the pretrained checkpoint as-is.
- Do not add user auth, real-time streaming, Docker, CI/CD, or deployment. Out of scope.
- Do not produce a 30-strategy comparison. Two strategies (baseline vs NLP-filtered), done well.
- Do not use Jupyter for production code — scratch only.

---

## Success criteria

A senior quant engineer reviewing the repo should think:
1. "This person handled lookahead bias on BOTH the trade and the news correctly."
2. "The NLP cascade is a real engineering pattern, not a buzzword salad."
3. "Fully local — they could run this airgapped, that's a real consideration for buy-side."
4. "The methodology section is honest about limitations."
5. "The dashboard is clean and the findings are clearly communicated."

Hit those five and the project succeeds regardless of whether the strategy turns out profitable.

Start with Phase 1. Stop after each phase. Wait for my go.
