# ERGrace Normalizer

A Python package for normalizing rowing ergometer relay results by team composition. It allows a fair comparison between teams with different numbers of men and women.

## What It Does

In an ergometer relay, the rowers of a team take turns on **one** ergometer for a fixed time (e.g. 20 or 30 minutes), and the team result is the total distance. Men and women differ systematically in ergometer output, so raw distance is not a fair comparison across team compositions.

**ERGrace Normalizer** answers the question *what fraction of their reference power did the team's rowers sustain?*

1. From each rower's reference power `P_i` (men / women), it computes the distance `D_ref` a composition-matched team would cover rowing exactly at reference.
2. It compares the actual distance `D` with that reference.
3. It reports the **power score** `σ = (D / D_ref)³ = P_team / P_ref`, together with the speed score `s = D / D_ref`.

A score of 0.8 means the rowers sustained 80 % of their reference power. The speed score and the power score always give the same ranking; the power score reports it on the scale of what the athletes actually produce.

## Installation

```bash
git clone https://github.com/lukassplitthoff/ergrace-normalizer.git
cd ergrace-normalizer
pip install -e .
```

Requirements: Python 3.7+, numpy, pandas, matplotlib (Pillow optional for GIFs, pytest for the tests).

## Quick Start

```python
from ergrace import ERGNormalizer

teams = {
    'Team A': {'n_men': 3, 'n_women': 2, 'distance_m': 6319},
    'Team B': {'n_men': 2, 'n_women': 3, 'distance_m': 5530},
    'Team C': {'n_men': 0, 'n_women': 5, 'distance_m': 5819},
}

normalizer = ERGNormalizer(duration_s=20 * 60)      # 20-minute relay
normalizer.add_teams_from_dict(teams)
normalizer.calculate_scores()
normalizer.print_results()
normalizer.plot_results('results.png')
```

## Physics

### Power from pace

The Concept2 monitor converts its (flywheel-derived) speed `v` in m/s into power

```
P = c · v³,        c = 2.8 W·s³/m³  (= 2.8 kg/m)
```

Equivalently, with the 500 m split `t500` in seconds, `P = 2.8 · (500 / t500)³`; a 2:00 split is 202.5 W. For a distance `d` rowed in time `t`, `v = d / t`.

### How a relay team's reference is built

In a relay, rowers take turns, so their **distances add**, not their powers: `D = Σ v_i τ_i`. With equal shares of the relay time `T` and every rower at the same fraction `σ` of their reference power `P_i`,

```
D     = σ^(1/3) · D_ref,      D_ref = (T/n) · Σ_i (P_i / c)^(1/3)
σ     = (D / D_ref)³ = P_team / P_ref
P_team = c · (D / T)³
P_ref  = [ (1/n) · Σ_i P_i^(1/3) ]³      (power mean with exponent 1/3)
```

The constant `c` cancels in `σ`. `P_ref` is the power at the reference team's mean speed, which is what the measured distance corresponds to. Dividing `P_team` by the *arithmetic* mean of the reference powers instead would compare the power at the mean speed with a mean power; by the power-mean inequality that penalizes mixed teams, by up to about 1.3 % for 2000 m references and more for shorter ones. The arithmetic mean is the matching reference only when rowers pull **simultaneously** in one boat, where the boat speed is set by their summed power (see the handicap race below).

A ranking depends on the references only through the ratio `P_men / P_women`. That ratio depends strongly on the reference distance (1.77 at 500 m, 1.48 at 2000 m, 1.44 at 5000 m for the world records), so choose and announce the reference before the event.

## Reference Powers

The defaults are the benchmark 2000 m times 5:40 (569.92 W) for men and 6:40 (350.00 W) for women. Set other references directly as powers, or from any distance and times:

```python
normalizer = ERGNormalizer(ref_power_men=540.0, ref_power_women=330.0, duration_s=1800)

# 2000 m world records (5:34.7 and 6:21.1), 30-minute relay
normalizer = ERGNormalizer.from_reference_times(2000, 334.7, 381.1, duration_s=1800)
```

## API Reference

### `ERGNormalizer(ref_power_men=569.92, ref_power_women=350.0, duration_s=1200)`

| Method | Description |
|---|---|
| `from_reference_times(distance_m, time_men_s, time_women_s, duration_s)` | Class method: references from times over a distance |
| `add_team(name, n_men, n_women, distance_m)` | Add a team (the old keyword `distance_20min_m` is still accepted); returns self |
| `add_teams_from_dict(team_dict)` | Bulk add `{name: {'n_men', 'n_women', 'distance_m'}}`; returns self |
| `calculate_scores()` | Compute reference distance, speed score and power score; returns self |
| `get_results()` | DataFrame: Rank, Team, Composition, Distance (km), Ref Distance (km), Speed Score, Ref Power (W), Team Power (W), Score |
| `print_results()` | Formatted table |
| `plot_results(save_path=None, ...)` | Distance bars with score markers |
| `animate_results(...)` | Cumulative PNG frames and a GIF revealing the ranking |

Static conversions: `time2power(t_2k_s)`, `distance2power(d_20min_m)`, `distance_time2power(distance_m, duration_s)`. Module functions in `ergrace.normalizer`: `power_from_speed`, `speed_from_power`, `power_from_distance_time`, `split_from_power`, `team_reference_power`.

```python
ERGNormalizer.time2power(6 * 60 + 30)                 # 6:30 for 2000 m -> 377.6 W
ERGNormalizer.distance_time2power(5500, 20 * 60)      # 5500 m in 20 min -> 269.6 W
```

## Example Output

```
 Rank   Team Composition Distance (km) Ref Distance (km) Speed Score Ref Power (W) Team Power (W)  Score
    1 Team_2       0M/5W         5.819             6.000      0.9698         350.0          319.3 0.9122
    2 Team_1       3M/2W         6.319             6.635      0.9523         473.4          408.8 0.8637
    3 Team_4       3M/2W         6.235             6.635      0.9397         473.4          392.8 0.8297
    4 Team_3       2M/3W         5.530             6.424      0.8609         429.5          274.0 0.6380
    5 Team_7       0M/4W         5.100             6.000      0.8500         350.0          214.9 0.6141
    6 Team_6       1M/4W         5.253             6.212      0.8457         388.4          234.9 0.6048
    7 Team_5       2M/3W         5.084             6.424      0.7915         429.5          212.9 0.4958
```

- **Score > 1**: the rowers sustained more than their reference power
- **Score = 1**: exactly at reference, for any team composition
- **Score < 1**: below reference

See [examples/team_comparison.py](examples/team_comparison.py) for a full example.

## RRC 2026 report

[examples/RRC2026/publication](examples/RRC2026/publication) contains a short paper applying the method to the Råda Rowing Challenge 2026 relay, including the derivation and a sensitivity analysis over the reference distance. `generate_figures.py` computes every figure, table and quoted number with this package:

```bash
python examples/RRC2026/publication/generate_figures.py
cd examples/RRC2026/publication && latexmk -pdf RRC2026_report.tex
```

## Tests

```bash
pytest tests
```

## Handicap / Pursuit Race

In addition to the erg-format normalizer above, the package can organize an
**on-water handicap (pursuit) race**: boats of different **classes**
(`1x`, `2x`, `4x`, `8+`), **genders** and **age categories**
(`junior`, `senior`, `master`) race the same N km course and should all arrive
at the same time. The slowest boat starts first; every other boat is held back
by the difference between its expected finish time and the slowest boat's.

Each crew's expected time is predicted **purely from reference data** — no
per-crew test result is needed. The reference table lives in
[ergrace/data/reference_times_2k.json](ergrace/data/reference_times_2k.json) and
holds an on-water 2 km reference time for every boat class / gender / category.
These are coherent, editable defaults — tune them for your club or event.

### How the prediction works

Time is **not** additive across the seats of a boat, but per-person **power**
is. So a crew's reference is the *mean of the per-seat reference powers* (the
same `P = 2.8 · (2000 / t)³` formula used by the erg normalizer), and the
predicted N km time is `t = N·1000 · (2.8 / P)^(1/3)`. A homogeneous crew
reproduces its boat's reference time exactly; a mixed crew is averaged in power
space, which is the physically correct choice.

The model works in **per-seat equivalent power**, never total boat watts: the
reference table stores a *per-seat* time per boat class, so the hull advantage
of a bigger shell is already baked in. A crew is therefore the **mean** of its
seat powers, not the sum — the reported "Seat Power (W)" is that mean per-seat
value, compared seat-for-seat across boat classes.

The predicted times are used **only to set the start stagger**. If every crew
rowed exactly to reference they would dead-heat — in the real race the first
boat across the line wins, so the finish order on the water is the placing.

**Assumption — constant power over distance.** Each crew is assumed to hold its
reference power for the whole course (finish time scales linearly with
distance). Real athletes can't sustain 2 km power over, say, 6 km, so if the
table holds true 2 km performances the *absolute* predicted times are
optimistic — but the *handicap* stays fair as long as every crew is scaled from
the same kind of reference. For accurate absolute times, populate the table with
reference times at (or near) the race distance.

### Quick start

```python
from ergrace import HandicapRace

race = HandicapRace(distance_km=6)
race.add_crew('Crew 1', '1x', [{'gender': 'male', 'category': 'senior'}])
race.add_crew('Crew 2', '8+',
              [{'gender': 'male',   'category': 'senior', 'count': 3},
               {'gender': 'female', 'category': 'senior', 'count': 5}])

race.calculate()
race.print_results()           # power, predicted time, start offset, adjacent gap
race.print_reference_table()   # the 2 km reference times used
race.plot_results('handicap_race.png')  # staggered starts, common finish
```

Each crew reports two gaps: **Start Offset** (time held behind the first/slowest
starter) and **Gap to Prev** (the start interval to the boat immediately in
front of you). See [examples/handicap_race.py](examples/handicap_race.py) for a
complete multi-boat example.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- Power–pace relation of the Concept2 Performance Monitor
- Reference times from the Concept2 world-record database and World Rowing

## Contact

For questions or suggestions, please open an issue on GitHub.
