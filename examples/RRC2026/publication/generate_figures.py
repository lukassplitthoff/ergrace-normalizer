"""
generate_figures.py — produce publication figures for RRC2026_report.tex

Run from the publication/ directory:
    python generate_figures.py

Output: figures/results.pdf  (Figure 2 of the paper)

Figure 1 (power curve) is produced inline with pgfplots inside the .tex file.
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")           # headless rendering
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe

# ── Output directory ──────────────────────────────────────────────────────────
os.makedirs("figures", exist_ok=True)

# ── Race data (corrected team compositions) ───────────────────────────────────
# Reference: 2000 m world records (Concept2 WR database)
#   Men:   O. Zeidler 5:34.7 → 597 W
#   Women: B. Mooney  6:21.1 → 405 W
REF_TIME_MEN_S   = 5 * 60 + 34.7   # 334.7 s → 1:23.7 / 500 m
REF_TIME_WOMEN_S = 6 * 60 + 21.1   # 381.1 s → 1:35.3 / 500 m
REF_DIST_M       = 2000
T_RACE           = 1800             # 30 min

def power(dist_m, time_s):
    """P = 2.8 * (d/T)^3  [W]"""
    return 2.8 * (dist_m / time_s) ** 3

P_MEN   = power(REF_DIST_M, REF_TIME_MEN_S)    # ≈ 597 W
P_WOMEN = power(REF_DIST_M, REF_TIME_WOMEN_S)  # ≈ 405 W

TEAMS = [
    # (short_label, lane, n_men, n_women, distance_m)
    ("Chalmers~1",      8,  2, 3, 9268),
    ("Göteborgs RK",    7,  0, 5, 8575),
    ("CTH-GU",         10,  3, 2, 9511),
    ("Jönköpings~2",    5,  2, 3, 9021),
    ("Mölndals~1",      4,  2, 3, 8744),
    ("Mölndals~2",      6,  1, 4, 8439),
    ("Chalmers~2",      1,  4, 1, 9095),
    ("Jönköpings~1",    2,  3, 2, 8660),
    ("Råda Crew",       9,  3, 2, 7733),
    ("Halmstads RK",    3,  2, 3, 6956),
]

# Compute scores
rows = []
for label, lane, nm, nf, dist in TEAMS:
    n_total = nm + nf
    p_ref = (nm * P_MEN + nf * P_WOMEN) / n_total
    p_act = power(dist, T_RACE)
    score = p_act / p_ref
    comp  = f"{nm}M/{nf}F"
    rows.append({
        "label": label,
        "lane":  lane,
        "comp":  comp,
        "dist":  dist / 1000.0,   # km
        "p_ref": p_ref,
        "p_act": p_act,
        "score": score,
    })

# Sort by score descending (best first)
rows.sort(key=lambda r: r["score"], reverse=True)

# ── Colours (publication style) ───────────────────────────────────────────────
BLUE  = "#1A3A6B"   # dark navy — distance bars
RED   = "#C0392B"   # deep red  — score markers

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(10, 4.5))
fig.patch.set_facecolor("white")
ax1.set_facecolor("white")

labels  = [r["label"] for r in rows]
dists   = [r["dist"]  for r in rows]
scores  = [r["score"] for r in rows]
comps   = [r["comp"]  for r in rows]
x       = np.arange(len(rows))
width   = 0.62

# Distance bars
bars = ax1.bar(x, dists, width, color=BLUE, alpha=0.82, zorder=2)
ax1.set_ylabel("Distance [km]", color=BLUE, fontsize=12, fontweight="bold")
ax1.tick_params(axis="y", labelcolor=BLUE, labelsize=10)
ax1.set_ylim(0, max(dists) * 1.25)
ax1.set_xticks(x)

# Tick labels: team name + composition on two lines
tick_labels = [f"{lab}\n({comp})" for lab, comp in zip(labels, comps)]
ax1.set_xticklabels(tick_labels, rotation=0, ha="center", fontsize=9)

# Grid (horizontal only, behind bars)
ax1.yaxis.grid(True, linestyle=":", color="gray", alpha=0.5, zorder=0)
ax1.set_axisbelow(True)

# Remove top and right spines
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

# Score markers (secondary axis)
ax2 = ax1.twinx()
ax2.set_facecolor("none")

ax2.plot(x, scores, color=RED, marker="o", markersize=8,
         linewidth=1.5, linestyle="--", zorder=5,
         markerfacecolor="white", markeredgewidth=2.0,
         label="Score")

# Reference line at score = 1
ax2.axhline(1.0, color="gray", linestyle=":", linewidth=1.0, zorder=1)

# Score annotations above markers
for xi, s in zip(x, scores):
    offset = 0.04
    txt = ax2.text(xi, s + offset, f"{s:.3f}", ha="center", va="bottom",
                   fontsize=9, fontweight="bold", color=RED, zorder=6)
    txt.set_path_effects([
        pe.withStroke(linewidth=2.5, foreground="white"),
        pe.Normal(),
    ])

ax2.set_ylabel("Score ($P_{\\mathrm{act}} / P_{\\mathrm{ref}}$)",
               color=RED, fontsize=12, fontweight="bold")
ax2.tick_params(axis="y", labelcolor=RED, labelsize=10)
ax2.set_ylim(0, 1.05)
ax2.spines["top"].set_visible(False)

# Legend
bar_patch  = mpatches.Patch(color=BLUE, alpha=0.82, label="Distance [km]")
score_line = plt.Line2D([0], [0], color=RED, marker="o", markersize=7,
                         markerfacecolor="white", markeredgewidth=1.8,
                         linewidth=1.5, linestyle="--", label="Score")
ax1.legend(handles=[bar_patch, score_line],
           loc="upper right", fontsize=9, frameon=False)

# Rank labels inside bars
for xi, row in zip(x, rows):
    rank = rows.index(row) + 1
    bar_top = row["dist"]
    ax1.text(xi, bar_top / 2, f"#{rank}",
             ha="center", va="center",
             fontsize=9, color="white", fontweight="bold", zorder=3)

plt.tight_layout(pad=1.0)
outpath = os.path.join("figures", "results.pdf")
fig.savefig(outpath, dpi=300, bbox_inches="tight", facecolor="white")
print(f"Saved: {outpath}")
plt.close(fig)
