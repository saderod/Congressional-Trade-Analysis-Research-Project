.PHONY: ingest clean nlp features research backtest api frontend all

ingest:
	uv run python -m src.ingest.congress
	uv run python -m src.ingest.prices
	uv run python -m src.ingest.news

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
	uv run python -m src.research.backtest

api:
	uv run uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	pnpm --dir frontend dev --host 127.0.0.1 --port 5173

all:
	$(MAKE) ingest
	$(MAKE) clean
	$(MAKE) nlp
	$(MAKE) features
	$(MAKE) research
	$(MAKE) backtest
