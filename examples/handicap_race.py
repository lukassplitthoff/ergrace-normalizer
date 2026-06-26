"""
Example: Handicap (pursuit) race across boat classes, genders and age categories.

A handicap race lines up boats of different classes (1x, 2x, 4x, 8+), genders
and age categories over the same N km course so that all crews should arrive at
the same time. Each crew's expected finish time is predicted purely from a table
of on-water 2 km reference times (see ergrace/data/reference_times_2k.json), and
the slowest boat starts first while the others are held back by the difference.

This example mirrors the erg-format example (examples/team_comparison.py).
"""

from ergrace import HandicapRace

# Build a 6 km handicap race using the bundled reference-times table.
race = HandicapRace(distance_km=6)

# Define the start list. Each crew is a boat; `members` lists groups of
# identical rowers. The total count must match the boat's number of seats
# (1x = 1, 2x = 2, 4x = 4, 8+ = 8). `category` defaults to "senior".
crews = [
    {"name": "Crew 1", "boat_class": "1x",
     "members": [{"gender": "male", "category": "senior"}]},

    # crew 2: 3x male + 5x female, 8+, senior
    {"name": "Crew 2", "boat_class": "8+",
     "members": [{"gender": "male", "category": "senior", "count": 3},
                 {"gender": "female", "category": "senior", "count": 5}]},

    {"name": "Crew 3", "boat_class": "2x",
     "members": [{"gender": "female", "category": "master", "count": 2}]},

    {"name": "Crew 4", "boat_class": "4x",
     "members": [{"gender": "male", "category": "junior", "count": 2},
                 {"gender": "female", "category": "junior", "count": 2}]},

    {"name": "Crew 5", "boat_class": "8+",
     "members": [{"gender": "female", "category": "junior", "count": 8}]},
]

race.add_crews_from_list(crews)

# Compute crew power, predicted times and the handicap start stagger.
race.calculate()

# Output 1: results table (power, predicted time, start offset, adjacent gap).
race.print_results()

# Output 2: the reference times used.
race.print_reference_table()

# Output 3: pursuit/stagger plot (staggered starts, common finish line).
race.plot_results("handicap_race.png")

# Results are also available as a DataFrame for further analysis.
results_df = race.get_results()
print("Start order (slowest first):")
print(results_df[["Start #", "Crew", "Boat", "Predicted Time", "Gap to Prev (s)"]])
