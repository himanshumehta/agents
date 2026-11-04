import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

out_dir = sys.argv[1]
png = sys.argv[2]
runs = [
    ("main.json", "main c2b2f5cbd"),
    ("pr-default.json", "this PR, default\nwait_until_answered=True"),
    ("pr-optin.json", "this PR\nwait_until_answered=False"),
]
INK = "#1f2328"
MUTED = "#59636e"
GRID = "#d1d9e0"
SPEECH = "#8c959f"
LISTEN = "#0969da"
BAD = "#cf222e"
GOOD = "#1a7f37"
ANSWER_AT = 12.0
XMAX = 28.5

fig, ax = plt.subplots(figsize=(11, 4.2), dpi=150)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")
ax.axvspan(0, ANSWER_AT, color="#f6f8fa", zorder=0)
ax.text(ANSWER_AT / 2, 3.05, "ringing: early media (SIP 183)", ha="center", va="bottom", color=MUTED, fontsize=9)
ax.text((ANSWER_AT + 24.0) / 2, 3.05, "answered (callStatus active)", ha="center", va="bottom", color=MUTED, fontsize=9)
ax.axvline(ANSWER_AT, color=INK, lw=1.2, ls="--", zorder=3)
ax.text(ANSWER_AT + 0.15, -0.62, "200 OK at 12.0 s", color=INK, fontsize=8.5, va="center")

for row, (fname, label) in enumerate(reversed(runs)):
    data = json.load(open(os.path.join(out_dir, fname)))
    ev = data["events"]
    y = row
    vs = next((e["t"] for e in ev if e["kind"] == "vad_start"), None)
    ve = next((e["t"] for e in ev if e["kind"] == "vad_end"), None)
    if vs is not None and ve is not None:
        ax.barh(y + 0.22, ve - vs, left=vs, height=0.16, color=SPEECH, zorder=2)
    listen = next((e["t"] for e in ev if e["kind"] == "amd_listening"), None)
    verdict = data["verdict"]
    vt = verdict.get("t", XMAX)
    if listen is not None:
        ax.barh(y - 0.08, vt - listen, left=listen, height=0.3, color=LISTEN, zorder=2)
    cat = verdict.get("category", "none")
    good = cat == "machine-vm"
    ax.plot([vt], [y - 0.08], marker="D", ms=9, color=GOOD if good else BAD, mec="white", mew=1.5, zorder=4)
    note = f"{cat} at {vt:.1f} s" + ("" if good else f"\n({verdict.get('reason', '')})")
    ax.text(vt + 0.35, y - 0.08, note, va="center", ha="left", color=INK, fontsize=9, fontweight="bold")
    if listen is not None:
        ax.text(listen, y - 0.36, f"AMD listens from {listen:.1f} s", color=LISTEN, fontsize=8, va="top")

ax.set_yticks(range(len(runs)))
ax.set_yticklabels([r[1] for r in reversed(runs)], color=INK, fontsize=9.5)
ax.set_xlim(0, XMAX)
ax.set_ylim(-0.8, 3.0)
ax.set_xlabel("seconds since the callee's audio track was subscribed", color=MUTED, fontsize=9)
ax.tick_params(axis="x", colors=MUTED, labelsize=8.5)
ax.tick_params(axis="y", length=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.grid(axis="x", color=GRID, lw=0.6, zorder=1)
ax.legend(
    handles=[
        Patch(color=SPEECH, label="voicemail greeting (Silero VAD speech)"),
        Patch(color=LISTEN, label="AMD listening window"),
        plt.Line2D([], [], marker="D", ls="", color=GOOD, label="verdict: machine-vm"),
        plt.Line2D([], [], marker="D", ls="", color=BAD, label="verdict: uncertain"),
    ],
    loc="upper center",
    bbox_to_anchor=(0.5, -0.2),
    ncol=4,
    frameon=False,
    fontsize=8.5,
    labelcolor=INK,
)
ax.set_title("AMD on a carrier that plays the voicemail greeting as SIP early media", color=INK, fontsize=11, loc="left", pad=22)
fig.tight_layout()
fig.savefig(png, facecolor="white")
print(png)
