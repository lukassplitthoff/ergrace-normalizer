# ERGrace Normalizer

A Python package for normalizing rowing ergometer (erg) performance based on team composition. This tool allows fair comparison between teams with different numbers of men and women by calculating normalized scores based on reference power values.

## What It Does

In rowing competitions, teams often have different gender compositions. Since men and women typically achieve different power outputs on the ergometer, direct comparison of raw performance (distance or time) is not fair.

**ERGrace Normalizer** solves this by:
1. Calculating a reference power for each team based on its composition (number of men and women)
2. Converting actual performance (20-minute distance) to power output
3. Computing a normalized score: `Score = Actual Power / Reference Power`

Teams with higher normalized scores performed better relative to their expected performance.

## Installation

### From Source

```bash
git clone https://github.com/yourusername/ergrace-normalizer.git
cd ergrace-normalizer
pip install -e .
```

### Requirements

- Python 3.7+
- numpy
- pandas
- matplotlib

## Quick Start

```python
from ergrace import ERGNormalizer

# Define your teams
teams = {
    'Team A': {'n_men': 3, 'n_women': 2, 'distance_20min_m': 6319},
    'Team B': {'n_men': 2, 'n_women': 3, 'distance_20min_m': 5530},
    'Team C': {'n_men': 0, 'n_women': 5, 'distance_20min_m': 5819}
}

# Create normalizer and add teams
normalizer = ERGNormalizer()
normalizer.add_teams_from_dict(teams)

# Calculate scores and display results
normalizer.calculate_scores()
normalizer.print_results()

# Create visualization
normalizer.plot_results('results.png')
```

## Reference Powers

The default reference powers are based on World Rowing ergometer records for age 19-29:

| Gender | 2K Time | Power  |
|--------|---------|--------|
| Men    | 5:40    | 569.92 W |
| Women  | 6:40    | 350.00 W |

You can customize these for different age groups:

```python
# Example: Age 30-39 (hypothetical values)
normalizer = ERGNormalizer(ref_power_men=540.0, ref_power_women=330.0)
```

## Power Calculation

The package uses the standard rowing power formula:

```
P = 2.8 / (pace_per_500m)^3
```

Where pace is in seconds per 500 meters.

### Converting from 2K Time

```python
from ergrace import ERGNormalizer

# Convert a 6:30 2K time to power
power = ERGNormalizer.time2power(6*60 + 30)
print(f"Power: {power:.1f} W")
```

### Converting from 20-Minute Distance

```python
# Convert 5500m in 20 minutes to power
power = ERGNormalizer.distance2power(5500)
print(f"Power: {power:.1f} W")
```

## API Reference

### ERGNormalizer

The main class for power normalization.

#### Methods

**`__init__(ref_power_men=569.92, ref_power_women=350.0)`**
- Initialize with reference power values

**`add_team(name, n_men, n_women, distance_20min_m)`**
- Add a single team
- Returns self for method chaining

**`add_teams_from_dict(team_dict)`**
- Bulk add teams from a dictionary
- Returns self for method chaining

**`calculate_scores()`**
- Calculate normalized scores for all teams
- Must be called before printing or plotting
- Returns self for method chaining

**`get_results()`**
- Returns results as a pandas DataFrame
- Columns: Rank, Team, Composition, Distance (km), Ref Power (W), Actual Power (W), Score

**`print_results()`**
- Print formatted results table to console

**`plot_results(save_path=None, ...)`**
- Create dual-axis visualization (distance bars + score overlay)
- Parameters:
  - `save_path`: Path to save figure (if None, displays instead)
  - `figsize`: Figure size tuple (default: (10, 6))
  - `dist_color`: Color for distance bars (default: "#011C5F")
  - `score_color`: Color for score line (default: "#BE0602")
  - `transparent`: Use transparent background (default: True)
  - `dpi`: Resolution for saved figure (default: 300)

**Static Methods:**

**`time2power(time_s)`**
- Convert 2K erg time (seconds) to power (Watts)

**`distance2power(distance_m)`**
- Convert 20-minute distance (meters) to power (Watts)

## Examples

See the [examples/](examples/) directory for complete examples:

- [team_comparison.py](examples/team_comparison.py) - Full example with multiple teams and visualization

### Adding Teams Individually

```python
normalizer = ERGNormalizer()
normalizer.add_team('Team Alpha', n_men=2, n_women=2, distance_20min_m=5500)
normalizer.add_team('Team Beta', n_men=3, n_women=1, distance_20min_m=5800)
normalizer.calculate_scores().print_results()
```

### Method Chaining

```python
results = (ERGNormalizer()
    .add_team('Team A', 3, 2, 6319)
    .add_team('Team B', 2, 3, 5530)
    .calculate_scores()
    .get_results())
```

### Custom Visualization

```python
normalizer.plot_results(
    save_path='my_results.png',
    figsize=(12, 7),
    dist_color='#0066CC',
    score_color='#CC0000',
    transparent=False,
    dpi=150
)
```

## Understanding the Results

### Normalized Score Interpretation

- **Score > 1.0**: Team performed better than expected for their composition
- **Score = 1.0**: Team performed exactly as expected
- **Score < 1.0**: Team performed below expectations

### Example Output

```
================================================================================
                       ERG POWER NORMALIZATION RESULTS
================================================================================

Reference Powers: Men = 569.9 W, Women = 350.0 W

 Rank      Team Composition  Distance (km)  Ref Power (W)  Actual Power (W)  Score
    1   Team_2       0M/5W           5.819          350.0             319.2  0.912
    2   Team_1       3M/2W           6.319          482.0             408.8  0.848
    3   Team_4       3M/2W           6.235          482.0             392.9  0.815
    4   Team_3       2M/3W           5.530          438.0             274.1  0.626
    5   Team_7       0M/4W           5.100          350.0             215.0  0.614
    6   Team_6       1M/4W           5.253          394.0             234.9  0.596
    7   Team_5       2M/3W           5.084          438.0             212.9  0.486

================================================================================
Note: Score = Actual Power / Reference Power
Higher score means better performance relative to team composition
================================================================================
```

In this example, Team_2 (all women) achieved the highest normalized score (0.912), meaning they performed closest to their expected capacity.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Acknowledgments

- Power formula based on standard rowing ergometer physics
- Reference times from World Rowing ergometer rankings

## Contact

For questions or suggestions, please open an issue on GitHub.
