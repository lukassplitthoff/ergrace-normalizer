"""
Mixed races: individuals of different categories race each other.

Run:  python examples/races/mixed_race.py
Writes the charts next to this script.
"""
import os

from ergrace import MixedRace, References

HERE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Fixed distance: 2000 m, staggered start → results are times ───────────
race = MixedRace(distance=2000, level=0.7, lanes={
    1: ("Anna",   "Junior W", "Mölndal"),
    2: ("Erik",   "Senior M", "Mölndal"),
    3: ("Karin",  "Master W", "Chalmers"),
    4: ("Johan",  "Master M", "Chalmers"),
    5: ("Sofia",  "Senior W", "Mölndal"),
    6: ("Leon",   "Junior M", "Chalmers"),
})
race.print_handicaps()
race.plot_handicaps(os.path.join(HERE, "mixed_distance_handicaps.png"))

race.record({"Anna": "7:48.0", "Erik": "6:52.5", "Karin": "8:06.2",
             "Johan": "7:05.8", "Sofia": "7:39.9", "Leon": "7:21.4"})
race.print_results()
race.print_team_results()
race.plot_results(os.path.join(HERE, "mixed_distance_results.png"))

# ── 2. Fixed time: 20 minutes, own references → results are distances ───────
club = References(2000, {"Senior M": "6:30", "Senior W": "7:25",
                         "Junior M": "6:45", "Junior W": "7:45",
                         "Master M": "6:55", "Master W": "7:55"})
race = MixedRace(time="20:00", references=club, lanes={
    1: "Junior W", 2: "Senior M", 3: "Master W", 4: "Master M"})
race.print_handicaps()
race.record({1: 4410, 2: 5160, 3: 4390, 4: 4905})
race.print_results()
race.plot_results(os.path.join(HERE, "mixed_time_results.png"))
