from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

from app.graph.build import build_graph  # noqa: E402  (needs env vars loaded first)
from app.graph.build_majors import build_majors_graph  # noqa: E402

app = FastAPI(title="TigerMind")
_graph = build_graph()
# Module-level singleton, same as _graph above -- a fresh build_majors_graph()
# per request would bind a fresh MemorySaver() each time and silently defeat
# checkpointing across calls.
_majors_graph = build_majors_graph()


class AskRequest(BaseModel):
    question: str
    domain: str


class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    confidence_ok: bool
    deferred: bool


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    result = _graph.invoke(
        {"question": request.question, "domain": request.domain}
    )
    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence_ok=result["confidence_ok"],
        deferred=result["deferred"],
    )


class MajorsMessageRequest(BaseModel):
    thread_id: str | None = None
    message: str


class MajorsResumeRequest(BaseModel):
    thread_id: str
    resume: str


class MajorsResponse(BaseModel):
    thread_id: str
    answer: str
    awaiting_confirmation: bool
    state_snapshot: dict


def _majors_response(thread_id: str, result: dict) -> MajorsResponse:
    return MajorsResponse(
        thread_id=thread_id,
        answer=result.get("answer") or "",
        awaiting_confirmation="__interrupt__" in result,
        state_snapshot={
            "target_major": result.get("target_major"),
            "interests": result.get("interests", []),
            "gpa": result.get("gpa"),
            "completed_courses": result.get("completed_courses", []),
        },
    )


@app.post("/majors/message", response_model=MajorsResponse)
def majors_message(request: MajorsMessageRequest) -> MajorsResponse:
    thread_id = request.thread_id or uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    result = _majors_graph.invoke(
        {"messages": [{"role": "user", "content": request.message}]}, config
    )
    return _majors_response(thread_id, result)


@app.post("/majors/resume", response_model=MajorsResponse)
def majors_resume(request: MajorsResumeRequest) -> MajorsResponse:
    config = {"configurable": {"thread_id": request.thread_id}}
    if not _majors_graph.get_state(config).next:
        raise HTTPException(
            status_code=400,
            detail="This thread isn't waiting on a confirmation.",
        )
    result = _majors_graph.invoke(Command(resume=request.resume), config)
    return _majors_response(request.thread_id, result)
