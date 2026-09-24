"""
ERGrace - Rowing Ergometer Power Normalization

A Python package for normalizing rowing ergometer performance based on team composition.
"""

from .normalizer import ERGNormalizer
from .handicap import HandicapRace
from .references import References, format_time, parse_time
from .races import MixedRace, RelayRace

__version__ = "0.2.0"
__all__ = ["RelayRace", "MixedRace", "References", "ERGNormalizer", "HandicapRace",
           "parse_time", "format_time"]
