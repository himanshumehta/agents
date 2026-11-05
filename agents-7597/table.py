import json, sys
cols = []
for path in sys.argv[1:]:
    cols.append(json.load(open(path)))
names = [r[0] for r in cols[0]["rows"]]
hdr = ["case".ljust(44)] + [c["label"].split("@")[0].ljust(7) for c in cols]
print(" ".join(hdr))
for i, n in enumerate(names):
    cells = []
    for c in cols:
        v = c["rows"][i][1]
        s = str(v.get("vad", v.get("error", "?")))
        if "stream" in v:
            s += "/" + str(v["stream"])
        cells.append(s.ljust(7))
    print(n[:44].ljust(44), " ".join(cells))
