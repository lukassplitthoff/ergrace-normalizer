"""
ERG Power Normalizer - Normalize rowing ergometer performance based on team composition.

This module provides tools for comparing rowing ergometer team performance
by normalizing results based on the gender composition of teams.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional, Union


class ERGNormalizer:
    """
    A class for normalizing rowing ergometer performance based on team composition.

    The normalizer calculates reference power based on the gender composition of teams
    and computes normalized scores that allow fair comparison between teams with
    different numbers of men and women.

    Reference power values are based on World Rowing ergometer records for age 19-29:
    - Men: 5:40 for 2K (569.92 W)
    - Women: 6:40 for 2K (350.00 W)

    Parameters
    ----------
    ref_power_men : float, optional
        Reference power for men in Watts (default: 569.92)
    ref_power_women : float, optional
        Reference power for women in Watts (default: 350.00)

    Examples
    --------
    >>> normalizer = ERGNormalizer()
    >>> normalizer.add_team('Team A', n_men=3, n_women=2, distance_20min_m=6319)
    >>> normalizer.add_team('Team B', n_men=2, n_women=3, distance_20min_m=5530)
    >>> normalizer.calculate_scores()
    >>> normalizer.print_results()
    """

    def __init__(self, ref_power_men: float = 569.92, ref_power_women: float = 350.0,
                 duration_s: float = 1200):
        """Initialize the ERGNormalizer with reference power values.

        Parameters
        ----------
        duration_s : float, optional
            Race duration in seconds (default: 1200). Use 1800 for 30-minute races.
        """
        self.ref_power_men = ref_power_men
        self.ref_power_women = ref_power_women
        self.duration_s = duration_s
        self.teams = {}
        self.results_calculated = False

    @staticmethod
    def time2power(time_s: float) -> float:
        """
        Convert 2K ergometer time to average power output.

        Uses the standard rowing power formula: P = 2.8 / (pace/500m)^3

        Parameters
        ----------
        time_s : float
            Time in seconds for 2000m

        Returns
        -------
        float
            Average power in Watts

        Examples
        --------
        >>> ERGNormalizer.time2power(5*60 + 40)  # 5:40 for 2K
        569.92
        """
        return 2.8 / (time_s / 2000) ** 3

    @staticmethod
    def distance2power(distance_m: float) -> float:
        """
        Convert 20-minute distance to average power output.

        Parameters
        ----------
        distance_m : float
            Distance covered in 20 minutes (meters)

        Returns
        -------
        float
            Average power in Watts

        Examples
        --------
        >>> ERGNormalizer.distance2power(6000)
        412.5
        """
        return 2.8 / (20 * 60 / distance_m) ** 3

    @staticmethod
    def distance_time2power(distance_m: float, duration_s: float) -> float:
        """
        Convert distance rowed in a given time to average power output.

        Parameters
        ----------
        distance_m : float
            Distance covered in meters
        duration_s : float
            Race duration in seconds

        Returns
        -------
        float
            Average power in Watts
        """
        return 2.8 / (duration_s / distance_m) ** 3

    def add_team(self, name: str, n_men: int, n_women: int, distance_20min_m: float) -> 'ERGNormalizer':
        """
        Add a team to the comparison.

        Parameters
        ----------
        name : str
            Team name
        n_men : int
            Number of men on the team
        n_women : int
            Number of women on the team
        distance_20min_m : float
            Distance covered in 20 minutes (meters)

        Returns
        -------
        ERGNormalizer
            Self for method chaining

        Examples
        --------
        >>> normalizer = ERGNormalizer()
        >>> normalizer.add_team('Team A', 3, 2, 6319)
        """
        self.teams[name] = {
            'n_men': n_men,
            'n_women': n_women,
            'distance_20min_m': distance_20min_m
        }
        self.results_calculated = False
        return self

    def add_teams_from_dict(self, team_dict: Dict[str, Dict]) -> 'ERGNormalizer':
        """
        Bulk add teams from a dictionary.

        Parameters
        ----------
        team_dict : dict
            Dictionary where keys are team names and values are dicts with keys:
            'n_men', 'n_women', 'distance_20min_m'

        Returns
        -------
        ERGNormalizer
            Self for method chaining

        Examples
        --------
        >>> teams = {
        ...     'Team A': {'n_men': 3, 'n_women': 2, 'distance_20min_m': 6319},
        ...     'Team B': {'n_men': 2, 'n_women': 3, 'distance_20min_m': 5530}
        ... }
        >>> normalizer = ERGNormalizer()
        >>> normalizer.add_teams_from_dict(teams)
        """
        for name, data in team_dict.items():
            self.add_team(
                name=name,
                n_men=data['n_men'],
                n_women=data['n_women'],
                distance_20min_m=data['distance_20min_m']
            )
        return self

    def _calculate_ref_power(self, n_men: int, n_women: int) -> float:
        """
        Calculate reference power based on team composition.

        Parameters
        ----------
        n_men : int
            Number of men
        n_women : int
            Number of women

        Returns
        -------
        float
            Reference power in Watts
        """
        total = n_men + n_women
        if total == 0:
            raise ValueError("Team must have at least one member")
        return (n_men * self.ref_power_men + n_women * self.ref_power_women) / total

    def calculate_scores(self) -> 'ERGNormalizer':
        """
        Calculate normalized scores for all teams.

        Returns
        -------
        ERGNormalizer
            Self for method chaining
        """
        for name, data in self.teams.items():
            ref_pwr = self._calculate_ref_power(data['n_men'], data['n_women'])
            actual_pwr = self.distance_time2power(data['distance_20min_m'], self.duration_s)
            score = actual_pwr / ref_pwr

            self.teams[name]['ref_pwr'] = ref_pwr
            self.teams[name]['actual_pwr'] = actual_pwr
            self.teams[name]['score'] = score

        self.results_calculated = True
        return self

    def get_results(self) -> pd.DataFrame:
        """
        Get results as a pandas DataFrame.

        Returns
        -------
        pd.DataFrame
            DataFrame with columns: Team, Composition, Distance (km),
            Ref Power (W), Actual Power (W), Score, Rank

        Raises
        ------
        RuntimeError
            If calculate_scores() hasn't been called yet
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate_scores() before getting results")

        data = []
        for name, team_data in self.teams.items():
            data.append({
                'Team': name,
                'Composition': f"{team_data['n_men']}M/{team_data['n_women']}W",
                'Distance (km)': team_data['distance_20min_m'] / 1000.0,
                'Ref Power (W)': round(team_data['ref_pwr'], 1),
                'Actual Power (W)': round(team_data['actual_pwr'], 1),
                'Score': round(team_data['score'], 3)
            })

        df = pd.DataFrame(data)
        df = df.sort_values('Score', ascending=False).reset_index(drop=True)
        df['Rank'] = range(1, len(df) + 1)

        # Reorder columns
        df = df[['Rank', 'Team', 'Composition', 'Distance (km)',
                 'Ref Power (W)', 'Actual Power (W)', 'Score']]

        return df

    def print_results(self) -> None:
        """
        Print formatted results table to console.

        Raises
        ------
        RuntimeError
            If calculate_scores() hasn't been called yet
        """
        df = self.get_results()

        print("\n" + "=" * 80)
        print("ERG POWER NORMALIZATION RESULTS".center(80))
        print("=" * 80)
        print(f"\nReference Powers: Men = {self.ref_power_men:.1f} W, Women = {self.ref_power_women:.1f} W")
        print("\n" + df.to_string(index=False))
        print("\n" + "=" * 80)
        print("Note: Score = Actual Power / Reference Power")
        print("Higher score means better performance relative to team composition")
        print("=" * 80 + "\n")

    def plot_results(self, save_path: Optional[str] = None,
                    figsize: tuple = (10, 6),
                    dist_color: str = "#011C5F",
                    score_color: str = "#BE0602",
                    transparent: bool = True,
                    dpi: int = 300) -> None:
        """
        Create visualization of results with dual-axis plot.

        Parameters
        ----------
        save_path : str, optional
            Path to save the figure. If None, displays instead.
        figsize : tuple, optional
            Figure size (width, height) in inches (default: (10, 6))
        dist_color : str, optional
            Color for distance bars (default: "#011C5F" - dark blue)
        score_color : str, optional
            Color for score line (default: "#BE0602" - red)
        transparent : bool, optional
            Whether to use transparent background (default: True)
        dpi : int, optional
            Resolution for saved figure (default: 300)

        Raises
        ------
        RuntimeError
            If calculate_scores() hasn't been called yet
        """
        if not self.results_calculated:
            raise RuntimeError("Call calculate_scores() before plotting")

        df = self.get_results()

        fig, ax1 = plt.subplots(figsize=figsize)

        # Transparent backgrounds
        if transparent:
            fig.patch.set_alpha(0.0)
            ax1.patch.set_alpha(0.0)

        # Bar plot for distance
        bars = ax1.bar(df['Team'], df['Distance (km)'],
                      color=dist_color, alpha=0.7,
                      label='Distance (km)', width=0.6)
        ax1.set_xlabel('')
        plt.setp(ax1.get_xticklabels(), rotation=60, ha='right', fontsize=12)
        ax1.set_ylabel('Distance (km)', color=dist_color,
                      fontsize=18, fontweight='bold')
        ax1.tick_params(axis='y', labelcolor=dist_color)
        ax1.set_ylim(0, df['Distance (km)'].max() * 1.2)

        # Twin axis for score
        ax2 = ax1.twinx()
        if transparent:
            ax2.patch.set_alpha(0.0)

        line = ax2.plot(df['Team'], df['Score'],
                       color=score_color, marker='o', markersize=10,
                       ls='', label='Score',
                       markerfacecolor='white', markeredgewidth=2)
        ax2.set_ylabel('Score', color=score_color,
                      fontsize=18, fontweight='bold')
        ax2.tick_params(axis='y', labelcolor=score_color)
        ax2.set_ylim(0, 1.1)

        # Annotations for score
        for i, row in df.iterrows():
            ax2.annotate(f'{row["Score"]:.2f}',
                        (row['Team'], row['Score']),
                        textcoords="offset points",
                        xytext=(0, 12), ha='center',
                        fontsize=16, fontweight='bold',
                        color='white')

        ax1.grid(False)
        ax2.grid(False)

        for spine in ax1.spines.values():
            spine.set_color('black')
        for spine in ax2.spines.values():
            spine.set_color('black')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, transparent=transparent, dpi=dpi)
            print(f"Plot saved to: {save_path}")
        else:
            plt.show()
