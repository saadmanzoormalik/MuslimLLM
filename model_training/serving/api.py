from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Muslim LLM Experimental Serving")
engine = None


class GenerateRequest(BaseModel):
    prompt: str
    max_new_tokens: int = 32


@app.get("/health")
def health(): return {"ok": True, "ready": engine is not None}


@app.post("/generate")
def generate(request: GenerateRequest):
    if engine is None: raise HTTPException(503, "Model is not loaded")
    return StreamingResponse(engine.stream(request.prompt, request.max_new_tokens), media_type="text/plain")

