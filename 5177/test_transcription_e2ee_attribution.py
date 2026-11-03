from __future__ import annotations

import asyncio
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import pytest

from livekit import rtc
from livekit.agents.types import TOPIC_TRANSCRIPTION

from .utils.livekit_test import ServerConfig, connect_room, make_room_name, wait_for_event

pytestmark = [pytest.mark.unit, pytest.mark.concurrent]

TIMEOUT = 10.0


def _alloc_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class _Srv:
    config: ServerConfig = field(default_factory=lambda: ServerConfig("", "", ""))


_srv = _Srv()


@pytest.fixture(scope="module")
def livekit_server():
    http_port = _alloc_port()
    rtc_tcp = _alloc_port()
    udp_start = http_port + 100
    udp_end = udp_start + 20
    cmd = (
        [
            "livekit-server",
            "--dev",
            "--port",
            str(http_port),
            "--rtc.tcp_port",
            str(rtc_tcp),
            "--rtc.udp_port.start",
            str(udp_start),
            "--rtc.udp_port.end",
            str(udp_end),
        ]
        if platform.system() == "Darwin"
        else [
            "docker",
            "run",
            "--rm",
            "--network",
            "host",
            "livekit/livekit-server",
            "--dev",
            "--port",
            str(http_port),
            "--rtc.tcp_port",
            str(rtc_tcp),
            "--rtc.udp_port.start",
            str(udp_start),
            "--rtc.udp_port.end",
            str(udp_end),
        ]
    )
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    req = urllib.request.Request(f"http://127.0.0.1:{http_port}", method="HEAD")
    deadline = time.monotonic() + 15.0
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(req, timeout=0.5):
                break
        except urllib.error.HTTPError:
            break
        except (urllib.error.URLError, OSError):
            time.sleep(0.3)
    _srv.config = ServerConfig(
        url=f"ws://localhost:{http_port}", api_key="devkey", api_secret="secret"
    )
    try:
        yield
    finally:
        proc.terminate()
        proc.wait(timeout=10)


@contextmanager
def _recv_ctx(room: rtc.Room) -> Iterator[asyncio.Future[tuple[str, str]]]:
    fut: asyncio.Future[tuple[str, str]] = asyncio.get_running_loop().create_future()
    consume_tasks: list[asyncio.Task[None]] = []

    def _handler(reader: rtc.TextStreamReader, identity: str) -> None:
        async def _consume() -> None:
            text = await reader.read_all()
            if not fut.done():
                fut.set_result((identity, text))

        consume_tasks.append(asyncio.ensure_future(_consume()))

    room.register_text_stream_handler(TOPIC_TRANSCRIPTION, _handler)
    try:
        yield fut
    finally:
        room.unregister_text_stream_handler(TOPIC_TRANSCRIPTION)


async def _publish_on_behalf(room: rtc.Room, *, sender_identity: str, text: str) -> None:
    writer = await room.local_participant.stream_text(
        topic=TOPIC_TRANSCRIPTION, sender_identity=sender_identity
    )
    await writer.write(text)
    await writer.aclose()


async def _wait_for_peer(room: rtc.Room, identity: str) -> None:
    if identity not in room.remote_participants:
        await wait_for_event(
            room,
            "participant_connected",
            timeout=TIMEOUT,
            predicate=lambda p: p.identity == identity,
        )


@pytest.mark.usefixtures("livekit_server")
class TestTranscriptionE2EEAttribution:
    async def test_sender_identity_preserved_without_e2ee(self):
        name = make_room_name("attr-plain")
        async with (
            connect_room("user", name, config=_srv.config) as user,
            connect_room("agent", name, agent=True, config=_srv.config) as agent,
        ):
            await _wait_for_peer(user, "agent")
            with _recv_ctx(user) as recv_fut:
                await _publish_on_behalf(agent, sender_identity="user", text="hello")
                identity, text = await asyncio.wait_for(recv_fut, timeout=TIMEOUT)
        assert identity == "user"
        assert text == "hello"

    @pytest.mark.xfail(
        strict=True,
        reason="upstream: server overrides sender identity on EncryptedPacket, livekit/agents#5177",
    )
    async def test_sender_identity_overridden_with_shared_key_e2ee(self):
        name = make_room_name("attr-e2ee-shared")
        options = rtc.RoomOptions(
            encryption=rtc.E2EEOptions(
                key_provider_options=rtc.KeyProviderOptions(shared_key=b"repro")
            )
        )
        async with (
            connect_room("user", name, options=options, config=_srv.config) as user,
            connect_room("agent", name, agent=True, options=options, config=_srv.config) as agent,
        ):
            await _wait_for_peer(user, "agent")
            with _recv_ctx(user) as recv_fut:
                await _publish_on_behalf(agent, sender_identity="user", text="hello")
                identity, text = await asyncio.wait_for(recv_fut, timeout=TIMEOUT)
        assert identity == "user"
        assert text == "hello"

    @pytest.mark.xfail(
        strict=True,
        reason="upstream: server overrides sender identity on EncryptedPacket, livekit/agents#5177",
    )
    async def test_sender_identity_overridden_with_per_participant_keys_e2ee(self):
        name = make_room_name("attr-e2ee-perp")
        options = rtc.RoomOptions(encryption=rtc.E2EEOptions())
        async with (
            connect_room("user", name, options=options, config=_srv.config) as user,
            connect_room("agent", name, agent=True, options=options, config=_srv.config) as agent,
        ):
            agent_key = b"agent-only-key-00"
            agent.e2ee_manager.key_provider.set_key("agent", agent_key, 0)
            user.e2ee_manager.key_provider.set_key("agent", agent_key, 0)
            await _wait_for_peer(user, "agent")
            with _recv_ctx(user) as recv_fut:
                await _publish_on_behalf(agent, sender_identity="user", text="hello")
                identity, text = await asyncio.wait_for(recv_fut, timeout=TIMEOUT)
        assert identity == "user"
        assert text == "hello"
