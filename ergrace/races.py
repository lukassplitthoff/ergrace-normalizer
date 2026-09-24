"""
Race formats with composition-fair handicaps and scoring.

Which class for which race?
---------------------------
=================  ==========================================  =====================
Class              Race                                        Entry = ...
=================  ==========================================  =====================
:class:`RelayRace`  a team shares ONE ergometer, rowers take   a team (any size and
                   turns (swap on the clock or equal legs)     mix of categories)
:class:`MixedRace`  individuals of different categories race   one athlete
                   each other, one ergometer each
:class:`CrewRace`   boats of different classes (1x ... 8+)      one crew in one boat
                   with mixed crews race on the water
=================  ==========================================  =====================

Every class takes exactly one of ``time=`` (fixed duration, the result is a
distance) or ``distance=`` (fixed distance, the result is a time).

Before the race, ``handicaps()`` gives what each entry must do so that all
entries rowing at the same fraction of their reference power finish together:

* fixed distance -> a **staggered start** (slowest entry starts first);
* fixed time     -> a **target distance** (and the equivalent metre credit).

After the race, ``record({...})`` takes the results and ``results()`` ranks the
entries by the power score ``sigma``, the fraction of reference power sustained.
``plot_handicaps()`` and ``plot_results()`` draw both.

Physics (derivation in ``examples/RRC2026/publication``)
--------------------------------------------------------
Every category has a reference speed ``v = d_ref / t_ref`` and power
``P = c v^3``.  Under the uniform-effort hypothesis each athlete rows at
``sigma^(1/3)`` times their reference speed.  An entry's reference speed is a
power mean of its athletes' reference speeds, set by what adds up:

* RelayRace, equal *time* shares   -> distances add  -> mean of v        (exponent 1)
* RelayRace, equal *distance* legs -> times add      -> harmonic mean    (exponent -1)
* MixedRace                        -> one athlete    -> own v
* CrewRace, all seats pull at once -> powers add     -> (mean of v^3)^(1/3) (exponent 3)

With the observed mean speed ``v_obs = D / T`` the score is
``sigma = (v_obs / v_ref)^3``; the constant ``c`` cancels.

References are 2000 m performances.  By default they are applied at any race
distance assuming constant power (absolute times optimistic for long races;
ratios and rankings unaffected).  ``fatigue=5`` instead applies Paul's law:
the reference split slows by ``fatigue`` seconds per 500 m for every doubling
of the distance each athlete actually rows.
"""

from collections import Counter
from typing import Dict, List, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

from .references import (BoatReferences, References, TimeLike, boat_seats,
                         format_time, parse_category, parse_time)

Number = Union[int, float]

_ABBR = {"junior": "Jun", "senior": "Sen", "master": "Mas"}


def _abbr(ref: References, label: str) -> str:
    age, g = ref.key(label)
    return f"{_ABBR.get(age, age.capitalize())} {g}"


def _abbr_key(label: str) -> str:
    """``"Junior M"`` -> ``"Jun M"``."""
    age, g = parse_category(label)
    return f"{_ABBR.get(age, age.capitalize())} {g}"


class _Race:
    """Shared logic of RelayRace and MixedRace."""

    kind = "race"

    def __init__(self, time: Optional[TimeLike] = None, distance: Optional[Number] = None,
                 references=None, level: float = 1.0, fatigue: Optional[float] = None):
        if (time is None) == (distance is None):
            raise ValueError("Give exactly one of time=... or distance=...")
        self.time_s = parse_time(time) if time is not None else None
        self.distance_m = float(distance) if distance is not None else None
        if (self.time_s is not None and self.time_s <= 0) or \
           (self.distance_m is not None and self.distance_m <= 0):
            raise ValueError("Race time/distance must be positive")
        if not 0 < level <= 2:
            raise ValueError("level is the expected fraction of reference power, e.g. 0.7")
        self.refs = references if references is not None else self._default_refs()
        self.level = float(level)
        if fatigue is not None and fatigue < 0:
            raise ValueError("fatigue is in seconds per 500 m per doubling, >= 0")
        self.fatigue = fatigue
        self.entries: Dict[str, Dict] = {}
        self._results: Dict[str, float] = {}

    @staticmethod
    def _default_refs():
        return References.default()

    def _fatigued(self, v_ref: float, effort_m: float) -> float:
        """Reference speed over ``effort_m`` metres (Paul's law if ``fatigue``)."""
        if not self.fatigue:
            return v_ref
        split = 500.0 / v_ref + self.fatigue * np.log2(effort_m / self.refs.distance_m)
        if split <= 0:
            raise ValueError("fatigue correction gives a non-positive split")
        return 500.0 / split

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
            df["Gap to Prev (s)"] = df["Start Offset (s)"].diff().fillna(0.0)
            df.insert(0, "Start #", range(1, len(df) + 1))
        else:
            d_max = df["Target Distance (m)"].max()
            df["Credit (m)"] = d_max - df["Target Distance (m)"]
            df = df.sort_values("Target Distance (m)").reset_index(drop=True)
        numbers = [self.entries[n].get("number") for n in df["Entry"]]
        if any(x is not None for x in numbers):
            df.insert(1 if self.fixed_distance else 0, "No.", numbers)
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
            cols = ["Start #", "Entry", "Category", "Expected Time", "Start Offset",
                    "Gap to Prev (s)"]
            if "No." in df:
                cols.insert(1, "No.")
            if "Lane" in df:
                cols.insert(2, "Lane")
            title = f"{self.kind.upper()} {self.format}: STAGGERED START ({lvl})"
            self._print_table(title, df, cols, {"Gap to Prev (s)": "{:.1f}".format})
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

    def print_reference_table(self) -> None:
        """Print the reference times used by this race."""
        print(f"\nReference times ({self.refs.distance_m:.0f} m):")
        print(self.refs.table().to_string())
        print()

    # ── plotting (see ergrace.plotting) ──────────────────────────────────────
    def plot_handicaps(self, save_path: Optional[str] = None, **kw):
        from .plotting import plot_handicaps
        return plot_handicaps(self, save_path, **kw)

    def plot_results(self, save_path: Optional[str] = None, **kw):
        from .plotting import plot_results
        return plot_results(self, save_path, **kw)


class RelayRace(_Race):
    """
    **Relay race**: each team shares ONE ergometer and its rowers take turns.

    Use this when teams (of any size and mix of categories) compete, the
    athletes of a team row one after another, and the team result is one
    distance or one time.  For individuals racing each other use
    :class:`MixedRace`; for crews in boats use :class:`CrewRace`.

    Parameters
    ----------
    time : str or float, optional
        Race duration (``"30:00"`` or seconds) -- each team's result is a distance.
    distance : float, optional
        Race distance in metres -- each team's result is a time.
    teams : dict
        ``{team: ["Junior M", "Senior W", "Senior M"]}`` or
        ``{team: {"Senior M": 2, "Senior W": 3}}``.  Teams may differ in size.
    split : {"time", "distance"}, optional
        How a team shares the work: equal *time* per rower (swap on the clock)
        or equal *distance* legs (e.g. 3 x 1000 m).  Default: ``"time"`` for
        timed races, ``"distance"`` for distance races.
    references : References, optional
        Category references (default :meth:`References.default`).
    level : float, optional
        Expected fraction of reference power for the handicaps (default 1.0;
        club crews typically 0.6--0.8).  Scales offsets/targets, not order.
    fatigue : float, optional
        Paul's-law slowdown in s/500 m per doubling of each rower's own
        distance.  Off by default; switch on (e.g. 5) when team sizes differ a
        lot, because a rower in a small team rows longer.

    Notes
    -----
    Equal time shares: distances add, the team reference speed is the mean of
    the rowers' speeds.  Equal legs: times add, it is their harmonic mean.

    Examples
    --------
    >>> relay = RelayRace(time="30:00", teams={
    ...     "Team 1": ["Junior M", "Senior W", "Senior M"],
    ...     "Team 2": ["Junior M", "Senior W", "Senior W"]})
    >>> relay.print_handicaps()                                    # doctest: +SKIP
    >>> relay.record({"Team 1": 8100, "Team 2": 7900}).print_results()  # doctest: +SKIP
    """

    kind = "relay"

    def __init__(self, time: Optional[TimeLike] = None, distance: Optional[Number] = None,
                 teams: Optional[Mapping] = None, split: Optional[str] = None,
                 references: Optional[References] = None, level: float = 1.0,
                 fatigue: Optional[float] = None):
        super().__init__(time, distance, references, level, fatigue)
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
        n = len(labels)
        v = np.array([self.refs.speed(lab) for lab in labels])
        if self.fatigue:
            # distance each rower actually rows (estimated at reference speed)
            if self.fixed_distance:
                if self.split == "distance":
                    effort = np.full(n, self.distance_m / n)
                else:
                    effort = v * (self.distance_m / v.mean()) / n
            else:
                if self.split == "time":
                    effort = v * self.time_s / n
                else:
                    effort = np.full(n, n / np.sum(1 / v) * self.time_s / n)
            v = np.array([self._fatigued(vi, ei) for vi, ei in zip(v, effort)])
        if self.split == "time":
            v_ref = float(v.mean())                      # distances add
        else:
            v_ref = float(n / np.sum(1.0 / v))           # times add
        counts = Counter(_abbr(self.refs, lab) for lab in labels)
        order = sorted(counts, key=lambda k: (k.split()[1], k.split()[0]))
        label = " + ".join(f"{counts[k]} {k}" if counts[k] > 1 else k for k in order)
        self.entries[name] = {"members": [self.refs.label(lab) for lab in labels],
                              "label": label, "ref_speed": v_ref}
        return self


class MixedRace(_Race):
    """
    **Mixed race**: individuals of different categories race each other,
    one ergometer each.

    Use this when every entry is one athlete (e.g. senior men against junior
    women over 2000 m).  Athletes may carry a team label; teams are then
    ranked by the mean score of their athletes (:meth:`team_results`).  For
    teams sharing one ergometer use :class:`RelayRace`; for crews in boats use
    :class:`CrewRace`.

    Parameters
    ----------
    distance : float, optional
        Race distance in metres -- results are times.
    time : str or float, optional
        Race duration -- results are distances.
    lanes : dict
        ``{lane: "Junior W"}``, ``{lane: ("Anna", "Junior W")}``,
        ``{lane: ("Anna", "Junior W", "Club A")}`` or
        ``{lane: {"name": "Anna", "category": "Junior W", "team": "Club A"}}``.
    references, level, fatigue
        As for :class:`RelayRace`.

    Results can be recorded by lane or by athlete name.

    Examples
    --------
    >>> race = MixedRace(distance=2000, lanes={1: "Junior W", 2: ("Erik", "Senior M")})
    >>> race.print_handicaps()                                        # doctest: +SKIP
    >>> race.record({1: "7:30.2", "Erik": "6:45.0"}).print_results()  # doctest: +SKIP
    """

    kind = "mixed race"

    def __init__(self, distance: Optional[Number] = None, time: Optional[TimeLike] = None,
                 lanes: Optional[Mapping] = None, references: Optional[References] = None,
                 level: float = 1.0, fatigue: Optional[float] = None):
        super().__init__(time, distance, references, level, fatigue)
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
        v = self.refs.speed(cat)
        effort = self.distance_m if self.fixed_distance else v * self.time_s
        if name in self.entries:
            raise ValueError(f"Duplicate athlete name {name!r}")
        self.entries[name] = {"lane": lane, "team": team,
                              "label": _abbr(self.refs, cat),
                              "category": self.refs.label(cat),
                              "ref_speed": self._fatigued(v, effort)}
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


class CrewRace(_Race):
    """
    **Crew race**: boats of different classes (1x, 2x, 4x, 8+ ...) with
    mixed crews race each other on the water.

    Use this when every entry is one boat whose rowers pull *simultaneously*
    (e.g. a mixed 4x against a women's 2x in a head race).  For teams taking
    turns on one ergometer use :class:`RelayRace`; for individuals on
    ergometers use :class:`MixedRace`.

    Parameters
    ----------
    distance : float, optional
        Course length in metres -- results are times (head / pursuit race).
    time : str or float, optional
        Race duration -- results are distances.
    crews : dict
        ``{crew: ("4x", ["Senior M", "Senior W", "Junior M", "Junior W"])}``,
        ``{crew: ("8+", {"Senior M": 4, "Senior W": 4})}``,
        ``{crew: ("2x", [...], 7)}`` with a boat / bib number, or
        ``{crew: {"boat": "2x", "rowers": [...], "number": 7}}``.  The number
        of rowers must match the boat class (coxswains are not listed).
    references : BoatReferences, optional
        On-water reference times per boat class and category (default
        :meth:`BoatReferences.default`, editable placeholder values).
    level, fatigue
        As for :class:`RelayRace`; ``fatigue`` uses the course length.

    Notes
    -----
    All seats of a boat move at the same speed and the hull's drag power
    ``~ v^3`` is supplied by the sum of the rowers' powers.  Seat ``i`` of
    category ``g`` is represented by the speed ``v_i`` of a full crew of that
    class and category (hull advantage included); the crew's reference speed
    is ``(mean_i v_i^3)^(1/3)``, i.e. the arithmetic mean of seat powers.

    Examples
    --------
    >>> race = CrewRace(distance=6000, crews={
    ...     "Mixed 4x": ("4x", ["Senior M", "Senior W", "Junior M", "Junior W"]),
    ...     "W 2x": ("2x", ["Senior W", "Senior W"])})
    >>> race.print_handicaps()                                         # doctest: +SKIP
    >>> race.record({"Mixed 4x": "21:40", "W 2x": "24:05"}).print_results()  # doctest: +SKIP
    """

    kind = "crew race"

    def __init__(self, distance: Optional[Number] = None, time: Optional[TimeLike] = None,
                 crews: Optional[Mapping] = None, references: Optional[BoatReferences] = None,
                 level: float = 1.0, fatigue: Optional[float] = None):
        super().__init__(time, distance, references, level, fatigue)
        for name, spec in (crews or {}).items():
            self.add_crew(name, spec)

    @staticmethod
    def _default_refs():
        return BoatReferences.default()

    def add_crew(self, name: str, spec) -> "CrewRace":
        """Add a crew: ``(boat, rowers)`` or ``{"boat": ..., "rowers": ...}``."""
        if isinstance(spec, Mapping):
            boat, rowers, number = spec["boat"], spec["rowers"], spec.get("number")
        else:
            boat, rowers, number = spec[0], spec[1], (spec[2] if len(spec) > 2 else None)
        if isinstance(rowers, Mapping):
            labels = [lab for lab, k in rowers.items() for _ in range(int(k))]
        elif isinstance(rowers, str):
            labels = [rowers]
        else:
            labels = list(rowers)
        seats = boat_seats(boat)
        if len(labels) != seats:
            raise ValueError(f"{name!r}: a {boat} has {seats} rowing seat(s), "
                             f"got {len(labels)} rower(s)")
        v = np.array([self.refs.speed(boat, lab) for lab in labels])
        v_ref = float(np.mean(v ** 3) ** (1 / 3))      # seat powers add
        effort = self.distance_m if self.fixed_distance else v_ref * self.time_s
        v_ref = self._fatigued(v_ref, effort)
        counts = Counter(_abbr_key(self.refs.label(lab)) for lab in labels)
        order = sorted(counts, key=lambda k: (k.split()[1], k.split()[0]))
        crew = " + ".join(f"{counts[k]} {k}" if counts[k] > 1 else k for k in order)
        self.entries[name] = {"boat": boat, "number": number,
                              "members": [self.refs.label(l) for l in labels],
                              "label": f"{boat}: {crew}", "ref_speed": v_ref}
        return self
