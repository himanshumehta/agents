import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location("obs", sys.argv[1])
m = importlib.util.module_from_spec(spec)
sys.modules["obs"] = m
spec.loader.exec_module(m)


def state(t):
    out = {"tags": sorted(t.tags), "outcome": t.outcome, "reason": t.outcome_reason}
    for k in ("lk.success", "lk.fail"):
        e = t._tags.get(k)
        if e is not None and e.metadata:
            out["meta:" + k] = e.metadata
    return out


def run(steps):
    t = m.Tagger()
    for fn, args, kw in steps:
        getattr(t, fn)(*args, **kw)
    return state(t)


S = lambda fn, *a, **k: (fn, a, k)
cases = [
    ("A fail(r1); add(lk.success)", [S("fail", reason="r1"), S("add", "lk.success")]),
    ("B success(r1); add(lk.fail)", [S("success", reason="r1"), S("add", "lk.fail")]),
    ("C success(r1); remove(lk.success)", [S("success", reason="r1"), S("remove", "lk.success")]),
    ("D add(lk.fail, metadata)", [S("add", "lk.fail", metadata={"code": 42})]),
    ("E add(lk.fail, metadata); success(r2)", [S("add", "lk.fail", metadata={"code": 42}), S("success", reason="r2")]),
    ("F fail(r1); success(r2); remove(lk.fail)", [S("fail", reason="r1"), S("success", reason="r2"), S("remove", "lk.fail")]),
    ("G success(r1); fail(r2); remove(lk.success)", [S("success", reason="r1"), S("fail", reason="r2"), S("remove", "lk.success")]),
    ("H fail(r1); add(lk.fail, metadata)", [S("fail", reason="r1"), S("add", "lk.fail", metadata={"code": 7})]),
]
print(json.dumps({"label": sys.argv[2], "rows": [(n, run(s)) for n, s in cases]}))
