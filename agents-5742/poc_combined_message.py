from __future__ import annotations

import asyncio
import json
import os
import sys

from google.genai import types

from livekit.agents import llm, utils
from livekit.plugins.google.realtime import RealtimeModel

LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"


class FakeGeminiSession:
    def __init__(self, owner, messages):
        self._owner = owner
        self._messages = messages

    async def receive(self):
        for m in self._messages:
            await asyncio.sleep(0.05)
            yield m
        self._owner._active_session = None

    async def close(self) -> None:
        return None


async def main() -> None:
    os.environ.setdefault("GOOGLE_API_KEY", "fake-key")
    rt = RealtimeModel().session()
    rt._msg_ch.close()
    await utils.aio.cancel_and_wait(rt._main_atask)

    restarts: list[str] = []
    rt._mark_restart_needed = lambda on_error=False: restarts.append(f"restart(on_error={on_error})")
    gens: list[llm.GenerationCreatedEvent] = []
    rt.on("generation_created", gens.append)

    pcm = b"\x00\x00" * 2400
    messages = [
        types.LiveServerMessage(
            server_content=types.LiveServerContent(
                model_turn=types.Content(
                    parts=[types.Part(inline_data=types.Blob(data=pcm, mime_type="audio/pcm;rate=24000"))]
                )
            )
        ),
        types.LiveServerMessage(
            server_content=types.LiveServerContent(turn_complete=True),
            tool_call=types.LiveServerToolCall(
                function_calls=[types.FunctionCall(id="fc-1", name="end_call", args={})]
            ),
        ),
    ]
    fake = FakeGeminiSession(rt, messages)
    rt._active_session = fake
    await rt._recv_task(fake)

    calls: list[str] = []
    if gens:
        async def drain() -> None:
            async for fc in gens[0].function_stream:
                calls.append(fc.name)

        await asyncio.wait_for(drain(), 2)
    err = rt._session_error
    result = {
        "label": LABEL,
        "generations": len(gens),
        "tool_calls_delivered": calls,
        "receive_task_error": type(err).__name__ if err else None,
        "restart": restarts,
    }
    print(
        f"{LABEL:<14} generations={len(gens)}  tool calls delivered={calls or '[]'}  "
        f"receive-task error={result['receive_task_error']}  reconnect={'yes' if restarts else 'no'}"
    )
    out = os.environ.get("POC_OUT")
    if out:
        json.dump(result, open(out, "w"), indent=1)
    await rt.aclose()


asyncio.run(main())
