"""Week 6 take-home: a local A2A-style translation channel."""

import json
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

CARD = {"name": "translation-homework", "skills": [{"id": "translate"}]}
GLOSSARY = {"permit review scheduled": "examen du permis planifie"}


class TranslationAgent(BaseHTTPRequestHandler):
    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/.well-known/agent.json":
            self.send_json(200, CARD)
        else:
            self.send_json(404, {"error": "Unknown endpoint"})

    def do_POST(self):
        if self.path != "/tasks":
            self.send_json(404, {"error": "Unknown endpoint"})
            return

        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        task_id = payload["taskId"]
        text = payload["message"]["parts"][0]["text"]
        translation = GLOSSARY.get(text.strip().casefold())

        if translation is None:
            self.send_json(200, {
                "taskId": task_id, "state": "failed", "error": "No glossary match"
            })
            return

        self.send_json(200, {
            "taskId": task_id,
            "state": "completed",
            "artifact": {"parts": [{"text": translation}]},
        })


def delegate(base_url, skill, text):
    with urllib.request.urlopen(f"{base_url}/.well-known/agent.json", timeout=2) as response:
        card = json.load(response)

    if skill not in {item["id"] for item in card["skills"]}:
        return f"Handled locally: remote agent has no {skill!r} skill."

    task_id = uuid4().hex
    request = urllib.request.Request(
        f"{base_url}/tasks",
        data=json.dumps({
            "taskId": task_id,
            "message": {"parts": [{"text": text}]},
        }).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=2) as response:
        result = json.load(response)

    if result.get("taskId") != task_id:
        raise ValueError("Response task ID does not match the request.")
    if result["state"] == "failed":
        return f"Task failed: {result['error']}"
    if result["state"] != "completed":
        raise ValueError(f"Unexpected task state: {result['state']}")

    for part in result.get("artifact", {}).get("parts", []):
        if isinstance(part.get("text"), str):
            return part["text"]
    raise ValueError("Completed task returned no text artifact.")


if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 0), TranslationAgent) as server:
        base_url = f"http://127.0.0.1:{server.server_port}"
        worker = Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            print(delegate(base_url, "translate", "Permit review scheduled"))
            print(delegate(base_url, "summarize", "Permit review scheduled"))
            print(delegate(base_url, "translate", "Unknown phrase"))
        finally:
            server.shutdown()
            worker.join()