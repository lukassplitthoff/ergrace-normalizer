"""
Race formats on the ergometer: relay races and mixed (individual) races.

Both formats come in two flavours:

* **fixed time**      -- everybody rows for ``time``; the result is a distance.
* **fixed distance**  -- everybody rows ``distance``; the result is a time.

Before the race, :meth:`handicaps` gives what each entry must do so that all
entries rowing at the same fraction of their reference power finish together:

* fixed distance -> a **staggered start** (slowest entry starts first);
* fixed time     -> a **target distance** (and the equivalent metre credit).

After the race, :meth:`record` takes the results and :meth:`results` ranks
entries by the power score ``sigma``, the fraction of reference power sustained.

Physics (see ``examples/RRC2026/publication`` for the derivation)
------------------------------------------------------------------
Every category has a reference speed ``v = d_ref / t_ref`` and power
``P = c v^3``.  Under the uniform-effort hypothesis each athlete rows at
``sigma^(1/3)`` times their reference speed.  An entry's reference speed is

* individual (mixed race):          its category's reference speed;
* relay with equal *time* shares:   arithmetic mean of the rowers' speeds
  (distances add);
* relay with equal *distance* legs: harmonic mean of the rowers' speeds
  (times add).

With the observed mean speed ``v_obs = D / T`` the score is
``sigma = (v_obs / v_ref)^3``; the constant ``c`` cancels.  References at
2000 m are applied at other race distances assuming constant power; this
shifts absolute times but not the handicap *ratios*.
"""

from collections import Counter
from typing import Dict, List, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

from .references import (References, TimeLike, format_time, parse_time)

Number = Union[int, float]

_ABBR = {"junior": "Jun", "senior": "Sen", "master": "Mas"}


def _abbr(ref: References, label: str) -> str:
    age, g = ref.key(label)
    return f"{_ABBR.get(age, age.capitalize())} {g}"


class _Race:
    """Shared logic of RelayRace and MixedRace."""

    kind = "race"

    def __init__(self, time: Optional[TimeLike] = None, distance: Optional[Number] = None,
                 references: Optional[References] = None, level: float = 1.0):
        if (time is None) == (distance is None):
            raise ValueError("Give exactly one of time=... or distance=...")
        self.time_s = parse_time(time) if time is not None else None
        self.distance_m = float(distance) if distance is not None else None
        if (self.time_s is not None and self.time_s <= 0) or \
           (self.distance_m is not None and self.distance_m <= 0):
            raise ValueError("Race time/distance must be positive")
        if not 0 < level <= 2:
            raise ValueError("level is the expected fraction of reference power, e.g. 0.7")
        self.refs = references or References.default()
        self.level = float(level)
        self.entries: Dict[str, Dict] = {}
        self._results: Dict[str, float] = {}

    # ── format ───────────────────────────────────────────────────────────────
    @property
    def fixed_distance(self) -> bool:
        return self.distance_m is not None

    @property
    def format(self) -> str:
        if self.fixed_distance:
            return f"{self.distance_m:.0f} m"
        return format_time(self.time_s, decimals=0)

    # ── predictions ──────────────────────────────────────────────────────────
    def _expected_speed(self, name: str) -> float:
        """Speed expected at the handicap level: v_ref * level^(1/3)."""
        return self.entries[name]["ref_speed"] * self.level ** (1 / 3)

    def handicaps(self) -> pd.DataFrame:
        """What each entry must do so that everybody finishes together.

        Fixed distance: ``Start offset`` [s] after the first start (slowest
        entry first).  Fixed time: ``Target distance`` [m] and ``Credit`` [m],
        the metres added to an entry's result to compare with the fastest.
        """
        if not self.entries:
            raise RuntimeError("No entries")
        rows = []
        for name, e in self.entries.items():
            v = self._expected_speed(name)
            row = {"Entry": name, "Category": e["label"], "Ref Speed (m/s)": e["ref_speed"]}
            if self.fixed_distance:
                row["Expected Time (s)"] = self.distance_m / v
            else:
                row["Target Distance (m)"] = v * self.time_s
            rows.append(row)
        df = pd.DataFrame(rows)
        if self.fixed_distance:
            t_max = df["Expected Time (s)"].max()
            df["Start Offset (s)"] = t_max - df["Expected Time (s)"]
            df = df.sort_values("Start Offset (s)").reset_index(drop=True)
            df["Start Offset"] = [format_time(s, sign=True) for s in df["Start Offset (s)"]]
            df["Expected Time"] = [format_time(s) for s in df["Expected Time (s)"]]
            df.insert(0, "Start #", range(1, len(df) + 1))
        else:
            d_max = df["Target Distance (m)"].max()
            df["Credit (m)"] = d_max - df["Target Distance (m)"]
            df = df.sort_values("Target Distance (m)").reset_index(drop=True)
        return df

    # ── results ──────────────────────────────────────────────────────────────
    def record(self, results: Mapping) -> "_Race":
        """Enter results: distances [m] for time races, times for distance races."""
        for key, value in results.items():
            name = self._resolve(key)
            val = parse_time(value) if self.fixed_distance else float(value)
            if val <= 0:
                raise ValueError(f"Result for {name!r} must be positive")
            self._results[name] = val
        return self

    def _resolve(self, key) -> str:
        if key in self.entries:
            return key
        raise KeyError(f"Unknown entry {key!r}")

    def results(self) -> pd.DataFrame:
        """Ranking by power score sigma = (v_obs / v_ref)^3."""
        if not self._results:
            raise RuntimeError("No results recorded; call record({...}) first")
        hc = self.handicaps().set_index("Entry")
        rows = []
        for name, val in self._results.items():
            e = self.entries[name]
            if self.fixed_distance:
                d, t = self.distance_m, val
            else:
                d, t = val, self.time_s
            s = (d / t) / e["ref_speed"]
            row = {"Entry": name, "Category": e["label"],
                   "Distance (m)": d, "Time (s)": t, "Time": format_time(t),
                   "Split /500 m": format_time(500 * t / d),
                   "Speed Score": s, "Score": s ** 3}
            if self.fixed_distance:
                off = hc.loc[name, "Start Offset (s)"]
                row["Start Offset (s)"] = off
                row["Finish Clock (s)"] = off + t
                row["Vs Handicap (s)"] = off + t - (hc["Start Offset (s)"]
                                                    + hc["Expected Time (s)"]).max()
            else:
                row["Target Distance (m)"] = hc.loc[name, "Target Distance (m)"]
                row["Vs Handicap (m)"] = d - row["Target Distance (m)"]
            rows.append(row)
        df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
        df.insert(0, "Rank", range(1, len(df) + 1))
        if self.fixed_distance:
            order = df["Finish Clock (s)"].rank(method="min").astype(int)
            df.insert(df.columns.get_loc("Finish Clock (s)") + 1, "Line Order", order)
        return df

    # ── printing ─────────────────────────────────────────────────────────────
    def _print_table(self, title: str, df: pd.DataFrame, cols: List[str], fmt: Dict):
        width = max(80, len(df[cols].to_string(index=False).split("\n")[0]))
        print("\n" + "=" * width)
        print(title.center(width))
        print("=" * width)
        print(df[cols].to_string(index=False, formatters=fmt))
        print("=" * width + "\n")

    def print_handicaps(self) -> None:
        df = self.handicaps()
        lvl = f"expected level {self.level:.0%} of reference power"
        if self.fixed_distance:
            cols = ["Start #", "Entry", "Category", "Expected Time", "Start Offset"]
            if "Lane" in df:
                cols.insert(2, "Lane")
            title = f"{self.kind.upper()} {self.format}: STAGGERED START ({lvl})"
            self._print_table(title, df, cols, {})
        else:
            cols = ["Entry", "Category", "Target Distance (m)", "Credit (m)"]
            title = f"{self.kind.upper()} {self.format}: TARGET DISTANCES ({lvl})"
            self._print_table(title, df, cols, {"Target Distance (m)": "{:.0f}".format,
                                                "Credit (m)": "{:.0f}".format})

    def print_results(self) -> None:
        df = self.results()
        fmt = {"Distance (m)": "{:.0f}".format, "Speed Score": "{:.4f}".format,
               "Score": "{:.4f}".format, "Vs Handicap (m)": "{:+.0f}".format,
               "Vs Handicap (s)": lambda s: format_time(s, sign=True)}
        if self.fixed_distance:
            cols = ["Rank", "Entry", "Category", "Time", "Split /500 m", "Speed Score",
                    "Score", "Line Order", "Vs Handicap (s)"]
        else:
            cols = ["Rank", "Entry", "Category", "Distance (m)", "Split /500 m",
                    "Speed Score", "Score", "Vs Handicap (m)"]
        extra = [c for c in ("Lane", "Team") if c in df]
        cols = cols[:2] + extra + cols[2:]
        self._print_table(f"{self.kind.upper()} {self.format}: RESULTS "
                          "(Score = fraction of reference power)", df, cols, fmt)

    # ── plotting (see ergrace.plotting) ──────────────────────────────────────
    def plot_handicaps(self, save_path: Optional[str] = None, **kw):
        from .plotting import plot_handicaps
        return plot_handicaps(self, save_path, **kw)

    def plot_results(self, save_path: Optional[str] = None, **kw):
        from .plotting import plot_results
        return plot_results(self, save_path, **kw)


class RelayRace(_Race):
    """
    Relay: each team shares one ergometer, rowers take turns.

    Parameters
    ----------
    time : str or float, optional
        Race duration (``"30:00"`` or seconds) -- result per team is a distance.
    distance : float, optional
        Race distance in metres -- result per team is a time.
    teams : dict
        ``{team: ["Junior M", "Senior W", "Senior M"]}`` or
        ``{team: {"Senior M": 2, "Senior W": 3}}``.
    split : {"time", "distance"}, optional
        How the work is shared: equal *time* per rower (swap on the clock) or
        equal *distance* legs.  Default: ``"time"`` for timed races and
        ``"distance"`` for distance races.
    references : References, optional
        Category references (default: :meth:`References.default`).
    level : float, optional
        Expected fraction of reference power used for the handicaps
        (default 1.0).  Club crews typically row at 0.6--0.8; the level
        scales start offsets and target distances but not their order.

    Examples
    --------
    >>> relay = RelayRace(time="30:00", teams={
    ...     "Team 1": ["Junior M", "Senior W", "Senior M"],
    ...     "Team 2": ["Junior M", "Senior W", "Senior W"]})
    >>> relay.print_handicaps()                       # doctest: +SKIP
    >>> relay.record({"Team 1": 8100, "Team 2": 7900}).print_results()  # doctest: +SKIP
    """

    kind = "relay"

    def __init__(self, time: Optional[TimeLike] = None, distance: Optional[Number] = None,
                 teams: Optional[Mapping] = None, split: Optional[str] = None,
                 references: Optional[References] = None, level: float = 1.0):
        super().__init__(time, distance, references, level)
        self.split = split or ("distance" if self.fixed_distance else "time")
        if self.split not in ("time", "distance"):
            raise ValueError("split must be 'time' or 'distance'")
        for name, members in (teams or {}).items():
            self.add_team(name, members)

    def add_team(self, name: str, members: Union[Sequence[str], Mapping[str, int]]
                 ) -> "RelayRace":
        """Add a team: list of category labels or ``{label: count}``."""
        if isinstance(members, Mapping):
            labels = [lab for lab, n in members.items() for _ in range(int(n))]
        elif isinstance(members, str):
            labels = [members]
        else:
            labels = list(members)
        if not labels:
            raise ValueError(f"Team {name!r} has no rowers")
        speeds = np.array([self.refs.speed(lab) for lab in labels])
        if self.split == "time":
            v_ref = float(speeds.mean())                         # distances add
        else:
            v_ref = float(len(speeds) / np.sum(1.0 / speeds))    # times add
        counts = Counter(_abbr(self.refs, lab) for lab in labels)
        order = sorted(counts, key=lambda k: (k.split()[1], k.split()[0]))
        label = " + ".join(f"{counts[k]} {k}" if counts[k] > 1 else k for k in order)
        self.entries[name] = {"members": [self.refs.label(lab) for lab in labels],
                              "label": label, "ref_speed": v_ref}
        return self


class MixedRace(_Race):
    """
    Mixed race: individuals of different categories race each other.

    Parameters
    ----------
    distance : float, optional
        Race distance in metres -- results are times.
    time : str or float, optional
        Race duration -- results are distances.
    lanes : dict
        ``{lane: "Junior W"}``, ``{lane: ("Anna", "Junior W")}`` or
        ``{lane: {"name": "Anna", "category": "Junior W", "team": "Club A"}}``.
        A ``team`` label enables :meth:`team_results`.
    references, level
        As for :class:`RelayRace`.

    Results can be recorded by lane or by athlete name.

    Examples
    --------
    >>> race = MixedRace(distance=2000, lanes={1: "Junior W", 2: ("Erik", "Senior M")})
    >>> race.print_handicaps()                                     # doctest: +SKIP
    >>> race.record({1: "7:30.2", "Erik": "6:45.0"}).print_results()  # doctest: +SKIP
    """

    kind = "mixed race"

    def __init__(self, distance: Optional[Number] = None, time: Optional[TimeLike] = None,
                 lanes: Optional[Mapping] = None, references: Optional[References] = None,
                 level: float = 1.0):
        super().__init__(time, distance, references, level)
        self._lane_to_name: Dict = {}
        for lane, spec in (lanes or {}).items():
            self.add_athlete(lane, spec)

    def add_athlete(self, lane, spec) -> "MixedRace":
        """Add an athlete in ``lane``; ``spec`` as described in the class doc."""
        if isinstance(spec, str):
            name, cat, team = None, spec, None
        elif isinstance(spec, Mapping):
            name, cat, team = spec.get("name"), spec["category"], spec.get("team")
        else:
            name, cat = spec[0], spec[1]
            team = spec[2] if len(spec) > 2 else None
        name = name or f"Lane {lane}"
        if name in self.entries:
            raise ValueError(f"Duplicate athlete name {name!r}")
        self.entries[name] = {"lane": lane, "team": team,
                              "label": _abbr(self.refs, cat),
                              "category": self.refs.label(cat),
                              "ref_speed": self.refs.speed(cat)}
        self._lane_to_name[lane] = name
        return self

    def _resolve(self, key) -> str:
        if key in self.entries:
            return key
        if key in self._lane_to_name:
            return self._lane_to_name[key]
        raise KeyError(f"Unknown lane or athlete {key!r}")

    def results(self) -> pd.DataFrame:
        df = super().results()
        df.insert(1, "Lane", [self.entries[n]["lane"] for n in df["Entry"]])
        if any(self.entries[n]["team"] for n in df["Entry"]):
            df.insert(3, "Team", [self.entries[n]["team"] for n in df["Entry"]])
        return df

    def handicaps(self) -> pd.DataFrame:
        df = super().handicaps()
        df.insert(df.columns.get_loc("Entry") + 1, "Lane",
                  [self.entries[n]["lane"] for n in df["Entry"]])
        return df

    def team_results(self) -> pd.DataFrame:
        """Teams ranked by the mean power score of their athletes."""
        df = self.results()
        if "Team" not in df:
            raise RuntimeError("No team labels given for the athletes")
        g = (df.dropna(subset=["Team"]).groupby("Team")
               .agg(Athletes=("Entry", "count"), Score=("Score", "mean"),
                    Best=("Score", "max"), Worst=("Score", "min"))
               .sort_values("Score", ascending=False).reset_index())
        g.insert(0, "Rank", range(1, len(g) + 1))
        return g

    def print_team_results(self) -> None:
        df = self.team_results()
        f = "{:.4f}".format
        self._print_table(f"{self.kind.upper()} {self.format}: TEAMS (mean power score)",
                          df, list(df.columns), {"Score": f, "Best": f, "Worst": f})
