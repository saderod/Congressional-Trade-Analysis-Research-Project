.PHONY: ingest clean nlp features research backtest api frontend all

ingest:
	@echo "Will ingest senate trades, prices, and news into data/raw."

clean:
	uv run python -m src.clean.transform

nlp:
	uv run python -m src.nlp.embeddings
	uv run python -m src.nlp.ensemble

features:
	uv run python -m src.features.build

research:
	uv run python -m src.research.eda

backtest:
	@echo "Will run baseline and NLP-filtered strategy backtests."

api:
	@echo "Will start the FastAPI service for research outputs."

frontend:
	@echo "Will start the React frontend dashboard."

all:
	@echo "Will run the full pipeline from ingest through frontend."
