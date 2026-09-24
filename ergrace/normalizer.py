"""
ERG Power Normalizer - Normalize rowing ergometer relay results by team composition.

Physics summary
---------------
The Concept2 monitor converts the flywheel-derived speed ``v`` [m/s] into power
with the fixed relation

    P = c * v**3,      c = 2.8 W s^3 m^-3   (equivalently 2.8 kg/m).

In a relay the rowers take turns on ONE ergometer, so their *distances* (not
their powers) add up:  D = sum_i v_i * tau_i.  If every rower of team k holds
the same fraction ``sigma_k`` of their reference power ``P_i``, each rows at
speed ``sigma_k**(1/3) * v_i`` and, for equal shares of the race time ``T``,

    D_k = sigma_k**(1/3) * T * vbar_k,     vbar_k = (1/n) sum_i (P_i / c)**(1/3)

so the power score is

    sigma_k = (D_k / D_k_ref)**3 = P_team / P_ref,

with P_team = c (D_k/T)**3 and P_ref = c vbar_k**3 = [(1/n) sum_i P_i**(1/3)]**3,
i.e. the power mean with exponent 1/3 of the individual reference powers: the
power at the reference team's mean speed, matching the measured distance.  The
constant ``c`` cancels exactly.  Dividing P_team by the *arithmetic* mean of the
reference powers would compare the power at the mean speed with a mean power;
by the power-mean inequality that penalizes mixed teams.  The arithmetic mean
is the matching reference only when the observable is summed power, i.e.
rowers pulling simultaneously in one boat (see :mod:`ergrace.handicap`).
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional

#: Concept2 power-pace constant c in P = c v^3, units W s^3 m^-3 (= kg/m).
C2_POWER_CONSTANT = 2.8


def power_from_speed(speed_m_s: float) -> float:
    """Ergometer power [W] from monitor speed [m/s]: ``P = c v^3``."""
    return C2_POWER_CONSTANT * speed_m_s ** 3


def speed_from_power(power_w: float) -> float:
    """Monitor speed [m/s] from power [W]: ``v = (P / c)^(1/3)``."""
    return (power_w / C2_POWER_CONSTANT) ** (1.0 / 3.0)


def power_from_distance_time(distance_m: float, time_s: float) -> float:
    """Average-speed power [W] for ``distance_m`` rowed in ``time_s``."""
    return power_from_speed(distance_m / time_s)


def split_from_power(power_w: float) -> float:
    """500 m split [s] corresponding to ``power_w``: ``t500 = 500 m / v``."""
    return 500.0 / speed_from_power(power_w)


def team_reference_power(powers_w) -> float:
    """Reference power [W] of a relay team: power mean with exponent 1/3.

    ``P_ref = [ (1/n) * sum_i P_i^(1/3) ]^3`` -- the power at the team's mean
    reference speed.  Equals ``P`` for a homogeneous team and lies below the
    arithmetic mean for a mixed team.
    """
    powers_w = np.asarray(powers_w, dtype=float)
    if powers_w.size == 0:
        raise ValueError("Team must have at least one member")
    if np.any(powers_w <= 0):
        raise ValueError("Reference powers must be positive")
    return float(np.mean(np.cbrt(powers_w)) ** 3)


class ERGNormalizer:
    """
    Normalize ergometer relay results by the gender composition of each team.

    Each team rows a relay of duration ``duration_s`` on one ergometer and
    reports its total distance.  The team's result is compared with the
    distance a composition-matched reference team would cover if every rower
    rowed at their gender's reference power for an equal share of the time.

    Two equivalent scores are reported:

    * ``Speed Score``  s = D / D_ref           (fraction of reference speed)
    * ``Score``        sigma = s**3 = P_team / P_ref
                                               (fraction of reference power)

    Both give the same ranking; ``Score`` is expressed in power, the quantity
    the athletes actually produce.  See the module docstring for the physics.

    Parameters
    ----------
    ref_power_men, ref_power_women : float, optional
        Individual reference powers in W.  Defaults 569.92 W and 350.00 W are
        the benchmark 2000 m times 5:40 and 6:40 (not world records); use
        :meth:`from_reference_times` to set references from any distance/time.
    duration_s : float, optional
        Relay duration in seconds (default 1200 = 20 min; 1800 for 30 min).

    Examples
    --------
    >>> normalizer = ERGNormalizer(duration_s=1200)
    >>> _ = normalizer.add_team('Team A', n_men=3, n_women=2, distance_m=6319)
    >>> _ = normalizer.add_team('Team B', n_men=2, n_women=3, distance_m=5530)
    >>> normalizer.calculate_scores().print_results()  # doctest: +SKIP
    """

    def __init__(self, ref_power_men: float = 569.92, ref_power_women: float = 350.0,
                 duration_s: float = 1200):
        if ref_power_men <= 0 or ref_power_women <= 0:
            raise ValueError("Reference powers must be positive")
        if duration_s <= 0:
            raise ValueError("duration_s must be positive")
        self.ref_power_men = float(ref_power_men)
        self.ref_power_women = float(ref_power_women)
        self.duration_s = float(duration_s)
        self.teams = {}
        self.results_calculated = False

    @classmethod
    def from_reference_times(cls, distance_m: float, time_men_s: float,
                             time_women_s: float, duration_s: float = 1200
                             ) -> 'ERGNormalizer':
        """Build a normalizer from reference performances over ``distance_m``.

        Example: 2000 m world records 5:34.7 / 6:21.1 ->
        ``ERGNormalizer.from_reference_times(2000, 334.7, 381.1, 1800)``.
        """
        return cls(ref_power_men=power_from_distance_time(distance_m, time_men_s),
                   ref_power_women=power_from_distance_time(distance_m, time_women_s),
                   duration_s=duration_s)

    # ── unit conversions (kept as static methods for backward compatibility) ──
    @staticmethod
    def time2power(time_s: float) -> float:
        """Power [W] for a 2000 m time ``time_s`` [s]: ``P = 2.8 (2000/t)^3``.

        >>> round(ERGNormalizer.time2power(5*60 + 40), 2)  # 5:40 for 2K
        569.92
        """
        return power_from_distance_time(2000.0, time_s)

    @staticmethod
    def distance2power(distance_m: float) -> float:
        """Power [W] for ``distance_m`` rowed in 20 minutes.

        >>> round(ERGNormalizer.distance2power(6000), 1)
        350.0
        """
        return power_from_distance_time(distance_m, 20 * 60)

    @staticmethod
    def distance_time2power(distance_m: float, duration_s: float) -> float:
        """Power [W] for ``distance_m`` [m] rowed in ``duration_s`` [s]."""
        return power_from_distance_time(distance_m, duration_s)

    # ── teams ────────────────────────────────────────────────────────────────
    def add_team(self, name: str, n_men: int, n_women: int,
                 distance_m: Optional[float] = None, *,
                 distance_20min_m: Optional[float] = None) -> 'ERGNormalizer':
        """
        Add a team.

        Parameters
        ----------
        name : str
            Team name.
        n_men, n_women : int
            Number of men and women; each rower is assumed to row an equal
            share of the relay time.
        distance_m : float
            Total team distance in metres covered in ``duration_s``.
        distance_20min_m : float, optional
            Deprecated alias of ``distance_m`` (kept for old scripts).
        """
        if distance_m is None:
            distance_m = distance_20min_m
        if distance_m is None:
            raise TypeError("add_team() requires distance_m")
        if n_men < 0 or n_women < 0 or n_men + n_women == 0:
            raise ValueError("Team needs a non-negative number of men and women, "
                             "at least one rower in total")
        if distance_m <= 0:
            raise ValueError("distance_m must be positive")
        self.teams[name] = {'n_men': int(n_men), 'n_women': int(n_women),
                            'distance_m': float(distance_m)}
        self.results_calculated = False
        return self

    def add_teams_from_dict(self, team_dict: Dict[str, Dict]) -> 'ERGNormalizer':
        """Bulk add teams: ``{name: {'n_men', 'n_women', 'distance_m'}}``.

        The old key ``'distance_20min_m'`` is still accepted.
        """
        for name, data in team_dict.items():
            dist = data.get('distance_m', data.get('distance_20min_m'))
            self.add_team(name, data['n_men'], data['n_women'], distance_m=dist)
        return self

    # ── physics ──────────────────────────────────────────────────────────────
    def _reference_speed(self, n_men: int, n_women: int) -> float:
        """Mean reference speed [m/s] of the team (equal time shares)."""
        n = n_men + n_women
        if n == 0:
            raise ValueError("Team must have at least one member")
        return (n_men * speed_from_power(self.ref_power_men)
                + n_women * speed_from_power(self.ref_power_women)) / n

    def _calculate_ref_power(self, n_men: int, n_women: int) -> float:
        """Team reference power [W]: power mean (exponent 1/3), see module doc."""
        return power_from_speed(self._reference_speed(n_men, n_women))

    def calculate_scores(self) -> 'ERGNormalizer':
        """Compute reference distance, speed score and power score per team."""
        for name, data in self.teams.items():
            v_ref = self._reference_speed(data['n_men'], data['n_women'])
            ref_dist = v_ref * self.duration_s
            speed_score = data['distance_m'] / ref_dist
            data['ref_distance_m'] = ref_dist
            data['speed_score'] = speed_score
            data['ref_pwr'] = power_from_speed(v_ref)
            data['actual_pwr'] = power_from_distance_time(data['distance_m'],
                                                          self.duration_s)
            data['score'] = speed_score ** 3        # == actual_pwr / ref_pwr
        self.results_calculated = True
        return self

    def get_results(self) -> pd.DataFrame:
        """Results as a DataFrame, ranked by score (full precision)."""
        if not self.results_calculated:
            raise RuntimeError("Call calculate_scores() before getting results")
        rows = [{
            'Team': name,
            'Composition': f"{d['n_men']}M/{d['n_women']}W",
            'Distance (km)': d['distance_m'] / 1000.0,
            'Ref Distance (km)': d['ref_distance_m'] / 1000.0,
            'Speed Score': d['speed_score'],
            'Ref Power (W)': d['ref_pwr'],
            'Team Power (W)': d['actual_pwr'],
            'Score': d['score'],
        } for name, d in self.teams.items()]
        df = pd.DataFrame(rows).sort_values('Score', ascending=False)
        df = df.reset_index(drop=True)
        df.insert(0, 'Rank', range(1, len(df) + 1))
        return df

    def print_results(self) -> None:
        """Print a formatted results table."""
        df = self.get_results()
        fmt = {'Distance (km)': '{:.3f}'.format, 'Ref Distance (km)': '{:.3f}'.format,
               'Speed Score': '{:.4f}'.format, 'Ref Power (W)': '{:.1f}'.format,
               'Team Power (W)': '{:.1f}'.format, 'Score': '{:.4f}'.format}
        width = 100
        print("\n" + "=" * width)
        print("ERG RELAY NORMALIZATION RESULTS".center(width))
        print("=" * width)
        print(f"\nIndividual reference powers: men = {self.ref_power_men:.1f} W, "
              f"women = {self.ref_power_women:.1f} W;  relay duration = "
              f"{self.duration_s:.0f} s")
        print("\n" + df.to_string(index=False, formatters=fmt))
        print("\n" + "=" * width)
        print("Speed Score = D / D_ref;  Score = Speed Score^3 = Team Power / Ref Power")
        print("Ref Power = [mean_i P_i^(1/3)]^3 (rowers take turns, so distances add)")
        print("=" * width + "\n")

    def plot_results(self, save_path: Optional[str] = None,
                    figsize: tuple = (10, 6),
                    dist_color: str = "#011C5F",
                    score_color: str = "#BE0602",
                    transparent: bool = True,
                    dpi: int = 300) -> None:
        """
        Create visualization of results with dual-axis plot.

        Parameters
        ----------
        save_path : str, optional
            Path to save the figure. If None, displays instead.
        figsize : tuple, optional
            Figure size (width, height) in inches (default: (10, 6))
        dist_color : str, optional
            Color for distance bars (default: "#011C5F" - dark blue)
        score_color : str, optional
            Color for score line (default: "#BE0602" - red)
        transparent : bool, optional
            Whether to use transparent background (default: True)
        dpi : int, optional
            Resolution for saved figure (default: 300)

        Raises
        ------
        RuntimeError
            If calculate_scores() hasn't been called yet
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate_scores() before plotting")

        df = self.get_results()

        fig, ax1 = plt.subplots(figsize=figsize)

        # Transparent backgrounds
        if transparent:
            fig.patch.set_alpha(0.0)
            ax1.patch.set_alpha(0.0)

        # Bar plot for distance
        bars = ax1.bar(df['Team'], df['Distance (km)'],
                      color=dist_color, alpha=0.7,
                      label='Distance (km)', width=0.6)
        ax1.set_xlabel('')
        plt.setp(ax1.get_xticklabels(), rotation=60, ha='right', fontsize=12)
        ax1.set_ylabel('Distance (km)', color=dist_color,
                      fontsize=18, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor=dist_color)
        ax1.set_ylim(0, df['Distance (km)'].max() * 1.2)

        # Twin axis for score
        ax2 = ax1.twinx()
        if transparent:
            ax2.patch.set_alpha(0.0)

        line = ax2.plot(df['Team'], df['Score'],
                       color=score_color, marker='o', markersize=10,
                       ls='', label='Score',
                       markerfacecolor='white', markeredgewidth=2)
        ax2.set_ylabel('Score', color=score_color,
                      fontsize=18, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor=score_color)
        ax2.set_ylim(0, max(1.1, df['Score'].max() * 1.15))

        # Annotations for score (in score color so they stay legible against any
        # background, including above the top marker where white text vanished)
        for i, row in df.iterrows():
            ax2.annotate(f'{row["Score"]:.2f}',
                        (row['Team'], row['Score']),
                        textcoords="offset points",
                        xytext=(0, 13), ha='center',
                        fontsize=15, fontweight='bold',
                        color=score_color)

        # Title + legend so the score (not bar height) reads as the ranking
        ax1.set_title('Team performance: raw distance vs. composition-normalized score',
                      fontsize=14, fontweight='bold', pad=15)
        handles = [bars, line[0]]
        labels = [h.get_label() for h in handles]
        ax1.legend(handles, labels, loc='upper right', frameon=False, fontsize=12)

        ax1.grid(False)
        ax2.grid(False)

        for spine in ax1.spines.values():
            spine.set_color('black')
        for spine in ax2.spines.values():
            spine.set_color('black')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, transparent=transparent, dpi=dpi)
            print(f"Plot saved to: {save_path}")
        else:
            plt.show()

    def _draw_frame(self, ax1, ax2, df: pd.DataFrame, n_revealed: int,
                    dist_color: str, score_color: str, transparent: bool,
                    highlight_winner: bool) -> None:
        """Render a single reveal frame onto the given axes.

        Teams in ``df`` are assumed to be ordered slowest -> fastest. The first
        ``n_revealed`` teams (left to right) are drawn; the rest are left blank
        so axis limits stay fixed across frames (overlay/click-through safe).
        """
        teams = df['Team'].tolist()
        x = np.arange(len(teams))
        dist = df['Distance (km)'].to_numpy()
        score = df['Score'].to_numpy()
        winner_idx = len(teams) - 1  # highest score is last after slow->fast sort

        if transparent:
            ax1.patch.set_alpha(0.0)
            ax2.patch.set_alpha(0.0)

        # Distance bars (left axis) for revealed teams only
        for i in range(n_revealed):
            is_winner = highlight_winner and n_revealed > winner_idx and i == winner_idx
            ax1.bar(x[i], dist[i], width=0.6, color=dist_color,
                    alpha=0.95 if is_winner else 0.7,
                    edgecolor=score_color if is_winner else 'none',
                    linewidth=3 if is_winner else 0)

        # Score markers + labels (right axis) for revealed teams only
        for i in range(n_revealed):
            ax2.plot(x[i], score[i], color=score_color, marker='o', markersize=11,
                     ls='', markerfacecolor='white', markeredgewidth=2.5)
            # Label in score color above the marker so it is always legible
            ax2.annotate(f'{score[i]:.2f}', (x[i], score[i]),
                         textcoords="offset points", xytext=(0, 13), ha='center',
                         fontsize=15, fontweight='bold', color=score_color)

        # Fixed axes, but only reveal tick labels for teams shown so far so the
        # final ranking order is not spoiled in early frames.
        ax1.set_xticks(x)
        ax1.set_xticklabels([t if i < n_revealed else ''
                             for i, t in enumerate(teams)])
        plt.setp(ax1.get_xticklabels(), rotation=60, ha='right', fontsize=12)
        ax1.set_xlim(-0.7, len(teams) - 0.3)
        ax1.set_ylabel('Distance (km)', color=dist_color, fontsize=18, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor=dist_color)
        ax1.set_ylim(0, dist.max() * 1.2)

        ax2.set_ylabel('Score', color=score_color, fontsize=18, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor=score_color)
        ax2.set_ylim(0, max(1.1, score.max() * 1.15))

        ax1.grid(False)
        ax2.grid(False)
        for spine in list(ax1.spines.values()) + list(ax2.spines.values()):
            spine.set_color('black')

    def animate_results(self, save_dir: str = "animation_frames",
                        gif_path: Optional[str] = "team_comparison.gif",
                        figsize: tuple = (10, 6),
                        dist_color: str = "#011C5F",
                        score_color: str = "#BE0602",
                        transparent: bool = True,
                        dpi: int = 150,
                        fps: float = 1.5,
                        hold_final: int = 3,
                        highlight_winner: bool = True) -> List[str]:
        """
        Generate an animated reveal of the ranking, slowest team to fastest.

        Teams are placed left (lowest score) to right (highest score) with the
        axes fixed across every frame, then revealed one at a time so the winner
        appears last. Produces both:

        * ``N`` cumulative PNG frames in ``save_dir`` (``frame_01.png`` ...) for
          click-through in PowerPoint or for overlaying as layers, and
        * an optional GIF stitched from those frames (requires Pillow).

        Parameters
        ----------
        save_dir : str, optional
            Directory for the PNG frames (created if needed). Default
            "animation_frames".
        gif_path : str, optional
            Path for the assembled GIF. If None, no GIF is written (frames only).
        figsize : tuple, optional
            Figure size (width, height) in inches (default: (10, 6)).
        dist_color, score_color : str, optional
            Colors for the distance bars and score markers/labels.
        transparent : bool, optional
            Transparent background for the PNG frames (default: True). The GIF is
            always composited on white (GIF has no real alpha channel).
        dpi : int, optional
            Resolution for the saved frames (default: 150).
        fps : float, optional
            Frames per second for the GIF (default: 1.5).
        hold_final : int, optional
            Extra repeats of the final full frame so the GIF pauses on the result
            (default: 3).
        highlight_winner : bool, optional
            Outline the winning team's bar on the final frame (default: True).

        Returns
        -------
        list of str
            Paths of the PNG frames written, in reveal order.

        Raises
        ------
        RuntimeError
            If calculate_scores() hasn't been called yet.
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate_scores() before animating")

        # Order slowest -> fastest so the reveal builds toward the winner
        df = self.get_results().sort_values('Score', ascending=True).reset_index(drop=True)
        n_teams = len(df)

        os.makedirs(save_dir, exist_ok=True)
        frame_paths: List[str] = []

        for k in range(1, n_teams + 1):
            fig, ax1 = plt.subplots(figsize=figsize)
            ax2 = ax1.twinx()
            if transparent:
                fig.patch.set_alpha(0.0)
            self._draw_frame(ax1, ax2, df, k, dist_color, score_color,
                             transparent, highlight_winner)
            fig.tight_layout()
            path = os.path.join(save_dir, f"frame_{k:02d}.png")
            fig.savefig(path, transparent=transparent, dpi=dpi)
            plt.close(fig)
            frame_paths.append(path)

        print(f"Wrote {n_teams} frames to: {save_dir}")

        if gif_path:
            try:
                from PIL import Image
            except ImportError:
                print("Pillow not installed; skipping GIF "
                      "(`pip install pillow`). PNG frames are still available.")
                return frame_paths

            def _on_white(p):
                img = Image.open(p).convert("RGBA")
                bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
                return Image.alpha_composite(bg, img).convert("RGB")

            seq = [_on_white(p) for p in frame_paths]
            seq += [seq[-1]] * max(0, hold_final)  # pause on the result
            duration_ms = int(1000 / fps)
            seq[0].save(gif_path, save_all=True, append_images=seq[1:],
                        duration=duration_ms, loop=0)
            print(f"GIF saved to: {gif_path}")

        return frame_paths
