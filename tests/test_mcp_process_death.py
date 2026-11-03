from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

from livekit.agents.llm.mcp import MCPServerStdio
from livekit.agents.llm.tool_context import ToolError

pytestmark = pytest.mark.unit

_HELPER = str(Path(__file__).parent / "utils" / "mcp_dying_server.py")


@pytest.mark.asyncio
async def test_real_subprocess_death_is_detected_and_reported_clearly() -> None:
    server = MCPServerStdio(command=sys.executable, args=[_HELPER])
    await server.initialize()
    try:
        tools = await server.list_tools()
        by_name = {t.info.name: t for t in tools}

        ping_result = await by_name["ping"]({})
        assert "pong" in ping_result

        client_task = server._client_task
        assert client_task is not None

        with pytest.raises(ToolError):
            await by_name["crash"]({})

        await asyncio.wait_for(client_task, timeout=5)
        assert not server.initialized

        with pytest.raises(ToolError, match="internal service is unavailable"):
            await by_name["ping"]({})
    finally:
        await server.aclose()
