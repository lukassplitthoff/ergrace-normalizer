"""
Reference performances per athlete category, and time helpers.

A *category* is an age group plus a gender, written the way you would say it:
``"Senior M"``, ``"junior W"``, ``"Master F"``, ``"M"`` (= senior men).
Each category has a reference performance (a time over a reference distance)
that defines score 1.0.  Internally everything is converted to a reference
power ``P = c (d / t)^3`` and a reference speed ``v = d / t``.

Only *ratios* between categories matter for handicaps and rankings; the
absolute level only sets the scale of the score.
"""

import json
import os
import re
from typing import Dict, Iterable, Tuple, Union

from .normalizer import power_from_distance_time

Number = Union[int, float]
TimeLike = Union[str, Number]

_DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "data", "erg_reference_2k.json")

_GENDERS = {"m": "M", "man": "M", "men": "M", "male": "M", "h": "M",
            "w": "W", "f": "W", "woman": "W", "women": "W", "female": "W"}
_AGES = {"junior": "junior", "juniors": "junior", "jun": "junior", "j": "junior",
         "u18": "junior", "u19": "junior",
         "senior": "senior", "seniors": "senior", "sen": "senior", "open": "senior",
         "master": "master", "masters": "master", "mas": "master", "veteran": "master"}


# ── time helpers ─────────────────────────────────────────────────────────────
def parse_time(value: TimeLike) -> float:
    """``"6:21.1"``, ``"1:02:03"``, ``"30:00"`` or a number of seconds -> seconds."""
    if isinstance(value, (int, float)):
        return float(value)
    parts = str(value).strip().split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError(f"Cannot parse time {value!r}")
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + float(p)
    return seconds


def format_time(seconds: float, decimals: int = 1, sign: bool = False) -> str:
    """Seconds -> ``"M:SS.s"`` (``"H:MM:SS.s"`` above one hour)."""
    neg = seconds < 0
    s = abs(seconds)
    s = round(s, decimals)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    width = 3 + decimals if decimals else 2
    sec_str = f"{sec:0{width}.{decimals}f}"
    body = f"{int(h)}:{int(m):02d}:{sec_str}" if h else f"{int(m)}:{sec_str}"
    prefix = "-" if neg else ("+" if sign else "")
    return prefix + body


# ── categories ───────────────────────────────────────────────────────────────
def parse_category(label: str) -> Tuple[str, str]:
    """``"Junior M"`` -> ``("junior", "M")``.  Age defaults to ``senior``."""
    tokens = [t for t in re.split(r"[\s_\-/,]+", str(label).strip().lower()) if t]
    age, gender = None, None
    for t in tokens:
        if t in _GENDERS and gender is None:
            gender = _GENDERS[t]
        elif t in _AGES and age is None:
            age = _AGES[t]
        else:
            raise ValueError(f"Unknown token {t!r} in category {label!r}; use e.g. "
                             f"'Senior M', 'Junior W', 'Master F'")
    if gender is None:
        raise ValueError(f"Category {label!r} has no gender (M/W)")
    return (age or "senior", gender)


def category_label(key: Tuple[str, str]) -> str:
    """``("junior", "M")`` -> ``"Junior M"``."""
    return f"{key[0].capitalize()} {key[1]}"


class References:
    """
    Reference performance per category.

    Parameters
    ----------
    distance_m : float
        Reference distance in metres (e.g. 2000).
    times : dict
        ``{category label: time}``; times as ``"M:SS.s"`` strings or seconds.

    Examples
    --------
    >>> refs = References.default()                   # bundled 2000 m table
    >>> round(refs.power("Senior M"), 1)
    597.4
    >>> refs = References(2000, {"Senior M": "6:00", "Senior W": "7:00",
    ...                          "Junior M": "6:20"})
    >>> refs.label("junior m")
    'Junior M'
    """

    def __init__(self, distance_m: Number, times: Dict[str, TimeLike]):
        if distance_m <= 0:
            raise ValueError("distance_m must be positive")
        self.distance_m = float(distance_m)
        self.times: Dict[Tuple[str, str], float] = {}
        for label, t in times.items():
            sec = parse_time(t)
            if sec <= 0:
                raise ValueError(f"Reference time for {label!r} must be positive")
            self.times[parse_category(label)] = sec

    @classmethod
    def default(cls) -> "References":
        """Bundled 2000 m table (senior = world records; junior/master = placeholders)."""
        return cls.from_json(_DEFAULT_PATH)

    @classmethod
    def from_json(cls, path: str) -> "References":
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        times = {f"{age} {g}": t for age, gs in doc["reference_times"].items()
                 for g, t in gs.items()}
        return cls(doc.get("distance_m", 2000), times)

    def updated(self, times: Dict[str, TimeLike]) -> "References":
        """Copy with some categories added or replaced."""
        merged = {category_label(k): v for k, v in self.times.items()}
        merged.update(times)
        return References(self.distance_m, merged)

    # lookups
    def key(self, label: str) -> Tuple[str, str]:
        k = parse_category(label)
        if k not in self.times:
            known = ", ".join(sorted(category_label(c) for c in self.times))
            raise KeyError(f"No reference for {category_label(k)!r}. Known: {known}")
        return k

    def label(self, label: str) -> str:
        return category_label(self.key(label))

    def power(self, label: str) -> float:
        """Reference power [W]."""
        return power_from_distance_time(self.distance_m, self.times[self.key(label)])

    def speed(self, label: str) -> float:
        """Reference speed [m/s] (independent of the constant c)."""
        return self.distance_m / self.times[self.key(label)]

    def categories(self) -> Iterable[str]:
        return [category_label(k) for k in sorted(self.times)]

    def table(self):
        """Reference table as a DataFrame."""
        import pandas as pd
        rows = [{"Category": category_label(k),
                 f"Time {self.distance_m:.0f} m": format_time(t),
                 "Split /500 m": format_time(t * 500 / self.distance_m),
                 "Power (W)": round(power_from_distance_time(self.distance_m, t), 1)}
                for k, t in sorted(self.times.items(), key=lambda kv: kv[1])]
        return pd.DataFrame(rows)

    def __repr__(self):
        cats = ", ".join(f"{category_label(k)} {format_time(t)}"
                         for k, t in sorted(self.times.items(), key=lambda kv: kv[1]))
        return f"References({self.distance_m:.0f} m: {cats})"
