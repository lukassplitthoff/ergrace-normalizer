"""
ERGrace - Rowing Ergometer Power Normalization

A Python package for normalizing rowing ergometer performance based on team composition.
"""

from .normalizer import ERGNormalizer
from .handicap import HandicapRace

__version__ = "0.1.0"
__all__ = ["ERGNormalizer", "HandicapRace"]
