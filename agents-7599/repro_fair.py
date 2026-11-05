"""EventLoopMonitor._watchdog_check loses the stack sample when a tick runs
concurrently with it.

Both cases run the real _watchdog_check and the real _on_tick. A trace function
pauses one thread at a chosen point of the stock code and runs the other
side there, so the interleaving is exact on every run.

Case A: the tick runs after the watchdog has built its sample and before it
stores it (between the two `with self._lock:` blocks of _watchdog_check).
Case B: the watchdog runs while the tick is between `self._tick_seq += 1` and
`self._last_tick_at = now` in _on_tick.
"""

import asyncio
import inspect
import sys
import threading
import time

from livekit.agents.telemetry.loop_monitor import BlockedReport, EventLoopMonitor

WARN, TICK = 0.1, 0.02


def line_of(func, text: str, occurrence: int = 1) -> int:
    lines, first = inspect.getsourcelines(func)
    hits = [first + i for i, ln in enumerate(lines) if ln.strip() == text]
    return hits[occurrence - 1]


def run_paused(func, lineno: int, at_line, *args):
    """Run func(*args) on this thread; call at_line() once when it reaches lineno."""
    fired = False

    def local(frame, event, arg):
        nonlocal fired
        if event == "line" and frame.f_lineno == lineno and not fired:
            fired = True
            at_line()
        return local

    def tracer(frame, event, arg):
        return local if frame.f_code is func.__code__ else None

    sys.settrace(tracer)
    try:
        func(*args)
    finally:
        sys.settrace(None)
    assert fired, f"never reached line {lineno}"


PENDING: list[threading.Thread] = []


def on_watchdog_thread(fn) -> None:
    t = threading.Thread(target=fn)
    t.start()
    t.join(1.0)
    if t.is_alive():
        print("case B: the watchdog waited for the monitor's lock; letting the tick finish first")
        PENDING.append(t)


def new_monitor():
    loop = asyncio.new_event_loop()
    mon = EventLoopMonitor(loop, warn_threshold=WARN, error_threshold=5.0,
                           tick_interval=TICK, emit_spans=False)
    reports: list[BlockedReport] = []
    mon._on_report = reports.append
    mon._loop_thread_ident = threading.get_ident()  # this thread is the loop thread
    return loop, mon, reports


def case_a() -> bool:
    loop, mon, reports = new_monitor()
    mon._last_tick_at = time.monotonic() - 0.15  # the loop has been blocked 130 ms
    sampled = threading.Event()
    tick_done = threading.Event()

    def watchdog():
        # pause the watchdog right after _sample_loop_thread returns its sample
        def local(frame, event, arg):
            if event == "return":
                sampled.set()
                # a monitor that holds its lock here makes the tick wait instead,
                # so give up after 1 s
                tick_done.wait(1.0)
            return local

        def tracer(frame, event, arg):
            return local if frame.f_code is EventLoopMonitor._sample_loop_thread.__code__ else None

        sys.settrace(tracer)
        try:
            mon._watchdog_check()
        finally:
            sys.settrace(None)

    w = threading.Thread(target=watchdog)
    w.start()
    assert sampled.wait(5)
    mon._on_tick()  # the block ends: the tick reports
    tick_done.set()
    w.join()

    stacks = reports[0].stacks
    print(f"case A: report stacks = {stacks}")
    ok = stacks[0].startswith("# loop thread sampled")
    print(f"case A: {'PASS' if ok else 'FAIL'}: the watchdog took a sample of this block, "
          f"the report {'has' if ok else 'does not have'} it")
    mon.stop()
    loop.close()
    return ok


def case_b() -> bool:
    loop, mon, reports = new_monitor()
    mon._last_tick_at = time.monotonic() - 0.15
    on_watchdog_thread(mon._watchdog_check)  # the watchdog samples block 0 (tick_seq 0)
    assert mon._incident is not None and mon._incident.samples
    time.sleep(0.05)  # block 0 lasts 180 ms in total

    between = line_of(EventLoopMonitor._on_tick, "self._last_tick_at = now")
    run_paused(EventLoopMonitor._on_tick, between,
               lambda: on_watchdog_thread(mon._watchdog_check), mon)
    for t in PENDING:
        t.join()

    stacks = reports[0].stacks
    print(f"case B: report stacks = {stacks}")
    ok = stacks[0].startswith("# loop thread sampled")
    print(f"case B: {'PASS' if ok else 'FAIL'}: the watchdog sampled block 0 before the tick, "
          f"the report for block 0 {'has' if ok else 'does not have'} the sample")
    mon.stop()
    loop.close()
    return ok


if __name__ == "__main__":
    case_a()
    case_b()
