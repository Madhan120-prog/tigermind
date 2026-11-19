"""The one LLM call site every agent in this project goes through.

Consolidates what used to be six copies of the same Anthropic-singleton
boilerplate (generic_domain_agent.py, router.py, majors_recommend.py,
majors_intake.py, synthesizer.py, eval/judge.py), and adds a temporary,
opt-in local fallback (Ollama) for when Anthropic credits aren't
available for development/testing -- see PLAN.md 17.x. LOCAL_LLM is
unset/false by default: the real, documented, production/CI/portfolio
stack is Anthropic, tiered by role (Haiku/Sonnet/Opus per PLAN.md
Section 14), exactly as before. The Ollama path is never reached unless
explicitly opted into, and it is not a substitute for Anthropic-based
verification -- a small local model is measurably weaker at the
structured-extraction and classification tasks this project relies on
(see PLAN.md 17.x for the specific, confirmed gaps). It exists only to
exercise code paths while credits are unavailable.
"""
import json
import os

import anthropic

LOCAL_LLM = os.environ.get("LOCAL_LLM", "").strip().lower() in ("1", "true", "yes")
LOCAL_LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "qwen2.5:7b-instruct")

_anthropic_client = None


def _get_anthropic_client() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _anthropic_client


class LLMResponse:
    """`.tool_input` is set when a `tool` schema was given, `.text`
    otherwise -- callers already know which one they asked for."""

    def __init__(self, text: str | None = None, tool_input: dict | None = None):
        self.text = text
        self.tool_input = tool_input


def complete(
    *, system: str, messages: list[dict], model: str, max_tokens: int, tool: dict | None = None
) -> LLMResponse:
    """model is a Claude model string (e.g. "claude-sonnet-4-5") and is
    ignored entirely on the Ollama path -- every call uses the one
    configured LOCAL_LLM_MODEL regardless of its normal tier, a known,
    accepted simplification for a temporary fallback, not a real
    per-call model choice.
    """
    if LOCAL_LLM:
        return _complete_ollama(system, messages, max_tokens, tool)
    return _complete_anthropic(system, messages, model, max_tokens, tool)


def _complete_anthropic(system: str, messages: list[dict], model: str, max_tokens: int, tool: dict | None) -> LLMResponse:
    kwargs = {}
    if tool is not None:
        kwargs["tools"] = [tool]
        kwargs["tool_choice"] = {"type": "tool", "name": tool["name"]}

    response = _get_anthropic_client().messages.create(
        model=model, max_tokens=max_tokens, system=system, messages=messages, **kwargs
    )

    if tool is not None:
        tool_input = next(block.input for block in response.content if block.type == "tool_use")
        return LLMResponse(tool_input=tool_input)
    return LLMResponse(text=response.content[0].text)


def _complete_ollama(system: str, messages: list[dict], max_tokens: int, tool: dict | None) -> LLMResponse:
    # Imported here, not at module level, so the normal Anthropic path
    # never needs the ollama package installed.
    import ollama

    ollama_messages = [{"role": "system", "content": system}, *messages]
    kwargs = {"options": {"num_predict": max_tokens}}
    # Ollama has no forced tool-choice (ollama.chat() takes no
    # tool_choice param at all) -- format=<json_schema> constrained
    # generation is the substitute, using the exact same schema each
    # tool already carries in its "input_schema".
    if tool is not None:
        kwargs["format"] = tool["input_schema"]

    response = ollama.chat(model=LOCAL_LLM_MODEL, messages=ollama_messages, **kwargs)
    content = response["message"]["content"]

    if tool is not None:
        return LLMResponse(tool_input=json.loads(content))
    return LLMResponse(text=content)
