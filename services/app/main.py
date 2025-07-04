from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

try:
    from services.app.copilot import CopilotRetriever

    retriever = CopilotRetriever()
except Exception as e:
    retriever = None


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answers: list[str]

app = FastAPI(
    title="Value Investing AI API",
    version="0.1.0",
    description="REST endpoints for the institutional-grade value-investing platform."
)


@app.get("/health", tags=["Utility"])
async def health_check():
    """Simple health-check endpoint for uptime monitoring."""
    return {"status": "ok"}

@app.post("/copilot/query", response_model=QueryResponse, tags=["Copilot"])
async def copilot_query(req: QueryRequest):
    if retriever is None:
        raise HTTPException(status_code=503, detail="Copilot not available")
    answers = retriever.query(req.question)
    return QueryResponse(answers=answers)