"""Block 2, first half: call the memory tools over MCP. TODO 6.

    python mcp_server.py &          # in one terminal
    PORT=8001 python mcp_server.py & # and a second instance
    python 01_mcp_client.py

Three things happen here and the third is the one to watch.
"""

from __future__ import annotations

import os
import asyncio

from mcp.client import Client

SUBJECT = "A. Muller"


def text_of(result) -> str:
    content = getattr(result, "content", result)
    if isinstance(content, list) and content:
        return getattr(content[0], "text", str(content[0]))
    return str(content)


async def call(port: int, tool: str, **args):
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        return await client.call_tool(tool, args)


async def main() -> int:
    """TODO 6. Three steps, and the third has a warning attached.

    1. Connect to :8000 and print the tool catalog. Seeing it arrive over
       HTTP is what makes the boundary real: these tools are not in this
       process.

    2. Call open_case and then remember on :8000. Watch
       artifacts/memory_store.json change while it runs.

    3. Redeem the SAME handle on :8001, the second instance, and recall from
       it.

    The warning: step 3 on its own does not prove the protocol is stateless.
    It would work under the old session-based protocol too, because each
    call opens its own connection and the state is on disk. It shows that a
    file is a file. 02_stateless.py is the demonstration that actually
    distinguishes the two, and it is the next thing you run.
    """
    async with Client("http://127.0.0.1:8000/mcp") as client:
        catalog = await client.list_tools()
        names = sorted(tool.name for tool in getattr(catalog, "tools", catalog))
        print("Tools on 8000:", ", ".join(names))

    case_handle = text_of(await call(8000, "open_case", subject=SUBJECT))
    assert case_handle.startswith("case-"), case_handle
    print("Case opened on 8000:", case_handle)

    fact = "Permit review scheduled"
    fact_handle = text_of(await call(
        8000, "remember", subject=SUBJECT, kind="status", fact=fact
    ))
    assert fact_handle.startswith("fact-"), fact_handle
    print("Fact saved on 8000:", fact_handle)

    denied = await call(8001, "case_subject", handle=case_handle)
    denial = text_of(denied)
    assert "Case access denied" in denial, denial
    print("Case lookup without a key: denied")

    subject = text_of(await call(
        8001, "case_subject",
        handle=case_handle,
        access_key=os.environ["WEEK6_CASE_KEY"],
    ))
    assert subject == SUBJECT, subject
    print("Same case resolved on 8001:", subject)

    recalled = text_of(await call(8001, "recall", subject=subject, query="permit"))
    assert fact in recalled, recalled
    print("Fact recalled on 8001:", recalled)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
