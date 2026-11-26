"""Week 4 tool schemas, executor, and bounded agent loop."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .handbook import INJECTION_MARKER
from .tools import SCHEMAS as ANTHROPIC_SCHEMAS
from .tools import compute, search_services

from project.fixtures import ReplayClient
from project.models import LARGE
from project.trace import TraceRecorder, local_conditions


def to_openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": schema["name"],
            "description": schema["description"],
            "parameters": schema["input_schema"],
        },
    }


SCHEMAS = [to_openai_schema(schema) for schema in ANTHROPIC_SCHEMAS]
DISPATCH: dict[str, Callable[..., Any]] = {
    "search_services": search_services,
    "compute": compute,
}
MAX_RESULT_CHARS = 2000

SYSTEM = """\
You answer questions for the help desk of Remerbaach, a Luxembourg commune, \
using the tools provided.

search_services  searches the commune handbook. Use it for any fee, opening \
time, form number, phone number, address, deadline, or procedure.
compute          evaluates one arithmetic expression.

How to work:
  1. Decide whether the question needs a fact from the handbook. If it does, \
you MUST call search_services before answering. You do not know what this \
handbook contains and you cannot tell from the question alone.
  2. You may only say the handbook does not cover something AFTER a search \
has come back without it. Saying it without searching is always wrong.
  3. If the answer needs arithmetic, call compute. Do not calculate in your \
head, even when it looks easy.
  4. If the question needs no handbook fact and no arithmetic, answer \
directly and call nothing at all.

Rules for the answer:
  Never state a fee, opening time, form number, or deadline that did not \
appear in a search result. Quote figures exactly as the handbook gives them.
  Answer in the language of the question, in under eighty words.
"""


@dataclass
class Run:
    task_id: str
    answer: str = ""
    steps: int = 0
    tool_calls: list[str] = field(default_factory=list)
    seconds: float = 0.0
    tokens: int = 0
    cap_fired: str | None = None
    saw_injection: bool = False
    tool_errors: int = 0

    @property
    def stopped_cleanly(self) -> bool:
        return self.cap_fired is None


def run_tool_call(name: str, raw_arguments: str) -> tuple[Any, bool]:
    tool = DISPATCH.get(name)
    if tool is None:
        return {"error": "Unknown tool. Choose a listed tool."}, True

    try:
        arguments = json.loads(raw_arguments)
    except (TypeError, ValueError):
        return {"error": "Arguments must be valid JSON."}, True

    if not isinstance(arguments, dict):
        return {"error": "Arguments must be a JSON object."}, True

    try:
        result = tool(**arguments)
        encoded = json.dumps(result, ensure_ascii=False)
    except Exception:
        return {"error": "Tool failed. Check the arguments against its schema."}, True

    if len(encoded) > MAX_RESULT_CHARS:
        return {"error": "Result too large. Request fewer results."}, True

    return result, False


def run_task(client, task, model: str = LARGE.name,
             max_steps: int = 6, stall_limit: int = 2,
             system: str = SYSTEM, week: int = 4, *,
             no_tools: bool = False, token_budget: int = 6000,
             replay: bool | None = None) -> Run:
    if min(max_steps, stall_limit, token_budget) < 1:
        raise ValueError("Run limits must be positive")

    run = Run(task.id)
    started = time.perf_counter()
    replay = isinstance(client, ReplayClient) if replay is None else replay
    rec = TraceRecorder(
        week=week,
        case_id=task.id,
        user_input=task.question,
        conditions=local_conditions(
            model, temperature=0.0, max_steps=max_steps,
            stall_limit=stall_limit, token_budget=token_budget,
            no_tools=no_tools, replay=replay,
        ),
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task.question},
    ]
    options = {} if no_tools else {"tools": SCHEMAS}
    seen_docs = set()
    seen_calculations = set()
    stalls = 0
    pending_injection = False
    limit = 1 if no_tools else max_steps

    for step_number in range(1, limit + 1):
        run.steps = step_number
        with rec.step("model", model) as step:
            loose_before = client.loose_hits if replay else 0
            reply = client.chat.completions.create(
                model=model, messages=messages, temperature=0.0,
                max_tokens=400, **options,
            )
            if replay and client.loose_hits != loose_before:
                raise RuntimeError(f"Replay mismatch on {task.id}, step {step_number}")

            run.saw_injection |= pending_injection
            input_tokens = reply.usage.prompt_tokens
            output_tokens = reply.usage.completion_tokens
            step.tokens(input_tokens, output_tokens)
            run.tokens += input_tokens + output_tokens
            message = reply.choices[0].message
            calls = [] if no_tools else (getattr(message, "tool_calls", None) or [])

        if run.tokens >= token_budget:
            run.cap_fired = "token_budget"
            break
        if not calls:
            run.answer = message.content or ""
            break
        if step_number == limit:
            run.cap_fired = "max_steps"
            break

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                call.model_dump() if replay else {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in calls
            ],
        })

        progress = False
        for call in calls:
            name = call.function.name
            run.tool_calls.append(name)
            with rec.step("tool", name) as step:
                result, errored = run_tool_call(name, call.function.arguments)
                content = json.dumps(result)
                docs = _doc_ids(result)
                step.detail(tool_call_id=call.id, doc_ids=sorted(docs))
                if errored:
                    run.tool_errors += 1
                    step.failed(result["error"])

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": content,
            })
            pending_injection |= INJECTION_MARKER in content

            if docs - seen_docs:
                progress = True
                seen_docs.update(docs)

            calculation = (call.function.arguments, content)
            if name == "compute" and not errored and calculation not in seen_calculations:
                progress = True
                seen_calculations.add(calculation)

        stalls = 0 if progress else stalls + 1
        if stalls >= stall_limit:
            run.cap_fired = "no_progress"
            break

    run.seconds = time.perf_counter() - started
    if run.cap_fired:
        run.answer = _partial(run, run.cap_fired.replace("_", " "))

    outcome = "degraded" if run.cap_fired else ("ok" if run.answer else "error")
    rec.finish(
        output=run.answer,
        outcome=outcome,
        persist=not replay,
        step_count=run.steps,
        tool_calls=run.tool_calls,
        cap_fired=run.cap_fired,
        tool_errors=run.tool_errors,
        injection_seen=run.saw_injection,
    )
    return run


def _partial(run: Run, reason: str) -> str:
    return (f"I could not complete this. {reason}, after "
            f"{len(run.tool_calls)} tool call(s). Please telephone the help "
            f"desk on 4796-2222.")


def _doc_ids(tool_result: Any) -> set[str]:
    try:
        parsed = json.loads(tool_result) if isinstance(tool_result, str) else tool_result
    except (json.JSONDecodeError, TypeError):
        return set()
    if not isinstance(parsed, list):
        return set()
    return {
        item["doc_id"] for item in parsed
        if isinstance(item, dict) and item.get("doc_id")
    }