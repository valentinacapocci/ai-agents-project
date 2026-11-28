import json
import select
import sys
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from pydantic import ValidationError
from typing_extensions import TypedDict

from project.trace import repo_root

from .extractor import ServiceRequest


class ApprovalState(TypedDict):
    payload: dict
    decision: dict


def approval_node(state: ApprovalState) -> dict:
    return {"decision": interrupt(state["payload"])}


def read_decision(payload: dict) -> dict:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    print("Type approve, reject, or edit {JSON fields}: ", end="", flush=True)
    if not select.select([sys.stdin], [], [], 300)[0]:
        return {"verdict": "timeout", "by": "system"}

    verdict, _, edits = sys.stdin.readline().strip().partition(" ")
    if verdict == "approve" and not edits:
        return {"verdict": "approve", "by": "operator"}
    if verdict == "edit":
        try:
            changes = json.loads(edits)
            if not isinstance(changes, dict):
                raise ValueError("Expected a JSON object")
            original = payload["arguments"]
            if changes.keys() - original.keys():
                raise ValueError("Unknown request field")
            record = ServiceRequest.model_validate({**original, **changes})
        except (ValueError, ValidationError) as exc:
            print(f"Edit rejected: {exc}")
        else:
            return {
                "verdict": "edit",
                "by": "operator",
                "arguments": record.model_dump(mode="json"),
            }

    return {"verdict": "reject", "by": "operator"}


def request_approval(payload: dict, unattended: bool = False) -> dict:
    if unattended or not sys.stdin.isatty():
        return {"verdict": "timeout", "by": "system"}

    builder = StateGraph(ApprovalState)
    builder.add_node("approval", approval_node)
    builder.add_edge(START, "approval")
    builder.add_edge("approval", END)

    path = repo_root() / "artifacts" / "app_approvals.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    config = {"configurable": {"thread_id": uuid4().hex}}

    with SqliteSaver.from_conn_string(str(path)) as saver:
        graph = builder.compile(checkpointer=saver)
        paused = graph.invoke({"payload": payload}, config)
        decision = read_decision(paused["__interrupt__"][0].value)
        result = graph.invoke(Command(resume=decision), config)
        return result["decision"]