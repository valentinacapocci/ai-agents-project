"""Week 3 stretch A: compare both models with one routing policy."""

import argparse

from pydantic import ValidationError

from queries import QUERIES
from router import Decision, apply_policy, classify
from scoring import report, score_routes

from project.fixtures import ReplayClient
from project.models import API_KEY, BASE_URL, LARGE, SMALL

LAB = "week03_routing_and_composition"


def replay_decisions(client, model):
    """Replay the recorded classifier calls at temperature zero."""
    requests_by_text = {}
    for entry in client.records.values():
        request = entry["request"]
        if (
            request["model"] == model
            and request.get("temperature") == 0.0
            and request.get("response_format", {}).get("type") == "json_schema"
        ):
            requests_by_text[request["messages"][-1]["content"]] = request

    for query in QUERIES:
        reply = client.chat.completions.create(**requests_by_text[query.text])
        try:
            yield Decision.model_validate_json(reply.choices[0].message.content)
        except ValidationError:
            yield None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("model",), default="model")
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()

    if args.replay:
        client = ReplayClient.from_lab(LAB)
        print(f"Course recording: {client.meta['recorded_at']}")
    else:
        from openai import OpenAI

        client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
        print("Live run with the current router prompt", flush=True)

    for model in (SMALL, LARGE):
        if args.replay:
            decisions = replay_decisions(client, model.name)
        else:
            decisions = (
                classify(client, query.text, model.name)[0] for query in QUERIES
            )

        results = [
            apply_policy(decision, query.text)
            for query, decision in zip(QUERIES, decisions, strict=True)
        ]
        print(report(score_routes(results, QUERIES), model.name), flush=True)
        print(
            f"  resident memory: {model.resident_gb} GB (course measurement)\n",
            flush=True,
        )


if __name__ == "__main__":
    main()