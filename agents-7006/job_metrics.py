import prometheus_client

from livekit.agents.job import JobProcess


def init_child(proc: JobProcess) -> None:
    prometheus_client.Counter("app_jobs_handled", "x").inc()
    prometheus_client.Histogram("app_turn_seconds", "x").observe(0.4)
    prometheus_client.Gauge("app_gauge_all", "x").set(1)
    prometheus_client.Gauge("app_gauge_livesum", "x", multiprocess_mode="livesum").set(1)
