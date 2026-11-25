"""Compare the three Week 5 architectures on Task B."""

from __future__ import annotations

import argparse
import asyncio
import time

from agents import baseline, propose, reviewer
from repo import Work, apply_fix, diff_summary, run_tests

from project.trace import TraceRecorder, local_conditions, write_json


TASK = (
    "Refactor discounts.py so the resident, off-peak, and club discounts "
    "and the total discount cap use the existing named constants instead "
    "of repeating their numeric values. Preserve behavior and all tests. "
    "The tests already pass at the start. Complete the refactor before "
    "using the tests to verify it."
)

EXPECTED_SUBSTITUTIONS = (
    "return RESIDENT_RATE if",
    "return OFF_PEAK_RATE if",
    "return CLUB_RATE if",
    "return min(total, MAX_TOTAL_DISCOUNT)",
)


def prepare_work(work: Work) -> None:
    """Apply the Task A fix to the temporary copy before measuring Task B."""
    applied = apply_fix(
        work,
        "discounts.py",
        "return start_hour > OFF_PEAK_FROM_HOUR",
        "return start_hour >= OFF_PEAK_FROM_HOUR",
    )
    if applied != "applied":
        raise RuntimeError(applied)

    result = run_tests(work)
    if not result.passed:
        raise RuntimeError(result.output)


def score_refactor(work: Work) -> dict:
    tests_passed = run_tests(work).passed
    source = work.read("discounts.py")
    constants_used = sum(
        substitution in source for substitution in EXPECTED_SUBSTITUTIONS
    )
    return {
        "tests_passed": tests_passed,
        "constants_used": constants_used,
        "green": tests_passed and constants_used == len(EXPECTED_SUBSTITUTIONS),
    }


def record(index: int, row: dict) -> None:
    architecture = row["architecture"]
    rec = TraceRecorder(
        week=5,
        case_id=f"task-b-{architecture}-run{index}",
        conditions=local_conditions(
            "qwen2.5:7b", temperature=0.0, architecture=architecture
        ),
        user_input=TASK,
    )
    with rec.step("check", "verify_refactor") as span:
        span.detail(**{key: str(value)[:200] for key, value in row.items()})
    rec.finish(
        output=str(row.get("fix") or ""),
        outcome="ok" if row["green"] else "error",
        **{key: str(value)[:300] for key, value in row.items()},
    )


async def run_baseline(index: int) -> dict:
    work = Work.fresh()
    try:
        prepare_work(work)
        started = time.perf_counter()
        calls = 0
        tokens = None
        error = None

        try:
            result = await baseline.run(TASK, deps=work)
            calls = sum(
                1 for message in result.all_messages() for part in message.parts
                if getattr(part, "tool_name", None)
            )
            tokens = result.usage.total_tokens
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        row = {
            "architecture": "A baseline",
            **score_refactor(work),
            "tool_calls": calls,
            "tokens": tokens,
            "seconds": round(time.perf_counter() - started, 1),
            "error": error,
        }
        record(index, row)
        return row
    finally:
        work.cleanup()


async def run_planned(index: int, with_reviewer: bool) -> dict:
    work = Work.fresh()
    try:
        prepare_work(work)
        started = time.perf_counter()
        architecture = "C planner+reviewer" if with_reviewer else "B planner"
        proposal = {}
        fix = None
        verdict = None
        applied = "not attempted"
        tokens = None
        error = None

        try:
            proposal = await propose(work, TASK, use_plan=True)
            fix = proposal["fix"]
            tokens = proposal["tokens"]

            if fix is None:
                applied = "plan rejected"
            else:
                if with_reviewer:
                    diff = diff_summary(work, fix.path, fix.old_line, fix.new_line)
                    result = await reviewer.run(
                        f"Task:\n{TASK}\n\nProposed change:\n{diff}"
                    )
                    verdict = result.output
                    tokens += result.usage.total_tokens

                if verdict is None or verdict.decision == "approve":
                    applied = apply_fix(work, fix.path, fix.old_line, fix.new_line)
                else:
                    applied = "reviewer rejected"

        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            tokens = None

        row = {
            "architecture": architecture,
            **score_refactor(work),
            "plan_ok": proposal.get("plan_ok"),
            "plan_problems": proposal.get("plan_problems", []),
            "applied": applied,
            "verdict": verdict.decision if verdict else None,
            "verdict_reason": verdict.reason if verdict else None,
            "fix": (
                f"{fix.path}: {fix.old_line.strip()} -> {fix.new_line.strip()}"
                if fix is not None else None
            ),
            "tokens": tokens,
            "seconds": round(time.perf_counter() - started, 1),
            "error": error,
        }
        record(index, row)
        return row
    finally:
        work.cleanup()


async def main_async(runs: int) -> list[dict]:
    rows = []
    for index in range(1, runs + 1):
        print(f"\nTask B round {index}/{runs}", flush=True)
        rows.append(await run_baseline(index))
        rows.append(await run_planned(index, with_reviewer=False))
        rows.append(await run_planned(index, with_reviewer=True))

        for row in rows[-3:]:
            print(
                f"{row['architecture']}: tests_passed={row['tests_passed']}, "
                f"constants_used={row['constants_used']}/4, "
                f"complete={row['green']}, tokens={row['tokens']}, "
                f"seconds={row['seconds']}",
                flush=True,
            )
            if row["error"]:
                print(f"  {row['error']}", flush=True)

        write_json("artifacts/week05_refactor.json", {"rows": rows})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    rows = asyncio.run(main_async(args.runs))
    print("\nTask B summary")
    for architecture in ("A baseline", "B planner", "C planner+reviewer"):
        group = [row for row in rows if row["architecture"] == architecture]
        completed = sum(row["green"] for row in group)
        average_seconds = sum(row["seconds"] for row in group) / len(group)
        token_counts = [row["tokens"] for row in group if row["tokens"] is not None]
        average_tokens = (
            f"{sum(token_counts) / len(token_counts):.0f}"
            if token_counts else "n/a"
        )
        print(
            f"{architecture}: {completed}/{len(group)} complete, "
            f"{average_tokens} avg tokens ({len(token_counts)}/{len(group)} measured), "
            f"{average_seconds:.1f} avg seconds"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())