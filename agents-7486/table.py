import json, sys
cols = [json.load(open(p)) for p in sys.argv[1:]]
def fmt(v):
    s = f"{v['outcome']}/{v['reason']} {','.join(t.replace('lk.', '') for t in v['tags'])}"
    if any(k.startswith("meta:") for k in v):
        s += " +meta"
    return s
print("case".ljust(42), " ".join(c["label"].split("@")[0].ljust(24) for c in cols))
for i, (n, _) in enumerate(cols[0]["rows"]):
    print(n[:42].ljust(42), " ".join(fmt(c["rows"][i][1]).ljust(24) for c in cols))
