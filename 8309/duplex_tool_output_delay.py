from __future__ import annotations

import asyncio

import pytest

from livekit.agents import Agent, AgentSession, function_tool, llm

from ..fake_io import FakeAudioOutput
from ..test_duplex_adapter import FRAME_MS, _FakeDuplexModel, _FakeDuplexSession

pytestmark = pytest.mark.virtual_time

_FIXED_GATE_FLOOR = 0.002
_FILLER_RMS_LEVEL = 0.3
_FUNCTION_CALL_FRAME_INDEX = 2


def _instrument_function_call_output(
    fake: _FakeDuplexSession,
) -> asyncio.Future[float]:
    output_sent_at: asyncio.Future[float] = asyncio.get_event_loop().create_future()
    original_append_items = fake._append_items

    async def patched_append_items(items: list[llm.ChatItem]) -> None:
        await original_append_items(items)
        if not output_sent_at.done() and any(
            isinstance(item, llm.FunctionCallOutput) for item in items
        ):
            output_sent_at.set_result(asyncio.get_running_loop().time())

    fake._append_items = patched_append_items
    return output_sent_at


async def _measure_tool_output_delay(filler_seconds: float) -> float:
    model = _FakeDuplexModel()
    adapter = llm.DuplexRealtimeAdapter(model, gate=lambda: llm.FixedGate(_FIXED_GATE_FLOOR))

    tool_returned_at: asyncio.Future[float] = asyncio.get_event_loop().create_future()

    class ToolAgent(Agent):
        def __init__(self) -> None:
            super().__init__(instructions="", llm=adapter)

        @function_tool
        async def get_weather(self) -> str:
            tool_returned_at.set_result(asyncio.get_running_loop().time())
            return "sunny"

    async with AgentSession(llm=adapter, aec_warmup_duration=None) as session:
        session.output.audio = FakeAudioOutput()
        await session.start(ToolAgent())

        fake = model.session_obj
        assert fake is not None
        output_sent_at = _instrument_function_call_output(fake)

        frame_count = round(filler_seconds * 1000 / FRAME_MS)
        for frame_index in range(frame_count):
            fake.push(_FILLER_RMS_LEVEL, count=1)
            if frame_index == _FUNCTION_CALL_FRAME_INDEX:
                fake.emit(
                    "function_call",
                    llm.FunctionCall(call_id="call_1", name="get_weather", arguments="{}"),
                )
            await asyncio.sleep(FRAME_MS / 1000)

        resolved_output_sent_at = await asyncio.wait_for(
            output_sent_at, timeout=filler_seconds + 5.0
        )

    resolved_tool_returned_at = await asyncio.wait_for(tool_returned_at, timeout=1.0)
    return resolved_output_sent_at - resolved_tool_returned_at


async def test_tool_output_delay_scales_with_filler_length() -> None:
    filler_lengths = [1.0, 3.0]
    delays = [await _measure_tool_output_delay(length) for length in filler_lengths]

    print("\nfiller_length_s | tool_output_delay_s")
    for length, delay in zip(filler_lengths, delays, strict=True):
        print(f"{length:16.3f} | {delay:.3f}")

    for length, delay in zip(filler_lengths, delays, strict=True):
        assert delay > length, (
            f"tool output sent {delay:.3f}s after the tool returned, "
            f"expected it to exceed the {length:.1f}s filler length"
        )

    delay_delta = delays[1] - delays[0]
    length_delta = filler_lengths[1] - filler_lengths[0]
    assert abs(delay_delta - length_delta) < 0.05, (
        f"expected the delay to scale with the filler length "
        f"(delta {delay_delta:.3f}s vs filler delta {length_delta:.1f}s)"
    )
