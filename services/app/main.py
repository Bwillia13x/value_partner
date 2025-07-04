from fastapi import FastAPI

app = FastAPI(
    title="Value Investing AI API",
    version="0.1.0",
    description="REST endpoints for the institutional-grade value-investing platform."
)


@app.get("/health", tags=["Utility"])
async def health_check():
    """Simple health-check endpoint for uptime monitoring."""
    return {"status": "ok"}