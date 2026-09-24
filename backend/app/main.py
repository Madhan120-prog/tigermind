from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

from app.graph.build_app import build_app_graph  # noqa: E402  (needs env vars loaded first)

app = FastAPI(title="TigerMind")
# Module-level singleton -- a fresh build_app_graph() per request would bind
# a fresh MemorySaver() each time and silently defeat checkpointing across
# calls sharing a thread_id.
_graph = build_app_graph()


class AskRequest(BaseModel):
    thread_id: str | None = None
    question: str


class AskResponse(BaseModel):
    thread_id: str
    answer: str
    sources: list[str]
    confidence_ok: bool
    deferred: bool
    awaiting_confirmation: bool
    confirmation_prompt: str | None = None
    draft_recommendation: dict | None = None
    state_snapshot: dict | None = None


def _majors_snapshot(result: dict) -> dict | None:
    # Only meaningful once the router has actually sent a turn into the
    # Majors flow -- a pure Tier-1 answer has no target_major/gpa to show.
    if result.get("route") != "majors":
        return None
    return {
        "target_major": result.get("target_major"),
        "interests": result.get("interests", []),
        "gpa": result.get("gpa"),
        "prereq_gpa": result.get("prereq_gpa"),
        "completed_courses": result.get("completed_courses", []),
    }


def _ask_response(thread_id: str, result: dict) -> AskResponse:
    # When paused mid-Majors-recommendation, "answer" is empty and the
    # actual confirmation question only lives in the interrupt payload --
    # a client that only sees awaiting_confirmation=True has nothing to
    # show the student before the next call resumes it.
    interrupts = result.get("__interrupt__")
    payload = interrupts[0].value if interrupts else None

    return AskResponse(
        thread_id=thread_id,
        answer=result.get("answer") or "",
        sources=result.get("sources", []),
        confidence_ok=result.get("confidence_ok", False),
        deferred=result.get("deferred", False),
        awaiting_confirmation=interrupts is not None,
        confirmation_prompt=payload.get("prompt") if payload else None,
        draft_recommendation=payload.get("draft") if payload else None,
        state_snapshot=_majors_snapshot(result),
    )


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    thread_id = request.thread_id or uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}

    # A thread currently paused on a Majors interrupt() treats the next
    # message as the answer to that confirmation, not a new turn -- so a
    # chat client never needs a second endpoint to resume one. This is the
    # same check /majors/resume used to make explicit.
    if _graph.get_state(config).next:
        result = _graph.invoke(Command(resume=request.question), config)
    else:
        result = _graph.invoke(
            {"messages": [{"role": "user", "content": request.question}], "question": request.question},
            config,
        )
    return _ask_response(thread_id, result)
