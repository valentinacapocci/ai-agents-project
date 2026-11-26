import argparse

from project.models import EMBED
from project.trace import TraceRecorder, local_conditions

from .memory import MemoryStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", required=True)
    parser.add_argument("query")
    args = parser.parse_args()

    store = MemoryStore.load()
    trace = TraceRecorder(
        week=7,
        case_id="week07-app-retrieval",
        conditions=local_conditions(EMBED.name, size=600, overlap=80, k=3),
        user_input=args.query,
    )

    with trace.step("retrieval", "memory.search") as step:
        hits = store.search(args.subject, args.query)
        step.detail(hits=len(hits))

    trace.finish(output=f"{len(hits)} hits", outcome="ok")
    for hit in hits:
        print(f"\n{hit}")
    print(f"\nmemory.search: {len(hits)} hits")


if __name__ == "__main__":
    main()