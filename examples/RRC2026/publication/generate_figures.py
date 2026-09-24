"""
generate_figures.py -- figures, tables and key numbers for RRC2026_report.tex

Everything quoted in the paper is computed here with the ``ergrace`` package,
so the text, tables and figures cannot drift apart.

Run from anywhere:
    python examples/RRC2026/publication/generate_figures.py

Outputs (in publication/figures/):
    reference.pdf          Fig. 2  -- gender gap vs distance, averaging bias
    results.pdf            Fig. 3  -- scores and rank sensitivity
    results_table.tex      Table II body
    sensitivity_table.tex  Table III body
    numbers.tex            \\newcommand macros for numbers quoted in the text
"""

import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "..")))
from ergrace import ERGNormalizer                                 # noqa: E402
from ergrace.normalizer import (power_from_distance_time,          # noqa: E402
                                speed_from_power, split_from_power)

OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# ── Data ────────────────────────────────────────────────────────────────────
T_RELAY = 30 * 60                     # s
N_ROWERS = 5

# Reference performances (Concept2 RowErg, open category), times in s.
# 500/2000/5000 m: world records; 1000 m: WRVIC 2026 event winners.
REFERENCES = {                         # label: (distance m, men s, women s)
    "500 m":  (500,  69.8,  84.5),
    "1000 m": (1000, 158.0, 189.4),
    "2000 m": (2000, 334.7, 381.1),
    "5000 m": (5000, 893.9, 1009.4),
}
PRIMARY = "2000 m"

TEAMS = [  # (full name for table, short label for figures, lane, men, women, distance m)
    ("Chalmers Roddklubb -- Team 1",       "Chalmers 1",   8, 2, 3, 9268),
    ("G{\\\"o}teborgs Roddklubb",           "Göteborgs RK", 7, 0, 5, 8575),
    ("CTH-GU",                             "CTH-GU",      10, 3, 2, 9511),
    ("J{\\\"o}nk{\\\"o}pings Rodds.\\ -- Team 2", "Jönköping 2", 5, 2, 3, 9021),
    ("M{\\\"o}lndals Roddklubb -- Team 1",   "Mölndal 1",    4, 2, 3, 8744),
    ("M{\\\"o}lndals Roddklubb -- Team 2",   "Mölndal 2",    6, 1, 4, 8439),
    ("Chalmers Roddklubb -- Team 2",       "Chalmers 2",   1, 4, 1, 9095),
    ("J{\\\"o}nk{\\\"o}pings Rodds.\\ -- Team 1", "Jönköping 1", 2, 3, 2, 8660),
    ("R{\\aa}da Crew",                     "Råda Crew",    9, 3, 2, 7733),
    ("Halmstads Roddklubb",                "Halmstads RK", 3, 2, 3, 6956),
]
SHORT = {t[0]: t[1] for t in TEAMS}


def run(ref_label):
    d, tm, tf = REFERENCES[ref_label]
    norm = ERGNormalizer.from_reference_times(d, tm, tf, duration_s=T_RELAY)
    for full, _, _, nm, nf, dist in TEAMS:
        norm.add_team(full, nm, nf, distance_m=dist)
    return norm, norm.calculate_scores().get_results()


results = {lab: run(lab) for lab in REFERENCES}
norm, df = results[PRIMARY]
ranks = {lab: dict(zip(r[1]["Team"], r[1]["Rank"])) for lab, r in results.items()}

dist = np.array([t[5] for t in TEAMS], float)
raw_rank = {t[0]: int(r) for t, r in
            zip(TEAMS, (-dist).argsort().argsort() + 1)}
lane = {t[0]: t[2] for t in TEAMS}

# ── Tables ──────────────────────────────────────────────────────────────────
with open(os.path.join(OUT, "results_table.tex"), "w") as f:
    for _, r in df.iterrows():
        f.write(f"    {r['Rank']:>2} & {r['Team']:<40} & {lane[r['Team']]:>2} & "
                f"{r['Composition'].replace('W', 'F')} & "
                f"{r['Distance (km)']:.3f} & {r['Ref Distance (km)']:.3f} & "
                f"{r['Speed Score']:.4f} & {r['Team Power (W)']:.0f} & "
                f"{r['Ref Power (W)']:.0f} & {r['Score']:.4f} & "
                f"{raw_rank[r['Team']]} \\\\\n")

def latex_short(full):
    return (SHORT[full].replace("ö", '{\\"o}').replace("å", "{\\aa}"))


with open(os.path.join(OUT, "sensitivity_table.tex"), "w") as f:
    for _, r in df.iterrows():
        cells = " & ".join(str(ranks[lab][r["Team"]]) for lab in REFERENCES)
        f.write(f"    {latex_short(r['Team']):<24} & {r['Composition'].replace('W', 'F')} & "
                f"{cells} \\\\\n")

# ── Numbers quoted in the text ──────────────────────────────────────────────
refP = {lab: (power_from_distance_time(d, tm), power_from_distance_time(d, tf))
        for lab, (d, tm, tf) in REFERENCES.items()}
Pm, Pf = refP[PRIMARY]
first, second = df.iloc[0], df.iloc[1]
# extra distance the runner-up would have needed to tie the winner
tie_margin_m = first["Speed Score"] * second["Ref Distance (km)"] * 1e3 - second["Distance (km)"] * 1e3


def arith_bias(pm, pf, nm, n=N_ROWERS):
    """Relative overestimate of the arithmetic mean over the 1/3-power mean."""
    arith = (nm * pm + (n - nm) * pf) / n
    v = (nm * speed_from_power(pm) + (n - nm) * speed_from_power(pf)) / n
    return arith / (2.8 * v ** 3) - 1


max_bias_2k = max(arith_bias(Pm, Pf, k) for k in range(N_ROWERS + 1))
old_scores = {}
for full, _, _, nm, nf, d in TEAMS:
    old_scores[full] = power_from_distance_time(d, T_RELAY) / ((nm * Pm + nf * Pf) / (nm + nf))
old_order = sorted(old_scores, key=old_scores.get, reverse=True)

top = df.iloc[0]
top_split = 500 * T_RELAY / (top["Distance (km)"] * 1e3)
top_ref_split = split_from_power(top["Ref Power (W)"])

macros = {
    "PmTwoK": f"{Pm:.0f}", "PfTwoK": f"{Pf:.0f}",
    "RatioTwoK": f"{Pm / Pf:.2f}",
    "SpeedRatioTwoK": f"{(Pm / Pf) ** (1 / 3):.3f}",
    "MeanDist": f"{dist.mean() / 1e3:.2f}",
    "StdDist": f"{dist.std(ddof=1) / 1e3:.2f}",
    "CvDist": f"{100 * dist.std(ddof=1) / dist.mean():.1f}",
    "MeanScore": f"{df['Score'].mean():.2f}",
    "MeanSpeedScore": f"{df['Speed Score'].mean():.3f}",
    "MinScore": f"{df['Score'].min():.2f}", "MaxScore": f"{df['Score'].max():.2f}",
    "TieMargin": f"{tie_margin_m:.1f}",
    "FirstTeam": SHORT[first["Team"]], "SecondTeam": SHORT[second["Team"]],
    "FirstScore": f"{first['Score']:.4f}", "SecondScore": f"{second['Score']:.4f}",
    "ScoreGap": f"${(first['Score'] - second['Score']) * 1e4:.1f}\\times10^{{-4}}$",
    "MaxBiasTwoK": f"{100 * max_bias_2k:.1f}",
    "OldFirst": SHORT[old_order[0]], "OldSecond": SHORT[old_order[1]],
    "TopSplit": f"{int(top_split // 60)}:{top_split % 60:04.1f}",
    "TopRefSplit": f"{int(top_ref_split // 60)}:{top_ref_split % 60:04.1f}",
    "TopSpeedDeficit": f"{100 * (1 - top['Speed Score']):.0f}",
    "TopPowerDeficit": f"{100 * (1 - top['Score']):.0f}",
}
for lab, (pm, pf) in refP.items():
    key = {"500 m": "Five", "1000 m": "OneK", "2000 m": "TwoK", "5000 m": "FiveK"}[lab]
    macros[f"Ratio{key}"] = f"{pm / pf:.2f}"
    macros[f"MaxBias{key}"] = f"{100 * max(arith_bias(pm, pf, k) for k in range(6)):.1f}"
with open(os.path.join(OUT, "numbers.tex"), "w") as f:
    f.write("% generated by generate_figures.py -- do not edit\n")
    for k, v in macros.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")

# ── Figure style ────────────────────────────────────────────────────────────
PDF_META = {"CreationDate": None}      # reproducible PDFs (no timestamp)
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SEQ = ["#b9d3f2", "#7fb0ea", "#3f86d9", "#1b5aa6"]     # one hue, light -> dark
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "TeX Gyre Termes",
                   "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 8.5, "pdf.fonttype": 42,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "figure.dpi": 150,
})


def tex(s):
    return s


# ── Fig. 2: gender gap vs distance; arithmetic-mean bias ───────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 2.6),
                               gridspec_kw={"width_ratios": [1, 1.15]})
xs = np.arange(len(REFERENCES))
pr = np.array([pm / pf for pm, pf in refP.values()])
ax1.plot(xs, pr, "-o", color=BLUE, lw=2, ms=5, zorder=3)
ax1.plot(xs, pr ** (1 / 3), "-s", color=ORANGE, lw=2, ms=5, zorder=3)
for x, p in zip(xs, pr):
    ax1.annotate(f"{p:.2f}", (x, p), xytext=(0, 6), textcoords="offset points",
                 ha="center", color=INK, fontsize=7.5)
ax1.text(3.05, pr[-1] - 0.07, r"power $P_m/P_f$", color=INK, ha="right", va="top")
ax1.text(3.05, pr[-1] ** (1 / 3) + 0.04, r"speed $v_m/v_f$", color=INK, ha="right", va="bottom")
ax1.axvspan(1.6, 2.4, color=GRID, alpha=0.6, lw=0, zorder=0)
ax1.text(2, 1.02, "used", ha="center", va="bottom", color=INK2, fontsize=7)
ax1.set_xticks(xs, [lab for lab in REFERENCES])
ax1.set_xlim(-0.35, 3.35)
ax1.set_ylim(1.0, 1.9)
ax1.set_xlabel("Reference distance")
ax1.set_ylabel("Men / women reference ratio")
ax1.yaxis.grid(True, color=GRID, lw=0.6)
ax1.set_axisbelow(True)
ax1.set_title("(a) Gender gap in speed and power", loc="left", fontsize=8.5, fontweight="bold")

nm = np.arange(N_ROWERS + 1)
for (lab, (pm, pf)), c in zip(refP.items(), SEQ):
    b = [100 * arith_bias(pm, pf, k) for k in nm]
    ax2.plot(nm, b, "-o", color=c, lw=2, ms=4.5, zorder=3, label=lab,
             markeredgecolor="white", markeredgewidth=0.8)
ax2.legend(title="reference", fontsize=7, title_fontsize=7, loc="upper right",
           handlelength=1.6)
ax2.set_xticks(nm, [f"{k}M/{N_ROWERS - k}F" for k in nm])
ax2.set_ylim(0, None)
ax2.set_xlim(-0.3, N_ROWERS + 0.3)
ax2.spines["bottom"].set_bounds(0, N_ROWERS)
ax2.set_xlabel("Team composition")
ax2.set_ylabel(r"$\langle P\rangle_{\rm arith}\,/\,P^{\rm ref}_k - 1$  [%]")
ax2.yaxis.grid(True, color=GRID, lw=0.6)
ax2.set_axisbelow(True)
ax2.set_title("(b) Bias of the arithmetic-mean reference", loc="left", fontsize=8.5, fontweight="bold")
fig.tight_layout(w_pad=2.5)
fig.savefig(os.path.join(OUT, "reference.pdf"), bbox_inches="tight", metadata=PDF_META)
plt.close(fig)

# ── Fig. 3: results + rank sensitivity ─────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.0, 3.3),
                               gridspec_kw={"width_ratios": [1.45, 1]})
order = list(df["Team"])                    # best first
y = np.arange(len(order))[::-1]             # best on top
scores = df["Score"].to_numpy()
sscores = df["Speed Score"].to_numpy()
for yi, s, ss in zip(y, scores, sscores):
    ax1.plot([ss ** 3, ss], [yi, yi], color=GRID, lw=2, zorder=1, solid_capstyle="round")
ax1.scatter(sscores, y, s=26, facecolor="white", edgecolor=MUTED, lw=1.2, zorder=3,
            label=r"speed score $s_k = D_k/D_k^{\rm ref}$")
ax1.scatter(scores, y, s=36, color="#1b3a5c", zorder=4, edgecolor="white", lw=0.8,
            label=r"power score $\sigma_k = s_k^3$")
ax1.annotate(f"dead heat: {tie_margin_m:.1f} m\nof {second['Distance (km)'] * 1e3:.0f} m",
             xy=(scores[1] - 0.115, y[0] - 0.5), ha="right", va="center",
             fontsize=7, color=INK2)
ax1.plot([scores[1] - 0.105] * 2, [y[1] + 0.1, y[0] - 0.1], color=MUTED, lw=0.8)
for yi, s, t in zip(y, scores, order):
    ax1.annotate(f"{s:.3f}", (s, yi), xytext=(-6, 0), textcoords="offset points",
                 ha="right", va="center", fontsize=7, color=INK)
labels = [f"{tex(SHORT[t])} ({r['Composition'].replace('W', 'F')})"
          for t, (_, r) in zip(order, df.iterrows())]
ax1.set_yticks(y, [f"{i + 1}. " + lab for i, lab in enumerate(labels)])
ax1.set_xlim(0.2, 1.02)
ax1.axvline(1.0, color=MUTED, lw=0.8, ls=(0, (2, 2)))
ax1.text(0.995, y[0] + 0.9, "reference", ha="right", va="bottom", fontsize=7, color=INK2)
ax1.set_ylim(-0.7, len(order) - 0.1)
ax1.set_xlabel(f"Score (reference: {PRIMARY} world records)")
ax1.xaxis.grid(True, color=GRID, lw=0.6)
ax1.set_axisbelow(True)
ax1.tick_params(axis="y", length=0)
ax1.spines["left"].set_visible(False)
ax1.legend(loc="upper left", fontsize=7, handletextpad=0.3, borderaxespad=0.2,
           bbox_to_anchor=(0.0, 0.8))
ax1.set_title("(a) Normalized result", loc="left", fontsize=8.5, fontweight="bold")

labs = list(REFERENCES)
hi = {order[0]: BLUE, order[1]: ORANGE, "G{\\\"o}teborgs Roddklubb": AQUA}
for t in order:
    rk = [ranks[lab][t] for lab in labs]
    c = hi.get(t, "#c9c8c3")
    ax2.plot(range(len(labs)), rk, "-o", color=c, lw=2 if t in hi else 1.2,
             ms=4.5 if t in hi else 3, zorder=3 if t in hi else 2,
             markeredgecolor="white", markeredgewidth=0.6)
    ax2.text(len(labs) - 1 + 0.12, rk[-1], tex(SHORT[t]), va="center", fontsize=7,
             color=INK if t in hi else INK2)
ax2.set_xticks(range(len(labs)), [lab for lab in labs])
ax2.set_yticks(range(1, len(order) + 1))
ax2.set_ylim(len(order) + 0.5, 0.5)
ax2.set_xlim(-0.2, len(labs) - 1 + 1.25)
ax2.set_xlabel("Reference distance")
ax2.set_ylabel("Rank")
ax2.axvspan(1.75, 2.25, color=GRID, alpha=0.6, lw=0, zorder=0)
ax2.spines["bottom"].set_bounds(0, len(labs) - 1)
ax2.set_title("(b) Rank vs. reference distance", loc="left", fontsize=8.5, fontweight="bold")
fig.tight_layout(w_pad=1.5)
fig.savefig(os.path.join(OUT, "results.pdf"), bbox_inches="tight", metadata=PDF_META)
fig.savefig(os.path.join(OUT, "results_preview.png"), bbox_inches="tight", dpi=220)
plt.close(fig)

# ── Console summary ─────────────────────────────────────────────────────────
norm.print_results()
print("Rank sensitivity:")
for t in order:
    print(f"  {SHORT[t]:<14}", "  ".join(f"{lab}:{ranks[lab][t]:>2}" for lab in labs))
print("\nMacros:", macros)
print(f"\nSaved figures and tables to {OUT}")
