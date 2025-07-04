from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from services.app.license import LicenseMiddleware
from services.app.plugins import PLUGINS
from services.app.valuation_routes import router as valuation_router
from services.app.special_routes import router as special_router

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

# Attach license middleware
app.add_middleware(LicenseMiddleware)


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


# ----------------- Marketplace Plugin Endpoints -----------------


@app.get("/plugins", tags=["Marketplace"])
async def list_plugins():
    return {"available_plugins": list(PLUGINS.keys())}


class PluginRequest(BaseModel):
    plugin: str
    payload: dict


@app.post("/plugins/run", tags=["Marketplace"])
async def run_plugin(req: PluginRequest):
    if req.plugin not in PLUGINS:
        raise HTTPException(status_code=404, detail="Plugin not found")
    try:
        result = PLUGINS[req.plugin](req.payload)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(valuation_router)
app.include_router(special_router)