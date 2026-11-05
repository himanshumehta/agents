"""AgentServer.run deletes PROMETHEUS_MULTIPROC_DIR files that this process already holds open."""

import asyncio
import os
import socket
import tempfile
import urllib.request

# prometheus_client reads PROMETHEUS_MULTIPROC_DIR when it creates a metric value,
# so it must be set before any metric is written.
os.environ["PROMETHEUS_MULTIPROC_DIR"] = tempfile.mkdtemp(prefix="prom-mp-")
MP_DIR = os.environ["PROMETHEUS_MULTIPROC_DIR"]

import prometheus_client  # noqa: E402
from livekit.agents import AgentServer, JobContext, JobExecutorType  # noqa: E402

# An application metric written at startup, before the server runs
# (for example a warm-up step, or a THREAD executor app that registers its own metrics).
APP_GAUGE = prometheus_client.Gauge("app_warmup_done", "set once warm-up finishes")
APP_GAUGE.set(1)

print("files before run():", sorted(os.listdir(MP_DIR)))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def main() -> None:
    prom_port = free_port()
    server = AgentServer(
        job_executor_type=JobExecutorType.THREAD,
        num_idle_processes=0,
        host="127.0.0.1",
        port=free_port(),
        prometheus_port=prom_port,
    )

    @server.rtc_session()
    async def entrypoint(ctx: JobContext) -> None:
        pass

    # unregistered=True: no LiveKit server needed. The cleanup runs either way.
    run_task = asyncio.create_task(server.run(devmode=True, unregistered=True))
    await asyncio.sleep(2)  # several UPDATE_LOAD_INTERVAL (0.5 s) ticks of the load task

    APP_GAUGE.set(2)  # still writes to the unlinked mmap file
    print("files after run(): ", sorted(os.listdir(MP_DIR)))

    body = await asyncio.to_thread(
        lambda: urllib.request.urlopen(f"http://127.0.0.1:{prom_port}/metrics").read().decode()
    )
    names = sorted({l.split("{")[0].split(" ")[0] for l in body.splitlines() if l and not l.startswith("#")})
    print("/metrics series:   ", names)

    missing = [m for m in ("app_warmup_done", "lk_agents_worker_load") if m not in body]
    if missing:
        print(f"FAIL: missing from /metrics after AgentServer.run(): {missing}")
    else:
        print("PASS: application and worker metrics survive AgentServer.run()")

    await server.aclose()
    run_task.cancel()


asyncio.run(main())
