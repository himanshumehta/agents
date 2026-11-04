"""Half-open websocket probe for streaming STT plugins (halfopen_probe.py).

A local server accepts the websocket upgrade, then never sends anything and never
answers pings, like a provider (or a NAT in between) that vanished without FIN/RST.
The probe streams silence into the plugin and reports how long it takes to notice.

    python halfopen_probe.py openai elevenlabs inworld deepgram

No API keys or network access needed.
"""

import asyncio
import sys
import time

import aiohttp
from aiohttp import web

from livekit import rtc
from livekit.agents import APIConnectOptions
from livekit.agents.utils import http_context

WATCH = 75.0
PORT = 8765
URL = f"http://127.0.0.1:{PORT}"


async def silent_ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(autoping=False)  # never answer pings
    await ws.prepare(request)
    await asyncio.sleep(3600)  # never send anything
    return ws


def make_stt(name: str, http: aiohttp.ClientSession):
    if name == "openai":
        from livekit.plugins import openai

        return openai.STT(api_key="x", base_url=URL + "/v1", use_realtime=True)
    if name == "elevenlabs":
        from livekit.plugins import elevenlabs

        return elevenlabs.STT(api_key="x", base_url=URL + "/v1", http_session=http)
    if name == "inworld":
        from livekit.plugins import inworld

        return inworld.STT(api_key="x", base_url=URL + "/", http_session=http)
    if name == "deepgram":
        from livekit.plugins import deepgram

        return deepgram.STT(api_key="x", base_url=URL + "/v1/listen", http_session=http)
    raise ValueError(name)


async def probe(name: str) -> str:
    async with aiohttp.ClientSession() as http:
        stt = make_stt(name, http)
        stream = stt.stream(conn_options=APIConnectOptions(max_retry=0))
        frame = rtc.AudioFrame(
            data=b"\x00\x00" * 160, sample_rate=16000, num_channels=1, samples_per_channel=160
        )

        async def feed() -> None:
            while True:
                stream.push_frame(frame)
                await asyncio.sleep(0.01)

        async def consume() -> None:
            async for _ in stream:
                pass

        feeder = asyncio.create_task(feed())
        start = time.perf_counter()
        try:
            await asyncio.wait_for(consume(), WATCH)
            result = f"stream ended after {time.perf_counter() - start:.1f}s"
        except asyncio.TimeoutError:
            result = f"no error after {WATCH:.0f}s, still waiting"
        except Exception as e:
            result = f"{type(e).__name__} after {time.perf_counter() - start:.1f}s"
        feeder.cancel()
        try:
            await asyncio.wait_for(stream.aclose(), 5)
        except Exception:
            pass
        return result


async def main(names: list[str]) -> None:
    http_context._new_session_ctx()
    app = web.Application()
    app.router.add_route("GET", "/{tail:.*}", silent_ws)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "127.0.0.1", PORT).start()
    try:
        for name in names:
            print(f"{name:12s} {await probe(name)}", flush=True)
    finally:
        await runner.cleanup()
        await http_context._close_http_ctx()


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["openai", "elevenlabs", "inworld", "deepgram"]))
