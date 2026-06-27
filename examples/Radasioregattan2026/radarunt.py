"""
Example: Rådasjön runt 2026 - Lopp 134, 6000 m handicap race.

Real start list (race 134, "Rådasjön runt 6000m") organized as a handicap /
pursuit race with HandicapRace. Crews are labelled by rowing club:

    ÖSR  Öresjö Segelsällskap Rodd
    MRK  Mölndals Roddklubb
    LRK  Lidingö Roddklubb
    GRK  Göteborgs Roddklubb
    SRF  Stockholms Roddförening

Inference rules applied to the published start list:
  * crews assumed to be senior unless noted otherwise (ÖSR/MRK 1 is junior),
  * gender guessed from each rower's first name,
  * boat class guessed from the number of rowers (1 -> 1x, 2 -> 2x,
    4 -> 4x, 8 -> 8+).

Where several crews come from the same club, the start number disambiguates
the label (e.g. "GRK 4").
"""

import os
import sys

# Make the package importable regardless of which interpreter runs this script
# (repo root is two levels up from examples/Radasioregattan2026/).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ergrace import HandicapRace

# Race distance from the start list: "Rådasjön runt 6000m".
race = HandicapRace(distance_km=6)

# Start list. Each crew's `members` reflect the gender guessed from the first
# names on the published crew sheet; rowers are senior unless a member
# carries an explicit "category" (ÖSR/MRK 1 is junior).
crews = [
    # 1  ÖSR - Petter; Svea Tillsten (junior crew)
    {"name": "ÖSR/MRK - Petter", "boat_number": 1, "boat_class": "2x",
     "members": [{"gender": "female", "category": "junior", "count": 1},
                 {"gender": "male", "category": "junior", "count": 1}]},

    # 2  MRK - Kelly Morrenhof; Henning Kirchberg; Philipp;
    #          Almida Thörjesson; Esad Dag; Sofia nn; Daniel Hellmich; Caroline nn
    {"name": "MRK - Kelly Morrenhof", "boat_number": 2, "boat_class": "8+",
     "members": [{"gender": "male", "count": 4},
                 {"gender": "female", "count": 4}]},

    # 3  LRK - Anna Rosengren; Richard Abrahamsson
    {"name": "LRK - Anna Rosengren", "boat_number": 3, "boat_class": "2x",
     "members": [{"gender": "male", "category": "senior", "count": 1},
                 {"gender": "female", "category": "senior", "count": 1}]},

    # 4  GRK - Niclas Wensberg; Edvin Aspelin
    {"name": "GRK - Niclas Wensberg", "boat_number": 4, "boat_class": "2x",
     "members": [{"gender": "male", "category": "senior", "count": 2}]},

    # 5  GRK - Ebba Rundqvist; Marie Alenvik; Catharina Landström; Åse Zachrisson
    {"name": "GRK - Ebba Rundqvist", "boat_number": 5, "boat_class": "4x",
     "members": [{"gender": "female", "category": "senior", "count": 4}]},

    # 6  MRK - Thomas Gispert; Benas nn
    {"name": "MRK - Thomas Gispert", "boat_number": 6, "boat_class": "2x",
     "members": [{"gender": "male", "count": 2}]},

    # 7  SRF - Edith Lesage; Catharina Malmfors; Karolina Wichman; Jacinta Waak
    {"name": "SRF - Edith Lesage", "boat_number": 7, "boat_class": "4x",
     "members": [{"gender": "female", "count": 4}]},

    # 8  GRK - Dácil Hernández; Anna Skogsberg; Sandra Trzil; Cecilia Helsing;
    #          Ulrika Clementz; Boglarka Fekete; Kajsa Grahn; Jessika Niklasson
    {"name": "GRK - Dácil Hernández", "boat_number": 8, "boat_class": "8+",
     "members": [{"gender": "female", "category": "senior", "count": 8}]},

    # 9  SRF - Jan Berglund
    {"name": "SRF - Jan Berglund", "boat_number": 9, "boat_class": "1x",
     "members": [{"gender": "male", "category": "senior", "count": 1}]},

     # 10  MRK - Alfre Krantz; Elsa Hörberg (ÖSS) (junior crew)
    {"name": "ÖSR/MRK - Alfre Krantz", "boat_number": 10, "boat_class": "2x",
     "members": [{"gender": "female", "category": "junior", "count": 1},
                 {"gender": "male", "category": "junior", "count": 1}]},

]

race.add_crews_from_list(crews)
race.calculate()

# Output 1a: results table in handicap start order (slowest crew first).
race.print_results(by="start")

# Output 1b: same results sorted by published boat number.
race.print_results(by="start")

# Output 2: the reference times used.
race.print_reference_table()

# Output 3: pursuit/stagger plot (staggered starts, common finish line).
race.plot_results("radarunt_handicap.png")
