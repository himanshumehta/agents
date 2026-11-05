import asyncio
import json
import os
import sys

from livekit.plugins import silero

ONNX = os.environ["SILERO_ONNX"]


def load(**kw):
    return silero.VAD.load(onnx_file_path=ONNX, **kw)


def case(name, build):
    try:
        vad, stream = build()
        out = {"vad": round(vad._opts.deactivation_threshold, 4)}
        if stream is not None:
            out["stream"] = round(stream._opts.deactivation_threshold, 4)
        return name, out
    except Exception as e:
        return name, {"error": f"{type(e).__name__}: {e}"}


async def main():
    rows = []

    def c1():
        return load(activation_threshold=0.8), None

    def c2():
        v = load()
        v.update_options(activation_threshold=0.8)
        return v, None

    def c3():
        v = load(activation_threshold=0.8)
        v.update_options(activation_threshold=0.5)
        return v, None

    def c4():
        v = load(deactivation_threshold=0.2)
        v.update_options(activation_threshold=0.8)
        return v, None

    def c5():
        v = load()
        v.update_options(activation_threshold=0.8, deactivation_threshold=0.3)
        return v, None

    def c6():
        v = load()
        v.update_options(activation_threshold=0.1)
        return v, None

    def c7():
        v = load()
        s = v.stream()
        v.update_options(activation_threshold=0.8)
        return v, s

    def c8():
        v = load()
        v.update_options(deactivation_threshold=0.3)
        v.update_options(activation_threshold=0.8)
        return v, None

    for name, fn in [
        ("1 load(act=0.8)  [reference]", c1),
        ("2 load(); update(act=0.8)", c2),
        ("3 load(act=0.8); update(act=0.5)", c3),
        ("4 load(deact=0.2); update(act=0.8)", c4),
        ("5 load(); update(act=0.8, deact=0.3)", c5),
        ("6 load(); update(act=0.1)  [floor]", c6),
        ("7 open stream, then update(act=0.8)", c7),
        ("8 load(); update(deact=0.3); update(act=0.8)", c8),
    ]:
        rows.append(case(name, fn))
    print(json.dumps({"label": sys.argv[1], "rows": rows}))


asyncio.run(main())
