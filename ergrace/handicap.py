"""
Handicap (pursuit) race format for ergrace.

This module adds a second race format on top of the erg power model in
:mod:`ergrace.normalizer`. In a handicap / pursuit race, boats of different
*classes* (1x, 2x, 4x, 8+), *genders* (male/female) and *age categories*
(junior, senior, master) race over the same N km course and should all arrive
at the same time. The slowest boat starts first; every other boat is held back
by the difference between its expected finish time and the slowest boat's, so
that crews of identical reference ability would cross the line together.

The prediction is purely *reference based*: each crew's expected time is built
from a table of on-water 2 km reference times (one per boat class / gender /
category), with no per-crew test result required.

Why the model routes through power
----------------------------------
Time is **not** additive across the seats of a boat, but per-person **power**
is. So a crew's reference is the *mean of the per-seat reference powers*, not a
mean of times. For a mixed crew these two give different answers and the power
mean is the correct one. The same power formula used by the erg normalizer is
reused here::

    P = 2.8 * (2000 / t_2k) ** 3          # time  -> power
    t = distance_m * (2.8 / P) ** (1/3)   # power -> time

What this tool decides (and does not)
-------------------------------------
The predicted times are used *only* to set the start stagger. If every crew
rowed exactly to reference they would dead-heat. In the real race the first
boat across the finish wins, so the finish order on the water is the placing --
not something this tool computes.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional

from .normalizer import ERGNormalizer

# Number of seats per boat class.
SEATS = {"1x": 1, "2x": 2, "4x": 4, "8+": 8}

# Default location of the bundled reference-times table.
_DEFAULT_REF_PATH = os.path.join(os.path.dirname(__file__), "data",
                                 "reference_times_2k.json")

_GENDER_ABBR = {"male": "M", "female": "F"}
_CATEGORY_ABBR = {"junior": "jun", "senior": "sen", "master": "mas"}


class HandicapRace:
    """
    Organize a handicap / pursuit race so all crews arrive together.

    Parameters
    ----------
    distance_km : float
        Race distance in kilometres.
    reference_path : str, optional
        Path to a reference-times JSON file. Defaults to the table bundled with
        the package (``ergrace/data/reference_times_2k.json``).

    Examples
    --------
    >>> race = HandicapRace(distance_km=6)
    >>> race.add_crew('Crew 1', '1x', [{'gender': 'male', 'category': 'senior'}])
    >>> race.add_crew('Crew 2', '8+',
    ...               [{'gender': 'male', 'category': 'senior', 'count': 3},
    ...                {'gender': 'female', 'category': 'senior', 'count': 5}])
    >>> race.calculate().print_results()
    """

    def __init__(self, distance_km: float, reference_path: Optional[str] = None):
        self.distance_km = distance_km
        self.distance_m = distance_km * 1000.0
        self.reference_path = reference_path or _DEFAULT_REF_PATH

        with open(self.reference_path, "r", encoding="utf-8") as fh:
            ref_doc = json.load(fh)

        self.ref_distance_m = ref_doc.get("distance_m", 2000)
        # Raw "M:SS.s" strings (for the reference-times table output).
        self.ref_times_raw = ref_doc["reference_times"]
        # Parsed to seconds for computation.
        self.ref_times_s = {
            boat: {
                gender: {cat: self.parse_time(t) for cat, t in cats.items()}
                for gender, cats in genders.items()
            }
            for boat, genders in self.ref_times_raw.items()
        }

        self.crews: Dict[str, Dict] = {}
        self.results_calculated = False

    # ------------------------------------------------------------------ #
    # Time / power helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def parse_time(value) -> float:
        """Parse a ``"M:SS.s"`` / ``"MM:SS"`` string (or a number) to seconds."""
        if isinstance(value, (int, float)):
            return float(value)
        value = value.strip()
        if ":" in value:
            mins, secs = value.split(":")
            return int(mins) * 60 + float(secs)
        return float(value)

    @staticmethod
    def format_time(seconds: float) -> str:
        """Format seconds as ``"M:SS.s"``."""
        minutes = int(seconds // 60)
        secs = seconds - minutes * 60
        return f"{minutes}:{secs:04.1f}"

    @staticmethod
    def power2time(power: float, distance_m: float) -> float:
        """
        Convert an average power to the time for ``distance_m`` (inverse of
        :meth:`ERGNormalizer.time2power` generalised to any distance).

        ``P = 2.8 * (distance/time)**3``  ->  ``time = distance * (2.8/P)**(1/3)``
        """
        return distance_m * (2.8 / power) ** (1.0 / 3.0)

    # ------------------------------------------------------------------ #
    # Crew management
    # ------------------------------------------------------------------ #
    def _person_ref_power(self, boat_class: str, gender: str, category: str) -> float:
        """Per-seat reference power for one rower of the given profile."""
        try:
            t_ref = self.ref_times_s[boat_class][gender][category]
        except KeyError:
            raise ValueError(
                f"No reference time for boat_class={boat_class!r}, "
                f"gender={gender!r}, category={category!r}. "
                f"Check {self.reference_path}."
            )
        return ERGNormalizer.time2power(t_ref)

    def add_crew(self, name: str, boat_class: str,
                 members: List[Dict]) -> "HandicapRace":
        """
        Add a crew (boat) to the race.

        Parameters
        ----------
        name : str
            Crew name.
        boat_class : str
            One of ``"1x"``, ``"2x"``, ``"4x"``, ``"8+"``.
        members : list of dict
            One entry per group of identical rowers, each with keys
            ``'gender'`` (male/female), ``'category'`` (junior/senior/master,
            default ``'senior'``) and ``'count'`` (default 1). The total count
            must equal the number of seats in ``boat_class``.

        Returns
        -------
        HandicapRace
            Self, for method chaining.
        """
        if boat_class not in SEATS:
            raise ValueError(
                f"Unknown boat_class {boat_class!r}; expected one of {list(SEATS)}.")

        seats = []
        for m in members:
            gender = m["gender"]
            category = m.get("category", "senior")
            count = int(m.get("count", 1))
            for _ in range(count):
                seats.append({"gender": gender, "category": category})

        if len(seats) != SEATS[boat_class]:
            raise ValueError(
                f"Crew {name!r}: {len(seats)} rower(s) given but a {boat_class} "
                f"has {SEATS[boat_class]} seat(s).")

        self.crews[name] = {"boat_class": boat_class, "seats": seats}
        self.results_calculated = False
        return self

    def add_crews_from_list(self, crews: List[Dict]) -> "HandicapRace":
        """
        Bulk-add crews from a list of dicts with keys ``name``, ``boat_class``,
        ``members`` (see :meth:`add_crew`).
        """
        for c in crews:
            self.add_crew(c["name"], c["boat_class"], c["members"])
        return self

    @staticmethod
    def _composition_label(seats: List[Dict]) -> str:
        """Compact composition string, e.g. ``"3M-sen / 5F-sen"``."""
        groups: Dict[tuple, int] = {}
        order: List[tuple] = []
        for s in seats:
            key = (s["gender"], s["category"])
            if key not in groups:
                groups[key] = 0
                order.append(key)
            groups[key] += 1
        parts = []
        for gender, category in order:
            parts.append(f"{groups[(gender, category)]}"
                         f"{_GENDER_ABBR.get(gender, gender)}-"
                         f"{_CATEGORY_ABBR.get(category, category)}")
        return " / ".join(parts)

    # ------------------------------------------------------------------ #
    # Computation
    # ------------------------------------------------------------------ #
    def calculate(self) -> "HandicapRace":
        """
        Compute crew power, predicted finish time and the handicap start
        stagger for every crew. Returns self for chaining.
        """
        if not self.crews:
            raise RuntimeError("Add at least one crew before calling calculate().")

        for name, crew in self.crews.items():
            boat = crew["boat_class"]
            powers = [self._person_ref_power(boat, s["gender"], s["category"])
                      for s in crew["seats"]]
            crew_power = float(np.mean(powers))            # average in power space
            predicted_time_s = self.power2time(crew_power, self.distance_m)

            crew["crew_power"] = crew_power
            crew["predicted_time_s"] = predicted_time_s
            crew["composition"] = self._composition_label(crew["seats"])

        # Slowest first: largest predicted time starts at offset 0.
        t_max = max(c["predicted_time_s"] for c in self.crews.values())
        order = sorted(self.crews.items(),
                       key=lambda kv: kv[1]["predicted_time_s"], reverse=True)

        prev_t = None
        for i, (name, crew) in enumerate(order, start=1):
            crew["start_order"] = i
            crew["start_offset_s"] = t_max - crew["predicted_time_s"]
            # Gap to the boat that started immediately in front (next slower).
            crew["gap_to_prev_s"] = 0.0 if prev_t is None \
                else prev_t - crew["predicted_time_s"]
            prev_t = crew["predicted_time_s"]

        self.results_calculated = True
        return self

    def _ordered_crews(self) -> List[Dict]:
        """Crews as a list of dicts (incl. name), in start order (slowest first)."""
        rows = [dict(name=n, **c) for n, c in self.crews.items()]
        rows.sort(key=lambda r: r["start_order"])
        return rows

    # ------------------------------------------------------------------ #
    # Outputs
    # ------------------------------------------------------------------ #
    def get_results(self) -> pd.DataFrame:
        """
        Results as a DataFrame, ordered by start (slowest crew first).

        Columns: Start #, Crew, Boat, Composition, Crew Power (W),
        Predicted Time, Start Offset (s), Gap to Prev (s).
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate() before getting results.")

        data = []
        for r in self._ordered_crews():
            data.append({
                "Start #": r["start_order"],
                "Crew": r["name"],
                "Boat": r["boat_class"],
                "Composition": r["composition"],
                "Crew Power (W)": round(r["crew_power"], 1),
                "Predicted Time": self.format_time(r["predicted_time_s"]),
                "Start Offset (s)": round(r["start_offset_s"], 1),
                "Gap to Prev (s)": round(r["gap_to_prev_s"], 1),
            })
        return pd.DataFrame(data)

    def print_results(self) -> None:
        """Print the formatted handicap-race table to the console."""
        df = self.get_results()
        title = f"HANDICAP RACE - {self.distance_km:g} km".center(80)
        print("\n" + "=" * 80)
        print(title)
        print("=" * 80)
        print(f"\nReference table: {os.path.basename(self.reference_path)} "
              f"({self.ref_distance_m:g} m per-seat times)")
        print("Start order is slowest crew first; all crews are predicted to "
              "finish together.")
        print("\n" + df.to_string(index=False))
        print("\n" + "=" * 80)
        print("Start Offset = time held behind the first (slowest) starter.")
        print("Gap to Prev  = start interval to the boat immediately in front.")
        print("On the water the first boat across the line wins.")
        print("=" * 80 + "\n")

    def print_reference_table(self) -> None:
        """Print the loaded 2 km reference times as a table."""
        rows = []
        for boat, genders in self.ref_times_raw.items():
            for gender, cats in genders.items():
                row = {"Boat": boat, "Gender": gender}
                row.update(cats)
                rows.append(row)
        df = pd.DataFrame(rows)

        print("\n" + "=" * 80)
        print(f"REFERENCE 2 km TIMES (per seat) - "
              f"{os.path.basename(self.reference_path)}".center(80))
        print("=" * 80)
        print("\n" + df.to_string(index=False))
        print("\n" + "=" * 80)
        print("Edit the JSON to match your club/event; times are 'M:SS.s'.")
        print("=" * 80 + "\n")

    def plot_results(self, save_path: Optional[str] = None,
                     figsize: tuple = (11, 6),
                     bar_color: str = "#1A3A6B",
                     accent_color: str = "#C0392B",
                     transparent: bool = True,
                     dpi: int = 300) -> None:
        """
        Draw the pursuit/stagger diagram: one row per crew (slowest at top),
        each bar spanning from its start to the common finish line. Total
        predicted time is annotated on each bar and the start interval to the
        adjacent boat is annotated at the start edge.

        Parameters mirror the erg normalizer's plot conventions (palette,
        ``transparent``, ``dpi``).
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate() before plotting.")

        rows = self._ordered_crews()
        n = len(rows)
        t_max = max(r["predicted_time_s"] for r in rows)  # common finish (s)

        # Plot slowest at the top -> reverse y so start_order 1 is highest.
        y = np.arange(n)[::-1]

        fig, ax = plt.subplots(figsize=figsize)
        if transparent:
            fig.patch.set_alpha(0.0)
            ax.patch.set_alpha(0.0)

        for yi, r in zip(y, rows):
            start = r["start_offset_s"]
            ax.barh(yi, t_max - start, left=start, height=0.55,
                    color=bar_color, alpha=0.85, zorder=2)
            # Start marker
            ax.plot(start, yi, marker="o", markersize=9, color=accent_color,
                    markerfacecolor="white", markeredgewidth=2.0, zorder=4)
            # Total predicted time on the bar
            ax.annotate(self.format_time(r["predicted_time_s"]),
                        (start + (t_max - start) / 2.0, yi),
                        ha="center", va="center", color="white",
                        fontsize=10, fontweight="bold", zorder=5)
            # Gap to the boat in front, at the start edge
            if r["gap_to_prev_s"] > 0:
                ax.annotate(f"+{r['gap_to_prev_s']:.0f}s",
                            (start, yi), textcoords="offset points",
                            xytext=(-6, 0), ha="right", va="center",
                            color=accent_color, fontsize=9, fontweight="bold",
                            zorder=5)

        # Common finish line
        ax.axvline(t_max, color=accent_color, linestyle="--", linewidth=1.5,
                   zorder=1)
        ax.annotate("FINISH", (t_max, y.max() + 0.55),
                    ha="center", va="bottom", color=accent_color,
                    fontsize=11, fontweight="bold")

        ax.set_yticks(y)
        ax.set_yticklabels([f"{r['name']} ({r['boat_class']})" for r in rows],
                           fontsize=11)
        ax.set_xlabel("Time from first start [s]", fontsize=13, fontweight="bold")
        ax.set_title(
            f"Handicap race - {self.distance_km:g} km: staggered starts, "
            f"common finish", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlim(-0.04 * t_max, 1.04 * t_max)
        ax.set_ylim(-0.7, y.max() + 0.9)
        ax.grid(axis="x", linestyle=":", color="gray", alpha=0.5, zorder=0)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, transparent=transparent, dpi=dpi)
            print(f"Plot saved to: {save_path}")
        else:
            plt.show()
