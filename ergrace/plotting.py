"""Visualizations for RelayRace and MixedRace (matplotlib)."""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter

from .references import format_time

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
NAVY, BLUE, ORANGE = "#1b3a5c", "#2a78d6", "#eb6834"

STYLE = {
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "TeX Gyre Termes", "DejaVu Serif"],
    "mathtext.fontset": "stix", "font.size": 9, "pdf.fonttype": 42,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False,
}


def _clock(x, _pos=None):
    return format_time(x, decimals=0)


def _serif_family() -> str:
    """First installed font of STYLE["font.serif"] (falls back to 'serif')."""
    from matplotlib import font_manager
    installed = {f.name for f in font_manager.fontManager.ttflist}
    return next((f for f in STYLE["font.serif"] if f in installed), "serif")


def _pin_fonts(fig):
    """Store the fonts on every text so the figure renders the same after the
    style context is left (e.g. when Jupyter displays it at the end of a cell)."""
    from matplotlib.text import Text
    family = _serif_family()
    for t in fig.findobj(Text):
        t.set_fontfamily(family)
        t.set_math_fontfamily(STYLE["mathtext.fontset"])


def _finish(fig, save_path, dpi):
    _pin_fonts(fig)
    fig.tight_layout()
    if save_path:
        meta = {"CreationDate": None} if str(save_path).endswith(".pdf") else None
        fig.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor="white",
                    metadata=meta)
        print(f"Saved: {save_path}")
    return fig


def _entry_label(race, name, rank=None):
    e = race.entries[name]
    prefix = f"{rank}. " if rank is not None else ""
    return f"{prefix}{name}  ({e['label']})"


def plot_handicaps(race, save_path: Optional[str] = None, dpi: int = 200):
    """Staggered-start chart (distance races) or metre credits (time races)."""
    df = race.handicaps()
    n = len(df)
    with plt.rc_context(STYLE):
        lab_w = 0.075 * max(len(_entry_label(race, nm)) for nm in df["Entry"])
        fig, ax = plt.subplots(figsize=(5.5 + lab_w, 0.42 * n + 1.5))
        y = np.arange(n)[::-1]
        if race.fixed_distance:
            finish = (df["Start Offset (s)"] + df["Expected Time (s)"]).max()
            for yi, (_, r) in zip(y, df.iterrows()):
                ax.barh(yi, r["Expected Time (s)"], left=r["Start Offset (s)"], height=0.55,
                        color=BLUE, alpha=0.85, edgecolor="white", lw=1)
                ax.text(r["Start Offset (s)"] - 0.01 * finish, yi,
                        r["Start Offset"], ha="right", va="center", fontsize=8, color=INK)
                ax.text(r["Start Offset (s)"] + 0.01 * finish, yi,
                        f"row {r['Expected Time']}", ha="left", va="center",
                        fontsize=7.5, color="white")
            ax.axvline(finish, color=INK, lw=1, ls=(0, (3, 2)))
            ax.text(finish, n - 0.35, f"common finish {format_time(finish, 0)}",
                    ha="right", va="bottom", fontsize=8, color=INK2)
            ax.set_xlim(-0.12 * finish, finish * 1.02)
            ax.xaxis.set_major_formatter(FuncFormatter(_clock))
            ax.set_xlabel("Race clock from first start [min:s]")
            title = f"Staggered start: {race.kind}, {race.format}"
            ax.set_ylim(-0.6, n - 0.1)
        else:
            credits = df["Credit (m)"].to_numpy()
            ax.barh(y, credits, height=0.55, color=BLUE, alpha=0.85)
            top = max(credits.max(), 1)
            for yi, (_, r) in zip(y, df.iterrows()):
                ax.text(r["Credit (m)"] + 0.015 * top, yi,
                        f"+{r['Credit (m)']:.0f} m  (target {r['Target Distance (m)']:.0f} m)",
                        va="center", fontsize=8, color=INK)
            ax.set_xlim(0, top * 1.55)
            ax.set_xlabel("Distance credit [m] (metres added to the result)")
            title = f"Handicap credits: {race.kind}, {race.format}"
            ax.set_ylim(-0.6, n - 0.4)
        ax.set_yticks(y, [_entry_label(race, nm) for nm in df["Entry"]])
        ax.tick_params(axis="y", length=0)
        ax.spines["left"].set_visible(False)
        ax.xaxis.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
        sub = (f"entries at {race.level:.0%} of reference power arrive together"
               if race.fixed_distance else
               f"entries at {race.level:.0%} of reference power tie after credit")
        ax.set_title(f"{title}\n", loc="left", fontsize=10, fontweight="bold")
        ax.text(0, 1.01, sub, transform=ax.transAxes, fontsize=8, color=INK2,
                va="bottom")
        return _finish(fig, save_path, dpi)


def plot_results(race, save_path: Optional[str] = None, dpi: int = 200,
                 show_teams: bool = True):
    """Power score per entry and performance against the handicap."""
    df = race.results()
    n = len(df)
    teams = None
    if show_teams and hasattr(race, "team_results") and "Team" in df:
        teams = race.team_results()
    ncols = 3 if teams is not None else 2
    widths = [1.5, 1] + ([0.9] if teams is not None else [])
    with plt.rc_context(STYLE):
        lab_w = 0.075 * max(len(_entry_label(race, nm, r))
                            for nm, r in zip(df["Entry"], df["Rank"]))
        if teams is not None:
            lab_w += 0.075 * max(len(str(t)) + 6 for t in teams["Team"])
        fig, axes = plt.subplots(1, ncols, figsize=(3.6 * ncols + lab_w, 0.42 * n + 1.6),
                                 gridspec_kw={"width_ratios": widths})
        ax1, ax2 = axes[0], axes[1]
        y = np.arange(n)[::-1]
        sc, ss = df["Score"].to_numpy(), df["Speed Score"].to_numpy()

        # (a) scores
        for yi, a, b in zip(y, sc, ss):
            ax1.plot([a, b], [yi, yi], color=GRID, lw=2, zorder=1, solid_capstyle="round")
        ax1.scatter(ss, y, s=26, facecolor="white", edgecolor=MUTED, lw=1.2, zorder=3,
                    label=r"speed score $v/v_{\rm ref}$")
        ax1.scatter(sc, y, s=36, color=NAVY, edgecolor="white", lw=0.8, zorder=4,
                    label=r"power score $\sigma=(v/v_{\rm ref})^3$")
        for yi, a in zip(y, sc):
            ax1.annotate(f"{a:.3f}", (a, yi), xytext=(-6, 0), textcoords="offset points",
                         ha="right", va="center", fontsize=7.5, color=INK)
        lo = min(sc.min(), ss.min())
        hi = max(1.02, ss.max() + 0.03)
        ax1.set_xlim(max(0, lo - 0.12), hi)
        ax1.axvline(1, color=MUTED, lw=0.8, ls=(0, (2, 2)))
        ax1.set_yticks(y, [_entry_label(race, nm, r) for nm, r in zip(df["Entry"], df["Rank"])])
        ax1.tick_params(axis="y", length=0)
        ax1.spines["left"].set_visible(False)
        ax1.xaxis.grid(True, color=GRID, lw=0.6)
        ax1.set_axisbelow(True)
        ax1.set_xlabel("Score (1 = reference)")
        ax1.set_ylim(-0.7, n - 0.2)
        ax1.legend(loc="lower left", fontsize=7.5, bbox_to_anchor=(0, 1.0), ncol=2,
                   handletextpad=0.3, columnspacing=1.0, borderaxespad=0.1)
        ax1.set_title(f"(a) Result: {race.kind}, {race.format}\n\n", loc="left",
                      fontsize=10, fontweight="bold")

        # (b) against the handicap
        if race.fixed_distance:
            dv = df["Vs Handicap (s)"].to_numpy()
            good = dv <= 0
            xlabel = "Finish vs predicted common finish [s]"
            txt = [format_time(v, 1, sign=True) for v in dv]
        else:
            dv = df["Vs Handicap (m)"].to_numpy()
            good = dv >= 0
            xlabel = "Distance vs target [m]"
            txt = [f"{v:+.0f} m" for v in dv]
        ax2.barh(y, dv, height=0.55, color=np.where(good, BLUE, ORANGE), alpha=0.9)
        span = max(np.abs(dv).max(), 1)
        for yi, v, t in zip(y, dv, txt):
            ax2.text(v + (0.03 if v >= 0 else -0.03) * span, yi, t, va="center",
                     ha="left" if v >= 0 else "right", fontsize=7.5, color=INK)
        ax2.axvline(0, color=INK, lw=0.8)
        ax2.set_xlim(-1.45 * span if dv.min() < 0 else -0.1 * span,
                     1.45 * span if dv.max() > 0 else 0.1 * span)
        ax2.set_yticks([])
        ax2.spines["left"].set_visible(False)
        ax2.set_ylim(-0.7, n - 0.2)
        ax2.xaxis.grid(True, color=GRID, lw=0.6)
        ax2.set_axisbelow(True)
        ax2.set_xlabel(xlabel)
        lvl = f"handicap at {race.level:.0%} of reference power"
        ax2.set_title("(b) Against the handicap\n\n", loc="left", fontsize=10,
                      fontweight="bold")
        ax2.text(0, 1.01, lvl, transform=ax2.transAxes, fontsize=8, color=INK2, va="bottom")

        # (c) teams
        if teams is not None:
            ax3 = axes[2]
            ty = np.arange(len(teams))[::-1]
            for yi, (_, r) in zip(ty, teams.iterrows()):
                ax3.plot([r["Worst"], r["Best"]], [yi, yi], color=GRID, lw=3,
                         solid_capstyle="round", zorder=1)
                ax3.scatter(r["Score"], yi, s=40, color=NAVY, edgecolor="white", zorder=3)
                ax3.annotate(f"{r['Score']:.3f}", (r["Score"], yi), xytext=(0, 7),
                             textcoords="offset points", ha="center", fontsize=7.5)
            ax3.set_yticks(ty, [f"{r['Rank']}. {r['Team']} ({r['Athletes']})"
                                for _, r in teams.iterrows()])
            ax3.tick_params(axis="y", length=0)
            ax3.spines["left"].set_visible(False)
            ax3.set_ylim(-0.7, len(teams) - 0.3)
            ax3.xaxis.grid(True, color=GRID, lw=0.6)
            ax3.set_axisbelow(True)
            ax3.set_xlabel("Mean power score (range = best/worst)")
            ax3.set_title("(c) Teams\n\n", loc="left", fontsize=10, fontweight="bold")
        return _finish(fig, save_path, dpi)
