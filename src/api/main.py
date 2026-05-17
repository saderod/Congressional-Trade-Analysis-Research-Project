"""FastAPI application entry point."""

from fastapi import FastAPI


app = FastAPI(title="congressional-alpha")


@app.get("/health")
def health() -> dict[str, str]:
    """Return a basic health response."""
    return {"status": "ok"}

