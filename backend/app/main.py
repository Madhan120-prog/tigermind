from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv()

from app.graph.build import build_graph  # noqa: E402  (needs env vars loaded first)

app = FastAPI(title="TigerMind")
_graph = build_graph()


class AskRequest(BaseModel):
    question: str
    domain: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence_ok: bool


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = _graph.invoke(
        {"question": request.question, "domain": request.domain}
    )
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence_ok=result["confidence_ok"],
    )
