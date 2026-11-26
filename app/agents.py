from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput

from project.models import LARGE, pydantic_ai_model

from .tools import REGISTRY

MODEL_NAME = LARGE.name
MODEL = pydantic_ai_model(LARGE)
TOOL_NAMES = ", ".join(sorted(REGISTRY))


class Plan(BaseModel):
    goal: str
    steps: list[str]


class Verdict(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(max_length=200)


planner = Agent(
    MODEL,
    output_type=PromptedOutput(Plan),
    retries=3,
    system_prompt=(
        "Return one JSON object with a goal and a list of steps. "
        "Use only these tools: "
        f"{TOOL_NAMES}. "
        "Begin each step with the exact tool name followed by a colon. "
        'Example: {"goal":"Find the required form",'
        '"steps":["search_services: find the waste invoice form"]}'
    ),
)

reviewer = Agent(
    MODEL,
    output_type=PromptedOutput(Verdict),
    retries=3,
    system_prompt=(
        "Independently review the draft reply to the resident's question. "
        "Reject if it answers a different question or contradicts the "
        "supplied evidence. Reject clear errors even if the reply sounds "
        "plausible. When evidence is absent, check responsiveness and "
        "internal consistency. Do not claim you verified handbook facts. "
        "Return approve or reject with a reason of at most 200 characters."
    ),
)


def make_plan(question: str) -> Plan:
    return planner.run_sync(question).output


def validate_plan(plan: Plan) -> tuple[bool, list[str]]:
    problems = []
    if not 1 <= len(plan.steps) <= 6:
        problems.append("The plan must contain one to six steps.")

    for step in plan.steps:
        tool_name, separator, description = step.partition(":")
        if not separator or not description.strip() or tool_name.strip() not in REGISTRY:
            problems.append(f"Expected a registered tool and description: {step}")

    return not problems, problems


def review(question: str, answer: str, evidence: list[str]) -> Verdict | None:
    evidence_text = "\n".join(evidence) or "(none supplied)"
    return reviewer.run_sync(
        f"Resident question:\n{question}\n\n"
        f"Draft reply:\n{answer}\n\n"
        f"Available evidence:\n{evidence_text}"
    ).output