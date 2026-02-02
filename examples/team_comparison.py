"""
Example: Team Comparison with Power Normalization

This example demonstrates how to use the ERGNormalizer to compare
team performance in a 20-minute rowing ergometer competition.
"""

from ergrace import ERGNormalizer

# Define team configurations
# Each team has a different composition of men and women
# and achieved different distances in 20 minutes
team_configs = {
    'Team_1': {'n_men': 3, 'n_women': 2, 'distance_20min_m': 6319},
    'Team_2': {'n_men': 0, 'n_women': 5, 'distance_20min_m': 5819},
    'Team_3': {'n_men': 2, 'n_women': 3, 'distance_20min_m': 5530},
    'Team_4': {'n_men': 3, 'n_women': 2, 'distance_20min_m': 6235},
    'Team_5': {'n_men': 2, 'n_women': 3, 'distance_20min_m': 5084},
    'Team_6': {'n_men': 1, 'n_women': 4, 'distance_20min_m': 5253},
    'Team_7': {'n_men': 0, 'n_women': 4, 'distance_20min_m': 5100}
}

# Create normalizer with default reference powers
# Men: 569.92 W (5:40 for 2K)
# Women: 350.00 W (6:40 for 2K)
normalizer = ERGNormalizer()

# Add all teams at once
normalizer.add_teams_from_dict(team_configs)

# Calculate normalized scores
normalizer.calculate_scores()

# Print formatted results
normalizer.print_results()

# Create visualization
normalizer.plot_results('team_comparison.png')

# You can also get the results as a DataFrame for further analysis
results_df = normalizer.get_results()
print("\nTop 3 teams by normalized score:")
print(results_df.head(3)[['Rank', 'Team', 'Score']])

# Example: Adding teams one by one
print("\n" + "="*80)
print("Alternative: Adding teams individually")
print("="*80)

normalizer2 = ERGNormalizer()
normalizer2.add_team('Alpha Squad', n_men=2, n_women=2, distance_20min_m=5500)
normalizer2.add_team('Beta Crew', n_men=3, n_women=1, distance_20min_m=5800)
normalizer2.calculate_scores()
normalizer2.print_results()

# Example: Using custom reference powers for different age groups
print("\n" + "="*80)
print("Example: Custom reference powers (Age 30-39)")
print("="*80)

# Reference powers for age 30-39 (hypothetical values)
normalizer3 = ERGNormalizer(ref_power_men=540.0, ref_power_women=330.0)
normalizer3.add_teams_from_dict({
    'Team_Masters_1': {'n_men': 3, 'n_women': 2, 'distance_20min_m': 5900},
    'Team_Masters_2': {'n_men': 2, 'n_women': 3, 'distance_20min_m': 5400}
})
normalizer3.calculate_scores()
normalizer3.print_results()
