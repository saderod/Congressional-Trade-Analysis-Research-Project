.PHONY: ingest clean nlp features research backtest api frontend all

ingest:
	@echo "Will ingest senate trades, prices, and news into data/raw."

clean:
	@echo "Will clean raw parquet files and load processed tables into DuckDB."

nlp:
	@echo "Will run embeddings, retrieval, and sentiment classification."

features:
	@echo "Will build lookahead-safe trade and NLP feature tables."

research:
	@echo "Will generate EDA outputs and statistical summaries."

backtest:
	@echo "Will run baseline and NLP-filtered strategy backtests."

api:
	@echo "Will start the FastAPI service for research outputs."

frontend:
	@echo "Will start the React frontend dashboard."

all:
	@echo "Will run the full pipeline from ingest through frontend."

