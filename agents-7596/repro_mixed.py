import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

os.environ["PROMETHEUS_MULTIPROC_DIR"] = tempfile.mkdtemp(prefix="prom-mp-")
MP_DIR = os.environ["PROMETHEUS_MULTIPROC_DIR"]

CHILD = """
import os, sys, time, prometheus_client
g = prometheus_client.Gauge(sys.argv[1], "x")
g.set(7)
c = prometheus_client.Counter(sys.argv[1] + "_c", "x")
c.inc()
print(os.getpid(), flush=True)
if sys.argv[2] == "stay":
    time.sleep(60)
"""

dead = subprocess.run([sys.executable, "-c", CHILD, "dead_proc_gauge", "exit"], capture_output=True, text=True)
dead_pid = int(dead.stdout.strip())
live = subprocess.Popen([sys.executable, "-c", CHILD, "live_sibling_gauge", "stay"], stdout=subprocess.PIPE, text=True)
live_pid = int(live.stdout.readline().strip())

import prometheus_client  # noqa: E402
from livekit.agents import AgentServer, JobContext, JobExecutorType  # noqa: E402

APP_GAUGE = prometheus_client.Gauge("app_warmup_done", "set once warm-up finishes")
APP_GAUGE.set(1)
me = os.getpid()


def owner(name):
    pid = int(name.rsplit("_", 1)[1].split(".")[0])
    return {me: "self", dead_pid: "dead", live_pid: "live"}.get(pid, str(pid))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def main():
    before = sorted(f"{owner(f)}:{f.rsplit('_', 1)[0]}" for f in os.listdir(MP_DIR))
    prom_port = free_port()
    server = AgentServer(job_executor_type=JobExecutorType.THREAD, num_idle_processes=0,
                         host="127.0.0.1", port=free_port(), prometheus_port=prom_port)

    @server.rtc_session()
    async def entrypoint(ctx: JobContext) -> None:
        pass

    run_task = asyncio.create_task(server.run(devmode=True, unregistered=True))
    await asyncio.sleep(2)
    APP_GAUGE.set(2)
    after = sorted(f"{owner(f)}:{f.rsplit('_', 1)[0]}" for f in os.listdir(MP_DIR))
    body = await asyncio.to_thread(lambda: urllib.request.urlopen(f"http://127.0.0.1:{prom_port}/metrics").read().decode())
    names = sorted({l.split("{")[0].split(" ")[0] for l in body.splitlines() if l and not l.startswith("#")})
    print(json.dumps({"label": sys.argv[1], "before": before, "after": after,
                      "series": [n for n in names if not n.startswith("lk_agents_child")]}))
    await server.aclose()
    run_task.cancel()
    live.kill()


asyncio.run(main())
