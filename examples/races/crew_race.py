"""
Crew races: boats of different classes with mixed crews race on the water.

Run:  python examples/races/crew_race.py
Writes the charts next to this script.
"""
import os

from ergrace import CrewRace

HERE = os.path.dirname(os.path.abspath(__file__))

head = CrewRace(distance=6000, level=0.7, crews={
    "Mixed 4x":  ("4x", ["Senior M", "Senior W", "Junior M", "Junior W"]),
    "Women 2x":  ("2x", ["Senior W", "Senior W"]),
    "Master 1x": ("1x", "Master M"),
    "Mixed 8+":  ("8+", {"Senior M": 4, "Senior W": 4}),
    "Junior 4x": ("4x", {"Junior W": 4}),
})
head.print_handicaps()
head.plot_handicaps(os.path.join(HERE, "crew_distance_handicaps.png"))

head.record({"Mixed 4x": "20:52", "Women 2x": "22:10", "Master 1x": "24:40",
             "Mixed 8+": "18:20", "Junior 4x": "21:45"})
head.print_results()
head.plot_results(os.path.join(HERE, "crew_distance_results.png"))
