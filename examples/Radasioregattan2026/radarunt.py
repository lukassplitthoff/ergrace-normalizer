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
  * all crews assumed to be senior,
  * gender guessed from each rower's first name,
  * boat class guessed from the number of rowers (1 -> 1x, 2 -> 2x,
    4 -> 4x, 8 -> 8+).

Where several crews come from the same club, the start number disambiguates
the label (e.g. "GRK 4").
"""

from ergrace import HandicapRace

# Race distance from the start list: "Rådasjön runt 6000m".
race = HandicapRace(distance_km=6)

# Start list. Each crew's `members` reflect the gender guessed from the first
# names on the published crew sheet; all rowers taken as senior.
crews = [
    # 1  ÖSR - Elsa Hörberg; Svea Tillsten
    {"name": "ÖSR 1", "boat_class": "2x",
     "members": [{"gender": "female", "count": 2}]},

    # 2  MRK - Kelly Morrenhof; Henning Kirchberg; Lukas Splitthoff;
    #          Almida Thörjesson; Esad Dag; Sofia nn; Daniel Hellmich; Caroline nn
    {"name": "MRK 2", "boat_class": "8+",
     "members": [{"gender": "male", "count": 4},
                 {"gender": "female", "count": 4}]},

    # 3  LRK - Anna Rosengren; Richard Abrahamsson
    {"name": "LRK 3", "boat_class": "2x",
     "members": [{"gender": "male", "count": 1},
                 {"gender": "female", "count": 1}]},

    # 4  GRK - Niclas Wensberg; Edvin Aspelin
    {"name": "GRK 4", "boat_class": "2x",
     "members": [{"gender": "male", "count": 2}]},

    # 5  GRK - Ebba Rundqvist; Marie Alenvik; Catharina Landström; Åse Zachrisson
    {"name": "GRK 5", "boat_class": "4x",
     "members": [{"gender": "female", "count": 4}]},

    # 6  MRK - Thomas Gispert; Benas nn
    {"name": "MRK 6", "boat_class": "2x",
     "members": [{"gender": "male", "count": 2}]},

    # 7  SRF - Edith Lesage; Catharina Malmfors; Karolina Wichman; Jacinta Waak
    {"name": "SRF 7", "boat_class": "4x",
     "members": [{"gender": "female", "count": 4}]},

    # 8  GRK - Dácil Hernández; Anna Skogsberg; Sandra Trzil; Cecilia Helsing;
    #          Ulrika Clementz; Boglarka Fekete; Kajsa Grahn; Jessika Niklasson
    {"name": "GRK 8", "boat_class": "8+",
     "members": [{"gender": "female", "count": 8}]},

    # 9  SRF - Jan Berglund
    {"name": "SRF 9", "boat_class": "1x",
     "members": [{"gender": "male", "count": 1}]},
]

race.add_crews_from_list(crews)
race.calculate()

# Output 1: results table (power, predicted time, start offset, adjacent gap).
race.print_results()

# Output 2: the reference times used.
race.print_reference_table()

# Output 3: pursuit/stagger plot (staggered starts, common finish line).
race.plot_results("radarunt_handicap.png")
