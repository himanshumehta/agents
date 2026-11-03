from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import time
import wave

sys.path.insert(0, os.getcwd())

from livekit import rtc
from livekit.agents import Agent, AgentSession
from livekit.plugins import silero

from tests.fake_io import FakeAudioInput
from tests.fake_stt import FakeSTT, FakeUserSpeech

SR = 16000
FRAME = 160
EVIDENCE_DIR = sys.argv[1]
LABEL = sys.argv[2]
ONLY = sys.argv[3:]


def load_word(name: str) -> bytes:
    with wave.open(os.path.join(EVIDENCE_DIR, name + ".wav")) as f:
        return f.readframes(f.getnframes())


def silence(seconds: float) -> bytes:
    return b"\x00\x00" * int(SR * seconds)


def build(parts: list[tuple[str, object]]) -> tuple[bytes, dict[str, tuple[float, float]]]:
    pcm = b""
    spans: dict[str, tuple[float, float]] = {}
    for kind, value in parts:
        if kind == "sil":
            pcm += silence(float(value))
        else:
            start = len(pcm) / 2 / SR
            pcm += load_word(str(value))
            spans[str(value)] = (start, len(pcm) / 2 / SR)
    return pcm, spans


def frames_from(pcm: bytes) -> list[rtc.AudioFrame]:
    step = FRAME * 2
    out = []
    for i in range(0, len(pcm), step):
        chunk = pcm[i : i + step]
        if len(chunk) < step:
            chunk += b"\x00" * (step - len(chunk))
        out.append(rtc.AudioFrame(data=chunk, sample_rate=SR, num_channels=1, samples_per_channel=FRAME))
    return out


async def run(name: str, parts, delays: dict[str, float], commit_at: float, use_vad: bool) -> dict:
    pcm, spans = build(parts)
    speeches = [
        FakeUserSpeech(start_time=spans[w][0], end_time=spans[w][1], transcript=w, stt_delay=d)
        for w, d in delays.items()
    ]
    audio_in = FakeAudioInput()
    session = AgentSession(
        stt=FakeSTT(fake_user_speeches=speeches),
        vad=silero.VAD.load(onnx_file_path=os.path.join(EVIDENCE_DIR, "silero_vad.onnx")) if use_vad else None,
        turn_handling={"turn_detection": "manual"},
    )
    session.input.audio = audio_in
    events: list[tuple[float, str, str]] = []
    clock = {"t0": None}

    def now() -> float:
        return round(time.perf_counter() - clock["t0"], 2) if clock["t0"] else 0.0

    session.on("user_state_changed", lambda ev: events.append((now(), "vad", ev.new_state)))
    session.on(
        "user_input_transcribed",
        lambda ev: events.append((now(), "final" if ev.is_final else "interim", ev.transcript)),
    )
    await session.start(Agent(instructions="evidence"))

    frames = frames_from(pcm + silence(commit_at + 1.0))
    loop = asyncio.get_running_loop()
    clock["t0"] = time.perf_counter()
    start = loop.time()
    for i, frame in enumerate(frames):
        offset = i * FRAME / SR
        if offset >= commit_at:
            break
        delay = start + offset - loop.time()
        if delay > 0:
            await asyncio.sleep(delay)
        audio_in.push(frame)
    delay = start + commit_at - loop.time()
    if delay > 0:
        await asyncio.sleep(delay)

    session.input.set_audio_enabled(False)
    committed = now()
    c0 = time.perf_counter()
    try:
        text = await asyncio.wait_for(
            session.commit_user_turn(transcript_timeout=10.0, skip_reply=True), 20
        )
    except Exception as e:
        text = f"ERROR {type(e).__name__}: {e}"
    latency = round(time.perf_counter() - c0, 2)
    await session.aclose()
    return {
        "scenario": name,
        "code": LABEL,
        "transcript": text,
        "commit_latency_s": latency,
        "commit_at_s": committed,
        "speech": {w: [round(a, 2), round(b, 2)] for w, (a, b) in spans.items()},
        "events": events,
    }


SCENARIOS = {
    "reporter-timeline": dict(
        parts=[("sil", 0.3), ("word", "hello")],
        delays={"hello": 0.5},
        commit_at=2.27,
        use_vad=True,
    ),
    "two-segments-late-final": dict(
        parts=[("sil", 0.3), ("word", "hello"), ("sil", 0.6), ("word", "again")],
        delays={"hello": 2.03, "again": 3.4},
        commit_at=3.75,
        use_vad=True,
    ),
    "no-vad-reporter-timeline": dict(
        parts=[("sil", 0.3), ("word", "hello")],
        delays={"hello": 0.5},
        commit_at=2.27,
        use_vad=False,
    ),
}


async def main() -> None:
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    for name, cfg in SCENARIOS.items():
        if ONLY and name not in ONLY:
            continue
        result = await run(name, **cfg)
        result["sha"] = sha
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
