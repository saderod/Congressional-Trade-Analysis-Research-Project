.PHONY: ingest clean nlp features research backtest api frontend all

ingest:
	@echo "Will ingest senate trades, prices, and news into data/raw."

clean:
	uv run python -m src.clean.transform

nlp:
	uv run python -m src.nlp.embeddings
	uv run python -m src.nlp.router

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
