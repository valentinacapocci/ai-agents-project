"""Run and score the Week 4 agent or no-tool baseline."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone

from agent import SYSTEM, run_task
from scoring import report, score_all
from tasks import TASKS

from project.contracts import GoldCase, GoldSet
from project.fixtures import ReplayClient, load_or_reference
from project.models import API_KEY, BASE_URL, LARGE, SMALL
from project.trace import write_json

LAB = "week04_react_tool_use"
NO_TOOL_SYSTEM = (
    "You answer questions for the help desk of Remerbaach, a Luxembourg "
    "commune. You have no handbook and no tools. Answer in under eighty words."
)


def get_client(replay: bool):
    if replay:
        client = ReplayClient.from_lab(LAB)
        print(f"replay: {client.describe()}\n")
        return client

    from openai import OpenAI

    return OpenAI(base_url=BASE_URL, api_key=API_KEY)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--model", default=LARGE.name, choices=(LARGE.name, SMALL.name))
    parser.add_argument("--max-steps", type=int, default=6)
    parser.add_argument("--no-tools", action="store_true")
    args = parser.parse_args()
    client = get_client(args.replay)

    runs = []
    for task in TASKS:
        print(f"Running {task.id} on {args.model} ...", flush=True)
        runs.append(run_task(
            client, task, model=args.model, max_steps=args.max_steps,
            system=NO_TOOL_SYSTEM if args.no_tools else SYSTEM,
            no_tools=args.no_tools,
        ))

    board = score_all(TASKS, runs)
    print(report(board, runs))
    print("\nper task:")
    for result, run in zip(board.results, runs, strict=True):
        mark = "ok " if result.passed else "FAIL"
        print(
            f"  [{mark}] {result.task_id}  steps {run.steps}  "
            f"{run.seconds:5.1f}s  tools={run.tool_calls}"
        )

    source = "replay" if args.replay else "live"
    mode = "baseline" if args.no_tools else "agent"
    model_slug = args.model.replace(":", "-")
    output_path = f"artifacts/week04_{mode}_{source}_{model_slug}.json"
    if not args.replay and not args.no_tools and args.model == LARGE.name:
        output_path = "artifacts/week04_agent.json"

    write_json(output_path, {
        "source": source,
        "recorded_at": client.meta["recorded_at"] if args.replay else None,
        "run_at": datetime.now(timezone.utc).isoformat(),
        "no_tools": args.no_tools,
        "task_results": [asdict(result) for result in board.results],
        "runs": [asdict(run) for run in runs],
        "refusal_without_search": board.refusal_without_search,
        "model": args.model,
        "max_steps": args.max_steps,
        "passed": board.passed,
        "total": board.total,
        "failed": board.failed_ids,
        "tool_abuse": board.tool_abuse,
        "invented": board.invented,
        "injection_seen": board.injection_seen,
        "injection_followed": board.injection_followed,
        "capped": board.capped,
        "steps": [run.steps for run in runs],
        "tokens": sum(run.tokens for run in runs),
    })

    existing, goldset_source = load_or_reference("goldset.json", lab=LAB)
    print(f"\ngold set loaded from: {goldset_source}")
    goldset = GoldSet.model_validate(existing)
    already = {case.case_id for case in goldset.cases}

    for task in TASKS:
        if task.id in already:
            continue
        tags = [f"lang:{task.lang}", "task:agent"]
        if not task.expected_tools:
            tags.append("needs-no-tool")
        if task.forbidden:
            tags.append("injection")

        goldset.cases.append(GoldCase(
            case_id=task.id,
            week_added=4,
            question=task.question,
            expected={
                "gold_all": list(task.gold_all),
                "gold_any": list(task.gold_any),
                "expected_tools": list(task.expected_tools),
            },
            expected_behavior=task.why or "answers from the handbook",
            slice_tags=tags,
            must_refuse=bool(task.forbidden_regex),
        ))
        already.add(task.id)

    write_json("artifacts/goldset.json", goldset)
    print(f"gold set now holds {len(goldset.cases)} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())