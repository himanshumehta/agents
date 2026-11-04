from __future__ import annotations

import asyncio
import time

import pytest

from livekit import rtc
from livekit.agents import vad

from .test_commit_user_turn_vad import _drain, _final_event, _speech_frame, _start_session, _vad_event

pytestmark = pytest.mark.unit


async def test_noise_segment_then_spoken_segment_commit_latency() -> None:
    session, recognition, stream = await _start_session(manual_flush=False, use_vad=True)
    try:
        recognition._push_audio(_speech_frame())
        await _drain(stream, 1)
        await recognition._on_vad_event(_vad_event(vad.VADEventType.START_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.END_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.START_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.END_OF_SPEECH))
        await recognition._on_stt_event(_final_event("hello"))
        recognition._last_final_transcript_time -= 0.6
        recognition._last_speaking_time -= 0.6
        t0 = time.monotonic()
        transcript = await asyncio.wait_for(
            recognition._commit_user_turn(
                audio_detached=True, transcript_timeout=2.0, stt_flush_duration=0.2, skip_reply=True
            ),
            10,
        )
        print(f"\nRESULT transcript={transcript!r} commit_s={time.monotonic() - t0:.2f}")
    finally:
        await session.aclose()


async def test_second_final_in_flight_commit_result() -> None:
    session, recognition, stream = await _start_session(manual_flush=False, use_vad=True)
    try:
        recognition._push_audio(_speech_frame())
        await _drain(stream, 1)
        await recognition._on_vad_event(_vad_event(vad.VADEventType.START_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.END_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.START_OF_SPEECH))
        await recognition._on_vad_event(_vad_event(vad.VADEventType.END_OF_SPEECH))
        await recognition._on_stt_event(_final_event("hello"))
        recognition._last_final_transcript_time -= 0.6
        recognition._last_speaking_time -= 0.6
        t0 = time.monotonic()
        commit = recognition._commit_user_turn(
            audio_detached=True, transcript_timeout=2.0, stt_flush_duration=0.2, skip_reply=True
        )

        async def _late_final() -> None:
            await asyncio.sleep(0.3)
            await recognition._on_stt_event(_final_event("again"))

        late = asyncio.create_task(_late_final())
        transcript = await asyncio.wait_for(commit, 10)
        took = time.monotonic() - t0
        await late
        print(f"\nRESULT in-flight transcript={transcript!r} commit_s={took:.2f}")
    finally:
        await session.aclose()
