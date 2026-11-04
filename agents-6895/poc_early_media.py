from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import wave
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.getcwd())

from livekit import rtc
from livekit.agents import stt, vad
from livekit.agents.llm import FunctionToolCall
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS, APIConnectOptions
from livekit.agents.voice.amd import detector as amd_detector
from livekit.agents.voice.amd.detector import AMD
from livekit.plugins import silero
from tests.fake_llm import FakeLLM, FakeLLMResponse

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 16000
FRAME_MS = 20
GREETING_AT = 0.5
BEEP_AT = 6.9
BEEP_LEN = 0.5
ANSWER_AT = 12.0
END_AT = 24.0
GREETING_TEXT = (
    "Hi, you've reached Maria. I can't take your call right now. "
    "Please leave a message after the tone."
)

T0 = 0.0
EVENTS: list[dict] = []


def now() -> float:
    return round(time.monotonic() - T0, 3)


def log(kind: str, **kw: object) -> None:
    EVENTS.append({"t": now(), "kind": kind, **kw})


def build_call_audio() -> np.ndarray:
    with wave.open(os.path.join(HERE, "greeting.wav")) as w:
        greeting = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    total = np.zeros(int(END_AT * SR), dtype=np.int16)
    g0 = int(GREETING_AT * SR)
    total[g0 : g0 + len(greeting)] = greeting
    b0 = int(BEEP_AT * SR)
    t = np.arange(int(BEEP_LEN * SR)) / SR
    total[b0 : b0 + len(t)] = (8000 * np.sin(2 * np.pi * 1000 * t)).astype(np.int16)
    return total


class GreetingSTT(stt.STT):
    def __init__(self) -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=True, interim_results=False))

    async def _recognize_impl(self, buffer, *, language, conn_options):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def stream(
        self,
        *,
        language: object = None,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> GreetingStream:
        return GreetingStream(stt=self, conn_options=conn_options)


class GreetingStream(stt.RecognizeStream):
    async def _run(self) -> None:
        voiced = 0.0
        received = 0.0
        emitted = False
        async for data in self._input_ch:
            if not isinstance(data, rtc.AudioFrame):
                continue
            pcm = np.frombuffer(data.data, dtype=np.int16)
            dur = data.samples_per_channel / data.sample_rate
            if received == 0.0:
                log("stt_first_audio")
            received += dur
            if np.sqrt(np.mean(pcm.astype(np.float32) ** 2)) > 300:
                voiced += dur
            if not emitted and voiced >= 4.0:
                emitted = True
                log("stt_final", text=GREETING_TEXT)
                self._event_ch.send_nowait(
                    stt.SpeechEvent(
                        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                        alternatives=[stt.SpeechData(text=GREETING_TEXT, language="en")],
                    )
                )
        log("stt_audio_received", seconds=round(received, 2))


async def run(mode: str, session_stt: bool = False) -> dict:
    global T0
    answered = asyncio.Event()

    async def fake_wait_for_track_publication(**_: object) -> SimpleNamespace:
        return SimpleNamespace(sid="track_sid")

    async def fake_wait_for_participant_attribute(*_: object, **__: object) -> None:
        log("amd_waits_for_answer")
        await answered.wait()

    amd_detector.wait_for_track_publication = fake_wait_for_track_publication
    amd_detector.wait_for_participant_attribute = fake_wait_for_participant_attribute

    llm = FakeLLM(
        fake_responses=[
            FakeLLMResponse(
                input=GREETING_TEXT,
                content="",
                ttft=0.2,
                duration=0.4,
                tool_calls=[
                    FunctionToolCall(
                        name="save_prediction", arguments='{"label": "machine-vm"}', call_id="c1"
                    )
                ],
            )
        ]
    )
    publisher = SimpleNamespace(
        kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP,
        identity="callee",
        track_publications={"track_sid": object()},
    )
    session = SimpleNamespace(
        llm=None,
        options=SimpleNamespace(ivr_detection=False),
        _ivr_activity=None,
        _activity=None,
        _amd=None,
        _root_span_context=None,
        _session_host=None,
        _room_io=SimpleNamespace(room=SimpleNamespace(remote_participants={"callee": publisher})),
    )
    kwargs: dict = {}
    if mode == "opt-in":
        kwargs["wait_until_answered"] = False
    detector = AMD(
        session,  # type: ignore[arg-type]
        llm=llm,
        stt=None if session_stt else GreetingSTT(),
        participant_identity="callee",
        suppress_compatibility_warning=True,
        **kwargs,
    )
    verdict: dict = {}

    def on_prediction(ev: object) -> None:
        verdict.update(
            t=now(),
            category=getattr(getattr(ev, "category", ""), "value", str(getattr(ev, "category", ""))),
            reason=getattr(ev, "reason", ""),
        )
        log("verdict", category=verdict["category"], reason=verdict["reason"])

    detector.on("amd_prediction", on_prediction)

    audio = build_call_audio()
    onnx = os.environ.get("SILERO_ONNX")
    vad_model = (
        silero.VAD.load(min_silence_duration=0.55, onnx_file_path=onnx)
        if onnx
        else silero.VAD.load(min_silence_duration=0.55)
    )
    vad_stream = vad_model.stream()

    async def feed_vad() -> None:
        async for ev in vad_stream:
            if ev.type == vad.VADEventType.START_OF_SPEECH:
                log("vad_start")
                detector._on_user_speech_started()
            elif ev.type == vad.VADEventType.END_OF_SPEECH:
                log("vad_end")
                detector._on_user_speech_ended(ev.silence_duration)

    T0 = time.monotonic()
    log("call_start", call_status="ringing")
    vad_task = asyncio.create_task(feed_vad())
    await detector._run(session)  # type: ignore[arg-type]
    listening_logged = False
    session_text_sent = False
    step = int(SR * FRAME_MS / 1000)
    for i in range(0, len(audio), step):
        target = i / SR
        delay = target - (time.monotonic() - T0)
        if delay > 0:
            await asyncio.sleep(delay)
        if not answered.is_set() and target >= ANSWER_AT:
            log("call_answered", call_status="active")
            answered.set()
        if session_stt and not session_text_sent and target >= 5.3:
            session_text_sent = True
            log("session_stt_final", text=GREETING_TEXT)
            detector._on_transcript(GREETING_TEXT)
        chunk = audio[i : i + step]
        frame = rtc.AudioFrame(chunk.tobytes(), SR, 1, len(chunk))
        vad_stream.push_frame(frame)
        detector.push_audio(frame)
        if not listening_logged and detector._classifier and detector._classifier.listening:
            listening_logged = True
            log("amd_listening")
        if verdict:
            break
    await asyncio.sleep(0.3)
    vad_stream.end_input()
    await detector.aclose()
    vad_task.cancel()
    return {"mode": mode, "events": EVENTS, "verdict": verdict}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["default", "opt-in"])
    ap.add_argument("--label", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--session-stt", action="store_true")
    a = ap.parse_args()
    res = asyncio.run(run(a.mode, a.session_stt))
    res["label"] = a.label or a.mode
    json.dump(res, open(a.out, "w"), indent=1)
    v = res["verdict"]
    lst = next((e["t"] for e in res["events"] if e["kind"] == "amd_listening"), None)
    print(
        f"{res['label']:<44} listening from {lst if lst is not None else '-':>6} s   "
        f"verdict {v.get('category', 'none'):<26} at {v.get('t', '-')} s   reason={v.get('reason', '-')}"
    )


if __name__ == "__main__":
    main()
