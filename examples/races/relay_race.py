"""
Relay races: each team shares one ergometer and its rowers take turns.

Run:  python examples/races/relay_race.py
Writes the charts next to this script.
"""
import os

from ergrace import RelayRace

HERE = os.path.dirname(os.path.abspath(__file__))
TEAMS = {
    "Team 1": ["Junior M", "Senior W", "Senior M"],
    "Team 2": ["Junior M", "Senior W", "Senior W"],
    "Team 3": {"Senior W": 3},
    "Team 4": ["Master M", "Master W", "Junior W"],
    "Team 5": {"Senior M": 2, "Junior W": 1},
}

# ── 1. Fixed time: 30 minutes, swap on the clock → result is a distance ──────
relay = RelayRace(time="30:00", teams=TEAMS, level=0.7)
relay.print_handicaps()                 # target distance / metre credit per team
relay.plot_handicaps(os.path.join(HERE, "relay_time_handicaps.png"))

relay.record({"Team 1": 8480, "Team 2": 8120, "Team 3": 7710,
              "Team 4": 7690, "Team 5": 8590})
relay.print_results()
relay.plot_results(os.path.join(HERE, "relay_time_results.png"))

# ── 2. Fixed distance: 3 × 1000 m legs → staggered start, result is a time ───
relay = RelayRace(distance=3000, teams=TEAMS, level=0.7)     # split="distance"
relay.print_handicaps()                 # who starts when, so all arrive together
relay.plot_handicaps(os.path.join(HERE, "relay_distance_handicaps.png"))

relay.record({"Team 1": "10:02.4", "Team 2": "10:20.9", "Team 3": "10:47.0",
              "Team 4": "10:52.3", "Team 5": "9:55.1"})
relay.print_results()
relay.plot_results(os.path.join(HERE, "relay_distance_results.png"))
