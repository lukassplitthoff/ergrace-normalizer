"""
Example: Rådasjön runt 2026 - Lopp 134, 6000 m handicap race.

Real start list (race 134, "Rådasjön runt 6000m") organized as a handicap /
pursuit race with CrewRace. Crews are labelled by rowing club:

    ÖSR  Öresjö Segelsällskap Rodd
    MRK  Mölndals Roddklubb
    LRK  Lidingö Roddklubb
    GRK  Göteborgs Roddklubb
    SRF  Stockholms Roddförening

Inference rules applied to the published start list:
  * crews assumed to be senior unless noted otherwise (ÖSR/MRK crews are junior),
  * gender guessed from each rower's first name,
  * boat class guessed from the number of rowers (1 -> 1x, 2 -> 2x,
    4 -> 4x, 8 -> 8+).

Crews are given as (boat class, rowers, boat number).
"""

import os
import sys

# Make the package importable regardless of which interpreter runs this script
# (repo root is two levels up from examples/Radasioregattan2026/).
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from ergrace import CrewRace

crews = {
    # 1  ÖSR - Petter; Svea Tillsten (junior crew)
    "ÖSR/MRK - Petter":       ("2x", ["Junior W", "Junior M"], 1),
    # 2  MRK - Kelly Morrenhof; Henning Kirchberg; Philipp; Almida Thörjesson;
    #          Esad Dag; Sofia nn; Daniel Hellmich; Caroline nn
    "MRK - Kelly Morrenhof":  ("8+", {"Senior M": 4, "Senior W": 4}, 2),
    # 3  LRK - Anna Rosengren; Richard Abrahamsson
    "LRK - Anna Rosengren":   ("2x", ["Senior M", "Senior W"], 3),
    # 4  GRK - Niclas Wensberg; Edvin Aspelin
    "GRK - Niclas Wensberg":  ("2x", {"Senior M": 2}, 4),
    # 5  GRK - Ebba Rundqvist; Marie Alenvik; Catharina Landström; Åse Zachrisson
    "GRK - Ebba Rundqvist":   ("4x", {"Senior W": 4}, 5),
    # 6  MRK - Thomas Gispert; Benas nn
    "MRK - Thomas Gispert":   ("2x", {"Senior M": 2}, 6),
    # 7  SRF - Edith Lesage; Catharina Malmfors; Karolina Wichman; Jacinta Waak
    "SRF - Edith Lesage":     ("4x", {"Senior W": 4}, 7),
    # 8  GRK - Dácil Hernández; Anna Skogsberg; Sandra Trzil; Cecilia Helsing;
    #          Ulrika Clementz; Boglarka Fekete; Kajsa Grahn; Jessika Niklasson
    "GRK - Dácil Hernández":  ("8+", {"Senior W": 8}, 8),
    # 9  SRF - Jan Berglund
    "SRF - Jan Berglund":     ("1x", "Senior M", 9),
    # 10 MRK - Alfre Krantz; Elsa Hörberg (ÖSS) (junior crew)
    "ÖSR/MRK - Alfre Krantz": ("2x", ["Junior W", "Junior M"], 10),
}

race = CrewRace(distance=6000, crews=crews)

# Start list: slowest crew first, with the interval to the boat in front.
race.print_handicaps()

# The reference times used.
race.print_reference_table()

# Staggered starts, common finish line.
race.plot_handicaps(os.path.join(HERE, "radarunt_handicap.png"))

# After the race: race.record({"SRF - Jan Berglund": "24:10.0", ...}).print_results()
