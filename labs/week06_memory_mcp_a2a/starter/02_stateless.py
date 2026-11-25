"""Compare modern and legacy MCP requests in both HTTP server modes."""

from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import time
import urllib.error
import urllib.request

PORT_STATELESS = 8941
PORT_SESSION = 8942
MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"

# MCP revision 2026-07-28 carries client metadata on each request.
SELF_DESCRIBING = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {
        "_meta": {
            "io.modelcontextprotocol/protocolVersion": MODERN_VERSION,
            "io.modelcontextprotocol/clientInfo": {
                "name": "week06-wire-check",
                "version": "1.0",
            },
            "io.modelcontextprotocol/clientCapabilities": {},
        },
    },
}

LEGACY_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
}


def serve(port: int, stateless: bool) -> None:
    from mcp.server import MCPServer

    app = MCPServer("memory-desk")

    @app.tool()
    def recall(handle: str) -> list[str]:
        """Read back everything attached to a case handle."""
        return [f"notes for {handle}"]

    asyncio.run(app.run_streamable_http_async(
        host="127.0.0.1",
        port=port,
        stateless_http=stateless,
    ))


def raw_post(port: int, body: dict, version: str) -> tuple[int, dict[str, str], str]:
    """Send a raw HTTP request and keep the response status, headers, and body."""
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp",
        data=json.dumps(body).encode("utf-8"),
        # MCP revision 2026-07-28 mirrors request metadata in HTTP headers.
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": version,
            "Mcp-Method": "tools/list",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, dict(response.headers), response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, dict(exc.headers), exc.read().decode("utf-8")


def ask(stateless: bool, port: int, body: dict, version: str) -> dict:
    process = mp.Process(target=serve, args=(port, stateless), daemon=True)
    process.start()
    try:
        time.sleep(4)
        status, headers, response_body = raw_post(port, body, version)
        lower_headers = {name.lower(): value for name, value in headers.items()}
        return {
            "version": version,
            "stateless": stateless,
            "status": status,
            "session_id": lower_headers.get("mcp-session-id"),
            "answered": '"tools"' in response_body,
            "body": response_body,
        }
    finally:
        process.terminate()
        process.join()


def main() -> int:
    modern_stateless = ask(True, PORT_STATELESS, SELF_DESCRIBING, MODERN_VERSION)
    modern_session = ask(False, PORT_SESSION, SELF_DESCRIBING, MODERN_VERSION)
    legacy_stateless = ask(True, PORT_STATELESS, LEGACY_REQUEST, LEGACY_VERSION)
    legacy_session = ask(False, PORT_SESSION, LEGACY_REQUEST, LEGACY_VERSION)

    rows = (modern_stateless, modern_session, legacy_stateless, legacy_session)
    print(f"\n{'revision':<14}{'stateless_http':<18}{'status':>8}"
          f"{'Mcp-Session-Id':>36}{'answered':>10}")
    print("-" * 86)
    for row in rows:
        print(f"{row['version']:<14}{str(row['stateless']):<18}"
              f"{row['status']:>8}{str(row['session_id']):>36}"
              f"{str(row['answered']):>10}")

    print("\nLegacy session response:", legacy_session["body"])

    checks = {
        "modern request lists tools without a session header in both modes": all(
            row["status"] == 200 and row["answered"] and row["session_id"] is None
            for row in (modern_stateless, modern_session)
        ),
        "legacy stateless mode lists tools without a session header": (
            legacy_stateless["status"] == 200
            and legacy_stateless["answered"]
            and legacy_stateless["session_id"] is None
        ),
        "legacy session mode refuses a request without a session ID": (
            legacy_session["status"] == 400
            and not legacy_session["answered"]
            and "missing session id" in legacy_session["body"].casefold()
        ),
    }

    print()
    for name, passed in checks.items():
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    mp.set_start_method("spawn")
    raise SystemExit(main())