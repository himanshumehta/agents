import asyncio
import json
import multiprocessing as mp
import os
import sys
import tempfile

os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", tempfile.mkdtemp(prefix="prom-7006-"))
MP_DIR = os.environ["PROMETHEUS_MULTIPROC_DIR"]

from livekit.agents import ipc  # noqa: E402
from livekit.agents.job import JobContext, JobProcess  # noqa: E402

from job_metrics import init_child  # noqa: E402


async def _entry(ctx: JobContext) -> None:
    pass


async def main() -> None:
    loop = asyncio.get_running_loop()
    proc = ipc.job_proc_executor.ProcJobExecutor(
        initialize_process_fnc=init_child,
        job_entrypoint_fnc=_entry,
        session_end_fnc=None,
        simulation_end_fnc=None,
        initialize_timeout=30.0,
        close_timeout=10.0,
        session_end_timeout=300.0,
        memory_warn_mb=0,
        memory_limit_mb=0,
        ping_interval=2.5,
        ping_timeout=10.0,
        high_ping_threshold=1.0,
        inference_executor=None,
        http_proxy=None,
        mp_ctx=mp.get_context("spawn"),
        loop=loop,
    )
    await proc.start()
    await proc.initialize()
    child = proc.pid
    alive = sorted(f for f in os.listdir(MP_DIR) if f.endswith(f"_{child}.db"))
    await proc.aclose()
    left = sorted(f for f in os.listdir(MP_DIR) if f.endswith(f"_{child}.db"))
    parent = sorted(f for f in os.listdir(MP_DIR) if f.endswith(f"_{os.getpid()}.db"))
    print(json.dumps({"label": sys.argv[1], "child_files_while_running": [f.rsplit("_", 1)[0] for f in alive],
                      "child_files_after_aclose": [f.rsplit("_", 1)[0] for f in left],
                      "parent_files": [f.rsplit("_", 1)[0] for f in parent]}))


if __name__ == "__main__":
    asyncio.run(main())
